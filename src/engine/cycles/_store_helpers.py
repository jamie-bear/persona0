"""Shared helpers for appending records to the EpisodicStore.

Extracted from fast_tick._try_store_append and slow_tick._try_store_append_raw
to eliminate duplication.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import NAMESPACE_URL, uuid5

from ...schema.state import AgentState
from ..adapters.embeddings import embed_text
from ..pii_redaction import redact_pii


_CYCLE_ORDER = {
    "interaction": 0,
    "fast_tick": 1,
    "slow_tick": 2,
    "macro": 3,
}


def next_record_sequence_index(event: Dict[str, Any]) -> int:
    """Return the next per-cycle sequence index for episodic record construction."""
    idx = int(event.get("_record_sequence_index", 0))
    event["_record_sequence_index"] = idx + 1
    return idx


def deterministic_record_metadata(
    state: AgentState,
    event: Dict[str, Any],
    *,
    cycle_type: str,
    record_type: str,
    sequence_index: int,
) -> Dict[str, str]:
    """Build deterministic ``id`` + ``created_at`` fields for episodic records.

    ``created_at`` prefers orchestrator-provided ``_logical_timestamp`` when
    available. Otherwise it derives from a fixed UTC epoch plus deterministic
    offsets from ``tick_counter``, ``cycle_type``, and ``sequence_index``.
    """
    logical_ts = event.get("_logical_timestamp")
    created_at_dt = None

    if isinstance(logical_ts, str) and logical_ts:
        try:
            created_at_dt = datetime.fromisoformat(logical_ts.replace("Z", "+00:00"))
            if created_at_dt.tzinfo is None:
                created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            created_at_dt = None

    if created_at_dt is None:
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        cycle_slot = _CYCLE_ORDER.get(cycle_type, 9)
        created_at_dt = base + timedelta(
            minutes=(state.tick_counter * 60) + (cycle_slot * 10),
            seconds=sequence_index,
        )
    else:
        created_at_dt = created_at_dt + timedelta(microseconds=sequence_index)

    created_at = created_at_dt.isoformat()
    identity = (
        f"tick:{state.tick_counter}|cycle:{cycle_type}|"
        f"record:{record_type}|seq:{sequence_index}|ts:{created_at}"
    )
    record_id = str(uuid5(NAMESPACE_URL, identity))
    return {"id": record_id, "created_at": created_at}


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
            context={"embedding": record.get("embedding", {})},
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


def attach_embedding_metadata(record: Dict[str, Any], text: str, *, content_type: str) -> Dict[str, Any]:
    """Attach embedding vector + metadata to a record payload."""
    embedded = embed_text(text, content_type=content_type)
    record["embedding"] = embedded["metadata"]
    return embedded


def upsert_vector_index(event: Dict[str, Any], record: Dict[str, Any], embedded: Dict[str, Any]) -> None:
    """Best-effort vector index upsert when a vector store is injected."""
    vector_store = event.get("_vector_store")
    if vector_store is None:
        return
    try:
        vector_store.upsert(record["id"], embedded["vector"], record)
    except Exception:
        pass
