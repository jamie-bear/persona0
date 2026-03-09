"""
Interaction cycle step stubs.

Reference: cognitive_loop.md §2
"""
from __future__ import annotations

from typing import Any, Dict, List

from ...schema.state import AgentState


def ingest_turn(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """A. ingest_turn — receive and normalise the user message."""


def parse_intent_affect(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """B. parse_intent_affect — extract intent and affective cues."""


def retrieve_memory_candidates(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """C. retrieve_memory_candidates — query episodic and semantic stores."""


def salience_competition(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """D. salience_competition — select what enters working context (capacity: 5)."""


def appraisal_update(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """E. appraisal_update — evaluate event against goals, self-model, current affect."""


def build_context_package(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """F. build_context_package — assemble the prompt context sent to LLM."""


def render_response(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """G. render_response — LLM renders candidate text; no writes to persistent state."""


def policy_and_consistency_check(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """H. policy_and_consistency_check — validate candidate response and pending writes."""


def commit_or_rollback(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """I. commit_or_rollback — handled by EgoOrchestrator; this stub is a no-op."""
