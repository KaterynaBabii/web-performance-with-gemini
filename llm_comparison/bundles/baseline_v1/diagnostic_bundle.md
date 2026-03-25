# Diagnostic bundle `baseline_v1` — web-gemini testbed (baseline behavior)

**Stack:** Node.js + Express + PostgreSQL 15 + Redis 7. **Workload:** Locust (search, dashboard, recommendations, checkout).

This bundle describes the **baseline** configuration: missing performance indexes on hot paths, N+1 dashboard queries, no Redis cache on recommendations, ILIKE/sequential patterns on search, loop-based checkout without a single transaction.

---

## 1. Product search — baseline route (`GET /products?search=`)

Issues noted in source: no dedicated FTS index path, `SELECT p.*`, heavy `LIKE`, no pagination.

```javascript
// BASELINE: Slow join, no index, selects all columns, inefficient filtering
const query = `
  SELECT p.*, c.name as category_name, c.parent_id
  FROM products p
  JOIN categories c ON p.category_id = c.id
  WHERE p.name ILIKE $1 OR p.description ILIKE $1
  ORDER BY p.created_at DESC
`;
// Parameter: %search%
```

---

## 2. User dashboard — baseline N+1 (`GET /users/:id/dashboard`)

Separate query per order for `order_items` (classic N+1).

```javascript
const userResult = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);
const ordersResult = await pool.query('SELECT * FROM orders WHERE user_id = $1', [userId]);
for (const order of orders) {
  const itemsResult = await pool.query(
    'SELECT * FROM order_items WHERE order_id = $1',
    [order.id]
  );
}
await pool.query('SELECT * FROM user_preferences WHERE user_id = $1', [userId]);
await pool.query(
  'SELECT * FROM user_activity WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10',
  [userId]
);
```

---

## 3. Recommendations — baseline (`GET /recommendations/:userId`)

No Redis cache; expensive join/aggregate on every request.

```sql
SELECT p.id, p.name, p.price, p.category_id,
       COALESCE(SUM(up.preference_score), 0) as relevance_score,
       COUNT(DISTINCT oi.order_id) as popularity
FROM products p
LEFT JOIN user_preferences up ON p.category_id = up.category_id AND up.user_id = $1
LEFT JOIN order_items oi ON p.id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.id
GROUP BY p.id, p.name, p.price, p.category_id
ORDER BY relevance_score DESC, popularity DESC
LIMIT 20
```

---

## 4. Checkout — baseline (`POST /checkout`)

Per-item `SELECT price` loop; per-item `INSERT`; no explicit transaction wrapping the full flow.

```javascript
for (const item of items) {
  const productResult = await pool.query('SELECT price FROM products WHERE id = $1', [item.productId]);
  total += parseFloat(productResult.rows[0].price) * item.quantity;
}
const orderResult = await pool.query(
  'INSERT INTO orders (user_id, total_amount, status) VALUES ($1, $2, $3) RETURNING id',
  [userId, total, 'pending']
);
for (const item of items) {
  const productResult = await pool.query('SELECT price FROM products WHERE id = $1', [item.productId]);
  await pool.query(
    'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ($1, $2, $3, $4)',
    [orderId, item.productId, item.quantity, productResult.rows[0].price]
  );
}
```

---

## 5. EXPLAIN ANALYZE — **paste real plans here**

> Replace this section with actual `EXPLAIN (ANALYZE, BUFFERS)` from your baseline DB for: (a) product search, (b) dashboard hot query, (c) recommendations query.

---

## 6. pg_stat_statements — **paste top-N summary**

> Replace with CSV or table export from `pg_stat_statements` ordered by `total_exec_time DESC LIMIT 20`.

---

## 7. Slow query log — **paste excerpt**

> Same wall-clock window as a representative Locust steady-state run (e.g. 3 minutes @ 300 users).

---

## 8. Locust workload summary — **paste one run**

Example fields: Aggregated RPS, mean / p95 latency per endpoint, failure count.

> Fill from `locust_*_run*.csv` Aggregated row or `/metrics` JSON after a baseline run.

---

*Bundle version: baseline_v1. Source excerpts: `server/src/routes/products.js`, `dashboard.js`, `recommendations.js`, `checkout.js` (baseline branches).*
