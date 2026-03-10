"""
Fast tick cycle step implementations (~30 min cadence).

Reference: cognitive_loop.md §3.1
CP-3: all steps behavior-complete except 'appraise' (LLM-dependent, kept as stub).
"""

from __future__ import annotations

from typing import Any, Dict, List

from ...schema.state import AgentState
from ._store_helpers import (
    attach_embedding_metadata,
    deterministic_record_metadata,
    next_record_sequence_index,
    try_store_append,
    upsert_vector_index,
)
from ..modules.emotion import EmotionModule
from ..modules.drive import DriveModule
from ..modules.thought import ThoughtGenerator
from ..modules.goal import GoalSystem
from ..retrieval import load_retrieval_limits
from ..adapters import llm as llm_adapter
from ..modules._config import load_config_section

_emotion_module = EmotionModule()
_drive_module = DriveModule()
_thought_gen = ThoughtGenerator()
_goal_system = GoalSystem()


def world_ingest(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """1. WORLD_INGEST — normalise activity_events from input into event context."""
    event.setdefault("activity_events", [])
    event.setdefault("appraisal_results", [])


def appraise(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """2. APPRAISE — adapter-generated appraisal with validated structure."""
    cfg = load_config_section("llm_adapter")
    if not bool(cfg.get("enabled", False)):
        event.setdefault("appraisal_results", [])
        return

    raw_results = llm_adapter.appraise_events(event.get("activity_events", []), state)
    event["appraisal_results"] = llm_adapter.validate_appraisal_results(raw_results)


def update_emotion(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """3. UPDATE_EMOTION — EMA decay + circadian modulation + appraisal deltas."""
    new_affect = _emotion_module.update(
        affect=state.affect,
        appraisal_results=event.get("appraisal_results", []),
        tick_counter=state.tick_counter,
    )
    state.affect = new_affect

    # Store the rest_need boost for DriveModule to consume
    event["_stress_rest_boost"] = _emotion_module.stress_rest_boost(new_affect.stress)

    pending_writes.append({"field_path": "affect.valence", "author_module": "EmotionModule"})
    pending_writes.append({"field_path": "affect.arousal", "author_module": "EmotionModule"})
    pending_writes.append({"field_path": "affect.stress", "author_module": "EmotionModule"})
    pending_writes.append({"field_path": "affect.energy", "author_module": "EmotionModule"})


def update_drives(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """3.5. UPDATE_DRIVES — growth rates + activity satisfaction + stress coupling."""
    new_drives = _drive_module.update(
        drives=state.drives,
        activity_events=event.get("activity_events", []),
        rest_boost=float(event.get("_stress_rest_boost", 0.0)),
    )
    state.drives = new_drives

    pending_writes.append({"field_path": "drives.social_need", "author_module": "DriveModule"})
    pending_writes.append({"field_path": "drives.mastery_need", "author_module": "DriveModule"})
    pending_writes.append({"field_path": "drives.rest_need", "author_module": "DriveModule"})
    pending_writes.append({"field_path": "drives.curiosity", "author_module": "DriveModule"})


def generate_thought(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """4. GENERATE_THOUGHT — deterministic category + template-based thought."""
    thought = _thought_gen.generate(
        state=state,
        active_desires=state.active_desires,
        tick_counter=state.tick_counter,
    )
    event["generated_thought"] = thought

    # Update consecutive category tracker (EPH)
    cats = list(state.consecutive_thought_categories)
    cats.append(thought["thought_category"])
    state.consecutive_thought_categories = cats[-3:]  # keep last 3
    pending_writes.append(
        {"field_path": "consecutive_thought_categories", "author_module": "ThoughtGenerator"}
    )


def salience_filter(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """5. SALIENCE_FILTER — collect candidates and trim to salience_buffer_capacity."""
    limits = load_retrieval_limits()
    capacity = int(limits["salience_buffer_capacity"])

    candidates: List[str] = []

    # Generated thought first (highest salience in background tick)
    thought = event.get("generated_thought")
    if thought and thought.get("id"):
        candidates.append(thought["id"])

    # Any pre-ranked memory ids from prior steps
    for record in event.get("ranked_memories", []):
        if len(candidates) >= capacity:
            break
        rid = record.get("id", "")
        if rid and rid not in candidates:
            candidates.append(rid)

    state.attention.salience_buffer = candidates[:capacity]
    pending_writes.append(
        {"field_path": "attention.salience_buffer", "author_module": "SalienceGate"}
    )


def update_goals(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """6. UPDATE_GOALS — tick progress/frustration; check suspension thresholds."""
    updated = _goal_system.tick_goals(state.goals)
    state.goals = updated
    pending_writes.append({"field_path": "goals", "author_module": "GoalSystem"})


def write_memory(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """7. WRITE_MEMORY — append generated thought as an episodic record.

    The episodic store reference is injected via event['_store'] by default_setup.
    If absent, the thought is recorded in event['_pending_episodic'] for inspection.
    """
    thought = event.get("generated_thought")
    if not thought:
        return

    metadata = deterministic_record_metadata(
        state,
        event,
        cycle_type="fast_tick",
        record_type="thought",
        sequence_index=next_record_sequence_index(event),
    )
    record = {
        "id": metadata["id"],
        "created_at": metadata["created_at"],
        "cycle_id": event.get("_cycle_id", ""),
        "author_module": "Orchestrator",
        "event_text": thought.get("text", ""),
        "importance": float(thought.get("intrusiveness", 0.3)),
        "decay_factor": 1.0,
        "lifecycle_state": "active",
        "record_type": "thought",
        "thought_category": thought.get("thought_category", "reflection"),
        "trigger": thought.get("trigger", "internal"),
        "source_desire_drive": thought.get("source_desire_drive"),
    }

    embedded = attach_embedding_metadata(
        record,
        record.get("event_text", ""),
        content_type="episodic_thought",
    )
    upsert_vector_index(event, record, embedded)

    store = event.get("_store")
    if store is not None:
        try_store_append(store, record, state, event)

    event.setdefault("_pending_episodic", []).append(record)
    pending_writes.append({"field_path": "episodic_log", "author_module": "Orchestrator"})


def log_cycle(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """8. LOG — handled by EgoOrchestrator; this step is a no-op."""
