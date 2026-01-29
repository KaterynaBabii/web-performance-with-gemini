#!/usr/bin/env python3
"""
Compute mean ± standard deviation for IEEE Access paper
Processes results from 3 independent runs and generates LaTeX-formatted statistics
"""

import json
import csv
import os
import sys
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_json(filepath):
    """Load JSON file and return data"""
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None

def load_csv(filepath):
    """Load Locust CSV and extract aggregated data"""
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Type') == '' and row.get('Name') == 'Aggregated':
                    return row
        return None
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None

def load_metrics_csv(filepath):
    """Load metrics CSV file (from /metrics endpoint export)
    Format: Metric,Value rows
    Returns dict with metric names as keys
    """
    try:
        metrics_dict = {}
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                metric_name = row.get('Metric', '').strip()
                value_str = row.get('Value', '').strip()
                if metric_name and value_str:
                    # Convert to numeric value
                    try:
                        value = float(value_str)
                        # Map to our standard keys
                        if 'Avg Latency' in metric_name:
                            metrics_dict['avg_ms'] = value
                        elif 'P95 Latency' in metric_name:
                            metrics_dict['p95_ms'] = value
                        elif 'Cache Hit Ratio' in metric_name:
                            metrics_dict['cache_hit_ratio'] = value
                        elif 'Throughput' in metric_name:
                            metrics_dict['throughput'] = value
                    except ValueError:
                        pass
        return metrics_dict if metrics_dict else None
    except Exception as e:
        print(f"Warning: Could not load metrics CSV {filepath}: {e}")
        return None

def compute_stats(values):
    """
    Compute mean and sample standard deviation (n-1 denominator)
    Returns: (mean, std, n)
    """
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

def check_outliers(values, threshold=2.0):
    """
    Check for outliers using z-score method
    Returns list of outlier indices
    """
    if len(values) < 3:
        return []
    
    values = np.array([float(v) for v in values])
    mean = np.mean(values)
    std = np.std(values, ddof=1)
    
    if std == 0:
        return []
    
    z_scores = np.abs((values - mean) / std)
    outliers = np.where(z_scores > threshold)[0].tolist()
    return outliers

def format_latex(mean, std, decimals=2):
    """Format as LaTeX: mean \\pm SD"""
    return f"{mean:.{decimals}f} \\pm {std:.{decimals}f}"

def analyze_runs(run_files, metric_name, extract_func, file_data_map=None):
    """
    Analyze multiple runs for a specific metric
    run_files: list of file paths
    metric_name: name of the metric
    extract_func: function to extract metric (can take filepath or data)
    file_data_map: optional dict mapping filepath -> pre-loaded data
    """
    values = []
    file_data = []
    
    for filepath in run_files:
        # Convert Path to string if needed
        filepath_str = str(filepath)
        
        # If we have pre-loaded data, use it
        if file_data_map and filepath_str in file_data_map:
            data = file_data_map[filepath_str]
            value = extract_func(filepath)  # Pass filepath, extract_func uses map
            if value is not None:
                values.append(value)
                file_data.append((filepath_str, value))
            continue
        
        # Otherwise, load file and extract
        if filepath_str.endswith('.json'):
            data = load_json(filepath_str)
        elif filepath_str.endswith('.csv'):
            # Try metrics CSV format first
            data = load_metrics_csv(filepath_str)
            if not data:
                # Fallback to Locust CSV
                data = load_csv(filepath_str)
        else:
            continue
        
        if data:
            value = extract_func(data)  # Pass data directly
            if value is not None:
                values.append(value)
                file_data.append((filepath_str, value))
    
    if len(values) == 0:
        return None
    
    mean, std, n = compute_stats(values)
    outliers = check_outliers(values)
    
    return {
        'metric': metric_name,
        'values': values,
        'mean': mean,
        'std': std,
        'n': n,
        'outliers': outliers,
        'files': file_data,
        'latex': format_latex(mean, std)
    }

