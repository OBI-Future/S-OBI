"""Deterministic smoke-only backend; this is not a benchmark baseline."""

from __future__ import annotations

from typing import Any, Mapping


def predict(task: Mapping[str, Any]) -> Any:
    """Return a deterministic placeholder prediction for end-to-end smoke tests."""

    options = task.get("options")
    if isinstance(options, list) and options and isinstance(options[0], dict):
        label = options[0].get("label")
        if isinstance(label, str):
            return label
    return "SMOKE_ONLY"
