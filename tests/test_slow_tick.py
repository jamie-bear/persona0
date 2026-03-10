"""
Unit tests for Phase 3 slow-tick pipeline steps and CP-3 exit gates.

Tests are organized around:
1. Desire lifecycle (generation, persistence, expiry, crystallization)
2. Slow tick steps (activity_transition, routine_event, desire_generation)
3. CP-3 exit gates (72-hour bounds, desire isolation from episodic store)

Reference: Phase 3 plan — Part D (tests/test_slow_tick.py), CP-3 exit gates
"""

from __future__ import annotations

from src.schema.state import AgentState, AffectState, DriveState, GoalRecord
from src.engine.modules.drive import DriveModule
from src.engine.cycles.slow_tick import (
    activity_transition,
    routine_event,
    desire_generation,
    _select_activity,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _state(**kwargs) -> AgentState:
    state = AgentState()
    for k, v in kwargs.items():
        setattr(state, k, v)
    return state


def _event(**kwargs) -> dict:
    return {"_cycle_id": "test-cycle", **kwargs}


def _desire(drive="social_need", urgency=0.80, age=0, expires=3) -> dict:
    return {
        "id": f"d-{drive}-{age}",
        "source_drive": drive,
        "urgency": urgency,
        "approach": True,
        "expires_after_ticks": expires,
        "age_in_ticks": age,
        "created_at_tick": 0,
        "content": f"want to address {drive}",
    }


# ── Desire generation ─────────────────────────────────────────────────────────


class TestDesireGeneration:
    module = DriveModule()

    def test_desires_generated_above_threshold(self):
        """Drive value ≥ impulse_threshold produces a desire."""
        # social_need threshold = 0.65
        drives = DriveState(social_need=0.80, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        state = _state(drives=drives)
        event = _event()
        pending = []
        desire_generation(state, event, pending)
        assert len(state.active_desires) >= 1
        drive_names = [d["source_drive"] for d in state.active_desires]
        assert "social_need" in drive_names

    def test_desires_not_generated_below_threshold(self):
        """Drive value below impulse_threshold produces no desire for that drive."""
        drives = DriveState(social_need=0.40, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        state = _state(drives=drives)
        event = _event()
        desire_generation(state, event, [])
        drive_names = [d["source_drive"] for d in state.active_desires]
        assert "social_need" not in drive_names

    def test_desire_urgency_equals_drive_value(self):
        """Generated desire urgency matches the drive value at generation."""
        drives = DriveState(social_need=0.77, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        state = _state(drives=drives)
        desire_generation(state, _event(), [])
        social_desires = [d for d in state.active_desires if d["source_drive"] == "social_need"]
        assert len(social_desires) == 1
        assert social_desires[0]["urgency"] == round(0.77, 4)

    def test_desire_approach_for_high_drive(self):
        """Generated desires always start as approach=True."""
        drives = DriveState(social_need=0.80, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        state = _state(drives=drives)
        desire_generation(state, _event(), [])
        for d in state.active_desires:
            assert d["approach"] is True

    def test_desire_expires_correctly(self):
        """Desire with age == expires_after_ticks - 1 is removed after aging."""
        # age=2, expires=3 → aged to 3 → 3 is NOT < 3 → removed
        old_desire = _desire(drive="social_need", urgency=0.80, age=2, expires=3)
        state = _state(persisted_desires=[old_desire])
        desire_generation(state, _event(), [])
        # The aged desire should be expired and not in persisted_desires
        # If social_need is below threshold, no new desire generated to replace it
        # The old one (aged to 3) should be gone
        old_persisted = [d for d in state.persisted_desires if d.get("age_in_ticks", 0) >= 3]
        assert len(old_persisted) == 0

    def test_persisted_desires_carry_between_ticks(self):
        """High-urgency new desire persists to state.persisted_desires."""
        drives = DriveState(social_need=0.80, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        state = _state(drives=drives)
        desire_generation(state, _event(), [])
        # social_need=0.80 >= persistence_threshold=0.50 → should persist
        drive_names = [d["source_drive"] for d in state.persisted_desires]
        assert "social_need" in drive_names


# ── Crystallization ───────────────────────────────────────────────────────────


class TestCrystallization:
    module = DriveModule()

    def test_crystallization_proposes_goal(self):
        """Aged desire with urgency ≥ urgency_min produces a GoalProposal."""
        # crystallization_threshold_ticks = 6, urgency_min = 0.65
        aged_desire = _desire(drive="social_need", urgency=0.80, age=6, expires=10)
        proposals = self.module.check_crystallization([aged_desire], [])
        assert len(proposals) == 1
        assert proposals[0]["crystallized_from_drive"] == "social_need"
        assert proposals[0]["priority"] == round(0.80 * 0.60, 4)  # dampen = 0.60

    def test_crystallization_requires_min_age(self):
        """Desire below crystallization_threshold_ticks does not crystallize."""
        young_desire = _desire(drive="social_need", urgency=0.80, age=3, expires=10)
        proposals = self.module.check_crystallization([young_desire], [])
        assert len(proposals) == 0

    def test_crystallization_requires_min_urgency(self):
        """Desire below crystallization_urgency_min does not crystallize."""
        low_urgency = _desire(drive="social_need", urgency=0.50, age=6, expires=10)
        proposals = self.module.check_crystallization([low_urgency], [])
        assert len(proposals) == 0

    def test_crystallization_respects_rate_limit(self):
        """At most 1 proposal per drive per call to check_crystallization."""
        desires = [
            _desire(drive="social_need", urgency=0.80, age=6, expires=10),
            _desire(drive="social_need", urgency=0.85, age=7, expires=10),
        ]
        desires[1]["id"] = "d2"
        proposals = self.module.check_crystallization(desires, [])
        social_proposals = [p for p in proposals if p["crystallized_from_drive"] == "social_need"]
        assert len(social_proposals) == 1

    def test_crystallization_skipped_with_existing_active_goal(self):
        """No proposal if an active goal already satisfies the same drive."""
        aged_desire = _desire(drive="social_need", urgency=0.80, age=6, expires=10)
        existing_goal = GoalRecord(
            id="g1",
            label="existing",
            status="active",
            crystallized_from_drive="social_need",
        )
        proposals = self.module.check_crystallization([aged_desire], [existing_goal])
        assert len(proposals) == 0

    def test_crystallization_not_blocked_by_suspended_goal(self):
        """A suspended goal does not block crystallization for the same drive."""
        aged_desire = _desire(drive="social_need", urgency=0.80, age=6, expires=10)
        suspended_goal = GoalRecord(
            id="g1",
            label="suspended",
            status="suspended",
            crystallized_from_drive="social_need",
        )
        proposals = self.module.check_crystallization([aged_desire], [suspended_goal])
        assert len(proposals) == 1

    def test_desire_generation_accepts_proposal_into_goals(self):
        """desire_generation integrates crystallized desire as a new GoalRecord."""
        # Seed a persisted desire old enough to crystallize
        old_desire = _desire(drive="social_need", urgency=0.80, age=5, expires=20)
        # age=5 → after aging → age=6 = threshold
        state = _state(persisted_desires=[old_desire])
        event = _event()
        desire_generation(state, event, [])
        # Should have a new goal for social_need
        social_goals = [g for g in state.goals if g.crystallized_from_drive == "social_need"]
        assert len(social_goals) == 1
        assert social_goals[0].status == "active"


# ── Activity transition ───────────────────────────────────────────────────────


class TestActivityTransition:
    def test_low_energy_gives_rest(self):
        """energy < 0.20 → activity = 'rest'."""
        state = _state(affect=AffectState(valence=0.1, arousal=0.3, stress=0.1, energy=0.10))
        event = _event()
        activity_transition(state, event, [])
        assert state.activity.current_activity == "rest"

    def test_medium_energy_gives_reading(self):
        """0.40 <= energy < 0.70 → activity = 'reading'."""
        state = _state(affect=AffectState(valence=0.1, arousal=0.3, stress=0.1, energy=0.55))
        event = _event()
        activity_transition(state, event, [])
        assert state.activity.current_activity == "reading"

    def test_high_energy_gives_task_completion(self):
        """energy >= 0.70 → activity = 'task_completion'."""
        state = _state(affect=AffectState(valence=0.1, arousal=0.3, stress=0.1, energy=0.85))
        event = _event()
        activity_transition(state, event, [])
        assert state.activity.current_activity == "task_completion"

    def test_activity_written_to_pending(self):
        """activity_transition appends activity.current_activity to pending_writes."""
        state = _state(affect=AffectState(valence=0.1, arousal=0.3, stress=0.1, energy=0.80))
        event = _event()
        pending = []
        activity_transition(state, event, pending)
        paths = [w["field_path"] for w in pending]
        assert "activity.current_activity" in paths

    def test_activity_selector_boundaries(self):
        """_select_activity returns correct category for each energy boundary."""
        assert _select_activity(0.10) == "rest"
        assert _select_activity(0.20) == "low_arousal_idle_period"  # 0.20 is NOT < 0.20
        assert _select_activity(0.35) == "low_arousal_idle_period"
        assert _select_activity(0.50) == "reading"
        assert _select_activity(0.70) == "task_completion"
        assert _select_activity(0.99) == "task_completion"


# ── Routine event ─────────────────────────────────────────────────────────────


class TestRoutineEvent:
    def test_routine_event_added_to_pending_episodic(self):
        """routine_event appends one record to event['_pending_episodic']."""
        state = _state()
        state.activity.current_activity = "reading"
        event = _event()
        routine_event(state, event, [])
        assert "_pending_episodic" in event
        assert len(event["_pending_episodic"]) == 1

    def test_routine_event_has_correct_activity(self):
        """Routine event record includes the current activity."""
        state = _state()
        state.activity.current_activity = "rest"
        event = _event()
        routine_event(state, event, [])
        record = event["_pending_episodic"][0]
        assert record["activity"] == "rest"
        assert record["record_type"] == "routine_event"

    def test_routine_event_text_matches_template(self):
        """Routine event text comes from _ROUTINE_TEMPLATES."""
        state = _state()
        state.activity.current_activity = "reading"
        event = _event()
        routine_event(state, event, [])
        record = event["_pending_episodic"][0]
        assert (
            "curiosity" in record["event_text"].lower() or "reading" in record["event_text"].lower()
        )

    def test_routine_event_writes_episodic_log(self):
        """routine_event appends 'episodic_log' to pending_writes."""
        state = _state()
        event = _event()
        pending = []
        routine_event(state, event, pending)
        paths = [w["field_path"] for w in pending]
        assert "episodic_log" in paths


# ── Desire objects NOT in episodic store (CP-3 exit gate) ────────────────────


class TestDesireNotInEpisodicStore:
    def test_desire_objects_not_in_pending_episodic(self):
        """After desire_generation, _pending_episodic contains no desire-typed records."""
        drives = DriveState(social_need=0.80, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        state = _state(drives=drives)
        event = _event()
        desire_generation(state, event, [])
        # Any records stored should not be desire objects
        for record in event.get("_pending_episodic", []):
            assert record.get("record_type") != "desire"
            assert record.get("source_drive") is None or record.get("record_type") == "thought"


# ── CP-3 Exit Gate: 72-hour drive bounds ─────────────────────────────────────


class TestCP3ExitGates:
    def test_72h_drive_bounds(self):
        """After 144 fast ticks (~72 hours), all drives stay in [0.0, 1.0].

        CP-3 exit gate: drive bounds invariant under extended simulation.
        No satisfaction events applied (worst case: maximum growth).
        """
        module = DriveModule()
        drives = DriveState(social_need=0.20, mastery_need=0.15, rest_need=0.10, curiosity=0.30)
        for _ in range(144):  # 144 ticks × 30 min = 72 hours
            drives = module.update(drives, activity_events=[])
            assert 0.0 <= drives.social_need <= 1.0, "social_need out of bounds"
            assert 0.0 <= drives.mastery_need <= 1.0, "mastery_need out of bounds"
            assert 0.0 <= drives.rest_need <= 1.0, "rest_need out of bounds"
            assert 0.0 <= drives.curiosity <= 1.0, "curiosity out of bounds"

    def test_drives_satisfied_by_activity_in_pipeline(self):
        """Full slow tick with conversation event reduces social_need."""
        drives = DriveState(social_need=0.80, mastery_need=0.15, rest_need=0.10, curiosity=0.30)
        from src.engine.modules.drive import DriveModule as DM

        module = DM()
        # Apply one update with conversation event
        new_drives = module.update(drives, [{"type": "conversation"}])
        assert new_drives.social_need < drives.social_need

    def test_all_drives_bounded_with_satisfaction(self):
        """All drives stay in [0.0, 1.0] even with constant satisfaction events."""
        module = DriveModule()
        drives = DriveState(social_need=0.20, mastery_need=0.15, rest_need=0.10, curiosity=0.30)
        events = [
            {"type": "conversation"},
            {"type": "task_completion"},
            {"type": "sleep"},
            {"type": "reading"},
        ]
        for _ in range(144):
            drives = module.update(drives, activity_events=events)
            assert 0.0 <= drives.social_need <= 1.0
            assert 0.0 <= drives.mastery_need <= 1.0
            assert 0.0 <= drives.rest_need <= 1.0
            assert 0.0 <= drives.curiosity <= 1.0
