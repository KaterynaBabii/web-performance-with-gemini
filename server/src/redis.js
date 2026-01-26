const redis = require('redis');
require('dotenv').config();

let client = null;

// Only create and connect if Redis cache is enabled
const ENABLE_REDIS_CACHE = process.env.ENABLE_REDIS_CACHE === '1' || process.env.APP_VERSION === 'optimized';
if (ENABLE_REDIS_CACHE) {
  client = redis.createClient({
    socket: {
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
    }
  });

  client.on('error', (err) => console.error('Redis Client Error', err));
  client.on('connect', () => console.log('Redis connected'));

  client.connect().catch((err) => {
    console.error('Failed to connect to Redis:', err);
  });
}

// Helper function to check if Redis is available
function isRedisAvailable() {
  return client !== null && client.isReady; // Check client.isReady for actual connection status
}

module.exports = {
  client,
  isRedisAvailable,
};

