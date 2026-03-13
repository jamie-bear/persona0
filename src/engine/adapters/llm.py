"""LLM adapter interface for response generation and event appraisal.

Supports providers: mock (default), openai, anthropic.
Production providers require api_key via environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from ..modules._config import load_config_section
from ...schema.state import AgentState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AdapterTimeoutError(RuntimeError):
    """Raised when provider requests exceed configured timeout."""


class AdapterCallError(RuntimeError):
    """Raised when provider call fails after retries."""


class RateLimitError(AdapterCallError):
    """Raised when the provider returns a rate-limit (429) response."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_RATE_LIMIT_RPM = 60
_DEFAULT_STREAMING = False


def _adapter_config() -> Dict[str, Any]:
    cfg = dict(load_config_section("llm_adapter"))
    cfg.setdefault("provider", "mock")
    cfg.setdefault("model", "stub-v1")
    cfg.setdefault("timeout_seconds", 30)
    cfg.setdefault("retries", 3)
    cfg.setdefault("rate_limit_rpm", _DEFAULT_RATE_LIMIT_RPM)
    cfg.setdefault("streaming", _DEFAULT_STREAMING)
    return cfg


# ---------------------------------------------------------------------------
# Rate limiter (token-bucket, per-minute)
# ---------------------------------------------------------------------------

_rate_state: Dict[str, Any] = {"tokens": 0.0, "last_refill": 0.0, "capacity": 0}


def _rate_limit_check(rpm: int) -> None:
    """Block until a request token is available.  Simple token-bucket."""
    now = time.monotonic()
    if _rate_state["capacity"] != rpm:
        # (re)initialise on config change
        _rate_state["tokens"] = float(rpm)
        _rate_state["last_refill"] = now
        _rate_state["capacity"] = rpm

    elapsed = now - _rate_state["last_refill"]
    _rate_state["tokens"] = min(float(rpm), _rate_state["tokens"] + elapsed * (rpm / 60.0))
    _rate_state["last_refill"] = now

    if _rate_state["tokens"] < 1.0:
        wait = (1.0 - _rate_state["tokens"]) / (rpm / 60.0)
        logger.debug("Rate-limit: sleeping %.2fs before next request", wait)
        time.sleep(wait)
        _rate_state["tokens"] = 0.0
    else:
        _rate_state["tokens"] -= 1.0


# ---------------------------------------------------------------------------
# Retry with exponential back-off
# ---------------------------------------------------------------------------


def _call_with_retry(operation: str, payload: Dict[str, Any], cfg: Dict[str, Any]) -> Any:
    retries = max(0, int(cfg.get("retries", 0)))
    last_error: Exception | None = None
    base_delay = 1.0  # seconds

    for attempt in range(retries + 1):
        try:
            rpm = int(cfg.get("rate_limit_rpm", _DEFAULT_RATE_LIMIT_RPM))
            if rpm > 0:
                _rate_limit_check(rpm)
            return _call_provider(operation, payload, cfg)
        except RateLimitError as exc:
            last_error = exc
            if attempt >= retries:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Rate-limited on attempt %d/%d for %s; retrying in %.1fs",
                attempt + 1, retries + 1, operation, delay,
            )
            time.sleep(delay)
        except AdapterTimeoutError as exc:
            last_error = exc
            if attempt >= retries:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Timeout on attempt %d/%d for %s; retrying in %.1fs",
                attempt + 1, retries + 1, operation, delay,
            )
            time.sleep(delay)
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                raise AdapterCallError(str(exc)) from exc
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Error on attempt %d/%d for %s: %s; retrying in %.1fs",
                attempt + 1, retries + 1, operation, exc, delay,
            )
            time.sleep(delay)

    raise AdapterCallError(str(last_error) if last_error else "adapter call failed")


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------


def _call_provider(operation: str, payload: Dict[str, Any], cfg: Dict[str, Any]) -> Any:
    """Route to the configured LLM provider."""
    provider = str(cfg.get("provider", "mock")).lower()

    if provider == "mock":
        return _call_mock(operation, payload)
    if provider == "openai":
        return _call_openai(operation, payload, cfg)
    if provider == "anthropic":
        return _call_anthropic(operation, payload, cfg)

    raise AdapterCallError(f"Unsupported llm_adapter.provider={provider!r}")


# ---------------------------------------------------------------------------
# Mock provider (unchanged from original)
# ---------------------------------------------------------------------------


def _call_mock(operation: str, payload: Dict[str, Any]) -> Any:
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


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


def _resolve_api_key(provider: str, cfg: Dict[str, Any]) -> str:
    """Resolve API key from config or environment variable."""
    key = cfg.get("api_key")
    if key and hasattr(key, "get_secret_value"):
        key = key.get_secret_value()
    if key:
        return str(key)

    env_map = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
    env_var = env_map.get(provider, "")
    key = os.environ.get(env_var, "")
    if not key:
        raise AdapterCallError(
            f"No API key for provider={provider!r}. "
            f"Set {env_var} or llm_adapter.api_key in config."
        )
    return key


