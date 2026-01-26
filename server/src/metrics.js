const fs = require('fs');
const path = require('path');

// Metrics collection
const metrics = {
  requests: [],
  dbQueries: [],
  cacheHits: 0,
  cacheMisses: 0,
};

// Ensure results directory exists
const resultsDir = path.join(__dirname, '..', '..', 'results');
if (!fs.existsSync(resultsDir)) {
  fs.mkdirSync(resultsDir, { recursive: true });
}

function recordRequest(req, res, duration) {
  metrics.requests.push({
    method: req.method,
    path: req.path,
    duration,
    timestamp: Date.now(),
    statusCode: res.statusCode,
  });
}

function recordDbQuery(query, duration) {
  metrics.dbQueries.push({
    query: query.substring(0, 100), // Truncate for storage
    duration,
    timestamp: Date.now(),
  });
}

function recordCacheHit() {
  metrics.cacheHits++;
}

function recordCacheMiss() {
  metrics.cacheMisses++;
}

// Calculate percentile
function percentile(arr, p) {
  if (arr.length === 0) return 0;
  const idx = Math.ceil(p * arr.length) - 1;
  return arr[Math.min(idx, arr.length - 1)];
}

function calculateStats() {
  // Return zeros when no metrics collected yet
  if (metrics.requests.length === 0) {
    return {
      requestCount: 0,
      errorCount: 0,
      avgLatency: 0,
      p95Latency: 0,
      throughput: 0,
      avgDbTime: 0,
      cacheHitRatio: 0,
    };
  }

  const durations = metrics.requests.map(r => r.duration);
  durations.sort((a, b) => a - b);

  const avgLatency = durations.reduce((a, b) => a + b, 0) / durations.length;
  const p95Latency = percentile(durations, 0.95);

  const dbDurations = metrics.dbQueries.map(q => q.duration);
  const avgDbTime = dbDurations.length > 0
    ? dbDurations.reduce((a, b) => a + b, 0) / dbDurations.length
    : 0;

  const totalCacheOps = metrics.cacheHits + metrics.cacheMisses;
  const cacheHitRatio = totalCacheOps > 0
    ? (metrics.cacheHits / totalCacheOps) * 100
    : 0;

  // Calculate throughput (requests per second)
  let throughput = 0;
  if (metrics.requests.length >= 2) {
    const timeSpan = (metrics.requests[metrics.requests.length - 1].timestamp - metrics.requests[0].timestamp) / 1000;
    throughput = timeSpan > 0 ? metrics.requests.length / timeSpan : 0;
  }

  // Count errors (4xx and 5xx responses)
  const errorCount = metrics.requests.filter(r => r.statusCode >= 400).length;

  return {
    requestCount: metrics.requests.length,
    errorCount: errorCount,
    avgLatency: Math.round(avgLatency * 100) / 100,
    p95Latency: Math.round(p95Latency * 100) / 100,
    throughput: Math.round(throughput * 100) / 100,
    avgDbTime: Math.round(avgDbTime * 100) / 100,
    cacheHitRatio: Math.round(cacheHitRatio * 100) / 100,
  };
}

function exportToCSV() {
  const stats = calculateStats();
  if (!stats) {
    console.log('No metrics to export');
    return;
  }

  const version = process.env.APP_VERSION || 'baseline';
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const resultsSubdir = version === 'optimized' ? 'gemini' : 'baseline';
  const filename = `results/${resultsSubdir}/metrics-${version}-${timestamp}.csv`;

  // Ensure subdirectory exists
  const subdir = path.join(resultsDir, resultsSubdir);
  if (!fs.existsSync(subdir)) {
    fs.mkdirSync(subdir, { recursive: true });
  }

  // Write summary stats
  const csvContent = `Metric,Value
Avg Latency (ms),${stats.avgLatency}
P95 Latency (ms),${stats.p95Latency}
Throughput (req/s),${stats.throughput}
Avg DB Query Time (ms),${stats.avgDbTime}
Cache Hit Ratio (%),${stats.cacheHitRatio}
`;

  fs.writeFileSync(filename, csvContent);
  console.log(`Metrics exported to ${filename}`);

  // Also write detailed request log
  const requestsFile = `results/${resultsSubdir}/requests-${version}-${timestamp}.csv`;
  const requestsCSV = 'timestamp,method,path,duration\n' +
    metrics.requests.map(r => `${r.timestamp},${r.method},${r.path},${r.duration}`).join('\n');
  fs.writeFileSync(requestsFile, requestsCSV);

  return filename;
}

// Middleware to track requests
function metricsMiddleware(req, res, next) {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    recordRequest(req, res, duration);
  });

  next();
}

// Export metrics on process exit
process.on('SIGINT', () => {
  exportToCSV();
  process.exit(0);
});

process.on('SIGTERM', () => {
  exportToCSV();
  process.exit(0);
});

module.exports = {
  metricsMiddleware,
  recordDbQuery,
  recordCacheHit,
  recordCacheMiss,
  calculateStats,
  exportToCSV,
};

