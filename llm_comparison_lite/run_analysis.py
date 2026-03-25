#!/usr/bin/env python3
"""
End-to-end pipeline: load four JSON files → CSV + LaTeX + console report (+ optional plots).

Documentation (single Markdown file for this project): LIGHTWEIGHT_COMPARISON.md

Run from this directory:
  python3 -m pip install -r requirements.txt
  python3 run_analysis.py --data-dir data --out-dir outputs --plots
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure local package import when executed as a script (no install required).
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_comparison_lite.categories import attach_normalized_category
from llm_comparison_lite.io import load_all_models
from llm_comparison_lite.latex_export import dataframe_to_booktabs
from llm_comparison_lite.metrics import (
    category_breakdown_table,
    compute_summary_table,
    pairwise_jaccard_table,
)
from llm_comparison_lite.plots import plot_category_counts, plot_jaccard_heatmap
from llm_comparison_lite.report import emit_markdown_tables, print_publication_summary


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lightweight LLM comparison: gemini / gpt4 / claude vs human JSON → tables."
    )
    ap.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory with four JSON files")
    ap.add_argument("--out-dir", type=Path, default=Path("outputs"), help="Where to write CSV, TeX, figures")
    ap.add_argument("--plots", action="store_true", help="Write matplotlib PNGs under out-dir")
    ap.add_argument(
        "--emit-markdown-tables",
        action="store_true",
        help="Print Markdown pipe tables to stdout (for pasting into LIGHTWEIGHT_COMPARISON.md)",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Skip the publication-style console report (still writes files unless --emit-markdown-only)",
    )
    ap.add_argument(
        "--emit-markdown-only",
        action="store_true",
        help="Only print Markdown tables; do not write CSV/TeX/PNG (implies --emit-markdown-tables)",
    )
    args = ap.parse_args()
    if args.emit_markdown_only:
        args.emit_markdown_tables = True
        args.quiet = True

    data_dir = args.data_dir.resolve()
    out_dir = args.out_dir.resolve()
    if not args.emit_markdown_only:
        out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load all four JSON files (strict field validation in io.load_recommendations).
    raw = load_all_models(data_dir)

    # 2) Normalize free-text categories → canonical buckets for fair counts / Jaccard keys.
    for _mid, rows in raw.items():
        attach_normalized_category(rows)

    # 3) Build summary (per LLM rates + human Jaccard + mean Jaccard vs other LLMs),
    #    pairwise LLM Jaccard matrix rows, and category × model breakdown (includes human).
    summary = compute_summary_table(raw)
    pairwise = pairwise_jaccard_table(raw)
    breakdown = category_breakdown_table(raw)

    if args.emit_markdown_tables:
        print(emit_markdown_tables(summary, pairwise, breakdown))

    if args.emit_markdown_only:
        return 0

    # 4) CSV
    summary_path = out_dir / "summary.csv"
    pairwise_path = out_dir / "pairwise_overlap.csv"
    breakdown_path = out_dir / "category_breakdown.csv"
    summary.to_csv(summary_path, index=False)
    pairwise.to_csv(pairwise_path, index=False)
    breakdown.to_csv(breakdown_path, index=False)

    # 5) LaTeX (booktabs)
    dataframe_to_booktabs(
        summary,
        out_dir / "table_summary.tex",
        caption="Per-model recommendation statistics and overlap metrics.",
        label="tab:llm_lite_summary",
    )
    dataframe_to_booktabs(
        pairwise,
        out_dir / "table_pairwise_overlap.tex",
        caption="Pairwise Jaccard overlap between LLM recommendation sets (endpoint and normalized category key).",
        label="tab:llm_lite_pairwise",
    )
    dataframe_to_booktabs(
        breakdown,
        out_dir / "table_category_breakdown.tex",
        caption="Recommendation counts and rates by model and normalized category.",
        label="tab:llm_lite_category",
    )

    # 6) Console
    if not args.quiet:
        print_publication_summary(summary, pairwise, breakdown)
        print(f"Wrote CSV:  {summary_path}\n            {pairwise_path}\n            {breakdown_path}")
        print(f"Wrote LaTeX: {out_dir / 'table_summary.tex'}")
        print(f"             {out_dir / 'table_pairwise_overlap.tex'}")
        print(f"             {out_dir / 'table_category_breakdown.tex'}")

    # 7) Optional figures
    if args.plots:
        plot_category_counts(breakdown, out_dir / "fig_category_counts.png")
        plot_jaccard_heatmap(pairwise, out_dir / "fig_jaccard_heatmap.png")
        if not args.quiet:
            print(f"Wrote plots: {out_dir / 'fig_category_counts.png'}")
            print(f"             {out_dir / 'fig_jaccard_heatmap.png'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
