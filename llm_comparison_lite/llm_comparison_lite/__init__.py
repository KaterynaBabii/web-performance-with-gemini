"""
Lightweight multi-model recommendation comparison.

Loads gemini.json, gpt4.json, claude.json, human.json → normalizes categories →
computes rates, human agreement (Jaccard), LLM–LLM Jaccard → summary.csv,
pairwise_overlap.csv, category_breakdown.csv, optional LaTeX + matplotlib.

CLI: run_analysis.py in the parent directory. Docs: ../LIGHTWEIGHT_COMPARISON.md
"""

__version__ = "1.0.0"
