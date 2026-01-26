# Testing Guide - Complete Step-by-Step Instructions

This guide provides comprehensive instructions for running performance tests comparing the Baseline and Gemini-optimized versions of the Web Gemini Performance Testbed.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Automated)](#quick-start-automated)
3. [Manual Testing Workflow](#manual-testing-workflow)
4. [Understanding Test Configurations](#understanding-test-configurations)
5. [Expected Results](#expected-results)
6. [Troubleshooting](#troubleshooting)
7. [Verification Checklist](#verification-checklist)

---

## Prerequisites

Before running tests, ensure you have:

1. **Docker and Docker Compose** installed and running
2. **Node.js 18+** installed
3. **Python 3.8+** with pip installed
4. **Locust** installed: `pip install locust`

Verify installations:

```bash
docker --version
docker compose version
node --version
python3 --version
pip3 show locust
```

---

## Quick Start (Automated)

The easiest way to run all tests is using the automated script:

### One-Command Test Run

```bash
# Make script executable (first time only)
chmod +x scripts/run-all-tests-final.sh

# Run all tests (takes ~30 minutes)
./scripts/run-all-tests-final.sh
```

This script will:
1. ✅ Drop all indexes for baseline state
2. ✅ Run 3 baseline tests (50, 150, 250 users)
3. ✅ Apply optimized indexes
4. ✅ Run 3 Gemini-optimized tests (50, 150, 250 users)
5. ✅ Generate final results table

**Results will be saved to:**
- `results/baseline/50.json`, `150.json`, `250.json`
- `results/baseline/locust_50.csv`, `locust_150.csv`, `locust_250.csv`
- `results/gemini/50.json`, `150.json`, `250.json`
- `results/gemini/locust_50.csv`, `locust_150.csv`, `locust_250.csv`
- `results/RESULTS_TABLE.md` (final comparison table)

**Monitor progress:**
```bash
# Watch test progress in real-time
tail -f /tmp/test-run.log
```

---

## Manual Testing Workflow

If you prefer to run tests manually or need to run individual tests:

### Phase 1: Initial Setup (One-Time)

```bash
# 1. Navigate to project root
cd /path/to/web-gemini

# 2. Start Docker services (PostgreSQL, Redis, API)
docker compose up -d --build

# 3. Wait for services to be healthy (~15 seconds)
docker compose ps

# 4. Seed the database with test data
#    (200k users, 50k products, 400k orders, 2M product events)
npm run seed

# 5. Verify database is seeded
docker exec -it web-gemini-postgres psql -U postgres -d web_gemini -c \
  "SELECT COUNT(*) as users FROM users; SELECT COUNT(*) as products FROM products;"
```

Expected counts:
- Users: ~200,000
- Products: ~50,000
- Orders: ~400,000
- Product Events: ~2,000,000

### Phase 2: Baseline Tests (Version A)

Baseline tests use **no indexes**, **no caching**, and **inefficient queries** (N+1 pattern).

#### Step 2.1: Prepare Baseline Database

```bash
# Drop all performance indexes
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
  < db/indexes_baseline_drop.sql

# Verify indexes are dropped (should return 0 rows)
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini -c \
  "SELECT indexname FROM pg_indexes WHERE tablename IN ('products','orders','order_items','user_preferences','user_activity','product_events') AND indexname NOT LIKE '%_pkey';"
```

#### Step 2.2: Start Baseline Server

```bash
# Start server in baseline mode (no cache, no optimizations)
APP_VERSION=baseline \
ENABLE_REDIS_CACHE=0 \
ENABLE_BATCH_DASHBOARD=0 \
ENABLE_OPT_SEARCH=0 \
docker compose up -d --force-recreate

# Wait for server to be ready
sleep 15

# Verify baseline configuration
docker exec web-gemini-app printenv | grep -E "ENABLE|APP_VERSION"
```

**Expected output:**
```
APP_VERSION=baseline
ENABLE_REDIS_CACHE=0
ENABLE_BATCH_DASHBOARD=0
ENABLE_OPT_SEARCH=0
```

**Verify health:**
```bash
curl http://localhost:3000/health
# Should return: {"status":"ok","version":"baseline",...}
```

#### Step 2.3: Run Baseline Load Tests

Run three tests at different load levels:

**Test A1: Low Load (50 users)**
```bash
# Reset metrics
docker compose restart app
sleep 10

# Run Locust test
cd loadtest
python3 -m locust \
  -H http://localhost:3000 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=3m \
  --headless \
  --csv=../results/baseline/50 \
  --loglevel=WARNING

# Collect metrics (AFTER test completes)
sleep 5
curl -s http://localhost:3000/metrics > ../results/baseline/50.json

# Rename CSV file
mv ../results/baseline/50_stats.csv ../results/baseline/locust_50.csv
```

**Test A2: Medium Load (150 users)**
```bash
docker compose restart app
sleep 10

cd loadtest
python3 -m locust \
  -H http://localhost:3000 \
  --users=150 \
  --spawn-rate=10 \
  --run-time=3m \
  --headless \
  --csv=../results/baseline/150 \
  --loglevel=WARNING

sleep 5
curl -s http://localhost:3000/metrics > ../results/baseline/150.json
mv ../results/baseline/150_stats.csv ../results/baseline/locust_150.csv
```

**Test A3: High Load (250 users)**
```bash
docker compose restart app
sleep 15  # Longer wait for high load

cd loadtest
python3 -m locust \
  -H http://localhost:3000 \
  --users=250 \
  --spawn-rate=10 \
  --run-time=3m \
  --headless \
  --csv=../results/baseline/250 \
  --loglevel=WARNING

sleep 5
curl -s http://localhost:3000/metrics > ../results/baseline/250.json
mv ../results/baseline/250_stats.csv ../results/baseline/locust_250.csv
```

### Phase 3: Gemini-Optimized Tests (Version B)

Gemini-optimized tests use **optimized indexes**, **Redis caching**, and **efficient queries** (JOINs, batch loading).

#### Step 3.1: Apply Optimized Database

```bash
# Apply optimized indexes
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini \
  < db/indexes_optimized.sql

# Verify indexes are created (should return 10 rows)
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini -c \
  "SELECT COUNT(*) as index_count FROM pg_indexes WHERE tablename IN ('products','orders','order_items','user_preferences','user_activity','product_events') AND indexname NOT LIKE '%_pkey';"
```

#### Step 3.2: Start Optimized Server

```bash
# Start server in optimized mode (with cache, optimizations)
APP_VERSION=optimized \
ENABLE_REDIS_CACHE=1 \
ENABLE_BATCH_DASHBOARD=1 \
ENABLE_OPT_SEARCH=1 \
docker compose up -d --force-recreate

# Wait for server to be ready
sleep 15

# Verify optimized configuration
docker exec web-gemini-app printenv | grep -E "ENABLE|APP_VERSION"
```

**Expected output:**
```
APP_VERSION=optimized
ENABLE_REDIS_CACHE=1
ENABLE_BATCH_DASHBOARD=1
ENABLE_OPT_SEARCH=1
```

**Verify health and cache:**
```bash
curl http://localhost:3000/health
# Should return: {"status":"ok","version":"optimized",...}

# Test cache (should be fast on second request)
time curl -s http://localhost:3000/recommendations/1 > /dev/null
time curl -s http://localhost:3000/recommendations/1 > /dev/null
# Second request should be much faster
```

#### Step 3.3: Run Gemini-Optimized Load Tests

Run the same three load levels:

**Test B1: Low Load (50 users)**
```bash
docker compose restart app
sleep 10

cd loadtest
python3 -m locust \
  -H http://localhost:3000 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=3m \
  --headless \
  --csv=../results/gemini/50 \
  --loglevel=WARNING

sleep 5
curl -s http://localhost:3000/metrics > ../results/gemini/50.json
mv ../results/gemini/50_stats.csv ../results/gemini/locust_50.csv
```

**Test B2: Medium Load (150 users)**
```bash
docker compose restart app
sleep 10

cd loadtest
python3 -m locust \
  -H http://localhost:3000 \
  --users=150 \
  --spawn-rate=10 \
  --run-time=3m \
  --headless \
  --csv=../results/gemini/150 \
  --loglevel=WARNING

sleep 5
curl -s http://localhost:3000/metrics > ../results/gemini/150.json
mv ../results/gemini/150_stats.csv ../results/gemini/locust_150.csv
```

**Test B3: High Load (250 users)**
```bash
docker compose restart app
sleep 15

cd loadtest
python3 -m locust \
  -H http://localhost:3000 \
  --users=250 \
  --spawn-rate=10 \
  --run-time=3m \
  --headless \
  --csv=../results/gemini/250 \
  --loglevel=WARNING

sleep 5
curl -s http://localhost:3000/metrics > ../results/gemini/250.json
mv ../results/gemini/250_stats.csv ../results/gemini/locust_250.csv
```

### Phase 4: Generate Results Table

```bash
# Generate final comparison table
python3 scripts/create-results-table.py

# View results
cat results/RESULTS_TABLE.md
```

The script will:
- Extract metrics from JSON files (avg_ms, p95_ms, cache_hit_ratio)
- Extract throughput from Locust CSV files
- Generate a markdown table and CSV file

---

## Understanding Test Configurations

### Baseline Configuration

**Database:**
- ❌ No performance indexes (only primary keys)
- ❌ Full table scans for searches
- ❌ No query optimization

**Code:**
- ❌ N+1 query pattern (dashboard endpoint)
- ❌ No Redis caching
- ❌ Inefficient LIKE searches (products endpoint)
- ❌ SELECT * (fetches all columns)
- ❌ No pagination

**Environment Variables:**
```bash
APP_VERSION=baseline
ENABLE_REDIS_CACHE=0
ENABLE_BATCH_DASHBOARD=0
ENABLE_OPT_SEARCH=0
```

### Gemini-Optimized Configuration

**Database:**
- ✅ 10 performance indexes (GIN for full-text, composite indexes)
- ✅ Indexed joins and filters
- ✅ Optimized query plans

**Code:**
- ✅ Single query with JOINs (dashboard endpoint)
- ✅ Redis caching with 5-minute TTL (recommendations endpoint)
- ✅ Full-text search with GIN index (products endpoint)
- ✅ Explicit column selection
- ✅ Pagination support

**Environment Variables:**
```bash
APP_VERSION=optimized
ENABLE_REDIS_CACHE=1
ENABLE_BATCH_DASHBOARD=1
ENABLE_OPT_SEARCH=1
```

---

## Expected Results

Based on the optimizations, you should see significant improvements:

### Target Performance Table

| Load | System | Avg(ms) | P95(ms) | Throughput(req/s) | Cache hit(%) |
|------|--------|---------|---------|-------------------|-------------|
| 50 | Baseline | ~490 | ~1140 | ~20 | 0% |
| 50 | Gemini | ~216 | ~590 | ~22 | ~30% |
| 150 | Baseline | 1200-1500 | 4500-5000 | 30-40 | 0% |
| 150 | Gemini | 200-400 | 800-1500 | 60-80 | 50-70% |
| 250 | Baseline | 2000-3000 | 8000-10000 | 25-40 | 0% |
| 250 | Gemini | 400-900 | 1200-3000 | 90-130 | 40-70% |

### Key Improvements

- **4-8× latency reduction** (avg and P95)
- **2-3× throughput improvement**
- **Strong cache evidence** (40-70% cache hit ratio for Gemini)

### Metrics Explanation

- **Avg(ms)**: Average response time in milliseconds
- **P95(ms)**: 95th percentile response time (95% of requests are faster than this)
- **Throughput(req/s)**: Requests per second the system can handle
- **Cache hit(%)**: Percentage of requests served from Redis cache (0% for baseline, 40-70% for Gemini)

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port 3000 is in use
lsof -i :3000

# Kill process if needed
kill -9 $(lsof -t -i :3000)

# Check Docker services
docker compose ps

# Check application logs
docker compose logs app
```

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker compose ps postgres

# Check connection
docker exec -it web-gemini-postgres psql -U postgres -d web_gemini

# Check if database is seeded
docker exec -it web-gemini-postgres psql -U postgres -d web_gemini -c \
  "SELECT COUNT(*) FROM users;"
```

### Redis Connection Errors

```bash
# Verify Redis is running
docker compose ps redis

# Check connection
docker exec -it web-gemini-redis redis-cli ping
# Should return: PONG

# Check Redis is enabled in app
docker exec web-gemini-app printenv | grep ENABLE_REDIS_CACHE
```

### Cache Hit Ratio is 0% (Gemini Tests)

**Possible causes:**
1. Redis cache not enabled - Check `ENABLE_REDIS_CACHE=1`
2. Locust using random user IDs - Should use fixed pool (already configured in `locustfile.py`)
3. Metrics collected after server restart - Always collect metrics AFTER test completes, BEFORE restart

**Fix:**
```bash
# Verify cache is working manually
curl http://localhost:3000/recommendations/1
curl http://localhost:3000/recommendations/1  # Should be faster
curl http://localhost:3000/metrics  # Should show cache_hit_ratio > 0
```

### Locust Not Found

```bash
# Install Locust
pip3 install locust

# Or use Docker
docker run -v $(pwd):/mnt/locust -p 8089:8089 \
  locustio/locust -f /mnt/locust/loadtest/locustfile.py \
  --host=http://host.docker.internal:3000
```

### Metrics Show 0 Requests

**Cause:** Metrics were collected before test started or after server restart.

**Fix:** Always follow this order:
1. Restart API (resets metrics)
2. Wait 10 seconds
3. Run Locust test
4. Wait 5 seconds after test completes
5. Collect metrics (BEFORE next restart)

### Baseline Performance Too Good

**Cause:** Indexes not dropped or optimizations still enabled.

**Fix:**
```bash
# Verify indexes are dropped
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini -c \
  "SELECT indexname FROM pg_indexes WHERE tablename IN ('products','orders') AND indexname NOT LIKE '%_pkey';"
# Should return 0 rows

# Verify baseline flags
docker exec web-gemini-app printenv | grep ENABLE
# All should be 0
```

---

## Verification Checklist

Before running tests, verify:

- [ ] Docker services are running: `docker compose ps`
- [ ] Database is seeded: Check user/product counts
- [ ] Baseline: No indexes (verify with SQL query)
- [ ] Baseline: All ENABLE flags are 0
- [ ] Baseline: Health check returns `"version":"baseline"`
- [ ] Gemini: 10 indexes created (verify with SQL query)
- [ ] Gemini: All ENABLE flags are 1
- [ ] Gemini: Health check returns `"version":"optimized"`
- [ ] Gemini: Cache works (test recommendations endpoint twice)
- [ ] Metrics endpoint works: `curl http://localhost:3000/metrics`

After each test:

- [ ] Metrics JSON file exists and has data
- [ ] Locust CSV file exists and renamed correctly
- [ ] Cache hit ratio is 0% for baseline tests
- [ ] Cache hit ratio is 40-70% for Gemini tests
- [ ] Metrics collected AFTER test completes

After all tests:

- [ ] All 6 JSON files exist (baseline: 50, 150, 250; gemini: 50, 150, 250)
- [ ] All 6 CSV files exist and are renamed correctly
- [ ] Results table generated: `results/RESULTS_TABLE.md`
- [ ] Results show clear improvements (Gemini faster than Baseline)

---

## Quick Reference Commands

```bash
# Start everything
docker compose up -d
npm run seed

# Baseline mode
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < db/indexes_baseline_drop.sql
APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 \
  docker compose up -d --force-recreate

# Optimized mode
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < db/indexes_optimized.sql
APP_VERSION=optimized ENABLE_REDIS_CACHE=1 ENABLE_BATCH_DASHBOARD=1 ENABLE_OPT_SEARCH=1 \
  docker compose up -d --force-recreate

# Run single test
cd loadtest
python3 -m locust -H http://localhost:3000 --users=50 --spawn-rate=5 --run-time=3m --headless --csv=../results/test

# Collect metrics
curl http://localhost:3000/metrics > results/test.json

# Generate results table
python3 scripts/create-results-table.py

# View results
cat results/RESULTS_TABLE.md
```

---

## Additional Resources

- **README.md**: Project overview and architecture
- **QUICK_START.md**: Quick reference checklist
- **prompts/**: Example prompts used for Gemini recommendations
- **CHANGELOG_OPTIMIZATIONS.md**: Detailed list of optimizations (if exists)

For questions or issues, check the troubleshooting section above or review the application logs:
```bash
docker compose logs app
```
