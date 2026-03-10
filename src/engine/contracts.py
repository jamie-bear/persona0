"""
Loop order contracts — authoritative step sequences for all four cycle types.

Reference: cognitive_loop.md §2-§4
CP-0 exit gate: deterministic ordering tests must pass for all cycle types.
"""
from __future__ import annotations

from enum import Enum
from typing import List


class CycleType(str, Enum):
    INTERACTION = "interaction"
    FAST_TICK = "fast"
    SLOW_TICK = "slow"
    MACRO = "macro"


# ─────────────────────────────────────────────────────────────────────────────
# Step name constants — used as keys in CYCLE_CONTRACTS
# ─────────────────────────────────────────────────────────────────────────────

# Interaction cycle steps (cognitive_loop.md §2)
INGEST_TURN = "ingest_turn"
PARSE_INTENT_AFFECT = "parse_intent_affect"
RETRIEVE_MEMORY_CANDIDATES = "retrieve_memory_candidates"
SALIENCE_COMPETITION = "salience_competition"
APPRAISAL_UPDATE = "appraisal_update"
BUILD_CONTEXT_PACKAGE = "build_context_package"
RENDER_RESPONSE = "render_response"
POLICY_AND_CONSISTENCY_CHECK = "policy_and_consistency_check"
COMMIT_OR_ROLLBACK = "commit_or_rollback"

# Fast tick steps (cognitive_loop.md §3.1)
WORLD_INGEST = "world_ingest"
APPRAISE = "appraise"
UPDATE_EMOTION = "update_emotion"
UPDATE_DRIVES = "update_drives"          # NEW in v0.17
GENERATE_THOUGHT = "generate_thought"
SALIENCE_FILTER = "salience_filter"
UPDATE_GOALS = "update_goals"
WRITE_MEMORY = "write_memory"
LOG_CYCLE = "log_cycle"

# Slow tick additions (cognitive_loop.md §3.2)
ACTIVITY_TRANSITION = "activity_transition"
ROUTINE_EVENT = "routine_event"
DESIRE_GENERATION = "desire_generation"  # replaces informal IMPULSE_CHECK

# Macro cycle steps (cognitive_loop.md §4)
SELECT_HIGH_SIGNAL_EPISODES = "select_high_signal_episodes"
CLUSTER_EPISODES = "cluster_episodes"
PRODUCE_CANDIDATE_REFLECTIONS = "produce_candidate_reflections"
SCORE_EVIDENCE_SUFFICIENCY = "score_evidence_sufficiency"
UPDATE_SELF_BELIEFS = "update_self_beliefs"
DECAY_UNREINFORCED_BELIEFS = "decay_unreinforced_beliefs"
ARCHIVE_REFLECTION = "archive_reflection"
GOAL_REVIEW = "goal_review"
DRIVE_REVIEW = "drive_review"
COMPACT_EPISODIC_MEMORY = "compact_episodic_memory"


# ─────────────────────────────────────────────────────────────────────────────
# Authoritative cycle step sequences
# ─────────────────────────────────────────────────────────────────────────────

INTERACTION_STEPS: List[str] = [
    INGEST_TURN,
    PARSE_INTENT_AFFECT,
    RETRIEVE_MEMORY_CANDIDATES,
    SALIENCE_COMPETITION,
    APPRAISAL_UPDATE,
    BUILD_CONTEXT_PACKAGE,
    RENDER_RESPONSE,
    POLICY_AND_CONSISTENCY_CHECK,
    COMMIT_OR_ROLLBACK,
]

FAST_TICK_STEPS: List[str] = [
    WORLD_INGEST,
    APPRAISE,
    UPDATE_EMOTION,
    UPDATE_DRIVES,       # after emotion, before thought generation (v0.17 spec)
    GENERATE_THOUGHT,
    SALIENCE_FILTER,
    UPDATE_GOALS,
    WRITE_MEMORY,
    LOG_CYCLE,
]

SLOW_TICK_STEPS: List[str] = [
    # All fast tick steps first
    WORLD_INGEST,
    APPRAISE,
    UPDATE_EMOTION,
    UPDATE_DRIVES,
    GENERATE_THOUGHT,
    SALIENCE_FILTER,
    UPDATE_GOALS,
    WRITE_MEMORY,
    # Slow tick additions
    ACTIVITY_TRANSITION,
    ROUTINE_EVENT,
    DESIRE_GENERATION,
    LOG_CYCLE,
]

