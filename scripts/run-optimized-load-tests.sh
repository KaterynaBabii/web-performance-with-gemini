#!/bin/bash
# Run all optimized (Gemini-informed) load tests (B1, B2, B3)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "GEMINI-OPTIMIZED LOAD TESTS - Starting"
echo "=========================================="

# Check if server is running
if ! curl -s http://localhost:3000/health > /dev/null; then
    echo "ERROR: Server is not running on port 3000"
    echo "Please start the optimized server first:"
    echo "  docker compose up -d --build"
    exit 1
fi

# Verify optimized version
HEALTH=$(curl -s http://localhost:3000/health)
if echo "$HEALTH" | grep -q "optimized"; then
    echo "✅ Server is running in optimized mode"
else
    echo "⚠️  WARNING: Server may not be in optimized mode"
    echo "Health check: $HEALTH"
fi

# Verify server is running
echo "Checking server status..."
curl -s http://localhost:3000/health > /dev/null || {
    echo "ERROR: Server is not running"
    exit 1
}

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
        --csv="$PROJECT_ROOT/results/gemini/$csv_prefix" \
        --html="$PROJECT_ROOT/results/gemini/${csv_prefix}_report.html" \
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
    if [ -f "$PROJECT_ROOT/results/gemini/${csv_prefix}_stats.csv" ]; then
        mv "$PROJECT_ROOT/results/gemini/${csv_prefix}_stats.csv" "$PROJECT_ROOT/results/gemini/locust_${csv_prefix}.csv"
        echo "✅ Saved: results/gemini/locust_${csv_prefix}.csv"
    else
        echo "⚠️  Warning: ${csv_prefix}_stats.csv not found - checking for existing locust file..."
        if [ -f "$PROJECT_ROOT/results/gemini/locust_${csv_prefix}.csv" ]; then
            echo "✅ Found existing: results/gemini/locust_${csv_prefix}.csv"
        else
            echo "❌ Error: No CSV file found for ${csv_prefix}"
        fi
    fi
    
    echo "✅ Metrics saved: $metrics_file"
    echo "✅ Test $test_name complete"
}

# Run B1 - Low load
run_test "B1 - Low Load" 50 5 "3m" "results/gemini/50.json" "50"

# Wait between tests
echo ""
echo "Waiting 10 seconds before next test..."
sleep 10

# Run B2 - Medium load
run_test "B2 - Medium Load" 150 10 "3m" "results/gemini/150.json" "150"

# Wait between tests
echo ""
echo "Waiting 10 seconds before next test..."
sleep 10

# Run B3 - High load
run_test "B3 - High Load" 250 15 "3m" "results/gemini/250.json" "250"

echo ""
echo "=========================================="
echo "✅ ALL GEMINI-OPTIMIZED TESTS COMPLETE"
echo "=========================================="
echo "Results saved:"
echo "  - results/gemini/50.json"
echo "  - results/gemini/locust_50.csv"
echo "  - results/gemini/150.json"
echo "  - results/gemini/locust_150.csv"
echo "  - results/gemini/250.json"
echo "  - results/gemini/locust_250.csv"

