from __future__ import annotations

from src.engine.cycles.macro import (
    archive_reflection,
    cluster_episodes,
    compact_episodic_memory,
    decay_unreinforced_beliefs,
    drive_review,
    goal_review,
    produce_candidate_reflections,
    score_evidence_sufficiency,
    select_high_signal_episodes,
    update_self_beliefs,
)
from src.schema.state import AgentState, GoalRecord, SelfBelief
from src.store.episodic_store import EpisodicStore


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
        reflections.append(
            {
                "reflection_id": f"r{i}",
                "proposed_self_belief_update": f"I engage with topic-{i}.",
                "confidence_delta": 0.10,
                "evidence_score": 0.90,
                "source_episode_ids": [f"e{i}a", f"e{i}b"],
                "pattern_statement": f"pattern-{i}",
            }
        )

    event = {"_macro_scored_reflections": reflections}
    pending: list = []
    update_self_beliefs(state, event, pending)

    # Config says max_new_statements_per_cycle = 3; only 3 new beliefs should be created
    new_beliefs = [b for b in state.self_model.beliefs if b.source_type == "REFLECTION"]
    assert len(new_beliefs) == 3


# ── CP-4.1: Confidence decay tests ──────────────────────────────────────────


def test_decay_unreinforced_beliefs_reduces_confidence() -> None:
    """Beliefs unreinforced beyond threshold_days should decay."""
    belief = SelfBelief(
        id="b1",
        statement="I enjoy reading.",
        confidence=0.60,
        source_type="REFLECTION",
        supporting_reflections=["refl-000001-001"],  # tick 1
    )
    state = AgentState(
        self_model={"beliefs": [belief.model_dump()]},
        tick_counter=20,  # 20 days since tick 1 > 14-day threshold
    )

    decay_unreinforced_beliefs(state, {"_macro_accepted_reflections": []}, pending := [])

    assert state.self_model.beliefs[0].confidence < 0.60
    assert state.self_model.beliefs[0].confidence == round(0.60 - 0.02, 4)
    assert any(w["field_path"] == "self_model.beliefs" for w in pending)


def test_decay_skips_const_seed_beliefs() -> None:
    """CONST_SEED beliefs should never decay."""
    belief = SelfBelief(
        id="const-seed-001",
        statement="I value honesty.",
        confidence=0.55,
        source_type="CONST_SEED",
    )
    state = AgentState(
        self_model={"beliefs": [belief.model_dump()]},
        tick_counter=100,  # Very old
    )

    decay_unreinforced_beliefs(state, {"_macro_accepted_reflections": []}, pending := [])

    assert state.self_model.beliefs[0].confidence == 0.55
    assert not any(w["field_path"] == "self_model.beliefs" for w in pending)


def test_decay_skips_recently_reinforced_beliefs() -> None:
    """Beliefs reinforced this cycle should not decay."""
    belief = SelfBelief(
        id="b1",
        statement="I enjoy reading.",
        confidence=0.60,
        source_type="REFLECTION",
        supporting_reflections=["refl-000001-001"],  # old
    )
    state = AgentState(
        self_model={"beliefs": [belief.model_dump()]},
        tick_counter=100,
    )
    event = {"_macro_accepted_reflections": [{"proposed_self_belief_update": "I enjoy reading."}]}

    decay_unreinforced_beliefs(state, event, [])

    assert state.self_model.beliefs[0].confidence == 0.60  # unchanged


def test_decay_tracks_archival_candidates() -> None:
    """Beliefs below archival threshold should appear in archival candidates."""
    belief = SelfBelief(
        id="b1",
        statement="I enjoy coding.",
        confidence=0.10,  # Below 0.15 archival threshold
        source_type="REFLECTION",
        supporting_reflections=["refl-000001-001"],
    )
    state = AgentState(
        self_model={"beliefs": [belief.model_dump()]},
        tick_counter=50,
    )

    event: dict = {"_macro_accepted_reflections": []}
    decay_unreinforced_beliefs(state, event, [])

    assert "b1" in event["_macro_archival_candidates"]


# ── CP-4.2: Recency window filter tests ─────────────────────────────────────


def test_recency_window_filters_old_episodes() -> None:
    """Episodes outside the recency window should be excluded."""
    state = AgentState()
    event = {
        "_macro_top_k": 10,
        "_macro_recency_window_hours": 24,
        "_macro_source_episodes": [
            _episode("e1", 0.9, created_at="2026-01-03T12:00:00Z"),  # recent
            _episode("e2", 0.8, created_at="2026-01-03T00:00:00Z"),  # recent
            _episode("e3", 0.95, created_at="2026-01-01T00:00:00Z"),  # old (>24h)
        ],
    }

    select_high_signal_episodes(state, event, [])

    selected_ids = [r["id"] for r in event["_macro_selected_episodes"]]
    assert "e3" not in selected_ids
    assert "e1" in selected_ids
    assert "e2" in selected_ids


