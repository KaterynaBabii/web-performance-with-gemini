# Web Gemini Performance Testbed

IEEE Access Research Testbed for Gemini-Assisted Performance Engineering

## Overview

This testbed demonstrates the application of Gemini AI for performance engineering assistance in a Node.js web application. The project includes two versions:

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
- Expected performance improvements

## Example Prompts

The `prompts/` directory contains example prompts used to generate recommendations:
- `prompt_query_optimization.txt` - Query performance analysis
- `prompt_caching_strategy.txt` - Caching strategy design
- `prompt_bottleneck_analysis.txt` - N+1 query detection

## Results

Expected performance improvements (from baseline to optimized):

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Avg Latency | ~180ms | ~25ms | 86% ↓ |
| P95 Latency | ~450ms | ~80ms | 82% ↓ |
| Throughput | ~55 req/s | ~380 req/s | 590% ↑ |
| Avg DB Query Time | ~120ms | ~18ms | 85% ↓ |
| Cache Hit Ratio | 0% | ~85% | N/A |

*Actual results will vary based on hardware and load test configuration*

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

### Phase 2: Baseline Tests (Version A)

```bash
# 1. Apply baseline database (drop indexes)
./scripts/apply-baseline-db.sh

# 2. Ensure baseline mode in docker-compose.yml
# (ENABLE_REDIS_CACHE=0, ENABLE_BATCH_DASHBOARD=0, ENABLE_OPT_SEARCH=0)
docker compose up -d --build

# 3. Run all baseline load tests (A1, A2, A3)
./scripts/run-baseline-load-tests.sh
```

This will run three tests:
- **A1**: 50 users, 3 minutes
- **A2**: 150 users, 3 minutes
- **A3**: 250 users, 3 minutes

Results are saved to:
- `results/baseline/50.json`, `150.json`, `250.json`
- `results/baseline/locust_50.csv`, `locust_150.csv`, `locust_250.csv`

### Phase 3: Gemini-Optimized Tests (Version B)

```bash
# 1. Apply optimized database (add indexes)
./scripts/apply-optimized-db.sh

# 2. Ensure optimized mode in docker-compose.yml
# (ENABLE_REDIS_CACHE=1, ENABLE_BATCH_DASHBOARD=1, ENABLE_OPT_SEARCH=1)
docker compose up -d --build

# 3. Run all optimized load tests (B1, B2, B3)
./scripts/run-optimized-load-tests.sh
```

This will run three tests:
- **B1**: 50 users, 3 minutes
- **B2**: 150 users, 3 minutes
- **B3**: 250 users, 3 minutes

Results are saved to:
- `results/gemini/50.json`, `150.json`, `250.json`
- `results/gemini/locust_50.csv`, `locust_150.csv`, `locust_250.csv`

### Phase 4: Generate Results Table

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

### Optional: Individual Test Runs

If you need to run tests individually, see the scripts in `scripts/` directory:
- `run-baseline-load-tests.sh` - Automated baseline tests
- `run-optimized-load-tests.sh` - Automated optimized tests
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

