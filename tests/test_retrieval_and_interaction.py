from src.engine.cycles.interaction import (
    build_context_package,
    retrieve_memory_candidates,
    salience_competition,
)
from src.engine.retrieval import load_retrieval_limits, rank_memory_candidates
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
