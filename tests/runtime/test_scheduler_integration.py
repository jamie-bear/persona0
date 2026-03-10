from __future__ import annotations

import pytest

from src.engine.contracts import CycleType
from src.engine.default_setup import register_default_steps
from src.engine.orchestrator import CycleResult, EgoOrchestrator
from src.runtime.scheduler import RetryPolicy, RuntimeScheduler, SchedulerCadence
from src.schema.state import AgentState


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += max(0.0, seconds)


@pytest.mark.asyncio
async def test_multi_hour_accelerated_ordering_is_deterministic() -> None:
    state = AgentState()
    orchestrator = register_default_steps(EgoOrchestrator(state))
    clock = FakeClock()

    ordering: list[CycleType] = []

    def run_cycle_spy(cycle_type: CycleType, input_event):
        ordering.append(cycle_type)
        return CycleResult(success=True, cycle_id=f"{len(ordering)}", cycle_type=cycle_type)

    orchestrator.run_cycle = run_cycle_spy  # type: ignore[assignment]

    scheduler = RuntimeScheduler(
        orchestrator,
        cadence=SchedulerCadence(fast_seconds=10, slow_seconds=30, macro_seconds=120),
        retry_policy=RetryPolicy(max_retries=1, base_backoff_seconds=1.0, jitter_ratio=0.0),
        time_fn=clock.time,
        sleep_fn=clock.sleep,
        jitter_fn=lambda _a, _b: 0.0,
    )

    await scheduler.run(run_for_seconds=360)

    assert len(ordering) == 51
    assert ordering[:3] == [CycleType.FAST_TICK, CycleType.SLOW_TICK, CycleType.MACRO]

    second_run_ordering: list[CycleType] = []

    def run_cycle_spy_2(cycle_type: CycleType, input_event):
        second_run_ordering.append(cycle_type)
        return CycleResult(success=True, cycle_id=f"r2-{len(second_run_ordering)}", cycle_type=cycle_type)

    orchestrator.run_cycle = run_cycle_spy_2  # type: ignore[assignment]
    clock.now = 0.0

    await scheduler.run(run_for_seconds=360)

    assert second_run_ordering == ordering


@pytest.mark.asyncio
async def test_retries_dead_letter_and_rollback_state_restoration() -> None:
    state = AgentState()
    orchestrator = register_default_steps(EgoOrchestrator(state))
    clock = FakeClock()

    attempts = {"fast": 0}

    def run_cycle_stub(cycle_type: CycleType, input_event):
        if cycle_type is CycleType.FAST_TICK:
            attempts["fast"] += 1
            return CycleResult(
                success=False,
                cycle_id=f"failed-{attempts['fast']}",
                cycle_type=cycle_type,
                rollback_reason="synthetic failure",
            )
        return CycleResult(success=True, cycle_id="ok", cycle_type=cycle_type)

    orchestrator.run_cycle = run_cycle_stub  # type: ignore[assignment]

    scheduler = RuntimeScheduler(
        orchestrator,
        cadence=SchedulerCadence(fast_seconds=10, slow_seconds=10_000, macro_seconds=10_000),
        retry_policy=RetryPolicy(max_retries=1, base_backoff_seconds=5.0, jitter_ratio=0.0),
        time_fn=clock.time,
        sleep_fn=clock.sleep,
        jitter_fn=lambda _a, _b: 0.0,
    )

    await scheduler.run(run_for_seconds=15)

    assert attempts["fast"] == 4
    assert len(scheduler.dead_letters) == 2
    assert scheduler.dead_letters[0].cycle_type is CycleType.FAST_TICK
    assert scheduler.readiness_probe()["dead_letter_size"] == 2


def test_orchestrator_rollback_restores_state_after_failed_cycle() -> None:
    state = AgentState()
    orchestrator = register_default_steps(EgoOrchestrator(state))

    def failing_world_ingest(state, event, pending_writes):
        state.activity.current_activity = "mutated-but-rollback"
        pending_writes.append({"field_path": "persona.name", "writer": "DriveModule"})

    orchestrator.register_step("world_ingest", failing_world_ingest)
    result = orchestrator.run_cycle(CycleType.FAST_TICK, {"source": "test"})

    assert result.success is False
    assert state.activity.current_activity == "idle"
