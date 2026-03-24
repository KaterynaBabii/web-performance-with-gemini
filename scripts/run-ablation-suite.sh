#!/bin/bash
# Ablation study: isolate indexing, caching, and query-rewrite effects vs full baseline.
# Writes under results/ablation/<variant>/ for use with:
#   python3 scripts/compute-statistics.py ablation
#
# Variants (same code paths as main paper; only DB + env flags differ):
#   baseline       — dropped perf indexes, ENABLE_REDIS_CACHE=0, BATCH=0, OPT_SEARCH=0
#   index_only     — optimized indexes, all ENABLE_*=0 (no cache, N+1 + slow search)
#   cache_only     — dropped perf indexes, ENABLE_REDIS_CACHE=1, BATCH=0, OPT_SEARCH=0
#   query_opt_only — dropped perf indexes, ENABLE_REDIS_CACHE=0, BATCH=1, OPT_SEARCH=1
#
# Defaults: LOAD=150 users, REPS=10, duration 3m per run (override with env vars).

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

LOAD="${ABLATION_LOAD:-150}"
REPS="${ABLATION_REPS:-10}"

get_spawn_rate() {
  local users=$1
  if [ "$users" -le 50 ]; then echo 5
  elif [ "$users" -le 100 ]; then echo 10
  elif [ "$users" -le 150 ]; then echo 15
  elif [ "$users" -le 200 ]; then echo 20
  elif [ "$users" -le 250 ]; then echo 25
  else echo 30
  fi
}

apply_db_baseline() {
  docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
    < "$PROJECT_ROOT/db/indexes_baseline_drop.sql" > /dev/null 2>&1 || true
}

apply_db_optimized() {
  docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
    < "$PROJECT_ROOT/db/indexes_optimized.sql" > /dev/null 2>&1
}

# Args: redis batch opt_search [label]
start_stack() {
  local er="$1"
  local eb="$2"
  local eo="$3"
  echo "[STACK] APP_VERSION=baseline ENABLE_REDIS_CACHE=$er ENABLE_BATCH_DASHBOARD=$eb ENABLE_OPT_SEARCH=$eo"
  APP_VERSION=baseline \
    ENABLE_REDIS_CACHE="$er" \
    ENABLE_BATCH_DASHBOARD="$eb" \
    ENABLE_OPT_SEARCH="$eo" \
    docker compose up -d --force-recreate > /dev/null 2>&1
}

run_variant_load_tests() {
  local variant=$1
  local users=$2
  local spawn_rate
  spawn_rate=$(get_spawn_rate "$users")
  local out_dir="$PROJECT_ROOT/results/ablation/$variant"
  mkdir -p "$out_dir"

  echo ""
  echo "================================================================================"
  echo "Ablation variant: $variant | Users: $users | Reps: $REPS"
  echo "================================================================================"

  for rep in $(seq 1 "$REPS"); do
    echo ""
    echo "--- $variant | users=$users | run $rep / $REPS ---"
    docker compose restart app > /dev/null 2>&1
    echo "[METRICS] Warmup 10s after app restart..."
    sleep 10

    cd "$PROJECT_ROOT/loadtest"
    python3 -m locust \
      -H http://localhost:3000 \
      --users="$users" \
      --spawn-rate="$spawn_rate" \
      --run-time=3m \
      --headless \
      --csv="$out_dir/${users}_run${rep}" \
      --loglevel=WARNING > /dev/null 2>&1

    sleep 5
    curl -s "http://localhost:3000/metrics" > "$out_dir/${users}_run${rep}.json" || true
    curl -s -X POST "http://localhost:3000/metrics/export" > /dev/null 2>&1 || true

    if [ -f "$out_dir/${users}_run${rep}_stats.csv" ]; then
      mv "$out_dir/${users}_run${rep}_stats.csv" "$out_dir/locust_${users}_run${rep}.csv"
    fi
    echo "✅ Saved $out_dir/${users}_run${rep}.json"
    sleep 10
  done
}

echo "================================================================================"
echo "ABLATION SUITE"
echo "Load level: $LOAD users | Repetitions: $REPS"
echo "Results: results/ablation/{baseline,index_only,cache_only,query_opt_only}/"
echo "Stats:   ABLATION_LOAD=$LOAD python3 scripts/compute-statistics.py ablation"
echo "================================================================================"

# --- baseline: no indexes, all flags off ---
echo ""
echo ">>> Variant: baseline"
apply_db_baseline
start_stack 0 0 0
sleep 15
run_variant_load_tests "baseline" "$LOAD"

# --- index only: optimized indexes, no cache / no code-path flags ---
echo ""
echo ">>> Variant: index_only"
apply_db_optimized
start_stack 0 0 0
sleep 15
run_variant_load_tests "index_only" "$LOAD"

# --- cache only: baseline DB, Redis cache on recommendations only ---
echo ""
echo ">>> Variant: cache_only"
apply_db_baseline
start_stack 1 0 0
sleep 15
run_variant_load_tests "cache_only" "$LOAD"

# --- query optimization only: batched dashboard + opt search, no Redis, baseline DB ---
echo ""
echo ">>> Variant: query_opt_only"
apply_db_baseline
start_stack 0 1 1
sleep 15
run_variant_load_tests "query_opt_only" "$LOAD"

echo ""
echo "================================================================================"
echo "✅ Ablation suite complete."
echo "Run: ABLATION_LOAD=$LOAD python3 scripts/compute-statistics.py ablation"
echo "================================================================================"
