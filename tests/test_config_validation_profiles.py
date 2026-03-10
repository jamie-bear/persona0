from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.modules import _config


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERSONA0_CONFIG_PROFILE", raising=False)
    monkeypatch.delenv("PERSONA0_CONFIG_FILES", raising=False)
    monkeypatch.delenv("PERSONA0_LLM_ADAPTER__API_KEY", raising=False)
    monkeypatch.delenv("PERSONA0_LLM_ADAPTER__MODEL", raising=False)
    _config.get_settings.cache_clear()


def test_dev_profile_validates_without_provider_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA0_CONFIG_PROFILE", "dev")

    settings = _config.get_settings()

    assert settings.llm_adapter.enabled is False
    assert settings.llm_adapter.provider == "mock"


def test_staging_profile_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA0_CONFIG_PROFILE", "staging")

    with pytest.raises(RuntimeError, match="api_key"):
        _config.get_settings()


def test_prod_profile_validates_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA0_CONFIG_PROFILE", "prod")
    monkeypatch.setenv("PERSONA0_LLM_ADAPTER__API_KEY", "super-secret")

    settings = _config.get_settings()

    assert settings.llm_adapter.enabled is True
    assert settings.llm_adapter.api_key is not None


def test_env_overrides_take_precedence_over_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    override_file = tmp_path / "override.yaml"
    override_file.write_text("llm_adapter:\n  model: from-file\n", encoding="utf-8")

    monkeypatch.setenv("PERSONA0_CONFIG_PROFILE", "dev")
    monkeypatch.setenv("PERSONA0_CONFIG_FILES", str(override_file))
    monkeypatch.setenv("PERSONA0_LLM_ADAPTER__MODEL", "from-env")

    settings = _config.get_settings()

    assert settings.llm_adapter.model == "from-env"


def test_sensitive_values_rejected_in_config_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("llm_adapter:\n  api_key: leaked\n", encoding="utf-8")

    monkeypatch.setenv("PERSONA0_CONFIG_PROFILE", "dev")
    monkeypatch.setenv("PERSONA0_CONFIG_FILES", str(bad_file))

    with pytest.raises(RuntimeError, match="must not be stored"):
        _config.get_settings()
