const express = require('express');
const router = express.Router();
const pool = require('../db');
const { recordDbQuery } = require('../metrics');

const ENABLE_BATCH_DASHBOARD = process.env.ENABLE_BATCH_DASHBOARD === '1' || process.env.APP_VERSION === 'optimized';

// GET /users/:id/dashboard
if (ENABLE_BATCH_DASHBOARD) {
  // OPTIMIZED: Single query with JOINs, batch loading
  router.get('/users/:id/dashboard', async (req, res) => {
    const userId = parseInt(req.params.id);
    
    try {
      // OPTIMIZATION: Single query with JOINs instead of N+1
      const query = `
        SELECT 
          u.id as user_id,
          u.email,
          u.name,
          u.created_at as user_created_at,
          o.id as order_id,
          o.total_amount,
          o.status as order_status,
          o.created_at as order_created_at,
          oi.id as item_id,
          oi.product_id,
          oi.quantity,
          oi.price as item_price,
          up.category_id as pref_category_id,
          up.preference_score,
          ua.endpoint,
          ua.duration_ms,
          ua.created_at as activity_created_at
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN user_preferences up ON u.id = up.user_id
        LEFT JOIN (
          SELECT user_id, endpoint, duration_ms, created_at,
                 ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
          FROM user_activity
        ) ua ON u.id = ua.user_id AND ua.rn <= 10
        WHERE u.id = $1
        ORDER BY o.created_at DESC, ua.created_at DESC
      `;
      
      const dbStart = Date.now();
      const result = await pool.query(query, [userId]);
      const dbDuration = Date.now() - dbStart;
      recordDbQuery(query, dbDuration);
      
      if (result.rows.length === 0) {
        return res.status(404).json({ error: 'User not found' });
      }
      
      // Transform flat result into nested structure
      const user = {
        id: result.rows[0].user_id,
        email: result.rows[0].email,
        name: result.rows[0].name,
        created_at: result.rows[0].user_created_at
      };
      
      const ordersMap = new Map();
      const preferences = [];
      const activities = [];
      const seenActivities = new Set();
      
      for (const row of result.rows) {
        // Build orders
        if (row.order_id && !ordersMap.has(row.order_id)) {
          ordersMap.set(row.order_id, {
            id: row.order_id,
            total_amount: row.total_amount,
            status: row.order_status,
            created_at: row.order_created_at,
            items: []
          });
        }
        
        if (row.order_id && row.item_id) {
          const order = ordersMap.get(row.order_id);
          order.items.push({
            id: row.item_id,
            product_id: row.product_id,
            quantity: row.quantity,
            price: row.item_price
          });
        }
        
        // Build preferences
        if (row.pref_category_id) {
          const pref = preferences.find(p => p.category_id === row.pref_category_id);
          if (!pref) {
            preferences.push({
              category_id: row.pref_category_id,
              preference_score: row.preference_score
            });
          }
        }
        
        // Build activities
        if (row.endpoint && !seenActivities.has(`${row.endpoint}-${row.activity_created_at}`)) {
          activities.push({
            endpoint: row.endpoint,
            duration_ms: row.duration_ms,
            created_at: row.activity_created_at
          });
          seenActivities.add(`${row.endpoint}-${row.activity_created_at}`);
        }
      }

      res.json({
        user,
        orders: Array.from(ordersMap.values()),
        preferences,
        recentActivity: activities
      });
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
} else {
  // BASELINE: N+1 query pattern - multiple separate queries
  router.get('/users/:id/dashboard', async (req, res) => {
    const userId = parseInt(req.params.id);
    
    try {
      // N+1 QUERY PATTERN - Each query executed separately
      // Query 1: Get user
      const dbStart1 = Date.now();
      const userResult = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);
      const dbDuration1 = Date.now() - dbStart1;
      recordDbQuery('SELECT * FROM users WHERE id = $1', dbDuration1);
      
      if (userResult.rows.length === 0) {
        return res.status(404).json({ error: 'User not found' });
      }
      
      // Query 2: Get orders
      const dbStart2 = Date.now();
      const ordersResult = await pool.query('SELECT * FROM orders WHERE user_id = $1', [userId]);
      const dbDuration2 = Date.now() - dbStart2;
      recordDbQuery('SELECT * FROM orders WHERE user_id = $1', dbDuration2);
      
      // Query 3-N: Get order items for each order (N+1 problem!)
      const orders = ordersResult.rows;
      const orderItems = [];
      for (const order of orders) {
        const dbStart3 = Date.now();
        const itemsResult = await pool.query(
          'SELECT * FROM order_items WHERE order_id = $1',
          [order.id]
        );
        const dbDuration3 = Date.now() - dbStart3;
        recordDbQuery('SELECT * FROM order_items WHERE order_id = $1', dbDuration3);
        orderItems.push(...itemsResult.rows);
      }
      
      // Query 4: Get preferences
      const dbStart4 = Date.now();
      const prefsResult = await pool.query(
        'SELECT * FROM user_preferences WHERE user_id = $1',
        [userId]
      );
      const dbDuration4 = Date.now() - dbStart4;
      recordDbQuery('SELECT * FROM user_preferences WHERE user_id = $1', dbDuration4);
      
      // Query 5: Get activity
      const dbStart5 = Date.now();
      const activityResult = await pool.query(
        'SELECT * FROM user_activity WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10',
        [userId]
      );
      const dbDuration5 = Date.now() - dbStart5;
      recordDbQuery('SELECT * FROM user_activity WHERE user_id = $1', dbDuration5);

      res.json({
        user: userResult.rows[0],
        orders: orders.map(order => ({
          ...order,
          items: orderItems.filter(item => item.order_id === order.id)
        })),
        preferences: prefsResult.rows,
        recentActivity: activityResult.rows
      });
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
}

module.exports = router;

