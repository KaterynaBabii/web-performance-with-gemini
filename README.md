# Web Gemini Performance Testbed

**This will run 10 tests** per user level: **10** independent Locust runs (`run1` … `run10`) at **50, 100, 150, 200, 250,** and **300** concurrent users. By default `./scripts/run-benchmark-grid.sh` exercises **both** baseline and optimized stacks (override with `BENCHMARK_GRID_SYSTEMS`). Step-by-step: [Testing Workflow](#testing-workflow).

## Overview

This testbed applies Gemini-assisted performance ideas to a Node.js web application. The primary benchmark is that **grid** (six user levels × 10 runs each, per stack); optional legacy scripts only run **50, 150,** and **250** users once each. Two application configurations:

- **Baseline Version**: Intentionally includes common performance anti-patterns (slow queries, N+1 problems, no caching)
- **Optimized Version**: Implements Gemini-informed improvements (indexes, query rewrites, Redis caching)

## Architecture

- **Backend**: Node.js + Express
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Load Testing**: Locust
- **Metrics**: CSV export for analysis

## Project Structure

```
web-gemini/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── db/
│   ├── schema.sql
│   ├── seed.sql
│   └── indexes_optimized.sql
├── server/
│   ├── package.json
│   └── src/
│       ├── app.js
│       ├── db.js
│       ├── redis.js
│       ├── metrics.js
│       └── routes/
│           ├── products.js
│           ├── dashboard.js
│           ├── recommendations.js
│           └── checkout.js
├── loadtest/
│   └── locustfile.py
├── prompts/
│   ├── prompt_query_optimization.txt
│   ├── prompt_caching_strategy.txt
│   └── prompt_bottleneck_analysis.txt
├── results/
│   ├── baseline/
│   └── gemini/
└── scripts/
    ├── run-benchmark-grid.sh
    ├── seed.js
    ├── run-baseline.sh
    └── run-optimized.sh
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.8+ (for Locust)

### 1. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be healthy (about 10 seconds)
```

### 2. Seed Database

```bash
# Install dependencies
cd server && npm install
cd ..

# Seed the database
npm run seed
```

### 3. Run Baseline Version

```bash
# Set environment
export APP_VERSION=baseline

# Start server
cd server && npm start
```

### 4. Run Optimized Version

First, apply database migrations:

```bash
# Connect to PostgreSQL
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < db/indexes_optimized.sql
```

Then start the optimized server:

```bash
# Set environment
export APP_VERSION=optimized

# Start server
cd server && npm start
```

## API Endpoints

### 1. GET /products?search=...

Product search endpoint with filtering.

**Baseline Issues:**
- No indexes
- SELECT * (includes large fields)
- Inefficient LIKE search
- No pagination

**Optimizations:**
- GIN index for full-text search
- Explicit column selection
- Pagination support
- Indexed category joins

### 2. GET /users/:id/dashboard

User dashboard with orders, preferences, and activity.

**Baseline Issues:**
- N+1 query pattern
- 5+ separate database queries
- Missing indexes

**Optimizations:**
- Single query with JOINs
- Batch loading
- Proper indexes

### 3. GET /recommendations/:userId

Personalized product recommendations.

**Baseline Issues:**
- Expensive computation on every request
- No caching

**Optimizations:**
- Redis caching (5-minute TTL)
- Cache invalidation on checkout
- Optimized query with indexes

### 4. POST /checkout

Order checkout endpoint.

**Baseline Issues:**
- Multiple separate queries
- No transaction handling
- Loop-based inserts

**Optimizations:**
- Database transactions
- Batch operations
- Cache invalidation

## Load Testing

### Install Locust

```bash
pip install locust
```

### Run Load Test

```bash
# Baseline testing (lower load)
locust -f loadtest/locustfile.py --host=http://localhost:3000 \
  --users=50 --spawn-rate=5 --run-time=3m \
  --csv=results/locust-baseline

# Optimized testing (higher load)
locust -f loadtest/locustfile.py --host=http://localhost:3000 \
  --users=100 --spawn-rate=10 --run-time=3m \
  --csv=results/locust-optimized
```

### Access Locust Web UI

```bash
locust -f loadtest/locustfile.py --host=http://localhost:3000
# Open http://localhost:8089
```

## Metrics Collection

Metrics are automatically collected and can be exported:

```bash
# Get current metrics
curl http://localhost:3000/metrics

# Export to CSV
curl -X POST http://localhost:3000/metrics/export
```

Metrics are saved to:
- `results/baseline/` for baseline version
- `results/gemini/` for optimized version

Metrics include:
- Avg Latency (ms)
- P95 Latency (ms)
- Throughput (req/s)
- Avg DB Query Time (ms)
- Cache Hit Ratio (%)

## Gemini Recommendations

See `CHANGES.md` for detailed documentation of:
- Gemini's analysis of performance issues
- Specific recommendations provided
- Implementation details
 - Measured performance outcomes tied to those recommendations

## Example Prompts

The `prompts/` directory contains example prompts used to generate recommendations:
- `prompt_query_optimization.txt` - Query performance analysis
- `prompt_caching_strategy.txt` - Caching strategy design
- `prompt_bottleneck_analysis.txt` - N+1 query detection

## Results

Report **measured** results generated from the benchmark grid and stored under `results/`.
## Testing Workflow

Complete step-by-step guide for running all performance tests.

### Phase 1: Initial Setup (One-Time)

```bash
# 1. Start Docker services
cd /Users/katerynababii/Documents/Projects/web-gemini
docker compose up -d

# 2. Seed database (if not already done)
npm run seed
```

### Phase 2: Full benchmark grid (recommended)

Prerequisites: Docker stack up, database seeded, Locust installed (`pip install -r requirements.txt` in `loadtest/` if needed).

```bash
# Runs baseline and optimized arms by default (tears down/recreates stack per condition).
./scripts/run-benchmark-grid.sh
```

This will run **10 tests** (10 Locust repetitions, `run1` … `run10`) **per user level**:

- **50** concurrent users  
- **100** concurrent users  
- **150** concurrent users  
- **200** concurrent users  
- **250** concurrent users  
- **300** concurrent users  

Each run uses a **3-minute** steady-state window (see script for spawn rates). Set `BENCHMARK_GRID_SYSTEMS=baseline` or `gemini` to run one arm only; set `BENCHMARK_GRID_REPS` to change the repetition count (default **10**).

Results are saved under:

- `results/baseline/<users>_run<1-10>.json` and `results/baseline/locust_<users>_run<k>.csv`
- `results/gemini/<users>_run<1-10>.json` and `results/gemini/locust_<users>_run<k>.csv`

### Phase 2b: Quick three-run scripts (optional)

Single Locust run each at **50, 150, and 250** users only—useful for smoke tests, **not** a substitute for the grid above.

**Baseline**

```bash
./scripts/apply-baseline-db.sh
# Baseline flags in docker-compose: ENABLE_REDIS_CACHE=0, ENABLE_BATCH_DASHBOARD=0, ENABLE_OPT_SEARCH=0
docker compose up -d --build
./scripts/run-baseline-load-tests.sh
```

**Gemini-optimized**

```bash
./scripts/apply-optimized-db.sh
# Optimized flags: ENABLE_REDIS_CACHE=1, ENABLE_BATCH_DASHBOARD=1, ENABLE_OPT_SEARCH=1
docker compose up -d --build
./scripts/run-optimized-load-tests.sh
```

Outputs: `results/baseline|gemini/{50,150,250}.json` and matching `locust_*.csv` (no `_run{k}` suffix).

### Phase 3: Generate Results Table

```bash
# Create final results table
python3 scripts/create-results-table.py

# View results
cat results/RESULTS_TABLE.md
```

The results table will show:
- Load (users)
- System (Baseline vs Gemini)
- Avg(ms) - Average latency
- P95(ms) - 95th percentile latency
- Throughput(req/s) - Requests per second
- Cache hit(%) - Cache hit ratio

### Optional: Other scripts

- `run-benchmark-grid.sh` — full statistical grid (10 runs × six user levels; see Phase 2)
- `run-baseline-load-tests.sh` / `run-optimized-load-tests.sh` — quick three-load smoke runs (Phase 2b)
- `apply-baseline-db.sh` - Reset to baseline database state
- `apply-optimized-db.sh` - Apply optimized indexes
- `create-results-table.py` - Generate results table

## Development

### Local Development (without Docker)

```bash
# Install dependencies
cd server && npm install

# Set up environment
cp .env.example .env
# Edit .env with your database credentials

# Start PostgreSQL and Redis locally
# Then run:
npm run seed
npm start
```

### Running Tests

```bash
# Test baseline version
APP_VERSION=baseline cd server && npm start

# Test optimized version
APP_VERSION=optimized cd server && npm start
```

