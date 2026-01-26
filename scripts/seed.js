const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_NAME || 'web_gemini',
});

async function seed() {
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');
    console.log('Starting database seed...');

    // Clear existing data
    await client.query('TRUNCATE TABLE order_items, orders, user_preferences, user_activity, product_events, products, categories, users RESTART IDENTITY CASCADE');

    // Insert categories
    const categoryResult = await client.query(
      'INSERT INTO categories (name, parent_id) VALUES ($1, NULL), ($2, NULL), ($3, NULL), ($4, NULL), ($5, NULL) RETURNING id',
      ['Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports']
    );
    const categories = categoryResult.rows;
    console.log('Categories created');

    // Insert 50k products using batch inserts
    console.log('Creating 50,000 products...');
    const productNames = [
      'Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Keyboard', 'Mouse', 'Monitor',
      'T-Shirt', 'Jeans', 'Jacket', 'Shoes', 'Hat', 'Socks', 'Belt',
      'Novel', 'Textbook', 'Magazine', 'Comic', 'Dictionary', 'Biography',
      'Chair', 'Table', 'Lamp', 'Vase', 'Curtain', 'Pillow', 'Rug',
      'Basketball', 'Football', 'Tennis Racket', 'Yoga Mat', 'Dumbbell', 'Bicycle'
    ];

    const batchSize = 1000;
    for (let batch = 0; batch < 50; batch++) {
      const values = [];
      const params = [];
      let paramIndex = 1;

      for (let i = 0; i < batchSize; i++) {
        const globalIndex = batch * batchSize + i;
        const category = categories[globalIndex % categories.length];
        const name = `${productNames[globalIndex % productNames.length]} ${Math.floor(globalIndex / productNames.length) + 1}`;
        const price = (Math.random() * 900 + 10).toFixed(2);
        const stock = Math.floor(Math.random() * 100);

        values.push(`($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3}, $${paramIndex + 4})`);
        params.push(name, `Description for ${name}.`, price, category.id, stock);
        paramIndex += 5;
      }

      await client.query(
        `INSERT INTO products (name, description, price, category_id, stock_quantity) VALUES ${values.join(', ')}`,
        params
      );
      
      if ((batch + 1) % 10 === 0) {
        console.log(`  Created ${(batch + 1) * batchSize} products...`);
      }
    }
    console.log('Products created: 50,000');

    // Insert 200k users using batch inserts
    console.log('Creating 200,000 users...');
    const userBatchSize = 5000;
    for (let batch = 0; batch < 40; batch++) {
      const values = [];
      const params = [];
      let paramIndex = 1;

      for (let i = 0; i < userBatchSize; i++) {
        const globalIndex = batch * userBatchSize + i;
        values.push(`($${paramIndex}, $${paramIndex + 1})`);
        params.push(`user${globalIndex}@example.com`, `User ${globalIndex}`);
        paramIndex += 2;
      }

      await client.query(
        `INSERT INTO users (email, name) VALUES ${values.join(', ')}`,
        params
      );
      
      if ((batch + 1) % 10 === 0) {
        console.log(`  Created ${(batch + 1) * userBatchSize} users...`);
      }
    }
    console.log('Users created: 200,000');

    // Get all user IDs for orders and events
    const userResult = await client.query('SELECT id FROM users ORDER BY id');
    const userIds = userResult.rows.map(r => r.id);
    const productResult = await client.query('SELECT id FROM products ORDER BY id');
    const productIds = productResult.rows.map(r => r.id);

    // Insert 400k orders
    console.log('Creating 400,000 orders...');
    const orderBatchSize = 1000;
    for (let batch = 0; batch < 400; batch++) {
      const values = [];
      const params = [];
      let paramIndex = 1;

      for (let i = 0; i < orderBatchSize; i++) {
        const userId = userIds[Math.floor(Math.random() * userIds.length)];
        const total = (Math.random() * 500 + 10).toFixed(2);
        const status = Math.random() > 0.3 ? 'completed' : 'pending';
        values.push(`($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2})`);
        params.push(userId, total, status);
        paramIndex += 3;
      }

      await client.query(
        `INSERT INTO orders (user_id, total_amount, status) VALUES ${values.join(', ')}`,
        params
      );
      
      if ((batch + 1) % 50 === 0) {
        console.log(`  Created ${(batch + 1) * orderBatchSize} orders...`);
      }
    }
    console.log('Orders created: 400,000');

    // Get order IDs for order_items
    const orderResult = await client.query('SELECT id FROM orders ORDER BY id');
    const orderIds = orderResult.rows.map(r => r.id);

    // Insert order_items (2-5 items per order)
    console.log('Creating order items...');
    const itemBatchSize = 5000;
    let itemCount = 0;
    let currentBatch = [];
    let currentParams = [];
    let paramIndex = 1;

    for (const orderId of orderIds) {
      const itemCountForOrder = Math.floor(Math.random() * 4) + 2;
      
      for (let j = 0; j < itemCountForOrder; j++) {
        const productId = productIds[Math.floor(Math.random() * productIds.length)];
        const quantity = Math.floor(Math.random() * 3) + 1;
        const price = (Math.random() * 100 + 10).toFixed(2);
        currentBatch.push(`($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3})`);
        currentParams.push(orderId, productId, quantity, price);
        paramIndex += 4;
        itemCount++;

        // Insert in batches
        if (currentBatch.length >= itemBatchSize) {
          await client.query(
            `INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ${currentBatch.join(', ')}`,
            currentParams
          );
          currentBatch = [];
          currentParams = [];
          paramIndex = 1;
        }
      }

      if (itemCount % 50000 === 0) {
        console.log(`  Created ${itemCount} order items...`);
      }
    }

    // Insert remaining items
    if (currentBatch.length > 0) {
      await client.query(
        `INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ${currentBatch.join(', ')}`,
        currentParams
      );
    }
    console.log(`Order items created: ~${itemCount}`);

    // Insert 2M product_events
    console.log('Creating 2,000,000 product events...');
    const eventTypes = ['view', 'click', 'purchase', 'add_to_cart'];
    const eventBatchSize = 10000;
    for (let batch = 0; batch < 200; batch++) {
      const values = [];
      const params = [];
      let paramIndex = 1;

      for (let i = 0; i < eventBatchSize; i++) {
        const userId = userIds[Math.floor(Math.random() * userIds.length)];
        const productId = productIds[Math.floor(Math.random() * productIds.length)];
        const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
        values.push(`($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2})`);
        params.push(userId, productId, eventType);
        paramIndex += 3;
      }

      await client.query(
        `INSERT INTO product_events (user_id, product_id, event_type) VALUES ${values.join(', ')}`,
        params
      );
      
      if ((batch + 1) % 20 === 0) {
        console.log(`  Created ${(batch + 1) * eventBatchSize} events...`);
      }
    }
    console.log('Product events created: 2,000,000');

    // Insert user preferences (3 per user)
    console.log('Creating user preferences...');
    const prefBatchSize = 5000;
    let prefCount = 0;
    for (let i = 0; i < userIds.length; i += prefBatchSize) {
      const batch = userIds.slice(i, i + prefBatchSize);
      const values = [];
      const params = [];
      let paramIndex = 1;

      for (const userId of batch) {
        for (let j = 0; j < 3; j++) {
          const category = categories[Math.floor(Math.random() * categories.length)];
          values.push(`($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2})`);
          params.push(userId, category.id, (Math.random() * 0.5 + 0.5).toFixed(2));
          paramIndex += 3;
          prefCount++;
        }
      }

      await client.query(
        `INSERT INTO user_preferences (user_id, category_id, preference_score) VALUES ${values.join(', ')}`,
        params
      );
      
      if (prefCount % 50000 === 0) {
        console.log(`  Created ${prefCount} preferences...`);
      }
    }
    console.log(`User preferences created: ${prefCount}`);

    await client.query('COMMIT');
    
    console.log('\n✅ Database seeded successfully!');
    console.log('Summary:');
    console.log(`  - 200,000 users`);
    console.log(`  - 50,000 products`);
    console.log(`  - 400,000 orders`);
    console.log(`  - ~${itemCount} order items`);
    console.log(`  - 2,000,000 product events`);
    console.log(`  - ${prefCount} user preferences`);
    
  } catch (error) {
    await client.query('ROLLBACK');
    console.error('Error seeding database:', error);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

seed();
