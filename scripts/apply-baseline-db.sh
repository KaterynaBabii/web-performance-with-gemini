#!/bin/bash
# Apply baseline database state (drop all indexes)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Applying baseline database state (dropping indexes)..."
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini < "$PROJECT_ROOT/db/indexes_baseline_drop.sql"

echo "✅ Baseline database state applied (no indexes)"

