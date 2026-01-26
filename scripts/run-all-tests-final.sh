#!/bin/bash
# Run all tests with proper baseline and optimized configurations

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "FINAL TEST RUN - Baseline and Gemini"
echo "=========================================="

# Function to run a single test
run_test() {
    local test_name=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local metrics_file=$5
    local csv_prefix=$6
    
    echo ""
    echo "=========================================="
    echo "Running $test_name"
    echo "  Users: $users"
    echo "  Spawn rate: $spawn_rate"
    echo "  Duration: $duration"
    echo "=========================================="
    
    # Reset metrics by restarting API
    echo "Resetting metrics (restarting API)..."
    docker compose restart app > /dev/null 2>&1
    echo "Waiting 10 seconds for server to be ready..."
    sleep 10
    
    # Verify metrics are zero
    INITIAL_METRICS=$(curl -s http://localhost:3000/metrics)
    echo "Initial metrics: $INITIAL_METRICS"
    
    # Run Locust
    echo "Starting Locust load test..."
    cd "$PROJECT_ROOT/loadtest"
    python3 -m locust \
        -H http://localhost:3000 \
        --users=$users \
        --spawn-rate=$spawn_rate \
        --run-time=$duration \
        --headless \
        --csv="$PROJECT_ROOT/results/$csv_prefix" \
        --html="$PROJECT_ROOT/results/${csv_prefix}_report.html" \
        --loglevel=WARNING 2>&1 | tail -5
    
    # Wait a moment for final requests to complete
    echo "Waiting 5 seconds for final requests to complete..."
    sleep 5
    
    # Collect metrics AFTER test completes
    echo "Collecting metrics (after test completion)..."
    curl -s http://localhost:3000/metrics > "$PROJECT_ROOT/$metrics_file"
    
    # Show collected metrics
    echo "Collected metrics:"
    cat "$PROJECT_ROOT/$metrics_file" | python3 -m json.tool 2>/dev/null || cat "$PROJECT_ROOT/$metrics_file"
    
    # Rename CSV files
    echo "Renaming CSV files..."
    if [ -f "$PROJECT_ROOT/results/${csv_prefix}_stats.csv" ]; then
        mv "$PROJECT_ROOT/results/${csv_prefix}_stats.csv" "$PROJECT_ROOT/results/locust_${csv_prefix}.csv"
        echo "✅ Saved: results/locust_${csv_prefix}.csv"
    fi
    
    echo "✅ Metrics saved: $metrics_file"
    echo "✅ Test $test_name complete"
}

# ==========================================
# PHASE 1: BASELINE TESTS
# ==========================================
echo ""
echo "=========================================="
echo "PHASE 1: BASELINE TESTS"
echo "=========================================="

# Drop indexes
echo "Dropping all performance indexes..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_baseline_drop.sql" > /dev/null 2>&1

# Start in baseline mode
echo "Starting in baseline mode (no cache, no optimizations)..."
APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 \
    docker compose up -d --force-recreate > /dev/null 2>&1
sleep 15

# Verify baseline mode
echo "Verifying baseline mode..."
ENV_CHECK=$(docker exec web-gemini-app printenv | grep -E "ENABLE|APP_VERSION" || true)
echo "$ENV_CHECK"
if echo "$ENV_CHECK" | grep -q "ENABLE_REDIS_CACHE=1"; then
    echo "ERROR: Redis cache is still enabled!"
    exit 1
fi

# Run baseline tests
run_test "Baseline 50" 50 5 "3m" "results/baseline/50.json" "baseline/50"
sleep 10

run_test "Baseline 150" 150 10 "3m" "results/baseline/150.json" "baseline/150"
sleep 10

run_test "Baseline 250" 250 10 "3m" "results/baseline/250.json" "baseline/250"
sleep 10

# ==========================================
# PHASE 2: GEMINI-OPTIMIZED TESTS
# ==========================================
echo ""
echo "=========================================="
echo "PHASE 2: GEMINI-OPTIMIZED TESTS"
echo "=========================================="

# Apply optimized indexes
echo "Applying optimized indexes..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_optimized.sql" > /dev/null 2>&1

# Start in optimized mode
echo "Starting in optimized mode (with cache, optimizations)..."
APP_VERSION=optimized ENABLE_REDIS_CACHE=1 ENABLE_BATCH_DASHBOARD=1 ENABLE_OPT_SEARCH=1 \
    docker compose up -d --force-recreate > /dev/null 2>&1
sleep 15

# Verify optimized mode
echo "Verifying optimized mode..."
ENV_CHECK=$(docker exec web-gemini-app printenv | grep -E "ENABLE|APP_VERSION" || true)
echo "$ENV_CHECK"
if echo "$ENV_CHECK" | grep -q "ENABLE_REDIS_CACHE=0"; then
    echo "ERROR: Redis cache is not enabled!"
    exit 1
fi

# Run Gemini tests
run_test "Gemini 50" 50 5 "3m" "results/gemini/50.json" "gemini/50"
sleep 10

run_test "Gemini 150" 150 10 "3m" "results/gemini/150.json" "gemini/150"
sleep 10

run_test "Gemini 250" 250 10 "3m" "results/gemini/250.json" "gemini/250"

# ==========================================
# PHASE 3: GENERATE RESULTS TABLE
# ==========================================
echo ""
echo "=========================================="
echo "PHASE 3: GENERATING RESULTS TABLE"
echo "=========================================="

cd "$PROJECT_ROOT"
python3 scripts/create-results-table.py

echo ""
echo "=========================================="
echo "✅ ALL TESTS COMPLETE"
echo "=========================================="
echo "Results saved to: results/RESULTS_TABLE.md"
cat results/RESULTS_TABLE.md

