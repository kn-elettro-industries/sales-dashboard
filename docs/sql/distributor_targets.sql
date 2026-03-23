-- Monthly distributor (customer) targets for vs-actual reporting.
-- Created automatically by the API; optional manual run.

CREATE TABLE IF NOT EXISTS distributor_targets (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    customer_name VARCHAR(512) NOT NULL,
    year_month VARCHAR(7) NOT NULL,
    target_revenue NUMERIC(20, 2) NOT NULL,
    allocation_pct_snapshot NUMERIC(8, 4),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, customer_name, year_month)
);
