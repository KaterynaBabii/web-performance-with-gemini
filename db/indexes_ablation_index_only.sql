-- Ablation: index_only and query_opt — only GIN full-text on products + composite (category_id, created_at).
-- Run AFTER db/indexes_baseline_drop.sql so the catalog matches "indexes + baseline code paths".

CREATE INDEX IF NOT EXISTS idx_products_name_search ON products
  USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

CREATE INDEX IF NOT EXISTS idx_products_category_created ON products(category_id, created_at DESC);
