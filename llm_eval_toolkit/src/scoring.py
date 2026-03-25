"""Scoring CSV loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

SCORING_COLUMNS = [
    "source",
    "recommendation_id",
    "category",
    "accepted",
    "invalid_or_unsafe",
    "actionability_score",
    "correctness_score",
    "time_to_analysis_minutes",
]


def load_scoring_csv(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=SCORING_COLUMNS)
    df = pd.read_csv(path)
    for col in SCORING_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[SCORING_COLUMNS]


def build_scoring_template(rows: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    base = df[["source", "recommendation_id"]].copy()
    for col in SCORING_COLUMNS:
        if col not in base.columns:
            base[col] = None
    return base[SCORING_COLUMNS]


def validate_scoring(df: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    if df.empty:
        return issues
    both = df[(df["accepted"] == 1) & (df["invalid_or_unsafe"] == 1)]
    if not both.empty:
        issues.append(
            f"{len(both)} rows have accepted=1 and invalid_or_unsafe=1; check scoring."
        )
    return issues
