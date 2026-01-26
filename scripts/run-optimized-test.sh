#!/bin/bash
# Run optimized test: apply indexes, start server, run locust, collect metrics

set -e

echo "=========================================="
echo "OPTIMIZED TEST - Starting..."
echo "=========================================="

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Apply database optimizations
echo "1. Applying database optimizations (indexes)..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_optimized.sql"

# Check if port 3000 is in use and kill existing process
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "2. Port 3000 is in use. Killing existing process..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start optimized server in background
echo "3. Starting optimized server..."
echo "   Setting optimized flags: ENABLE_REDIS_CACHE=1, ENABLE_BATCH_DASHBOARD=1, ENABLE_OPT_SEARCH=1"
export APP_VERSION=optimized
export ENABLE_REDIS_CACHE=1
export ENABLE_BATCH_DASHBOARD=1
export ENABLE_OPT_SEARCH=1
cd "$PROJECT_ROOT/server"
npm install 2>/dev/null || true
PORT=3000 APP_VERSION=optimized ENABLE_REDIS_CACHE=1 ENABLE_BATCH_DASHBOARD=1 ENABLE_OPT_SEARCH=1 node src/app.js &
SERVER_PID=$!
cd "$PROJECT_ROOT"

# Wait for server to start
echo "4. Waiting for server to start..."
sleep 5

# Check if server is running
if ! curl -s http://localhost:3000/health > /dev/null; then
    echo "ERROR: Server failed to start"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo "5. Server is running. Starting Locust load test..."
echo "   Run this command in another terminal:"
echo "   cd $PROJECT_ROOT"
echo "   locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=100 --spawn-rate=10 --run-time=3m --headless --csv=results/locust-optimized"
echo ""
echo "   Or run it now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=100 --spawn-rate=10 --run-time=3m --headless --csv=results/locust-optimized || echo "Locust not installed. Install with: pip install locust"
fi

echo ""
echo "6. Collecting metrics from /metrics endpoint..."
curl -s http://localhost:3000/metrics | jq '.' > "$PROJECT_ROOT/results/gemini/metrics.json" 2>/dev/null || curl -s http://localhost:3000/metrics > "$PROJECT_ROOT/results/gemini/metrics.json"

echo "7. Exporting metrics to CSV..."
curl -s -X POST http://localhost:3000/metrics/export > /dev/null

echo ""
echo "=========================================="
echo "OPTIMIZED TEST - Complete!"
echo "=========================================="
echo "Results saved to:"
echo "  - results/gemini/metrics.json"
echo "  - results/gemini/metrics-*.csv"
echo ""
echo "Press Enter to stop the server..."
read
kill $SERVER_PID 2>/dev/null || true
echo "Server stopped."

