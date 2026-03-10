import pytest

from src.engine.cycles.interaction import (
    build_context_package,
    render_response,
    retrieve_memory_candidates,
    salience_competition,
)
from src.engine.retrieval import load_retrieval_limits, rank_memory_candidates
from src.engine.orchestrator import PolicyViolation
from src.store.vector_store import VectorStore
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


@pytest.fixture
def vector_indexed_memory_fixture():
    records = [
        {
            "id": "m-alpha",
            "event_text": "I enjoyed reading near the quiet lake",
            "recency": 0.9,
            "importance": 0.85,
            "self_relevance": 0.7,
            "source": "episodic",
        },
        {
            "id": "m-beta",
            "event_text": "I fixed a bug in the parser and felt proud",
            "recency": 0.8,
            "importance": 0.75,
            "self_relevance": 0.8,
            "source": "episodic",
        },
    ]

    store = VectorStore()
    store.upsert("m-alpha", [1.0, 0.0, 0.0], {"source": "episodic"})
    store.upsert("m-beta", [0.8, 0.6, 0.0], {"source": "episodic"})

    return {"records": records, "vector_store": store}


def test_retrieve_memory_candidates_prefers_vector_results_then_reranks(
    vector_indexed_memory_fixture,
):
    fixture = vector_indexed_memory_fixture
    state = AgentState()
    event = {
        "message": "Help me recall my lakeside reading memory",
        "memory_records": fixture["records"],
        "_vector_store": fixture["vector_store"],
        "vector_filters": {"source": "episodic"},
    }

    from src.engine.cycles import interaction as interaction_cycle

    def _fake_embed_text(_text, *, content_type="user_turn"):
        return {
            "vector": [1.0, 0.0, 0.0],
            "metadata": {"model": "test", "dimension": 3, "content_type": content_type},
        }

    original = interaction_cycle.embed_text
    interaction_cycle.embed_text = _fake_embed_text
    try:
        retrieve_memory_candidates(state, event, [])
    finally:
        interaction_cycle.embed_text = original

    ids = [item["id"] for item in event["memory_candidates"]]
    assert ids[0] == "m-alpha"
    assert set(ids) == {"m-alpha", "m-beta"}


def test_retrieve_memory_candidates_keeps_why_selected_complete_with_vector_hits(
    vector_indexed_memory_fixture,
):
    fixture = vector_indexed_memory_fixture
    state = AgentState()
    event = {
        "message": "Recall coding memory",
        "memory_records": fixture["records"],
        "_vector_store": fixture["vector_store"],
    }

    from src.engine.cycles import interaction as interaction_cycle

    def _fake_embed_text(_text, *, content_type="user_turn"):
        return {
            "vector": [0.8, 0.6, 0.0],
            "metadata": {"model": "test", "dimension": 3, "content_type": content_type},
        }

    original = interaction_cycle.embed_text
    interaction_cycle.embed_text = _fake_embed_text
    try:
        retrieve_memory_candidates(state, event, [])
    finally:
        interaction_cycle.embed_text = original

    for candidate in event["memory_candidates"]:
        why_selected = candidate["why_selected"]
        assert "score_components" in why_selected
        assert "weights" in why_selected
        assert "hybrid_score" in why_selected
        assert set(why_selected["score_components"].keys()) == {
            "similarity",
            "recency",
            "importance",
            "self_relevance",
        }
