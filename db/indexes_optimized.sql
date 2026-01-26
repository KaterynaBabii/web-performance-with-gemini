-- Optimized indexes for Gemini-informed performance improvements
-- Run this after baseline testing to create the optimized version

-- Index for product category joins
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);

-- Full-text search index for product search
CREATE INDEX IF NOT EXISTS idx_products_name_search ON products 
  USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- Index for user orders
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);

-- Index for order items lookups
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

-- Index for user preferences
CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);

-- Index for user activity queries
CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id, created_at DESC);

-- Composite index for product search performance
CREATE INDEX IF NOT EXISTS idx_products_category_created ON products(category_id, created_at DESC);

-- Indexes for product events
CREATE INDEX IF NOT EXISTS idx_product_events_user ON product_events(user_id);
CREATE INDEX IF NOT EXISTS idx_product_events_product ON product_events(product_id);
CREATE INDEX IF NOT EXISTS idx_product_events_type ON product_events(event_type);

