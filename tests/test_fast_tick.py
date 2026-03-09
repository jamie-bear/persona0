"""
Unit tests for Phase 3 fast-tick cognitive modules.

Covers: EmotionModule, DriveModule, ThoughtGenerator, GoalSystem.
All tests are isolated from the orchestrator.

Reference: Phase 3 plan — Part D (tests/test_fast_tick.py)
"""
from __future__ import annotations

import pytest
from src.schema.state import AffectState, DriveState, AgentState, GoalRecord
from src.engine.modules.emotion import EmotionModule
from src.engine.modules.drive import DriveModule
from src.engine.modules.thought import ThoughtGenerator, CATEGORIES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_drives(**kwargs) -> DriveState:
    defaults = dict(social_need=0.20, mastery_need=0.15, rest_need=0.10, curiosity=0.30)
    defaults.update(kwargs)
    return DriveState(**defaults)


def _make_affect(**kwargs) -> AffectState:
    defaults = dict(valence=0.10, arousal=0.30, stress=0.10, energy=0.70)
    defaults.update(kwargs)
    return AffectState(**defaults)


def _make_goal(status="active", blocked_by=None, frustration=0.0,
               progress=0.0, drive=None) -> GoalRecord:
    return GoalRecord(
        id="g1",
        label="Test goal",
        motive=drive or "mastery_need",
        status=status,
        frustration=frustration,
        progress=progress,
        blocked_by=blocked_by or [],
        crystallized_from_drive=drive,
    )


# ── EmotionModule ─────────────────────────────────────────────────────────────

class TestEmotionModule:
    module = EmotionModule()

    def test_emotion_decays_toward_baseline(self):
        """After 20 ticks with no appraisals, all variables approach baseline."""
        affect = AffectState(valence=-0.8, arousal=0.9, stress=0.9, energy=0.0)
        baseline = dict(valence=0.10, arousal=0.30, stress=0.10, energy=0.70)
        for tick in range(20):
            affect = self.module.update(affect, [], tick_counter=tick)
        assert affect.valence > -0.8, "valence should move toward baseline"
        assert affect.arousal < 0.9, "arousal should decay toward baseline"
        assert affect.stress < 0.9, "stress should decay toward baseline"
        assert affect.energy > 0.0, "energy should decay toward baseline"

    def test_affect_clamped_at_upper_bound(self):
        """Appraisal-driven deltas cannot push affect above 1.0."""
        affect = _make_affect(valence=0.95, stress=0.95)
        big_appraisal = [{"goal_congruence": 5.0, "threat": 5.0, "arousal_cue": 5.0}]
        result = self.module.update(affect, big_appraisal, tick_counter=0)
        assert result.valence <= 1.0
        assert result.stress <= 1.0
        assert result.arousal <= 1.0
        assert result.energy <= 1.0

    def test_affect_clamped_at_lower_bound(self):
        """Negative appraisals cannot push affect below -1.0."""
        affect = _make_affect(valence=-0.95, arousal=-0.95)
        big_negative = [{"goal_congruence": -5.0, "threat": 0.0, "arousal_cue": -5.0}]
        result = self.module.update(affect, big_negative, tick_counter=0)
        assert result.valence >= -1.0
        assert result.arousal >= -1.0

    def test_circadian_energy_varies_over_day(self):
        """Energy at tick 0 and tick 24 differ due to circadian cosine wave."""
        affect_base = _make_affect(energy=0.70)
        # Run one tick at different times of day
        result_tick0 = self.module.update(affect_base, [], tick_counter=0)
        result_tick24 = self.module.update(affect_base, [], tick_counter=24)
        # Circadian amplitude is 0.15; the two ticks should not be identical
        assert abs(result_tick0.energy - result_tick24.energy) > 1e-6

    def test_appraisal_goal_congruence_raises_valence(self):
        """Positive goal_congruence increases valence."""
        affect = _make_affect(valence=0.0)
        result = self.module.update(affect, [{"goal_congruence": 1.0}], tick_counter=0)
        assert result.valence > affect.valence + 0.05  # EMA decay is small, net should be positive

    def test_appraisal_threat_raises_stress(self):
        """Positive threat increases stress."""
        affect = _make_affect(stress=0.0)
        result = self.module.update(affect, [{"threat": 1.0}], tick_counter=0)
        assert result.stress > 0.0

    def test_stress_rest_boost_above_threshold(self):
        """stress_rest_boost returns positive value when stress exceeds threshold."""
        boost = self.module.stress_rest_boost(stress=0.80)
        assert boost > 0.0

    def test_stress_rest_boost_below_threshold(self):
        """stress_rest_boost returns 0.0 when stress is below threshold."""
        boost = self.module.stress_rest_boost(stress=0.50)
        assert boost == 0.0


