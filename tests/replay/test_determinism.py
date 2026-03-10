"""
CP-1 exit gate: replay determinism tests.

Tests:
1. Identical seed + event sequence → identical state hash sequence (0% divergence)
2. Episodic store rollback leaves no residue
3. Synthetic day fixture runs end-to-end
"""

import json
from pathlib import Path
import tempfile
from typing import List

from src.engine.contracts import CycleType
from src.engine.cycle_log import hash_state
from src.engine.default_setup import register_default_steps
from src.engine.orchestrator import EgoOrchestrator
from src.schema.state import AgentState
from src.store.episodic_store import EpisodicStore


FIXTURES = Path(__file__).parent.parent / "fixtures"


def _run_sequence_with_records(seed_state: dict, cycles: list) -> tuple[List[str], List[dict]]:
    """Run cycles with a real episodic store and return hashes + record metadata."""
    state = AgentState.model_validate(seed_state)
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EpisodicStore(Path(tmpdir) / "episodic.sqlite")
        orch = register_default_steps(EgoOrchestrator(state), store=store)
        hashes = []
        for cycle_spec in cycles:
            cycle_type = CycleType(cycle_spec["type"])
            orch.run_cycle(cycle_type, cycle_spec.get("input", {}))
            hashes.append(hash_state(orch.state))

        rows = store._conn.execute(
            "SELECT id, created_at, cycle_id FROM episodic_log ORDER BY created_at ASC, id ASC"
        ).fetchall()
        records = [
            {"id": row["id"], "created_at": row["created_at"], "cycle_id": row["cycle_id"]}
            for row in rows
        ]
    return hashes, records


def _run_sequence(seed_state: dict, cycles: list) -> List[str]:
    """Run a sequence of cycles and return the list of state hashes after each cycle."""
    state = AgentState.model_validate(seed_state)
    orch = EgoOrchestrator(state)
    hashes = []
    for cycle_spec in cycles:
        cycle_type = CycleType(cycle_spec["type"])
        input_event = cycle_spec.get("input", {})
        orch.run_cycle(cycle_type, input_event)
        hashes.append(hash_state(orch.state))
    return hashes


class TestDeterminism:
    """CP-1 exit gate: replay divergence must be 0%."""

    def test_identical_seed_identical_hashes(self):
        """Two runs with the same seed and sequence must produce identical hash sequences."""
        fixture = json.loads((FIXTURES / "synthetic_day.json").read_text())
        seed = fixture["seed_state"]
        cycles = fixture["cycles"]

        run1 = _run_sequence(seed, cycles)
        run2 = _run_sequence(seed, cycles)

        divergences = [(i, h1, h2) for i, (h1, h2) in enumerate(zip(run1, run2)) if h1 != h2]

        assert not divergences, "Replay divergence detected at positions: " + ", ".join(
            f"step {i}" for i, _, _ in divergences
        )

    def test_divergence_rate_zero(self):
        """Divergence rate across all cycles must be exactly 0%."""
        fixture = json.loads((FIXTURES / "synthetic_day.json").read_text())
        seed = fixture["seed_state"]
        cycles = fixture["cycles"]

        run1 = _run_sequence(seed, cycles)
        run2 = _run_sequence(seed, cycles)

        total = len(run1)
        diverged = sum(1 for h1, h2 in zip(run1, run2) if h1 != h2)
        divergence_rate = diverged / total if total > 0 else 0.0

        assert divergence_rate == 0.0, f"Divergence rate: {divergence_rate:.2%}"

    def test_different_seeds_different_hashes(self):
        """Different seed states must produce different hash sequences (sanity check)."""
        fixture = json.loads((FIXTURES / "synthetic_day.json").read_text())
        seed_a = fixture["seed_state"]
        cycles = fixture["cycles"]

        # Modify seed B slightly
        import copy

        seed_b = copy.deepcopy(seed_a)
        seed_b["drives"]["social_need"] = 0.90  # very different

        run_a = _run_sequence(seed_a, cycles)
        run_b = _run_sequence(seed_b, cycles)

        # At least some hashes should differ
        assert run_a != run_b, "Different seeds produced identical hash sequences"

    def test_synthetic_day_fixture_completes(self):
        """The full synthetic day fixture must complete without exceptions."""
        fixture = json.loads((FIXTURES / "synthetic_day.json").read_text())
        hashes = _run_sequence(fixture["seed_state"], fixture["cycles"])
        assert len(hashes) == len(fixture["cycles"])

    def test_tick_counter_increments_deterministically(self):
        """tick_counter must be the same after N cycles regardless of run."""
        fixture = json.loads((FIXTURES / "synthetic_day.json").read_text())
        n_cycles = len(fixture["cycles"])

        state_a = AgentState.model_validate(fixture["seed_state"])
        orch_a = EgoOrchestrator(state_a)
        for cycle_spec in fixture["cycles"]:
            orch_a.run_cycle(CycleType(cycle_spec["type"]))

        state_b = AgentState.model_validate(fixture["seed_state"])
        orch_b = EgoOrchestrator(state_b)
        for cycle_spec in fixture["cycles"]:
            orch_b.run_cycle(CycleType(cycle_spec["type"]))

        assert orch_a.state.tick_counter == orch_b.state.tick_counter == n_cycles

    def test_episodic_metadata_deterministic(self):
        """Episodic record id/created_at fields must be replay-deterministic."""
        fixture = json.loads((FIXTURES / "synthetic_day.json").read_text())
        seed = fixture["seed_state"]
        cycles = fixture["cycles"]

        _, records_run1 = _run_sequence_with_records(seed, cycles)
        _, records_run2 = _run_sequence_with_records(seed, cycles)

        assert records_run1 == records_run2
        assert records_run1, "Expected at least one episodic record in synthetic_day replay"
