"""
Record type schemas — all persistent and ephemeral data records.

Reference: ego_data.md §2 (record schemas + mutability annotations)
"""

from __future__ import annotations

from typing import Annotated, List, Optional
from pydantic import BaseModel, Field


class RecordMeta(BaseModel):
    """Shared metadata for all record types.

    Reference: ego_data.md §2 (shared meta schema)
    """

    id: str
    created_at: str
    """ISO8601 timestamp."""

    source_type: str = "human"
    """human | synthetic | derived"""

    source_ref: str = ""
    """Reference to the source cycle_id or interaction_id."""

    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    privacy_tier: str = "medium"
    """low | medium | high"""

    ttl_days: Optional[int] = None
    mutability_class: str = "SELF"
    """CONST | SELF | EXT | EPH"""

    lifecycle_state: str = "active"
    """active | cooling | archived | deleted"""


class AffectSnapshot(BaseModel):
    """Affect state snapshot embedded in episodic records."""

    valence: float = 0.0
    arousal: float = 0.0
    stress: float = 0.0


class DriveSnapshot(BaseModel):
    """Drive state snapshot embedded in episodic records."""

    social_need: float = 0.0
    mastery_need: float = 0.0
    rest_need: float = 0.0
    curiosity: float = 0.0


class EpisodicEvent(BaseModel):
    """An episodic event record in the append-only episodic log.

    Mutability: SELF / Orchestrator (append-only; existing records immutable except decay_factor)
    Reference: ego_data.md §2.1
    """

    meta: RecordMeta
    when: str
    """ISO8601 timestamp of the event."""

    context: dict = Field(default_factory=dict)
    """{'location': str, 'participants': [str]}"""

    event_text: str
    affect_snapshot: AffectSnapshot = Field(default_factory=AffectSnapshot)
    drive_snapshot: DriveSnapshot = Field(default_factory=DriveSnapshot)
    goal_links: List[str] = Field(default_factory=list)
    importance: Annotated[float, Field(ge=0.0, le=1.0)] = 0.50
    reflection_pending: bool = True
    decay_factor: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    """Retrieval weight modifier; decays over time. Only mutable field post-creation."""


class ThoughtFragment(BaseModel):
    """A thought fragment record.

    Mutability: SELF / Orchestrator (append-only)
    Reference: ego_data.md §2.2
    """

    meta: RecordMeta
    trigger: str = "internal"
    """internal | external | memory_recall | desire"""

    source_desire_drive: Optional[str] = None
    """Which drive sourced this thought, if trigger == 'desire'."""

    text: str
    intrusiveness: Annotated[float, Field(ge=0.0, le=1.0)] = 0.30
    relevance_goal_id: Optional[str] = None
    thought_category: str = "reflection"
    """reflection | planning | rumination | curiosity | self-evaluation | social | fantasy"""


class Reflection(BaseModel):
    """A reflection record produced by the nightly macro-cycle.

    Mutability: SELF / ReflectionEngine (append-only)
    Reference: ego_data.md §2.3
    """

    meta: RecordMeta
    source_episode_ids: List[str] = Field(default_factory=list)
    pattern_statement: str
    confidence_delta: float
    """Max +0.15 per cycle (enforced by ReflectionEngine)."""

    proposed_self_belief_update: Optional[str] = None


class Goal(BaseModel):
    """A goal record in the goal store.

    Mutability: SELF / GoalSystem + DriveModule
    Reference: ego_data.md §2.4
    """

    meta: RecordMeta
    label: str
    motive: str = ""
    priority: Annotated[float, Field(ge=0.0, le=1.0)] = 0.50
    horizon: str = "medium"
    """short | medium | long"""

    progress: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    frustration: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    status: str = "active"
    """active | suspended | completed | abandoned"""

    blocked_by: List[str] = Field(default_factory=list)
    crystallized_from_drive: Optional[str] = None
    crystallized_at: Optional[str] = None


class SelfBelief(BaseModel):
    """A self-model belief record.

    Mutability: SELF / ReflectionEngine (rate-limited per self_editability_policy.md §3.2)
    Reference: ego_data.md §2.5
    """

    meta: RecordMeta
    statement: str
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.55
    supporting_reflections: List[str] = Field(default_factory=list)
    last_challenged_at: Optional[str] = None
    stability: Optional[float] = None


class Desire(BaseModel):
    """An ephemeral desire object.

    Mutability: EPH / DriveModule — NEVER persisted to any store.
    Reference: ego_data.md §2.6, drive_system.md §4
    """

    id: str
    source_drive: str
    content: str
    urgency: Annotated[float, Field(ge=0.0, le=1.0)]
    approach: bool = True
    expires_after_ticks: int = 3
    created_at_tick: int = 0
    age_in_ticks: int = 0

    @property
    def expired(self) -> bool:
        return self.age_in_ticks >= self.expires_after_ticks
