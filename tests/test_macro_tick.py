from __future__ import annotations

from src.engine.cycles.macro import (
    archive_reflection,
    cluster_episodes,
    drive_review,
    produce_candidate_reflections,
    score_evidence_sufficiency,
    select_high_signal_episodes,
    update_self_beliefs,
)
from src.schema.state import AgentState, SelfBelief


def _episode(
    eid: str,
    importance: float,
    *,
    valence: float = 0.0,
    stress: float = 0.0,
    goal: str | None = None,
    location: str | None = None,
    created_at: str = "2026-01-01T00:00:00Z",
):
    return {
        "id": eid,
        "created_at": created_at,
        "event_text": f"event {eid}",
        "importance": importance,
        "affect_snapshot": {"valence": valence, "stress": stress},
        "goal_links": [goal] if goal else [],
        "context": {"location": location} if location else {},
        "record_type": "routine_event",
    }


def test_select_high_signal_episodes_top_k_ordering() -> None:
    state = AgentState()
    event = {
        "_macro_top_k": 2,
        "_macro_source_episodes": [
            _episode("e1", 0.2, valence=0.1),
            _episode("e2", 0.9, stress=0.9),
            _episode("e3", 0.6, goal="g1"),
        ],
    }

    select_high_signal_episodes(state, event, [])

    selected_ids = [r["id"] for r in event["_macro_selected_episodes"]]
    assert selected_ids == ["e2", "e3"]


def test_macro_pipeline_updates_self_beliefs_with_pending_write() -> None:
    state = AgentState()
    event = {
        "_macro_source_episodes": [
            _episode("e1", 0.9, goal="g1", created_at="2026-01-01T00:00:00Z"),
            _episode("e2", 0.85, goal="g1", created_at="2026-01-01T03:00:00Z"),
            _episode("e3", 0.8, goal="g1", created_at="2026-01-02T01:00:00Z"),
        ],
    }
    pending = []

    select_high_signal_episodes(state, event, pending)
    cluster_episodes(state, event, pending)
    produce_candidate_reflections(state, event, pending)
    score_evidence_sufficiency(state, event, pending)
    update_self_beliefs(state, event, pending)

    assert state.self_model.beliefs
    assert any(b.source_type == "REFLECTION" for b in state.self_model.beliefs)
    assert any(w["field_path"] == "self_model.beliefs" for w in pending)


def test_confidence_capped_without_two_supporting_reflections() -> None:
    belief = SelfBelief(
        id="b1",
        statement="I repeatedly engage with goal:g1.",
        confidence=0.74,
        source_type="REFLECTION",
    )
    state = AgentState(self_model={"beliefs": [belief.model_dump()]})
    event = {
        "_macro_scored_reflections": [
            {
                "reflection_id": "r1",
                "proposed_self_belief_update": "I repeatedly engage with goal:g1.",
                "confidence_delta": 0.15,
                "evidence_score": 0.95,
                "source_episode_ids": ["e1", "e2"],
                "pattern_statement": "pattern",
            }
        ]
    }

    update_self_beliefs(state, event, pending := [])

    assert state.self_model.beliefs[0].confidence == 0.75
    assert len(state.self_model.beliefs[0].supporting_reflections) == 1
    assert pending


def test_archive_reflection_emits_semantic_store_write() -> None:
    state = AgentState()
    event = {
        "_macro_accepted_reflections": [
            {
                "reflection_id": "r1",
                "source_episode_ids": ["e1", "e2"],
                "pattern_statement": "pattern",
                "confidence_delta": 0.1,
                "evidence_score": 0.8,
            }
        ]
    }
    pending = []

    archive_reflection(state, event, pending)

    assert len(event["_pending_reflections"]) == 1
    assert any(w["field_path"] == "semantic_store" for w in pending)


def test_drive_review_reports_unmet_drives() -> None:
    state = AgentState()
    state.drives.social_need = 0.75
    state.drives.mastery_need = 0.65

    event = {}
    drive_review(state, event, [])

    assert event["_macro_unmet_drives"] == [{"drive": "social_need", "value": 0.75}]


def test_drive_review_clears_nightly_ephemeral_state() -> None:
    """Verify that drive_review clears persisted_desires and consecutive_thought_categories."""
    state = AgentState()
    state.persisted_desires = [{"id": "d1", "source_drive": "social_need", "urgency": 0.7}]
    state.consecutive_thought_categories = ["reflection", "reflection", "planning"]

    pending: list = []
    drive_review(state, {}, pending)

    assert state.persisted_desires == []
    assert state.consecutive_thought_categories == []
    assert any(w["field_path"] == "persisted_desires" for w in pending)


def test_max_new_statements_per_cycle_enforced() -> None:
    """Verify that update_self_beliefs respects the max_new_statements_per_cycle cap."""
    state = AgentState()

    # Create 5 distinct reflections that would each create a new belief
    reflections = []
    for i in range(5):
        reflections.append({
            "reflection_id": f"r{i}",
            "proposed_self_belief_update": f"I engage with topic-{i}.",
            "confidence_delta": 0.10,
            "evidence_score": 0.90,
            "source_episode_ids": [f"e{i}a", f"e{i}b"],
            "pattern_statement": f"pattern-{i}",
        })

    event = {"_macro_scored_reflections": reflections}
    pending: list = []
    update_self_beliefs(state, event, pending)

    # Config says max_new_statements_per_cycle = 3; only 3 new beliefs should be created
    new_beliefs = [b for b in state.self_model.beliefs if b.source_type == "REFLECTION"]
    assert len(new_beliefs) == 3
