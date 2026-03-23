import os
import pandas as pd
from sqlalchemy import create_engine, text
import logging
from typing import Optional
from cachetools import TTLCache, cached

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    logging.warning("DATABASE_URL is not set. The backend will not be able to connect to the database.")

def _clean_db_url(url: str) -> str:
    """Strip parameters unsupported by psycopg2 (e.g. channel_binding) from the URL."""
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("channel_binding", None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return url

_engine = None

def get_engine():
    """Lazy engine creation so app starts even if DB is slow/unreachable at boot (e.g. Render)."""
    global _engine
    if _engine is not None:
        return _engine
    if not DATABASE_URL:
        logging.error("DATABASE_URL is not set — cannot create engine.")
        return None
    try:
        clean_url = _clean_db_url(DATABASE_URL)
        _engine = create_engine(
            clean_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            connect_args={"sslmode": "require"}
        )
        return _engine
    except Exception as e:
        logging.error(f"Failed to initialize PostgreSQL engine in Backend: {e}")
        return None

def _tenant_cache_from_env() -> TTLCache:
    """In-memory cache for full tenant DataFrames. Tunable via env to reduce DB egress or support more tenants."""
    try:
        maxsize = int(os.environ.get("TENANT_CACHE_MAXSIZE", "10"))
    except ValueError:
        maxsize = 10
    try:
        ttl = int(os.environ.get("TENANT_CACHE_TTL_SECONDS", str(4 * 3600)))
    except ValueError:
        ttl = 4 * 3600
    return TTLCache(maxsize=max(1, maxsize), ttl=max(60, ttl))


# Default: 10 tenants, 4h TTL — see docs/OPTIMIZATION.md
tenant_cache = _tenant_cache_from_env()


def invalidate_tenant_cache(tenant_id: str) -> None:
    """Call after upload so the next dashboard/API request gets fresh data from DB."""
    try:
        key = (tenant_id,)
        if key in tenant_cache:
            del tenant_cache[key]
    except Exception:
        pass


# ─── AUTH USERS ────────────────────────────────────────────────────────────
def _ensure_auth_users_table(conn):
    """Create auth_users table if it does not exist."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS auth_users (
            username VARCHAR(128) PRIMARY KEY,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(32) DEFAULT 'viewer',
            tenant VARCHAR(128) DEFAULT 'default_elettro',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()


def create_user(username: str, password: str, role: str = "viewer", tenant: str = "default_elettro") -> Optional[str]:
    """
    Create a new user. Returns error message on failure, None on success.
    """
    if not username or not password:
        return "Username and password are required."
    username = username.strip().lower()
    if len(username) < 2:
        return "Username must be at least 2 characters."
    if len(password) < 6:
        return "Password must be at least 6 characters."
    eng = get_engine()
    if eng is None:
        return "Database unavailable."
    try:
        import bcrypt
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        with eng.connect() as conn:
            _ensure_auth_users_table(conn)
            conn.execute(
                text("INSERT INTO auth_users (username, password_hash, role, tenant) VALUES (:u, :h, :r, :t)"),
                {"u": username, "h": pw_hash, "r": role, "t": tenant}
            )
            conn.commit()
        return None
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg or "already exists" in msg:
            return "Username already taken."
        logging.error(f"create_user: {e}")
        return "Sign up failed. Please try again."


def verify_user(username: str, password: str):
    """
    Verify credentials. Returns dict with user, role, tenant on success, None on failure.
    """
    if not username or not password:
        return None
    username = username.strip().lower()
    eng = get_engine()
    if eng is None:
        return None
    try:
        import bcrypt
        with eng.connect() as conn:
            _ensure_auth_users_table(conn)
            row = conn.execute(
                text("SELECT username, password_hash, role, tenant FROM auth_users WHERE username = :u"),
                {"u": username}
            ).fetchone()
        if not row:
            return None
        _, pw_hash, role, tenant = row
        if bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8")):
            return {"user": username, "role": role or "viewer", "tenant": tenant or "default_elettro"}
        return None
    except Exception as e:
        logging.error(f"verify_user: {e}")
        return None


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


def _tenant_query_date_filter() -> str:
    """Limit rows fetched from DB to reduce RAM. Set EGRESS_MAX_YEARS=3 in env to enable. Default=0 (load all)."""
    try:
        years = int(os.environ.get("EGRESS_MAX_YEARS", "0"))
        if years <= 0:
            return ""
        # Column is often lowercase 'date' in Postgres when created via pandas to_sql
        return f" AND date >= (CURRENT_DATE - INTERVAL '{years} years')"
    except Exception:
        return ""


@cached(cache=tenant_cache)
def get_cached_tenant_df(tenant_id: str) -> pd.DataFrame:
    """Internal cached helper to fetch full tenant dataset from DB. Enriches FINANCIAL_YEAR and MONTH from DATE when missing."""
    eng = get_engine()
    if eng is None:
        return pd.DataFrame()
    try:
        date_filter = _tenant_query_date_filter()
        query = text(f"SELECT * FROM sales_master WHERE tenant_id = :tid{date_filter}")
        df = pd.read_sql(query, eng, params={"tid": tenant_id})
        if df.empty:
            return df
        try:
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
        except Exception as e:
            logging.warning("get_cached_tenant_df: enrich/coerce failed, returning raw df: %s", e)
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


def clear_tenant_data(tenant_id: str = "default_elettro") -> int:
    """Delete all rows for a tenant so data can be re-uploaded with enrichment (e.g. after adding customer master)."""
    eng = get_engine()
    if eng is None:
        return 0
    try:
        with eng.connect() as conn:
            result = conn.execute(text("DELETE FROM sales_master WHERE tenant_id = :tid"), {"tid": tenant_id})
            conn.commit()
            invalidate_tenant_cache(tenant_id)
            return result.rowcount
    except Exception as e:
        logging.error(f"clear_tenant_data: {e}")
        return 0


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

            if new_records_count > 0:
                invalidate_tenant_cache(tenant_id)
            return new_records_count
    except Exception as e:
        logging.error(f"Failed to update Postgres database: {e}")
        return 0


# ─── SALES TARGETS (per tenant, dashboard KPI vs target) ────────────────────

def _ensure_sales_targets_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_sales_targets (
            tenant_id VARCHAR(128) PRIMARY KEY,
            target_revenue NUMERIC(20, 2),
            target_orders INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()


def get_sales_targets(tenant_id: str) -> dict:
    """Return {revenue: float|None, orders: int|None} for the tenant."""
    eng = get_engine()
    if eng is None:
        return {"revenue": None, "orders": None}
    try:
        with eng.connect() as conn:
            _ensure_sales_targets_table(conn)
            row = conn.execute(
                text("SELECT target_revenue, target_orders FROM tenant_sales_targets WHERE tenant_id = :t"),
                {"t": tenant_id},
            ).fetchone()
        if not row:
            return {"revenue": None, "orders": None}
        rev, ord_ = row[0], row[1]
        return {
            "revenue": float(rev) if rev is not None else None,
            "orders": int(ord_) if ord_ is not None else None,
        }
    except Exception as e:
        logging.error("get_sales_targets: %s", e)
        return {"revenue": None, "orders": None}


def set_sales_targets(tenant_id: str, target_revenue: Optional[float], target_orders: Optional[int]) -> bool:
    """Upsert sales targets for tenant. None clears that field."""
    eng = get_engine()
    if eng is None:
        return False
    try:
        with eng.connect() as conn:
            _ensure_sales_targets_table(conn)
            conn.execute(
                text("""
                    INSERT INTO tenant_sales_targets (tenant_id, target_revenue, target_orders, updated_at)
                    VALUES (:tid, :rev, :ord, CURRENT_TIMESTAMP)
                    ON CONFLICT (tenant_id) DO UPDATE SET
                        target_revenue = EXCLUDED.target_revenue,
                        target_orders = EXCLUDED.target_orders,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {"tid": tenant_id, "rev": target_revenue, "ord": target_orders},
            )
            conn.commit()
        return True
    except Exception as e:
        logging.error("set_sales_targets: %s", e)
        return False