# ── DriveModule ───────────────────────────────────────────────────────────────

class TestDriveModule:
    module = DriveModule()

    def test_drives_grow_per_tick(self):
        """Each drive increases by at least its growth_rate after one tick."""
        drives = DriveState(social_need=0.10, mastery_need=0.10, rest_need=0.10, curiosity=0.10)
        updated = self.module.update(drives, activity_events=[])
        assert updated.social_need > 0.10
        assert updated.mastery_need > 0.10
        assert updated.rest_need > 0.10
        assert updated.curiosity > 0.10

    def test_drives_clamped_at_1_0(self):
        """No drive exceeds 1.0 even after 100 ticks with no satisfaction."""
        drives = DriveState(social_need=0.90, mastery_need=0.90, rest_need=0.90, curiosity=0.90)
        for _ in range(100):
            drives = self.module.update(drives, activity_events=[])
        assert drives.social_need <= 1.0
        assert drives.mastery_need <= 1.0
        assert drives.rest_need <= 1.0
        assert drives.curiosity <= 1.0

    def test_drives_clamped_at_0_0(self):
        """Satisfaction on an already-zero drive keeps it at 0.0 (not negative)."""
        drives = DriveState(social_need=0.0, mastery_need=0.0, rest_need=0.0, curiosity=0.0)
        # Apply satisfaction events for all drives
        events = [
            {"type": "conversation"},
            {"type": "task_completion"},
            {"type": "sleep"},
            {"type": "reading"},
        ]
        updated = self.module.update(drives, activity_events=events)
        assert updated.social_need >= 0.0
        assert updated.mastery_need >= 0.0
        assert updated.rest_need >= 0.0
        assert updated.curiosity >= 0.0

    def test_satisfaction_reduces_social_need(self):
        """A 'conversation' event reduces social_need by reduction_per_event."""
        drives = _make_drives(social_need=0.80)
        updated = self.module.update(drives, activity_events=[{"type": "conversation"}])
        assert updated.social_need < drives.social_need

    def test_satisfaction_map_correct_per_drive(self):
        """One event per drive type causes the correct drive to reduce."""
        drives = _make_drives(social_need=0.80, mastery_need=0.80,
                               rest_need=0.80, curiosity=0.80)
        # conversation → social_need
        d1 = self.module.update(drives, [{"type": "conversation"}])
        assert d1.social_need < drives.social_need

        # task_completion → mastery_need
        d2 = self.module.update(drives, [{"type": "task_completion"}])
        assert d2.mastery_need < drives.mastery_need

        # sleep → rest_need
        d3 = self.module.update(drives, [{"type": "sleep"}])
        assert d3.rest_need < drives.rest_need

        # reading → curiosity
        d4 = self.module.update(drives, [{"type": "reading"}])
        assert d4.curiosity < drives.curiosity

    def test_no_satisfaction_for_unmapped_event(self):
        """An unmapped event type does not reduce any drive (only growth applies)."""
        drives = _make_drives(social_need=0.50)
        updated = self.module.update(drives, activity_events=[{"type": "unmapped_activity_xyz"}])
        # social_need should have grown (not decreased) since the event is unmapped
        assert updated.social_need >= drives.social_need

    def test_desire_generated_above_threshold(self):
        """generate_desire returns a dict when drive_value >= impulse_threshold."""
        # social_need threshold = 0.65
        desire = self.module.generate_desire("social_need", 0.80, tick_counter=1)
        assert desire is not None
        assert desire["source_drive"] == "social_need"
        assert desire["urgency"] == round(0.80, 4)

    def test_desire_not_generated_below_threshold(self):
        """generate_desire returns None when drive_value < impulse_threshold."""
        desire = self.module.generate_desire("social_need", 0.40, tick_counter=1)
        assert desire is None

    def test_desire_urgency_equals_drive_value(self):
        """Desire urgency is exactly the drive value (rounded to 4dp)."""
        desire = self.module.generate_desire("mastery_need", 0.777, tick_counter=5)
        assert desire is not None
        assert desire["urgency"] == round(0.777, 4)

    def test_desire_approach_flag(self):
        """All generated desires have approach=True (simplified model)."""
        desire = self.module.generate_desire("curiosity", 0.85, tick_counter=0)
        assert desire is not None
        assert desire["approach"] is True

    def test_age_and_expire_removes_expired(self):
        """age_and_expire removes desires whose age equals or exceeds expires_after_ticks."""
        desires = [
            {"id": "d1", "age_in_ticks": 2, "expires_after_ticks": 3},  # will survive
            {"id": "d2", "age_in_ticks": 2, "expires_after_ticks": 3},  # becomes age=3, removed
        ]
        # After aging: age becomes 3; 3 is NOT < expires_after_ticks (3) → both removed
        result = DriveModule.age_and_expire_desires(desires)
        assert len(result) == 0

    def test_age_and_expire_keeps_young_desire(self):
        """age_and_expire keeps desires that have not yet expired."""
        desires = [{"id": "d1", "age_in_ticks": 0, "expires_after_ticks": 3}]
        result = DriveModule.age_and_expire_desires(desires)
        assert len(result) == 1
        assert result[0]["age_in_ticks"] == 1

    def test_persist_new_desires_filters_by_urgency(self):
        """persist_new_desires only includes desires at or above persistence_threshold (0.50)."""
        active = [
            {"id": "d1", "source_drive": "social_need", "urgency": 0.80},
            {"id": "d2", "source_drive": "mastery_need", "urgency": 0.40},
        ]
        result = DriveModule.persist_new_desires(active, [])
        drive_names = [d["source_drive"] for d in result]
        assert "social_need" in drive_names
        assert "mastery_need" not in drive_names


