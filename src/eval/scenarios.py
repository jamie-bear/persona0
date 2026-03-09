"""Scenario fixtures for evaluation runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_fixture(path: str | Path) -> list[dict[str, Any]]:
    fixture_path = Path(path)
    with fixture_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if not isinstance(payload, list):
        raise ValueError("Scenario fixture must be a list")
    return payload
