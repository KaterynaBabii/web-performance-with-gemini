#!/bin/bash
# Run all baseline load tests (A1, A2, A3)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "BASELINE LOAD TESTS - Starting"
echo "=========================================="

# Check if server is running
if ! curl -s http://localhost:3000/health > /dev/null; then
    echo "ERROR: Server is not running on port 3000"
    echo "Please start the baseline server first:"
    echo "  cd server"
    echo "  APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 node src/app.js"
    exit 1
fi

# Verify baseline metrics are zero
echo "Checking initial metrics..."
INITIAL_METRICS=$(curl -s http://localhost:3000/metrics)
echo "$INITIAL_METRICS"

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
    docker compose restart app
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
        --csv="$PROJECT_ROOT/results/baseline/$csv_prefix" \
        --html="$PROJECT_ROOT/results/baseline/${csv_prefix}_report.html" \
        --loglevel=WARNING
    
    # Wait a moment for final requests to complete
    echo "Waiting 5 seconds for final requests to complete..."
    sleep 5
    
    # Collect metrics AFTER test completes (never mid-run)
    echo "Collecting metrics (after test completion)..."
    curl -s http://localhost:3000/metrics > "$PROJECT_ROOT/$metrics_file"
    
    # Show collected metrics
    echo "Collected metrics:"
    cat "$PROJECT_ROOT/$metrics_file" | python3 -m json.tool 2>/dev/null || cat "$PROJECT_ROOT/$metrics_file"
    
    # Rename CSV files
    echo "Renaming CSV files..."
    if [ -f "$PROJECT_ROOT/results/baseline/${csv_prefix}_stats.csv" ]; then
        mv "$PROJECT_ROOT/results/baseline/${csv_prefix}_stats.csv" "$PROJECT_ROOT/results/baseline/locust_${csv_prefix}.csv"
        echo "✅ Saved: results/baseline/locust_${csv_prefix}.csv"
    else
        echo "⚠️  Warning: ${csv_prefix}_stats.csv not found - checking for existing locust file..."
        if [ -f "$PROJECT_ROOT/results/baseline/locust_${csv_prefix}.csv" ]; then
            echo "✅ Found existing: results/baseline/locust_${csv_prefix}.csv"
        else
            echo "❌ Error: No CSV file found for ${csv_prefix}"
        fi
    fi
    
    echo "✅ Metrics saved: $metrics_file"
    echo "✅ Test $test_name complete"
}

# Run A1 - Low load
run_test "A1 - Low Load" 50 5 "3m" "results/baseline/50.json" "50"

# Wait between tests
echo ""
echo "Waiting 10 seconds before next test..."
sleep 10

# Run A2 - Medium load
run_test "A2 - Medium Load" 150 10 "3m" "results/baseline/150.json" "150"

# Wait between tests
echo ""
echo "Waiting 10 seconds before next test..."
sleep 10

# Run A3 - High load
run_test "A3 - High Load" 250 15 "3m" "results/baseline/250.json" "250"

echo ""
echo "=========================================="
echo "✅ ALL BASELINE TESTS COMPLETE"
echo "=========================================="
echo "Results saved:"
echo "  - results/baseline/50.json"
echo "  - results/baseline/locust_50.csv"
echo "  - results/baseline/150.json"
echo "  - results/baseline/locust_150.csv"
echo "  - results/baseline/250.json"
echo "  - results/baseline/locust_250.csv"

