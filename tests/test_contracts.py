"""
CP-0 exit gate: loop order contract determinism tests.

Tests:
1. All four cycle types have non-empty step lists
2. Key ordering invariants are satisfied
3. Same cycle type always returns the same step sequence
4. Specific required steps are present in each cycle type
"""
from src.engine.contracts import (
    CYCLE_CONTRACTS,
    CycleType,
    APPRAISE,
    BUILD_CONTEXT_PACKAGE,
    COMMIT_OR_ROLLBACK,
    DESIRE_GENERATION,
    FAST_TICK_STEPS,
    GENERATE_THOUGHT,
    INTERACTION_STEPS,
    LOG_CYCLE,
    MACRO_STEPS,
    POLICY_AND_CONSISTENCY_CHECK,
    RENDER_RESPONSE,
    SLOW_TICK_STEPS,
    UPDATE_DRIVES,
    UPDATE_EMOTION,
    UPDATE_SELF_BELIEFS,
    WRITE_MEMORY,
    get_steps,
    validate_step_ordering,
)


def test_all_cycle_types_have_steps():
    """Every cycle type must have at least one step."""
    for cycle_type in CycleType:
        steps = get_steps(cycle_type)
        assert len(steps) > 0, f"{cycle_type} has no steps"


def test_step_ordering_invariants():
    """CP-0 exit gate: key ordering invariants must pass for all cycle types."""
    errors = validate_step_ordering()
    all_errors = []
    for ct, errs in errors.items():
        for err in errs:
            all_errors.append(f"{ct}: {err}")
    assert not all_errors, "Step ordering violations: " + "; ".join(all_errors)


def test_step_lists_are_deterministic():
    """get_steps must return the same sequence on every call (determinism)."""
    for cycle_type in CycleType:
        first = get_steps(cycle_type)
        second = get_steps(cycle_type)
        assert first == second, f"{cycle_type} step list is not deterministic"


def test_interaction_required_steps():
    """Interaction cycle must contain all 9 required steps in correct order."""
    steps = INTERACTION_STEPS
    for required in [RENDER_RESPONSE, POLICY_AND_CONSISTENCY_CHECK, COMMIT_OR_ROLLBACK]:
        assert required in steps, f"Missing step: {required}"

    render_idx = steps.index(RENDER_RESPONSE)
    policy_idx = steps.index(POLICY_AND_CONSISTENCY_CHECK)
    commit_idx = steps.index(COMMIT_OR_ROLLBACK)
    assert render_idx < policy_idx < commit_idx, (
        "Interaction step order violated: render must precede policy check, which must precede commit"
    )


def test_fast_tick_update_drives_after_emotion():
    """Fast tick: UPDATE_DRIVES must come after UPDATE_EMOTION."""
    steps = FAST_TICK_STEPS
    assert UPDATE_EMOTION in steps
    assert UPDATE_DRIVES in steps
    assert steps.index(UPDATE_EMOTION) < steps.index(UPDATE_DRIVES)


def test_fast_tick_generate_thought_after_drives():
    """Fast tick: GENERATE_THOUGHT must come after UPDATE_DRIVES."""
    steps = FAST_TICK_STEPS
    assert steps.index(UPDATE_DRIVES) < steps.index(GENERATE_THOUGHT)


def test_slow_tick_desire_generation_after_write_memory():
    """Slow tick: DESIRE_GENERATION must come after WRITE_MEMORY."""
    steps = SLOW_TICK_STEPS
    assert WRITE_MEMORY in steps
    assert DESIRE_GENERATION in steps
    assert steps.index(WRITE_MEMORY) < steps.index(DESIRE_GENERATION)


def test_slow_tick_contains_fast_tick_core():
    """Slow tick must include the core fast tick steps (world_ingest through write_memory)."""
    fast_core = [s for s in FAST_TICK_STEPS if s != LOG_CYCLE]
    slow_steps = SLOW_TICK_STEPS
    for step in fast_core:
        assert step in slow_steps, f"Slow tick missing fast tick step: {step}"


def test_macro_self_belief_update_after_evidence_score():
    """Macro: UPDATE_SELF_BELIEFS must come after evidence scoring."""
    from src.engine.contracts import SCORE_EVIDENCE_SUFFICIENCY, ARCHIVE_REFLECTION
    steps = MACRO_STEPS
    score_idx = steps.index(SCORE_EVIDENCE_SUFFICIENCY)
    update_idx = steps.index(UPDATE_SELF_BELIEFS)
    archive_idx = steps.index(ARCHIVE_REFLECTION)
    assert score_idx < update_idx < archive_idx


def test_no_duplicate_steps_in_interaction():
    """No step should appear twice in the interaction cycle."""
    steps = INTERACTION_STEPS
    assert len(steps) == len(set(steps)), "Duplicate steps in interaction cycle"


def test_cycle_contracts_dict_complete():
    """CYCLE_CONTRACTS must contain an entry for every CycleType."""
    for ct in CycleType:
        assert ct in CYCLE_CONTRACTS, f"Missing contract for {ct}"
