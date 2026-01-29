# Preparing Results for IEEE Access Paper

## Overview

This guide explains how to compute mean ± standard deviation for your benchmark results over 3 independent runs, formatted for LaTeX tables in your IEEE Access paper.

## Requirements

- 3 independent runs for each test configuration
- Results in JSON (metrics) and CSV (Locust) format
- Python 3.8+ with numpy

## Step 1: Run 3 Independent Tests

For each configuration (Baseline 50, Baseline 150, Baseline 250, Gemini 50, Gemini 150, Gemini 250), you need to run the test **3 times independently**.

### Option A: Manual Runs

Run each test 3 times, saving results with run numbers:

```bash
# Run 1
./scripts/run-all-tests-final.sh
# Rename results
mv results/baseline/50.json results/baseline/50_run1.json
mv results/baseline/locust_50.csv results/baseline/locust_50_run1.csv

# Run 2 (restart everything)
./scripts/run-all-tests-final.sh
mv results/baseline/50.json results/baseline/50_run2.json
mv results/baseline/locust_50.csv results/baseline/locust_50_run2.csv

# Run 3
./scripts/run-all-tests-final.sh
mv results/baseline/50.json results/baseline/50_run3.json
mv results/baseline/locust_50.csv results/baseline/locust_50_run3.csv
```

### Option B: Automated 3-Run Script

Create a script to run 3 times automatically (recommended):

```bash
# Create 3-run script
cat > scripts/run-3-times.sh << 'EOF'
#!/bin/bash
for i in 1 2 3; do
  echo "=== Run $i of 3 ==="
  ./scripts/run-all-tests-final.sh
  
  # Rename results with run number
  for folder in baseline gemini; do
    for load in 50 150 250; do
      [ -f "results/$folder/$load.json" ] && \
        mv "results/$folder/$load.json" "results/$folder/${load}_run${i}.json"
      [ -f "results/$folder/locust_$load.csv" ] && \
        mv "results/$folder/locust_$load.csv" "results/$folder/locust_${load}_run${i}.csv"
    done
  done
done
EOF
chmod +x scripts/run-3-times.sh
```

## Step 2: Compute Statistics

Use the statistics computation script:

```bash
# Process all configurations
python3 scripts/compute-statistics.py all

# Or process a single configuration
python3 scripts/compute-statistics.py baseline_50
python3 scripts/compute-statistics.py gemini_150
```

## Step 3: Review Output

The script will output:

1. **Raw values** from each run
2. **Mean** and **Standard Deviation** (sample SD, n-1)
3. **LaTeX format**: `mean \pm SD`
4. **Outlier detection** (z-score > 2.0)
5. **Coefficient of Variation** (CV) to check variance

### Example Output

```
Processing: Baseline 50
================================================================================

Avg Latency (ms):
  Files: 3
  Values: [490.2, 485.7, 494.3]
  Mean: 490.07
  Std Dev: 4.30
  LaTeX: 490.07 \pm 4.30
  ✅ No outliers detected
  Coefficient of Variation: 0.88%
  ✅ Low variance (CV < 5%)
```

## Step 4: LaTeX Table Format

The script automatically generates a LaTeX table:

```latex
\begin{table}[h]
\centering
\caption{Performance Results (Mean $\pm$ SD over 3 runs)}
\label{tab:results}
\begin{tabular}{lccccc}
\hline
Load & System & Avg(ms) & P95(ms) & Throughput(req/s) & Cache hit(\%) \\
\hline
50 & Baseline & 490.07 \pm 4.30 & 1140.25 \pm 12.45 & 20.15 \pm 0.32 & 0.00 \pm 0.00 \\
50 & Gemini & 216.42 \pm 3.18 & 590.33 \pm 8.92 & 22.08 \pm 0.25 & 31.60 \pm 2.15 \\
...
\hline
\end{tabular}
\end{table}
```

## Quality Checks

The script performs automatic quality checks:

### 1. Outlier Detection
- Uses z-score method (threshold = 2.0)
- Flags values that deviate significantly from mean

### 2. Variance Assessment
- **Coefficient of Variation (CV) = (SD / Mean) × 100%**
- **CV < 5%**: Excellent (low variance) ✅
- **5% ≤ CV < 20%**: Acceptable
- **CV ≥ 20%**: High variance ⚠️ (investigate)

### 3. Consistency Checks
- Verifies all 3 runs have data
- Checks for missing files
- Validates data format

## Interpreting Results

### Good Results (Low Variance)
```
Values: [490.2, 485.7, 494.3]
Mean: 490.07
Std Dev: 4.30
CV: 0.88%
```
✅ **Interpretation**: Very consistent runs, low experimental error

### Acceptable Results (Moderate Variance)
```
Values: [490.2, 510.5, 485.7]
Mean: 495.13
Std Dev: 12.45
CV: 2.51%
```
✅ **Interpretation**: Acceptable variance for controlled experiment

### Problematic Results (High Variance)
```
Values: [490.2, 650.3, 485.7]
Mean: 542.07
Std Dev: 89.12
CV: 16.44%
```
⚠️ **Interpretation**: High variance - investigate:
- System load during test
- Database state consistency
- Network conditions
- Consider running more than 3 runs

## Manual Calculation (if needed)

If you need to compute manually:

```python
import numpy as np

values = [490.2, 485.7, 494.3]
mean = np.mean(values)
std = np.std(values, ddof=1)  # Sample SD (n-1)
print(f"{mean:.2f} \\pm {std:.2f}")
```

## Troubleshooting

### "No files found"
- Check file naming: `*_run1.json`, `*_run2.json`, `*_run3.json`
- Verify files are in `results/baseline/` or `results/gemini/`

### High Variance
- Ensure tests are truly independent (restart services between runs)
- Check for system load variations
- Verify database state is consistent
- Consider running 5 runs instead of 3

### Missing Metrics
- Ensure JSON files contain: `avg_ms`, `p95_ms`, `cache_hit_ratio`
- Ensure CSV files contain: `Requests/s` in aggregated row

## Best Practices

1. **Independent Runs**: Restart Docker services between runs
2. **Consistent Environment**: Same hardware, same time of day
3. **Documentation**: Note any system changes between runs
4. **Validation**: Check for outliers before finalizing results
5. **Reproducibility**: Document exact test parameters

## Example Workflow

```bash
# 1. Run 3 independent test suites
./scripts/run-3-times.sh

# 2. Compute statistics
python3 scripts/compute-statistics.py all

# 3. Review output for outliers and variance

# 4. Copy LaTeX table to your paper

# 5. Include in methodology: "Each configuration was tested 3 times independently. 
#    Results are reported as mean ± standard deviation."
```

