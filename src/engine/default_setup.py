"""
Factory for registering all default step implementations with an EgoOrchestrator.

Usage::

    from src.engine.orchestrator import EgoOrchestrator
    from src.engine.default_setup import register_default_steps
    from src.store.episodic_store import EpisodicStore

    store = EpisodicStore(":memory:")
    orchestrator = register_default_steps(EgoOrchestrator(state), store=store)
    result = orchestrator.run_cycle(CycleType.FAST_TICK, {})

Reference: cognitive_loop.md §3 (all cycle step orders defined in contracts.py)
"""
from __future__ import annotations

from typing import Optional

from ..store.episodic_store import EpisodicStore
from .contracts import (
    ACTIVITY_TRANSITION,
    APPRAISE,
    BUILD_CONTEXT_PACKAGE,
    COMMIT_OR_ROLLBACK,
    DESIRE_GENERATION,
    GENERATE_THOUGHT,
    INGEST_TURN,
    LOG_CYCLE,
    RETRIEVE_MEMORY_CANDIDATES,
    ROUTINE_EVENT,
    SALIENCE_COMPETITION,
    SALIENCE_FILTER,
    UPDATE_EMOTION,
    UPDATE_DRIVES,
    UPDATE_GOALS,
    WORLD_INGEST,
    WRITE_MEMORY,
)
from .cycles import fast_tick, slow_tick, interaction
from .orchestrator import EgoOrchestrator


def register_default_steps(
    orchestrator: EgoOrchestrator,
    store: Optional[EpisodicStore] = None,
) -> EgoOrchestrator:
    """Register all behavior-complete step implementations on the orchestrator.

    Steps that remain stubs (LLM-dependent) are registered as no-ops so the
    orchestrator can still call them in order without KeyError.

    Args:
        orchestrator: the EgoOrchestrator instance to configure
        store: optional EpisodicStore; when provided, write_memory and
               routine_event will persist records to it

    Returns:
        the same orchestrator (mutated in-place), for chaining
    """
    # ── Interaction cycle ──────────────────────────────────────────────────────
    orchestrator.register_step(INGEST_TURN, interaction.ingest_turn)
    orchestrator.register_step("parse_intent_affect", interaction.parse_intent_affect)
    orchestrator.register_step(RETRIEVE_MEMORY_CANDIDATES, interaction.retrieve_memory_candidates)
    orchestrator.register_step(SALIENCE_COMPETITION, interaction.salience_competition)
    orchestrator.register_step("appraisal_update", interaction.appraisal_update)
    orchestrator.register_step(BUILD_CONTEXT_PACKAGE, interaction.build_context_package)
    orchestrator.register_step("render_response", interaction.render_response)
    orchestrator.register_step("policy_and_consistency_check", interaction.policy_and_consistency_check)
    orchestrator.register_step(COMMIT_OR_ROLLBACK, interaction.commit_or_rollback)

    # ── Fast tick ──────────────────────────────────────────────────────────────
    orchestrator.register_step(WORLD_INGEST, fast_tick.world_ingest)
    orchestrator.register_step(APPRAISE, fast_tick.appraise)
    orchestrator.register_step(UPDATE_EMOTION, fast_tick.update_emotion)
    orchestrator.register_step(UPDATE_DRIVES, fast_tick.update_drives)
    orchestrator.register_step(GENERATE_THOUGHT, fast_tick.generate_thought)
    orchestrator.register_step(SALIENCE_FILTER, fast_tick.salience_filter)
    orchestrator.register_step(UPDATE_GOALS, fast_tick.update_goals)
    orchestrator.register_step(LOG_CYCLE, fast_tick.log_cycle)

    # write_memory needs optional store injection
    if store is not None:
        def _write_memory_with_store(state, event, pending_writes):
            event.setdefault("_store", store)
            fast_tick.write_memory(state, event, pending_writes)
        orchestrator.register_step(WRITE_MEMORY, _write_memory_with_store)
    else:
        orchestrator.register_step(WRITE_MEMORY, fast_tick.write_memory)

    # ── Slow tick adds ─────────────────────────────────────────────────────────
    orchestrator.register_step(ACTIVITY_TRANSITION, slow_tick.activity_transition)
    orchestrator.register_step(DESIRE_GENERATION, slow_tick.desire_generation)

    if store is not None:
        def _routine_event_with_store(state, event, pending_writes):
            event.setdefault("_store", store)
            slow_tick.routine_event(state, event, pending_writes)
        orchestrator.register_step(ROUTINE_EVENT, _routine_event_with_store)
    else:
        orchestrator.register_step(ROUTINE_EVENT, slow_tick.routine_event)

    return orchestrator
