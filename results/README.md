# `results/` directory

- **Raw benchmark artifacts:** `baseline/`, `gemini/`, and optional ablation folders (`index_only/`, `query_opt/`, `cache_only/`, `ablation/`). For git, **only** `{load}_run{k}.json` and `locust_{load}_run{k}.csv` are tracked; other CSVs (failures, stats_history, metrics-*, requests-*) are gitignored noise.  
**Full grid expectations:** `scripts/run-benchmark-grid.sh` runs **10** Locust runs (repetitions `run1` … `run10`) at **each** user level **50, 100, 150, 200, 250, 300** per system arm (default: both `baseline` and `gemini`).

Shorter legacy scripts (`run-baseline-load-tests.sh` / `run-optimized-load-tests.sh`) only hit **50, 150, 250** once each—they do **not** replace the 10×6 grid for full statistical comparison.

