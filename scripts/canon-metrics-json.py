#!/usr/bin/env python3
"""
Merge canonical IEEE paper metric keys into a per-run JSON from /metrics + Locust.

Writes (and preserves existing fields):
  avg_latency_ms, p95_latency_ms, throughput_rps, cache_hit_pct

Usage:
  python3 scripts/canon-metrics-json.py results/<variant>/300_run1.json [results/<variant>/locust_300_run1.csv]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def load_aggregated_row(csv_path: Path) -> dict | None:
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Type") == "" and row.get("Name") == "Aggregated":
                return row
    return None


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: canon-metrics-json.py <run.json> [locust_stats.csv]", file=sys.stderr)
        sys.exit(1)
    jpath = Path(sys.argv[1])
    data = json.loads(jpath.read_text(encoding="utf-8"))

    thr = data.get("throughput_rps")
    if thr is None:
        thr = data.get("throughput")
    if len(sys.argv) > 2:
        cpath = Path(sys.argv[2])
        if cpath.exists():
            row = load_aggregated_row(cpath)
            if row and row.get("Requests/s"):
                # Locust Aggregated row is authoritative for steady-state RPS
                thr = float(row["Requests/s"])

    avg = data.get("avg_latency_ms")
    if avg is None:
        avg = data.get("avg_ms")
    p95 = data.get("p95_latency_ms")
    if p95 is None:
        p95 = data.get("p95_ms")
    cache = data.get("cache_hit_pct")
    if cache is None:
        cache = data.get("cache_hit_ratio")

    data["avg_latency_ms"] = float(avg or 0)
    data["p95_latency_ms"] = float(p95 or 0)
    data["throughput_rps"] = float(thr or 0)
    data["cache_hit_pct"] = float(cache or 0)

    jpath.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