# ── ThoughtGenerator ──────────────────────────────────────────────────────────

class TestThoughtGenerator:
    gen = ThoughtGenerator()

    def _make_state(self, **kwargs) -> AgentState:
        state = AgentState()
        for k, v in kwargs.items():
            setattr(state, k, v)
        return state

    def test_thought_category_from_desire(self):
        """Social desire maps to 'social' category."""
        affect = _make_affect()
        drives = _make_drives(social_need=0.30)
        desires = [{"source_drive": "social_need", "approach": True}]
        cat = self.gen.select_category(affect, drives, desires, [])
        assert cat == "social"

    def test_thought_category_from_mastery_desire(self):
        """Mastery approach desire maps to 'planning' category."""
        affect = _make_affect()
        drives = _make_drives(mastery_need=0.30)
        desires = [{"source_drive": "mastery_need", "approach": True}]
        cat = self.gen.select_category(affect, drives, desires, [])
        assert cat == "planning"

    def test_thought_category_guardrail(self):
        """After 3 identical categories, the 4th call returns a different category."""
        affect = _make_affect()
        drives = _make_drives(social_need=0.30)
        desires = [{"source_drive": "social_need", "approach": True}]
        # First 3: "social"
        recent = ["social", "social", "social"]
        cat = self.gen.select_category(affect, drives, desires, recent)
        assert cat != "social", "guardrail should override 4th consecutive 'social'"

    def test_thought_has_required_fields(self):
        """Generated thought has all required fields."""
        state = AgentState()
        thought = self.gen.generate(state, [], tick_counter=0)
        assert "id" in thought
        assert "text" in thought
        assert "thought_category" in thought
        assert "trigger" in thought
        assert "intrusiveness" in thought
        assert "meta" in thought

    def test_thought_category_in_known_categories(self):
        """Generated thought category is always in the known category list."""
        state = AgentState()
        for tick in range(10):
            state.consecutive_thought_categories = []
            thought = self.gen.generate(state, [], tick_counter=tick)
            assert thought["thought_category"] in CATEGORIES

    def test_thought_desire_trigger_tagged(self):
        """When desire drives category, trigger='desire' and source_desire_drive is set."""
        state = AgentState()
        desires = [{"source_drive": "social_need", "approach": True, "urgency": 0.80}]
        thought = self.gen.generate(state, desires, tick_counter=0)
        if thought["thought_category"] == "social":
            assert thought["trigger"] == "desire"
            assert thought["source_desire_drive"] == "social_need"

    def test_internal_trigger_without_desire(self):
        """Thought without desire trigger has trigger='internal'."""
        state = AgentState()
        thought = self.gen.generate(state, [], tick_counter=0)
        # With no desires, baseline rules → trigger should be internal
        assert thought["trigger"] == "internal"

    def test_thought_low_valence_selects_rumination(self):
        """Low valence (< -0.3) selects rumination or self-evaluation category."""
        affect = _make_affect(valence=-0.5)
        drives = _make_drives(mastery_need=0.20)  # below 0.4 → rumination
        cat = self.gen.select_category(affect, drives, [], [])
        assert cat in ("rumination", "self-evaluation")

    def test_thought_high_arousal_selects_planning_or_curiosity(self):
        """High arousal (> 0.6) selects planning or curiosity."""
        affect = _make_affect(arousal=0.7, valence=0.5)  # valence positive, no desire
        drives = _make_drives()
        cat = self.gen.select_category(affect, drives, [], [])
        assert cat in ("planning", "curiosity")


