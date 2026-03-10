"""Telemetry primitives for counters, timings, trace context, and SLO alerts."""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from statistics import mean
from typing import DefaultDict, Dict, Iterable, Iterator, List, Optional, Tuple

LabelSet = Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class TraceContext:
    correlation_id: str
    request_id: Optional[str] = None
    session_id: Optional[str] = None


_trace_ctx: ContextVar[Optional[TraceContext]] = ContextVar("trace_context", default=None)


def _labelset(labels: Optional[Dict[str, str]] = None) -> LabelSet:
    if not labels:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


class TelemetryCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: DefaultDict[str, DefaultDict[LabelSet, float]] = defaultdict(lambda: defaultdict(float))
        self._timers_ms: DefaultDict[str, DefaultDict[LabelSet, List[float]]] = defaultdict(lambda: defaultdict(list))

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timers_ms.clear()

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._counters[name][_labelset(labels)] += value

    def observe_ms(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._timers_ms[name][_labelset(labels)].append(float(duration_ms))

    @contextmanager
    def time_block(self, name: str, labels: Optional[Dict[str, str]] = None) -> Iterator[None]:
        start = time.monotonic()
        try:
            yield
        finally:
            self.observe_ms(name, (time.monotonic() - start) * 1000.0, labels)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        with self._lock:
            return self._counters.get(name, {}).get(_labelset(labels), 0.0)

    def get_timer_values(self, name: str, labels: Optional[Dict[str, str]] = None) -> List[float]:
        with self._lock:
            return list(self._timers_ms.get(name, {}).get(_labelset(labels), []))

    def format_prometheus(self) -> str:
        lines: List[str] = []
        with self._lock:
            for metric_name in sorted(self._counters.keys()):
                for labels, value in sorted(self._counters[metric_name].items()):
                    lines.append(f"{metric_name}{_format_labels(labels)} {value}")
            for metric_name in sorted(self._timers_ms.keys()):
                for labels, values in sorted(self._timers_ms[metric_name].items()):
                    if not values:
                        continue
                    lines.append(f"{metric_name}_count{_format_labels(labels)} {len(values)}")
                    lines.append(f"{metric_name}_sum{_format_labels(labels)} {sum(values):.3f}")
                    lines.append(f"{metric_name}_avg{_format_labels(labels)} {mean(values):.3f}")
                    lines.append(f"{metric_name}_max{_format_labels(labels)} {max(values):.3f}")
        return "\n".join(lines) + ("\n" if lines else "")

    def evaluate_alerts(self) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        total_cycles = self.get_counter("cycle_total")
        rollbacks = self.get_counter("cycle_rollback_total")
        policy_blocks = self.get_counter("policy_block_total")
        latencies = self.get_timer_values("cycle_latency_ms")

        if total_cycles >= 5 and total_cycles > 0 and (rollbacks / total_cycles) > 0.2:
            alerts.append({"name": "rollback_spike", "severity": "critical", "value": f"{rollbacks/total_cycles:.2%}"})
        if len(latencies) >= 5 and (sum(latencies) / len(latencies)) > 500.0:
            alerts.append({"name": "latency_regression", "severity": "warning", "value": f"{sum(latencies)/len(latencies):.1f}ms"})
        if total_cycles >= 5 and total_cycles > 0 and (policy_blocks / total_cycles) > 0.1:
            alerts.append({"name": "policy_block_anomaly", "severity": "warning", "value": f"{policy_blocks/total_cycles:.2%}"})
        return alerts


def _format_labels(labels: LabelSet) -> str:
    if not labels:
        return ""
    values = ",".join(f'{k}="{v}"' for k, v in labels)
    return "{" + values + "}"


def telemetry_labels(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    ctx = get_trace_context()
    if ctx is not None:
        labels["correlation_id"] = ctx.correlation_id
        if ctx.request_id:
            labels["request_id"] = ctx.request_id
        if ctx.session_id:
            labels["session_id"] = ctx.session_id
    if extra:
        labels.update(extra)
    return labels


def set_trace_context(trace: TraceContext) -> None:
    _trace_ctx.set(trace)


def clear_trace_context() -> None:
    _trace_ctx.set(None)


def get_trace_context() -> Optional[TraceContext]:
    return _trace_ctx.get()


def ensure_trace_context(event: Dict[str, object]) -> TraceContext:
    correlation_id = str(event.get("correlation_id") or uuid.uuid4())
    request_id = str(event["request_id"]) if event.get("request_id") is not None else None
    session_id = str(event["session_id"]) if event.get("session_id") is not None else None
    event["correlation_id"] = correlation_id
    if request_id is not None:
        event["request_id"] = request_id
    if session_id is not None:
        event["session_id"] = session_id
    trace = TraceContext(correlation_id=correlation_id, request_id=request_id, session_id=session_id)
    set_trace_context(trace)
    return trace


default_telemetry = TelemetryCollector()
