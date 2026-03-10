"""
CP-6: P95 context-build latency benchmark.

Non-functional target: context build (memory retrieval + salience + context
packaging) must complete in < 250 ms at P95 across 50 repeated calls,
excluding any LLM invocation.

Reference: architecture.md §7 — non-functional targets
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import pytest

from src.engine.cycles.interaction import (
    build_context_package,
    retrieve_memory_candidates,
    salience_competition,
)
from src.engine.retrieval import load_retrieval_limits
from src.schema.state import AgentState, AttentionState


def _make_memory_records(n: int) -> List[Dict[str, Any]]:
    """Generate n synthetic memory record dicts for benchmarking."""
    return [
        {
            "id": f"mem-{i:04d}",
            "event_text": f"Memory event number {i}.",
            "importance": round(0.1 + (i % 10) * 0.09, 2),
            "recency_score": round(1.0 - i / (n + 1), 4),
            "similarity_score": round((i % 7) / 7.0, 4),
            "self_relevance_score": round((i % 5) / 5.0, 4),
        }
        for i in range(n)
    ]


def _run_context_build_pipeline(state: AgentState, records: List[Dict[str, Any]]) -> None:
    """Run the three deterministic interaction steps: C → D → F."""
    event: Dict[str, Any] = {
        "message": "Hello, how are you today?",
        "memory_records": records,
    }
    pending: List[Dict[str, str]] = []
    retrieve_memory_candidates(state, event, pending)
    salience_competition(state, event, pending)
    build_context_package(state, event, pending)


@pytest.fixture
def bench_state() -> AgentState:
    """Minimal AgentState with a cleared attention buffer for benchmarking."""
    state = AgentState()
    state.attention = AttentionState()
    return state


@pytest.fixture
def bench_records() -> List[Dict[str, Any]]:
    """20 memory records — matches default candidate_limit."""
    limits = load_retrieval_limits()
    return _make_memory_records(int(limits["candidate_limit"]))


class TestContextBuildLatency:
    """P95 latency for context build must be < 250 ms."""

    N_SAMPLES = 50
    P95_LIMIT_MS = 250.0

    def test_p95_context_build_under_250ms(
        self, bench_state: AgentState, bench_records: List[Dict[str, Any]]
    ) -> None:
        """50-sample P95 for retrieve→salience→context_package must be < 250 ms."""
        durations_ms: List[float] = []

        for _ in range(self.N_SAMPLES):
            # Reset salience buffer each iteration so state doesn't accumulate
            bench_state.attention = AttentionState()
            t0 = time.perf_counter()
            _run_context_build_pipeline(bench_state, bench_records)
            t1 = time.perf_counter()
            durations_ms.append((t1 - t0) * 1000)

        durations_ms.sort()
        p95_index = int(self.N_SAMPLES * 0.95) - 1
        p95_ms = durations_ms[p95_index]

        assert p95_ms < self.P95_LIMIT_MS, (
            f"P95 context-build latency {p95_ms:.2f} ms exceeds {self.P95_LIMIT_MS} ms limit. "
            f"min={durations_ms[0]:.2f} ms, max={durations_ms[-1]:.2f} ms, "
            f"mean={sum(durations_ms) / len(durations_ms):.2f} ms"
        )

    def test_mean_context_build_under_50ms(
        self, bench_state: AgentState, bench_records: List[Dict[str, Any]]
    ) -> None:
        """Mean context build should be well under 50 ms for baseline confidence."""
        durations_ms: List[float] = []

        for _ in range(self.N_SAMPLES):
            bench_state.attention = AttentionState()
            t0 = time.perf_counter()
            _run_context_build_pipeline(bench_state, bench_records)
            t1 = time.perf_counter()
            durations_ms.append((t1 - t0) * 1000)

        mean_ms = sum(durations_ms) / len(durations_ms)

        assert mean_ms < 50.0, (
            f"Mean context-build latency {mean_ms:.2f} ms is unexpectedly high. "
            f"P95={sorted(durations_ms)[int(self.N_SAMPLES * 0.95) - 1]:.2f} ms"
        )
