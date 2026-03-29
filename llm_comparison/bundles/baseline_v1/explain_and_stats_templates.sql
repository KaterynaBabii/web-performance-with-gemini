-- Templates for baseline_v1 diagnostic bundle (PostgreSQL 15).
-- Run against a DATABASE THAT MATCHES db/schema.sql AND your seeded data.
-- Replace $1, $2, ... with representative parameters, then capture output into the bundle.

-- =============================================================================
-- 1) Product search (baseline ILIKE pattern from diagnostic_bundle.md)
-- =============================================================================
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT p.*, c.name AS category_name, c.parent_id
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE p.name ILIKE '%laptop%' OR p.description ILIKE '%laptop%'
ORDER BY p.created_at DESC;

-- =============================================================================
-- 2) Dashboard — single order_items lookup (repeat EXPLAIN per order for N+1,
--    or explain the batched equivalent once you rewrite)
-- =============================================================================
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM order_items WHERE order_id = 1;

-- Optional: orders for a user (baseline loads all then loops)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM orders WHERE user_id = 1;

-- =============================================================================
-- 3) Recommendations (baseline SQL from bundle)
-- =============================================================================
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT p.id, p.name, p.price, p.category_id,
       COALESCE(SUM(up.preference_score), 0) AS relevance_score,
       COUNT(DISTINCT oi.order_id) AS popularity
FROM products p
LEFT JOIN user_preferences up ON p.category_id = up.category_id AND up.user_id = 1
LEFT JOIN order_items oi ON p.id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.id
GROUP BY p.id, p.name, p.price, p.category_id
ORDER BY relevance_score DESC, popularity DESC
LIMIT 20;

-- =============================================================================
-- 4) Checkout — product price lookup (baseline does per-id SELECT)
-- =============================================================================
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT price FROM products WHERE id = 1;

-- =============================================================================
-- pg_stat_statements: enable once, reset before steady-state window, export after
-- =============================================================================
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- SELECT pg_stat_statements_reset();

-- After load test (same window as slow-query log):
SELECT
  calls,
  round(total_exec_time::numeric, 2) AS total_ms,
  round(mean_exec_time::numeric, 2) AS mean_ms,
  rows,
  left(query, 120) AS query_prefix
FROM pg_stat_statements
WHERE query NOT ILIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;

-- =============================================================================
-- Slow query log (postgresql.conf) — excerpt belongs in bundle §7, not here
-- log_min_duration_statement = 100  -- example: log queries >= 100ms
-- =============================================================================
