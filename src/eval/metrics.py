"""Checkpoint-aligned evaluators for retrieval quality and reflection safety.

References:
- .knowledge/execution/v0.1/checkpoints/execution_checkpoints.md (CP-2, CP-4)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


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
    scenarios: Iterable[Mapping[str, object]],
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
    updates: Iterable[Mapping[str, object]],
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
