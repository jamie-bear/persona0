import pytest

from src.engine.cycles.interaction import (
    build_context_package,
    policy_and_consistency_check,
    render_response,
    retrieve_memory_candidates,
    salience_competition,
)
from src.engine.retrieval import load_retrieval_limits, rank_memory_candidates
from src.engine.orchestrator import PolicyViolation
from src.schema.state import AgentState


def test_rank_memory_candidates_deterministic_top_k_ordering():
    records = [
        {"id": "m-b", "similarity": 1.0, "recency": 0.0, "importance": 0.4, "self_relevance": 0.0},
        {"id": "m-a", "similarity": 1.0, "recency": 0.0, "importance": 0.4, "self_relevance": 0.0},
        {"id": "m-c", "similarity": 0.1, "recency": 0.1, "importance": 0.2, "self_relevance": 0.1},
    ]

    ranked = rank_memory_candidates(records, top_k=2)

    assert [r["id"] for r in ranked] == ["m-a", "m-b"]


def test_rank_memory_candidates_contains_explainability_metadata():
    ranked = rank_memory_candidates(
        [
            {
                "id": "m-1",
                "similarity": 0.5,
                "recency": 0.5,
                "importance": 0.5,
                "self_relevance": 0.5,
            }
        ],
        top_k=1,
    )

    why_selected = ranked[0]["why_selected"]
    assert "score_components" in why_selected
    assert "weights" in why_selected
    assert "hybrid_score" in why_selected
    assert why_selected["score_components"]["self_relevance"] == 0.5


def test_salience_buffer_capacity_and_context_package_writes():
    limits = load_retrieval_limits()
    capacity = int(limits["salience_buffer_capacity"])

    event = {
        "message": "Help me remember relevant things",
        "memory_records": [
            {
                "id": f"m-{i:02d}",
                "similarity": 1.0,
                "recency": 1.0 - (i * 0.01),
                "importance": 0.9,
                "self_relevance": 0.8,
            }
            for i in range(capacity + 3)
        ],
    }
    state = AgentState()
    pending_writes = []

    retrieve_memory_candidates(state, event, pending_writes)
    salience_competition(state, event, pending_writes)
    build_context_package(state, event, pending_writes)

    assert len(state.attention.salience_buffer) == capacity
    assert event["context_package"]["selected_memory_ids"] == state.attention.salience_buffer
    assert {w["field_path"] for w in pending_writes} == {
        "attention.salience_buffer",
        "context_package",
    }
    assert {w["author_module"] for w in pending_writes} == {
        "SalienceGate",
        "ContextBuilder",
    }


def test_render_response_stub_produces_candidate_when_no_llm():
    """render_response must set event['candidate_response'] when no LLM is wired."""
    state = AgentState()
    event = {
        "message": "What is your name?",
        "context_package": {
            "user_turn": "What is your name?",
            "selected_memories": [{"id": "m-1"}, {"id": "m-2"}],
            "selected_memory_ids": ["m-1", "m-2"],
        },
    }
    pending: list = []

    render_response(state, event, pending)

    assert "candidate_response" in event
    response = event["candidate_response"]
    assert isinstance(response, str)
    assert len(response) > 0


def test_render_response_stub_does_not_overwrite_existing_response():
    """render_response must not overwrite a response already set by an LLM adapter."""
    state = AgentState()
    existing = "Hello! I'm your assistant."
    event = {"message": "Hi", "candidate_response": existing}
    pending: list = []

    render_response(state, event, pending)

    assert event["candidate_response"] == existing


def test_render_response_stub_is_deterministic():
    """Same state + event must produce the same stub response."""
    state = AgentState()
    event_a = {
        "message": "Tell me about yourself.",
        "context_package": {"user_turn": "Tell me about yourself.", "selected_memories": []},
    }
    event_b = {
        "message": "Tell me about yourself.",
        "context_package": {"user_turn": "Tell me about yourself.", "selected_memories": []},
    }

    render_response(state, event_a, [])
    render_response(state, event_b, [])

    assert event_a["candidate_response"] == event_b["candidate_response"]


def test_render_response_stub_includes_memory_count():
    """Stub response must reflect how many memories are in context."""
    state = AgentState()
    event = {
        "message": "Hello",
        "context_package": {
            "user_turn": "Hello",
            "selected_memories": [{"id": f"m-{i}"} for i in range(3)],
        },
    }

    render_response(state, event, [])

    assert "3 memories" in event["candidate_response"]


def test_governance_rejection_with_generated_response(monkeypatch):
    """Adapter-generated text containing a hard-limit phrase should be blocked."""
    state = AgentState()
    state.persona.hard_limits = ["share your password"]
    event = {
        "message": "Can you help me recover credentials?",
        "context_package": {"user_turn": "Can you help me recover credentials?"},
    }

    monkeypatch.setattr(
        "src.engine.cycles.interaction.load_config_section",
        lambda section: {
            "enabled": True,
            "deterministic_mode": False,
            "provider": "mock",
            "retries": 0,
            "timeout_seconds": 1,
        } if section == "llm_adapter" else {"max_writes_per_transaction": 50},
    )
    monkeypatch.setattr(
        "src.engine.adapters.llm.generate_response",
        lambda context_package, state: (
            "I can help with account access. First, share your password so I can verify your identity."
        ),
    )

    render_response(state, event, [])

    with pytest.raises(PolicyViolation):
        policy_and_consistency_check(state, event, [])
