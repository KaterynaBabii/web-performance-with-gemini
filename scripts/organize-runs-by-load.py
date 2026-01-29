#!/usr/bin/env python3
"""
Organize timestamped metrics CSV files into groups by load level
Helps identify which files belong to which test configuration
"""

import csv
import os
from pathlib import Path
from collections import defaultdict

def load_metrics_csv(filepath):
    """Load metrics CSV and return dict"""
    try:
        metrics_dict = {}
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                metric_name = row.get('Metric', '').strip()
                value_str = row.get('Value', '').strip()
                if metric_name and value_str:
                    try:
                        value = float(value_str)
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
        return None

def organize_files():
    """Organize timestamped files by estimated load level"""
    project_root = Path(__file__).parent.parent
    
    for folder in ['baseline', 'gemini']:
        print(f"\n{'='*80}")
        print(f"Organizing {folder.upper()} files")
        print(f"{'='*80}\n")
        
        metrics_files = sorted(project_root.glob(f"results/{folder}/metrics-*.csv"))
        
        if not metrics_files:
            print(f"No metrics files found in results/{folder}/")
            continue
        
        # Group by similar metrics (estimate load level)
        groups = defaultdict(list)
        
        for mfile in metrics_files:
            data = load_metrics_csv(str(mfile))
            if data and data.get('avg_ms', 0) > 0:
                # Estimate load level based on avg latency ranges
                avg = data['avg_ms']
                if avg < 600:
                    load_est = "50"
                elif avg < 2000:
                    load_est = "150"
                else:
                    load_est = "250"
                
                groups[load_est].append((mfile, data))
        
        # Print groups
        for load in ['50', '150', '250']:
            if load in groups:
                files = groups[load]
                print(f"Load {load} ({len(files)} files):")
                for mfile, data in files[:10]:  # Show first 10
                    print(f"  {mfile.name}")
                    print(f"    Avg: {data.get('avg_ms', 0):.2f}ms, "
                          f"P95: {data.get('p95_ms', 0):.2f}ms, "
                          f"Throughput: {data.get('throughput', 0):.2f} req/s")
                if len(files) > 10:
                    print(f"  ... and {len(files) - 10} more files")
                print()

if __name__ == "__main__":
    organize_files()

