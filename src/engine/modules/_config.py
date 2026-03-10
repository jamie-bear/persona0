"""Shared config loader for cognitive modules.

Loads a base config plus environment-specific overlay and validates strictly.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import ValidationError

from .config_schema import RuntimeConfig

_CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
_DEFAULT_CONFIG_PATH = _CONFIG_ROOT / "defaults.yaml"
_ENV_CONFIG_ROOT = _CONFIG_ROOT / "environments"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=1)
def get_runtime_config() -> Dict[str, Any]:
    env = os.getenv("PERSONA0_CONFIG_ENV", "dev").strip().lower() or "dev"
    config = _load_yaml(_DEFAULT_CONFIG_PATH)
    overlay_path = _ENV_CONFIG_ROOT / f"{env}.yaml"
    if overlay_path.exists():
        config = _deep_merge(config, _load_yaml(overlay_path))
    return RuntimeConfig.model_validate(config).model_dump()


def validate_runtime_config() -> None:
    """Force config parse + strict schema validation."""
    try:
        get_runtime_config()
    except ValidationError as exc:
        raise ValueError(f"Invalid runtime configuration: {exc}") from exc


def load_config_section(section: str) -> Dict[str, Any]:
    return get_runtime_config().get(section, {})


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
