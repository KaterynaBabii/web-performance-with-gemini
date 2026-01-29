#!/bin/bash
# Run only Baseline 150 and 250 tests (for getting 3 runs for statistics)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running Baseline 150 and 250 Tests"
echo "To get 3 runs for statistics"
echo "=========================================="

# Ensure baseline mode
echo "Dropping indexes..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_baseline_drop.sql" > /dev/null 2>&1

echo "Starting in baseline mode..."
APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 \
    docker compose up -d --force-recreate > /dev/null 2>&1
sleep 15

# Function to run a test
run_test() {
    local load=$1
    local run_num=$2
    
    echo ""
    echo "=========================================="
    echo "Baseline $load - Run $run_num"
    echo "=========================================="
    
    docker compose restart app > /dev/null 2>&1
    sleep 10
    
    cd "$PROJECT_ROOT/loadtest"
    python3 -m locust \
        -H http://localhost:3000 \
        --users=$load \
        --spawn-rate=$((load / 15)) \
        --run-time=3m \
        --headless \
        --csv=../results/baseline/${load}_run${run_num} \
        --loglevel=WARNING 2>&1 | tail -3
    
    sleep 5
    curl -s http://localhost:3000/metrics > ../results/baseline/${load}_run${run_num}.json
    
    echo "✅ Run $run_num complete for load $load"
}

# Run 150 users - 2 more times (assuming 1 already exists)
echo ""
echo "Running Baseline 150 (2 more runs)..."
run_test 150 2
sleep 10
run_test 150 3

# Run 250 users - 2 more times (assuming 1 already exists)
echo ""
echo "Running Baseline 250 (2 more runs)..."
run_test 250 2
sleep 10
run_test 250 3

echo ""
echo "=========================================="
echo "✅ All tests complete"
echo "=========================================="
echo ""
echo "Now run: python3 scripts/compute-statistics.py all"
echo ""

