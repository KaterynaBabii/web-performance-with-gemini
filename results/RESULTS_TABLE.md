# Performance Results Table

| Load | System | Avg(ms) | P95(ms) | Throughput(req/s) | Cache hit(%) |
|------|--------|---------|---------|-------------------|-------------|
| 50 | Gemini | 262.35 | 755.00 | 21.39 | 34.26 |
| 50 | Baseline | 229.49 | 617.00 | 21.95 | 27.80 |
| 150 | Gemini | 1900.82 | 5633.00 | 36.85 | 41.93 |
| 150 | Baseline | 2890.33 | 5570.00 | 29.28 | 55.91 |
| 250 | Gemini | 3156.12 | 7284.00 | 44.73 | 61.17 |
| 250 | Baseline | 7720.46 | 13096.00 | 23.53 | 34.13 |

## Notes
- Load: Number of concurrent users
- Avg(ms): Average response time in milliseconds
- P95(ms): 95th percentile response time in milliseconds
- Throughput: Requests per second
- Cache hit(%): Percentage of requests served from cache