def extract_metrics_from_json(data):
    """Extract all metrics from JSON metrics file"""
    return {
        'avg_ms': data.get('avg_ms', 0),
        'p95_ms': data.get('p95_ms', 0),
        'cache_hit_ratio': data.get('cache_hit_ratio', 0),
        'requests': data.get('requests', 0),
        'errors': data.get('errors', 0)
    }

def extract_throughput_from_csv(data):
    """Extract throughput from Locust CSV"""
    if data:
        return float(data.get('Requests/s', 0))
    return None

def process_test_configuration(config_name, json_files, csv_files, metrics_files=None):
    """
    Process a test configuration (e.g., "Baseline 50" or "Gemini 150")
    """
    print(f"\n{'='*80}")
    print(f"Processing: {config_name}")
    print(f"{'='*80}")
    
    results = {}
    
    # Prioritize metrics CSV files if we have 3+ (for proper statistics)
    use_metrics_csv = metrics_files and len(metrics_files) >= 3
    
    # Extract metrics from JSON files (only if we don't have enough CSV metrics)
    if json_files and not use_metrics_csv:
        # Average latency
        avg_latency = analyze_runs(
            json_files,
            'Avg Latency (ms)',
            lambda d: d.get('avg_ms') if isinstance(d, dict) else None
        )
        if avg_latency:
            results['avg_latency'] = avg_latency
        
        # P95 latency
        p95_latency = analyze_runs(
            json_files,
            'P95 Latency (ms)',
            lambda d: d.get('p95_ms') if isinstance(d, dict) else None
        )
        if p95_latency:
            results['p95_latency'] = p95_latency
        
        # Cache hit ratio
        cache_hit = analyze_runs(
            json_files,
            'Cache Hit Ratio (%)',
            lambda d: d.get('cache_hit_ratio') if isinstance(d, dict) else None
        )
        if cache_hit:
            results['cache_hit'] = cache_hit
    
    # Extract throughput from CSV files (Locust)
    if csv_files:
        throughput = analyze_runs(
            csv_files,
            'Throughput (req/s)',
            extract_throughput_from_csv
        )
        if throughput:
            results['throughput'] = throughput
    
    # Extract metrics from timestamped metrics CSV files
    # Group by load level by checking file timestamps and assuming they're from same test
    if metrics_files and len(metrics_files) >= 3:
        print(f"  Found {len(metrics_files)} metrics CSV files for {config_name}")
        # Sort by timestamp
        sorted_metrics = sorted(metrics_files, key=lambda x: x.name)
        
        # Extract metrics from all files
        metrics_data = []
        for mfile in sorted_metrics:
            data = load_metrics_csv(str(mfile))
            if data and data.get('avg_ms', 0) > 0:  # Only include non-zero metrics
                metrics_data.append((mfile, data))
        
        print(f"  Valid metrics files: {len(metrics_data)}")
        
        # If we have at least 3 valid metrics files, use them (override JSON if needed)
        if len(metrics_data) >= 3:
            # Create a lookup dict for file -> data
            file_data_map = {str(f[0]): f[1] for f in metrics_data}
            
            # Extract avg_ms (always use CSV if we have 3+ files)
            avg_from_metrics = analyze_runs(
                [f[0] for f in metrics_data],
                'Avg Latency (ms)',
                lambda f: file_data_map.get(str(f), {}).get('avg_ms') if file_data_map.get(str(f)) else None,
                file_data_map
            )
            if avg_from_metrics and avg_from_metrics['n'] >= 3:
                results['avg_latency'] = avg_from_metrics
            
            # Extract p95_ms
            p95_from_metrics = analyze_runs(
                [f[0] for f in metrics_data],
                'P95 Latency (ms)',
                lambda f: file_data_map.get(str(f), {}).get('p95_ms') if file_data_map.get(str(f)) else None,
                file_data_map
            )
            if p95_from_metrics and p95_from_metrics['n'] >= 3:
                results['p95_latency'] = p95_from_metrics
            
            # Extract cache_hit_ratio
            cache_from_metrics = analyze_runs(
                [f[0] for f in metrics_data],
                'Cache Hit Ratio (%)',
                lambda f: file_data_map.get(str(f), {}).get('cache_hit_ratio') if file_data_map.get(str(f)) else None,
                file_data_map
            )
            if cache_from_metrics and cache_from_metrics['n'] >= 3:
                results['cache_hit'] = cache_from_metrics
            
            # Extract throughput if available
            thr_from_metrics = analyze_runs(
                [f[0] for f in metrics_data],
                'Throughput (req/s)',
                lambda f: file_data_map.get(str(f), {}).get('throughput') if file_data_map.get(str(f)) else None,
                file_data_map
            )
            if thr_from_metrics and thr_from_metrics['n'] >= 3:
                results['throughput'] = thr_from_metrics
    
    # Print results
    for key, result in results.items():
        print(f"\n{result['metric']}:")
        print(f"  Files: {len(result['files'])}")
        print(f"  Values: {result['values']}")
        print(f"  Mean: {result['mean']:.2f}")
        print(f"  Std Dev: {result['std']:.2f}")
        print(f"  LaTeX: {result['latex']}")
        
        if result['outliers']:
            print(f"  ⚠️  WARNING: Outliers detected at indices {result['outliers']}")
            for idx in result['outliers']:
                print(f"     - {result['files'][idx][0]}: {result['files'][idx][1]}")
        else:
            print(f"  ✅ No outliers detected")
        
        # Check coefficient of variation (CV)
        if result['mean'] > 0:
            cv = (result['std'] / result['mean']) * 100
            print(f"  Coefficient of Variation: {cv:.2f}%")
            if cv > 20:
                print(f"  ⚠️  WARNING: High variance (CV > 20%)")
            elif cv < 5:
                print(f"  ✅ Low variance (CV < 5%)")
    
    return results

