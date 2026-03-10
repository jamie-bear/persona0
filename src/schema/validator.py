"""
Schema and mutability validation utilities.

Reference:
- self_editability_policy.md §5.1 (pre-commit validation)
- execution_checkpoints.md CP-0 exit gate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from pydantic import ValidationError

from .mutability import FieldOwnershipRegistry, MutabilityViolation
from .state import AgentState


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False


def validate_state_packet(data: Dict[str, Any]) -> ValidationResult:
    """Validate a raw dict against the AgentState schema.

    Returns ValidationResult with any schema errors.
    """
    result = ValidationResult(valid=True)
    try:
        AgentState.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            result.add_error(f"schema: {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}")
    return result


def validate_no_ownership_conflicts(registry: FieldOwnershipRegistry) -> ValidationResult:
    """Assert that no field appears under two different ownership entries.

    Returns ValidationResult. Passes when registry.conflicts() is empty.
    This is part of the CP-0 exit gate: field ownership conflicts = 0.
    """
    result = ValidationResult(valid=True)
    for field_path, reason in registry.conflicts():
        result.add_error(f"ownership_conflict: {field_path}: {reason}")
    return result


def validate_proposed_writes(
    proposed_writes: List[Dict[str, str]],
    registry: FieldOwnershipRegistry,
) -> ValidationResult:
    """Validate a list of proposed field writes before commit.

    Each item in proposed_writes should be: {'field_path': str, 'author_module': str}

    Raises nothing — returns ValidationResult with all violations collected.
    This is the programmatic implementation of self_editability_policy.md §5.1.
    """
    result = ValidationResult(valid=True)
    for write in proposed_writes:
        field_path = write.get("field_path", "")
        author = write.get("author_module", "")
        try:
            registry.validate_write(field_path, author)
        except MutabilityViolation as exc:
            result.add_error(str(exc))
        except KeyError:
            result.add_error(f"UNREGISTERED FIELD: field='{field_path}' author='{author}'")
    return result


def validate_const_fields_unchanged(
    before: AgentState,
    after: AgentState,
) -> ValidationResult:
    """Assert that CONST fields in before and after states are identical.

    This is the strongest form of the CONST protection check.
    """
    result = ValidationResult(valid=True)

    before_persona = before.persona.model_dump()
    after_persona = after.persona.model_dump()

    for key, before_val in before_persona.items():
        after_val = after_persona.get(key)
        if before_val != after_val:
            result.add_error(
                f"CONST_VIOLATION: persona.{key} changed from {before_val!r} to {after_val!r}"
            )
    return result
