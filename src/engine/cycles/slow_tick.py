"""
Slow tick cycle step stubs (~2–4 hr cadence).

Runs all fast tick steps, then adds activity, routine, and desire generation.
Reference: cognitive_loop.md §3.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from ...schema.state import AgentState


def activity_transition(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """9. ACTIVITY_TRANSITION — select activity for circadian phase, energy, goals."""


def routine_event(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """10. ROUTINE_EVENT — generate a routine experience based on current activity."""


def desire_generation(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """11. DESIRE_GENERATION — generate ephemeral desires from high-drive states;
    check crystallization; persist desires above persistence threshold."""