def generate_latex_table(all_results):
    """Generate LaTeX table from all results"""
    print(f"\n{'='*80}")
    print("LaTeX TABLE FORMAT")
    print(f"{'='*80}\n")
    
    # Group by load level
    by_load = defaultdict(dict)
    
    for config_name, results in all_results.items():
        # Parse config name (e.g., "Baseline 50" -> load=50, system="Baseline")
        parts = config_name.split()
        if len(parts) >= 2:
            system = parts[0]
            load = int(parts[1])
            
            if load not in by_load:
                by_load[load] = {}
            by_load[load][system] = results
    
    # Generate table
    print("\\begin{table}[h]")
    print("\\centering")
    print("\\caption{Performance Results (Mean $\\pm$ SD over 3 runs)}")
    print("\\label{tab:results}")
    print("\\begin{tabular}{lccccc}")
    print("\\hline")
    print("Load & System & Avg(ms) & P95(ms) & Throughput(req/s) & Cache hit(\\%) \\\\")
    print("\\hline")
    
    for load in sorted(by_load.keys()):
        for system in ['Baseline', 'Gemini']:
            if system in by_load[load]:
                results = by_load[load][system]
                avg = results.get('avg_latency', {}).get('latex', 'N/A')
                p95 = results.get('p95_latency', {}).get('latex', 'N/A')
                thr = results.get('throughput', {}).get('latex', 'N/A')
                cache = results.get('cache_hit', {}).get('latex', 'N/A')
                
                print(f"{load} & {system} & {avg} & {p95} & {thr} & {cache} \\\\")
    
    print("\\hline")
    print("\\end{tabular}")
    print("\\end{table}\n")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 compute-statistics.py <config>")
        print("\nExample:")
        print("  python3 compute-statistics.py baseline_50")
        print("  python3 compute-statistics.py gemini_150")
        print("\nOr process all configurations:")
        print("  python3 compute-statistics.py all")
        sys.exit(1)
    
    config_arg = sys.argv[1]
    project_root = Path(__file__).parent.parent
    
    if config_arg == 'all':
        # Process all configurations
        all_results = {}
        
        configs = [
            ('Baseline 50', 'baseline', '50'),
            ('Baseline 150', 'baseline', '150'),
            ('Baseline 250', 'baseline', '250'),
            ('Gemini 50', 'gemini', '50'),
            ('Gemini 150', 'gemini', '150'),
            ('Gemini 250', 'gemini', '250'),
        ]
        
        for config_name, folder, load in configs:
            # Look for JSON files (with or without _run suffix)
            json_pattern1 = f"results/{folder}/{load}.json"  # Exact match first
            json_pattern2 = f"results/{folder}/{load}_run*.json"  # Then run-numbered files
            
            # Look for Locust CSV files (multiple patterns)
            csv_pattern1 = f"results/{folder}/locust_{load}.csv"  # Exact match
            csv_pattern2 = f"results/{folder}/locust_{load}_run*.csv"  # Run-numbered
            csv_pattern3 = f"results/{folder}/{load}_run*_stats.csv"  # Stats files from runs
            
            # Look for timestamped metrics CSV files and filter by estimated load
            all_metrics_files = list(project_root.glob(f"results/{folder}/metrics-*.csv"))
            metrics_files = []
            
            # Filter metrics files by estimated load level based on avg latency
            load_thresholds = {
                '50': (0, 600),      # 0-600ms avg = load 50
                '150': (600, 2000),  # 600-2000ms avg = load 150
                '250': (2000, 999999) # 2000ms+ avg = load 250
            }
            
            min_avg, max_avg = load_thresholds.get(load, (0, 999999))
            
            for mfile in all_metrics_files:
                data = load_metrics_csv(str(mfile))
                if data:
                    avg = data.get('avg_ms', 0)
                    if min_avg <= avg < max_avg and avg > 0:  # Valid non-zero metrics
                        metrics_files.append(mfile)
            
            json_files = list(project_root.glob(json_pattern1)) + list(project_root.glob(json_pattern2))
            csv_files = (list(project_root.glob(csv_pattern1)) + 
                        list(project_root.glob(csv_pattern2)) + 
                        list(project_root.glob(csv_pattern3)))
            
            if json_files or csv_files or metrics_files:
                results = process_test_configuration(config_name, json_files, csv_files, metrics_files)
                all_results[config_name] = results
        
        # Generate LaTeX table
        generate_latex_table(all_results)
        
    else:
        # Process single configuration
        parts = config_arg.split('_')
        if len(parts) != 2:
            print(f"Error: Invalid configuration '{config_arg}'. Use format: baseline_50 or gemini_150")
            sys.exit(1)
        
        folder = parts[0]
        load = parts[1]
        
        json_pattern1 = f"results/{folder}/{load}.json"
        json_pattern2 = f"results/{folder}/{load}_run*.json"
        csv_pattern1 = f"results/{folder}/locust_{load}.csv"
        csv_pattern2 = f"results/{folder}/locust_{load}_run*.csv"
        csv_pattern3 = f"results/{folder}/{load}_run*_stats.csv"
        
        # Also look for timestamped metrics CSV files
        all_metrics_files = list(project_root.glob(f"results/{folder}/metrics-*.csv"))
        metrics_files = []
        
        # Filter metrics files by estimated load level
        load_thresholds = {
            '50': (0, 600),
            '150': (600, 2000),
            '250': (2000, 999999)
        }
        min_avg, max_avg = load_thresholds.get(load, (0, 999999))
        
        for mfile in all_metrics_files:
            data = load_metrics_csv(str(mfile))
            if data:
                avg = data.get('avg_ms', 0)
                if min_avg <= avg < max_avg and avg > 0:
                    metrics_files.append(mfile)
        
        json_files = list(project_root.glob(json_pattern1)) + list(project_root.glob(json_pattern2))
        csv_files = (list(project_root.glob(csv_pattern1)) + 
                    list(project_root.glob(csv_pattern2)) + 
                    list(project_root.glob(csv_pattern3)))
        
        if not json_files and not csv_files and not metrics_files:
            print(f"Error: No files found for {config_arg}")
            print(f"  Looked for: {json_pattern}, {csv_pattern}, metrics-*.csv")
            sys.exit(1)
        
        config_name = f"{folder.capitalize()} {load}"
        process_test_configuration(config_name, json_files, csv_files, metrics_files)

if __name__ == "__main__":
    main()

