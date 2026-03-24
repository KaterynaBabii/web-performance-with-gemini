#!/bin/bash
# Re-run the main grid for **baseline only** (slow path):
# - DB: indexes_baseline_drop.sql (no GIN/composite/optimized indexes)
# - App: APP_VERSION=baseline, no Redis cache, N+1 dashboard, no FTS path
# - Loads: 50, 100, 150, 200, 250, 300 × REPS (default 10) × 3 min Locust each
#
# Usage (from repo root):
#   chmod +x scripts/run-baseline-grid.sh
#   ./scripts/run-baseline-grid.sh
#
# Optional:
#   BENCHMARK_GRID_REPS=10 ./scripts/run-baseline-grid.sh

set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export BENCHMARK_GRID_SYSTEMS=baseline
exec "$SCRIPT_DIR/run-benchmark-grid.sh"
