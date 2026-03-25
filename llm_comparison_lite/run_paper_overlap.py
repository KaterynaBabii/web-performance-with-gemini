#!/usr/bin/env python3
"""
Gemini vs independent human engineer — paper metrics (overlap, agreement, etc.).

Reads the same JSON shape as run_analysis.py but only:
  data/gemini.json
  data/human.json

Canonical match key: lowercased endpoint + normalized category (see paper_overlap.py).

Usage (from llm_comparison_lite/):
  python3 run_paper_overlap.py --data-dir data --out-dir outputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_comparison_lite.io import load_recommendations
from llm_comparison_lite.paper_overlap import (
    compute_gemini_human_paper_metrics,
    metrics_to_csv_row,
    metrics_to_latex_table,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Paper table: Gemini vs human overlap metrics")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = ap.parse_args()

    data_dir = args.data_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    gemini = load_recommendations(data_dir / "gemini.json")
    human = load_recommendations(data_dir / "human.json")

    m = compute_gemini_human_paper_metrics(gemini, human)
    df = metrics_to_csv_row(m)
    csv_path = out_dir / "paper_overlap_summary.csv"
    df.to_csv(csv_path, index=False)

    tex = metrics_to_latex_table(
        m,
        caption=(
            "Quantitative comparison of offline Gemini recommendations versus an independent "
            "human performance engineer on identical artifacts. Overlap uses exact matches on "
            "normalized endpoint and primary category."
        ),
        label="tab:gemini_human_overlap",
    )
    tex_path = out_dir / "table_gemini_human_overlap.tex"
    tex_path.write_text(tex, encoding="utf-8")

    print("Gemini vs human (paper metrics)")
    print(f"  |H|={m['NH']}  |G|={m['NG']} (dedup keys; rows={m['NG_rows']})  |G∩H|={m['NO']}")
    print(f"  Agreement |G∩H|/|H| = {m['AR_pct']:.2f}%")
    print(f"  Gemini |G∩H|/|G|   = {m['GP_pct']:.2f}%")
    print(f"  Human-only={m['HO']}  Gemini-only valid={m['GV']}  Invalid Gemini rows={m['NI']} ({m['NIR_pct']:.2f}%)")
    print(f"Wrote {csv_path}")
    print(f"Wrote {tex_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
