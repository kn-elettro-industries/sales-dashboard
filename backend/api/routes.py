from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Response, Request
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import pandas as pd
import json
import io
import os
from datetime import datetime, timedelta

import calendar

from .db import (
    get_tenant_data,
    create_user,
    verify_user,
    get_sales_targets,
    set_sales_targets,
    get_distributor_target,
    list_distributor_targets,
    upsert_distributor_target,
)
from .customer_geo_overrides import apply_customer_geo_overrides, apply_customer_name_canonical

router = APIRouter()

# Download filenames (PDF/CSV) — was ELETTRO_; use brand-aligned prefix.
REPORT_FILE_PREFIX = "KN_Elettro_Intelligence"

# Keyword-based exclusion: row excluded if material group CONTAINS any of these (case-insensitive).
# Kept in sync with legacy/config.py EXCLUDE_KEYWORDS.
EXCLUDE_KEYWORDS = [
    "SERVICE", "AIR VENT", "PACKING", "RAW", "BRASS", "PANEL",
    "SALES ACCOUNT", "MASTER BATCH", "SEMI", "PPCP", "FIXED",
    "PROTECTION", "HIPS", "ABS", "INDIRECT", "NYLOAN", "PP BLACK",
    "NASER MILES PARIS", "DOCUMENT HOLDER",
    "SWISS MILITARY MODLE MAZE",
    "SELF ADHESIVE TIE MOUNT", "SCREW TYPE TIE MOUNT",
    "FINISHED GOOD",
]

# Rename mappings: regex pattern → standardized name (applied before exclusion)
MATERIAL_GROUP_MAPPINGS = {
    r"CONDUIT.*GLAND": "POLYAMIDE CONDUIT GLAND",
    r"REVER": "REVERSE FORWARD",
    r"REVERSE FORWORD": "REVERSE FORWARD",
}


# ─── AUTH (real: users stored in auth_users table) ───

class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class SignupRequest(BaseModel):
    username: str = ""
    password: str = ""
    confirm_password: str = ""


@router.get("/auth/signup-enabled")
def auth_signup_enabled():
    """Returns whether public signup is allowed. When false, only admin can create accounts."""
    enabled = os.environ.get("SIGNUP_ENABLED", "false").strip().lower() in ("true", "1", "yes")
    return {"enabled": enabled}


