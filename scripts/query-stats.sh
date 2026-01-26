#!/bin/bash
# Query pg_stat_statements for performance analysis
# Useful for IEEE Access reviewers

echo "=== Top 10 Slowest Queries (by total execution time) ==="
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini -c "
SELECT 
    LEFT(query, 100) as query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) as total_ms,
    ROUND(mean_exec_time::numeric, 2) as avg_ms,
    ROUND(max_exec_time::numeric, 2) as max_ms
FROM pg_stat_statements 
ORDER BY total_exec_time DESC 
LIMIT 10;
"

echo ""
echo "=== Query Statistics Summary ==="
docker exec -i web-gemini-postgres psql -U postgres -d web_gemini -c "
SELECT 
    COUNT(*) as total_queries,
    SUM(calls) as total_calls,
    ROUND(SUM(total_exec_time)::numeric, 2) as total_time_ms,
    ROUND(AVG(mean_exec_time)::numeric, 2) as avg_mean_time_ms
FROM pg_stat_statements;
"

