const express = require('express');
const router = express.Router();
const pool = require('../db');
const { recordDbQuery, recordCacheHit, recordCacheMiss } = require('../metrics');
const { client: redis, isRedisAvailable } = require('../redis');

const ENABLE_REDIS_CACHE = process.env.ENABLE_REDIS_CACHE === '1' || process.env.APP_VERSION === 'optimized';

// GET /recommendations/:userId
if (ENABLE_REDIS_CACHE) {
  // OPTIMIZED: Redis caching with TTL and smart invalidation
  router.get('/recommendations/:userId', async (req, res) => {
    const userId = parseInt(req.params.userId);
    const cacheKey = `recommendations:${userId}`;
    
    try {
      // Check cache first
      if (isRedisAvailable()) {
        const cached = await redis.get(cacheKey);
        if (cached) {
          recordCacheHit();
          return res.json(JSON.parse(cached));
        }
        recordCacheMiss();
      }
      
      // Cache miss - compute recommendations
      const query = `
        SELECT 
          p.id,
          p.name,
          p.price,
          p.category_id,
          COALESCE(SUM(up.preference_score), 0) as relevance_score,
          COUNT(DISTINCT oi.order_id) as popularity
        FROM products p
        LEFT JOIN user_preferences up ON p.category_id = up.category_id AND up.user_id = $1
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id
        GROUP BY p.id, p.name, p.price, p.category_id
        ORDER BY relevance_score DESC, popularity DESC
        LIMIT 20
      `;
      
      const dbStart = Date.now();
      const result = await pool.query(query, [userId]);
      const dbDuration = Date.now() - dbStart;
      recordDbQuery(query, dbDuration);
      
      const recommendations = result.rows.map(product => ({
        ...product,
        score: parseFloat(product.relevance_score) + parseFloat(product.popularity) * 0.1
      }));

      const response = {
        recommendations,
        generatedAt: new Date().toISOString(),
        cached: false
      };
      
      // Cache for 5 minutes (300 seconds)
      if (isRedisAvailable()) {
        await redis.setEx(cacheKey, 300, JSON.stringify(response));
      }

      res.json(response);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
} else {
  // BASELINE: No caching, expensive computation on every request
  router.get('/recommendations/:userId', async (req, res) => {
    const userId = parseInt(req.params.userId);
    
    try {
      // Expensive query: Join multiple tables, complex calculation
      const query = `
        SELECT 
          p.id,
          p.name,
          p.price,
          p.category_id,
          COALESCE(SUM(up.preference_score), 0) as relevance_score,
          COUNT(DISTINCT oi.order_id) as popularity
        FROM products p
        LEFT JOIN user_preferences up ON p.category_id = up.category_id AND up.user_id = $1
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id
        GROUP BY p.id, p.name, p.price, p.category_id
        ORDER BY relevance_score DESC, popularity DESC
        LIMIT 20
      `;
      
      const dbStart = Date.now();
      const result = await pool.query(query, [userId]);
      const dbDuration = Date.now() - dbStart;
      recordDbQuery(query, dbDuration);
      
      // Simulate additional computation
      const recommendations = result.rows.map(product => ({
        ...product,
        score: parseFloat(product.relevance_score) + parseFloat(product.popularity) * 0.1
      }));

      res.json({
        recommendations,
        generatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
}

module.exports = router;

