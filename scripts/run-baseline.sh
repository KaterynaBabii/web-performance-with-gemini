#!/bin/bash
# Run baseline version for testing

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if port 3000 is in use
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "⚠️  Port 3000 is already in use. Killing existing process..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "Starting baseline version..."
export APP_VERSION=baseline
export ENABLE_REDIS_CACHE=0
export ENABLE_BATCH_DASHBOARD=0
export ENABLE_OPT_SEARCH=0
cd "$PROJECT_ROOT/server" && npm start
