const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_NAME || 'web_gemini',
  max: 50,  // Increased for high concurrent load (250 users)
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,  // Increased timeout for high load
});

module.exports = pool;

