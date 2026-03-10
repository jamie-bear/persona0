"""
Interaction cycle step stubs.

Reference: cognitive_loop.md §2
"""
from __future__ import annotations

from typing import Any, Dict, List

from ...schema.state import AgentState
from ..retrieval import load_retrieval_limits, rank_memory_candidates


def ingest_turn(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """A. ingest_turn — receive and normalise the user message."""


def parse_intent_affect(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """B. parse_intent_affect — extract intent and affective cues."""


def retrieve_memory_candidates(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """C. retrieve_memory_candidates — query episodic and semantic stores."""
    records = event.get("memory_records", [])
    limits = load_retrieval_limits()
    event["memory_candidates"] = rank_memory_candidates(
        records,
        top_k=int(limits["candidate_limit"]),
    )


def salience_competition(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """D. salience_competition — select what enters working context (capacity: 5)."""
    limits = load_retrieval_limits()
    capacity = int(limits["salience_buffer_capacity"])
    candidates = event.get("memory_candidates", [])
    selected = [c.get("id") for c in candidates if c.get("id")][:capacity]

    state.attention.salience_buffer = selected
    pending_writes.append(
        {"field_path": "attention.salience_buffer", "author_module": "SalienceGate"}
    )


def appraisal_update(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """E. appraisal_update — evaluate event against goals, self-model, current affect."""


def build_context_package(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """F. build_context_package — assemble the prompt context sent to LLM."""
    selected_ids = state.attention.salience_buffer
    candidate_by_id = {c.get("id"): c for c in event.get("memory_candidates", [])}
    selected_memories = [candidate_by_id[mid] for mid in selected_ids if mid in candidate_by_id]

    event["context_package"] = {
        "user_turn": event.get("message", ""),
        "selected_memory_ids": list(selected_ids),
        "selected_memories": selected_memories,
    }
    pending_writes.append({"field_path": "context_package", "author_module": "ContextBuilder"})


def render_response(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """G. render_response — build candidate text for policy checks.

    Supports two deterministic paths:
    1) If ``event['_render_fn']`` is callable, it is invoked with
       ``(state, context_package, event)`` and should return text.
    2) Otherwise a deterministic local fallback template is used.

    This step intentionally performs no persistent writes.
    """
    context = event.get("context_package", {})
    render_fn = event.get("_render_fn")

    if callable(render_fn):
        candidate = str(render_fn(state, context, event))
    else:
        user_turn = str(context.get("user_turn", "")).strip()
        selected_ids = list(context.get("selected_memory_ids", []))
        memory_hint = ", ".join(selected_ids[:3]) if selected_ids else "no-prior-memory"
        candidate = (
            f"I hear you: {user_turn}. "
            f"I considered memories: {memory_hint}. "
            "I will respond consistently with my persona values."
        ).strip()

    event["candidate_response"] = candidate


def policy_and_consistency_check(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """H. policy_and_consistency_check — validate candidate response and pending writes.

    Produces structured PolicyOutcome objects for auditability (CP-5).
    Results are stored in event['_policy_check_result'] for the cycle log.
    """
    from ..governance import (
        PolicyCheckResult,
        check_hard_limits,
        check_proposed_writes,
        check_value_consistency,
    )
    from ...schema.mutability import DEFAULT_REGISTRY
    from ..modules._config import load_config_section

    gov_cfg = load_config_section("governance")
    max_writes = int(gov_cfg.get("max_writes_per_transaction", 50))

    combined = PolicyCheckResult()

    # 1. Validate proposed writes against ownership registry
    write_result = check_proposed_writes(pending_writes, DEFAULT_REGISTRY, max_writes)
    for outcome in write_result.outcomes:
        combined.add(outcome)

    # 2. Check candidate response against hard limits
    candidate_text = str(event.get("candidate_response", ""))
    if candidate_text:
        limit_result = check_hard_limits(state, candidate_text)
        for outcome in limit_result.outcomes:
            combined.add(outcome)

        # 3. Check value consistency
        value_result = check_value_consistency(state, candidate_text)
        for outcome in value_result.outcomes:
            combined.add(outcome)

    summary = combined.summary()
    event["_policy_check_result"] = summary

    if not combined.passed:
        from ..orchestrator import PolicyViolation
        blocked = summary.get("block_categories", [])
        raise PolicyViolation(
            "Policy check failed: " + ", ".join(blocked or ["unknown"])
        )


def commit_or_rollback(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """I. commit_or_rollback — handled by EgoOrchestrator; this stub is a no-op."""
