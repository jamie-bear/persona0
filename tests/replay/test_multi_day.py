"""
CP-6: Multi-day replay tests with longitudinal metric computation.

Tests:
1. Multi-day simulation completes without error across 3 simulated days
2. Replay determinism holds across multi-day runs
3. MCS/ISS/ECI metrics computed from cycle snapshots meet thresholds
4. Rollback rate is 0% across entire simulation
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from src.engine.contracts import CycleType
from src.engine.cycle_log import hash_state
from src.engine.default_setup import register_default_steps
from src.engine.orchestrator import EgoOrchestrator
from src.eval.metrics import (
    CycleSnapshot,
    compute_all_metrics,
    compute_eci,
    compute_iss,
    compute_mcs,
    rollback_rate,
)
from src.schema.state import AgentState

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _run_multi_day(seed_state: dict, cycles: list) -> tuple[list[str], list[CycleSnapshot]]:
    """Run a multi-day cycle sequence and collect hashes + snapshots."""
    state = AgentState.model_validate(seed_state)
    orch = register_default_steps(EgoOrchestrator(state))
    hashes = []
    snapshots = []

    for cycle_spec in cycles:
        cycle_type = CycleType(cycle_spec["type"])
        result = orch.run_cycle(cycle_type, cycle_spec.get("input", {}))
        hashes.append(hash_state(orch.state))

        # Collect snapshot for metrics
        snapshots.append(CycleSnapshot(
            tick=orch.state.tick_counter,
            beliefs=[
                {"statement": b.statement, "confidence": b.confidence}
                for b in orch.state.self_model.beliefs
            ],
            affect={
                "valence": orch.state.affect.valence,
                "arousal": orch.state.affect.arousal,
                "stress": orch.state.affect.stress,
                "energy": orch.state.affect.energy,
            },
            episodic_count=orch.state.tick_counter,  # proxy: tick count ≈ record count
            rollback=not result.success,
        ))

    return hashes, snapshots


class TestMultiDayReplay:
    """CP-6: Multi-day simulation and metric validation."""

    def test_multi_day_completes(self) -> None:
        """24-cycle, 3-day simulation must complete without exceptions."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        hashes, snapshots = _run_multi_day(fixture["seed_state"], fixture["cycles"])
        assert len(hashes) == len(fixture["cycles"])
        assert len(snapshots) == len(fixture["cycles"])

    def test_multi_day_determinism(self) -> None:
        """Two runs with the same seed must produce identical hash sequences."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        run1, _ = _run_multi_day(fixture["seed_state"], fixture["cycles"])
        run2, _ = _run_multi_day(fixture["seed_state"], fixture["cycles"])

        divergences = [i for i, (h1, h2) in enumerate(zip(run1, run2)) if h1 != h2]
        assert not divergences, f"Divergence at positions: {divergences}"

    def test_zero_rollback_rate(self) -> None:
        """Rollback rate across all cycles must be 0%."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        _, snapshots = _run_multi_day(fixture["seed_state"], fixture["cycles"])

        result = rollback_rate(snapshots)
        assert result["rollback_rate"] == 0.0, f"Rollback rate: {result['rollback_rate']}"

    def test_mcs_above_threshold(self) -> None:
        """Memory Coherence Score must be >= 0.5."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        _, snapshots = _run_multi_day(fixture["seed_state"], fixture["cycles"])

        result = compute_mcs(snapshots)
        assert result["mcs"] >= 0.5, f"MCS too low: {result['mcs']}"

    def test_iss_above_threshold(self) -> None:
        """Identity Stability Score must be >= 0.5."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        _, snapshots = _run_multi_day(fixture["seed_state"], fixture["cycles"])

        result = compute_iss(snapshots)
        assert result["iss"] >= 0.5, f"ISS too low: {result['iss']}"

    def test_eci_above_threshold(self) -> None:
        """Emotional Consistency Index must be >= 0.3."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        _, snapshots = _run_multi_day(fixture["seed_state"], fixture["cycles"])

        result = compute_eci(snapshots)
        assert result["eci"] >= 0.3, f"ECI too low: {result['eci']}"

    def test_all_metrics_computed(self) -> None:
        """compute_all_metrics should return all three metric categories."""
        fixture = json.loads((FIXTURES / "multi_day.json").read_text())
        _, snapshots = _run_multi_day(fixture["seed_state"], fixture["cycles"])

        all_results = compute_all_metrics(snapshots)
        assert "mcs" in all_results
        assert "iss" in all_results
        assert "eci" in all_results

        # Verify each has the expected score key
        assert "mcs" in all_results["mcs"]
        assert "iss" in all_results["iss"]
        assert "eci" in all_results["eci"]
