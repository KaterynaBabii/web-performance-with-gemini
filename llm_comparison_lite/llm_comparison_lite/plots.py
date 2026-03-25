"""Optional matplotlib figures for slides or supplementary material."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_category_counts(
    breakdown: pd.DataFrame,
    out_path: Path,
    *,
    title: str = "Recommendations by category (normalized)",
) -> None:
    """Stacked or grouped bar: one group per LLM, bars = categories."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # LLMs only for this plot (exclude human unless present and desired)
    sub = breakdown[breakdown["model"].isin(["gemini", "gpt4", "claude"])].copy()
    if sub.empty:
        return

    pivot = sub.pivot_table(
        index="category_normalized",
        columns="model",
        values="n",
        aggfunc="sum",
        fill_value=0,
    )

    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot.T.plot(kind="bar", ax=ax, rot=0)
    ax.set_ylabel("Count")
    ax.set_xlabel("Model")
    ax.set_title(title)
    ax.legend(title="Category", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_jaccard_heatmap(pairwise: pd.DataFrame, out_path: Path) -> None:
    """3×3 symmetric heatmap of pairwise Jaccard between LLMs."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    models = ["gemini", "gpt4", "claude"]
    mat = np.eye(len(models))
    idx = {m: i for i, m in enumerate(models)}
    for _, row in pairwise.iterrows():
        a, b = row["model_a"], row["model_b"]
        if a in idx and b in idx:
            v = float(row["jaccard"])
            i, j = idx[a], idx[b]
            mat[i, j] = mat[j, i] = v

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(mat, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(len(models)))
    ax.set_yticks(range(len(models)))
    ax.set_xticklabels(models)
    ax.set_yticklabels(models)
    for i in range(len(models)):
        for j in range(len(models)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", color="black", fontsize=9)
    ax.set_title("Pairwise Jaccard (endpoint + category key)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
