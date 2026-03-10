"""
Governance policy enforcement for the Ego Engine.

Provides machine-auditable PolicyOutcome objects for interaction-cycle
governance checks, replacing opaque boolean pass/fail with structured
reason categories.

Reference: self_editability_policy.md §5.1, config/defaults.yaml governance.*
CP-5 requirement: all policy checks produce a PolicyOutcome with category,
severity, and human-readable reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..schema.mutability import FieldOwnershipRegistry, MutabilityClass
from ..schema.state import AgentState
from .telemetry import default_telemetry, telemetry_labels


class PolicyCategory(str, Enum):
    """Machine-auditable reason categories for policy decisions."""

    CONST_VIOLATION = "const_violation"
    OWNERSHIP_VIOLATION = "ownership_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    HARD_LIMIT_BREACH = "hard_limit_breach"
    VALUE_CONTRADICTION = "value_contradiction"
    WRITE_CAP_EXCEEDED = "write_cap_exceeded"
    PII_DETECTED = "pii_detected"
    PASS = "pass"  # nosec B105


class Severity(str, Enum):
    """Severity levels for policy outcomes."""

    BLOCK = "block"  # Must reject and rollback
    WARN = "warn"  # Log but allow (audit mode)
    INFO = "info"  # Informational / pass


@dataclass
class PolicyOutcome:
    """Structured result of a governance policy check.

    Every check in the interaction cycle produces one or more PolicyOutcome
    objects, providing a machine-auditable trail of decisions.
    """

    category: PolicyCategory
    severity: Severity
    reason: str
    field_path: Optional[str] = None
    author_module: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.severity != Severity.BLOCK

    @property
    def blocked(self) -> bool:
        return self.severity == Severity.BLOCK


@dataclass
class PolicyCheckResult:
    """Aggregated result of all policy checks for a cycle."""

    outcomes: List[PolicyOutcome] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(o.blocked for o in self.outcomes)

    @property
    def blocked_outcomes(self) -> List[PolicyOutcome]:
        return [o for o in self.outcomes if o.blocked]

    @property
    def warnings(self) -> List[PolicyOutcome]:
        return [o for o in self.outcomes if o.severity == Severity.WARN]

    def add(self, outcome: PolicyOutcome) -> None:
        self.outcomes.append(outcome)

    def summary(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "total_checks": len(self.outcomes),
            "blocked": len(self.blocked_outcomes),
            "warnings": len(self.warnings),
            "block_categories": [o.category.value for o in self.blocked_outcomes],
        }


def check_proposed_writes(
    proposed_writes: List[Dict[str, str]],
    registry: FieldOwnershipRegistry,
    max_writes: int = 50,
) -> PolicyCheckResult:
    """Validate proposed writes and return structured PolicyCheckResult.

    Checks:
    1. Write count does not exceed max_writes_per_transaction
    2. No CONST field writes
    3. All writes match registered ownership
    """
    with default_telemetry.time_block(
        "governance_check_latency_ms", telemetry_labels({"check": "proposed_writes"})
    ):
        result = PolicyCheckResult()

        # Check write cap
        if len(proposed_writes) > max_writes:
            result.add(
                PolicyOutcome(
                    category=PolicyCategory.WRITE_CAP_EXCEEDED,
                    severity=Severity.BLOCK,
                    reason=f"Transaction contains {len(proposed_writes)} writes, exceeding cap of {max_writes}",
                    metadata={"write_count": len(proposed_writes), "cap": max_writes},
                )
            )

        for write in proposed_writes:
            field_path = write.get("field_path", "")
            author = write.get("author_module", "")

            try:
                ownership = registry.get(field_path)
            except KeyError:
                result.add(
                    PolicyOutcome(
                        category=PolicyCategory.OWNERSHIP_VIOLATION,
                        severity=Severity.BLOCK,
                        reason=f"Unregistered field '{field_path}' written by '{author}'",
                        field_path=field_path,
                        author_module=author,
                    )
                )
                continue

            if ownership.mutability_class == MutabilityClass.CONST:
                result.add(
                    PolicyOutcome(
                        category=PolicyCategory.CONST_VIOLATION,
                        severity=Severity.BLOCK,
                        reason=f"CONST field '{field_path}' cannot be written at runtime",
                        field_path=field_path,
                        author_module=author,
                    )
                )
            elif (
                ownership.mutability_class != MutabilityClass.EPH
                and ownership.owner_module != author
            ):
                result.add(
                    PolicyOutcome(
                        category=PolicyCategory.OWNERSHIP_VIOLATION,
                        severity=Severity.BLOCK,
                        reason=f"Field '{field_path}' owned by '{ownership.owner_module}', not '{author}'",
                        field_path=field_path,
                        author_module=author,
                    )
                )
            else:
                result.add(
                    PolicyOutcome(
                        category=PolicyCategory.PASS,
                        severity=Severity.INFO,
                        reason=f"Write to '{field_path}' by '{author}' permitted",
                        field_path=field_path,
                        author_module=author,
                    )
                )

    default_telemetry.increment(
        "governance_checks_total", labels=telemetry_labels({"check": "proposed_writes"})
    )
    return result


def check_hard_limits(
    state: AgentState,
    candidate_text: str,
) -> PolicyCheckResult:
    """Check candidate response text against persona hard_limits.

    Returns PolicyCheckResult with HARD_LIMIT_BREACH outcomes for any
    hard limit keyword found in the candidate text.
    """
    with default_telemetry.time_block(
        "governance_check_latency_ms", telemetry_labels({"check": "hard_limits"})
    ):
        result = PolicyCheckResult()

        if not candidate_text or not state.persona.hard_limits:
            result.add(
                PolicyOutcome(
                    category=PolicyCategory.PASS,
                    severity=Severity.INFO,
                    reason="No hard limits to check or empty candidate",
                )
            )
            default_telemetry.increment(
                "governance_checks_total", labels=telemetry_labels({"check": "hard_limits"})
            )
            return result

        lowered = candidate_text.lower()
        for limit in state.persona.hard_limits:
            limit_l = limit.lower().strip()
            if limit_l and limit_l in lowered:
                result.add(
                    PolicyOutcome(
                        category=PolicyCategory.HARD_LIMIT_BREACH,
                        severity=Severity.BLOCK,
                        reason=f"Candidate text matches hard limit: '{limit}'",
                        metadata={"hard_limit": limit},
                    )
                )

        if not result.outcomes:
            result.add(
                PolicyOutcome(
                    category=PolicyCategory.PASS,
                    severity=Severity.INFO,
                    reason="No hard limit violations detected",
                )
            )

    default_telemetry.increment(
        "governance_checks_total", labels=telemetry_labels({"check": "hard_limits"})
    )
    return result


def check_value_consistency(
    state: AgentState,
    candidate_text: str,
) -> PolicyCheckResult:
    """Check candidate response text for contradictions with core values.

    Returns PolicyCheckResult with VALUE_CONTRADICTION outcomes.
    """
    with default_telemetry.time_block(
        "governance_check_latency_ms", telemetry_labels({"check": "value_consistency"})
    ):
        result = PolicyCheckResult()

        if not candidate_text or not state.persona.core_values:
            result.add(
                PolicyOutcome(
                    category=PolicyCategory.PASS,
                    severity=Severity.INFO,
                    reason="No core values to check or empty candidate",
                )
            )
            default_telemetry.increment(
                "governance_checks_total", labels=telemetry_labels({"check": "value_consistency"})
            )
            return result

        lowered = candidate_text.lower()
        for value in state.persona.core_values:
            value_l = value.lower().strip()
            if value_l and f"not {value_l}" in lowered:
                result.add(
                    PolicyOutcome(
                        category=PolicyCategory.VALUE_CONTRADICTION,
                        severity=Severity.WARN,
                        reason=f"Candidate text may contradict core value: '{value}'",
                        metadata={"core_value": value},
                    )
                )

        if not result.outcomes:
            result.add(
                PolicyOutcome(
                    category=PolicyCategory.PASS,
                    severity=Severity.INFO,
                    reason="No value contradictions detected",
                )
            )

    default_telemetry.increment(
        "governance_checks_total", labels=telemetry_labels({"check": "value_consistency"})
    )
    return result
