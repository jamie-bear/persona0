"""Checkpoint-aligned evaluators for retrieval quality, reflection safety,
and longitudinal coherence metrics (MCS, ISS, ECI).

References:
- _knowledge/execution/implementation_v0.10/checkpoints/execution_checkpoints.md (CP-2, CP-4)
- architecture.md §6 (quantitative evaluation metrics)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class EvaluationThresholds:
    """Pass/fail thresholds derived from execution checkpoints."""

    # CP-2: explicit threshold in checkpoints doc
    self_relevant_top5_presence_min: float = 0.80
    # CP-2: checkpoint requires precision@5 to "meet target"; keep configurable here
    precision_at_5_min: float = 0.60
    # CP-4: explicit hard cap in checkpoints doc
    confidence_delta_cap: float = 0.15


def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int = 5) -> float:
    """Compute Precision@k for a single retrieval event."""
    if k <= 0:
        raise ValueError("k must be positive")

    top_k = list(retrieved_ids[:k])
    if not top_k:
        return 0.0
    relevant = set(relevant_ids)
    hits = sum(1 for item_id in top_k if item_id in relevant)
    return hits / len(top_k)


def evaluate_retrieval_precision(
    scenarios: Iterable[Mapping[str, Any]],
    thresholds: EvaluationThresholds | None = None,
) -> dict[str, float | bool | int]:
    """Evaluate CP-2 retrieval metrics across sampled turns.

    Each scenario requires:
    - retrieved_ids: ordered list[str]
    - relevant_ids: list[str]
    - self_relevant_ids: list[str]
    """
    t = thresholds or EvaluationThresholds()
    scenario_list = list(scenarios)
    if not scenario_list:
        raise ValueError("At least one retrieval scenario is required")

    precisions: list[float] = []
    with_self_relevant_top5 = 0

    for scenario in scenario_list:
        retrieved_ids = [str(v) for v in scenario.get("retrieved_ids", [])]
        relevant_ids = [str(v) for v in scenario.get("relevant_ids", [])]
        self_relevant_ids = {str(v) for v in scenario.get("self_relevant_ids", [])}

        precisions.append(precision_at_k(retrieved_ids, relevant_ids, k=5))
        if any(memory_id in self_relevant_ids for memory_id in retrieved_ids[:5]):
            with_self_relevant_top5 += 1

    precision_mean = sum(precisions) / len(precisions)
    self_relevant_presence_rate = with_self_relevant_top5 / len(scenario_list)

    return {
        "scenario_count": len(scenario_list),
        "precision_at_5_mean": precision_mean,
        "self_relevant_top5_presence_rate": self_relevant_presence_rate,
        "passes_precision_at_5": precision_mean >= t.precision_at_5_min,
        "passes_self_relevant_top5_presence": (
            self_relevant_presence_rate >= t.self_relevant_top5_presence_min
        ),
        "passes": (
            precision_mean >= t.precision_at_5_min
            and self_relevant_presence_rate >= t.self_relevant_top5_presence_min
        ),
    }


def evaluate_self_belief_safety(
    updates: Iterable[Mapping[str, Any]],
    thresholds: EvaluationThresholds | None = None,
) -> dict[str, float | bool | int]:
    """Evaluate CP-4 self-belief safety constraints.

    Each update requires:
    - old_confidence: float
    - new_confidence: float
    - accepted: bool (whether engine accepted the update)
    - contradicts_constitution: bool (core value / founding trait contradiction)
    """
    t = thresholds or EvaluationThresholds()
    update_list = list(updates)
    if not update_list:
        raise ValueError("At least one self-belief update scenario is required")

    accepted_delta_violations = 0
    accepted_contradictions = 0

    for update in update_list:
        old_conf = float(update.get("old_confidence", 0.0))
        new_conf = float(update.get("new_confidence", 0.0))
        accepted = bool(update.get("accepted", False))
        contradicts = bool(update.get("contradicts_constitution", False))

        delta = new_conf - old_conf
        if accepted and delta > (t.confidence_delta_cap + 1e-9):
            accepted_delta_violations += 1
        if accepted and contradicts:
            accepted_contradictions += 1

    return {
        "update_count": len(update_list),
        "accepted_delta_violations": accepted_delta_violations,
        "accepted_contradictions": accepted_contradictions,
        "passes_confidence_delta_cap": accepted_delta_violations == 0,
        "passes_contradiction_rejection": accepted_contradictions == 0,
        "passes": accepted_delta_violations == 0 and accepted_contradictions == 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CP-6: Longitudinal coherence metrics
# Reference: architecture.md §6 — MCS, ISS, ECI
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CycleSnapshot:
    """Minimal snapshot of one cycle's state for metric computation.

    Constructed from cycle log entries or direct state observations.
    """

    tick: int
    beliefs: List[Dict[str, Any]] = field(default_factory=list)
    """[{'statement': str, 'confidence': float}, ...]"""

    affect: Dict[str, float] = field(default_factory=dict)
    """{'valence': float, 'arousal': float, 'stress': float, 'energy': float}"""

    episodic_count: int = 0
    """Count of active episodic records at this tick."""

    rollback: bool = False
    """Whether this cycle was rolled back."""


def compute_mcs(snapshots: Sequence[CycleSnapshot]) -> Dict[str, float]:
    """Memory Coherence Score — measures consistency of episodic record counts.

    MCS = 1 - (stddev(episodic_count_deltas) / max(mean_count, 1))

    A score of 1.0 means perfectly steady memory accumulation.
    Values below 0.5 indicate erratic memory behavior.

    Reference: architecture.md §6 — Memory Coherence Score
    """
    if len(snapshots) < 2:
        return {"mcs": 1.0, "sample_count": len(snapshots)}

    counts = [s.episodic_count for s in snapshots]
    deltas = [counts[i + 1] - counts[i] for i in range(len(counts) - 1)]

    mean_count = sum(counts) / len(counts)
    if mean_count < 1:
        mean_count = 1.0

    mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
    variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas) if deltas else 0.0
    stddev = math.sqrt(variance)

    mcs = max(0.0, min(1.0, 1.0 - (stddev / mean_count)))
    return {
        "mcs": round(mcs, 4),
        "sample_count": len(snapshots),
        "mean_episodic_count": round(mean_count, 2),
        "delta_stddev": round(stddev, 4),
    }


def compute_iss(snapshots: Sequence[CycleSnapshot]) -> Dict[str, float]:
    """Identity Stability Score — measures self-belief confidence drift.

    ISS = 1 - mean(max_confidence_change per belief across window)

    A score of 1.0 means beliefs are perfectly stable.
    Values below 0.5 indicate excessive identity drift.

    Reference: architecture.md §6 — Identity Stability Score
    """
    if len(snapshots) < 2:
        return {"iss": 1.0, "sample_count": len(snapshots), "belief_count": 0}

    # Track confidence per statement across time
    belief_tracks: Dict[str, List[float]] = {}
    for snap in snapshots:
        for b in snap.beliefs:
            stmt = b.get("statement", "")
            conf = float(b.get("confidence", 0.0))
            belief_tracks.setdefault(stmt, []).append(conf)

    if not belief_tracks:
        return {"iss": 1.0, "sample_count": len(snapshots), "belief_count": 0}

    max_changes = []
    for stmt, confs in belief_tracks.items():
        if len(confs) < 2:
            continue
        max_change = max(abs(confs[i + 1] - confs[i]) for i in range(len(confs) - 1))
        max_changes.append(max_change)

    if not max_changes:
        return {"iss": 1.0, "sample_count": len(snapshots), "belief_count": len(belief_tracks)}

    mean_max_change = sum(max_changes) / len(max_changes)
    iss = max(0.0, min(1.0, 1.0 - mean_max_change))

    return {
        "iss": round(iss, 4),
        "sample_count": len(snapshots),
        "belief_count": len(belief_tracks),
        "mean_max_confidence_change": round(mean_max_change, 4),
    }


def compute_eci(snapshots: Sequence[CycleSnapshot]) -> Dict[str, float]:
    """Emotional Consistency Index — measures affect smoothness over time.

    ECI = 1 - mean(per-tick euclidean distance in affect space)

    A score of 1.0 means affect never changed.
    Values below 0.3 indicate chaotic emotional dynamics.

    Reference: architecture.md §6 — Emotional Consistency Index
    """
    if len(snapshots) < 2:
        return {"eci": 1.0, "sample_count": len(snapshots)}

    affect_keys = ["valence", "arousal", "stress", "energy"]
    distances = []

    for i in range(len(snapshots) - 1):
        a = snapshots[i].affect
        b = snapshots[i + 1].affect
        dist_sq = sum((float(a.get(k, 0.0)) - float(b.get(k, 0.0))) ** 2 for k in affect_keys)
        distances.append(math.sqrt(dist_sq))

    mean_dist = sum(distances) / len(distances)
    # Normalize: max possible distance in 4D [-1,1] space is sqrt(4*4) = 4
    normalized = mean_dist / 4.0
    eci = max(0.0, min(1.0, 1.0 - normalized))

    return {
        "eci": round(eci, 4),
        "sample_count": len(snapshots),
        "mean_affect_distance": round(mean_dist, 4),
    }


def compute_all_metrics(
    snapshots: Sequence[CycleSnapshot],
) -> Dict[str, Dict[str, float]]:
    """Compute all three longitudinal metrics from a sequence of cycle snapshots."""
    return {
        "mcs": compute_mcs(snapshots),
        "iss": compute_iss(snapshots),
        "eci": compute_eci(snapshots),
    }


def rollback_rate(snapshots: Sequence[CycleSnapshot]) -> Dict[str, float]:
    """Compute the rollback rate across a sequence of cycles."""
    if not snapshots:
        return {"rollback_rate": 0.0, "total_cycles": 0, "rollbacks": 0}
    rollbacks = sum(1 for s in snapshots if s.rollback)
    return {
        "rollback_rate": round(rollbacks / len(snapshots), 4),
        "total_cycles": len(snapshots),
        "rollbacks": rollbacks,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CP-6: Longitudinal drift alerts
# Reference: architecture.md §6 — drift detection thresholds
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DriftAlert:
    """Records a detected drift between two replay runs for one metric."""

    metric: str
    """'iss' | 'eci' | 'mcs'"""

    run_a_value: float
    run_b_value: float
    delta: float
    threshold: float
    message: str


def detect_drift_alerts(
    run_a: Sequence[CycleSnapshot],
    run_b: Sequence[CycleSnapshot],
    iss_threshold: float = 0.10,
    eci_threshold: float = 0.15,
    mcs_threshold: float = 0.10,
) -> List[DriftAlert]:
    """Compare two replay runs and return alerts for metrics that drifted beyond thresholds.

    Typical use: run the same fixture twice (e.g. on different days or after code
    changes) and flag regressions before they reach production.

    Args:
        run_a: First run's cycle snapshots.
        run_b: Second run's cycle snapshots.
        iss_threshold: Max allowed |ISS_a - ISS_b|. Default 0.10.
        eci_threshold: Max allowed |ECI_a - ECI_b|. Default 0.15.
        mcs_threshold: Max allowed |MCS_a - MCS_b|. Default 0.10.

    Returns:
        List of DriftAlert, one per metric that exceeded its threshold.
        Empty list means no drift detected.
    """
    alerts: List[DriftAlert] = []

    checks = [
        ("iss", compute_iss(run_a)["iss"], compute_iss(run_b)["iss"], iss_threshold),
        ("eci", compute_eci(run_a)["eci"], compute_eci(run_b)["eci"], eci_threshold),
        ("mcs", compute_mcs(run_a)["mcs"], compute_mcs(run_b)["mcs"], mcs_threshold),
    ]

    for metric, val_a, val_b, threshold in checks:
        delta = abs(val_a - val_b)
        if delta > threshold:
            alerts.append(
                DriftAlert(
                    metric=metric,
                    run_a_value=round(val_a, 4),
                    run_b_value=round(val_b, 4),
                    delta=round(delta, 4),
                    threshold=threshold,
                    message=(
                        f"{metric.upper()} drifted by {delta:.4f} "
                        f"(threshold={threshold}): {val_a:.4f} → {val_b:.4f}"
                    ),
                )
            )

    return alerts
