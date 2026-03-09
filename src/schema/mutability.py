"""
Mutability class registry and field ownership enforcement.

Reference: self_editability_policy.md §2-§5
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class MutabilityClass(str, Enum):
    """Four mutability classes for all state fields.

    CONST  — set at persona creation; read-only thereafter
    SELF   — writable by Ego Engine internal processes (reflection, goal lifecycle)
    EXT    — writable by operator/user via config or preference API
    EPH    — ephemeral; cleared each tick or conversation turn; never persisted
    """

    CONST = "CONST"
    SELF = "SELF"
    EXT = "EXT"
    EPH = "EPH"


@dataclass(frozen=True)
class FieldOwnership:
    """Ownership record for a single state field."""

    field_path: str
    """Dot-separated path, e.g. 'affect.valence'."""

    mutability_class: MutabilityClass

    owner_module: str
    """Canonical module name that holds write rights, e.g. 'EmotionModule'."""

    description: str = ""


class MutabilityViolation(Exception):
    """Raised when a module attempts to write a field it does not own or that is CONST."""

    def __init__(self, field_path: str, author_module: str, reason: str) -> None:
        self.field_path = field_path
        self.author_module = author_module
        self.reason = reason
        super().__init__(
            f"MUTABILITY VIOLATION: field='{field_path}' author='{author_module}' reason='{reason}'"
        )


class FieldOwnershipRegistry:
    """Canonical registry of all field ownership rules.

    Provides the enforcement point required by self_editability_policy.md §5.1.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, FieldOwnership] = {}

    def register(self, ownership: FieldOwnership) -> None:
        if ownership.field_path in self._registry:
            raise ValueError(
                f"Duplicate field registration: '{ownership.field_path}' already registered"
            )
        self._registry[ownership.field_path] = ownership

    def get(self, field_path: str) -> FieldOwnership:
        if field_path not in self._registry:
            raise KeyError(f"Field '{field_path}' is not registered in ownership registry")
        return self._registry[field_path]

    def validate_write(self, field_path: str, author_module: str) -> None:
        """Assert that author_module may write field_path.

        Raises MutabilityViolation on any violation.
        This is the enforcement point for self_editability_policy.md §5.1.
        """
        ownership = self.get(field_path)

        if ownership.mutability_class == MutabilityClass.CONST:
            raise MutabilityViolation(
                field_path,
                author_module,
                "CONST field cannot be written at runtime",
            )

        if ownership.mutability_class == MutabilityClass.EPH:
            # EPH fields may be written by any module (cleared automatically)
            return

        if ownership.owner_module != author_module:
            raise MutabilityViolation(
                field_path,
                author_module,
                f"field is owned by '{ownership.owner_module}', not '{author_module}'",
            )

    def conflicts(self) -> list[tuple[str, str]]:
        """Return list of (field_path, reason) for any detected conflicts.

        Currently checks for duplicate field paths (prevented at registration).
        Returns empty list when the registry is valid.
        """
        # Duplicate registration is caught at register() time.
        # This method is reserved for future cross-field conflict checks.
        return []

    @property
    def all_fields(self) -> list[FieldOwnership]:
        return list(self._registry.values())


