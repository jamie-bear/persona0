"""
Cycle log writer — structured per-cycle observability log.

Reference: cognitive_loop.md §6 (cycle log schema)
CP-1 requirement: every cycle emits before_state_hash and field deltas.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schema.state import AgentState


def hash_state(state: AgentState) -> str:
    """Deterministic SHA-256 hash of the agent state.

    Canonicalised via Pydantic's model_dump_json with sort_keys equivalent.
    Same state always produces the same hash — used for replay verification.
    """
    canonical = state.model_dump_json()
    # Sort keys for determinism across Python versions
    canonical_sorted = json.dumps(json.loads(canonical), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical_sorted.encode("utf-8")).hexdigest()


def compute_delta(before: AgentState, after: AgentState) -> Dict[str, Any]:
    """Return a minimal delta dict of fields that changed between two states.

    Only includes fields whose serialised values differ.
    """
    before_dict = json.loads(before.model_dump_json())
    after_dict = json.loads(after.model_dump_json())

    delta: Dict[str, Any] = {}
    for key in after_dict:
        if after_dict[key] != before_dict.get(key):
            delta[key] = {"before": before_dict.get(key), "after": after_dict[key]}
    return delta


@dataclass
class CycleLogEntry:
    """One entry in the cycle log.

    Reference: cognitive_loop.md §6
    """

    cycle_id: str
    cycle_type: str
    """interaction | fast | slow | macro"""

    timestamp: str
    """ISO8601 UTC timestamp at cycle start."""

    before_state_hash: str
    after_state_hash: str
    delta: Dict[str, Any] = field(default_factory=dict)
    modules_executed: List[str] = field(default_factory=list)
    selected_memories: List[str] = field(default_factory=list)
    dominant_goal: Optional[str] = None
    affect_delta: Dict[str, float] = field(default_factory=dict)
    drive_delta: Dict[str, float] = field(default_factory=dict)
    desires_generated: int = 0
    desires_crystallized: int = 0
    write_count: int = 0
    rollback: bool = False
    rollback_reason: Optional[str] = None
    duration_ms: int = 0

    def to_jsonl(self) -> str:
        """Serialize to a single JSONL line."""
        return json.dumps(self.__dict__, sort_keys=True, ensure_ascii=True)


class CycleLogger:
    """Append-only JSONL cycle log writer.

    CP-1 requirement: produces structured log with before/after hash per cycle.
    """

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: CycleLogEntry) -> None:
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(entry.to_jsonl() + "\n")

    def read_all(self) -> List[CycleLogEntry]:
        if not self._log_path.exists():
            return []
        entries = []
        with self._log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(CycleLogEntry(**data))
        return entries
