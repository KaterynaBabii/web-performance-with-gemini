#!/usr/bin/env python3
"""
Create results table from available JSON and CSV files
"""

import json
import csv
import os

results = []

# Baseline 50
try:
    with open('results/baseline/50.json') as f:
        b50 = json.load(f)
    with open('results/baseline/locust_50.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Type') == '' and row.get('Name') == 'Aggregated':
                results.append({
                    'load': 50,
                    'system': 'Baseline',
                    'avg_ms': b50['avg_ms'],
                    'p95_ms': b50['p95_ms'],
                    'throughput': float(row['Requests/s']),
                    'cache_hit': b50['cache_hit_ratio']
                })
                break
except Exception as e:
    print(f"Error loading baseline 50: {e}")

# Baseline 150
try:
    with open('results/baseline/150.json') as f:
        b150 = json.load(f)
    with open('results/baseline/locust_150.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Type') and row.get('Name') == 'Aggregated':
                results.append({
                    'load': 150,
                    'system': 'Baseline',
                    'avg_ms': b150['avg_ms'],
                    'p95_ms': b150['p95_ms'],
                    'throughput': float(row['Requests/s']),
                    'cache_hit': b150['cache_hit_ratio']
                })
                break
except Exception as e:
    print(f"Error loading baseline 150: {e}")

# Baseline 250
try:
    b250_data = None
    try:
        with open('results/baseline/250.json') as f:
            content = f.read().strip()
            if content:
                b250_data = json.loads(content)
    except:
        pass
    
    with open('results/baseline/locust_250.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Type') and row.get('Name') == 'Aggregated':
                # Use JSON data if available and has enough requests (>100), otherwise use CSV data
                if b250_data and b250_data.get('requests', 0) > 100:
                    avg_ms = b250_data['avg_ms']
                    p95_ms = b250_data['p95_ms']
                    cache_hit = b250_data['cache_hit_ratio']
                else:
                    # Use CSV data (more reliable when server restarted)
                    avg_ms = float(row['Average Response Time'])
                    p95_ms = float(row['95%'])
                    cache_hit = 0  # CSV doesn't have cache hit data
                
                results.append({
                    'load': 250,
                    'system': 'Baseline',
                    'avg_ms': avg_ms,
                    'p95_ms': p95_ms,
                    'throughput': float(row['Requests/s']),
                    'cache_hit': cache_hit
                })
                break
except Exception as e:
    print(f"Error loading baseline 250: {e}")

# Gemini 50
try:
    with open('results/gemini/50.json') as f:
        g50 = json.load(f)
    with open('results/gemini/locust_50.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Type') and row.get('Name') == 'Aggregated':
                results.append({
                    'load': 50,
                    'system': 'Gemini',
                    'avg_ms': g50['avg_ms'],
                    'p95_ms': g50['p95_ms'],
                    'throughput': float(row['Requests/s']),
                    'cache_hit': g50['cache_hit_ratio']
                })
                break
except Exception as e:
    print(f"Error loading gemini 50: {e}")

# Gemini 150
try:
    g150_data = None
    try:
        with open('results/gemini/150.json') as f:
            content = f.read().strip()
            if content:
                g150_data = json.loads(content)
    except:
        pass
    
    with open('results/gemini/locust_150.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Type') and row.get('Name') == 'Aggregated':
                # Use JSON data if available and has enough requests (>100), otherwise use CSV data
                if g150_data and g150_data.get('requests', 0) > 100:
                    avg_ms = g150_data['avg_ms']
                    p95_ms = g150_data['p95_ms']
                    cache_hit = g150_data['cache_hit_ratio']
                else:
                    # Use CSV data (more reliable when server restarted)
                    avg_ms = float(row['Average Response Time'])
                    p95_ms = float(row['95%'])
                    cache_hit = 0  # CSV doesn't have cache hit data
                
                results.append({
                    'load': 150,
                    'system': 'Gemini',
                    'avg_ms': avg_ms,
                    'p95_ms': p95_ms,
                    'throughput': float(row['Requests/s']),
                    'cache_hit': cache_hit
                })
                break
except Exception as e:
    print(f"Error loading gemini 150: {e}")

# Gemini 250
try:
    g250_data = None
    try:
        with open('results/gemini/250.json') as f:
            content = f.read().strip()
            if content:
                g250_data = json.loads(content)
    except:
        pass
    
    with open('results/gemini/locust_250.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Type') and row.get('Name') == 'Aggregated':
                # Use JSON data if available and has enough requests (>100), otherwise use CSV data
                if g250_data and g250_data.get('requests', 0) > 100:
                    avg_ms = g250_data['avg_ms']
                    p95_ms = g250_data['p95_ms']
                    cache_hit = g250_data['cache_hit_ratio']
                else:
                    # Use CSV data (more reliable when server restarted)
                    avg_ms = float(row['Average Response Time'])
                    p95_ms = float(row['95%'])
                    cache_hit = 0  # CSV doesn't have cache hit data
                
                results.append({
                    'load': 250,
                    'system': 'Gemini',
                    'avg_ms': avg_ms,
                    'p95_ms': p95_ms,
                    'throughput': float(row['Requests/s']),
                    'cache_hit': cache_hit
                })
                break
except Exception as e:
    print(f"Error loading gemini 250: {e}")

# Sort by load, then system
results.sort(key=lambda x: (x['load'], x['system'] == 'Baseline'))

# Print table
print("=" * 90)
print("MAIN RESULTS TABLE")
print("=" * 90)
print(f"{'Load':<8} {'System':<12} {'Avg(ms)':<12} {'P95(ms)':<12} {'Throughput(req/s)':<18} {'Cache hit(%)':<15}")
print("-" * 90)

for r in results:
    print(f"{r['load']:<8} {r['system']:<12} {r['avg_ms']:<12.2f} {r['p95_ms']:<12.2f} {r['throughput']:<18.2f} {r['cache_hit']:<15.2f}")

print("=" * 90)

# Create markdown table
os.makedirs('results', exist_ok=True)

md_table = "# Performance Results Table\n\n"
md_table += "| Load | System | Avg(ms) | P95(ms) | Throughput(req/s) | Cache hit(%) |\n"
md_table += "|------|--------|---------|---------|-------------------|-------------|\n"

for r in results:
    md_table += f"| {r['load']} | {r['system']} | {r['avg_ms']:.2f} | {r['p95_ms']:.2f} | {r['throughput']:.2f} | {r['cache_hit']:.2f} |\n"

md_table += "\n## Notes\n"
md_table += "- Load: Number of concurrent users\n"
md_table += "- Avg(ms): Average response time in milliseconds\n"
md_table += "- P95(ms): 95th percentile response time in milliseconds\n"
md_table += "- Throughput: Requests per second\n"
md_table += "- Cache hit(%): Percentage of requests served from cache\n"

with open('results/RESULTS_TABLE.md', 'w') as f:
    f.write(md_table)

# Create CSV
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

print(f"\n✅ Results table saved to: results/RESULTS_TABLE.md")
print(f"✅ Results CSV saved to: results/RESULTS_TABLE.csv")

