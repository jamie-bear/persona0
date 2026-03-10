"""
CP-0 exit gate: schema validation and mutability conflict tests.

Tests:
1. AgentState validates against sample_state.json
2. All CONST fields are correctly registered
3. Field ownership conflicts = 0
4. validate_proposed_writes rejects CONST writes
5. validate_const_fields_unchanged detects CONST mutations
"""

import json
from pathlib import Path

import pytest

from src.schema.mutability import (
    MutabilityClass,
    build_default_registry,
)
from src.schema.state import AgentState
from src.schema.validator import (
    validate_const_fields_unchanged,
    validate_no_ownership_conflicts,
    validate_proposed_writes,
    validate_state_packet,
)


FIXTURES = Path(__file__).parent / "fixtures"


# ─────────────────────────────────────────────────────────────────────────────
# Schema validation
# ─────────────────────────────────────────────────────────────────────────────


def test_sample_state_validates():
    """AgentState must validate against the sample_state.json fixture."""
    data = json.loads((FIXTURES / "sample_state.json").read_text())
    result = validate_state_packet(data)
    assert result.valid, f"Schema errors: {result.errors}"


def test_default_state_validates():
    """Default AgentState() must be valid without any arguments."""
    state = AgentState()
    result = validate_state_packet(state.model_dump())
    assert result.valid, f"Schema errors: {result.errors}"


def test_affect_bounds_enforced():
    """Pydantic should reject affect values outside [-1, 1]."""
    data = json.loads((FIXTURES / "sample_state.json").read_text())
    data["affect"]["valence"] = 2.0  # out of bounds
    result = validate_state_packet(data)
    assert not result.valid
    assert any("valence" in e for e in result.errors)


def test_founding_traits_require_structured_objects():
    """founding_traits entries must include statement + initial_confidence."""
    data = json.loads((FIXTURES / "sample_state.json").read_text())
    data["persona"]["founding_traits"] = ["legacy string trait"]
    result = validate_state_packet(data)
    assert not result.valid
    assert any("founding_traits" in e for e in result.errors)


def test_founding_trait_confidence_bounds_enforced():
    """Founding trait confidence must be clamped to [0, 1]."""
    data = json.loads((FIXTURES / "sample_state.json").read_text())
    data["persona"]["founding_traits"][0]["initial_confidence"] = 1.2
    result = validate_state_packet(data)
    assert not result.valid
    assert any("initial_confidence" in e for e in result.errors)


def test_bootstrap_seeds_beliefs_from_founding_traits():
    """Bootstrap should seed self_model beliefs from constitution founding traits."""
    data = json.loads((FIXTURES / "synthetic_day.json").read_text())["seed_state"]
    state = AgentState.model_validate(data)

    assert len(state.self_model.beliefs) == len(state.persona.founding_traits)
    for belief, trait in zip(state.self_model.beliefs, state.persona.founding_traits):
        assert belief.statement == trait.statement
        assert belief.confidence == trait.initial_confidence
        assert belief.source_type == "CONST_SEED"


