#!/usr/bin/env python3
"""
End-to-end evaluation pipeline for LLM recommendation comparison.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.categories import infer_categories_from_text, normalize_categories
from src.io_utils import discover_input_files, load_recommendations
from src.latex import write_latex_tables
from src.metrics import compute_similarity_matrix, compute_summary_metrics
from src.plots import plot_accepted_by_source, plot_invalid_rate, plot_jaccard_heatmap
from src.scoring import build_scoring_template, load_scoring_csv, validate_scoring


def build_recommendations_df(inputs_dir: Path) -> pd.DataFrame:
    sources = discover_input_files(inputs_dir)
    rows = []
    for source, path in sorted(sources.items()):
        rows.extend(load_recommendations(path, source))
    if not rows:
        raise SystemExit("No input files found in inputs directory.")

    df = pd.DataFrame(rows)
    df["categories_normalized"] = df.apply(
        lambda r: "|".join(
            normalize_categories(r["raw_category"])
            if r["raw_category"]
            else infer_categories_from_text(r["raw_text"])
        ),
        axis=1,
    )
    return df


def apply_scoring(df: pd.DataFrame, scoring_df: pd.DataFrame) -> pd.DataFrame:
    if scoring_df.empty:
        df["category_scored"] = None
        df["accepted"] = None
        df["invalid_or_unsafe"] = None
        df["actionability_score"] = None
        df["correctness_score"] = None
        df["time_to_analysis_minutes"] = None
        return df

    scoring_df = scoring_df.copy()
    scoring_df["category_scored"] = scoring_df["category"].apply(
        lambda v: "|".join(normalize_categories(v)) if pd.notna(v) else None
    )
    for col in [
        "accepted",
        "invalid_or_unsafe",
        "actionability_score",
        "correctness_score",
        "time_to_analysis_minutes",
    ]:
        scoring_df[col] = pd.to_numeric(scoring_df[col], errors="coerce")

    merged = df.merge(
        scoring_df[
            [
                "source",
                "recommendation_id",
                "category_scored",
                "accepted",
                "invalid_or_unsafe",
                "actionability_score",
                "correctness_score",
                "time_to_analysis_minutes",
            ]
        ],
        on=["source", "recommendation_id"],
        how="left",
    )
    merged["categories_normalized"] = merged.apply(
        lambda r: r["category_scored"] if pd.notna(r["category_scored"]) else r["categories_normalized"],
        axis=1,
    )
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM recommendation evaluation toolkit")
    ap.add_argument("--inputs", type=Path, default=Path("inputs"), help="Input directory")
    ap.add_argument("--scoring", type=Path, default=None, help="Scoring CSV file")
    ap.add_argument("--outputs", type=Path, default=Path("outputs"), help="Output directory")
    ap.add_argument("--human-source", type=str, default="human", help="Human source id")
    ap.add_argument("--emit-scoring-template", action="store_true", help="Write scoring template CSV")
    args = ap.parse_args()

    inputs_dir = args.inputs.resolve()
    outputs_dir = args.outputs.resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    recs_df = build_recommendations_df(inputs_dir)
    scoring_df = load_scoring_csv(args.scoring)

    if args.emit_scoring_template:
        template = build_scoring_template(recs_df.to_dict(orient="records"))
        template_path = outputs_dir / "scoring_template.csv"
        template.to_csv(template_path, index=False)

    issues = validate_scoring(scoring_df)
    if issues:
        (outputs_dir / "validation_report.txt").write_text(
            "\n".join(issues) + "\n", encoding="utf-8"
        )

    merged = apply_scoring(recs_df, scoring_df)
    merged.to_csv(outputs_dir / "per_recommendation_scored.csv", index=False)

    sources = sorted(merged["source"].unique().tolist())
    summary = compute_summary_metrics(merged, sources, human_source=args.human_source)
    summary.to_csv(outputs_dir / "summary_metrics.csv", index=False)

    similarity = compute_similarity_matrix(merged, sources)
    similarity.to_csv(outputs_dir / "similarity_matrix.csv")

    write_latex_tables(summary, similarity, outputs_dir / "latex_tables.tex")

    plot_accepted_by_source(summary, outputs_dir / "accepted_by_source.png")
    plot_invalid_rate(summary, outputs_dir / "invalid_rate_by_source.png")
    plot_jaccard_heatmap(similarity, outputs_dir / "jaccard_heatmap.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
