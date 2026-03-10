"""Typed configuration loading with layered precedence.

Precedence (highest -> lowest):
1. Environment variables (PERSONA0_*)
2. Operator config files (PERSONA0_CONFIG_FILES, comma-separated)
3. Deployment profile file (config/profiles/{profile}.yaml, profile from PERSONA0_CONFIG_PROFILE)
4. Immutable defaults (config/defaults.immutable.yaml)
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml
from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
_IMMUTABLE_DEFAULTS_PATH = _CONFIG_DIR / "defaults.immutable.yaml"
_PROFILES_DIR = _CONFIG_DIR / "profiles"

_CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
_DEFAULT_CONFIG_PATH = _CONFIG_ROOT / "defaults.yaml"
_ENV_CONFIG_ROOT = _CONFIG_ROOT / "environments"

def _deep_merge(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _profile_name() -> str:
    return os.getenv("PERSONA0_CONFIG_PROFILE", "dev").strip().lower() or "dev"


def _operator_config_paths() -> Iterable[Path]:
    raw = os.getenv("PERSONA0_CONFIG_FILES", "").strip()
    if not raw:
        return []
    return [Path(item.strip()).expanduser() for item in raw.split(",") if item.strip()]


def _build_file_config() -> Dict[str, Any]:
    if not _IMMUTABLE_DEFAULTS_PATH.exists():
        raise RuntimeError(f"Missing immutable defaults: {_IMMUTABLE_DEFAULTS_PATH}")

    merged = _load_yaml(_IMMUTABLE_DEFAULTS_PATH)
    profile = _profile_name()
    profile_path = _PROFILES_DIR / f"{profile}.yaml"
    if not profile_path.exists():
        raise RuntimeError(f"Unknown config profile {profile!r}; expected file at {profile_path}")
    merged = _deep_merge(merged, _load_yaml(profile_path))

    for override_path in _operator_config_paths():
        if not override_path.exists():
            raise RuntimeError(f"Configured override file does not exist: {override_path}")
        merged = _deep_merge(merged, _load_yaml(override_path))

    llm_cfg = merged.get("llm_adapter", {})
    forbidden = [key for key in ("api_key", "organization_id", "access_token") if key in llm_cfg]
    if forbidden:
        keys = ", ".join(sorted(forbidden))
        raise RuntimeError(
            f"Sensitive llm_adapter keys ({keys}) must not be stored in config files; use env vars"
        )

    return merged


class LLMAdapterConfig(BaseModel):
    enabled: bool = False
    provider: str = "mock"
    model: str = "mock-chat-v1"
    timeout_seconds: int = 2
    retries: int = 1
    deterministic_mode: bool = True
    api_key: SecretStr | None = None
    organization_id: SecretStr | None = None

    @model_validator(mode="after")
    def _validate_credentials(self) -> "LLMAdapterConfig":
        if self.enabled and self.provider != "mock" and self.api_key is None:
            raise ValueError("llm_adapter.api_key is required for enabled non-mock providers")
        return self


class TickConfig(BaseModel):
    fast_interval_seconds: int
    slow_interval_seconds: int
    macro_interval_seconds: int


class RetrievalConfig(BaseModel):
    recency_weight: float
    importance_weight: float
    semantic_similarity_weight: float
    self_relevance_weight: float
    goal_relevance_weight: float = 0.15
    candidate_limit: int
    salience_buffer_capacity: int
    min_importance_threshold: float


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    tick: TickConfig
    retrieval: RetrievalConfig
    llm_adapter: LLMAdapterConfig


class RuntimeEnvOverrides(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PERSONA0_", env_nested_delimiter="__", extra="ignore")

    tick: Dict[str, Any] | None = None
    retrieval: Dict[str, Any] | None = None
    llm_adapter: Dict[str, Any] | None = None


@lru_cache(maxsize=1)
def get_settings() -> RuntimeConfig:
    merged = _build_file_config()
    env_overrides = RuntimeEnvOverrides().model_dump(mode="python", exclude_none=True)
    merged = _deep_merge(merged, env_overrides)
    try:
        return RuntimeConfig.model_validate(merged)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid runtime configuration: {exc}") from exc


def load_config_section(section: str) -> Dict[str, Any]:
    payload = get_settings().model_dump(mode="python")
    return payload.get(section, {})


def validate_startup_config() -> None:
    get_settings()


# Backward-compatible aliases used by runtime entrypoints and legacy tests.
@lru_cache(maxsize=1)
def get_runtime_config() -> Dict[str, Any]:
    """Return runtime config as a plain dict (legacy helper).

    Legacy precedence:
    1) defaults.yaml
    2) config/environments/{PERSONA0_CONFIG_ENV}.yaml
    """
    merged = _load_yaml(_DEFAULT_CONFIG_PATH) if _DEFAULT_CONFIG_PATH.exists() else {}

    env_name = os.getenv("PERSONA0_CONFIG_ENV", "dev").strip().lower() or "dev"
    env_path = _ENV_CONFIG_ROOT / f"{env_name}.yaml"
    if env_path.exists():
        merged = _deep_merge(merged, _load_yaml(env_path))

    return merged


def validate_runtime_config() -> None:
    """Validate runtime config and normalize errors to ValueError (legacy helper)."""
    cfg = get_runtime_config()
    allowed_top_level = {
        "tick",
        "drives",
        "affect",
        "goals",
        "reflection",
        "retrieval",
        "memory",
        "governance",
        "observability",
        "llm_adapter",
    }
    unknown = sorted(set(cfg.keys()) - allowed_top_level)
    if unknown:
        raise ValueError(f"Unknown config sections: {', '.join(unknown)}")

    try:
        RuntimeConfig.model_validate(cfg)
    except ValidationError as exc:
        raise ValueError(f"Invalid runtime configuration: {exc}") from exc


def load_drives_config() -> Dict[str, Any]:
    return load_config_section("drives")


def load_affect_config() -> Dict[str, Any]:
    return load_config_section("affect")


def load_goals_config() -> Dict[str, Any]:
    return load_config_section("goals")


def load_memory_config() -> Dict[str, Any]:
    return load_config_section("memory")


def load_tick_config() -> Dict[str, Any]:
    return load_config_section("tick")


def load_reflection_config() -> Dict[str, Any]:
    return load_config_section("reflection")
