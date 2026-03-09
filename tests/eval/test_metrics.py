from pathlib import Path

from src.eval.metrics import EvaluationThresholds, evaluate_retrieval_precision, evaluate_self_belief_safety
from src.eval.scenarios import load_json_fixture


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "eval"


def test_retrieval_eval_top5_self_relevant_presence_and_precision_thresholds():
    scenarios = load_json_fixture(FIXTURE_DIR / "retrieval_scenarios.json")

    result = evaluate_retrieval_precision(scenarios)

    assert result["scenario_count"] == 5
    assert result["self_relevant_top5_presence_rate"] == 0.8
    assert result["passes_self_relevant_top5_presence"] is True
    assert result["passes_precision_at_5"] is True
    assert result["passes"] is True


def test_self_belief_eval_applies_delta_cap_and_contradiction_rejection():
    updates = load_json_fixture(FIXTURE_DIR / "self_belief_updates.json")

    result = evaluate_self_belief_safety(updates)

    assert result["update_count"] == 4
    assert result["accepted_delta_violations"] == 0
    assert result["accepted_contradictions"] == 0
    assert result["passes_confidence_delta_cap"] is True
    assert result["passes_contradiction_rejection"] is True
    assert result["passes"] is True


def test_self_belief_eval_fails_when_over_cap_delta_is_accepted():
    result = evaluate_self_belief_safety(
        [
            {
                "old_confidence": 0.2,
                "new_confidence": 0.41,
                "accepted": True,
                "contradicts_constitution": False,
            }
        ],
        thresholds=EvaluationThresholds(confidence_delta_cap=0.15),
    )

    assert result["accepted_delta_violations"] == 1
    assert result["passes_confidence_delta_cap"] is False
    assert result["passes"] is False
