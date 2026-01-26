-- Drop all performance indexes to create baseline state
-- This ensures we start with no indexes for baseline testing

DROP INDEX IF EXISTS idx_products_category;
DROP INDEX IF EXISTS idx_products_name_search;
DROP INDEX IF EXISTS idx_products_category_created;
DROP INDEX IF EXISTS idx_orders_user;
DROP INDEX IF EXISTS idx_order_items_order;
DROP INDEX IF EXISTS idx_user_preferences_user;
DROP INDEX IF EXISTS idx_user_activity_user;
DROP INDEX IF EXISTS idx_product_events_user;
DROP INDEX IF EXISTS idx_product_events_product;
DROP INDEX IF EXISTS idx_product_events_type;