# ─── DISTRIBUTOR (CUSTOMER) MONTHLY TARGETS ─────────────────────────────────

def _ensure_distributor_targets_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS distributor_targets (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(128) NOT NULL,
            customer_name VARCHAR(512) NOT NULL,
            year_month VARCHAR(7) NOT NULL,
            target_revenue NUMERIC(20, 2) NOT NULL,
            allocation_pct_snapshot NUMERIC(8, 4),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tenant_id, customer_name, year_month)
        )
    """))
    conn.commit()


def get_distributor_target(tenant_id: str, customer_name: str, year_month: str) -> Optional[float]:
    """Single monthly ₹ target for a distributor, or None."""
    eng = get_engine()
    if eng is None or not customer_name or not year_month:
        return None
    try:
        with eng.connect() as conn:
            _ensure_distributor_targets_table(conn)
            row = conn.execute(
                text("""
                    SELECT target_revenue FROM distributor_targets
                    WHERE tenant_id = :tid AND customer_name = :c AND year_month = :ym
                """),
                {"tid": tenant_id, "c": customer_name.strip(), "ym": year_month.strip()},
            ).fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0])
    except Exception as e:
        logging.error("get_distributor_target: %s", e)
        return None


def list_distributor_targets(tenant_id: str, year_month: Optional[str] = None) -> list:
    """All distributor rows for tenant, optionally filtered by YYYY-MM."""
    eng = get_engine()
    if eng is None:
        return []
    try:
        with eng.connect() as conn:
            _ensure_distributor_targets_table(conn)
            if year_month:
                rows = conn.execute(
                    text("""
                        SELECT customer_name, year_month, target_revenue, allocation_pct_snapshot
                        FROM distributor_targets WHERE tenant_id = :t AND year_month = :ym
                        ORDER BY customer_name
                    """),
                    {"t": tenant_id, "ym": year_month},
                ).fetchall()
            else:
                rows = conn.execute(
                    text("""
                        SELECT customer_name, year_month, target_revenue, allocation_pct_snapshot
                        FROM distributor_targets WHERE tenant_id = :t
                        ORDER BY year_month DESC, customer_name
                    """),
                    {"t": tenant_id},
                ).fetchall()
        return [
            {
                "customer_name": r[0],
                "year_month": r[1],
                "target_revenue": float(r[2]) if r[2] is not None else None,
                "allocation_pct_snapshot": float(r[3]) if r[3] is not None else None,
            }
            for r in rows
        ]
    except Exception as e:
        logging.error("list_distributor_targets: %s", e)
        return []


def upsert_distributor_target(
    tenant_id: str,
    customer_name: str,
    year_month: str,
    target_revenue: float,
    allocation_pct_snapshot: Optional[float] = None,
) -> bool:
    eng = get_engine()
    if eng is None:
        return False
    try:
        with eng.connect() as conn:
            _ensure_distributor_targets_table(conn)
            conn.execute(
                text("""
                    INSERT INTO distributor_targets
                        (tenant_id, customer_name, year_month, target_revenue, allocation_pct_snapshot, updated_at)
                    VALUES (:tid, :c, :ym, :rev, :pct, CURRENT_TIMESTAMP)
                    ON CONFLICT (tenant_id, customer_name, year_month) DO UPDATE SET
                        target_revenue = EXCLUDED.target_revenue,
                        allocation_pct_snapshot = EXCLUDED.allocation_pct_snapshot,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {"tid": tenant_id, "c": customer_name.strip(), "ym": year_month.strip(), "rev": target_revenue, "pct": allocation_pct_snapshot},
            )
            conn.commit()
        return True
    except Exception as e:
        logging.error("upsert_distributor_target: %s", e)
        return False

