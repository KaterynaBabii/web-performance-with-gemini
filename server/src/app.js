const express = require('express');
const cors = require('cors');
require('dotenv').config();

const { metricsMiddleware, exportToCSV } = require('./metrics');
const productsRouter = require('./routes/products');
const dashboardRouter = require('./routes/dashboard');
const recommendationsRouter = require('./routes/recommendations');
const checkoutRouter = require('./routes/checkout');

const app = express();
const PORT = process.env.PORT || 3000;
const APP_VERSION = process.env.APP_VERSION || 'baseline';

// Middleware
app.use(cors());
app.use(express.json());
app.use(metricsMiddleware);

// Routes
app.use(productsRouter);
app.use(dashboardRouter);
app.use(recommendationsRouter);
app.use(checkoutRouter);

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    version: APP_VERSION,
    timestamp: new Date().toISOString()
  });
});

// Metrics endpoint
app.get('/metrics', (req, res) => {
  const { calculateStats } = require('./metrics');
  const stats = calculateStats();

  // Return expected format plus extra fields for variance/debugging
  res.json({
    // Core paper metrics
    requests: stats.requestCount || 0,
    errors: stats.errorCount || 0,
    avg_ms: stats.avgLatency || 0,
    p95_ms: stats.p95Latency || 0,
    cache_hit_ratio: stats.cacheHitRatio || 0,
    throughput: stats.throughput || 0,
    avg_db_ms: stats.avgDbTime || 0,
    // Instrumentation fields
    cache_hits: stats.cacheHits || 0,
    cache_misses: stats.cacheMisses || 0,
    warmup_started_at: stats.warmupStartedAt || null,
    warmup_completed_at: stats.warmupCompletedAt || null,
    first_request_at: stats.firstRequestAt || null,
    last_request_at: stats.lastRequestAt || null,
  });
});

// Export metrics endpoint
app.post('/metrics/export', (req, res) => {
  const filename = exportToCSV();
  res.json({ message: 'Metrics exported', filename });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Version: ${APP_VERSION}`);
  if (APP_VERSION === 'optimized') {
    console.log('🚀 Running OPTIMIZED version');
  } else {
    console.log('🐌 Running BASELINE version');
  }
});

