const express = require('express');
const router = express.Router();
const pool = require('../db');
const { recordDbQuery } = require('../metrics');
const { client: redis, isRedisAvailable } = require('../redis');

const APP_VERSION = process.env.APP_VERSION || 'baseline';

// POST /checkout
if (APP_VERSION === 'optimized') {
  // OPTIMIZED: Transaction, batch insert, cache invalidation
  router.post('/checkout', async (req, res) => {
    const { userId, items } = req.body;
    
    if (!userId || !items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ error: 'Invalid request' });
    }
    
    const client = await pool.connect();
    
    try {
      await client.query('BEGIN');
      
      // Get all product prices in one query
      const productIds = items.map(item => item.productId);
      const placeholders = productIds.map((_, i) => `$${i + 1}`).join(', ');
      const productsResult = await client.query(
        `SELECT id, price FROM products WHERE id IN (${placeholders})`,
        productIds
      );
      
      const productMap = new Map(productsResult.rows.map(p => [p.id, parseFloat(p.price)]));
      
      // Validate all products exist
      for (const item of items) {
        if (!productMap.has(item.productId)) {
          throw new Error(`Product ${item.productId} not found`);
        }
      }
      
      // Calculate total
      const total = items.reduce((sum, item) => {
        return sum + productMap.get(item.productId) * item.quantity;
      }, 0);
      
      // Create order
      const orderResult = await client.query(
        'INSERT INTO orders (user_id, total_amount, status) VALUES ($1, $2, $3) RETURNING id',
        [userId, total, 'pending']
      );
      const orderId = orderResult.rows[0].id;
      
      // Batch insert order items
      const values = items.map((item, idx) => {
        const base = idx * 4;
        return `($${base + 1}, $${base + 2}, $${base + 3}, $${base + 4})`;
      }).join(', ');
      
      const params = items.flatMap(item => [
        orderId,
        item.productId,
        item.quantity,
        productMap.get(item.productId)
      ]);
      
      await client.query(
        `INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ${values}`,
        params
      );
      
      await client.query('COMMIT');
      
      // Invalidate user's recommendation cache
      if (isRedisAvailable()) {
        await redis.del(`recommendations:${userId}`);
      }
      
      res.json({
        orderId,
        total,
        status: 'pending'
      });
    } catch (error) {
      await client.query('ROLLBACK');
      console.error('Error processing checkout:', error);
      res.status(500).json({ error: 'Internal server error' });
    } finally {
      client.release();
    }
  });
} else {
  // BASELINE: Simple write, but could be optimized with transactions
  router.post('/checkout', async (req, res) => {
    const { userId, items } = req.body;
    
    if (!userId || !items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ error: 'Invalid request' });
    }
    
    try {
      // Calculate total
      let total = 0;
      for (const item of items) {
        const productResult = await pool.query('SELECT price FROM products WHERE id = $1', [item.productId]);
        if (productResult.rows.length === 0) {
          return res.status(400).json({ error: `Product ${item.productId} not found` });
        }
        total += parseFloat(productResult.rows[0].price) * item.quantity;
      }
      
      // Create order
      const orderResult = await pool.query(
        'INSERT INTO orders (user_id, total_amount, status) VALUES ($1, $2, $3) RETURNING id',
        [userId, total, 'pending']
      );
      const orderId = orderResult.rows[0].id;
      
      // Insert order items (could use batch insert)
      for (const item of items) {
        const productResult = await pool.query('SELECT price FROM products WHERE id = $1', [item.productId]);
        await pool.query(
          'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ($1, $2, $3, $4)',
          [orderId, item.productId, item.quantity, productResult.rows[0].price]
        );
      }
      
      res.json({
        orderId,
        total,
        status: 'pending'
      });
    } catch (error) {
      console.error('Error processing checkout:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
}

module.exports = router;

