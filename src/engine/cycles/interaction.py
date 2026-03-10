"""
Interaction cycle step stubs.

Reference: cognitive_loop.md §2
"""
from __future__ import annotations

from typing import Any, Dict, List

from ...schema.state import AgentState
from ..adapters.embeddings import embed_text
from ..retrieval import load_retrieval_limits, rank_memory_candidates
from ..adapters import llm as llm_adapter
from ..modules._config import load_config_section


def ingest_turn(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """A. ingest_turn — receive and normalise the user message."""


def parse_intent_affect(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """B. parse_intent_affect — extract intent and affective cues."""


def retrieve_memory_candidates(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """C. retrieve_memory_candidates — vector search then rerank for explainability."""
    with default_telemetry.time_block("interaction_step_latency_ms", telemetry_labels({"step": "retrieve_memory_candidates"})):
        limits = load_retrieval_limits()
        top_k = int(limits["candidate_limit"])
        records = list(event.get("memory_records", []))
        record_by_id = {str(r.get("id")): r for r in records if r.get("id")}

        query_text = str(event.get("message", ""))
        query_embedded = embed_text(query_text, content_type="user_turn")
        event["query_embedding"] = query_embedded["metadata"]

        candidates: List[Dict[str, Any]] = []
        vector_store = event.get("_vector_store")
        if vector_store is not None:
            vector_hits = vector_store.query(
                query_embedded["vector"],
                top_k=top_k,
                filters=event.get("vector_filters"),
            )
            for hit in vector_hits:
                rid = str(hit.get("id", ""))
                if not rid:
                    continue
                base = dict(record_by_id.get(rid, {}))
                base.setdefault("id", rid)
                base["similarity"] = float(hit.get("similarity", base.get("similarity", 0.0)))
                candidates.append(base)

        if not candidates:
            candidates = records

        event["memory_candidates"] = rank_memory_candidates(candidates, top_k=top_k)


def salience_competition(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """D. salience_competition — select what enters working context (capacity: 5)."""
    with default_telemetry.time_block("interaction_step_latency_ms", telemetry_labels({"step": "salience_competition"})):
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
    """G. render_response — LLM renders candidate text; no writes to persistent state.

    In production, an LLM adapter sets event['candidate_response'] before this
    step runs (or this step calls out to an LLM API).  When no LLM is wired
    the step produces a deterministic stub so downstream governance checks
    (step H) always have a candidate_response to validate.
    """
    if event.get("candidate_response"):
        # LLM adapter already populated the response; nothing to do.
        return

    cfg = load_config_section("llm_adapter")
    use_adapter = bool(cfg.get("enabled", False))
    deterministic_mode = bool(cfg.get("deterministic_mode", False))

    if use_adapter:
        try:
            event["candidate_response"] = llm_adapter.generate_response(
                event.get("context_package", {}),
                state,
            )
            return
        except Exception as exc:
            event["_response_adapter_error"] = str(exc)
            if not deterministic_mode:
                raise

    if deterministic_mode:
        event["candidate_response"] = _deterministic_fallback_response(state, event)
        return

    raise RuntimeError("No response available: adapter disabled and deterministic_mode is off")


def _deterministic_fallback_response(state: AgentState, event: Dict[str, Any]) -> str:
    """Deterministic response fallback used explicitly in dev/test mode."""
    persona_name = str(state.persona.name) if state.persona else "Assistant"
    ctx = event.get("context_package", {})
    memory_count = len(ctx.get("selected_memories", []))
    user_turn = str(event.get("message", ""))[:80]
    dominant_goal = next(
        (g.label for g in state.goals if getattr(g, "status", None) == "active"),
        None,
    )
    goal_note = f" (pursuing: {dominant_goal})" if dominant_goal else ""
    return (
        f"[{persona_name}{goal_note}] Responding to: {user_turn!r} "
        f"with {memory_count} memories in context."
    )


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
    if summary.get("blocked", 0) > 0:
        default_telemetry.increment("policy_block_total", labels=telemetry_labels())
    if summary.get("warnings", 0) > 0:
        default_telemetry.increment("policy_warning_total", labels=telemetry_labels())

    if not combined.passed:
        from ..orchestrator import PolicyViolation
        blocked = summary.get("block_categories", [])
        raise PolicyViolation(
            "Policy check failed: " + ", ".join(blocked or ["unknown"])
        )


def commit_or_rollback(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """I. commit_or_rollback — handled by EgoOrchestrator; this stub is a no-op."""
