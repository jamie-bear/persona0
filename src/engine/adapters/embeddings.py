"""Deterministic embeddings adapter used for memory indexing and retrieval."""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List

_DEFAULT_DIMENSION = 16
_DEFAULT_MODEL = "deterministic-hash-v1"


def _float_from_digest(chunk: bytes) -> float:
    unsigned = int.from_bytes(chunk, byteorder="big", signed=False)
    return (unsigned / 255.0) * 2.0 - 1.0


def generate_embedding(text: str, *, dimension: int = _DEFAULT_DIMENSION) -> List[float]:
    """Generate a deterministic embedding vector for a text payload."""
    source = (text or "").encode("utf-8")
    vector: List[float] = []
    counter = 0
    while len(vector) < dimension:
        digest = hashlib.sha256(source + f"|{counter}".encode("utf-8")).digest()
        for idx in range(len(digest)):
            if len(vector) >= dimension:
                break
            vector.append(_float_from_digest(digest[idx: idx + 1]))
        counter += 1

    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return [0.0 for _ in range(dimension)]
    return [v / norm for v in vector]


def build_embedding_metadata(
    *,
    text: str,
    vector: List[float],
    model: str = _DEFAULT_MODEL,
    content_type: str = "memory_record",
) -> Dict[str, Any]:
    """Return compact metadata describing the embedding provenance."""
    checksum = hashlib.sha1((text or "").encode("utf-8")).hexdigest()
    return {
        "model": model,
        "dimension": len(vector),
        "content_sha1": checksum,
        "content_type": content_type,
    }


def embed_text(text: str, *, content_type: str = "memory_record") -> Dict[str, Any]:
    """Convenience wrapper returning both embedding vector and metadata."""
    vector = generate_embedding(text)
    return {
        "vector": vector,
        "metadata": build_embedding_metadata(
            text=text,
            vector=vector,
            content_type=content_type,
        ),
    }
