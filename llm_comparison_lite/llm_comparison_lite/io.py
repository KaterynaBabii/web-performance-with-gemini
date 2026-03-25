"""Load and validate recommendation JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Required fields on every recommendation object
REQUIRED_FIELDS = (
    "endpoint",
    "raw_text",
    "category",
    "accepted_by_human",
    "invalid_or_hallucinated",
    "safety_risk",
)

ALLOWED_SAFETY = frozenset({"low", "medium", "high"})


def load_recommendations(path: Path) -> list[dict[str, Any]]:
    """
    Load a JSON file that is either:
    - a list of recommendation objects, or
    - a dict with key \"recommendations\" containing that list.
    """
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "recommendations" in raw:
        items = raw["recommendations"]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError(f"{path}: expected a list or {{\"recommendations\": [...]}}")

    if not isinstance(items, list):
        raise ValueError(f"{path}: recommendations must be a list")

    for i, row in enumerate(items):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: item {i} is not an object")
        for k in REQUIRED_FIELDS:
            if k not in row:
                raise ValueError(f"{path}: item {i} missing field {k!r}")
        sr = str(row["safety_risk"]).lower().strip()
        if sr not in ALLOWED_SAFETY:
            raise ValueError(
                f"{path}: item {i} safety_risk must be one of {sorted(ALLOWED_SAFETY)}, got {row['safety_risk']!r}"
            )
        row["safety_risk"] = sr  # normalize casing

    return items


def load_all_models(
    data_dir: Path,
    *,
    gemini_name: str = "gemini.json",
    gpt4_name: str = "gpt4.json",
    claude_name: str = "claude.json",
    human_name: str = "human.json",
) -> dict[str, list[dict[str, Any]]]:
    """Load the four standard input files; keys are model ids: gemini, gpt4, claude, human."""
    data_dir = Path(data_dir)
    return {
        "gemini": load_recommendations(data_dir / gemini_name),
        "gpt4": load_recommendations(data_dir / gpt4_name),
        "claude": load_recommendations(data_dir / claude_name),
        "human": load_recommendations(data_dir / human_name),
    }