def test_drive_bounds_enforced():
    """Pydantic should reject drive values outside [0, 1]."""
    data = json.loads((FIXTURES / "sample_state.json").read_text())
    data["drives"]["social_need"] = -0.1  # out of bounds
    result = validate_state_packet(data)
    assert not result.valid
    assert any("social_need" in e for e in result.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Mutability registry
# ─────────────────────────────────────────────────────────────────────────────


def test_no_ownership_conflicts():
    """CP-0 exit gate: field ownership conflicts must equal 0."""
    registry = build_default_registry()
    result = validate_no_ownership_conflicts(registry)
    assert result.valid, f"Ownership conflicts: {result.errors}"


def test_const_fields_registered():
    """All CONST fields must be in the registry with class CONST."""
    registry = build_default_registry()
    const_fields = [
        "persona.name",
        "persona.core_values",
        "persona.hard_limits",
        "persona.founding_traits",
        "persona.disclosure_policy",
    ]
    for field_path in const_fields:
        ownership = registry.get(field_path)
        assert ownership.mutability_class == MutabilityClass.CONST, (
            f"Expected {field_path} to be CONST, got {ownership.mutability_class}"
        )


def test_self_fields_registered():
    """Key SELF fields must be in the registry with correct owner modules."""
    registry = build_default_registry()
    checks = [
        ("affect.valence", "EmotionModule"),
        ("drives.social_need", "DriveModule"),
        ("goals", "GoalSystem"),
    ]
    for field_path, expected_owner in checks:
        ownership = registry.get(field_path)
        assert ownership.mutability_class == MutabilityClass.SELF
        assert ownership.owner_module == expected_owner


def test_eph_fields_registered():
    """EPH fields must be in the registry with class EPH."""
    registry = build_default_registry()
    eph_fields = ["active_desires", "context_package", "attention.salience_buffer"]
    for field_path in eph_fields:
        ownership = registry.get(field_path)
        assert ownership.mutability_class == MutabilityClass.EPH


def test_duplicate_registration_raises():
    """Registering the same field twice must raise ValueError."""
    from src.schema.mutability import FieldOwnership, FieldOwnershipRegistry

    r = FieldOwnershipRegistry()
    fo = FieldOwnership("test.field", MutabilityClass.SELF, "TestModule")
    r.register(fo)
    with pytest.raises(ValueError):
        r.register(fo)


# ─────────────────────────────────────────────────────────────────────────────
# Write validation
# ─────────────────────────────────────────────────────────────────────────────


def test_const_write_rejected():
    """Proposed writes to CONST fields must be rejected."""
    registry = build_default_registry()
    writes = [{"field_path": "persona.name", "author_module": "EmotionModule"}]
    result = validate_proposed_writes(writes, registry)
    assert not result.valid
    assert any("CONST" in e for e in result.errors)


def test_wrong_owner_write_rejected():
    """Proposed writes by wrong owner module must be rejected."""
    registry = build_default_registry()
    writes = [{"field_path": "affect.valence", "author_module": "DriveModule"}]
    result = validate_proposed_writes(writes, registry)
    assert not result.valid


def test_correct_owner_write_accepted():
    """Proposed writes by correct owner must be accepted."""
    registry = build_default_registry()
    writes = [{"field_path": "affect.valence", "author_module": "EmotionModule"}]
    result = validate_proposed_writes(writes, registry)
    assert result.valid, result.errors


def test_eph_write_accepted_from_any_module():
    """EPH fields may be written by any module."""
    registry = build_default_registry()
    writes = [{"field_path": "active_desires", "author_module": "AnyModule"}]
    result = validate_proposed_writes(writes, registry)
    assert result.valid, result.errors


def test_unregistered_field_flagged():
    """Writes to unregistered fields must be flagged."""
    registry = build_default_registry()
    writes = [{"field_path": "nonexistent.field", "author_module": "SomeModule"}]
    result = validate_proposed_writes(writes, registry)
    assert not result.valid
    assert any("UNREGISTERED" in e for e in result.errors)


# ─────────────────────────────────────────────────────────────────────────────
# CONST field protection
# ─────────────────────────────────────────────────────────────────────────────


def test_const_unchanged_passes():
    """validate_const_fields_unchanged passes when CONST fields are identical."""
    state = AgentState()
    state.persona.name = "Mira"
    after = state.model_copy(deep=True)
    result = validate_const_fields_unchanged(state, after)
    assert result.valid, result.errors


def test_const_changed_detected():
    """validate_const_fields_unchanged detects CONST field mutation."""
    before = AgentState()
    before.persona.name = "Mira"
    after = before.model_copy(deep=True)
    after.persona.name = "Changed"
    result = validate_const_fields_unchanged(before, after)
    assert not result.valid
    assert any("CONST_VIOLATION" in e for e in result.errors)
