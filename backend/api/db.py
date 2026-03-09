import os
import pandas as pd
from sqlalchemy import create_engine
import logging
from typing import Optional
from cachetools import TTLCache, cached

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.shpkzdnfcgxzqradrmku:Elettro%40123@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?sslmode=require"
)

_engine = None

def get_engine():
    """Lazy engine creation so app starts even if DB is slow/unreachable at boot (e.g. Render)."""
    global _engine
    if _engine is not None:
        return _engine
    try:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            connect_args={"sslmode": "require"}
        )
        return _engine
    except Exception as e:
        logging.error(f"Failed to initialize PostgreSQL engine in Backend: {e}")
        return None

# Cache up to 10 tenants' full DataFrames for 1 hour
tenant_cache = TTLCache(maxsize=10, ttl=3600)

def _fy_from_date(date):
    """Same as routes.calculate_fy: April = start of FY. Used for read-time enrichment."""
    if pd.isna(date):
        return "UNKNOWN"
    try:
        d = pd.to_datetime(date)
        if hasattr(d, "month"):
            y = d.year % 100
            return f"FY{y}-{(d.year + 1) % 100}" if d.month >= 4 else f"FY{y - 1}-{y}"
    except Exception:
        pass
    return "UNKNOWN"


@cached(cache=tenant_cache)
def get_cached_tenant_df(tenant_id: str) -> pd.DataFrame:
    """Internal cached helper to fetch full tenant dataset from DB. Enriches FINANCIAL_YEAR and MONTH from DATE when missing."""
    eng = get_engine()
    if eng is None:
        return pd.DataFrame()
    try:
        query = f"SELECT * FROM sales_master WHERE tenant_id = '{tenant_id}'"
        df = pd.read_sql(query, eng)
        if df.empty:
            return df
        # Coerce AMOUNT to numeric (DB may return string)
        amt_col = next((c for c in df.columns if str(c).upper() == "AMOUNT"), None)
        if amt_col is not None:
            df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)
        date_col = next((c for c in df.columns if str(c).upper() == "DATE"), None)
        if date_col is not None:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            if hasattr(df[date_col].dtype, "tz") and df[date_col].dtype.tz is not None:
                df[date_col] = df[date_col].dt.tz_localize(None)
            if "FINANCIAL_YEAR" not in df.columns:
                df["FINANCIAL_YEAR"] = df[date_col].apply(_fy_from_date)
            if "MONTH" not in df.columns:
                df["MONTH"] = df[date_col].dt.strftime("%b-%y").str.upper()
        return df
    except Exception as e:
        logging.error(f"Error fetching data from DB: {e}")
        return pd.DataFrame()

def get_tenant_data(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches the sales_master data for a specific SaaS tenant, with optional date filtering.
    Leverages in-memory caching to avoid hitting Supabase on every API request.
    Never raises: returns empty DataFrame on any error.
    """
    try:
        raw = get_cached_tenant_df(tenant_id)
        df = raw.copy() if raw is not None and isinstance(raw, pd.DataFrame) else pd.DataFrame()
    except Exception as e:
        logging.error(f"get_tenant_data: %s", e)
        df = pd.DataFrame()

    try:
        if not df.empty and "DATE" in df.columns:
            if start_date:
                start_dt = pd.to_datetime(start_date)
                if getattr(start_dt, "tz", None) is not None:
                    start_dt = start_dt.tz_localize(None)
                df = df[df["DATE"] >= start_dt]
            if end_date:
                end_dt = pd.to_datetime(end_date)
                if getattr(end_dt, "tz", None) is not None:
                    end_dt = end_dt.tz_localize(None)
                # Date-only (e.g. "2025-03-05") → include full end day
                if len(str(end_date).strip()) <= 10:
                    end_dt = end_dt + pd.Timedelta(days=1)
                    df = df[df["DATE"] < end_dt]
                else:
                    df = df[df["DATE"] <= end_dt]
    except Exception as e:
        logging.error(f"get_tenant_data date filter: %s", e)
        df = pd.DataFrame()
    return df

from sqlalchemy import text

def update_database(new_df: pd.DataFrame, tenant_id: str = "default_elettro") -> int:
    """Updates the PostgreSQL database with new records for the specific tenant."""
    if new_df is None or new_df.empty:
        return 0

    eng = get_engine()
    if eng is None:
        logging.error("Database engine not initialized. Cannot update.")
        return 0

    # Inject multi-tenant ID
    new_df["tenant_id"] = tenant_id

    try:
        with eng.connect() as conn:
            # Check if table exists
            has_table = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sales_master')"
            )).scalar()

            new_records_count = 0

            if not has_table:
                # First time creation
                new_df.to_sql("sales_master", eng, if_exists="replace", index=False)
                new_records_count = len(new_df)
                logging.info(f"Created new Postgres table with {new_records_count} records for tenant {tenant_id}.")
            else:
                # Deduplication logic per tenant
                existing_invoices = pd.read_sql(
                    text("SELECT \"INVOICE_NO\" FROM sales_master WHERE tenant_id = :tid"), 
                    conn, params={"tid": tenant_id}
                )
                existing_set = set(existing_invoices["INVOICE_NO"])
                
                if "INVOICE_NO" in new_df.columns:
                    to_insert = new_df[~new_df["INVOICE_NO"].isin(existing_set)]
                else:
                    logging.warning("INVOICE_NO missing in new data. Appending all.")
                    to_insert = new_df

                new_records_count = len(to_insert)

                if new_records_count > 0:
                    to_insert.to_sql("sales_master", eng, if_exists="append", index=False)
                    logging.info(f"Appended {new_records_count} new records to Postgres for tenant {tenant_id}.")
                else:
                    logging.info("No new records to append to Postgres DB.")

            return new_records_count
    except Exception as e:
        logging.error(f"Failed to update Postgres database: {e}")
        return 0

