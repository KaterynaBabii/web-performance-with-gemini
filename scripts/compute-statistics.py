#!/usr/bin/env python3
"""
Compute mean ± standard deviation for IEEE Access / resubmission.
Supports six load levels (50–300), 95% CIs, Welch t and Mann–Whitney U (p-values),
and an optional ablation mode (results/ablation/*).
"""

import json
import csv
import os
import sys
import math
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

def t_confidence_interval(mean, std, n, alpha=0.05):
    """
    Compute two-sided (1-alpha) confidence interval using Student's t.
    Returns (lower, upper). For n < 2, returns (mean, mean).
    Uses hard-coded t quantiles for n up to 30; falls back to normal for larger n.
    """
    if n < 2 or std == 0:
        return (mean, mean)

    df = n - 1
    # Approximate critical values for 95% CI (alpha=0.05)
    t_table_95 = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }
    if abs(alpha - 0.05) > 1e-6:
        # For now, we only support 95% CI
        alpha = 0.05

    if df in t_table_95:
        t_crit = t_table_95[df]
    else:
        # Large df: approximate with normal 1.96 for 95% CI
        t_crit = 1.96

    margin = t_crit * (std / math.sqrt(n))
    return (mean - margin, mean + margin)

def _norm_cdf(z):
    """Standard normal CDF Phi(z)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def mann_whitney_u_two_sided(sample1, sample2):
    """
    Two-sample Mann–Whitney U test (Wilcoxon rank-sum) with tie correction.
    Uses normal approximation with continuity correction; suitable for n1,n2 >= 4.
    Returns (U, p_value_two_sided). U is the smaller of U1, U2.
    """
    x = np.asarray(sample1, dtype=float)
    y = np.asarray(sample2, dtype=float)
    n1, n2 = len(x), len(y)
    if n1 < 1 or n2 < 1:
        return float("nan"), float("nan")

    vals = np.concatenate([x, y])
    grp = np.array([0] * n1 + [1] * n2)
    n = n1 + n2
    order = np.argsort(vals, kind="mergesort")
    sorted_vals = vals[order]

    # Average ranks for ties (1-based ranks)
    rank_at_sorted_pos = np.empty(n, dtype=float)
    r = 1
    i = 0
    while i < n:
        j = i
        while j < n and sorted_vals[j] == sorted_vals[i]:
            j += 1
        t = j - i
        mean_rank = (r + (r + t - 1)) / 2.0
        rank_at_sorted_pos[i:j] = mean_rank
        r += t
        i = j

    ranks = np.empty(n, dtype=float)
    ranks[order] = rank_at_sorted_pos

    r1 = ranks[grp == 0].sum()
    u1 = n1 * n2 + n1 * (n1 + 1) / 2.0 - r1
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    mu = n1 * n2 / 2.0
    sv = np.sort(vals)
    tie_sum = 0.0
    i = 0
    while i < len(sv):
        j = i
        while j < len(sv) and sv[j] == sv[i]:
            j += 1
        t = j - i
        if t > 1:
            tie_sum += t**3 - t
        i = j

    var_u = (n1 * n2 / 12.0) * ((n1 + n2 + 1) - tie_sum / max((n1 + n2) * (n1 + n2 - 1), 1))
    if var_u <= 0:
        return float(u), 1.0

    # Continuity correction toward the mean
    if u < mu:
        z = (u - mu + 0.5) / math.sqrt(var_u)
    elif u > mu:
        z = (u - mu - 0.5) / math.sqrt(var_u)
    else:
        z = 0.0

    p_two = 2.0 * (1.0 - _norm_cdf(abs(z)))
    return float(u), float(min(max(p_two, 0.0), 1.0))


def welch_t_test(sample1, sample2):
    """
    Compute Welch's t-test statistic for two independent samples.
    Returns (t_stat, df). We do not compute an exact p-value here,
    but t_stat and df are enough for interpretation / external tools.
    """
    x1 = np.array(sample1, dtype=float)
    x2 = np.array(sample2, dtype=float)
    n1, n2 = len(x1), len(x2)
    if n1 < 2 or n2 < 2:
        return (0.0, 0.0)

    m1, m2 = np.mean(x1), np.mean(x2)
    s1_sq = np.var(x1, ddof=1)
    s2_sq = np.var(x2, ddof=1)

    numerator = m1 - m2
    denom = math.sqrt(s1_sq / n1 + s2_sq / n2)
    if denom == 0:
        return (0.0, 0.0)

    t_stat = numerator / denom
    # Welch–Satterthwaite approximation for df
    df_num = (s1_sq / n1 + s2_sq / n2) ** 2
    df_den = (s1_sq**2 / (n1**2 * (n1 - 1))) + (s2_sq**2 / (n2**2 * (n2 - 1)))
    df = df_num / df_den if df_den > 0 else 0.0
    return (float(t_stat), float(df))


def welch_t_pvalue_two_sided(sample1, sample2):
    """
    Two-sided p-value for Welch's t-test (unequal variances).
    Uses scipy.stats.t.sf if SciPy is installed; otherwise a normal approximation
    (document as approximate when df is small).
    Returns (p_value, t_stat, df_welch).
    """
    x1 = np.array(sample1, dtype=float)
    x2 = np.array(sample2, dtype=float)
    n1, n2 = len(x1), len(x2)
    if n1 < 2 or n2 < 2:
        return float("nan"), float("nan"), float("nan")
    t_stat, df = welch_t_test(sample1, sample2)
    if df <= 0 or not math.isfinite(t_stat):
        return float("nan"), t_stat, df
    try:
        from scipy.stats import t as student_t  # type: ignore

        p = 2.0 * student_t.sf(abs(t_stat), df)
        return float(min(max(p, 0.0), 1.0)), t_stat, df
    except ImportError:
        p = 2.0 * (1.0 - _norm_cdf(abs(t_stat)))
        return float(min(max(p, 0.0), 1.0)), t_stat, df


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
        'latex': format_latex(mean, std),
        'ci_95': t_confidence_interval(mean, std, n),
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
        if result.get("ci_95"):
            lo, hi = result["ci_95"]
            print(f"  95% CI (t): [{lo:.2f}, {hi:.2f}]")
        
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
    print("\\caption{Performance Results (Mean $\\pm$ SD over repeated runs)}")
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


def generate_ablation_latex_table(ablation_results):
    """LaTeX table for ablation study (one load level, multiple variants)."""
    print(f"\n{'='*80}")
    print("ABLATION STUDY — LaTeX TABLE")
    print(f"{'='*80}\n")

    order = [
        "Ablation Baseline",
        "Ablation IndexOnly",
        "Ablation CacheOnly",
        "Ablation QueryOpt",
    ]
    print("\\begin{table}[h]")
    print("\\centering")
    print("\\caption{Ablation Study (Mean $\\pm$ SD over repeated runs)}")
    print("\\label{tab:ablation}")
    print("\\begin{tabular}{lccccc}")
    print("\\hline")
    print(
        "Configuration & Avg(ms) & P95(ms) & Throughput(req/s) & Cache hit(\\%) & n \\\\"
    )
    print("\\hline")
    for name in order:
        if name not in ablation_results:
            continue
        results = ablation_results[name]
        avg = results.get("avg_latency", {}).get("latex", "N/A")
        p95 = results.get("p95_latency", {}).get("latex", "N/A")
        thr = results.get("throughput", {}).get("latex", "N/A")
        cache = results.get("cache_hit", {}).get("latex", "N/A")
        n = results.get("avg_latency", {}).get("n", "")
        short = name.replace("Ablation ", "")
        print(f"{short} & {avg} & {p95} & {thr} & {cache} & {n} \\\\")
    print("\\hline")
    print("\\end{tabular}")
    print("\\end{table}\n")


def compare_baseline_gemini(all_results):
    """Welch t-test and two-sided Mann–Whitney U between Baseline and Gemini per load."""
    print(f"\n{'='*80}")
    print("Baseline vs. Gemini: Welch t-test and Mann–Whitney U (two-sided p), per load")
    print(f"{'='*80}\n")

    # Group by load similarly to generate_latex_table
    by_load = defaultdict(dict)
    for config_name, results in all_results.items():
        parts = config_name.split()
        if len(parts) >= 2:
            system = parts[0]
            load = int(parts[1])
            by_load[load][system] = results

    metrics_keys = [
        ('avg_latency', 'Avg Latency (ms)'),
        ('p95_latency', 'P95 Latency (ms)'),
        ('throughput', 'Throughput (req/s)'),
        ('cache_hit', 'Cache Hit Ratio (%)'),
    ]

    for load in sorted(by_load.keys()):
        if 'Baseline' not in by_load[load] or 'Gemini' not in by_load[load]:
            continue

        print(f"\nLoad {load} users")
        print("-" * 40)

        base = by_load[load]['Baseline']
        gem = by_load[load]['Gemini']

        for key, label in metrics_keys:
            b_res = base.get(key)
            g_res = gem.get(key)
            if not b_res or not g_res:
                continue

            b_vals = b_res.get('values', [])
            g_vals = g_res.get('values', [])
            if len(b_vals) < 2 or len(g_vals) < 2:
                continue

            t_stat, df = welch_t_test(b_vals, g_vals)
            p_welch, _, _ = welch_t_pvalue_two_sided(b_vals, g_vals)
            u_stat, p_mw = mann_whitney_u_two_sided(b_vals, g_vals)
            sig = ""
            if not math.isnan(p_mw):
                if p_mw < 0.001:
                    sig = " ***"
                elif p_mw < 0.01:
                    sig = " **"
                elif p_mw < 0.05:
                    sig = " *"
            pw = f"{p_welch:.4g}" if not math.isnan(p_welch) else "n/a"
            print(
                f"{label}: Welch t = {t_stat:.3f} (df ≈ {df:.1f}, p = {pw}); "
                f"Mann–Whitney U = {u_stat:.1f}, p = {p_mw:.4g}{sig}"
            )

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 compute-statistics.py <config>")
        print("\nExample:")
        print("  python3 compute-statistics.py baseline_50")
        print("  python3 compute-statistics.py gemini_150")
        print("\nOr process all configurations:")
        print("  python3 compute-statistics.py all")
        print("  python3 compute-statistics.py ablation")
        sys.exit(1)
    
    config_arg = sys.argv[1]
    project_root = Path(__file__).parent.parent

    # Loads used by run-benchmark-grid.sh (and manual runs)
    GRID_LOADS = ["50", "100", "150", "200", "250", "300"]
    
    if config_arg == 'all':
        # Process all configurations
        all_results = {}
        
        configs = []
        for load in GRID_LOADS:
            configs.append((f"Baseline {load}", "baseline", load))
            configs.append((f"Gemini {load}", "gemini", load))
        
        for config_name, folder, load in configs:
            # Look for JSON files (with or without _run suffix)
            json_pattern1 = f"results/{folder}/{load}.json"  # Exact match first
            json_pattern2 = f"results/{folder}/{load}_run*.json"  # Then run-numbered files
            
            # Look for Locust CSV files (multiple patterns)
            csv_pattern1 = f"results/{folder}/locust_{load}.csv"  # Exact match
            csv_pattern2 = f"results/{folder}/locust_{load}_run*.csv"  # Run-numbered
            csv_pattern3 = f"results/{folder}/{load}_run*_stats.csv"  # Stats files from runs
            
            # Do not bucket timestamped metrics-*.csv by latency — filenames lack load;
            # mis-assigns 100/200/300. Use JSON + Locust only for grid statistics.
            metrics_files = []
            
            json_files = list(project_root.glob(json_pattern1)) + list(project_root.glob(json_pattern2))
            csv_files = (list(project_root.glob(csv_pattern1)) + 
                        list(project_root.glob(csv_pattern2)) + 
                        list(project_root.glob(csv_pattern3)))
            
            if json_files or csv_files or metrics_files:
                results = process_test_configuration(config_name, json_files, csv_files, metrics_files)
                all_results[config_name] = results
        
        # Generate LaTeX table
        generate_latex_table(all_results)
        # Also print simple Welch t statistics for Baseline vs Gemini
        compare_baseline_gemini(all_results)

    elif config_arg == "ablation":
        ablation_results = {}
        load = os.environ.get("ABLATION_LOAD", "150")
        ablation_configs = [
            ("Ablation Baseline", f"ablation/baseline", load),
            ("Ablation IndexOnly", f"ablation/index_only", load),
            ("Ablation CacheOnly", f"ablation/cache_only", load),
            ("Ablation QueryOpt", f"ablation/query_opt_only", load),
        ]
        for config_name, rel_folder, ld in ablation_configs:
            base = project_root / "results" / rel_folder
            json_files = sorted(
                set(list(base.glob(f"{ld}.json")) + list(base.glob(f"{ld}_run*.json")))
            )
            csv_files = sorted(
                set(
                    list(base.glob(f"locust_{ld}.csv"))
                    + list(base.glob(f"locust_{ld}_run*.csv"))
                    + list(base.glob(f"{ld}_run*_stats.csv"))
                )
            )
            metrics_files = []
            if json_files or csv_files:
                results = process_test_configuration(
                    config_name, json_files, csv_files, metrics_files
                )
                ablation_results[config_name] = results
            else:
                print(f"Note: no data yet for {config_name} under results/{rel_folder}/")
        if ablation_results:
            generate_ablation_latex_table(ablation_results)
        
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
        
        # Avoid ambiguous metrics-*.csv bucketing for arbitrary loads
        metrics_files = []
        
        json_files = list(project_root.glob(json_pattern1)) + list(project_root.glob(json_pattern2))
        csv_files = (list(project_root.glob(csv_pattern1)) + 
                    list(project_root.glob(csv_pattern2)) + 
                    list(project_root.glob(csv_pattern3)))
        
        if not json_files and not csv_files and not metrics_files:
            print(f"Error: No files found for {config_arg}")
            print(
                f"  Looked for: {json_pattern1}, {json_pattern2}, "
                f"{csv_pattern1}, {csv_pattern2}, {csv_pattern3}"
            )
            sys.exit(1)
        
        config_name = f"{folder.capitalize()} {load}"
        process_test_configuration(config_name, json_files, csv_files, metrics_files)

if __name__ == "__main__":
    main()

