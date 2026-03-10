from __future__ import annotations

import threading
import urllib.request

from src.engine.contracts import CycleType
from src.engine.cycle_log import CycleLogger
from src.engine.orchestrator import EgoOrchestrator, PolicyViolation
from src.engine.telemetry import default_telemetry
from src.runtime.metrics_server import build_metrics_server
from src.schema.state import AgentState


def _orch(tmp_path):
    default_telemetry.reset()
    logger = CycleLogger(tmp_path / "cycles.jsonl")
    state = AgentState()
    state.persona.name = "Mira"
    return EgoOrchestrator(state, logger), logger


def test_telemetry_emits_success_path_metrics(tmp_path):
    orch, logger = _orch(tmp_path)

    result = orch.run_cycle(
        CycleType.FAST_TICK,
        {"request_id": "req-1", "session_id": "sess-1", "correlation_id": "corr-1"},
    )

    assert result.success
    assert default_telemetry.get_counter("cycle_total") == 1
    assert default_telemetry.get_counter("cycle_rollback_total") == 0
    assert default_telemetry.get_timer_values("cycle_latency_ms", {"cycle_type": "fast", "correlation_id": "corr-1", "request_id": "req-1", "session_id": "sess-1"})

    entries = logger.read_all()
    assert entries[0].correlation_id == "corr-1"
    assert entries[0].request_id == "req-1"
    assert entries[0].session_id == "sess-1"


def test_telemetry_emits_failure_path_metrics(tmp_path):
    orch, logger = _orch(tmp_path)

    def fail_step(state, event, pending_writes):
        raise PolicyViolation("forced")

    orch.register_step("world_ingest", fail_step)
    result = orch.run_cycle(CycleType.FAST_TICK, {"correlation_id": "corr-fail"})

    assert not result.success
    assert default_telemetry.get_counter("cycle_total") == 1
    assert default_telemetry.get_counter("cycle_rollback_total") == 1
    entries = logger.read_all()
    assert entries[0].rollback
    assert entries[0].correlation_id == "corr-fail"


def test_metrics_exporter_and_alerts_endpoint(tmp_path):
    default_telemetry.reset()
    for _ in range(6):
        default_telemetry.increment("cycle_total")
    for _ in range(2):
        default_telemetry.increment("cycle_rollback_total")
    for _ in range(2):
        default_telemetry.increment("policy_block_total")
    for value in [700, 800, 750, 900, 650, 810]:
        default_telemetry.observe_ms("cycle_latency_ms", value)

    server, _ = build_metrics_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        metrics = urllib.request.urlopen(f"{base}/metrics").read().decode("utf-8")
        alerts = urllib.request.urlopen(f"{base}/alerts").read().decode("utf-8")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert "cycle_total" in metrics
    assert "cycle_latency_ms_avg" in metrics
    assert "rollback_spike" in alerts
    assert "latency_regression" in alerts
    assert "policy_block_anomaly" in alerts