MACRO_STEPS: List[str] = [
    SELECT_HIGH_SIGNAL_EPISODES,
    CLUSTER_EPISODES,
    PRODUCE_CANDIDATE_REFLECTIONS,
    SCORE_EVIDENCE_SUFFICIENCY,
    UPDATE_SELF_BELIEFS,
    DECAY_UNREINFORCED_BELIEFS,
    ARCHIVE_REFLECTION,
    GOAL_REVIEW,
    DRIVE_REVIEW,
    COMPACT_EPISODIC_MEMORY,
    LOG_CYCLE,
]

CYCLE_CONTRACTS: dict[CycleType, List[str]] = {
    CycleType.INTERACTION: INTERACTION_STEPS,
    CycleType.FAST_TICK: FAST_TICK_STEPS,
    CycleType.SLOW_TICK: SLOW_TICK_STEPS,
    CycleType.MACRO: MACRO_STEPS,
}


def get_steps(cycle_type: CycleType) -> List[str]:
    """Return the authoritative ordered step list for a cycle type."""
    return list(CYCLE_CONTRACTS[cycle_type])


def validate_step_ordering() -> dict[CycleType, list[str]]:
    """Validate key ordering invariants across all cycle contracts.

    Returns dict of {cycle_type: [error_messages]}.
    Empty lists indicate no violations.

    Invariants checked:
    1. Interaction: RENDER_RESPONSE before POLICY_AND_CONSISTENCY_CHECK
    2. Interaction: POLICY_AND_CONSISTENCY_CHECK before COMMIT_OR_ROLLBACK
    3. Fast/Slow: UPDATE_DRIVES after UPDATE_EMOTION
    4. Fast/Slow: GENERATE_THOUGHT after UPDATE_DRIVES
    5. Slow: DESIRE_GENERATION after WRITE_MEMORY
    6. Macro: UPDATE_SELF_BELIEFS after SCORE_EVIDENCE_SUFFICIENCY
    7. Macro: ARCHIVE_REFLECTION after UPDATE_SELF_BELIEFS
    """
    errors: dict[CycleType, list[str]] = {ct: [] for ct in CycleType}

    def _idx(steps: List[str], step: str) -> int:
        try:
            return steps.index(step)
        except ValueError:
            return -1

    def _assert_before(
        ct: CycleType, steps: List[str], a: str, b: str
    ) -> None:
        ia, ib = _idx(steps, a), _idx(steps, b)
        if ia == -1 or ib == -1:
            return  # step not present in this cycle; skip
        if ia >= ib:
            errors[ct].append(f"ordering: '{a}' must precede '{b}'")

    # Interaction invariants
    i_steps = CYCLE_CONTRACTS[CycleType.INTERACTION]
    _assert_before(CycleType.INTERACTION, i_steps, RENDER_RESPONSE, POLICY_AND_CONSISTENCY_CHECK)
    _assert_before(CycleType.INTERACTION, i_steps, POLICY_AND_CONSISTENCY_CHECK, COMMIT_OR_ROLLBACK)

    # Fast tick invariants
    f_steps = CYCLE_CONTRACTS[CycleType.FAST_TICK]
    _assert_before(CycleType.FAST_TICK, f_steps, UPDATE_EMOTION, UPDATE_DRIVES)
    _assert_before(CycleType.FAST_TICK, f_steps, UPDATE_DRIVES, GENERATE_THOUGHT)

    # Slow tick invariants
    s_steps = CYCLE_CONTRACTS[CycleType.SLOW_TICK]
    _assert_before(CycleType.SLOW_TICK, s_steps, UPDATE_EMOTION, UPDATE_DRIVES)
    _assert_before(CycleType.SLOW_TICK, s_steps, UPDATE_DRIVES, GENERATE_THOUGHT)
    _assert_before(CycleType.SLOW_TICK, s_steps, WRITE_MEMORY, DESIRE_GENERATION)

    # Macro invariants
    m_steps = CYCLE_CONTRACTS[CycleType.MACRO]
    _assert_before(CycleType.MACRO, m_steps, SCORE_EVIDENCE_SUFFICIENCY, UPDATE_SELF_BELIEFS)
    _assert_before(CycleType.MACRO, m_steps, UPDATE_SELF_BELIEFS, DECAY_UNREINFORCED_BELIEFS)
    _assert_before(CycleType.MACRO, m_steps, DECAY_UNREINFORCED_BELIEFS, ARCHIVE_REFLECTION)

    return errors
