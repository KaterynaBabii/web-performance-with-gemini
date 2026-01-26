const express = require('express');
const router = express.Router();
const pool = require('../db');
const { recordDbQuery } = require('../metrics');
const { client: redis, isRedisAvailable } = require('../redis');

const ENABLE_OPT_SEARCH = process.env.ENABLE_OPT_SEARCH === '1' || process.env.APP_VERSION === 'optimized';

// GET /products?search=...
if (ENABLE_OPT_SEARCH) {
  // OPTIMIZED: Index on category_id, full-text search, select only needed columns, pagination
  router.get('/products', async (req, res) => {
    const search = req.query.search || '';
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const offset = (page - 1) * limit;
    
    try {
      // OPTIMIZATIONS:
      // 1. Use full-text search with GIN index
      // 2. Select only needed columns (not *)
      // 3. Add pagination
      // 4. Use parameterized queries with proper types
      const query = `
        SELECT 
          p.id,
          p.name,
          p.price,
          p.category_id,
          p.stock_quantity,
          c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')) @@ plainto_tsquery('english', $1)
           OR p.name ILIKE $2
        ORDER BY p.created_at DESC
        LIMIT $3 OFFSET $4
      `;
      
      const dbStart = Date.now();
      const result = await pool.query(query, [search, `%${search}%`, limit, offset]);
      const dbDuration = Date.now() - dbStart;
      recordDbQuery(query, dbDuration);
      
      // Get total count for pagination
      const countQuery = `
        SELECT COUNT(*) as total
        FROM products p
        WHERE to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')) @@ plainto_tsquery('english', $1)
           OR p.name ILIKE $2
      `;
      const countResult = await pool.query(countQuery, [search, `%${search}%`]);

      res.json({
        products: result.rows,
        pagination: {
          page,
          limit,
          total: parseInt(countResult.rows[0].total),
          totalPages: Math.ceil(parseInt(countResult.rows[0].total) / limit)
        }
      });
    } catch (error) {
      console.error('Error fetching products:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
} else {
  // BASELINE: Slow join, no index, selects all columns, inefficient filtering
  router.get('/products', async (req, res) => {
    const search = req.query.search || '';
    
    try {
      // BASELINE ISSUES:
      // 1. No index on category_id or name
      // 2. Selecting all columns including large text fields
      // 3. Inefficient LIKE search (no full-text search)
      // 4. No pagination
      const query = `
        SELECT p.*, c.name as category_name, c.parent_id
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.name LIKE $1 OR p.description LIKE $1
        ORDER BY p.created_at DESC
      `;
      
      const dbStart = Date.now();
      const result = await pool.query(query, [`%${search}%`]);
      const dbDuration = Date.now() - dbStart;
      recordDbQuery(query, dbDuration);

      res.json({
        products: result.rows,
        count: result.rows.length
      });
    } catch (error) {
      console.error('Error fetching products:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
}

module.exports = router;

