import pandas as pd
from sqlalchemy import create_engine, text
import logging

import config

# Create global SQLAlchemy engine
# Set pool settings for SaaS concurrency
try:
    engine = create_engine(
        config.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"}  # Required for Supabase cloud
    )
except Exception as e:
    logging.error(f"Failed to initialize PostgreSQL engine: {e}")
    engine = None

def load_data(tenant_id="default_elettro"):
    """
    Loads data for a specific tenant from PostgreSQL.
    """
    if engine is None:
        return pd.DataFrame()
        
    try:
        # Check if table exists
        with engine.connect() as conn:
            # We use text() to execute raw SQL safely
            has_table = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sales_master')"
            )).scalar()
            
            if not has_table:
                return pd.DataFrame()

        # Query data for specific tenant
        query = f"SELECT * FROM sales_master WHERE tenant_id = '{tenant_id}'"
        df = pd.read_sql(query, engine)
        
        if "DATE" in df.columns:
            df["DATE"] = pd.to_datetime(df["DATE"], errors='coerce')
            
        return df
    except Exception as e:
        logging.error(f"Error loading tenant data from Postgres: {e}")
        return pd.DataFrame()

def clear_tenant_data(tenant_id="default_elettro"):
    """
    Safely deletes only the records belonging to the multi-tenant ID.
    (Leaves other SaaS customers' data intact).
    """
    if engine is None:
        return
        
    try:
        with engine.begin() as conn: 
            # Check table exists before dropping
            has_table = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sales_master')"
            )).scalar()
            
            if has_table:
                del_query = text("DELETE FROM sales_master WHERE tenant_id = :tid")
                conn.execute(del_query, {"tid": tenant_id})
    except Exception as e:
        logging.error(f"Error clearing multi-tenant Postgres data: {e}")