def _create_token(user: str, role: str, tenant: str) -> str:
    """Create a short-lived JWT for the logged-in user."""
    import jwt
    from datetime import datetime, timedelta, timezone
    secret = os.environ.get("JWT_SECRET", "elettro-dev-secret-change-in-production")
    payload = {
        "user": user,
        "role": role,
        "tenant": tenant,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _verify_token(token: str):
    """Verify JWT and return payload or None."""
    import jwt
    try:
        secret = os.environ.get("JWT_SECRET", "elettro-dev-secret-change-in-production")
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None


@router.post("/auth/login")
def auth_login(req: LoginRequest):
    """Verify credentials against auth_users table. Returns user + token for Add user."""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    user = verify_user(req.username.strip(), req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _create_token(user["user"], user.get("role", "viewer"), user.get("tenant", "default_elettro"))
    return {**user, "token": token}


@router.post("/auth/signup")
def auth_signup(req: SignupRequest):
    """Create a new user account. Disabled when SIGNUP_ENABLED is not 'true' — only admin can add users via seed script."""
    if not os.environ.get("SIGNUP_ENABLED", "false").strip().lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="Sign up is disabled. Contact your administrator for access.")
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    err = create_user(req.username, req.password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    # Auto-return user for immediate login
    user = verify_user(req.username.strip(), req.password)
    token = _create_token(user["user"], user.get("role", "viewer"), user.get("tenant", "default_elettro"))
    return {**user, "token": token}


@router.get("/auth/me")
def auth_me():
    """Placeholder: in production validate session/JWT and return current user."""
    return {"user": None, "role": None}


class CreateUserRequest(BaseModel):
    username: str = ""
    password: str = ""


class SalesTargetsPut(BaseModel):
    """Persisted sales targets for dashboard KPI progress (same tenant as sales_master)."""
    tenant_id: str = "default_elettro"
    target_revenue: Optional[float] = None  # absolute ₹ amount
    target_orders: Optional[int] = None


class DistributorTargetPut(BaseModel):
    """Monthly distributor (customer) target. Use % of company goal OR explicit ₹."""
    tenant_id: str = "default_elettro"
    customer_name: str = ""
    year_month: str = ""  # YYYY-MM
    target_revenue: Optional[float] = None
    # If set (e.g. 30), target_revenue = company revenue goal × (pct / 100). Requires company goal on Executive Summary.
    allocation_pct_of_company_goal: Optional[float] = None


@router.post("/admin/create-user")
def admin_create_user(request: Request, req: CreateUserRequest):
    """Admin only: create a new user. Use Bearer token (from login) — no password needed."""
    is_admin = False
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        payload = _verify_token(token)
        if payload and (payload.get("role") or "").lower() == "admin":
            is_admin = True
    if not is_admin:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Log out and log in again, then try Add user.")
    err = create_user(req.username.strip(), req.password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"message": f"User '{req.username}' created."}

def serialize_df(df: pd.DataFrame) -> list:
    """Helper to cleanly serialize pandas dataframes to JSON. Returns [] on error to avoid 500s."""
    if df is None or df.empty:
        return []
    try:
        raw = df.to_json(orient="records", date_format="iso")
        # pandas can output NaN which is invalid JSON; replace so json.loads works
        if raw.find("NaN") != -1:
            raw = raw.replace("NaN", "null")
        return json.loads(raw)
    except Exception:
        return []

def _date_amount_columns(df: pd.DataFrame):
    """Return (date_col, amount_col) with case-insensitive match so trend works when DB returns lowercase."""
    if df is None or df.empty:
        return None, None
    date_col = next((c for c in df.columns if str(c).upper() == "DATE"), None)
    amount_col = next((c for c in df.columns if str(c).upper() == "AMOUNT"), None)
    return date_col, amount_col


def _unique_labels_ci(series: pd.Series, *, exclude_substr: tuple = ("NOT FOUND", "UNKNOWN")) -> List[str]:
    """Strip values; drop junk rows; collapse case-insensitive duplicates (first spelling wins). Sorted for stable UI."""
    if series is None or getattr(series, "empty", True):
        return []
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    canon: Dict[str, str] = {}
    for val in s:
        up = val.upper()
        if any(x in up for x in exclude_substr):
            continue
        k = val.lower()
        if k not in canon:
            canon[k] = val
    return sorted(canon.values(), key=lambda x: x.lower())


def _revenue_amount_series(df: pd.DataFrame) -> pd.Series:
    """Per-row value for customer revenue rollups: **AMOUNT only** (excludes tax / TOTALAMOUNT by design)."""
    idx = df.index
    if "AMOUNT" in df.columns:
        return pd.to_numeric(df["AMOUNT"], errors="coerce").fillna(0)
    return pd.Series(0.0, index=idx)


def _most_frequent_customer_label(series: pd.Series) -> str:
    """Canonical display name when the same account appears under different spellings / casing."""
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return ""
    return str(s.value_counts().index[0])


def _customer_summary_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per logical customer: group by case-insensitive trimmed name; Revenue from _revenue_amount_series.
    Includes STATE and CITY when present (most common value per customer when invoices differ).
    """
    empty_cols = ["CUSTOMER_NAME", "STATE", "CITY", "Revenue", "Orders", "AvgOrder", "LastOrder"]
    if df is None or df.empty or "CUSTOMER_NAME" not in df.columns:
        return pd.DataFrame(columns=empty_cols)
    if "AMOUNT" not in df.columns:
        return pd.DataFrame(columns=empty_cols)
    d = df.copy()
    d["_rev"] = _revenue_amount_series(d)
    d["_ck"] = d["CUSTOMER_NAME"].astype(str).str.strip().str.lower()
    d = d[d["_ck"] != ""]
    if d.empty:
        return pd.DataFrame(columns=empty_cols)
    inv_col = "INVOICE_NO" if "INVOICE_NO" in d.columns else None
    has_date = "DATE" in d.columns
    parts = {
        "CUSTOMER_NAME": ("CUSTOMER_NAME", _most_frequent_customer_label),
        "Revenue": ("_rev", "sum"),
        "AvgOrder": ("_rev", "mean"),
    }
    if "STATE" in d.columns:
        parts["STATE"] = ("STATE", _most_frequent_customer_label)
    if "CITY" in d.columns:
        parts["CITY"] = ("CITY", _most_frequent_customer_label)
    if inv_col:
        parts["Orders"] = (inv_col, "nunique")
    else:
        parts["Orders"] = ("_rev", "count")
    if has_date:
        parts["LastOrder"] = ("DATE", "max")
    out = d.groupby("_ck", as_index=False).agg(**parts)
    if "_ck" in out.columns:
        out = out.drop(columns=["_ck"])
    if "STATE" not in out.columns:
        out["STATE"] = ""
    if "CITY" not in out.columns:
        out["CITY"] = ""
    if has_date:
        _lo = pd.to_datetime(out["LastOrder"], errors="coerce")
        out["LastOrder"] = _lo.dt.strftime("%Y-%m-%d").where(_lo.notna(), "")
    else:
        out["LastOrder"] = ""
    # Stable column order for CSV/API
    col_order = ["CUSTOMER_NAME", "CITY", "STATE", "Revenue", "Orders", "AvgOrder", "LastOrder"]
    out = out[[c for c in col_order if c in out.columns]]
    return out


def _material_group_column(df: pd.DataFrame):
    """Return the material group column name if present (any common casing)."""
    candidates = [
        "ITEM_NAME_GROUP", "MATERIALGROUP", "MATERIAL_GROUP", "PRODUCT_CATEGORY", "CATEGORY", "ITEM_GROUP",
        "item_name_group", "materialgroup", "material_group", "product_category", "category", "item_group",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    # After standardize(), columns are UPPER; tolerate uncommon DB names
    for c in df.columns:
        cu = str(c).upper()
        if "GROUP" in cu and ("MATERIAL" in cu or "ITEM_NAME" in cu or "PRODUCT" in cu):
            return c
    return None

def _apply_material_mappings(df: pd.DataFrame) -> pd.DataFrame:
    """Rename/standardize material groups using regex patterns (same as legacy ETL)."""
    if df is None or df.empty:
        return df
    grp_col = _material_group_column(df)
    if grp_col is None:
        return df
    for pattern, replacement in MATERIAL_GROUP_MAPPINGS.items():
        mask = df[grp_col].astype(str).str.contains(pattern, case=False, na=False)
        df.loc[mask, grp_col] = replacement
    return df


def _exclude_material_groups(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove non-sales material groups using keyword/substring matching (same as legacy ETL).
    Row excluded if material group CONTAINS any keyword (case-insensitive).
    """
    if df is None or df.empty:
        return df
    grp_col = _material_group_column(df)
    if grp_col is None:
        return df
    norm = (
        df[grp_col]
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.upper()
    )
    mask = pd.Series(False, index=df.index)
    for keyword in EXCLUDE_KEYWORDS:
        mask = mask | norm.str.contains(keyword, case=False, na=False)
    return df[~mask]

def apply_filters(df: pd.DataFrame, states=None, cities=None, customers=None, material_groups=None, fiscal_years=None, months=None, items=None) -> pd.DataFrame:
    """Apply granular filters to a dataframe. Ignores empty or whitespace-only filter strings. `items` filters ITEMNAME (item-wise)."""
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if df.empty:
        return df
    if states and str(states).strip():
        state_list = [s.strip() for s in states.split(",") if s.strip()]
        if "STATE" in df.columns and state_list:
            df = df[df["STATE"].isin(state_list)]
    if cities and str(cities).strip():
        city_list = [c.strip() for c in cities.split(",") if c.strip()]
        if "CITY" in df.columns and city_list:
            gser = df["CITY"].astype(str).str.strip()
            want = {c.lower() for c in city_list}
            df = df[gser.str.lower().isin(want)]
    if customers and str(customers).strip():
        cust_list = [c.strip() for c in customers.split(",") if c.strip()]
        if "CUSTOMER_NAME" in df.columns and cust_list:
            df = df[df["CUSTOMER_NAME"].isin(cust_list)]
    mg_list: List[str] = []
    if material_groups is not None:
        if isinstance(material_groups, (list, tuple)):
            mg_list = [str(m).strip() for m in material_groups if str(m).strip()]
        elif str(material_groups).strip():
            mg_list = [m.strip() for m in str(material_groups).split(",") if m.strip()]
    if mg_list:
        grp_col = _material_group_column(df)
        if grp_col:
            gser = df[grp_col].astype(str).str.strip()
            mg_lower = {m.lower() for m in mg_list}
            df = df[gser.str.lower().isin(mg_lower)]
    if fiscal_years and str(fiscal_years).strip():
        fy_list = [f.strip() for f in fiscal_years.split(",") if f.strip()]
        if "FINANCIAL_YEAR" in df.columns and fy_list:
            # Normalize so "FY25-26" and "25-26" both match
            fy_set = set()
            for f in fy_list:
                fy_set.add(f)
                if str(f).upper().startswith("FY") and len(f) > 2:
                    fy_set.add(str(f)[2:].strip())
                else:
                    fy_set.add("FY" + str(f).strip())
            col = df["FINANCIAL_YEAR"].astype(str).str.strip()
            df = df[col.isin(fy_set)]
    if months and str(months).strip():
        month_list = [m.strip() for m in months.split(",") if m.strip()]
        if "MONTH" in df.columns and month_list:
            df = df[df["MONTH"].isin(month_list)]
    if items and str(items).strip():
        item_list = [x.strip() for x in str(items).split(",") if x.strip()]
        if "ITEMNAME" in df.columns and item_list:
            df = df[df["ITEMNAME"].astype(str).str.strip().isin(item_list)]
    return df

# Single canonical placeholder for missing state/region (avoids "State Not Found" vs "STATE NOT FOUND ⚠️")
STATE_PLACEHOLDER = "State Not Found"

# Helper functions adapted from etl_pipeline
def standardize(df):
    """Standardize column names and fuzzy-match to canonical names (synced with legacy ETL)."""
    if df.empty:
        return df
    df.columns = df.columns.str.strip().str.upper()
    df.columns = df.columns.str.replace(".", "", regex=False).str.replace(" ", "_")

    for col in list(df.columns):
        cu = col.upper()

        # CITY synonyms
        if any(x in cu for x in ["CITY", "TOWN", "DISTRICT", "LOCATION", "STATION", "DESTINATION", "PLACE"]):
            if "CITY" not in df.columns:
                df.rename(columns={col: "CITY"}, inplace=True)

        # STATE synonyms
        elif any(x in cu for x in ["STATE", "REGION", "PROVINCE", "TERRITORY", "POS", "SUPPLY"]):
            if "STATE" not in df.columns:
                df.rename(columns={col: "STATE"}, inplace=True)

        # CUSTOMER synonyms
        elif any(x in cu for x in ["CUSTOMER", "PARTY", "BILL TO", "BUYER", "DEBTOR"]):
            if "CUSTOMER_NAME" not in df.columns:
                df.rename(columns={col: "CUSTOMER_NAME"}, inplace=True)

        # ITEM synonyms (but not GROUP columns)
        elif any(x in cu for x in ["ITEM", "MATERIAL", "PRODUCT", "DESCRIPTION", "PART"]):
            if "ITEMNAME" not in df.columns and "GROUP" not in cu:
                df.rename(columns={col: "ITEMNAME"}, inplace=True)

        # INVOICE synonyms
        elif cu in ("NO", "NO.") or any(x in cu for x in ["INVOICE", "BILL_NO", "DOC_NO", "VOUCHER"]):
            if "INVOICE_NO" not in df.columns and "DATE" not in cu:
                df.rename(columns={col: "INVOICE_NO"}, inplace=True)

    return df

def _coalesce_state_region(df: pd.DataFrame) -> pd.DataFrame:
    """One STATE column: merge REGION/PROVINCE/TERRITORY into STATE where STATE is empty, then drop extras."""
    if df is None or df.empty:
        return df
    region_cols = [c for c in ["REGION", "PROVINCE", "TERRITORY"] if c in df.columns]
    if not region_cols:
        if "STATE" not in df.columns:
            df["STATE"] = STATE_PLACEHOLDER
        else:
            df["STATE"] = df["STATE"].fillna("").astype(str).str.strip()
            df.loc[df["STATE"].astype(str).str.strip() == "", "STATE"] = STATE_PLACEHOLDER
        return df
    if "STATE" not in df.columns:
        df["STATE"] = df[region_cols[0]].fillna("").astype(str).str.strip()
    for rc in region_cols:
        mask = (df["STATE"].fillna("").astype(str).str.strip() == "") | (df["STATE"].astype(str).str.upper().str.contains("NOT FOUND", na=False))
        df.loc[mask, "STATE"] = df.loc[mask, rc].fillna("").astype(str).str.strip()
        df.drop(columns=[rc], inplace=True, errors="ignore")
    df["STATE"] = df["STATE"].fillna("").astype(str).str.strip()
    df.loc[df["STATE"] == "", "STATE"] = STATE_PLACEHOLDER
    return df

def calculate_fy(date):
    """Indian FY label: April -> March (e.g. Apr 2025-Mar 2026 is FY25-26)."""
    if pd.isna(date): return "UNKNOWN"
    if date.month >= 4: return f"FY{date.year % 100}-{(date.year + 1) % 100}"
    else: return f"FY{(date.year - 1) % 100}-{date.year % 100}"


COMPANY_STATE = "MAHARASHTRA"
TAX_RATE = 0.18

def calculate_taxes(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate IGST/CGST/SGST based on STATE (same as legacy ETL)."""
    if df is None or df.empty or "AMOUNT" not in df.columns:
        return df

    cols_to_drop = [
        "TOTALAMOUNT", "TAX", "IGST", "CGST", "SGST",
        "IGST_RATE", "CGST_RATE", "SGST_RATE",
        "GRAND_TOTAL", "NET_AMOUNT", "TOTAL_TAX", "ROUND_OFF",
    ]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")

    df["IGST"] = 0.0
    df["CGST"] = 0.0
    df["SGST"] = 0.0
    df["TAX"] = 0.0
    df["TOTALAMOUNT"] = 0.0

    state_series = df["STATE"].copy() if "STATE" in df.columns else pd.Series(["Unknown"] * len(df), index=df.index)
    state_series = state_series.fillna("Unknown").astype(str).str.upper().str.strip()

    intra = state_series.isin([COMPANY_STATE, "UNKNOWN", "STATE NOT FOUND"])
    inter = ~intra

    df.loc[inter, "IGST"] = df.loc[inter, "AMOUNT"] * TAX_RATE
    df.loc[intra, "CGST"] = df.loc[intra, "AMOUNT"] * (TAX_RATE / 2)
    df.loc[intra, "SGST"] = df.loc[intra, "AMOUNT"] * (TAX_RATE / 2)

    df["TAX"] = df["IGST"] + df["CGST"] + df["SGST"]
    df["TOTALAMOUNT"] = df["AMOUNT"] + df["TAX"]

    return df


# ─── UPLOAD PIPELINE ───

# In-memory customer master per tenant (uploaded via /upload/customer-master)
_customer_masters: dict[str, pd.DataFrame] = {}


def _merge_customer_master(df: pd.DataFrame, tenant_id: str) -> pd.DataFrame:
    """Enrich sales data with STATE/CITY from the customer master if available."""
    master = _customer_masters.get(tenant_id)
    if master is None or master.empty:
        return df
    if "CUSTOMER_NAME" not in df.columns or "CUSTOMER_NAME" not in master.columns:
        return df
    master_cols = [c for c in ["CUSTOMER_NAME", "STATE", "CITY"] if c in master.columns]
    if len(master_cols) < 2:
        return df
    merged = pd.merge(df, master[master_cols], on="CUSTOMER_NAME", how="left", suffixes=("_raw", "_master"))
    for col in ["STATE", "CITY"]:
        mc = f"{col}_master"
        rc = f"{col}_raw"
        if mc in merged.columns and rc in merged.columns:
            merged[col] = merged[mc].fillna(merged[rc])
            merged.drop(columns=[mc, rc], inplace=True)
        elif mc in merged.columns:
            merged.rename(columns={mc: col}, inplace=True)
        elif rc in merged.columns:
            merged.rename(columns={rc: col}, inplace=True)
    return merged


@router.post("/data/clear")
def clear_data(tenant_id: str = Form("default_elettro")):
    """Clear all sales data for a tenant so it can be re-uploaded with enrichment."""
    from .db import clear_tenant_data
    deleted = clear_tenant_data(tenant_id)
    return {"deleted_rows": deleted, "tenant": tenant_id}


@router.post("/upload/customer-master")
async def upload_customer_master(file: UploadFile = File(...), tenant_id: str = Form("default_elettro")):
    """Upload a customer master Excel/CSV. Stored in memory; used to enrich STATE/CITY on subsequent sales uploads."""
    try:
        content = await file.read()
        if file.filename and file.filename.endswith(".csv"):
            master = pd.read_csv(io.BytesIO(content))
        else:
            master = pd.read_excel(io.BytesIO(content))
        master = standardize(master)
        _customer_masters[tenant_id] = master
        cols = list(master.columns)
        return {"filename": file.filename, "rows": len(master), "columns": cols, "tenant": tenant_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process customer master: {str(e)}")


@router.post("/upload")
async def handle_data_upload(file: UploadFile = File(...), tenant_id: str = Form("default_elettro")):
    try:
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
            
        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # 1. Clean & Standardize
        df = standardize(df)
        df = _coalesce_state_region(df)

        # 2. Enrich from customer master (STATE/CITY)
        df = _merge_customer_master(df, tenant_id)
        df = apply_customer_name_canonical(df)
        df = apply_customer_geo_overrides(df)

        # 3. Enrich Dates
        if "DATE" in df.columns:
            df["DATE"] = pd.to_datetime(df["DATE"], errors='coerce')
            df["FINANCIAL_YEAR"] = df["DATE"].apply(calculate_fy)
            df["MONTH"] = df["DATE"].dt.strftime("%b-%y").str.upper()

        if "CITY" not in df.columns: df["CITY"] = "City Not Found"
        if "STATE" not in df.columns: df["STATE"] = STATE_PLACEHOLDER

        # 4. Standardize material group names, then exclude non-sales rows (ETL rule)
        df = _apply_material_mappings(df)
        df = _exclude_material_groups(df)

        # 5. Calculate taxes (IGST/CGST/SGST based on state)
        df = calculate_taxes(df)

        # 6. Insert into database
        from .db import update_database
        rows_inserted = update_database(df, tenant_id)

        return {"filename": file.filename, "rows_inserted": rows_inserted, "tenant": tenant_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


# ─── Legacy Streamlit compatibility (v1) ───

@router.get("/v1/data")
def v1_data(tenant_id: str = Query("default_elettro")):
    """Legacy Streamlit: return full tenant data as JSON list of records."""
    df = get_tenant_data(tenant_id)
    return serialize_df(df)


@router.post("/v1/upload_batch")
async def v1_upload_batch(files: List[UploadFile] = File(...), tenant_id: str = Form("default_elettro")):
    """Legacy Streamlit: accept multiple files, process each like /upload; return last result."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    last_result = None
    for file in files:
        try:
            content = await file.read()
            if file.filename and file.filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
            if df.empty:
                continue
            df = standardize(df)
            df = _coalesce_state_region(df)
            if "DATE" in df.columns:
                df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
                df["FINANCIAL_YEAR"] = df["DATE"].apply(calculate_fy)
                df["MONTH"] = df["DATE"].dt.strftime("%b-%y").str.upper()
            if "CITY" not in df.columns:
                df["CITY"] = "City Not Found"
            if "STATE" not in df.columns:
                df["STATE"] = STATE_PLACEHOLDER
            df = _apply_material_mappings(df)
            df = _exclude_material_groups(df)
            df = calculate_taxes(df)
            from .db import update_database
            rows = update_database(df, tenant_id)
            last_result = {"filename": file.filename, "rows_inserted": rows, "tenant": tenant_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed on {file.filename}: {str(e)}")
    return last_result or {"filename": None, "rows_inserted": 0, "tenant": tenant_id}


# ─── DATA QUALITY / HEALTH ───

@router.get("/data/health")
def get_data_health(tenant_id: str = "default_elettro"):
    """Returns data quality metrics for the tenant: row counts, missing dates, duplicates, negative amounts, and a simple score."""
    df = get_tenant_data(tenant_id)
    if df.empty:
        return {
            "tenant_id": tenant_id,
            "total_rows": 0,
            "missing_dates": 0,
            "duplicate_invoices": 0,
            "negative_amounts": 0,
            "score": 0,
            "status": "no_data",
            "message": "No data found for this tenant.",
        }
    total = len(df)
    missing_dates = int(df["DATE"].isna().sum()) if "DATE" in df.columns else total
    dupes = 0
    if "INVOICE_NO" in df.columns and "DATE" in df.columns:
        dupes = int(total - df.drop_duplicates(subset=["INVOICE_NO", "DATE"]).shape[0])
    neg = int((df["AMOUNT"] < 0).sum()) if "AMOUNT" in df.columns else 0
    score = 100.0
    if total > 0:
        score = score - (missing_dates / total * 30) - (min(dupes / max(total, 1) * 100, 40)) - (min(neg / max(total, 1) * 100, 30))
    score = max(0, min(100, round(score, 1)))
    status = "good" if score >= 80 else "warning" if score >= 50 else "poor"
    return {
        "tenant_id": tenant_id,
        "total_rows": total,
        "missing_dates": missing_dates,
        "duplicate_invoices": dupes,
        "negative_amounts": neg,
        "score": score,
        "status": status,
        "message": f"Data quality score: {score}/100. {'No major issues.' if status == 'good' else 'Review missing dates, duplicates, or negative amounts.' if status == 'warning' else 'Significant data quality issues detected.'}",
    }


# ─── NATIVE PDF REPORTS ───
# pdf_generator (matplotlib) imported lazily below to avoid slow import on Render

@router.get("/reports/test-pdf")
def test_pdf():
    """Generate a simple test PDF to verify fpdf2 is working."""
    import fpdf as _fpdf_module
    fpdf_version = getattr(_fpdf_module, '__version__', 'unknown')
    fpdf_path = getattr(_fpdf_module, '__file__', 'unknown')
    from fpdf import FPDF
    import inspect
    cell_sig = str(inspect.signature(FPDF.cell))
    uses_text_param = 'text' in inspect.signature(FPDF.cell).parameters
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    # Use positional arg for max compatibility
    pdf.cell(0, 20, "TEST PDF - fpdf version check", 0, 1, "C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"fpdf version: {fpdf_version}", 0, 1, "L")
    pdf.cell(0, 8, f"fpdf path: {fpdf_path[:80]}", 0, 1, "L")
    pdf.cell(0, 8, f"cell() uses 'text=' param: {uses_text_param}", 0, 1, "L")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    # Test text= kwarg - will be blank on old PyFPDF
    pdf.cell(0, 10, text="If THIS line has text, fpdf2 is working correctly.", border=1)
    pdf.ln(12)
    # Test positional (always works)
    pdf.cell(0, 10, "This line uses positional args (always works).", 1, 1)
    raw = pdf.output()
    pdf_bytes = bytes(raw) if isinstance(raw, (bytearray, memoryview)) else raw.encode("latin-1") if isinstance(raw, str) else raw
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="test.pdf"'})


@router.get("/reports/download")
def download_pdf_report(
    tenant_id: str = "default_elettro",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    report_type: str = "Executive Summary",
    specific_entity: Optional[str] = None,
    filter_customer: Optional[str] = None,
    filter_state: Optional[str] = None,
    filter_material: Optional[str] = None,
    # Global filter bar params
    states: Optional[str] = None,
    cities: Optional[str] = None,
    customers: Optional[str] = None,
    material_groups: Optional[str] = None,
    fiscal_years: Optional[str] = None,
    months: Optional[str] = None,
    items: Optional[str] = None,
    include_cover: bool = Query(True, description="Distributor Strategy Report: include branded cover page"),
):
    try:
        from .pdf_generator import generate_pdf_report, generate_dynamic_pdf_report, generate_distributor_strategy_pdf
        df = get_tenant_data(tenant_id, start_date, end_date)
        logging.info(f"REPORT: raw rows={len(df)}, cols={list(df.columns)[:10]}")
        df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
        logging.info(f"REPORT: after filters rows={len(df)}, report_type={report_type}, entity={specific_entity}, months={months}")

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail="No data for the selected filters and date range. Widen filters or choose a different period."
            )

        if report_type == "Distributor Strategy Report":
            customer_name = specific_entity if specific_entity and str(specific_entity).strip() and str(specific_entity) != "All" else None
            if not customer_name and customers:
                parts = [p.strip() for p in str(customers).split(",") if p.strip()]
                if len(parts) == 1:
                    customer_name = parts[0]
            if not customer_name and "CUSTOMER_NAME" in df.columns:
                uniq = df["CUSTOMER_NAME"].dropna().unique()
                customer_name = uniq[0] if len(uniq) == 1 else "All Customers"
            customer_name = customer_name or "All Customers"
            if customer_name != "All Customers" and "CUSTOMER_NAME" in df.columns:
                df = df[df["CUSTOMER_NAME"].astype(str).str.strip() == str(customer_name).strip()]
            if df.empty:
                raise HTTPException(
                    status_code=404,
                    detail="No data for the selected customer and filters. Widen filters or choose a different period."
                )

            effective_months = months

            # Extra safeguard: if the dataframe already resolves to a single month
            # (e.g. due to other filtering), display that month on the PDF.
            if (not effective_months or not str(effective_months).strip()) and ("MONTH" in df.columns) and (not df.empty):
                uniq_months = (
                    df["MONTH"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .unique()
                    .tolist()
                )
                if len(uniq_months) == 1:
                    effective_months = uniq_months[0]
            fy_parts = []
            if fiscal_years:
                fy_parts = [p.strip() for p in str(fiscal_years).split(",") if p.strip()]
                analysis_period = fy_parts[0] if len(fy_parts) == 1 else (fiscal_years if isinstance(fiscal_years, str) else "YTD")
            elif start_date and end_date:
                analysis_period = f"{start_date} to {end_date}"
            else:
                analysis_period = "YTD"

            # If a month filter is selected in the UI, include it in the analysis period text
            # so it shows up on the PDF cover + summary.
            if effective_months and str(effective_months).strip():
                month_parts = [p.strip() for p in str(effective_months).split(",") if p.strip()]
                if len(month_parts) == 1:
                    suffix = f"Month: {month_parts[0]}"
                else:
                    shown = ", ".join(month_parts[:6])
                    suffix = f"Months: {shown}{'...' if len(month_parts) > 6 else ''}"
                analysis_period = f"{analysis_period} | {suffix}" if analysis_period else suffix
            pdf_bytes = generate_distributor_strategy_pdf(
                df,
                customer_name,
                analysis_period,
                selected_fiscal_years=fy_parts,
                include_cover=include_cover,
            )
            entity_name = str(customer_name).replace(" ", "_")
        else:
            pdf_bytes = generate_pdf_report(
                df,
                report_type,
                tenant_id,
                specific_entity,
                filter_customer,
                filter_state,
                filter_material,
                customers=customers,
                states=states,
                cities=cities,
                material_groups=material_groups,
                months=months,
                fiscal_years=fiscal_years,
                start_date=start_date,
                end_date=end_date,
            )
            entity_name = str(specific_entity).replace(' ', '_') if specific_entity and specific_entity != "All" else "Summary"

        filename = f"{REPORT_FILE_PREFIX}_{report_type.replace(' ', '_')}_{entity_name}_{tenant_id}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


# ─── DYNAMIC PDF REPORTS (Streamlit-like) ───

class DynamicReportSpec(BaseModel):
    title: str = "Dynamic Report"
    primary_dimension: str = "customer"
    secondary_dimension: Optional[str] = None
    top_n: int = 12
    include_trend: bool = True
    include_share: bool = True
    include_top_table: bool = True
    include_pivot: bool = False


class DynamicReportRequest(BaseModel):
    tenant_id: str = "default_elettro"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    # Global filter bar params (comma-separated strings)
    states: Optional[str] = None
    cities: Optional[str] = None
    customers: Optional[str] = None
    material_groups: Optional[str] = None
    fiscal_years: Optional[str] = None
    months: Optional[str] = None
    items: Optional[str] = None
    spec: DynamicReportSpec


@router.post("/reports/dynamic")
def download_dynamic_report(req: DynamicReportRequest):
    try:
        from .pdf_generator import generate_dynamic_pdf_report
        df = get_tenant_data(req.tenant_id, req.start_date, req.end_date)
        df = apply_filters(df, req.states, req.cities, req.customers, req.material_groups, req.fiscal_years, req.months, req.items)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data for the selected filters and date range.")

        pdf_bytes = generate_dynamic_pdf_report(
            df=df,
            title=req.spec.title,
            tenant=req.tenant_id,
            primary_dimension=req.spec.primary_dimension,
            secondary_dimension=req.spec.secondary_dimension,
            top_n=req.spec.top_n,
            include_trend=req.spec.include_trend,
            include_share=req.spec.include_share,
            include_top_table=req.spec.include_top_table,
            include_pivot=req.spec.include_pivot,
            customers=req.customers,
            states=req.states,
            cities=req.cities,
            material_groups=req.material_groups,
            months=req.months,
            fiscal_years=req.fiscal_years,
            start_date=req.start_date,
            end_date=req.end_date,
        )

        safe_title = (req.spec.title or "Dynamic_Report").replace(" ", "_")
        filename = f"{REPORT_FILE_PREFIX}_Dynamic_{safe_title}_{req.tenant_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate dynamic report: {str(e)}")


# ─── AI CHATBOT ───
# chatbot imported lazily in handle_chat_query to keep app import fast

class ChatRequest(BaseModel):
    query: str
    tenant: str = "default_elettro"
    startDate: Optional[str] = None
    endDate: Optional[str] = None

@router.post("/chat")
def handle_chat_query(req: ChatRequest):
    try:
        from .chatbot import process_query as chat_process_query
        df = get_tenant_data(req.tenant, req.startDate, req.endDate)
        response_text = chat_process_query(req.query, df)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")

# ─── FILTER OPTIONS ───

def _item_name_column(df: pd.DataFrame) -> Optional[str]:
    """Column holding SKU / item description for filter picklists."""
    for c in ("ITEMNAME", "ITEM_NAME", "PRODUCT_NAME", "MATERIAL_NAME", "ITEM_DESC"):
        if c in df.columns:
            return c
    return None


@router.get("/filters/options")
def get_filter_options(
    request: Request,
    tenant_id: str = "default_elettro",
    material_groups_json: Optional[str] = Query(None),
):
    """Returns all unique filter values for the sidebar multi-selects.

    Pass selected groups as ``material_groups_json`` (URL-encoded JSON array), e.g. ``["Air filter","X"]``.
    Single query param survives proxies reliably; ``items`` is then restricted to SKUs in those groups.
    Fallback: repeated ``material_groups`` query keys (Starlette getlist).
    """
    material_groups: List[str] = []
    if material_groups_json and str(material_groups_json).strip():
        try:
            parsed = json.loads(material_groups_json)
            if isinstance(parsed, list):
                material_groups = [str(x).strip() for x in parsed if str(x).strip()]
        except (json.JSONDecodeError, TypeError, ValueError):
            material_groups = []
    if not material_groups:
        material_groups = [m.strip() for m in request.query_params.getlist("material_groups") if m.strip()]

    df = get_tenant_data(tenant_id)
    if df.empty:
        return {"states": [], "cities": [], "cities_by_state": {}, "customers": [], "material_groups": [], "fiscal_years": [], "months": [], "items": []}

    # Align column names with the rest of the API (ITEMNAME, ITEM_NAME_GROUP, …) so filters match apply_filters
    df = standardize(df.copy())
    df = _coalesce_state_region(df)

    df_for_items = df
    if material_groups:
        df_for_items = apply_filters(df, None, None, None, material_groups, None, None, None)

    # Exclude placeholders; collapse "Pune" / "PUNE" / spacing variants so picklists do not show duplicates
    states = _unique_labels_ci(df["STATE"], exclude_substr=("NOT FOUND",)) if "STATE" in df.columns else []
    cities = _unique_labels_ci(df["CITY"], exclude_substr=("NOT FOUND", "UNKNOWN")) if "CITY" in df.columns else []
    customers = sorted(df["CUSTOMER_NAME"].dropna().unique().tolist()) if "CUSTOMER_NAME" in df.columns else []
    
    grp_col = _material_group_column(df)
    material_group_choices = sorted(df[grp_col].dropna().unique().tolist()) if grp_col else []
    
    fiscal_years = sorted(df["FINANCIAL_YEAR"].dropna().unique().tolist()) if "FINANCIAL_YEAR" in df.columns else []
    months = []
    if "MONTH" in df.columns:
        try:
            unique_months = df["MONTH"].dropna().unique()
            month_df = pd.DataFrame({"MONTH": unique_months})
            month_df["SortKey"] = pd.to_datetime(month_df["MONTH"], format="%b-%y", errors='coerce')
            months = month_df.sort_values("SortKey")["MONTH"].tolist()
        except:
            months = sorted(df["MONTH"].dropna().unique().tolist())

    _ITEM_CAP = 4000
    item_names: list = []
    item_col = _item_name_column(df_for_items)
    if item_col:
        raw_items = df_for_items[item_col].dropna().astype(str).str.strip()
        raw_items = raw_items[raw_items != ""]
        item_names = sorted(raw_items.unique().tolist())[:_ITEM_CAP]

    cities_by_state: dict = {}
    if "STATE" in df.columns and "CITY" in df.columns:
        for st in df["STATE"].dropna().unique():
            st_s = str(st).strip()
            if not st_s or "NOT FOUND" in st_s.upper():
                continue
            sub = df[df["STATE"].astype(str).str.strip() == st_s]["CITY"]
            clist = _unique_labels_ci(sub, exclude_substr=("NOT FOUND", "UNKNOWN"))
            if clist:
                cities_by_state[st_s] = clist

    return {
        "states": states,
        "cities": cities,
        "cities_by_state": cities_by_state,
        "customers": customers,
        "material_groups": material_group_choices,
        "fiscal_years": fiscal_years,
        "months": months,
        "items": item_names,
    }

# ─── SALES TARGETS (Neon / Postgres) ───

@router.get("/settings/sales-targets")
def api_get_sales_targets(tenant_id: str = Query("default_elettro")):
    """Current saved targets for the tenant (dashboard revenue/order goals)."""
    t = get_sales_targets(tenant_id)
    return {"tenant_id": tenant_id, "target_revenue": t["revenue"], "target_orders": t["orders"]}


@router.put("/settings/sales-targets")
def api_put_sales_targets(body: SalesTargetsPut):
    """Create or update sales targets. Use null to clear a target."""
    ok = set_sales_targets(body.tenant_id, body.target_revenue, body.target_orders)
    if not ok:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return {"ok": True, "tenant_id": body.tenant_id, **get_sales_targets(body.tenant_id)}


# ─── DISTRIBUTOR MONTHLY TARGETS (per customer, material split inside customer) ───

@router.get("/distributor/targets")
def api_list_distributor_targets(
    tenant_id: str = Query("default_elettro"),
    year_month: Optional[str] = None,
):
    """Saved monthly ₹ targets per distributor (optional filter by YYYY-MM)."""
    return {"targets": list_distributor_targets(tenant_id, year_month)}


@router.put("/distributor/targets")
def api_put_distributor_target(body: DistributorTargetPut):
    """
    Set a distributor's monthly target. Either pass target_revenue (₹) OR
    allocation_pct_of_company_goal (e.g. 30 = 30% of company revenue goal from Executive Summary).
    """
    if not body.customer_name or not body.year_month:
        raise HTTPException(status_code=400, detail="customer_name and year_month (YYYY-MM) are required.")
    ym = body.year_month.strip()
    if len(ym) != 7 or ym[4] != "-":
        raise HTTPException(status_code=400, detail="year_month must be YYYY-MM.")

    rev: Optional[float] = body.target_revenue
    pct_snap: Optional[float] = None
    if body.allocation_pct_of_company_goal is not None:
        g = get_sales_targets(body.tenant_id)
        gr = g.get("revenue")
        if gr is None or float(gr) <= 0:
            raise HTTPException(
                status_code=400,
                detail="Set a company revenue goal (Executive Summary → Save targets) before using percent allocation.",
            )
        pct = float(body.allocation_pct_of_company_goal)
        if pct < 0 or pct > 100:
            raise HTTPException(status_code=400, detail="Percent must be between 0 and 100.")
        rev = float(gr) * (pct / 100.0)
        pct_snap = pct
    if rev is None or rev < 0:
        raise HTTPException(status_code=400, detail="Provide target_revenue or allocation_pct_of_company_goal.")

    ok = upsert_distributor_target(body.tenant_id, body.customer_name, ym, float(rev), pct_snap)
    if not ok:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return {
        "ok": True,
        "tenant_id": body.tenant_id,
        "customer_name": body.customer_name.strip(),
        "year_month": ym,
        "target_revenue": float(rev),
        "allocation_pct_snapshot": pct_snap,
    }


def build_distributor_vs_target_report(tenant_id: str, customer_name: str, year_month: str) -> dict:
    """
    Shared payload for JSON and PDF: actual vs target by material group for one customer/month.
    """
    ym = year_month.strip()
    if len(ym) != 7 or ym[4] != "-":
        raise HTTPException(status_code=400, detail="year_month must be YYYY-MM.")
    try:
        y, m = map(int, ym.split("-"))
        last_day = calendar.monthrange(y, m)[1]
        start_str = f"{y}-{m:02d}-01"
        end_str = f"{y}-{m:02d}-{last_day}"
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid year_month.")

    target = get_distributor_target(tenant_id, customer_name, ym)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail="No saved target for this customer and month. Save under Distributor vs Target first.",
        )

    df = get_tenant_data(tenant_id, start_str, end_str)
    cn = "CUSTOMER_NAME"
    amt_col = next((c for c in df.columns if str(c).upper() == "AMOUNT"), None)
    if not df.empty and cn not in df.columns:
        raise HTTPException(status_code=400, detail="CUSTOMER_NAME column missing.")
    if not df.empty and amt_col is None:
        raise HTTPException(status_code=400, detail="AMOUNT column missing.")

    if df.empty or amt_col is None:
        return {
            "tenant_id": tenant_id,
            "customer_name": customer_name.strip(),
            "year_month": ym,
            "period": {"start": start_str, "end": end_str},
            "customer_target": round(float(target), 2),
            "customer_actual": 0.0,
            "customer_variance": round(-float(target), 2),
            "customer_pct_of_target": 0.0,
            "material_groups": [],
            "message": "No invoice rows in database for this month.",
        }

    df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)
    dfc = df[df[cn].astype(str).str.strip() == customer_name.strip()]
    if dfc.empty:
        return {
            "tenant_id": tenant_id,
            "customer_name": customer_name.strip(),
            "year_month": ym,
            "period": {"start": start_str, "end": end_str},
            "customer_target": round(float(target), 2),
            "customer_actual": 0.0,
            "customer_variance": round(-float(target), 2),
            "customer_pct_of_target": 0.0,
            "material_groups": [],
            "message": "No sales for this customer in the selected month.",
        }

    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in dfc.columns else ("MATERIALGROUP" if "MATERIALGROUP" in dfc.columns else None)
    cust_actual = float(dfc[amt_col].sum())
    rows = []

    if grp_col is None:
        tgt = float(target)
        var = cust_actual - tgt
        pct_t = (cust_actual / tgt * 100) if tgt > 0 else 0.0
        rows.append({
            "material_group": "(all)",
            "actual": round(cust_actual, 2),
            "share_of_customer_pct": 100.0,
            "target": round(tgt, 2),
            "variance": round(var, 2),
            "pct_of_target": round(pct_t, 1),
        })
    else:
        mg = dfc.groupby(grp_col)[amt_col].sum()
        for gname, aval in mg.items():
            aval = float(aval)
            share = (aval / cust_actual) if cust_actual > 0 else 0.0
            tgt = float(target) * share
            var = aval - tgt
            pct = (aval / tgt * 100) if tgt > 0 else 0.0
            rows.append({
                "material_group": str(gname),
                "actual": round(aval, 2),
                "share_of_customer_pct": round(share * 100, 2),
                "target": round(tgt, 2),
                "variance": round(var, 2),
                "pct_of_target": round(pct, 1),
            })
        rows.sort(key=lambda x: x["actual"], reverse=True)

    tgt_f = float(target)
    cvar = cust_actual - tgt_f
    cpct = (cust_actual / tgt_f * 100) if tgt_f > 0 else 0.0
    return {
        "tenant_id": tenant_id,
        "customer_name": customer_name.strip(),
        "year_month": ym,
        "period": {"start": start_str, "end": end_str},
        "customer_target": round(tgt_f, 2),
        "customer_actual": round(cust_actual, 2),
        "customer_variance": round(cvar, 2),
        "customer_pct_of_target": round(cpct, 1),
        "material_groups": rows,
    }


@router.get("/reports/distributor-vs-target")
def report_distributor_vs_target(
    tenant_id: str = Query("default_elettro"),
    customer_name: str = Query(..., description="Distributor / CUSTOMER_NAME"),
    year_month: str = Query(..., description="YYYY-MM"),
):
    """
    Compare actual sales vs saved monthly target for one customer.
    Material-group targets = customer target × (group sales ÷ customer sales) for that month.
    """
    return build_distributor_vs_target_report(tenant_id, customer_name, year_month)


@router.get("/reports/distributor-vs-target/pdf")
def report_distributor_vs_target_pdf(
    tenant_id: str = Query("default_elettro"),
    customer_name: str = Query(..., description="Distributor / CUSTOMER_NAME"),
    year_month: str = Query(..., description="YYYY-MM"),
):
    """PDF export of Distributor vs Target (same data as JSON report)."""
    from .pdf_generator import generate_distributor_vs_target_pdf

    data = build_distributor_vs_target_report(tenant_id, customer_name, year_month)
    pdf_bytes = generate_distributor_vs_target_pdf(data)
    safe_c = "".join(c if c.isalnum() or c in "-_" else "_" for c in customer_name.strip())[:40]
    ym = year_month.strip().replace("/", "-")
    fname = f"{REPORT_FILE_PREFIX}_DistributorVsTarget_{safe_c}_{ym}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ─── DASHBOARD (single-call for faster load) ───

@router.get("/dashboard/summary")
def get_dashboard_summary(
    tenant_id: str = "default_elettro",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    customers: Optional[str] = None,
    material_groups: Optional[str] = None,
    fiscal_years: Optional[str] = None,
    months: Optional[str] = None,
    items: Optional[str] = None,
    trend_limit: int = 36,
    material_limit: int = 10,
    top_customers_limit: int = 10,
    goal_revenue: Optional[float] = None,
    goal_orders: Optional[int] = None,
):
    """Single endpoint: summary + trend + material groups + top customers + previous-period comparison + optional goals."""
    def _empty(msg: str):
        st = get_sales_targets(tenant_id)
        return {
            "summary": {"revenue": 0, "orders": 0, "customers": 0, "average_order_value": 0},
            "previous_summary": None,
            "comparison": None,
            "goals": None,
            "sales_targets": {"revenue": st["revenue"], "orders": st["orders"]},
            "trend": [],
            "material_groups": [],
            "top_customers": [],
            "message": msg,
        }
    try:
        df = get_tenant_data(tenant_id, start_date, end_date)
        df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return _empty("No rows in database for this tenant. Upload data from the Data page (Cloud Data Uploader).")
        # Coerce numeric/date so DB string or tz-aware types never raise
        amt_col = next((c for c in df.columns if str(c).upper() == "AMOUNT"), None)
        if amt_col is not None:
            df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)
        date_col_raw = next((c for c in df.columns if str(c).upper() == "DATE"), None)
        if date_col_raw is not None:
            df[date_col_raw] = pd.to_datetime(df[date_col_raw], errors="coerce")
            if hasattr(df[date_col_raw].dtype, "tz") and df[date_col_raw].dtype.tz is not None:
                df[date_col_raw] = df[date_col_raw].dt.tz_localize(None)
        revenue = float(df[amt_col].sum()) if amt_col is not None else 0.0
        orders = int(df["INVOICE_NO"].nunique()) if "INVOICE_NO" in df.columns else 0
        cust_count = int(df["CUSTOMER_NAME"].nunique()) if "CUSTOMER_NAME" in df.columns else 0
        aov = revenue / orders if orders > 0 else 0
        summary = {"revenue": revenue, "orders": orders, "customers": cust_count, "average_order_value": aov}

        previous_summary = None
        comparison = None
        if start_date and end_date and "DATE" in df.columns:
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                if len(str(end_date).strip()) <= 10:
                    end_dt = end_dt + pd.Timedelta(days=1)
                delta = end_dt - start_dt
                prev_end = start_dt - pd.Timedelta(days=1)
                prev_start = prev_end - delta
                prev_start_str = prev_start.strftime("%Y-%m-%d")
                prev_end_str = prev_end.strftime("%Y-%m-%d")
                df_prev = get_tenant_data(tenant_id, prev_start_str, prev_end_str)
                df_prev = apply_filters(df_prev, states, cities, customers, material_groups, fiscal_years, months, items)
                if not df_prev.empty:
                    _amt = next((c for c in df_prev.columns if str(c).upper() == "AMOUNT"), None)
                    pr = float(df_prev[_amt].sum()) if _amt is not None else 0.0
                    po = int(df_prev["INVOICE_NO"].nunique()) if "INVOICE_NO" in df_prev.columns else 0
                    pc = int(df_prev["CUSTOMER_NAME"].nunique()) if "CUSTOMER_NAME" in df_prev.columns else 0
                    paov = pr / po if po > 0 else 0
                    previous_summary = {"revenue": pr, "orders": po, "customers": pc, "average_order_value": paov}
                    rev_pct = ((revenue - pr) / pr * 100) if pr > 0 else 0
                    ord_pct = ((orders - po) / po * 100) if po > 0 else 0
                    cust_pct = ((cust_count - pc) / pc * 100) if pc > 0 else 0
                    aov_pct = ((aov - paov) / paov * 100) if paov > 0 else 0
                    comparison = {
                        "revenue_pct": round(rev_pct, 1),
                        "orders_pct": round(ord_pct, 1),
                        "customers_pct": round(cust_pct, 1),
                        "average_order_value_pct": round(aov_pct, 1),
                    }
            except Exception:
                pass

        db_targets = get_sales_targets(tenant_id)
        eff_goal_rev = goal_revenue if goal_revenue is not None and goal_revenue > 0 else (
            db_targets["revenue"] if db_targets.get("revenue") and db_targets["revenue"] > 0 else None
        )
        eff_goal_ord = goal_orders if goal_orders is not None and goal_orders > 0 else (
            db_targets["orders"] if db_targets.get("orders") and db_targets["orders"] > 0 else None
        )
        goals = None
        if eff_goal_rev is not None and eff_goal_rev > 0:
            goals = {
                "revenue_target": eff_goal_rev,
                "revenue_achievement_pct": round(revenue / eff_goal_rev * 100, 1),
            }
        if eff_goal_ord is not None and eff_goal_ord > 0:
            goals = goals or {}
            goals["orders_target"] = eff_goal_ord
            goals["orders_achievement_pct"] = round(orders / eff_goal_ord * 100, 1)

        trend = []
        date_col, amount_col = _date_amount_columns(df)
        if date_col and amount_col:
            df_t = df.copy()
            df_t[date_col] = pd.to_datetime(df_t[date_col], errors="coerce")
            df_t = df_t.dropna(subset=[date_col])
            if not df_t.empty:
                t = df_t.groupby(pd.Grouper(key=date_col, freq="ME"))[amount_col].sum().reset_index()
                t = t.rename(columns={date_col: "DATE", amount_col: "AMOUNT"})
                t["DATE"] = t["DATE"].dt.strftime("%Y-%m")
                trend = serialize_df(t.tail(trend_limit))
        if not trend and amount_col:
            month_col = next((c for c in df.columns if str(c).upper() == "MONTH"), None)
            if month_col:
                try:
                    by_month = df.groupby(month_col)[amount_col].sum().reset_index()
                    by_month = by_month.rename(columns={amount_col: "AMOUNT", month_col: "MONTH"})
                    month_str = by_month["MONTH"].astype(str).str.strip()
                    month_str = month_str.str[:3].str.title() + "-" + month_str.str[-2:]
                    by_month["DATE"] = pd.to_datetime(month_str, format="%b-%y", errors="coerce")
                    by_month = by_month.dropna(subset=["DATE"]).sort_values("DATE")
                    by_month["DATE"] = by_month["DATE"].dt.strftime("%Y-%m")
                    trend = serialize_df(by_month[["DATE", "AMOUNT"]].tail(trend_limit))
                except Exception:
                    pass

        grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
        material_groups_list = []
        if grp_col in df.columns and amt_col is not None:
            mg = df.groupby(grp_col)[amt_col].sum().sort_values(ascending=False).head(material_limit).reset_index()
            # Split total revenue target by each row's share of filtered sales (same logic for customers & materials)
            if eff_goal_rev is not None and eff_goal_rev > 0 and revenue > 0:
                mg["SHARE_PCT"] = (mg[amt_col] / revenue * 100).round(2)
                mg["TARGET_REVENUE"] = (eff_goal_rev * mg[amt_col] / revenue).round(2)
                _tr = mg["TARGET_REVENUE"]
                mg["VS_TARGET_PCT"] = (mg[amt_col] / _tr * 100).where(_tr > 0, 0).round(1)
            material_groups_list = serialize_df(mg)

        top_customers_list = []
        if "CUSTOMER_NAME" in df.columns and amt_col is not None:
            tc = df.groupby("CUSTOMER_NAME")[amt_col].sum().sort_values(ascending=False).head(top_customers_limit).reset_index()
            if eff_goal_rev is not None and eff_goal_rev > 0 and revenue > 0:
                tc["SHARE_PCT"] = (tc[amt_col] / revenue * 100).round(2)
                tc["TARGET_REVENUE"] = (eff_goal_rev * tc[amt_col] / revenue).round(2)
                _trc = tc["TARGET_REVENUE"]
                tc["VS_TARGET_PCT"] = (tc[amt_col] / _trc * 100).where(_trc > 0, 0).round(1)
            top_customers_list = serialize_df(tc)

        return {
            "summary": summary,
            "previous_summary": previous_summary,
            "comparison": comparison,
            "goals": goals,
            "sales_targets": {"revenue": db_targets["revenue"], "orders": db_targets["orders"]},
            "trend": trend,
            "material_groups": material_groups_list,
            "top_customers": top_customers_list,
        }
    except Exception as e:
        logging.exception("dashboard/summary: processing failed: %s", e)
        err_msg = str(e).strip() or "Unknown error"
        if len(err_msg) > 200:
            err_msg = err_msg[:197] + "..."
        return _empty(f"Backend error: {err_msg}")


# ─── EXECUTIVE SUMMARY ───

@router.get("/metrics/summary")
def get_kpi_summary(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found.")
    revenue = float(df["AMOUNT"].sum()) if "AMOUNT" in df.columns else 0.0
    orders = int(df["INVOICE_NO"].nunique()) if "INVOICE_NO" in df.columns else 0
    customers = int(df["CUSTOMER_NAME"].nunique()) if "CUSTOMER_NAME" in df.columns else 0
    return {
        "revenue": revenue,
        "orders": orders,
        "customers": customers,
        "average_order_value": revenue / orders if orders > 0 else 0
    }

@router.get("/charts/trend")
def get_sales_trend(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    amount_col = next((c for c in df.columns if str(c).upper() == "AMOUNT"), None)
    date_col, _ = _date_amount_columns(df)
    if not amount_col:
        return []
    out = []
    if date_col:
        df_t = df.copy()
        df_t[date_col] = pd.to_datetime(df_t[date_col], errors="coerce")
        df_t = df_t.dropna(subset=[date_col])
        if not df_t.empty:
            trend = df_t.groupby(pd.Grouper(key=date_col, freq="ME"))[amount_col].sum().reset_index()
            trend = trend.rename(columns={date_col: "DATE", amount_col: "AMOUNT"})
            trend["DATE"] = trend["DATE"].dt.strftime("%Y-%m")
            return serialize_df(trend)
    month_col = next((c for c in df.columns if str(c).upper() == "MONTH"), None)
    if month_col:
        try:
            by_month = df.groupby(month_col)[amount_col].sum().reset_index()
            by_month = by_month.rename(columns={amount_col: "AMOUNT", month_col: "MONTH"})
            month_str = by_month["MONTH"].astype(str).str.strip()
            month_str = month_str.str[:3].str.title() + "-" + month_str.str[-2:]
            by_month["DATE"] = pd.to_datetime(month_str, format="%b-%y", errors="coerce")
            by_month = by_month.dropna(subset=["DATE"]).sort_values("DATE")
            by_month["DATE"] = by_month["DATE"].dt.strftime("%Y-%m")
            return serialize_df(by_month[["DATE", "AMOUNT"]])
        except Exception:
            pass
    return []

@router.get("/charts/material-groups")
def get_material_groups(tenant_id: str = "default_elettro", limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    if df.empty or grp_col not in df.columns:
        return []
    merged = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(limit).reset_index()
    return serialize_df(merged)

@router.get("/charts/top-customers")
def get_top_customers(tenant_id: str = "default_elettro", limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty or "CUSTOMER_NAME" not in df.columns:
        return []
    merged = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(limit).reset_index()
    return serialize_df(merged)

# ─── SALES & GROWTH ───

@router.get("/sales/monthly")
def get_monthly_sales(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty or "DATE" not in df.columns:
        return []
    df["MONTH"] = df["DATE"].dt.to_period("M").astype(str)
    monthly = df.groupby("MONTH").agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique"),
        Customers=("CUSTOMER_NAME", "nunique")
    ).reset_index()
    return serialize_df(monthly)

@router.get("/sales/daily")
def get_daily_sales(tenant_id: str = "default_elettro", days: int = 30, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty or "DATE" not in df.columns:
        return []
    df["DAY"] = df["DATE"].dt.strftime("%Y-%m-%d")
    daily = df.groupby("DAY").agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique")
    ).sort_index().tail(days).reset_index()
    return serialize_df(daily)

@router.get("/sales/growth")
def get_growth_metrics(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty or "DATE" not in df.columns:
        return {"mom_growth": 0, "current_month_rev": 0, "prev_month_rev": 0}
    df["MONTH"] = df["DATE"].dt.to_period("M")
    monthly = df.groupby("MONTH")["AMOUNT"].sum().sort_index()
    if len(monthly) < 2:
        return {"mom_growth": 0, "current_month_rev": float(monthly.iloc[-1]) if len(monthly) > 0 else 0, "prev_month_rev": 0}
    curr = float(monthly.iloc[-1])
    prev = float(monthly.iloc[-2])
    growth = ((curr - prev) / prev * 100) if prev > 0 else 0
    return {"mom_growth": round(growth, 1), "current_month_rev": curr, "prev_month_rev": prev}

# ─── CUSTOMER INTELLIGENCE ───

@router.get("/customers/all")
def get_all_customers(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    cust = _customer_summary_df(df)
    if cust.empty:
        return []
    cust = cust.sort_values("Revenue", ascending=False).reset_index(drop=True)
    return serialize_df(cust)

@router.get("/customers/rfm")
def get_rfm_segments(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty or "CUSTOMER_NAME" not in df.columns or "DATE" not in df.columns:
        return []
    if "AMOUNT" not in df.columns:
        return []
    df = df.copy()
    df["_rev"] = _revenue_amount_series(df)
    df["_ck"] = df["CUSTOMER_NAME"].astype(str).str.strip().str.lower()
    df = df[df["_ck"] != ""]
    if df.empty:
        return []
    max_date = df["DATE"].max()
    inv_col = "INVOICE_NO" if "INVOICE_NO" in df.columns else None
    if inv_col:
        rfm = df.groupby("_ck").agg(
            CUSTOMER_NAME=("CUSTOMER_NAME", _most_frequent_customer_label),
            Recency=("DATE", lambda x: (max_date - x.max()).days),
            Frequency=(inv_col, "nunique"),
            Monetary=("_rev", "sum"),
        ).reset_index()
    else:
        rfm = df.groupby("_ck").agg(
            CUSTOMER_NAME=("CUSTOMER_NAME", _most_frequent_customer_label),
            Recency=("DATE", lambda x: (max_date - x.max()).days),
            Frequency=("DATE", "count"),
            Monetary=("_rev", "sum"),
        ).reset_index()
    if "_ck" in rfm.columns:
        rfm = rfm.drop(columns=["_ck"])
    # Simple scoring
    for col in ["Recency", "Frequency", "Monetary"]:
        rfm[f"{col}_Score"] = pd.qcut(rfm[col], q=4, labels=[4,3,2,1] if col == "Recency" else [1,2,3,4], duplicates="drop").astype(int)
    rfm["RFM_Score"] = rfm["Recency_Score"] + rfm["Frequency_Score"] + rfm["Monetary_Score"]
    def segment(score):
        if score >= 10: return "Champions"
        elif score >= 8: return "Loyal"
        elif score >= 6: return "Potential"
        elif score >= 4: return "At Risk"
        else: return "Lost"
    rfm["Segment"] = rfm["RFM_Score"].apply(segment)
    return serialize_df(rfm[["CUSTOMER_NAME", "Recency", "Frequency", "Monetary", "Segment"]])

# ─── GEOGRAPHIC ───

@router.get("/geographic/states")
def get_state_data(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    if df.empty or "STATE" not in df.columns:
        return []
    # Exclude placeholder so map/region only show real states (avoids "no state found" / duplicate region)
    df = df[~df["STATE"].astype(str).str.upper().str.contains("NOT FOUND", na=False)]
    if df.empty:
        return []
    # Single row per state: merge MAHARASHTRA / Maharashtra / maharashtra (map + filters)
    df = df.copy()
    df["STATE"] = df["STATE"].astype(str).str.strip()
    df = df[df["STATE"].str.len() > 0]
    df["_STATE_KEY"] = df["STATE"].str.upper()
    state = df.groupby("_STATE_KEY", as_index=False).agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique"),
        Customers=("CUSTOMER_NAME", "nunique"),
    ).sort_values("Revenue", ascending=False)
    state["STATE"] = state["_STATE_KEY"].map(lambda x: str(x).title() if pd.notna(x) else "")
    state = state.drop(columns=["_STATE_KEY"])
    
    # Add market share
    total_rev = state["Revenue"].sum()
    state["MarketShare"] = (state["Revenue"] / total_rev * 100).round(1) if total_rev > 0 else 0
    state["Revenue_Cr"] = (state["Revenue"] / 10000000).round(2)
    
    # Add lat/lon from geo_data
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    try:
        from shared.geo_data import STATE_COORDS
        state["lat"] = state["STATE"].map(lambda x: STATE_COORDS.get(str(x).strip(), [20.5937, 78.9629])[0])
        state["lon"] = state["STATE"].map(lambda x: STATE_COORDS.get(str(x).strip(), [20.5937, 78.9629])[1])
    except:
        state["lat"] = 20.5937
        state["lon"] = 78.9629
    
    return serialize_df(state)

@router.get("/geographic/cities")
def get_city_data(tenant_id: str = "default_elettro", limit: int = 20, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    col = "CITY" if "CITY" in df.columns else "STATE"
    if df.empty or col not in df.columns:
        return []
    df = df.copy()
    df[col] = df[col].astype(str).str.strip()
    df = df[df[col].str.len() > 0]
    key_col = "_GEO_KEY"
    df[key_col] = df[col].str.upper()
    city = df.groupby(key_col).agg(
        Revenue=("AMOUNT", "sum"),
        Customers=("CUSTOMER_NAME", "nunique"),
    ).sort_values("Revenue", ascending=False).head(limit).reset_index()
    city[col] = city[key_col].map(lambda x: str(x).title() if pd.notna(x) else "")
    city = city.drop(columns=[key_col])
    return serialize_df(city)

# ─── MATERIAL PERFORMANCE ───

@router.get("/materials/performance")
def get_material_performance(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    grp_col = _material_group_column(df)
    if df.empty or grp_col is None:
        return []
    perf = df.groupby(grp_col).agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique"),
        Customers=("CUSTOMER_NAME", "nunique"),
        AvgPrice=("AMOUNT", "mean")
    ).sort_values("Revenue", ascending=False).reset_index()
    # Stable JSON key for UIs (many datasets use MATERIALGROUP only; reports table expects ITEM_NAME_GROUP)
    if grp_col != "ITEM_NAME_GROUP":
        perf = perf.rename(columns={grp_col: "ITEM_NAME_GROUP"})
    total = perf["Revenue"].sum()
    perf["Share"] = (perf["Revenue"] / total * 100).round(1)
    perf["CumulativeShare"] = perf["Share"].cumsum().round(1)
    return serialize_df(perf)

@router.get("/materials/pareto")
def get_pareto_data(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None, items: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    grp_col = _material_group_column(df)
    if df.empty or grp_col is None:
        return []
    pareto = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).reset_index()
    if grp_col != "ITEM_NAME_GROUP":
        pareto = pareto.rename(columns={grp_col: "ITEM_NAME_GROUP"})
    total = pareto["AMOUNT"].sum()
    pareto["Percentage"] = (pareto["AMOUNT"] / total * 100).round(1)
    pareto["Cumulative"] = pareto["Percentage"].cumsum().round(1)
    pareto["Class"] = pareto["Cumulative"].apply(lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C"))
    return serialize_df(pareto)

# ─── REPORTS API ───

@router.get("/reports/item-details")
def get_item_details(
    tenant_id: str = "default_elettro", 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    states: Optional[str] = None, 
    cities: Optional[str] = None, 
    customers: Optional[str] = None, 
    material_groups: Optional[str] = None, 
    fiscal_years: Optional[str] = None, 
    months: Optional[str] = None,
    items: Optional[str] = None,
):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    
    if df.empty:
        return []
        
    item_col = "ITEMNAME" if "ITEMNAME" in df.columns else None
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    
    if not item_col or not grp_col in df.columns:
        return []
        
    qty_col = "QTY" if "QTY" in df.columns else ("QUANTITY" if "QUANTITY" in df.columns else None)
    
    aggs = {
        "AMOUNT": "sum",
        "INVOICE_NO": "nunique"
    }
    if qty_col:
        aggs[qty_col] = "sum"
        
    item_rows = df.groupby([item_col, grp_col]).agg(aggs).reset_index()
    
    item_rows.rename(columns={
        item_col: "Item",
        grp_col: "Category",
        "AMOUNT": "Revenue",
        "INVOICE_NO": "Orders"
    }, inplace=True)
    
    if qty_col:
        item_rows.rename(columns={qty_col: "Quantity"}, inplace=True)
    else:
        item_rows["Quantity"] = 0
        
    return serialize_df(item_rows.sort_values("Revenue", ascending=False))


def _fy_chronological_sort_key(fy_label: str) -> tuple:
    """Sort Indian FY labels like FY24-25, FY25-26 in time order."""
    s = str(fy_label).strip().upper().replace("FY", "")
    parts = [p.strip() for p in s.split("-") if p.strip()]
    try:
        if len(parts) >= 2:
            return (int(parts[0]), int(parts[1]))
        return (int(parts[0]), 0)
    except (ValueError, TypeError, IndexError):
        return (9999, 9999)


@router.get("/reports/fy-comparison")
def get_fy_comparison(
    tenant_id: str = "default_elettro",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    customers: Optional[str] = None,
    material_groups: Optional[str] = None,
    months: Optional[str] = None,
    items: Optional[str] = None,
):
    """
    Metrics by FINANCIAL_YEAR for Reports. Uses the same filters as other report APIs but **does not**
    apply the global fiscal-year filter, so multiple FYs can appear within the selected date range.
    """
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, None, months, items)
    if df.empty:
        return {"rows": []}
    if "FINANCIAL_YEAR" not in df.columns:
        date_col = next((c for c in df.columns if str(c).upper() == "DATE"), None)
        if date_col is not None:
            df = df.copy()
            dt = pd.to_datetime(df[date_col], errors="coerce")
            df["FINANCIAL_YEAR"] = dt.apply(lambda x: calculate_fy(x) if pd.notna(x) else None)
        else:
            return {"rows": [], "message": "FINANCIAL_YEAR not available for this dataset."}
    if df.empty:
        return {"rows": []}
    amt_col = next((c for c in df.columns if str(c).upper() == "AMOUNT"), None)
    if amt_col is None:
        return {"rows": [], "message": "AMOUNT column missing."}

    fy_series = df["FINANCIAL_YEAR"].astype(str).str.strip()
    df = df.assign(_fy=fy_series)
    df = df[df["_fy"].ne("") & df["_fy"].ne("nan") & df["_fy"].ne("None")]

    if df.empty:
        return {"rows": []}

    rows_out: list = []
    for fy, part in df.groupby("_fy", sort=False):
        rev = float(pd.to_numeric(part[amt_col], errors="coerce").fillna(0).sum())
        orders = int(part["INVOICE_NO"].nunique()) if "INVOICE_NO" in part.columns else int(len(part))
        cust = int(part["CUSTOMER_NAME"].nunique()) if "CUSTOMER_NAME" in part.columns else 0
        aov = rev / orders if orders > 0 else 0.0
        rows_out.append({
            "fiscal_year": str(fy),
            "revenue": round(rev, 2),
            "orders": orders,
            "customers": cust,
            "avg_order_value": round(aov, 2),
        })

    rows_out.sort(key=lambda r: _fy_chronological_sort_key(r["fiscal_year"]))
    prev_rev: Optional[float] = None
    for r in rows_out:
        if prev_rev is not None and prev_rev > 0:
            r["revenue_yoy_pct"] = round((r["revenue"] - prev_rev) / prev_rev * 100, 1)
        else:
            r["revenue_yoy_pct"] = None
        prev_rev = r["revenue"]

    return {"rows": rows_out}


# ─── DATA EXPORT ───

@router.get("/export/data")
def export_filtered_data(
    tenant_id: str = "default_elettro",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    customers: Optional[str] = None,
    material_groups: Optional[str] = None,
    fiscal_years: Optional[str] = None, 
    months: Optional[str] = None,
    items: Optional[str] = None,
):
    """
    Export the currently filtered dataset as CSV for use by the frontend Export Data button.
    """
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)

    if df.empty:
        # Return a valid but empty CSV so the download still works
        csv_bytes = "".encode("utf-8")
    else:
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")

    filename = f"{REPORT_FILE_PREFIX}_Export_{tenant_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/export/customers-below-revenue")
def export_customers_below_revenue(
    tenant_id: str = Query("default_elettro"),
    max_revenue_inr: float = Query(
        550_000.0,
        ge=0,
        description="Include customers with total revenue at or below this INR (sum of AMOUNT only). Default 550000 = ₹5.5 L.",
    ),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    customers: Optional[str] = None,
    material_groups: Optional[str] = None,
    fiscal_years: Optional[str] = None,
    months: Optional[str] = None,
    items: Optional[str] = None,
):
    """
    CSV of one row per customer: CITY, STATE, Revenue, Orders, AvgOrder, LastOrder — customers whose
    total sales (same basis as /customers/all) are **at or below** ``max_revenue_inr`` (default ₹5.5 L).
    """
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months, items)
    _hdr = "CUSTOMER_NAME,CITY,STATE,Revenue,Orders,AvgOrder,LastOrder,MaxRevenueThreshold_INR\n"
    if df.empty or "CUSTOMER_NAME" not in df.columns or "AMOUNT" not in df.columns:
        csv_bytes = _hdr.encode("utf-8-sig")
    else:
        cust = _customer_summary_df(df)
        if cust.empty:
            csv_bytes = _hdr.encode("utf-8-sig")
        else:
            cust = cust[cust["Revenue"] <= float(max_revenue_inr)].sort_values("Revenue", ascending=True)
            cust["MaxRevenueThreshold_INR"] = float(max_revenue_inr)
            csv_bytes = cust.to_csv(index=False).encode("utf-8-sig")

    safe_max = int(max_revenue_inr) if float(max_revenue_inr) == int(float(max_revenue_inr)) else round(float(max_revenue_inr), 2)
    filename = f"{REPORT_FILE_PREFIX}_Customers_Under_{safe_max}INR_{tenant_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── INTEGRATIONS (stubs: email, Slack, BI) ───

class EmailReportRequest(BaseModel):
    report_type: str = "Executive Summary"
    recipient_email: str = ""
    tenant_id: str = "default_elettro"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/integrations/email-report")
def email_report_stub(req: EmailReportRequest):
    """Stub: in production wire to SMTP or SendGrid to email the report PDF."""
    if not req.recipient_email or "@" not in req.recipient_email:
        raise HTTPException(status_code=400, detail="Valid recipient_email required.")
    return {"ok": True, "message": "Email report is not configured. Configure SMTP or use the download button."}


# ─── ANOMALIES (for alerts / AI) ───

@router.get("/analytics/anomalies")
def get_anomalies(
    tenant_id: str = "default_elettro",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    states: Optional[str] = None,
    customers: Optional[str] = None,
    material_groups: Optional[str] = None,
    fiscal_years: Optional[str] = None,
    months: Optional[str] = None,
    items: Optional[str] = None,
    drop_threshold_pct: float = 20.0,
):
    """Returns customers or entities with revenue drop vs previous period (for alerts / dashboard)."""
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, None, customers, material_groups, fiscal_years, months, items)
    if df.empty or "CUSTOMER_NAME" not in df.columns or "DATE" not in df.columns:
        return {"anomalies": [], "period": "current"}

    # Previous period (same length)
    try:
        start_dt = pd.to_datetime(start_date) if start_date else df["DATE"].min()
        end_dt = pd.to_datetime(end_date) if end_date else df["DATE"].max()
        if len(str(end_date or "").strip()) <= 10:
            end_dt = end_dt + pd.Timedelta(days=1)
        delta = end_dt - start_dt
        prev_end = start_dt - pd.Timedelta(days=1)
        prev_start = prev_end - delta
        df_prev = get_tenant_data(tenant_id, prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d"))
        df_prev = apply_filters(df_prev, states, None, customers, material_groups, fiscal_years, months, items)
    except Exception:
        return {"anomalies": [], "period": "current"}

    if df_prev.empty:
        return {"anomalies": [], "period": "current"}

    cur = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum()
    prev = df_prev.groupby("CUSTOMER_NAME")["AMOUNT"].sum()
    common = cur.index.intersection(prev.index)
    anomalies = []
    for c in common:
        pv = float(prev.get(c, 0))
        cv = float(cur.get(c, 0))
        if pv > 0 and cv < pv:
            pct = (cv - pv) / pv * 100
            if pct <= -drop_threshold_pct:
                anomalies.append({"entity": c, "entity_type": "customer", "current_revenue": cv, "previous_revenue": pv, "change_pct": round(pct, 1)})
    anomalies.sort(key=lambda x: x["change_pct"])
    return {"anomalies": anomalies[:20], "period": "current"}
