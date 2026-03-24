#!/bin/bash
# Paper ablation at 300 users: index_only, query_opt, cache_only (n=10 each).
# Uses docker-compose overrides + DB scripts. Baseline/Gemini grid: use run-benchmark-grid.sh.
#
# Prerequisites: Docker running, postgres container web-gemini-postgres, schema loaded.
#
# Output:
#   results/{index_only,query_opt,cache_only}/300_run{k}.json
#   results/{...}/locust_300_run{k}.csv
#
# Optional: ABLATION_EXTRA=5 to run reps 11–15 after an initial 10 (CV follow-up).

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

USERS=300
REPS="${ABLATION_REPS:-10}"
START_REP="${ABLATION_START_REP:-1}"
END_REP=$((START_REP + REPS - 1))

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
  echo "[DB] Dropping optimized / ablation indexes (baseline catalog)..."
  docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
    < "$PROJECT_ROOT/db/indexes_baseline_drop.sql" > /dev/null 2>&1 || true
}

apply_db_index_pair() {
  apply_db_baseline
  echo "[DB] Applying ablation index pair (GIN + composite category_id, created_at)..."
  docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
    < "$PROJECT_ROOT/db/indexes_ablation_index_only.sql" > /dev/null 2>&1
}

run_variant() {
  local name=$1
  local compose_extra=$2
  local db_mode=$3

  local spawn_rate
  spawn_rate=$(get_spawn_rate "$USERS")

  echo ""
  echo "################################################################################"
  echo "# Variant: $name | users=$USERS | reps $START_REP..$END_REP"
  echo "################################################################################"

  case "$db_mode" in
    baseline_only)
      apply_db_baseline
      ;;
    index_pair)
      apply_db_index_pair
      ;;
    *)
      echo "Unknown db_mode: $db_mode" >&2
      exit 1
      ;;
  esac

  echo "[STACK] docker compose -f docker-compose.yml -f $compose_extra up -d --force-recreate"
  docker compose -f docker-compose.yml -f "$compose_extra" up -d --force-recreate > /dev/null 2>&1

  echo "[STACK] Waiting 15s..."
  sleep 15

  local results_dir="$PROJECT_ROOT/results/$name"
  mkdir -p "$results_dir"

  for rep in $(seq "$START_REP" "$END_REP"); do
    echo ""
    echo "------------------------------------------------------------------------"
    echo " $name | run $rep / $END_REP | spawn_rate=$spawn_rate | 3m"
    echo "------------------------------------------------------------------------"

    docker compose -f docker-compose.yml -f "$compose_extra" restart app > /dev/null 2>&1
    echo "[METRICS] App restarted; warmup 10s..."
    sleep 10
    curl -s http://localhost:3000/metrics > /dev/null || echo "WARNING: /metrics not reachable"

    cd "$PROJECT_ROOT/loadtest"
    python3 -m locust \
      -H http://localhost:3000 \
      --users="$USERS" \
      --spawn-rate="$spawn_rate" \
      --run-time=3m \
      --headless \
      --csv="$results_dir/${USERS}_run${rep}" \
      --loglevel=WARNING > /dev/null 2>&1

    sleep 5
    curl -s http://localhost:3000/metrics > "$results_dir/${USERS}_run${rep}.json" || {
      echo "WARNING: failed to save metrics JSON"
    }
    curl -s -X POST http://localhost:3000/metrics/export > /dev/null 2>&1 || true

    local stats_src="$results_dir/${USERS}_run${rep}_stats.csv"
    local stats_dst="$results_dir/locust_${USERS}_run${rep}.csv"
    if [ -f "$stats_src" ]; then
      mv "$stats_src" "$stats_dst"
    else
      echo "WARNING: missing Locust stats: $stats_src"
    fi

    python3 "$PROJECT_ROOT/scripts/canon-metrics-json.py" \
      "$results_dir/${USERS}_run${rep}.json" \
      "$results_dir/locust_${USERS}_run${rep}.csv" || true

    echo "[OK] $name run $rep saved."
    sleep 15
  done
}

echo "================================================================================"
echo "PAPER ABLATION @ 300 users — index_only, query_opt, cache_only"
echo "Repetitions: $START_REP .. $END_REP (set ABLATION_REPS / ABLATION_START_REP to adjust)"
echo "Optional: ABLATION_VARIANT=index_only|query_opt|cache_only to run one variant only"
echo "================================================================================"

run_all() {
  run_variant "index_only" "docker-compose.index_only.yml" "index_pair"
  run_variant "query_opt" "docker-compose.query_opt.yml" "index_pair"
  run_variant "cache_only" "docker-compose.cache_only.yml" "baseline_only"
}

if [ -n "${ABLATION_VARIANT:-}" ]; then
  case "${ABLATION_VARIANT}" in
    index_only)
      run_variant "index_only" "docker-compose.index_only.yml" "index_pair" ;;
    query_opt)
      run_variant "query_opt" "docker-compose.query_opt.yml" "index_pair" ;;
    cache_only)
      run_variant "cache_only" "docker-compose.cache_only.yml" "baseline_only" ;;
    *)
      echo "Unknown ABLATION_VARIANT=${ABLATION_VARIANT}" >&2
      exit 1 ;;
  esac
else
  run_all
fi

echo ""
echo "================================================================================"
echo "Done. Re-canonicalize existing JSON if needed:"
echo "  python3 scripts/canon-metrics-json.py results/index_only/300_run1.json results/index_only/locust_300_run1.csv"
echo "Then: python3 scripts/export-paper-tables.py"
echo "================================================================================"
