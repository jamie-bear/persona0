"""Hybrid memory retrieval helpers for interaction cycles."""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict, Iterable, List

from .modules._config import load_config_section

from .telemetry import default_telemetry, telemetry_labels


@dataclass(frozen=True)
class RetrievalWeights:
    similarity: float
    recency: float
    importance: float
    self_relevance: float


def _load_retrieval_config() -> Dict[str, Any]:
    return dict(load_config_section("retrieval"))


def load_weights() -> RetrievalWeights:
    retrieval_cfg = _load_retrieval_config()
    return RetrievalWeights(
        similarity=float(retrieval_cfg.get("semantic_similarity_weight", 0.30)),
        recency=float(retrieval_cfg.get("recency_weight", 0.30)),
        importance=float(retrieval_cfg.get("importance_weight", 0.25)),
        # Prefer canonical self_relevance_weight; fall back to legacy goal_relevance_weight.
        self_relevance=float(
            retrieval_cfg.get(
                "self_relevance_weight",
                retrieval_cfg.get("goal_relevance_weight", 0.15),
            )
        ),
    )


def load_retrieval_limits() -> Dict[str, float]:
    retrieval_cfg = _load_retrieval_config()
    return {
        "candidate_limit": int(retrieval_cfg.get("candidate_limit", 20)),
        "salience_buffer_capacity": int(retrieval_cfg.get("salience_buffer_capacity", 5)),
        "min_importance_threshold": float(retrieval_cfg.get("min_importance_threshold", 0.15)),
    }


def rank_memory_candidates(memory_records: Iterable[Dict[str, Any]], top_k: int | None = None) -> List[Dict[str, Any]]:
    """Rank memory records by weighted hybrid score and return top-k with explainability."""
    start = time.monotonic()
    limits = load_retrieval_limits()
    weights = load_weights()
    limit = top_k if top_k is not None else int(limits["candidate_limit"])
    min_importance = float(limits["min_importance_threshold"])

    ranked: List[Dict[str, Any]] = []
    for record in memory_records:
        importance = float(record.get("importance", 0.0))
        if importance < min_importance:
            continue

        similarity = float(record.get("similarity", 0.0))
        recency = float(record.get("recency", 0.0))
        # Prefer canonical self_relevance per record; retain goal_relevance for backward compatibility.
        self_relevance = float(record.get("self_relevance", record.get("goal_relevance", 0.0)))

        score = (
            weights.similarity * similarity
            + weights.recency * recency
            + weights.importance * importance
            + weights.self_relevance * self_relevance
        )
        ranked.append(
            {
                **record,
                "hybrid_score": score,
                "why_selected": {
                    "score_components": {
                        "similarity": similarity,
                        "recency": recency,
                        "importance": importance,
                        "self_relevance": self_relevance,
                    },
                    "weights": {
                        "similarity": weights.similarity,
                        "recency": weights.recency,
                        "importance": weights.importance,
                        "self_relevance": weights.self_relevance,
                    },
                    "hybrid_score": score,
                },
            }
        )

    ranked.sort(key=lambda r: (-r["hybrid_score"], str(r.get("id", ""))))
    selected = ranked[:limit]
    default_telemetry.observe_ms(
        "retrieval_latency_ms",
        (time.monotonic() - start) * 1000.0,
        telemetry_labels({"stage": "rank"}),
    )
    default_telemetry.increment("retrieval_calls_total")
    return selected
