-- Sales targets for Executive Summary KPIs (per tenant). Created automatically by the API on first use.
-- Optional: run manually if you prefer to provision ahead of time.

CREATE TABLE IF NOT EXISTS tenant_sales_targets (
    tenant_id VARCHAR(128) PRIMARY KEY,
    target_revenue NUMERIC(20, 2),
    target_orders INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
