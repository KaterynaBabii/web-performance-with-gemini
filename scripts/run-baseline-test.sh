#!/bin/bash
# Run baseline test: start server, run locust, collect metrics

set -e

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "BASELINE TEST - Starting..."
echo "=========================================="

# Start services if not running
echo "1. Starting Docker services..."
cd "$PROJECT_ROOT"
docker compose up -d postgres redis

# Wait for services to be ready
echo "2. Waiting for services to be healthy..."
sleep 10

# Seed database
echo "3. Seeding database..."
cd "$PROJECT_ROOT" || {
    echo "ERROR: Failed to change to project root: $PROJECT_ROOT"
    exit 1
}
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found. Current directory: $(pwd)"
    echo "Expected project root: $PROJECT_ROOT"
    exit 1
fi
echo "   Running from: $(pwd)"
npm run seed || {
    echo "ERROR: Database seeding failed"
    exit 1
}

# Check if port 3000 is in use and kill existing process
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "4. Port 3000 is in use. Killing existing process..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start baseline server in background
echo "5. Starting baseline server..."
echo "   Setting baseline flags: ENABLE_REDIS_CACHE=0, ENABLE_BATCH_DASHBOARD=0, ENABLE_OPT_SEARCH=0"
export APP_VERSION=baseline
export ENABLE_REDIS_CACHE=0
export ENABLE_BATCH_DASHBOARD=0
export ENABLE_OPT_SEARCH=0
cd "$PROJECT_ROOT/server"
npm install 2>/dev/null || true
PORT=3000 APP_VERSION=baseline ENABLE_REDIS_CACHE=0 ENABLE_BATCH_DASHBOARD=0 ENABLE_OPT_SEARCH=0 node src/app.js &
SERVER_PID=$!
cd "$PROJECT_ROOT"

# Wait for server to start
echo "6. Waiting for server to start..."
sleep 5

# Check if server is running
if ! curl -s http://localhost:3000/health > /dev/null; then
    echo "ERROR: Server failed to start"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo "7. Server is running. Starting Locust load test..."
echo "   Run this command in another terminal:"
echo "   cd $PROJECT_ROOT"
echo "   locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=50 --spawn-rate=5 --run-time=3m --headless --csv=results/locust-baseline"
echo ""
echo "   Or run it now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=50 --spawn-rate=5 --run-time=3m --headless --csv=results/locust-baseline || echo "Locust not installed. Install with: pip install locust"
fi

echo ""
echo "8. Collecting metrics from /metrics endpoint..."
curl -s http://localhost:3000/metrics | jq '.' > "$PROJECT_ROOT/results/baseline/metrics.json" 2>/dev/null || curl -s http://localhost:3000/metrics > "$PROJECT_ROOT/results/baseline/metrics.json"

echo "9. Exporting metrics to CSV..."
curl -s -X POST http://localhost:3000/metrics/export > /dev/null

echo ""
echo "=========================================="
echo "BASELINE TEST - Complete!"
echo "=========================================="
echo "Results saved to:"
echo "  - results/baseline/metrics.json"
echo "  - results/baseline/metrics-*.csv"
echo ""
echo "Press Enter to stop the server..."
read
kill $SERVER_PID 2>/dev/null || true
echo "Server stopped."

