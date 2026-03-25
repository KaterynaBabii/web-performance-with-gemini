"""Matplotlib figures for summary metrics."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import pandas as pd


def plot_accepted_by_source(summary: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(summary["source"], summary["n_accepted"])
    ax.set_ylabel("Accepted recommendations")
    ax.set_xlabel("Source")
    ax.set_title("Accepted recommendations by source")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_invalid_rate(summary: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(summary["source"], summary["invalid_rate"])
    ax.set_ylabel("Invalid rate")
    ax.set_xlabel("Source")
    ax.set_title("Invalid recommendation rate by source")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_jaccard_heatmap(similarity: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(similarity.values, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(len(similarity.columns)))
    ax.set_yticks(range(len(similarity.index)))
    ax.set_xticklabels(similarity.columns)
    ax.set_yticklabels(similarity.index)
    for i in range(len(similarity.index)):
        for j in range(len(similarity.columns)):
            ax.text(j, i, f"{similarity.values[i, j]:.2f}", ha="center", va="center")
    ax.set_title("Jaccard similarity across sources")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
