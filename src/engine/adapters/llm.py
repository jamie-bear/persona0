"""LLM adapter interface for response generation and event appraisal."""

from __future__ import annotations

from typing import Any, Dict, List

from ..modules._config import load_config_section
from ...schema.state import AgentState


class AdapterTimeoutError(RuntimeError):
    """Raised when provider requests exceed configured timeout."""


class AdapterCallError(RuntimeError):
    """Raised when provider call fails after retries."""


def generate_response(context_package: Dict[str, Any], state: AgentState) -> str:
    """Generate a model response using configured provider settings."""
    cfg = _adapter_config()
    payload = {
        "context_package": context_package,
        "persona_name": state.persona.name,
    }
    raw = _call_with_retry("response", payload, cfg)
    if not isinstance(raw, str) or not raw.strip():
        raise AdapterCallError("response adapter returned empty/non-string output")
    return raw.strip()


def appraise_events(
    activity_events: List[Dict[str, Any]], state: AgentState
) -> List[Dict[str, Any]]:
    """Generate structured appraisal signals for fast-tick emotional updates."""
    cfg = _adapter_config()
    payload = {
        "activity_events": activity_events,
        "active_goal_labels": [g.label for g in state.goals if g.status == "active"],
    }
    raw = _call_with_retry("appraise", payload, cfg)
    return validate_appraisal_results(raw)


def _adapter_config() -> Dict[str, Any]:
    cfg = dict(load_config_section("llm_adapter"))
    cfg.setdefault("provider", "mock")
    cfg.setdefault("model", "stub-v1")
    cfg.setdefault("timeout_seconds", 2)
    cfg.setdefault("retries", 0)
    return cfg


def _call_with_retry(operation: str, payload: Dict[str, Any], cfg: Dict[str, Any]) -> Any:
    retries = max(0, int(cfg.get("retries", 0)))
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return _call_provider(operation, payload, cfg)
        except AdapterTimeoutError as exc:
            last_error = exc
            if attempt >= retries:
                raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            last_error = exc
            if attempt >= retries:
                raise AdapterCallError(str(exc)) from exc

    raise AdapterCallError(str(last_error) if last_error else "adapter call failed")


def _call_provider(operation: str, payload: Dict[str, Any], cfg: Dict[str, Any]) -> Any:
    """Provider dispatch.

    Current default provider is `mock` for deterministic local tests.
    """
    provider = str(cfg.get("provider", "mock"))

    if provider != "mock":
        raise AdapterCallError(f"Unsupported llm_adapter.provider={provider!r}")

    if operation == "response":
        context = payload.get("context_package", {})
        mock = context.get("mock_response")
        if isinstance(mock, str):
            return mock
        return "I can help with that. Could you share one more detail so I can be precise?"

    if operation == "appraise":
        events = payload.get("activity_events", [])
        return [
            {
                "event_id": str(ev.get("id", f"evt-{idx}")),
                "goal_congruence": 0.25,
                "threat": 0.0,
                "arousal_cue": 0.1,
                "rationale": "Routine activity appears aligned with current goals.",
            }
            for idx, ev in enumerate(events)
        ]

    raise AdapterCallError(f"Unsupported adapter operation: {operation}")


def validate_appraisal_results(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        raise AdapterCallError("appraise_events adapter returned non-list output")

    validated: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        validated.append(
            {
                "event_id": str(item.get("event_id", f"evt-{idx}")),
                "goal_congruence": _to_unit_float(item.get("goal_congruence", 0.0)),
                "threat": _to_unit_float(item.get("threat", 0.0)),
                "arousal_cue": _to_unit_float(item.get("arousal_cue", 0.0)),
                "rationale": str(item.get("rationale", "")).strip(),
            }
        )
    return validated


def _to_unit_float(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(-1.0, min(1.0, numeric))