# ─────────────────────────────────────────────────────────────────────────────
# Default registry — loaded at bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def build_default_registry() -> FieldOwnershipRegistry:
    """Construct the canonical field ownership registry from the spec.

    Reference: self_editability_policy.md §3 (full state mutability table).
    """
    r = FieldOwnershipRegistry()

    # ── CONST: Persona Constitution ──────────────────────────────────────────
    const_fields = [
        ("persona.name", "Bootstrap", "Persona name; set at creation"),
        ("persona.schema_version", "Bootstrap", "Constitution schema version"),
        ("persona.primary_language", "Bootstrap", "Primary language"),
        ("persona.core_values", "Bootstrap", "Non-negotiable value commitments"),
        ("persona.hard_limits", "Bootstrap", "Never-behaviours"),
        ("persona.disclosure_policy", "Bootstrap", "Disclosure rules"),
        ("persona.founding_traits", "Bootstrap", "Initial identity seeds"),
        ("persona.privacy_tier_defaults", "Bootstrap", "Default TTL and retention"),
    ]
    for path, owner, desc in const_fields:
        r.register(FieldOwnership(path, MutabilityClass.CONST, owner, desc))

    # ── SELF: Self-model / identity beliefs ──────────────────────────────────
    self_fields = [
        ("self_model.beliefs", "ReflectionEngine", "Self-belief records (append + update)"),
        ("self_model.beliefs[].confidence", "ReflectionEngine", "Confidence delta; rate-limited"),
        ("self_model.beliefs[].statement", "ReflectionEngine", "Belief statement text"),
        ("self_model.beliefs[].last_challenged_at", "AppraisalModule", "Staleness reset"),
        ("self_model.beliefs[].stability", "ReflectionEngine", "Derived from confidence trajectory"),
        # Goals
        ("goals[].progress", "GoalSystem", "Goal progress [0,1]"),
        ("goals[].frustration", "GoalSystem", "Goal frustration [0,1]"),
        ("goals[].status", "GoalSystem", "Goal lifecycle status"),
        ("goals[].priority", "GoalSystem", "Goal priority (daily review)"),
        ("goals", "GoalSystem", "Goal store (new goal creation)"),
        # Memory (append-only self-editable)
        ("episodic_log", "Orchestrator", "Append-only episodic event log"),
        ("semantic_store", "ReflectionEngine", "Derived semantic generalisations"),
        # Affect
        ("affect.valence", "EmotionModule", "Valence [-1,1]"),
        ("affect.arousal", "EmotionModule", "Arousal [-1,1]"),
        ("affect.stress", "EmotionModule", "Stress [-1,1]"),
        ("affect.energy", "EmotionModule", "Energy [-1,1]"),
        # Drives
        ("drives.social_need", "DriveModule", "Social need drive [0,1]"),
        ("drives.mastery_need", "DriveModule", "Mastery need drive [0,1]"),
        ("drives.rest_need", "DriveModule", "Rest need drive [0,1]"),
        ("drives.curiosity", "DriveModule", "Curiosity drive [0,1]"),
        # Activity
        ("activity.current_activity", "ActivitySelector", "Current activity label"),
    ]
    for path, owner, desc in self_fields:
        r.register(FieldOwnership(path, MutabilityClass.SELF, owner, desc))

    # ── EXT: Externally editable ──────────────────────────────────────────────
    ext_fields = [
        ("config", "Operator", "All numeric parameters"),
        ("user_preferences", "UserPreferenceAPI", "User privacy and style preferences"),
        ("relationship", "Orchestrator", "Familiarity/trust per user (seeded by operator)"),
    ]
    for path, owner, desc in ext_fields:
        r.register(FieldOwnership(path, MutabilityClass.EXT, owner, desc))

    # ── EPH: Ephemeral ────────────────────────────────────────────────────────
    eph_fields = [
        ("attention.salience_buffer", "SalienceGate", "Per-tick salience buffer"),
        ("attention.current_focus", "SalienceGate", "Current focus topic"),
        ("active_desires", "DriveModule", "Ephemeral desire objects; not persisted"),
        ("persisted_desires", "DriveModule", "Desires carried across slow ticks; not long-term"),
        ("appraisal_results", "AppraisalModule", "Per-tick appraisal outputs"),
        ("context_package", "ContextBuilder", "Assembled prompt context; discarded after render"),
        ("candidate_response", "LLMRenderer", "Draft response; discarded on commit/rollback"),
    ]
    for path, owner, desc in eph_fields:
        r.register(FieldOwnership(path, MutabilityClass.EPH, owner, desc))

    return r


# Module-level singleton for convenience; consumers may also construct their own.
DEFAULT_REGISTRY: FieldOwnershipRegistry = build_default_registry()
