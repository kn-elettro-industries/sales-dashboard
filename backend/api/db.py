import os
import pandas as pd
from sqlalchemy import create_engine, text
import logging

from dotenv import load_dotenv

load_dotenv()

# We can read from environment variables or fallback to the same string used in config.py
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.shpkzdnfcgxzqradrmku:Elettro%40123@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?sslmode=require"
)

try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"}
    )
except Exception as e:
    logging.error(f"Failed to initialize PostgreSQL engine in Backend: {e}")
    engine = None

def get_tenant_data(tenant_id: str = "default_elettro") -> pd.DataFrame:
    """
    Fetches the sales_master data for a specific SaaS tenant.
    """
    if engine is None:
        return pd.DataFrame()
        
    try:
        query = f"SELECT * FROM sales_master WHERE tenant_id = '{tenant_id}'"
        df = pd.read_sql(query, engine)
        
        if "DATE" in df.columns:
            df["DATE"] = pd.to_datetime(df["DATE"], errors='coerce')
            
        return df
    except Exception as e:
        logging.error(f"Error fetching data from DB: {e}")
        return pd.DataFrame()
