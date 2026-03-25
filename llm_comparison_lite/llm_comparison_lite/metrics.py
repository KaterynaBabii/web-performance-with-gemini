"""Core metrics: Jaccard overlap, per-model rates, category aggregates."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

# Models whose outputs are compared as \"advisors\" (expert human is reference only).
LLM_MODEL_IDS = ("gemini", "gpt4", "claude")


def _as_bool(v: Any) -> bool:
    """Coerce JSON-ish values to bool."""
    if isinstance(v, bool):
        return v
    s = str(v).lower().strip()
    return s in ("true", "1", "yes")


def recommendation_keys(rows: Iterable[dict]) -> set[str]:
    """
    Build a set identity for each recommendation for overlap metrics.
    Uses normalized endpoint + normalized category (not raw_text) to approximate
    \"same suggestion\" without embedding models.
    """
    keys: set[str] = set()
    for r in rows:
        ep = str(r.get("endpoint", "")).lower().strip()
        cat = str(r.get("category_normalized", r.get("category", ""))).lower().strip()
        keys.add(f"{ep}||{cat}")
    return keys


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard index in [0, 1]; 1.0 if both empty."""
    if not a and not b:
        return 1.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def rows_to_dataframe(model_id: str, rows: list[dict]) -> pd.DataFrame:
    """Flatten list of dicts to a DataFrame with coerced booleans."""
    if not rows:
        return pd.DataFrame(
            columns=[
                "model",
                "endpoint",
                "raw_text",
                "category",
                "category_normalized",
                "accepted_by_human",
                "invalid_or_hallucinated",
                "safety_risk",
            ]
        )
    records = []
    for r in rows:
        records.append(
            {
                "model": model_id,
                "endpoint": r.get("endpoint", ""),
                "raw_text": r.get("raw_text", ""),
                "category": r.get("category", ""),
                "category_normalized": r.get("category_normalized", ""),
                "accepted_by_human": _as_bool(r.get("accepted_by_human")),
                "invalid_or_hallucinated": _as_bool(r.get("invalid_or_hallucinated")),
                "safety_risk": str(r.get("safety_risk", "low")).lower().strip(),
            }
        )
    return pd.DataFrame.from_records(records)


def compute_summary_table(
    data: dict[str, list[dict]],
    *,
    human_id: str = "human",
) -> pd.DataFrame:
    """
    One row per LLM with totals, rates, agreement with human expert (Jaccard on keys),
    and mean Jaccard vs the other two LLMs.
    """
    human_keys = recommendation_keys(data.get(human_id, []))
    key_by_model = {m: recommendation_keys(data[m]) for m in LLM_MODEL_IDS if m in data}

    rows_out = []
    for m in LLM_MODEL_IDS:
        if m not in data:
            continue
        df = rows_to_dataframe(m, data[m])
        n = len(df)
        if n == 0:
            rows_out.append(
                {
                    "model": m,
                    "n_total": 0,
                    "n_accepted": 0,
                    "acceptance_rate": np.nan,
                    "invalid_or_hallucinated_rate": np.nan,
                    "hallucination_rate": np.nan,
                    "safety_high_risk_rate": np.nan,
                    "agreement_with_human_jaccard": jaccard(key_by_model[m], human_keys),
                    "mean_jaccard_vs_other_llms": np.nan,
                }
            )
            continue

        n_acc = int(df["accepted_by_human"].sum())
        n_inv = int(df["invalid_or_hallucinated"].sum())
        n_high = int((df["safety_risk"] == "high").sum())

        others = [x for x in LLM_MODEL_IDS if x != m and x in key_by_model]
        pair_js = [jaccard(key_by_model[m], key_by_model[o]) for o in others]

        rows_out.append(
            {
                "model": m,
                "n_total": n,
                "n_accepted": n_acc,
                "acceptance_rate": n_acc / n,
                # Single human-labeled flag in data; we report both names for the paper
                "invalid_or_hallucinated_rate": n_inv / n,
                "hallucination_rate": n_inv / n,
                "safety_high_risk_rate": n_high / n,
                "agreement_with_human_jaccard": jaccard(key_by_model[m], human_keys),
                "mean_jaccard_vs_other_llms": float(np.mean(pair_js)) if pair_js else np.nan,
            }
        )

    return pd.DataFrame(rows_out)


def pairwise_jaccard_table(data: dict[str, list[dict]]) -> pd.DataFrame:
    """All unordered pairs among gemini, gpt4, claude."""
    keys = {m: recommendation_keys(data[m]) for m in LLM_MODEL_IDS if m in data}
    mids = [m for m in LLM_MODEL_IDS if m in keys]
    rows = []
    for i, a in enumerate(mids):
        for b in mids[i + 1 :]:
            rows.append(
                {
                    "model_a": a,
                    "model_b": b,
                    "jaccard": jaccard(keys[a], keys[b]),
                }
            )
    return pd.DataFrame(rows)


def category_breakdown_table(data: dict[str, list[dict]]) -> pd.DataFrame:
    """Per model (including human) × normalized category counts and rates."""
    frames = []
    for mid, rows in data.items():
        df = rows_to_dataframe(mid, rows)
        if df.empty:
            continue
        g = df.groupby("category_normalized", dropna=False)
        part = g.agg(
            n=("endpoint", "count"),
            n_accepted=("accepted_by_human", "sum"),
            n_invalid=("invalid_or_hallucinated", "sum"),
        ).reset_index()
        part["model"] = mid
        part["acceptance_rate"] = np.where(part["n"] > 0, part["n_accepted"] / part["n"], np.nan)
        part["invalid_rate"] = np.where(part["n"] > 0, part["n_invalid"] / part["n"], np.nan)
        frames.append(part)
    if not frames:
        return pd.DataFrame(
            columns=[
                "model",
                "category_normalized",
                "n",
                "n_accepted",
                "n_invalid",
                "acceptance_rate",
                "invalid_rate",
            ]
        )
    out = pd.concat(frames, ignore_index=True)
    return out[
        [
            "model",
            "category_normalized",
            "n",
            "n_accepted",
            "n_invalid",
            "acceptance_rate",
            "invalid_rate",
        ]
    ].sort_values(["model", "category_normalized"])


def human_model_jaccard_rows(data: dict[str, list[dict]]) -> pd.DataFrame:
    """Optional: each LLM vs human for a dedicated overlap table."""
    if "human" not in data:
        return pd.DataFrame(columns=["model", "human_jaccard"])
    hk = recommendation_keys(data["human"])
    rows = []
    for m in LLM_MODEL_IDS:
        if m not in data:
            continue
        rows.append({"model": m, "human_jaccard": jaccard(recommendation_keys(data[m]), hk)})
    return pd.DataFrame(rows)
