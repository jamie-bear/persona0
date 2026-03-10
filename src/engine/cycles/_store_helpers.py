"""Shared helpers for appending records to the EpisodicStore.

Extracted from fast_tick._try_store_append and slow_tick._try_store_append_raw
to eliminate duplication.
"""
from __future__ import annotations

from typing import Any, Dict

from ...schema.state import AgentState
from ..pii_redaction import redact_pii


def try_store_append(store: Any, record: Dict, state: AgentState, event: Dict) -> None:
    """Attempt to append a raw record dict to an EpisodicStore.

    Constructs the required EpisodicEvent + RecordMeta from the raw dict and
    current agent state. Applies PII redaction before persist (CP-5).
    Silently skips on failure (non-critical path).
    """
    try:
        from ...store.episodic_store import EpisodicStore
        from ...schema.records import EpisodicEvent, RecordMeta, AffectSnapshot, DriveSnapshot

        if not isinstance(store, EpisodicStore):
            return

        # CP-5: PII redaction before long-term commit
        event_text = record["event_text"]
        redaction = redact_pii(event_text)
        clean_text = redaction.redacted_text

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
            event_text=clean_text,
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
