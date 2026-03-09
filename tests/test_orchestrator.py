"""
CP-1 exit gate: orchestrator commit/rollback tests.

Tests:
1. Successful cycle commits state changes
2. Forced rollback leaves store unchanged
3. CONST write attempt triggers rollback
4. Rollback leaves state identical to before-snapshot
5. Cycle log is emitted for both success and rollback cases
"""
import json
import tempfile
from pathlib import Path

import pytest

from src.engine.contracts import CycleType
from src.engine.cycle_log import CycleLogger, hash_state
from src.engine.orchestrator import EgoOrchestrator, PolicyViolation
from src.schema.state import AgentState


def _make_orchestrator(tmp_path: Path) -> tuple[EgoOrchestrator, CycleLogger, Path]:
    log_path = tmp_path / "test.jsonl"
    logger = CycleLogger(log_path)
    state = AgentState()
    state.persona.name = "Mira"
    orch = EgoOrchestrator(state, logger)
    return orch, logger, log_path


# ─────────────────────────────────────────────────────────────────────────────
# Basic commit / rollback
# ─────────────────────────────────────────────────────────────────────────────

def test_successful_cycle_returns_success(tmp_path):
    """A cycle with no step functions registered succeeds (all no-ops)."""
    orch, logger, _ = _make_orchestrator(tmp_path)
    result = orch.run_cycle(CycleType.FAST_TICK)
    assert result.success
    assert result.rollback_reason is None


def test_successful_cycle_increments_tick(tmp_path):
    """A successful cycle must increment the tick counter."""
    orch, _, _ = _make_orchestrator(tmp_path)
    assert orch.state.tick_counter == 0
    orch.run_cycle(CycleType.FAST_TICK)
    assert orch.state.tick_counter == 1


def test_policy_violation_triggers_rollback(tmp_path):
    """A step that raises PolicyViolation must cause full rollback."""
    orch, _, _ = _make_orchestrator(tmp_path)

    def bad_step(state, event, pending_writes):
        raise PolicyViolation("Simulated policy failure")

    orch.register_step("world_ingest", bad_step)

    before_hash = hash_state(orch.state)
    result = orch.run_cycle(CycleType.FAST_TICK)

    assert not result.success
    assert result.rollback_reason is not None
    assert "Simulated policy failure" in result.rollback_reason
    # State must be identical to before
    assert hash_state(orch.state) == before_hash


def test_rollback_leaves_no_state_residue(tmp_path):
    """After rollback, the state must be bit-identical to the before-snapshot."""
    orch, _, _ = _make_orchestrator(tmp_path)

    def mutating_then_failing_step(state, event, pending_writes):
        state.affect.valence = 0.99  # mutate state
        raise PolicyViolation("Fail after mutation")

    orch.register_step("update_emotion", mutating_then_failing_step)

    snapshot_json = orch.state.model_dump_json()
    orch.run_cycle(CycleType.FAST_TICK)
    after_json = orch.state.model_dump_json()

    assert json.loads(snapshot_json) == json.loads(after_json), (
        "Rollback did not restore state to pre-cycle snapshot"
    )


def test_const_write_triggers_rollback(tmp_path):
    """Attempted write to CONST field via validate_const_fields_unchanged must rollback."""
    orch, _, _ = _make_orchestrator(tmp_path)

    def mutate_const(state, event, pending_writes):
        state.persona.name = "Hacked"  # CONST violation

    orch.register_step("world_ingest", mutate_const)

    result = orch.run_cycle(CycleType.FAST_TICK)
    assert not result.success
    assert "CONST" in (result.rollback_reason or "")
    # Name must be restored
    assert orch.state.persona.name == "Mira"


def test_multiple_successful_cycles(tmp_path):
    """Multiple sequential cycles must all succeed when no violations occur."""
    orch, _, _ = _make_orchestrator(tmp_path)
    for _ in range(5):
        result = orch.run_cycle(CycleType.FAST_TICK)
        assert result.success
    assert orch.state.tick_counter == 5


# ─────────────────────────────────────────────────────────────────────────────
# Cycle log
# ─────────────────────────────────────────────────────────────────────────────

def test_cycle_log_emitted_on_success(tmp_path):
    """A successful cycle must write one entry to the cycle log."""
    orch, logger, log_path = _make_orchestrator(tmp_path)
    orch.run_cycle(CycleType.FAST_TICK)
    entries = logger.read_all()
    assert len(entries) == 1
    assert not entries[0].rollback


def test_cycle_log_emitted_on_rollback(tmp_path):
    """A rolled-back cycle must write one entry marked rollback=True."""
    orch, logger, log_path = _make_orchestrator(tmp_path)

    def fail_step(state, event, pending_writes):
        raise PolicyViolation("forced rollback")

    orch.register_step("world_ingest", fail_step)
    orch.run_cycle(CycleType.FAST_TICK)

    entries = logger.read_all()
    assert len(entries) == 1
    assert entries[0].rollback


def test_cycle_log_before_after_hash_populated(tmp_path):
    """Cycle log entries must have non-empty before and after state hashes."""
    orch, logger, _ = _make_orchestrator(tmp_path)
    orch.run_cycle(CycleType.FAST_TICK)
    entries = logger.read_all()
    assert entries[0].before_state_hash
    assert entries[0].after_state_hash
    assert len(entries[0].before_state_hash) == 64  # SHA-256 hex


def test_rollback_entry_before_equals_after_hash(tmp_path):
    """On rollback, before_state_hash must equal after_state_hash (no change)."""
    orch, logger, _ = _make_orchestrator(tmp_path)

    def fail_step(state, event, pending_writes):
        raise PolicyViolation("forced")

    orch.register_step("world_ingest", fail_step)
    orch.run_cycle(CycleType.FAST_TICK)

    entries = logger.read_all()
    assert entries[0].before_state_hash == entries[0].after_state_hash


# ─────────────────────────────────────────────────────────────────────────────
# All cycle types execute without error
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cycle_type", list(CycleType))
def test_all_cycle_types_run(tmp_path, cycle_type):
    """Every cycle type must complete without raising exceptions."""
    orch, _, _ = _make_orchestrator(tmp_path)
    result = orch.run_cycle(cycle_type)
    assert result.success
