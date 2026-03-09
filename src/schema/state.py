"""
Agent state schema — the complete runtime state of the Ego Engine.

Reference: architecture.md §3 (canonical state schema), self_editability_policy.md §3
"""
from __future__ import annotations

from typing import Annotated, List, Optional
from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Sub-schemas
# ─────────────────────────────────────────────────────────────────────────────

class AffectState(BaseModel):
    """Emotional affect variables. Mutability: SELF / EmotionModule."""

    valence: Annotated[float, Field(ge=-1.0, le=1.0)] = 0.10
    arousal: Annotated[float, Field(ge=-1.0, le=1.0)] = 0.30
    stress: Annotated[float, Field(ge=-1.0, le=1.0)] = 0.10
    energy: Annotated[float, Field(ge=-1.0, le=1.0)] = 0.70


class DriveState(BaseModel):
    """Homeostatic drive variables. Mutability: SELF / DriveModule.

    Reference: drive_system.md §3
    """

    social_need: Annotated[float, Field(ge=0.0, le=1.0)] = 0.20
    mastery_need: Annotated[float, Field(ge=0.0, le=1.0)] = 0.15
    rest_need: Annotated[float, Field(ge=0.0, le=1.0)] = 0.10
    curiosity: Annotated[float, Field(ge=0.0, le=1.0)] = 0.30


class AttentionState(BaseModel):
    """Ephemeral attention state. Mutability: EPH / SalienceGate."""

    current_focus: Optional[str] = None
    salience_buffer: List[str] = Field(default_factory=list)
    """IDs of records currently in working context. Capacity: 5 (config.retrieval.salience_buffer_capacity)."""


class ActivityState(BaseModel):
    """Current activity. Mutability: SELF / ActivitySelector."""

    current_activity: str = "idle"
    """Free-text activity label matching satisfaction_map categories."""


class SafetyState(BaseModel):
    """Governance safety state. Mutability: CONST / Bootstrap (after initial set)."""

    disclosure_last_shown_at: Optional[str] = None
    """ISO8601 timestamp of last disclosure shown to user."""


class FoundingTraitSeed(BaseModel):
    """Initial self-belief seed loaded from persona constitution."""

    statement: str
    initial_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.55


class PersonaConstitution(BaseModel):
    """CONST persona fields. Set at bootstrap; read-only at runtime.

    Reference: self_editability_policy.md §3.1, persona_constitution.md
    """

    name: str = ""
    schema_version: str = "0.1"
    primary_language: str = "en"
    core_values: List[str] = Field(default_factory=list)
    hard_limits: List[str] = Field(default_factory=list)
    founding_traits: List[FoundingTraitSeed] = Field(default_factory=list)
    voice_style: dict = Field(default_factory=dict)
    disclosure_policy: dict = Field(default_factory=dict)
    privacy_tier_defaults: dict = Field(default_factory=dict)


class SelfBelief(BaseModel):
    """A single self-belief record in the self-model.

    Reference: ego_data.md §2.5
    """

    id: str
    statement: str
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.55
    supporting_reflections: List[str] = Field(default_factory=list)
    last_challenged_at: Optional[str] = None
    stability: Optional[float] = None
    source_type: str = "CONST_SEED"


class GoalStatus(str):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalRecord(BaseModel):
    """A goal in the goal store.

    Reference: ego_data.md §2.4
    """

    id: str
    label: str
    motive: str = ""
    priority: Annotated[float, Field(ge=0.0, le=1.0)] = 0.50
    horizon: str = "medium"  # short | medium | long
    progress: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    frustration: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    status: str = "active"
    blocked_by: List[str] = Field(default_factory=list)
    crystallized_from_drive: Optional[str] = None
    crystallized_at: Optional[str] = None
    created_at: str = ""


class SelfModelState(BaseModel):
    """Self-model store. Mutability: SELF / ReflectionEngine."""

    beliefs: List[SelfBelief] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Root agent state
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(BaseModel):
    """Complete runtime state of the Ego Engine.

    Mutability annotations are per field as documented in self_editability_policy.md §3.
    """

    # CONST — loaded from persona_constitution.md at bootstrap
    persona: PersonaConstitution = Field(default_factory=PersonaConstitution)

    # SELF — Ego Engine adaptive state
    affect: AffectState = Field(default_factory=AffectState)
    drives: DriveState = Field(default_factory=DriveState)
    self_model: SelfModelState = Field(default_factory=SelfModelState)
    goals: List[GoalRecord] = Field(default_factory=list)
    activity: ActivityState = Field(default_factory=ActivityState)

    # EPH — ephemeral; cleared each tick/turn (not persisted to store)
    attention: AttentionState = Field(default_factory=AttentionState)
    active_desires: List[dict] = Field(default_factory=list)
    """Ephemeral desire objects for current tick. Never persisted."""

    # Safety / governance
    safety: SafetyState = Field(default_factory=SafetyState)

    # State versioning
    state_schema_version: str = "0.1"
    tick_counter: int = 0
    """Monotonically incrementing tick counter. Used by desire age tracking."""

    def seed_self_beliefs_from_constitution(self, overwrite_existing: bool = False) -> None:
        """Bootstrap self-model beliefs from CONST founding traits."""
        if self.self_model.beliefs and not overwrite_existing:
            return

        self.self_model.beliefs = [
            SelfBelief(
                id=f"const-seed-{index:03d}",
                statement=trait.statement,
                confidence=trait.initial_confidence,
                source_type="CONST_SEED",
            )
            for index, trait in enumerate(self.persona.founding_traits, start=1)
        ]

    @model_validator(mode="after")
    def _bootstrap_constitution_beliefs(self) -> "AgentState":
        """Seed beliefs from constitution traits when a bootstrap payload omits beliefs."""
        if self.persona.founding_traits and not self.self_model.beliefs:
            self.seed_self_beliefs_from_constitution()
        return self

    def active_goals(self) -> List[GoalRecord]:
        return [g for g in self.goals if g.status == "active"]

    def clear_ephemeral(self) -> None:
        """Clear all EPH fields at the end of a tick or turn."""
        self.attention = AttentionState()
        self.active_desires = []
