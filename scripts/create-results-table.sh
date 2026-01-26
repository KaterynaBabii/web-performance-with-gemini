#!/bin/bash
# Create a results comparison table from collected metrics

echo "=========================================="
echo "RESULTS COMPARISON TABLE"
echo "=========================================="
echo ""

# Find the most recent metrics files
BASELINE_CSV=$(ls -t results/baseline/metrics-*.csv 2>/dev/null | head -1)
OPTIMIZED_CSV=$(ls -t results/gemini/metrics-*.csv 2>/dev/null | head -1)

if [ -z "$BASELINE_CSV" ] || [ -z "$OPTIMIZED_CSV" ]; then
    echo "ERROR: Could not find metrics files."
    echo "Baseline: $BASELINE_CSV"
    echo "Optimized: $OPTIMIZED_CSV"
    exit 1
fi

echo "Using:"
echo "  Baseline: $BASELINE_CSV"
echo "  Optimized: $OPTIMIZED_CSV"
echo ""

# Extract values from CSV files
baseline_avg_latency=$(grep "Avg Latency" "$BASELINE_CSV" | cut -d',' -f2)
baseline_p95_latency=$(grep "P95 Latency" "$BASELINE_CSV" | cut -d',' -f2)
baseline_throughput=$(grep "Throughput" "$BASELINE_CSV" | cut -d',' -f2)
baseline_db_time=$(grep "Avg DB Query Time" "$BASELINE_CSV" | cut -d',' -f2)
baseline_cache_hit=$(grep "Cache Hit Ratio" "$BASELINE_CSV" | cut -d',' -f2)

optimized_avg_latency=$(grep "Avg Latency" "$OPTIMIZED_CSV" | cut -d',' -f2)
optimized_p95_latency=$(grep "P95 Latency" "$OPTIMIZED_CSV" | cut -d',' -f2)
optimized_throughput=$(grep "Throughput" "$OPTIMIZED_CSV" | cut -d',' -f2)
optimized_db_time=$(grep "Avg DB Query Time" "$OPTIMIZED_CSV" | cut -d',' -f2)
optimized_cache_hit=$(grep "Cache Hit Ratio" "$OPTIMIZED_CSV" | cut -d',' -f2)

# Calculate improvements
calc_improvement() {
    local baseline=$1
    local optimized=$2
    if [ -n "$baseline" ] && [ -n "$optimized" ] && [ "$baseline" != "0" ]; then
        improvement=$(echo "scale=1; (($baseline - $optimized) / $baseline) * 100" | bc)
        echo "$improvement"
    else
        echo "N/A"
    fi
}

avg_improvement=$(calc_improvement "$baseline_avg_latency" "$optimized_avg_latency")
p95_improvement=$(calc_improvement "$baseline_p95_latency" "$optimized_p95_latency")
throughput_improvement=$(calc_improvement "$baseline_throughput" "$optimized_throughput")
db_improvement=$(calc_improvement "$baseline_db_time" "$optimized_db_time")

# Print table
printf "%-30s | %15s | %15s | %15s\n" "Metric" "Baseline" "Optimized" "Improvement"
printf "%-30s-+-%15s-+-%15s-+-%15s\n" "------------------------------" "---------------" "---------------" "---------------"
printf "%-30s | %15s | %15s | %15s%%\n" "Avg Latency (ms)" "$baseline_avg_latency" "$optimized_avg_latency" "$avg_improvement"
printf "%-30s | %15s | %15s | %15s%%\n" "P95 Latency (ms)" "$baseline_p95_latency" "$optimized_p95_latency" "$p95_improvement"
printf "%-30s | %15s | %15s | %15s%%\n" "Throughput (req/s)" "$baseline_throughput" "$optimized_throughput" "$throughput_improvement"
printf "%-30s | %15s | %15s | %15s%%\n" "Avg DB Query Time (ms)" "$baseline_db_time" "$optimized_db_time" "$db_improvement"
printf "%-30s | %15s | %15s | %15s\n" "Cache Hit Ratio (%)" "$baseline_cache_hit" "$optimized_cache_hit" "N/A"

echo ""
echo "Results saved to: results/comparison-table.txt"
{
    echo "RESULTS COMPARISON TABLE"
    echo "========================"
    echo ""
    printf "%-30s | %15s | %15s | %15s\n" "Metric" "Baseline" "Optimized" "Improvement"
    printf "%-30s-+-%15s-+-%15s-+-%15s\n" "------------------------------" "---------------" "---------------" "---------------"
    printf "%-30s | %15s | %15s | %15s%%\n" "Avg Latency (ms)" "$baseline_avg_latency" "$optimized_avg_latency" "$avg_improvement"
    printf "%-30s | %15s | %15s | %15s%%\n" "P95 Latency (ms)" "$baseline_p95_latency" "$optimized_p95_latency" "$p95_improvement"
    printf "%-30s | %15s | %15s | %15s%%\n" "Throughput (req/s)" "$baseline_throughput" "$optimized_throughput" "$throughput_improvement"
    printf "%-30s | %15s | %15s | %15s%%\n" "Avg DB Query Time (ms)" "$baseline_db_time" "$optimized_db_time" "$db_improvement"
    printf "%-30s | %15s | %15s | %15s\n" "Cache Hit Ratio (%)" "$baseline_cache_hit" "$optimized_cache_hit" "N/A"
} > results/comparison-table.txt