# ── GoalSystem ────────────────────────────────────────────────────────────────

class TestGoalSystem:
    from src.engine.modules.goal import GoalSystem
    system = GoalSystem()

    def test_goal_progress_ticks_when_not_blocked(self):
        """Active goal with no blockers gains +0.01 progress per tick."""
        goal = _make_goal(status="active", blocked_by=[], progress=0.0)
        updated = self.system.tick_goals([goal])
        assert updated[0].progress == pytest.approx(0.01, abs=1e-4)

    def test_goal_frustration_accumulates_when_stalled(self):
        """Active goal with blockers gains frustration each tick."""
        goal = _make_goal(status="active", blocked_by=["blocker1"], frustration=0.0)
        updated = self.system.tick_goals([goal])
        assert updated[0].frustration > 0.0

    def test_goal_suspends_at_threshold(self):
        """Goal transitions to 'suspended' when frustration >= 0.75."""
        goal = _make_goal(status="active", blocked_by=["b"], frustration=0.70)
        # 0.70 + 0.05 = 0.75 = threshold → suspended
        updated = self.system.tick_goals([goal])
        assert updated[0].status == "suspended"

    def test_goal_frustration_decays_when_progressing(self):
        """Active goal without blockers reduces frustration each tick."""
        goal = _make_goal(status="active", blocked_by=[], frustration=0.50)
        updated = self.system.tick_goals([goal])
        assert updated[0].frustration < 0.50

    def test_inactive_goals_not_modified(self):
        """Suspended and completed goals are not modified by tick_goals."""
        suspended = _make_goal(status="suspended", frustration=0.50)
        completed = _make_goal(status="completed")
        updated = self.system.tick_goals([suspended, completed])
        assert updated[0].frustration == 0.50
        assert updated[1].status == "completed"

    def test_accept_proposal_creates_goal(self):
        """Valid proposal with no conflicts creates a new GoalRecord."""
        proposal = {
            "label": "Test goal",
            "motive": "social_need",
            "priority": 0.60,
            "horizon": "short",
            "crystallized_from_drive": "social_need",
            "crystallized_at": "2024-01-01T00:00:00+00:00",
        }
        result = self.system.accept_proposal(proposal, [])
        assert result is not None
        assert result.label == "Test goal"
        assert result.status == "active"
        assert result.crystallized_from_drive == "social_need"

    def test_accept_proposal_rejected_when_drive_already_has_goal(self):
        """Proposal rejected if an active goal for the same drive exists."""
        existing = GoalRecord(
            id="g1", label="existing", status="active",
            crystallized_from_drive="social_need",
        )
        proposal = {"crystallized_from_drive": "social_need", "label": "new"}
        result = self.system.accept_proposal(proposal, [existing])
        assert result is None

    def test_accept_proposal_rejected_at_max_goals(self):
        """Proposal rejected when active goal count equals max_active_goals."""
        active_goals = [
            GoalRecord(id=f"g{i}", label=f"g{i}", status="active",
                       crystallized_from_drive=f"drive_{i}")
            for i in range(8)
        ]
        proposal = {"crystallized_from_drive": "new_drive", "label": "new"}
        result = self.system.accept_proposal(proposal, active_goals)
        assert result is None
