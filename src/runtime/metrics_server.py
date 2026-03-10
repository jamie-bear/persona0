"""Minimal metrics exporter endpoint for telemetry and SLO alerts."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Tuple

from ..engine.telemetry import default_telemetry


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/metrics":
            payload = default_telemetry.format_prometheus().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/alerts":
            alerts = default_telemetry.evaluate_alerts()
            body = ("[]" if not alerts else str(alerts)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def build_metrics_server(host: str = "0.0.0.0", port: int = 9108) -> Tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer((host, port), _MetricsHandler)
    return server, f"http://{host}:{port}"
