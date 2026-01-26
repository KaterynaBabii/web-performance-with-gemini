#!/bin/bash
# Run optimized version for testing

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if port 3000 is in use
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "⚠️  Port 3000 is already in use. Killing existing process..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "Applying database optimizations..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_optimized.sql"

echo "Starting optimized version..."
export APP_VERSION=optimized
export ENABLE_REDIS_CACHE=1
export ENABLE_BATCH_DASHBOARD=1
export ENABLE_OPT_SEARCH=1
cd "$PROJECT_ROOT/server" && npm start
