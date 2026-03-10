from __future__ import annotations

import pytest

from src.engine.modules import _config


def _reset_cache() -> None:
    _config.get_runtime_config.cache_clear()


def test_loads_environment_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA0_CONFIG_ENV", "staging")
    _reset_cache()

    cfg = _config.get_runtime_config()

    assert cfg["tick"]["fast_interval_seconds"] == 900
    assert cfg["llm_adapter"]["enabled"] is True


def test_validation_fails_for_unknown_field(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad_defaults = tmp_path / "defaults.yaml"
    bad_defaults.write_text("tick:\n  fast_interval_seconds: 1\n  slow_interval_seconds: 1\n  macro_interval_seconds: 1\nunknown_section: {}\n")
    env_dir = tmp_path / "environments"
    env_dir.mkdir()

    monkeypatch.setattr(_config, "_DEFAULT_CONFIG_PATH", bad_defaults)
    monkeypatch.setattr(_config, "_ENV_CONFIG_ROOT", env_dir)
    monkeypatch.setenv("PERSONA0_CONFIG_ENV", "prod")
    _reset_cache()

    with pytest.raises(ValueError):
        _config.validate_runtime_config()