def _build_messages(operation: str, payload: Dict[str, Any]) -> list[dict[str, str]]:
    """Build chat-style messages for response or appraise operations."""
    if operation == "response":
        ctx = payload.get("context_package", {})
        system_prompt = ctx.get("system_prompt", "You are a helpful persona.")
        user_prompt = ctx.get("user_prompt", ctx.get("user_message", ""))
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    if operation == "appraise":
        events = payload.get("activity_events", [])
        goal_labels = payload.get("active_goal_labels", [])
        system_prompt = (
            "You are an appraisal engine. For each event, return a JSON array of objects "
            "with keys: event_id, goal_congruence (-1 to 1), threat (0 to 1), "
            "arousal_cue (0 to 1), rationale (string). "
            "Active goals: " + ", ".join(goal_labels) if goal_labels else ""
        )
        user_content = json.dumps(events, default=str)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    raise AdapterCallError(f"Cannot build messages for operation: {operation}")


def _call_openai(operation: str, payload: Dict[str, Any], cfg: Dict[str, Any]) -> Any:
    """Call OpenAI Chat Completions API."""
    try:
        import openai  # type: ignore[import-untyped]
    except ImportError as exc:
        raise AdapterCallError(
            "openai package is required for provider=openai. Install with: pip install openai"
        ) from exc

    api_key = _resolve_api_key("openai", cfg)
    model = str(cfg.get("model", "gpt-4o"))
    timeout = int(cfg.get("timeout_seconds", 30))
    streaming = bool(cfg.get("streaming", False))
    messages = _build_messages(operation, payload)

    client = openai.OpenAI(api_key=api_key, timeout=timeout)

    try:
        if streaming:
            return _openai_streaming(client, model, messages)
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            content = response.choices[0].message.content or ""
    except openai.RateLimitError as exc:
        raise RateLimitError(f"OpenAI rate limit: {exc}") from exc
    except openai.APITimeoutError as exc:
        raise AdapterTimeoutError(f"OpenAI timeout: {exc}") from exc
    except openai.APIError as exc:
        raise AdapterCallError(f"OpenAI API error: {exc}") from exc

    return _parse_provider_output(operation, content)


def _openai_streaming(client: Any, model: str, messages: list) -> str:
    """Collect a streaming OpenAI response into a single string."""
    import openai  # type: ignore[import-untyped]

    chunks: list[str] = []
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                chunks.append(delta.content)
    except openai.RateLimitError as exc:
        raise RateLimitError(f"OpenAI rate limit (stream): {exc}") from exc
    except openai.APITimeoutError as exc:
        raise AdapterTimeoutError(f"OpenAI timeout (stream): {exc}") from exc
    except openai.APIError as exc:
        raise AdapterCallError(f"OpenAI API error (stream): {exc}") from exc

    return "".join(chunks)


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


def _call_anthropic(operation: str, payload: Dict[str, Any], cfg: Dict[str, Any]) -> Any:
    """Call Anthropic Messages API."""
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError as exc:
        raise AdapterCallError(
            "anthropic package is required for provider=anthropic. "
            "Install with: pip install anthropic"
        ) from exc

    api_key = _resolve_api_key("anthropic", cfg)
    model = str(cfg.get("model", "claude-sonnet-4-20250514"))
    timeout = int(cfg.get("timeout_seconds", 30))
    streaming = bool(cfg.get("streaming", False))
    messages = _build_messages(operation, payload)

    # Anthropic uses a separate system parameter
    system_msg = ""
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            user_messages.append(msg)

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    try:
        if streaming:
            return _anthropic_streaming(client, model, system_msg, user_messages)
        else:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_msg,
                messages=user_messages,
            )
            content = response.content[0].text if response.content else ""
    except anthropic.RateLimitError as exc:
        raise RateLimitError(f"Anthropic rate limit: {exc}") from exc
    except anthropic.APITimeoutError as exc:
        raise AdapterTimeoutError(f"Anthropic timeout: {exc}") from exc
    except anthropic.APIError as exc:
        raise AdapterCallError(f"Anthropic API error: {exc}") from exc

    return _parse_provider_output(operation, content)


def _anthropic_streaming(
    client: Any, model: str, system_msg: str, user_messages: list
) -> str:
    """Collect a streaming Anthropic response into a single string."""
    import anthropic  # type: ignore[import-untyped]

    chunks: list[str] = []
    try:
        with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=system_msg,
            messages=user_messages,
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
    except anthropic.RateLimitError as exc:
        raise RateLimitError(f"Anthropic rate limit (stream): {exc}") from exc
    except anthropic.APITimeoutError as exc:
        raise AdapterTimeoutError(f"Anthropic timeout (stream): {exc}") from exc
    except anthropic.APIError as exc:
        raise AdapterCallError(f"Anthropic API error (stream): {exc}") from exc

    return "".join(chunks)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_provider_output(operation: str, content: str) -> Any:
    """Parse raw LLM text output into the expected structure."""
    if operation == "response":
        return content

    if operation == "appraise":
        # Try to extract JSON array from the response
        text = content.strip()
        # Handle markdown code blocks
        if "```" in text:
            start = text.find("```")
            end = text.rfind("```")
            if start != end:
                inner = text[start:end]
                # Strip the opening ``` and optional language tag
                first_newline = inner.find("\n")
                if first_newline >= 0:
                    text = inner[first_newline + 1:]

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except json.JSONDecodeError:
            logger.warning("Failed to parse appraisal JSON; returning empty list")
            return []

    raise AdapterCallError(f"Cannot parse output for operation: {operation}")


# ---------------------------------------------------------------------------
# Validation helpers (unchanged)
# ---------------------------------------------------------------------------


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
