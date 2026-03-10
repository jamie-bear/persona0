from __future__ import annotations

import argparse
import asyncio
import random
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..engine.contracts import CycleType
from ..engine.default_setup import register_default_steps
from ..engine.orchestrator import EgoOrchestrator
from ..engine.modules._config import load_tick_config, validate_startup_config
from ..schema.state import AgentState


Hook = Callable[[], Any]


@dataclass
class SchedulerCadence:
    fast_seconds: float = 1800.0
    slow_seconds: float = 10800.0
    macro_seconds: float = 86400.0

    @classmethod
    def from_defaults(cls) -> "SchedulerCadence":
        tick_cfg = load_tick_config()
        return cls(
            fast_seconds=float(tick_cfg.get("fast_interval_seconds", 1800.0)),
            slow_seconds=float(tick_cfg.get("slow_interval_seconds", 10800.0)),
            macro_seconds=float(tick_cfg.get("macro_interval_seconds", 86400.0)),
        )


@dataclass
class RetryPolicy:
    max_retries: int = 2
    base_backoff_seconds: float = 2.0
    jitter_ratio: float = 0.2


@dataclass
class DeadLetterRecord:
    cycle_type: CycleType
    input_event: Dict[str, Any]
    reason: str
    failed_at: str


@dataclass
class SchedulerHealth:
    liveness: bool = False
    readiness: bool = False
    heartbeat_at: Optional[str] = None
    last_cycle_at: Optional[str] = None
    last_error: Optional[str] = None
    in_flight_cycles: int = 0
    dead_letter_size: int = 0


