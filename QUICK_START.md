# Quick Start - Testing Checklist

## ✅ Pre-flight Check

- [ ] Docker and Docker Compose installed
- [ ] Node.js 18+ installed  
- [ ] Python 3.8+ with `pip install locust`

## 🚀 Execution Steps

### 1. Build and Start Services
```bash
docker compose up --build -d
```

### 2. Seed Database
```bash
cd server && npm install && cd ..
npm run seed
```

### 3. Run Baseline Test
```bash
# Start baseline server
cd server
APP_VERSION=baseline npm start &
cd ..

# Wait 5 seconds, then run Locust
locust -f loadtest/locustfile.py --host=http://localhost:3000 \
  --users=50 --spawn-rate=5 --run-time=3m --headless \
  --csv=results/locust-baseline

# Collect metrics
curl http://localhost:3000/metrics > results/baseline/metrics.json
curl -X POST http://localhost:3000/metrics/export
```

### 4. Apply Database Optimizations
```bash
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < db/indexes_optimized.sql
```

### 5. Verify Code Changes (Already Implemented ✅)

- ✅ **Dashboard Batch Query**: `server/src/routes/dashboard.js` - Single query with JOINs
- ✅ **Recommendations Redis Cache**: `server/src/routes/recommendations.js` - Redis with 5min TTL
- ✅ **Product Search Rewrite**: `server/src/routes/products.js` - Full-text search + pagination

### 6. Run Optimized Test
```bash
# Stop baseline server first (Ctrl+C or kill PID)

# Start optimized server
cd server
APP_VERSION=optimized npm start &
cd ..

# Wait 5 seconds, then run Locust
locust -f loadtest/locustfile.py --host=http://localhost:3000 \
  --users=100 --spawn-rate=10 --run-time=3m --headless \
  --csv=results/locust-optimized

# Collect metrics
curl http://localhost:3000/metrics > results/gemini/metrics.json
curl -X POST http://localhost:3000/metrics/export
```

### 7. Create Results Table
```bash
./scripts/create-results-table.sh
cat results/comparison-table.txt
```

## 📊 Expected Results

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Avg Latency | ~180ms | ~25ms | 86% ↓ |
| P95 Latency | ~450ms | ~80ms | 82% ↓ |
| Throughput | ~55 req/s | ~380 req/s | 590% ↑ |
| Avg DB Query Time | ~120ms | ~18ms | 85% ↓ |
| Cache Hit Ratio | 0% | ~85% | N/A |

## 🔍 Verification Commands

```bash
# Check services
docker compose ps

# Check database indexes
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini -c "\di"

# Check server health
curl http://localhost:3000/health

# View metrics
curl http://localhost:3000/metrics | jq '.'
```

## 📁 Results Location

- Baseline: `results/baseline/metrics-*.csv`
- Optimized: `results/gemini/metrics-*.csv`
- Comparison: `results/comparison-table.txt`

