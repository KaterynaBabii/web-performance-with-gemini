"""LaTeX table generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def dataframe_to_booktabs(df: pd.DataFrame, caption: str, label: str) -> str:
    lines = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\begin{tabular}{%s}" % ("l" * len(df.columns)))
    lines.append("\\toprule")
    lines.append(" & ".join(df.columns) + " \\\\")
    lines.append("\\midrule")
    for _, row in df.iterrows():
        vals = [str(v) for v in row.tolist()]
        lines.append(" & ".join(vals) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def write_latex_tables(
    summary: pd.DataFrame,
    similarity: pd.DataFrame,
    out_path: Path,
) -> None:
    summary_fmt = summary.copy()
    float_cols = [
        "acceptance_rate",
        "invalid_rate",
        "jaccard_vs_human",
        "precision_vs_human",
        "recall_vs_human",
        "mean_time_to_analysis_minutes",
    ]
    for col in float_cols:
        if col in summary_fmt.columns:
            summary_fmt[col] = summary_fmt[col].map(
                lambda v: f"{v:.4f}" if pd.notna(v) else "NA"
            )
    summary_tex = dataframe_to_booktabs(
        summary_fmt,
        caption="Summary metrics per source.",
        label="tab:summary_metrics",
    )

    sim_fmt = similarity.copy()
    sim_fmt = sim_fmt.apply(lambda col: col.map(lambda v: f"{v:.4f}" if pd.notna(v) else "NA"))
    sim_tex = dataframe_to_booktabs(
        sim_fmt.reset_index().rename(columns={"index": "source"}),
        caption="Jaccard similarity between sources (category sets).",
        label="tab:jaccard_matrix",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(summary_tex + "\n\n" + sim_tex + "\n", encoding="utf-8")