class RuntimeScheduler:
    """Async runtime scheduler for continuous fast/slow/macro execution."""

    _CYCLE_ORDER = [CycleType.FAST_TICK, CycleType.SLOW_TICK, CycleType.MACRO]

    def __init__(
        self,
        orchestrator: EgoOrchestrator,
        cadence: Optional[SchedulerCadence] = None,
        retry_policy: Optional[RetryPolicy] = None,
        *,
        sleep_fn: Optional[Callable[[float], Awaitable[None]]] = None,
        time_fn: Optional[Callable[[], float]] = None,
        jitter_fn: Optional[Callable[[float, float], float]] = None,
        startup_hooks: Optional[List[Hook]] = None,
        shutdown_hooks: Optional[List[Hook]] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.cadence = cadence or SchedulerCadence.from_defaults()
        self.retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep_fn or asyncio.sleep
        self._time = time_fn or asyncio.get_running_loop().time
        self._jitter = jitter_fn or random.uniform
        self._startup_hooks = startup_hooks or []
        self._shutdown_hooks = shutdown_hooks or []
        self.health = SchedulerHealth()
        self.dead_letters: List[DeadLetterRecord] = []
        self._shutdown_requested = False

    async def run(self, run_for_seconds: Optional[float] = None) -> None:
        await self._run_hooks(self._startup_hooks)
        self.health.liveness = True
        self.health.readiness = True
        start = self._time()
        next_due = {
            CycleType.FAST_TICK: start,
            CycleType.SLOW_TICK: start,
            CycleType.MACRO: start,
        }

        try:
            while not self._shutdown_requested:
                now = self._time()
                if run_for_seconds is not None and (now - start) >= run_for_seconds:
                    break

                due = [ct for ct in self._CYCLE_ORDER if now >= next_due[ct]]
                if not due:
                    soonest = min(next_due.values())
                    await self._sleep(max(0.0, soonest - now))
                    self._update_heartbeat()
                    continue

                for cycle_type in due:
                    interval = self._interval(cycle_type)
                    while now >= next_due[cycle_type] and not self._shutdown_requested:
                        await self._execute_with_retry(cycle_type)
                        next_due[cycle_type] += interval
                        now = self._time()
                    self._update_heartbeat()
        finally:
            self.health.readiness = False
            self.health.liveness = False
            await self._run_hooks(self._shutdown_hooks)

    def request_shutdown(self) -> None:
        self._shutdown_requested = True

    def liveness_probe(self) -> Dict[str, Any]:
        return {
            "live": self.health.liveness,
            "heartbeat_at": self.health.heartbeat_at,
            "in_flight_cycles": self.health.in_flight_cycles,
        }

    def readiness_probe(self) -> Dict[str, Any]:
        return {
            "ready": self.health.readiness,
            "last_error": self.health.last_error,
            "dead_letter_size": self.health.dead_letter_size,
        }

    async def _execute_with_retry(self, cycle_type: CycleType) -> None:
        input_event = {"source": "runtime_scheduler"}
        for attempt in range(self.retry_policy.max_retries + 1):
            self.health.in_flight_cycles += 1
            try:
                result = self.orchestrator.run_cycle(cycle_type, input_event)
                if result.success:
                    self.health.last_cycle_at = _utc_now()
                    self.health.last_error = None
                    return
                error = result.rollback_reason or "cycle rollback"
            except Exception as exc:  # broad catch keeps scheduler alive
                error = str(exc)
            finally:
                self.health.in_flight_cycles = max(0, self.health.in_flight_cycles - 1)

            if attempt >= self.retry_policy.max_retries:
                self.health.last_error = error
                self.dead_letters.append(
                    DeadLetterRecord(
                        cycle_type=cycle_type,
                        input_event=dict(input_event),
                        reason=error,
                        failed_at=_utc_now(),
                    )
                )
                self.health.dead_letter_size = len(self.dead_letters)
                return

            backoff = self.retry_policy.base_backoff_seconds * (2 ** attempt)
            backoff += self._jitter(0.0, backoff * self.retry_policy.jitter_ratio)
            await self._sleep(backoff)

    async def _run_hooks(self, hooks: List[Hook]) -> None:
        for hook in hooks:
            value = hook()
            if asyncio.iscoroutine(value):
                await value

    def _interval(self, cycle_type: CycleType) -> float:
        if cycle_type is CycleType.FAST_TICK:
            return self.cadence.fast_seconds
        if cycle_type is CycleType.SLOW_TICK:
            return self.cadence.slow_seconds
        return self.cadence.macro_seconds

    def _update_heartbeat(self) -> None:
        self.health.heartbeat_at = _utc_now()


class _StoreLifecycleHook:
    """Adapts common store lifecycle methods to scheduler hooks."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def startup(self) -> None:
        connect = getattr(self._store, "connect", None)
        if callable(connect):
            connect()

    def shutdown(self) -> None:
        close = getattr(self._store, "close", None)
        if callable(close):
            close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_runtime_scheduler(state: Optional[AgentState] = None, store: Any = None) -> RuntimeScheduler:
    validate_startup_config()
    state = state or AgentState()
    orchestrator = register_default_steps(EgoOrchestrator(state), store=store)
    startup_hooks: List[Hook] = [validate_runtime_config]
    shutdown_hooks: List[Hook] = []
    if store is not None:
        lifecycle = _StoreLifecycleHook(store)
        startup_hooks.append(lifecycle.startup)
        shutdown_hooks.append(lifecycle.shutdown)
    return RuntimeScheduler(orchestrator, startup_hooks=startup_hooks, shutdown_hooks=shutdown_hooks)


async def _run_main(duration_seconds: Optional[float] = None) -> None:
    scheduler = build_runtime_scheduler()
    loop = asyncio.get_running_loop()

    def _signal_stop(*_: Any) -> None:
        scheduler.request_shutdown()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, _signal_stop)
        except NotImplementedError:
            pass

    await scheduler.run(run_for_seconds=duration_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Persona0 runtime scheduler")
    parser.add_argument("--duration-seconds", type=float, default=None)
    args = parser.parse_args()
    asyncio.run(_run_main(duration_seconds=args.duration_seconds))


if __name__ == "__main__":
    main()
