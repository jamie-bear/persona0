"""Vector store adapters for memory retrieval.

Provides two implementations:
- VectorStore: In-memory cosine-similarity index (dev/test)
- PgVectorStore: PostgreSQL + pgvector backend (production)

The production store supports batch upserts, hybrid search with metadata
filtering, and index lifecycle management.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class VectorStore:
    """Simple cosine-similarity vector index with metadata filtering.

    Suitable for development, testing, and small deployments.
    """

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}

    def upsert(self, record_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self._records[str(record_id)] = {
            "record_id": str(record_id),
            "vector": list(vector),
            "metadata": dict(metadata),
        }

    def query(
        self,
        vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []
        for rec in self._records.values():
            if not self._matches_filters(rec["metadata"], filters):
                continue
            similarity = self._cosine_similarity(vector, rec["vector"])
            scored.append(
                {
                    "id": rec["record_id"],
                    "similarity": similarity,
                    "metadata": rec["metadata"],
                }
            )

        scored.sort(key=lambda item: (-float(item["similarity"]), str(item["id"])))
        return scored[: max(int(top_k), 0)]

    def batch_upsert(
        self, records: Sequence[Dict[str, Any]], batch_size: int = 100
    ) -> int:
        """Upsert multiple records. Returns count of records upserted."""
        count = 0
        for rec in records:
            self.upsert(
                record_id=str(rec["record_id"]),
                vector=rec["vector"],
                metadata=rec.get("metadata", {}),
            )
            count += 1
        return count

    @staticmethod
    def _matches_filters(metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        if not filters:
            return True
        for key, expected in filters.items():
            if metadata.get(key) != expected:
                return False
        return True

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        a_norm = math.sqrt(sum(float(x) * float(x) for x in a))
        b_norm = math.sqrt(sum(float(y) * float(y) for y in b))
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return dot / (a_norm * b_norm)


class PgVectorStore:
    """PostgreSQL + pgvector production vector store.

    Requires: pip install psycopg[binary] pgvector

    Features:
    - Persistent vector storage with pgvector extension
    - Batch upserts with configurable batch sizes
    - Hybrid search: cosine similarity + metadata filters
    - Index lifecycle management (create, reindex, vacuum)

    Connection is configured via:
    - PERSONA0_PGVECTOR_DSN environment variable, or
    - Explicit dsn parameter
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        table_name: str = "persona0_vectors",
        dimension: int = 16,
    ) -> None:
        self._dsn = dsn or os.environ.get(
            "PERSONA0_PGVECTOR_DSN",
            "postgresql://localhost:5432/persona0",
        )
        self._table = table_name
        self._dimension = dimension
        self._conn: Any = None

    def _get_conn(self) -> Any:
        if self._conn is not None and not self._conn.closed:
            return self._conn

        try:
            import psycopg  # type: ignore[import-untyped]
            from pgvector.psycopg import register_vector  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "psycopg and pgvector are required for PgVectorStore. "
                "Install with: pip install 'psycopg[binary]' pgvector"
            ) from exc

        self._conn = psycopg.connect(self._dsn, autocommit=True)
        register_vector(self._conn)
        return self._conn

    def ensure_schema(self) -> None:
        """Create the vector table and index if they don't exist."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    record_id TEXT PRIMARY KEY,
                    embedding vector({self._dimension}),
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table}_embedding
                ON {self._table}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table}_metadata
                ON {self._table}
                USING gin (metadata)
            """)

    def upsert(self, record_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._table} (record_id, embedding, metadata, updated_at)
                VALUES (%s, %s::vector, %s::jsonb, now())
                ON CONFLICT (record_id)
                DO UPDATE SET embedding = EXCLUDED.embedding,
                              metadata = EXCLUDED.metadata,
                              updated_at = now()
                """,
                (str(record_id), vector, _json_dumps(metadata)),
            )

    def batch_upsert(
        self, records: Sequence[Dict[str, Any]], batch_size: int = 100
    ) -> int:
        """Upsert records in batches. Returns total count upserted."""
        conn = self._get_conn()
        total = 0
        batch: list[tuple] = []

        for rec in records:
            batch.append((
                str(rec["record_id"]),
                rec["vector"],
                _json_dumps(rec.get("metadata", {})),
            ))
            if len(batch) >= batch_size:
                self._flush_batch(conn, batch)
                total += len(batch)
                batch = []

        if batch:
            self._flush_batch(conn, batch)
            total += len(batch)

        logger.info("Batch upserted %d vectors into %s", total, self._table)
        return total

    def _flush_batch(self, conn: Any, batch: list[tuple]) -> None:
        with conn.cursor() as cur:
            cur.executemany(
                f"""
                INSERT INTO {self._table} (record_id, embedding, metadata, updated_at)
                VALUES (%s, %s::vector, %s::jsonb, now())
                ON CONFLICT (record_id)
                DO UPDATE SET embedding = EXCLUDED.embedding,
                              metadata = EXCLUDED.metadata,
                              updated_at = now()
                """,
                batch,
            )

    def query(
        self,
        vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        where_clause, params = self._build_filter_clause(filters)

        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT record_id,
                       1 - (embedding <=> %s::vector) AS similarity,
                       metadata
                FROM {self._table}
                {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [vector, *params, vector, max(int(top_k), 0)],
            )
            results = []
            for row in cur.fetchall():
                results.append({
                    "id": row[0],
                    "similarity": float(row[1]),
                    "metadata": row[2] if isinstance(row[2], dict) else {},
                })
            return results

    @staticmethod
    def _build_filter_clause(
        filters: Optional[Dict[str, Any]],
    ) -> tuple[str, list]:
        if not filters:
            return "", []
        conditions = []
        params: list = []
        for key, value in filters.items():
            conditions.append(f"metadata->>%s = %s")
            params.extend([key, str(value)])
        return "WHERE " + " AND ".join(conditions), params

    # -----------------------------------------------------------------------
    # Index lifecycle management
    # -----------------------------------------------------------------------

    def reindex(self) -> None:
        """Rebuild the IVFFlat index (use after large batch inserts)."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"REINDEX INDEX idx_{self._table}_embedding")
        logger.info("Reindexed %s", self._table)

    def vacuum(self) -> None:
        """Run VACUUM ANALYZE on the vector table."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"VACUUM ANALYZE {self._table}")
        logger.info("Vacuumed %s", self._table)

    def count(self) -> int:
        """Return the number of records in the store."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._table}")
            return cur.fetchone()[0]

    def delete(self, record_id: str) -> bool:
        """Delete a record by ID. Returns True if a row was removed."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self._table} WHERE record_id = %s",
                (str(record_id),),
            )
            return cur.rowcount > 0

    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """Delete records matching metadata filters. Returns count deleted."""
        where_clause, params = self._build_filter_clause(filters)
        if not where_clause:
            return 0
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._table} {where_clause}", params)
            return cur.rowcount

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None


def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)
