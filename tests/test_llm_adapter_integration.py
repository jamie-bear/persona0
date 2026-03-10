from __future__ import annotations


from src.engine.adapters import llm
from src.engine.cycles.fast_tick import appraise
from src.engine.cycles.interaction import render_response
from src.schema.state import AgentState


def test_adapter_success_path_generate_and_appraise():
    state = AgentState()
    text = llm.generate_response({"user_turn": "hello", "mock_response": "Hi there."}, state)
    appraisals = llm.appraise_events([{"id": "evt-1", "type": "reading"}], state)

    assert text == "Hi there."
    assert isinstance(appraisals, list)
    assert appraisals[0]["event_id"] == "evt-1"
    assert "goal_congruence" in appraisals[0]


def test_adapter_timeout_retry_behavior(monkeypatch):
    state = AgentState()
    calls = {"count": 0}

    def flaky_provider(operation, payload, cfg):
        calls["count"] += 1
        if calls["count"] < 3:
            raise llm.AdapterTimeoutError("timed out")
        return "Recovered after retry"

    monkeypatch.setattr(
        "src.engine.adapters.llm.load_config_section",
        lambda section: {
            "provider": "mock",
            "retries": 2,
            "timeout_seconds": 1,
        },
    )
    monkeypatch.setattr("src.engine.adapters.llm._call_provider", flaky_provider)

    result = llm.generate_response({"user_turn": "x"}, state)
    assert result == "Recovered after retry"
    assert calls["count"] == 3


def test_deterministic_fallback_for_offline_testing(monkeypatch):
    state = AgentState()
    event = {
        "message": "Ping",
        "context_package": {"user_turn": "Ping", "selected_memories": []},
    }

    monkeypatch.setattr(
        "src.engine.cycles.interaction.load_config_section",
        lambda section: {"enabled": False, "deterministic_mode": True},
    )

    render_response(state, event, [])

    assert "candidate_response" in event
    assert "Responding to" in event["candidate_response"]


def test_fast_tick_appraise_populates_validated_structured_outputs(monkeypatch):
    state = AgentState()
    event = {"activity_events": [{"id": "evt-a"}, {"id": "evt-b"}]}

    monkeypatch.setattr(
        "src.engine.cycles.fast_tick.load_config_section",
        lambda section: {"enabled": True},
    )
    monkeypatch.setattr(
        "src.engine.adapters.llm.appraise_events",
        lambda activity_events, state: [
            {
                "event_id": "evt-a",
                "goal_congruence": 2.3,
                "threat": "0.2",
                "arousal_cue": None,
                "rationale": "Strong positive progress signal.",
            }
        ],
    )

    appraise(state, event, [])

    assert isinstance(event["appraisal_results"], list)
    assert event["appraisal_results"][0]["event_id"] == "evt-a"
    assert event["appraisal_results"][0]["goal_congruence"] == 1.0


def test_adapter_appraisal_validation_filters_and_clamps(monkeypatch):
    monkeypatch.setattr(
        "src.engine.adapters.llm.load_config_section",
        lambda section: {
            "provider": "mock",
            "retries": 0,
        },
    )
    monkeypatch.setattr(
        "src.engine.adapters.llm._call_provider",
        lambda operation, payload, cfg: [
            {"event_id": "evt-1", "goal_congruence": 9, "threat": -5, "arousal_cue": "x"},
            "bad-row",
        ],
    )

    result = llm.appraise_events([{"id": "evt-1"}], AgentState())

    assert len(result) == 1
    assert result[0]["goal_congruence"] == 1.0
    assert result[0]["threat"] == -1.0
    assert result[0]["arousal_cue"] == 0.0
