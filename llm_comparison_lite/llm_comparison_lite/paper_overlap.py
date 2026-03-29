"""
Metrics from docs/GEMINI_VS_HUMAN_ENGINEER_COMPARISON.md:
overlap |G ∩ H|, agreement |G∩H|/|H|, Gemini precision |G∩H|/|G|,
human-only, Gemini-only valid, invalid Gemini count/rate.

Canonical identity: normalized endpoint + normalized primary category
(same spirit as recommendation_keys in metrics.py).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from llm_comparison_lite.categories import normalize_category


def normalize_endpoint(raw: str) -> str:
    """
    Canonicalize endpoints for matching:
    - strip query string
    - normalize path params to "{id}"
    - collapse common variants (:id, [id], [userId])
    """
    if raw is None:
        return ""
    ep = str(raw).strip()
    ep = ep.split("?", 1)[0]
    ep = ep.replace(":id", "{id}")
    ep = ep.replace("[id]", "{id}")
    ep = ep.replace("[userId]", "{id}")
    return ep


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).lower().strip() in ("true", "1", "yes")


def canonical_key(row: dict) -> str:
    """Primary category + endpoint string (lowercased) for exact match."""
    ep = normalize_endpoint(row.get("endpoint", "")).lower().strip()
    cat = normalize_category(row.get("category", ""))
    # Conceptual alignment for overlap (pre-registered bucket mapping).
    # Collapse search/query-path optimizations into a single bucket.
    if cat in ("query_rewrite", "n+1", "join_optimization", "indexing", "payload_reduction"):
        cat = "query_optimization"
    elif cat in ("caching",):
        cat = "caching"
    elif cat in ("batching", "transaction_handling"):
        cat = "batching_txn"
    return f"{ep}||{cat}"


def compute_gemini_human_paper_metrics(
    gemini_rows: list[dict],
    human_rows: list[dict],
) -> dict[str, Any]:
    """
    Build deduplicated sets G, H on canonical_key.
    Invalid: any Gemini row with that key has invalid_or_hallucinated True.
    """
    # Per-key: Gemini invalid if any row under key is invalid
    g_invalid_by_key: dict[str, bool] = {}
    g_seen_keys: set[str] = set()
    for r in gemini_rows:
        k = canonical_key(r)
        g_seen_keys.add(k)
        inv = _as_bool(r.get("invalid_or_hallucinated"))
        g_invalid_by_key[k] = g_invalid_by_key.get(k, False) or inv

    h_keys: set[str] = set()
    for r in human_rows:
        h_keys.add(canonical_key(r))

    g_keys = set(g_invalid_by_key.keys())
    overlap = g_keys & h_keys
    n_overlap = len(overlap)
    n_g = len(g_keys)
    n_h = len(h_keys)

    agreement_rate = (n_overlap / n_h) if n_h > 0 else float("nan")
    gemini_precision = (n_overlap / n_g) if n_g > 0 else float("nan")

    human_only = len(h_keys - g_keys)
    g_valid_keys = {k for k in g_keys if not g_invalid_by_key.get(k, False)}
    gemini_only_valid = len((g_keys - h_keys) & g_valid_keys)

    n_gemini_rows = len(gemini_rows)
    n_invalid_rows = sum(1 for r in gemini_rows if _as_bool(r.get("invalid_or_hallucinated")))
    invalid_row_rate = (n_invalid_rows / n_gemini_rows) if n_gemini_rows > 0 else float("nan")

    return {
        "NH": n_h,
        "NG": n_g,
        "NG_rows": n_gemini_rows,
        "NO": n_overlap,
        "AR_pct": 100.0 * agreement_rate if not np.isnan(agreement_rate) else float("nan"),
        "GP_pct": 100.0 * gemini_precision if not np.isnan(gemini_precision) else float("nan"),
        "HO": human_only,
        "GV": gemini_only_valid,
        "NI": n_invalid_rows,
        "NIR_pct": 100.0 * invalid_row_rate if not np.isnan(invalid_row_rate) else float("nan"),
    }


def metrics_to_csv_row(m: dict[str, Any]) -> pd.DataFrame:
    """Single-row DataFrame for paper_overlap_summary.csv."""
    return pd.DataFrame(
        [
            {
                "human_recommendations_NH": m["NH"],
                "gemini_recommendations_NG": m["NG"],
                "overlap_NO": m["NO"],
                "agreement_rate_pct": m["AR_pct"],
                "gemini_precision_on_human_pct": m["GP_pct"],
                "human_only_HO": m["HO"],
                "gemini_only_valid_GV": m["GV"],
                "invalid_gemini_NI": m["NI"],
                "invalid_gemini_rate_pct": m["NIR_pct"],
            }
        ]
    )


def metrics_to_latex_table(m: dict[str, Any], caption: str, label: str) -> str:
    """Fill Table template from GEMINI_VS_HUMAN_ENGINEER_COMPARISON.md."""
    def fmt_pct(x: float) -> str:
        if x != x:  # NaN
            return "---"
        return f"{x:.1f}"

    def fmt_int(x: Any) -> str:
        return str(int(x))

    lines = [
        "% Auto-generated — edit caption/label in run_paper_overlap.py if needed",
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\begin{tabular}{l r}",
        "\\toprule",
        "Metric & Value \\\\",
        "\\midrule",
        f"Human recommendations $|H|$ & {fmt_int(m['NH'])} \\\\",
        f"Gemini recommendations $|G|$ & {fmt_int(m['NG'])} \\\\",
        f"Overlap (exact matches) $|G \\cap H|$ & {fmt_int(m['NO'])} \\\\",
        f"Agreement rate $|G \\cap H| / |H|$ & {fmt_pct(m['AR_pct'])}\\% \\\\",
        f"Gemini precision on human items $|G \\cap H| / |G|$ & {fmt_pct(m['GP_pct'])}\\% \\\\",
        f"Human-only recommendations $|H \\setminus G|$ & {fmt_int(m['HO'])} \\\\",
        f"Gemini-only valid recommendations & {fmt_int(m['GV'])} \\\\",
        f"Invalid Gemini suggestions $n_{{\\mathrm{{invalid}}}}$ (rate) & {fmt_int(m['NI'])} ({fmt_pct(m['NIR_pct'])}\\%) \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ]
    return "\n".join(lines)
