"""In-memory vector store adapter for memory retrieval."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class VectorStore:
    """Simple cosine-similarity vector index with metadata filtering."""

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
