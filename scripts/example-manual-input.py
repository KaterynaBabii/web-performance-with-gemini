#!/usr/bin/env python3
"""
Example: Compute statistics from manually provided data
Use this if you have results from 3 runs in CSV/JSON format
"""

import json
import sys
import numpy as np

def compute_stats(values):
    """Compute mean and sample standard deviation"""
    if not values or len(values) == 0:
        return (0, 0, 0)
    
    values = [float(v) for v in values if v is not None]
    if len(values) == 0:
        return (0, 0, 0)
    
    n = len(values)
    mean = np.mean(values)
    
    if n == 1:
        std = 0.0
    else:
        std = np.std(values, ddof=1)  # Sample standard deviation (n-1)
    
    return (mean, std, n)

def format_latex(mean, std, decimals=2):
    """Format as LaTeX: mean \\pm SD"""
    return f"{mean:.{decimals}f} \\pm {std:.{decimals}f}"

def check_outliers(values, threshold=2.0):
    """Check for outliers using z-score"""
    if len(values) < 3:
        return []
    
    values_arr = np.array([float(v) for v in values])
    mean = np.mean(values_arr)
    std = np.std(values_arr, ddof=1)
    
    if std == 0:
        return []
    
    z_scores = np.abs((values_arr - mean) / std)
    outliers = np.where(z_scores > threshold)[0].tolist()
    return outliers

# Example usage
if __name__ == "__main__":
    print("="*80)
    print("IEEE ACCESS STATISTICS COMPUTATION")
    print("="*80)
    print()
    print("Paste your 3 run results below, or modify this script with your data.")
    print()
    
    # EXAMPLE DATA - Replace with your actual values
    # Format: [run1_value, run2_value, run3_value]
    
    example_data = {
        "Avg Latency (ms)": [490.2, 485.7, 494.3],
        "P95 Latency (ms)": [1140.5, 1135.2, 1145.8],
        "Throughput (req/s)": [20.15, 20.08, 20.22],
        "Cache Hit Ratio (%)": [0.0, 0.0, 0.0],
    }
    
    print("EXAMPLE RESULTS:")
    print("-"*80)
    
    for metric_name, values in example_data.items():
        mean, std, n = compute_stats(values)
        outliers = check_outliers(values)
        cv = (std / mean * 100) if mean > 0 else 0
        
        print(f"\n{metric_name}:")
        print(f"  Values: {values}")
        print(f"  Mean: {mean:.2f}")
        print(f"  Std Dev: {std:.2f}")
        print(f"  LaTeX: {format_latex(mean, std)}")
        print(f"  Coefficient of Variation: {cv:.2f}%")
        
        if outliers:
            print(f"  ⚠️  WARNING: Outliers at indices {outliers}")
        else:
            print(f"  ✅ No outliers detected")
        
        if cv < 5:
            print(f"  ✅ Low variance (CV < 5%)")
        elif cv >= 20:
            print(f"  ⚠️  High variance (CV >= 20%)")
    
    print()
    print("="*80)
    print("TO USE WITH YOUR DATA:")
    print("="*80)
    print()
    print("1. Replace 'example_data' dictionary with your actual values")
    print("2. Run: python3 scripts/example-manual-input.py")
    print()
    print("Or use the automated script with your result files:")
    print("  python3 scripts/compute-statistics.py all")
    print()

