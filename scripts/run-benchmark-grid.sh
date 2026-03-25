#!/bin/bash
# Run extended benchmark grid (baseline vs optimized)
# - Systems: baseline, gemini (optimized)
# - Loads: 50, 100, 150, 200, 250, 300 users
# - Repetitions: 10 per (system, load) condition

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Which arms to run: all | baseline | gemini (re-run baseline only: BENCHMARK_GRID_SYSTEMS=baseline)
case "${BENCHMARK_GRID_SYSTEMS:-all}" in
  baseline|Baseline)
    SYSTEMS=("baseline")
    ;;
  gemini|Gemini|optimized)
    SYSTEMS=("gemini")
    ;;
  all|*)
    SYSTEMS=("baseline" "gemini")
    ;;
esac

LOADS=(50 100 150 200 250 300)
REPS="${BENCHMARK_GRID_REPS:-10}"

# Derive spawn rate heuristically from load
get_spawn_rate() {
  local users=$1
  if [ "$users" -le 50 ]; then
    echo 5
  elif [ "$users" -le 100 ]; then
    echo 10
  elif [ "$users" -le 150 ]; then
    echo 15
  elif [ "$users" -le 200 ]; then
    echo 20
  elif [ "$users" -le 250 ]; then
    echo 25
  else
    echo 30
  fi
}

run_condition() {
  local system=$1   # baseline | gemini
  local users=$2
  local rep=$3

  local spawn_rate
  spawn_rate=$(get_spawn_rate "$users")

  echo ""
  echo "================================================================================"
  echo "System: $system | Users: $users | Run: $rep / $REPS"
  echo "Spawn rate: $spawn_rate, Duration: 3m"
  echo "================================================================================"

  # Configure DB indexes
  if [ "$system" = "baseline" ]; then
    echo "[DB] Dropping optimized indexes for baseline..."
    docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
      < "$PROJECT_ROOT/db/indexes_baseline_drop.sql" > /dev/null 2>&1 || true
  else
    echo "[DB] Applying optimized indexes for Gemini..."
    docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
      < "$PROJECT_ROOT/db/indexes_optimized.sql" > /dev/null 2>&1
  fi

  # Start stack with correct feature flags
  if [ "$system" = "baseline" ]; then
    echo "[STACK] Starting baseline stack (no cache, no optimizations)..."
    APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 \
      docker compose up -d --force-recreate > /dev/null 2>&1
  else
    echo "[STACK] Starting Gemini-optimized stack (cache + query + batching)..."
    APP_VERSION=optimized ENABLE_REDIS_CACHE=1 ENABLE_BATCH_DASHBOARD=1 ENABLE_OPT_SEARCH=1 \
      docker compose up -d --force-recreate > /dev/null 2>&1
  fi

  echo "[STACK] Waiting 15 seconds for services to be ready..."
  sleep 15

  # Reset metrics by restarting app container
  echo "[METRICS] Restarting app to reset in-memory metrics..."
  docker compose restart app > /dev/null 2>&1
  echo "[METRICS] Warmup sleep 10s to ensure clean start (recorded in logs only)."
  sleep 10

  # Verify metrics are near zero before the run
  echo "[METRICS] Initial /metrics snapshot (should be zeros)..."
  curl -s http://localhost:3000/metrics || echo "WARNING: /metrics not reachable"

  # Run Locust for this condition
  echo "[LOAD] Starting Locust: users=$users, spawn_rate=$spawn_rate, duration=3m"
  cd "$PROJECT_ROOT/loadtest"

  local results_dir="../results/$system"
  mkdir -p "$results_dir"

  python3 -m locust \
    -H http://localhost:3000 \
    --users="$users" \
    --spawn-rate="$spawn_rate" \
    --run-time=3m \
    --headless \
    --csv="$results_dir/${users}_run${rep}" \
    --loglevel=WARNING > /dev/null 2>&1

  echo "[LOAD] Locust run complete. Waiting 5s for trailing requests..."
  sleep 5

  # Collect metrics AFTER test completes, BEFORE any restart
  echo "[METRICS] Collecting /metrics JSON for this run..."
  curl -s http://localhost:3000/metrics > "$results_dir/${users}_run${rep}.json" || {
    echo "WARNING: Failed to collect /metrics JSON for $system $users run $rep"
  }

  # Also trigger CSV export via metrics export endpoint (server-side summary)
  echo "[METRICS] Triggering server-side CSV export via /metrics/export..."
  curl -s -X POST http://localhost:3000/metrics/export > /dev/null 2>&1 || {
    echo "WARNING: /metrics/export failed (exportToCSV)"
  }

  # Rename Locust stats CSV to a standard per-run name
  local stats_src="$results_dir/${users}_run${rep}_stats.csv"
  local stats_dst="$results_dir/locust_${users}_run${rep}.csv"
  if [ -f "$stats_src" ]; then
    mv "$stats_src" "$stats_dst"
    echo "[RESULTS] Saved Locust stats CSV: $stats_dst"
  else
    echo "WARNING: Expected Locust stats CSV not found: $stats_src"
  fi

  if [ -f "$results_dir/${users}_run${rep}.json" ]; then
    python3 "$PROJECT_ROOT/scripts/canon-metrics-json.py" \
      "$results_dir/${users}_run${rep}.json" \
      "$results_dir/locust_${users}_run${rep}.csv" 2>/dev/null || true
  fi

  echo "[RESULTS] Saved metrics JSON: $results_dir/${users}_run${rep}.json"
  echo "✅ Condition complete: system=$system, users=$users, run=$rep"
}

echo "================================================================================"
echo "EXTENDED BENCHMARK GRID"
echo "Systems: ${SYSTEMS[*]}  (set BENCHMARK_GRID_SYSTEMS=baseline|gemini|all)"
echo "Loads:   ${LOADS[*]}"
echo "Runs:    $REPS repetitions per (system, load)"
echo "================================================================================"

for system in "${SYSTEMS[@]}"; do
  for users in "${LOADS[@]}"; do
    for rep in $(seq 1 "$REPS"); do
      run_condition "$system" "$users" "$rep"
      echo ""
      echo "Sleeping 15s before next condition to avoid overlapping effects..."
      sleep 15
    done
  done
done

echo ""
echo "================================================================================"
echo "✅ Extended benchmark grid complete."
echo "Results stored under results/baseline and results/gemini."
echo "You can now run: python3 scripts/compute-statistics.py all"
echo "================================================================================"

