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
    """G. render_response — LLM renders candidate text; no writes to persistent state."""


def policy_and_consistency_check(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """H. policy_and_consistency_check — validate candidate response and pending writes."""


def commit_or_rollback(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """I. commit_or_rollback — handled by EgoOrchestrator; this stub is a no-op."""
