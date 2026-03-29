# Locust benchmark — baseline app, 300 users, 3 minutes

| Field | Value |
|-------|--------|
| CONFIG_NAME | baseline |
| APP_VERSION | baseline |
| ENABLE_REDIS_CACHE | 0 |
| ENABLE_BATCH_DASHBOARD | 0 |
| ENABLE_OPT_SEARCH | 0 |
| Git commit | `bd51cb1eca8deab6cfd28fad38d3f2e5a58bfcf2` |
| Locust CSV | `results/baseline/locust_300_run1.csv` |
| Spawn rate | 30 users/s |
| Run time | 3m |

## Per-endpoint table (from Locust `*_stats.csv`)

| Endpoint | Avg latency (ms) | P95 latency (ms) | Throughput (req/s) | Request count | Failures |
|----------|------------------|------------------|---------------------|---------------|----------|
| `GET /products?search=[term]` | 2748.14 | 5600 | 9.21 | 1643 | 0 |
| `GET /users/[id]/dashboard` | 16349.83 | 27000 | 5.62 | 1002 | 0 |
| `GET /recommendations/[userId]` | 9026.05 | 14000 | 5.70 | 1017 | 0 |
| `POST /checkout` | 22164.67 | 43000 | 2.80 | 500 | 0 |
| **Aggregated** | 9889.37 | 28000 | 23.33 | 4162 | 0 |

*P95 column uses the `95%` percentile field from the Locust CSV.*
