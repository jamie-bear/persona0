"""
Slow tick cycle step implementations (~2–4 hr cadence).

Runs all fast tick steps first, then adds activity transition, routine event
generation, and desire generation / crystallization.

Reference: cognitive_loop.md §3.2
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from ...schema.state import AgentState
from ..modules.drive import DriveModule
from ..modules.goal import GoalSystem

_drive_module = DriveModule()
_goal_system = GoalSystem()

# ── Activity selector ─────────────────────────────────────────────────────────
# Energy-based lookup. Returns activity label from satisfaction_map vocabulary.
_ACTIVITY_TABLE = [
    (0.20, "rest"),
    (0.40, "low_arousal_idle_period"),
    (0.70, "reading"),
]
_DEFAULT_ACTIVITY = "task_completion"


def _select_activity(energy: float) -> str:
    for threshold, label in _ACTIVITY_TABLE:
        if energy < threshold:
            return label
    return _DEFAULT_ACTIVITY


# ── Routine event templates per activity ─────────────────────────────────────
_ROUTINE_TEMPLATES: Dict[str, str] = {
    "rest":                  "Resting quietly, letting the mind settle.",
    "low_arousal_idle_period": "Spending some time in low-stimulation idle.",
    "reading":               "Reading and following a thread of curiosity.",
    "task_completion":       "Working through something that requires focus.",
    "conversation":          "Having a conversation with someone.",
    "social_activity":       "Spending time in a social context.",
    "sleep":                 "Sleeping and recovering.",
    "idle":                  "Passing time without a particular focus.",
}


def activity_transition(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """9. ACTIVITY_TRANSITION — select activity based on energy level.

    Writes to activity.current_activity (SELF / ActivitySelector).
    """
    new_activity = _select_activity(state.affect.energy)
    state.activity.current_activity = new_activity
    event["_new_activity"] = new_activity
    pending_writes.append({"field_path": "activity.current_activity", "author_module": "ActivitySelector"})


def routine_event(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """10. ROUTINE_EVENT — generate a routine EpisodicEvent from current activity.

    The record is appended to event['_pending_episodic'] and optionally to
    the injected episodic store (event['_store']).
    """
    activity = event.get("_new_activity", state.activity.current_activity)
    text = _ROUTINE_TEMPLATES.get(activity, f"Engaged in {activity}.")
    now = datetime.now(timezone.utc).isoformat()
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "created_at": now,
        "cycle_id": event.get("_cycle_id", ""),
        "author_module": "Orchestrator",
        "event_text": text,
        "importance": 0.25,
        "decay_factor": 1.0,
        "lifecycle_state": "active",
        "record_type": "routine_event",
        "activity": activity,
    }

    store = event.get("_store")
    if store is not None:
        _try_store_append_raw(store, record, state, event)

    event.setdefault("_pending_episodic", []).append(record)
    pending_writes.append({"field_path": "episodic_log", "author_module": "Orchestrator"})


def desire_generation(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """11. DESIRE_GENERATION — desire generation + crystallization + persistence.

    Steps:
    1. Age and expire persisted desires from previous slow ticks
    2. Generate new desires for drives above impulse_threshold
    3. Check crystallization on aged desires → produce goal proposals
    4. Accept valid proposals into goals list
    5. Persist high-urgency new desires for next slow tick
    6. Set state.active_desires (EPH)
    """
    # 1. Age and expire persisted desires
    aged = _drive_module.age_and_expire_desires(state.persisted_desires)

    # 2. Generate new desires
    new_desires = _drive_module.generate_all_desires(
        drives=state.drives,
        tick_counter=state.tick_counter,
    )
    state.active_desires = new_desires
    event["_desires_generated"] = len(new_desires)

    # 3. Crystallization check on aged desires
    proposals = _drive_module.check_crystallization(
        persisted_desires=aged,
        current_goals=state.goals,
    )
    event["_proposals"] = proposals
    event["_desires_crystallized"] = len(proposals)

    # 4. Accept proposals → add to goals
    for proposal in proposals:
        new_goal = _goal_system.accept_proposal(proposal, state.goals)
        if new_goal is not None:
            state.goals = list(state.goals) + [new_goal]

    if proposals:
        pending_writes.append({"field_path": "goals", "author_module": "GoalSystem"})

    # 5. Persist high-urgency new desires
    state.persisted_desires = _drive_module.persist_new_desires(
        active_desires=new_desires,
        persisted_desires=aged,
    )
    pending_writes.append({"field_path": "persisted_desires", "author_module": "DriveModule"})
    pending_writes.append({"field_path": "active_desires",    "author_module": "DriveModule"})


# ── helpers ───────────────────────────────────────────────────────────────────

def _try_store_append_raw(store: Any, record: Dict, state: AgentState, event: Dict) -> None:
    """Attempt to append a routine event record to an EpisodicStore."""
    try:
        from ...store.episodic_store import EpisodicStore
        from ...schema.records import EpisodicEvent, RecordMeta, AffectSnapshot, DriveSnapshot
        if not isinstance(store, EpisodicStore):
            return
        meta = RecordMeta(
            id=record["id"],
            created_at=record["created_at"],
            source_type="synthetic",
            source_ref=f"tick:{state.tick_counter}",
            mutability_class="SELF",
            lifecycle_state="active",
        )
        ep = EpisodicEvent(
            meta=meta,
            when=record["created_at"],
            event_text=record["event_text"],
            importance=record["importance"],
            affect_snapshot=AffectSnapshot(
                valence=state.affect.valence,
                arousal=state.affect.arousal,
                stress=state.affect.stress,
            ),
            drive_snapshot=DriveSnapshot(
                social_need=state.drives.social_need,
                mastery_need=state.drives.mastery_need,
                rest_need=state.drives.rest_need,
                curiosity=state.drives.curiosity,
            ),
        )
        store.append(ep, cycle_id=event.get("_cycle_id", ""), author_module="Orchestrator")
    except Exception:
        pass
