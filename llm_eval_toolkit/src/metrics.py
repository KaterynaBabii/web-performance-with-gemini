"""Metric computation for recommendation evaluation."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def category_set(df: pd.DataFrame, source: str) -> set[str]:
    sub = df[df["source"] == source]
    cats = set()
    for raw in sub["categories_normalized"].dropna():
        for c in str(raw).split("|"):
            if c:
                cats.add(c)
    cats.discard("invalid_unsafe")
    return cats


def compute_summary_metrics(
    df: pd.DataFrame,
    sources: list[str],
    human_source: str = "human",
) -> pd.DataFrame:
    rows = []
    human_cats = category_set(df, human_source) if human_source in sources else set()

    for src in sources:
        sub = df[df["source"] == src]
        n_total = int(len(sub))
        has_accept = sub["accepted"].notna().any()
        has_invalid = sub["invalid_or_unsafe"].notna().any()
        n_accepted = int((sub["accepted"] == 1).sum()) if has_accept else 0
        n_invalid = int((sub["invalid_or_unsafe"] == 1).sum()) if has_invalid else 0
        acceptance_rate = (n_accepted / n_total) if (n_total and has_accept) else np.nan
        invalid_rate = (n_invalid / n_total) if (n_total and has_invalid) else np.nan

        src_cats = category_set(df, src)
        category_coverage = len(src_cats)
        jacc = jaccard(src_cats, human_cats) if human_cats else np.nan
        precision = (len(src_cats & human_cats) / len(src_cats)) if src_cats else np.nan
        recall = (len(src_cats & human_cats) / len(human_cats)) if human_cats else np.nan

        time_vals = sub["time_to_analysis_minutes"].dropna()
        time_mean = float(time_vals.mean()) if not time_vals.empty else np.nan

        rows.append(
            {
                "source": src,
                "n_total": n_total,
                "n_accepted": n_accepted,
                "acceptance_rate": acceptance_rate,
                "n_invalid": n_invalid,
                "invalid_rate": invalid_rate,
                "category_coverage": category_coverage,
                "jaccard_vs_human": jacc,
                "precision_vs_human": precision,
                "recall_vs_human": recall,
                "mean_time_to_analysis_minutes": time_mean,
            }
        )
    return pd.DataFrame(rows)


def compute_similarity_matrix(df: pd.DataFrame, sources: list[str]) -> pd.DataFrame:
    mat = pd.DataFrame(index=sources, columns=sources, dtype=float)
    for a in sources:
        for b in sources:
            mat.loc[a, b] = jaccard(category_set(df, a), category_set(df, b))
    return mat
