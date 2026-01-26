#!/bin/bash
# Apply optimized database state (add all indexes)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Applying optimized database state (adding indexes)..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_optimized.sql"

echo "✅ Optimized database state applied (all indexes created)"

