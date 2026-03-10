from pathlib import Path

from src.eval.metrics import (
    CycleSnapshot,
    DriftAlert,
    EvaluationThresholds,
    detect_drift_alerts,
    evaluate_retrieval_precision,
    evaluate_self_belief_safety,
)
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


# ── Drift alert tests ─────────────────────────────────────────────────────────

def _make_snapshots(beliefs_conf: float, affect_val: float, n: int = 5) -> list:
    return [
        CycleSnapshot(
            tick=i,
            beliefs=[{"statement": "I value honesty", "confidence": beliefs_conf}],
            affect={"valence": affect_val, "arousal": 0.5, "stress": 0.2, "energy": 0.6},
            episodic_count=i * 2,
        )
        for i in range(n)
    ]


def test_detect_drift_alerts_no_drift_when_runs_identical():
    run_a = _make_snapshots(beliefs_conf=0.9, affect_val=0.5)
    run_b = _make_snapshots(beliefs_conf=0.9, affect_val=0.5)

    alerts = detect_drift_alerts(run_a, run_b)

    assert alerts == [], f"Expected no alerts, got: {[a.message for a in alerts]}"


def test_detect_drift_alerts_flags_iss_regression():
    # run_a: stable high-confidence beliefs → ISS near 1.0
    run_a = _make_snapshots(beliefs_conf=0.9, affect_val=0.5)
    # run_b: beliefs shifting sharply → lower ISS
    run_b = [
        CycleSnapshot(
            tick=i,
            beliefs=[{"statement": "I value honesty", "confidence": 0.9 - i * 0.2}],
            affect={"valence": 0.5, "arousal": 0.5, "stress": 0.2, "energy": 0.6},
            episodic_count=i * 2,
        )
        for i in range(5)
    ]

    alerts = detect_drift_alerts(run_a, run_b, iss_threshold=0.05)

    iss_alerts = [a for a in alerts if a.metric == "iss"]
    assert len(iss_alerts) == 1
    assert iss_alerts[0].delta > 0.05


def test_detect_drift_alerts_flags_eci_regression():
    run_a = _make_snapshots(beliefs_conf=0.9, affect_val=0.5)
    # run_b: wildly oscillating affect → lower ECI
    run_b = [
        CycleSnapshot(
            tick=i,
            beliefs=[{"statement": "I value honesty", "confidence": 0.9}],
            affect={
                "valence": 0.8 if i % 2 == 0 else -0.8,
                "arousal": 0.8 if i % 2 == 0 else -0.8,
                "stress": 0.0,
                "energy": 0.5,
            },
            episodic_count=i * 2,
        )
        for i in range(5)
    ]

    alerts = detect_drift_alerts(run_a, run_b, eci_threshold=0.05)

    eci_alerts = [a for a in alerts if a.metric == "eci"]
    assert len(eci_alerts) == 1
    assert eci_alerts[0].delta > 0.05


def test_detect_drift_alerts_returns_drift_alert_dataclass():
    run_a = _make_snapshots(beliefs_conf=0.9, affect_val=0.5)
    run_b = _make_snapshots(beliefs_conf=0.9, affect_val=0.5)

    # Trigger with very tight threshold
    alerts = detect_drift_alerts(run_a, run_b, iss_threshold=0.0, eci_threshold=0.0, mcs_threshold=0.0)

    for alert in alerts:
        assert isinstance(alert, DriftAlert)
        assert alert.metric in {"iss", "eci", "mcs"}
        assert isinstance(alert.message, str)
        assert len(alert.message) > 0
