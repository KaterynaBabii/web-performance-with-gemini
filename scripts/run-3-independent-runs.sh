#!/bin/bash
# Run 3 independent test suites for IEEE Access paper statistics

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "RUNNING 3 INDEPENDENT TEST SUITES"
echo "For IEEE Access Paper Statistics"
echo "=========================================="
echo ""
echo "This will take approximately 90 minutes (30 min × 3 runs)"
echo ""

for run in 1 2 3; do
    echo ""
    echo "=========================================="
    echo "RUN $run of 3"
    echo "=========================================="
    echo ""
    
    # Run the full test suite
    ./scripts/run-all-tests-final.sh
    
    # Rename results with run number
    echo ""
    echo "Renaming results for run $run..."
    
    for folder in baseline gemini; do
        for load in 50 150 250; do
            # Rename JSON files
            if [ -f "results/$folder/$load.json" ]; then
                mv "results/$folder/$load.json" "results/$folder/${load}_run${run}.json"
                echo "  ✅ Renamed: results/$folder/${load}_run${run}.json"
            fi
            
            # Rename CSV files
            if [ -f "results/$folder/locust_$load.csv" ]; then
                mv "results/$folder/locust_$load.csv" "results/$folder/locust_${load}_run${run}.csv"
                echo "  ✅ Renamed: results/$folder/locust_${load}_run${run}.csv"
            fi
        done
    done
    
    echo ""
    echo "✅ Run $run complete"
    
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
echo "Now compute statistics:"
echo "  python3 scripts/compute-statistics.py all"
echo ""