def test_recency_window_keeps_all_when_within_range() -> None:
    """All episodes within the window should be kept."""
    state = AgentState()
    event = {
        "_macro_top_k": 10,
        "_macro_recency_window_hours": 72,
        "_macro_source_episodes": [
            _episode("e1", 0.5, created_at="2026-01-03T12:00:00Z"),
            _episode("e2", 0.5, created_at="2026-01-02T12:00:00Z"),
            _episode("e3", 0.5, created_at="2026-01-01T12:00:00Z"),
        ],
    }

    select_high_signal_episodes(state, event, [])

    assert len(event["_macro_selected_episodes"]) == 3


# ── CP-4.3: Goal review lifecycle tests ──────────────────────────────────────


def test_goal_review_suspends_high_frustration_goals() -> None:
    """Goals at frustration >= 0.75 should be suspended."""
    from datetime import datetime, timezone

    goal = GoalRecord(
        id="g1",
        label="Learn Rust",
        status="active",
        frustration=0.80,
        created_at=datetime.now(timezone.utc).isoformat(),  # Recent — not stale
    )
    state = AgentState(goals=[goal])

    event: dict = {"_macro_accepted_reflections": []}
    pending: list = []
    goal_review(state, event, pending)

    assert state.goals[0].status == "suspended"
    assert "g1" in event["_macro_goal_review"]["suspended_goal_ids"]
    assert any(w["field_path"] == "goals" for w in pending)


def test_goal_review_abandons_stale_goals() -> None:
    """Goals with no progress after staleness_days should be abandoned."""
    goal = GoalRecord(
        id="g1",
        label="Old goal",
        status="active",
        progress=0.0,
        created_at="2025-01-01T00:00:00Z",  # Very old
    )
    state = AgentState(goals=[goal])

    event: dict = {"_macro_accepted_reflections": []}
    pending: list = []
    goal_review(state, event, pending)

    assert state.goals[0].status == "abandoned"
    assert "g1" in event["_macro_goal_review"]["abandoned_goal_ids"]


# ── CP-4.5: Macro-cycle determinism replay test ─────────────────────────────


def test_macro_pipeline_determinism() -> None:
    """Running the full pipeline twice with identical inputs should produce identical outputs."""
    episodes = [
        _episode("e1", 0.9, goal="g1", created_at="2026-01-01T00:00:00Z"),
        _episode("e2", 0.85, goal="g1", created_at="2026-01-01T03:00:00Z"),
        _episode("e3", 0.8, goal="g1", created_at="2026-01-02T01:00:00Z"),
    ]

    results = []
    for _ in range(2):
        state = AgentState(tick_counter=5)
        event = {"_macro_source_episodes": list(episodes)}
        pending: list = []

        select_high_signal_episodes(state, event, pending)
        cluster_episodes(state, event, pending)
        produce_candidate_reflections(state, event, pending)
        score_evidence_sufficiency(state, event, pending)
        update_self_beliefs(state, event, pending)
        decay_unreinforced_beliefs(state, event, pending)

        results.append(
            {
                "beliefs": [(b.statement, b.confidence) for b in state.self_model.beliefs],
                "reflections": [
                    r["reflection_id"] for r in event.get("_macro_accepted_reflections", [])
                ],
                "clusters": len(event.get("_macro_clusters", [])),
            }
        )

    assert results[0] == results[1]


def test_compact_episodic_memory_no_store_is_noop() -> None:
    state = AgentState()
    event: dict = {}

    compact_episodic_memory(state, event, [])

    assert event["_macro_memory_compaction"]["enabled"] is False


def test_compact_episodic_memory_runs_cool_and_archive() -> None:
    from tempfile import TemporaryDirectory
    from pathlib import Path

    with TemporaryDirectory() as tmp:
        store = EpisodicStore(Path(tmp) / "macro.db")
        from src.schema.records import EpisodicEvent, RecordMeta

        record = EpisodicEvent(
            meta=RecordMeta(
                id="e1",
                created_at="2026-01-01T00:00:00Z",
                source_type="synthetic",
                lifecycle_state="active",
            ),
            when="2026-01-01T00:00:00Z",
            event_text="event e1",
            importance=0.05,
        )
        store.append(record, "c1", "Orchestrator")
        store.update_decay_factor("e1", 0.05)

        event = {"_store": store}
        compact_episodic_memory(AgentState(), event, [])

        summary = event["_macro_memory_compaction"]
        assert summary["enabled"] is True
        assert "e1" in summary["cooled_ids"]
        assert "e1" in summary["archived_ids"]
        assert store.count("archived") == 1
