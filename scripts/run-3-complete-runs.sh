#!/bin/bash
# Run complete test suite 3 times for IEEE Access paper statistics
# This ensures all configurations have 3 independent runs

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "RUNNING 3 COMPLETE TEST SUITES"
echo "For IEEE Access Paper (Mean ± SD)"
echo "=========================================="
echo ""
echo "This will take approximately 90 minutes (30 min × 3 runs)"
echo "Each run includes:"
echo "  - Baseline tests: 50, 150, 250 users"
echo "  - Gemini tests: 50, 150, 250 users"
echo ""

for run in 1 2 3; do
    echo ""
    echo "=========================================="
    echo "RUN $run of 3"
    echo "=========================================="
    echo ""
    
    # ==========================================
    # PHASE 1: BASELINE TESTS
    # ==========================================
    echo "PHASE 1: BASELINE TESTS (Run $run)"
    
    # Drop indexes
    echo "  Dropping all performance indexes..."
    docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_baseline_drop.sql" > /dev/null 2>&1
    
    # Start in baseline mode
    echo "  Starting in baseline mode..."
    APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 \
        docker compose up -d --force-recreate > /dev/null 2>&1
    sleep 15
    
    # Verify baseline mode
    ENV_CHECK=$(docker exec web-gemini-app printenv | grep -E "ENABLE_REDIS_CACHE" || true)
    if echo "$ENV_CHECK" | grep -q "ENABLE_REDIS_CACHE=1"; then
        echo "  ERROR: Redis cache is still enabled!"
        exit 1
    fi
    
    # Function to run a single baseline test
    run_baseline_test() {
        local load=$1
        local spawn_rate=$2
        
        echo "    Running Baseline $load users..."
        docker compose restart app > /dev/null 2>&1
        sleep 10
        
        cd "$PROJECT_ROOT/loadtest"
        python3 -m locust \
            -H http://localhost:3000 \
            --users=$load \
            --spawn-rate=$spawn_rate \
            --run-time=3m \
            --headless \
            --csv=../results/baseline/${load}_run${run} \
            --loglevel=WARNING > /dev/null 2>&1
        
        sleep 5
        curl -s http://localhost:3000/metrics > ../results/baseline/${load}_run${run}.json
        
        # Rename CSV file
        if [ -f "../results/baseline/${load}_run${run}_stats.csv" ]; then
            mv "../results/baseline/${load}_run${run}_stats.csv" "../results/baseline/locust_${load}_run${run}.csv"
        fi
        
        echo "    ✅ Baseline $load complete"
    }
    
    # Run baseline tests
    run_baseline_test 50 5
    sleep 5
    run_baseline_test 150 10
    sleep 5
    run_baseline_test 250 10
    sleep 10
    
    # ==========================================
    # PHASE 2: GEMINI-OPTIMIZED TESTS
    # ==========================================
    echo ""
    echo "PHASE 2: GEMINI-OPTIMIZED TESTS (Run $run)"
    
    # Apply optimized indexes
    echo "  Applying optimized indexes..."
    docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_optimized.sql" > /dev/null 2>&1
    
    # Start in optimized mode
    echo "  Starting in optimized mode..."
    APP_VERSION=optimized ENABLE_REDIS_CACHE=1 ENABLE_BATCH_DASHBOARD=1 ENABLE_OPT_SEARCH=1 \
        docker compose up -d --force-recreate > /dev/null 2>&1
    sleep 15
    
    # Verify optimized mode
    ENV_CHECK=$(docker exec web-gemini-app printenv | grep -E "ENABLE_REDIS_CACHE" || true)
    if echo "$ENV_CHECK" | grep -q "ENABLE_REDIS_CACHE=0"; then
        echo "  ERROR: Redis cache is not enabled!"
        exit 1
    fi
    
    # Function to run a single Gemini test
    run_gemini_test() {
        local load=$1
        local spawn_rate=$2
        
        echo "    Running Gemini $load users..."
        docker compose restart app > /dev/null 2>&1
        sleep 10
        
        cd "$PROJECT_ROOT/loadtest"
        python3 -m locust \
            -H http://localhost:3000 \
            --users=$load \
            --spawn-rate=$spawn_rate \
            --run-time=3m \
            --headless \
            --csv=../results/gemini/${load}_run${run} \
            --loglevel=WARNING > /dev/null 2>&1
        
        sleep 5
        curl -s http://localhost:3000/metrics > ../results/gemini/${load}_run${run}.json
        
        # Rename CSV file
        if [ -f "../results/gemini/${load}_run${run}_stats.csv" ]; then
            mv "../results/gemini/${load}_run${run}_stats.csv" "../results/gemini/locust_${load}_run${run}.csv"
        fi
        
        echo "    ✅ Gemini $load complete"
    }
    
    # Run Gemini tests
    run_gemini_test 50 5
    sleep 5
    run_gemini_test 150 10
    sleep 5
    run_gemini_test 250 10
    
    echo ""
    echo "✅ Run $run of 3 complete"
    
    if [ $run -lt 3 ]; then
        echo ""
        echo "Waiting 30 seconds before next run..."
        sleep 30
    fi
done

echo ""
echo "=========================================="
echo "✅ ALL 3 RUNS COMPLETE"
echo "=========================================="
echo ""
echo "Results saved with _run1, _run2, _run3 suffixes"
echo ""
echo "Now compute statistics:"
echo "  python3 scripts/compute-statistics.py all"
echo ""
echo "This will generate LaTeX table with mean ± SD for all metrics"
echo ""

