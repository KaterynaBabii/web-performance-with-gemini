#!/usr/bin/env python3
"""
Extract results from JSON and CSV files and create results table
"""

import json
import csv
import os

def load_json(filepath):
    """Load JSON file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None

def load_csv(filepath):
    """Load Locust CSV and extract throughput and error rate"""
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Type') == 'Aggregated':
                    total_requests = int(row.get('Request Count', 0))
                    failures = int(row.get('Failure Count', 0))
                    rps = float(row.get('Requests/s', 0))
                    error_rate = (failures / total_requests * 100) if total_requests > 0 else 0
                    return {
                        'throughput': round(rps, 2),
                        'error_rate': round(error_rate, 2)
                    }
        return None
    except FileNotFoundError:
        return None

def extract_results():
    """Extract all results and create table"""
    
    results = []
    
    # Baseline results
    for load in [50, 150, 250]:
        json_file = f'results/baseline/{load}.json'
        csv_file = f'results/baseline/locust_{load}.csv'
        
        metrics = load_json(json_file)
        locust = load_csv(csv_file)
        
        if metrics and locust:
            results.append({
                'load': load,
                'system': 'Baseline',
                'avg_ms': metrics.get('avg_ms', 0),
                'p95_ms': metrics.get('p95_ms', 0),
                'throughput': locust.get('throughput', 0),
                'cache_hit': metrics.get('cache_hit_ratio', 0),
                'error_rate': locust.get('error_rate', 0)
            })
    
    # Gemini results
    for load in [50, 150, 250]:
        json_file = f'results/gemini/{load}.json'
        csv_file = f'results/gemini/locust_{load}.csv'
        
        metrics = load_json(json_file)
        locust = load_csv(csv_file)
        
        if metrics and locust:
            results.append({
                'load': load,
                'system': 'Gemini',
                'avg_ms': metrics.get('avg_ms', 0),
                'p95_ms': metrics.get('p95_ms', 0),
                'throughput': locust.get('throughput', 0),
                'cache_hit': metrics.get('cache_hit_ratio', 0),
                'error_rate': locust.get('error_rate', 0)
            })
    
    return results

def create_table(results):
    """Create formatted table"""
    print("=" * 90)
    print("MAIN RESULTS TABLE")
    print("=" * 90)
    print(f"{'Load':<8} {'System':<12} {'Avg(ms)':<12} {'P95(ms)':<12} {'Throughput(req/s)':<18} {'Cache hit(%)':<15}")
    print("-" * 90)
    
    for r in results:
        print(f"{r['load']:<8} {r['system']:<12} {r['avg_ms']:<12.2f} {r['p95_ms']:<12.2f} {r['throughput']:<18.2f} {r['cache_hit']:<15.2f}")
    
    print("=" * 90)
    
    # Also create markdown table
    md_table = "| Load | System | Avg(ms) | P95(ms) | Throughput(req/s) | Cache hit(%) |\n"
    md_table += "|------|--------|---------|---------|-------------------|-------------|\n"
    
    for r in results:
        md_table += f"| {r['load']} | {r['system']} | {r['avg_ms']:.2f} | {r['p95_ms']:.2f} | {r['throughput']:.2f} | {r['cache_hit']:.2f} |\n"
    
    return md_table

if __name__ == '__main__':
    results = extract_results()
    
    if not results:
        print("ERROR: No results found. Check that all JSON and CSV files exist.")
        exit(1)
    
    print(f"\nFound {len(results)} result sets")
    
    # Print table
    md_table = create_table(results)
    
    # Save to file
    with open('results/RESULTS_TABLE.md', 'w') as f:
        f.write("# Performance Results Table\n\n")
        f.write(md_table)
        f.write("\n\n## Notes\n")
        f.write("- Load: Number of concurrent users\n")
        f.write("- Avg(ms): Average response time in milliseconds\n")
        f.write("- P95(ms): 95th percentile response time in milliseconds\n")
        f.write("- Throughput: Requests per second\n")
        f.write("- Cache hit(%): Percentage of requests served from cache\n")
    
    print(f"\n✅ Results table saved to: results/RESULTS_TABLE.md")
    
    # Also save as CSV
    with open('results/RESULTS_TABLE.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=['Load', 'System', 'Avg(ms)', 'P95(ms)', 'Throughput(req/s)', 'Cache hit(%)'])
        writer.writeheader()
        for r in results:
            writer.writerow({
                'Load': r['load'],
                'System': r['system'],
                'Avg(ms)': f"{r['avg_ms']:.2f}",
                'P95(ms)': f"{r['p95_ms']:.2f}",
                'Throughput(req/s)': f"{r['throughput']:.2f}",
                'Cache hit(%)': f"{r['cache_hit']:.2f}"
            })
    
    print(f"✅ Results CSV saved to: results/RESULTS_TABLE.csv")

