-- Optional indexes for sales_master (run once on your Postgres / Supabase SQL editor).
-- Improves tenant-scoped reads and date-filtered queries.

-- Primary pattern: WHERE tenant_id = $1
CREATE INDEX IF NOT EXISTS idx_sales_master_tenant_id
  ON sales_master (tenant_id);

-- If you often filter by tenant + date (matches EGRESS_MAX_YEARS and dashboard date ranges)
CREATE INDEX IF NOT EXISTS idx_sales_master_tenant_date
  ON sales_master (tenant_id, date);

-- ANALYZE after bulk loads
-- ANALYZE sales_master;
