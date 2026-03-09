"""Shared config loader for cognitive modules.

Follows the same pattern as src/engine/retrieval.py — reads config/defaults.yaml
once and caches sections to avoid repeated disk reads.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "defaults.yaml"


@lru_cache(maxsize=1)
def _load_full_config() -> Dict[str, Any]:
    with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config_section(section: str) -> Dict[str, Any]:
    """Return a top-level section from config/defaults.yaml.

    Results are cached; the file is read at most once per process.
    """
    return _load_full_config().get(section, {})


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
