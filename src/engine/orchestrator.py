"""
Ego Engine Orchestrator — coordinates all cognitive cycle types.

Core guarantees:
- Transactional: every cycle either fully commits or fully rolls back
- Deterministic: same input + state → same non-LLM outputs
- Single-writer: enforced via FieldOwnershipRegistry

Reference: cognitive_loop.md §8 (top-level pseudocode), self_editability_policy.md §5.1
CP-1 exit gate: rollback leaves no persistent write residue
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema.mutability import DEFAULT_REGISTRY, FieldOwnershipRegistry, MutabilityViolation
from ..schema.state import AgentState
from ..schema.validator import validate_const_fields_unchanged, validate_proposed_writes
from .contracts import CYCLE_CONTRACTS, CycleType
from .cycle_log import CycleLogEntry, CycleLogger, compute_delta, hash_state


class PolicyViolation(Exception):
    """Raised when a cycle produces output that fails policy checks."""


class CycleResult:
    """Result of a single orchestrated cycle."""

    def __init__(
        self,
        success: bool,
        cycle_id: str,
        cycle_type: CycleType,
        written_fields: Optional[List[str]] = None,
        rollback_reason: Optional[str] = None,
        desires_generated: int = 0,
        desires_crystallized: int = 0,
        duration_ms: int = 0,
    ) -> None:
        self.success = success
        self.cycle_id = cycle_id
        self.cycle_type = cycle_type
        self.written_fields: List[str] = written_fields or []
        self.rollback_reason = rollback_reason
        self.desires_generated = desires_generated
        self.desires_crystallized = desires_crystallized
        self.duration_ms = duration_ms

    def __repr__(self) -> str:
        status = "OK" if self.success else f"ROLLBACK({self.rollback_reason})"
        return f"CycleResult({self.cycle_type.value} {status})"


StepFn = Any  # Callable[[AgentState, dict, list], None]


class EgoOrchestrator:
    """Deterministic orchestrator for all Ego Engine cycle types.

    Usage::

        orchestrator = EgoOrchestrator(state, logger)
        result = orchestrator.run_cycle(CycleType.FAST_TICK, {})

    Step functions are registered per step name. Unregistered steps execute
    as no-ops (allowing stub-driven development through CP-1).
    """

    def __init__(
        self,
        state: AgentState,
        logger: Optional[CycleLogger] = None,
        registry: Optional[FieldOwnershipRegistry] = None,
    ) -> None:
        self.state = state
        self._logger = logger
        self._registry = registry or DEFAULT_REGISTRY
        self._step_registry: Dict[str, StepFn] = {}

    def register_step(self, step_name: str, fn: StepFn) -> None:
        """Register a step implementation function.

        fn signature: (state: AgentState, context: dict, pending_writes: list) -> None
        """
        self._step_registry[step_name] = fn

    def run_cycle(
        self,
        cycle_type: CycleType,
        input_event: Optional[Dict[str, Any]] = None,
    ) -> CycleResult:
        """Execute a full cycle of the given type.

        Transaction contract:
        1. Snapshot current state
        2. Execute each step in contract order
        3. Validate all pending writes against ownership registry
        4. Validate CONST fields unchanged
        5. If any validation fails: rollback to snapshot, log as rollback
        6. If all pass: commit writes, log success

        Returns CycleResult.
        """
        cycle_id = str(uuid.uuid4())
        start_ts = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()
        input_event = input_event or {}

        # Step 1: Snapshot before state
        snapshot = self.state.model_copy(deep=True)
        before_hash = hash_state(snapshot)

        pending_writes: List[Dict[str, str]] = []
        modules_executed: List[str] = []
        desires_generated = 0
        desires_crystallized = 0

        try:
            # Step 2: Execute each step in contract order
            for step_name in CYCLE_CONTRACTS[cycle_type]:
                step_fn = self._step_registry.get(step_name)
                if step_fn is not None:
                    step_fn(self.state, input_event, pending_writes)
                modules_executed.append(step_name)

            # Step 3: Validate proposed writes
            write_validation = validate_proposed_writes(pending_writes, self._registry)
            if not write_validation.valid:
                raise PolicyViolation(
                    "Write validation failed: " + "; ".join(write_validation.errors)
                )

            # Step 4: Validate CONST fields unchanged
            const_validation = validate_const_fields_unchanged(snapshot, self.state)
            if not const_validation.valid:
                raise PolicyViolation(
                    "CONST violation: " + "; ".join(const_validation.errors)
                )

            # Step 5: Commit — state changes made by step_fns are already applied;
            # persist any episodic writes from pending_writes context
            written_fields = [w["field_path"] for w in pending_writes]

            # Finalize cycle state as part of the committed state footprint.
            self.state.clear_ephemeral()
            self.state.tick_counter += 1

            after_hash = hash_state(self.state)
            delta = compute_delta(snapshot, self.state)

            duration_ms = int((time.monotonic() - start_ts) * 1000)
            entry = self._build_log_entry(
                cycle_id=cycle_id,
                cycle_type=cycle_type,
                timestamp=timestamp,
                before_hash=before_hash,
                after_hash=after_hash,
                delta=delta,
                modules_executed=modules_executed,
                desires_generated=desires_generated,
                desires_crystallized=desires_crystallized,
                write_count=len(written_fields),
                rollback=False,
                duration_ms=duration_ms,
            )
            if self._logger:
                self._logger.append(entry)

            return CycleResult(
                success=True,
                cycle_id=cycle_id,
                cycle_type=cycle_type,
                written_fields=written_fields,
                desires_generated=desires_generated,
                desires_crystallized=desires_crystallized,
                duration_ms=duration_ms,
            )

        except (PolicyViolation, MutabilityViolation) as exc:
            # Full rollback
            self.state = snapshot

            duration_ms = int((time.monotonic() - start_ts) * 1000)
            rollback_reason = str(exc)
            entry = self._build_log_entry(
                cycle_id=cycle_id,
                cycle_type=cycle_type,
                timestamp=timestamp,
                before_hash=before_hash,
                after_hash=before_hash,  # unchanged on rollback
                delta={},
                modules_executed=modules_executed,
                desires_generated=0,
                desires_crystallized=0,
                write_count=0,
                rollback=True,
                rollback_reason=rollback_reason,
                duration_ms=duration_ms,
            )
            if self._logger:
                self._logger.append(entry)

            return CycleResult(
                success=False,
                cycle_id=cycle_id,
                cycle_type=cycle_type,
                rollback_reason=rollback_reason,
                duration_ms=duration_ms,
            )

    @staticmethod
    def _build_log_entry(
        cycle_id: str,
        cycle_type: CycleType,
        timestamp: str,
        before_hash: str,
        after_hash: str,
        delta: Dict,
        modules_executed: List[str],
        desires_generated: int,
        desires_crystallized: int,
        write_count: int,
        rollback: bool,
        duration_ms: int,
        rollback_reason: Optional[str] = None,
    ) -> CycleLogEntry:
        return CycleLogEntry(
            cycle_id=cycle_id,
            cycle_type=cycle_type.value,
            timestamp=timestamp,
            before_state_hash=before_hash,
            after_state_hash=after_hash,
            delta=delta,
            modules_executed=modules_executed,
            desires_generated=desires_generated,
            desires_crystallized=desires_crystallized,
            write_count=write_count,
            rollback=rollback,
            rollback_reason=rollback_reason,
            duration_ms=duration_ms,
        )
