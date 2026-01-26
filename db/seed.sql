-- Seed data for Web Gemini Performance Testbed
-- This file is generated - for programmatic seeding, use scripts/seed.js

-- Clear existing data
TRUNCATE TABLE order_items, orders, user_preferences, user_activity, products, categories, users RESTART IDENTITY CASCADE;

-- Insert categories
INSERT INTO categories (name, parent_id) VALUES
  ('Electronics', NULL),
  ('Clothing', NULL),
  ('Books', NULL),
  ('Home & Garden', NULL),
  ('Sports', NULL);

-- Note: For 1000 products and 100 users, use the Node.js seed script
-- This SQL file is a template. Run: node scripts/seed.js
-- Or use the programmatic seeding approach in scripts/seed.js

