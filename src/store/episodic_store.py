"""
Episodic event store backed by SQLite.

Reference: self_editability_policy.md §3.2 (memory stores: append-only)
CP-1: records are never modified or deleted (except decay_factor)
CP-5: lifecycle transitions (active → cooling → archived → deleted) and
      user-initiated forget/delete operations added.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schema.records import EpisodicEvent, RecordMeta


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS episodic_log (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    author_module TEXT NOT NULL,
    event_text TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    decay_factor REAL NOT NULL DEFAULT 1.0,
    lifecycle_state TEXT NOT NULL DEFAULT 'active',
    payload JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_created_at ON episodic_log(created_at);
CREATE INDEX IF NOT EXISTS idx_lifecycle ON episodic_log(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_importance ON episodic_log(importance);
"""


_VALID_LIFECYCLE_STATES = {"active", "cooling", "archived", "deleted"}
_VALID_TRANSITIONS = {
    "active": {"cooling", "deleted"},
    "cooling": {"archived", "active", "deleted"},
    "archived": {"deleted"},
    "deleted": set(),  # terminal state
}


class EpisodicStore:
    """SQLite-backed episodic event store with lifecycle management.

    Invariants:
    - Records are never modified after insertion (except decay_factor and lifecycle_state)
    - lifecycle_state transitions follow: active → cooling → archived → deleted
    - Deleted records are soft-deleted (lifecycle_state = 'deleted'), not removed from DB
    - All writes carry author_module and cycle_id for provenance
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CREATE_TABLE)
        self._conn.commit()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, event: EpisodicEvent, cycle_id: str, author_module: str) -> str:
        """Append a new episodic event. Returns the record id.

        Raises ValueError if a record with the same id already exists
        (prevents accidental re-insertion of the same record).
        """
        payload = event.model_dump_json()
        try:
            self._conn.execute(
                """
                INSERT INTO episodic_log
                    (id, created_at, cycle_id, author_module, event_text,
                     importance, decay_factor, lifecycle_state, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.meta.id,
                    event.meta.created_at,
                    cycle_id,
                    author_module,
                    event.event_text,
                    event.importance,
                    event.decay_factor,
                    event.meta.lifecycle_state,
                    payload,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"EpisodicStore: record '{event.meta.id}' already exists"
            ) from exc
        return event.meta.id

    def update_decay_factor(self, record_id: str, new_decay_factor: float) -> None:
        """Update decay_factor for a record (the only mutable field post-creation)."""
        self._conn.execute(
            "UPDATE episodic_log SET decay_factor = ? WHERE id = ?",
            (new_decay_factor, record_id),
        )
        self._conn.commit()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def transition_lifecycle(
        self, record_id: str, new_state: str
    ) -> bool:
        """Transition a record's lifecycle state.

        Valid transitions: active→cooling, cooling→archived, any→deleted.
        Returns True if the transition was applied, False if the record was
        not found or the transition is invalid.

        Raises ValueError for invalid target states.
        """
        if new_state not in _VALID_LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle state: '{new_state}'")

        row = self._conn.execute(
            "SELECT lifecycle_state FROM episodic_log WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return False

        current = row["lifecycle_state"]
        if new_state not in _VALID_TRANSITIONS.get(current, set()):
            return False

        self._conn.execute(
            "UPDATE episodic_log SET lifecycle_state = ? WHERE id = ?",
            (new_state, record_id),
        )
        self._conn.commit()
        return True

    def cool_records(
        self,
        max_records: int = 100,
        importance_threshold: float = 0.15,
        decay_threshold: float = 0.10,
    ) -> List[str]:
        """Move low-importance, low-decay active records to 'cooling' state.

        Returns list of record IDs that were transitioned.
        Reference: config/defaults.yaml memory.decay_cooling_threshold,
                   memory.importance_cooling_threshold
        """
        rows = self._conn.execute(
            """
            SELECT id FROM episodic_log
            WHERE lifecycle_state = 'active'
              AND importance < ?
              AND decay_factor < ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (importance_threshold, decay_threshold, max_records),
        ).fetchall()

        cooled = []
        for row in rows:
            rid = row["id"]
            if self.transition_lifecycle(rid, "cooling"):
                cooled.append(rid)
        return cooled

    def archive_cooled(self, max_records: int = 50) -> List[str]:
        """Move cooling records to 'archived' state.

        Returns list of record IDs that were transitioned.
        Reference: config/defaults.yaml memory.max_records_archived_per_cycle
        """
        rows = self._conn.execute(
            """
            SELECT id FROM episodic_log
            WHERE lifecycle_state = 'cooling'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (max_records,),
        ).fetchall()

        archived = []
        for row in rows:
            rid = row["id"]
            if self.transition_lifecycle(rid, "archived"):
                archived.append(rid)
        return archived

    def forget(self, record_id: str) -> bool:
        """User-initiated forget: transition any non-deleted record to 'deleted'.

        This is a soft-delete; the record remains in the DB but is excluded
        from all queries. Returns True if successful.

        Reference: ego_data.md §6 (user deletion rights)
        """
        row = self._conn.execute(
            "SELECT lifecycle_state FROM episodic_log WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return False

        current = row["lifecycle_state"]
        if current == "deleted":
            return False

        # User forget bypasses normal transition rules — any state → deleted
        self._conn.execute(
            "UPDATE episodic_log SET lifecycle_state = 'deleted' WHERE id = ?",
            (record_id,),
        )
        self._conn.commit()
        return True

    def forget_bulk(self, record_ids: List[str]) -> int:
        """Forget multiple records at once. Returns count of records deleted."""
        count = 0
        for rid in record_ids:
            if self.forget(rid):
                count += 1
        return count

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        lifecycle_state: str = "active",
        min_importance: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return raw payload dicts for matching records.

        Ordered by created_at DESC (most recent first).
        """
        rows = self._conn.execute(
            """
            SELECT payload FROM episodic_log
            WHERE lifecycle_state = ?
              AND importance >= ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (lifecycle_state, min_importance, limit, offset),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT payload FROM episodic_log WHERE id = ?", (record_id,)
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def count(self, lifecycle_state: str = "active") -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM episodic_log WHERE lifecycle_state = ?",
            (lifecycle_state,),
        ).fetchone()
        return row[0]

    def close(self) -> None:
        self._conn.close()
