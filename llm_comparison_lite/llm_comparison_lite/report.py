"""Console reporting: publication-ready formatted summary."""

from __future__ import annotations

import pandas as pd
import numpy as np


def print_publication_summary(
    summary: pd.DataFrame,
    pairwise: pd.DataFrame,
    breakdown: pd.DataFrame,
) -> None:
    """Print clear, copy-friendly blocks for methods/results drafts."""

    print("\n" + "=" * 72)
    print("LIGHTWEIGHT LLM COMPARISON — SUMMARY (per model)")
    print("=" * 72)
    # Format floats for display
    disp = summary.copy()
    for c in disp.columns:
        if disp[c].dtype == float or disp[c].dtype == "float64":
            disp[c] = disp[c].map(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
    print(disp.to_string(index=False))

    print("\n" + "-" * 72)
    print("Definitions")
    print("-" * 72)
    print(
        "- acceptance_rate: fraction of that model's items with accepted_by_human == true.\n"
        "- invalid_or_hallucinated_rate / hallucination_rate: same flag (single human label).\n"
        "- agreement_with_human_jaccard: Jaccard on sets of (endpoint, category_normalized).\n"
        "- mean_jaccard_vs_other_llms: mean pairwise Jaccard to the other two LLMs."
    )

    print("\n" + "=" * 72)
    print("PAIRWISE JACCARD (LLM ↔ LLM)")
    print("=" * 72)
    print(pairwise.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n" + "=" * 72)
    print("CATEGORY BREAKDOWN (head)")
    print("=" * 72)
    print(
        breakdown.sort_values(["model", "n"], ascending=[True, False])
        .head(24)
        .to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    print("\n(Full tables written to CSV under output directory.)\n")


def _md_cell(v) -> str:
    """Escape pipes for Markdown tables."""
    if pd.isna(v):
        return "—"
    if isinstance(v, (float, np.floating)):
        return f"{float(v):.4f}"
    if isinstance(v, (bool, np.bool_)):
        return "true" if v else "false"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    s = str(v).replace("|", "\\|")
    return s


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """GitHub-flavored Markdown pipe table (no extra dependencies)."""
    cols = list(df.columns)
    head = "| " + " | ".join(_md_cell(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = []
    for _, row in df.iterrows():
        body.append("| " + " | ".join(_md_cell(row[c]) for c in cols) + " |")
    return "\n".join([head, sep, *body])


def emit_markdown_tables(
    summary: pd.DataFrame,
    pairwise: pd.DataFrame,
    breakdown: pd.DataFrame,
) -> str:
    """Single document fragment: three Markdown tables for pasting into a report."""
    parts = [
        "### Summary (per LLM)\n",
        dataframe_to_markdown(summary),
        "\n\n### Pairwise Jaccard (LLM ↔ LLM)\n",
        dataframe_to_markdown(pairwise),
        "\n\n### Category breakdown (all sources)\n",
        dataframe_to_markdown(
            breakdown.sort_values(["model", "category_normalized"]).reset_index(drop=True)
        ),
        "\n",
    ]
    return "\n".join(parts)
