from src.engine.cycles.fast_tick import write_memory
from src.engine.cycles.slow_tick import routine_event
from src.schema.state import AgentState
from src.store.vector_store import VectorStore


def test_write_memory_adds_embedding_metadata_and_vector_upsert():
    state = AgentState()
    vector_store = VectorStore()
    event = {
        "generated_thought": {
            "text": "I should follow up on that debugging session.",
            "intrusiveness": 0.6,
            "thought_category": "planning",
            "trigger": "internal",
        },
        "_vector_store": vector_store,
    }

    write_memory(state, event, [])

    record = event["_pending_episodic"][0]
    assert "embedding" in record
    assert record["embedding"]["content_type"] == "episodic_thought"
    assert vector_store.query([1.0] + [0.0] * 15, top_k=10, filters=None)


def test_routine_event_adds_embedding_metadata():
    state = AgentState()
    event = {"_new_activity": "reading"}

    routine_event(state, event, [])

    record = event["_pending_episodic"][0]
    assert "embedding" in record
    assert record["embedding"]["content_type"] == "episodic_routine"
