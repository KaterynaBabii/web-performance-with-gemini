# Locust benchmark summary (tabular)

**Source file:** `results/baseline/locust_300_run1.csv`  
**Load:** 300 concurrent users (Locust `WebGeminiUser`; see `loadtest/locustfile.py`).  
**Note:** Values are taken from that CSV’s per-endpoint statistics row (not the paper’s Aggregated row alone).

| Endpoint (Locust name) | Avg latency (ms) | P95 latency (ms) | Throughput (req/s) | Request count | Failures |
|------------------------|------------------|------------------|--------------------|---------------|----------|
| `GET /products?search=[term]` | 1373.53 | 1900 | 6.93 | 1246 | 0 |
| `GET /users/[id]/dashboard` | 48276.83 | 64000 | 3.43 | 616 | 0 |
| `GET /recommendations/[userId]` | 4954.31 | 6500 | 4.42 | 795 | 0 |
| `POST /checkout` | 12759.87 | 23000 | 2.09 | 376 | 0 |
| **Aggregated (all tasks)** | 13249.70 | 54000 | 16.87 | 3033 | 0 |

**How to reproduce:** Run Locust against the baseline app configuration, export CSV, and copy the same columns—or run `scripts/` load workflow if documented in repo root README.

**Paper checklist:** For publication, cite **one** canonical run id (path + git commit + env vars) and optionally repeat runs with mean ± CI in supplementary material.
