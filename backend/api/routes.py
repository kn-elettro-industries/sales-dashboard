from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Response
from pydantic import BaseModel
from typing import Optional, List
import logging
import pandas as pd
import json
import io
import os
from datetime import datetime, timedelta

from .db import get_tenant_data

router = APIRouter()

EXCLUDED_MATERIAL_GROUPS = {
    # Common non-sales buckets that should not appear in filters/analytics
    "SALES ACCOUNTS",
    "SALES ACCOUNT",
    "SERVICES",
    "SERVICE",
    "FINISHED GOODS",
    "FINISHED GOOD",
    # Additional exclusions (panel, packing, raw material, etc.)
    "PANEL DOOR SWITCH",
    "SCREW TYPE TIE MOUNT",
    "DOCUMENT HOLDER",
    "PACKING MATERIALS",
    "PACKING MATERIAL",
    "AIR VENT FELT",
    "SMALL BRASS CONNECTOR 9020E/9040E",
    "RAW-MATERIAL",
    "RAW MATERIAL",
}


# ─── AUTH (minimal: mock login + role for UI) ───

class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


@router.post("/auth/login")
def auth_login(req: LoginRequest):
    """Mock login: accepts any credentials. In production replace with real auth."""
    role = os.environ.get("ELETTRO_DEFAULT_ROLE", "viewer")
    return {"user": req.username or "user", "role": role, "tenant": "default_elettro"}


@router.get("/auth/me")
def auth_me():
    """Placeholder: in production validate session/JWT and return current user."""
    return {"user": None, "role": None}

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

def _material_group_column(df: pd.DataFrame):
    """Return the material group column name if present (any common casing)."""
    candidates = [
        "ITEM_NAME_GROUP", "MATERIALGROUP", "MATERIAL_GROUP", "PRODUCT_CATEGORY", "CATEGORY", "ITEM_GROUP",
        "item_name_group", "materialgroup", "material_group", "product_category", "category", "item_group",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None

def _exclude_material_groups(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove non-sales material groups from analytics + filters.
    Applied in upload ETL and read-time (apply_filters / get_filter_options).
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
    return df[~norm.isin(EXCLUDED_MATERIAL_GROUPS)]

def apply_filters(df: pd.DataFrame, states=None, cities=None, customers=None, material_groups=None, fiscal_years=None, months=None) -> pd.DataFrame:
    """Apply granular filters to a dataframe. Ignores empty or whitespace-only filter strings."""
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if df.empty:
        return df
    df = _exclude_material_groups(df)
    if states and str(states).strip():
        state_list = [s.strip() for s in states.split(",") if s.strip()]
        if "STATE" in df.columns and state_list:
            df = df[df["STATE"].isin(state_list)]
    if cities and str(cities).strip():
        city_list = [c.strip() for c in cities.split(",") if c.strip()]
        if "CITY" in df.columns and city_list:
            df = df[df["CITY"].isin(city_list)]
    if customers and str(customers).strip():
        cust_list = [c.strip() for c in customers.split(",") if c.strip()]
        if "CUSTOMER_NAME" in df.columns and cust_list:
            df = df[df["CUSTOMER_NAME"].isin(cust_list)]
    if material_groups and str(material_groups).strip():
        mg_list = [m.strip() for m in material_groups.split(",") if m.strip()]
        grp_col = _material_group_column(df)
        if grp_col and mg_list:
            df = df[df[grp_col].isin(mg_list)]
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
    return df

# Single canonical placeholder for missing state/region (avoids "State Not Found" vs "STATE NOT FOUND ⚠️")
STATE_PLACEHOLDER = "State Not Found"

# Helper functions adapted from etl_pipeline
def standardize(df):
    if df.empty: return df
    df.columns = df.columns.str.strip().str.upper()
    df.columns = df.columns.str.replace(".", "", regex=False).str.replace(" ", "_")
    for col in df.columns:
        col_upper = col.upper()
        if any(x in col_upper for x in ["CITY", "TOWN", "DISTRICT", "LOCATION"]) and "CITY" not in df.columns:
            df.rename(columns={col: "CITY"}, inplace=True)
        elif any(x in col_upper for x in ["STATE", "REGION", "PROVINCE", "TERRITORY"]) and "STATE" not in df.columns:
            df.rename(columns={col: "STATE"}, inplace=True)
        elif any(x in col_upper for x in ["CUSTOMER", "PARTY", "BILL TO"]) and "CUSTOMER_NAME" not in df.columns:
            df.rename(columns={col: "CUSTOMER_NAME"}, inplace=True)
        elif any(x in col_upper for x in ["ITEM", "MATERIAL", "PRODUCT"]) and "ITEMNAME" not in df.columns and "GROUP" not in col_upper:
            df.rename(columns={col: "ITEMNAME"}, inplace=True)
        elif (col_upper == "NO" or any(x in col_upper for x in ["INVOICE", "BILL_NO"])) and "INVOICE_NO" not in df.columns and "DATE" not in col_upper:
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
    if pd.isna(date): return "UNKNOWN"
    if date.month >= 4: return f"FY{date.year % 100}-{(date.year + 1) % 100}"
    else: return f"FY{(date.year - 1) % 100}-{date.year % 100}"

# ─── UPLOAD PIPELINE ───

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

        # 2. Enrich Dates
        if "DATE" in df.columns:
            df["DATE"] = pd.to_datetime(df["DATE"], errors='coerce')
            df["FINANCIAL_YEAR"] = df["DATE"].apply(calculate_fy)
            df["MONTH"] = df["DATE"].dt.strftime("%b-%y").str.upper()

        if "CITY" not in df.columns: df["CITY"] = "City Not Found"
        if "STATE" not in df.columns: df["STATE"] = STATE_PLACEHOLDER

        # 2.5 Exclude non-sales material groups (ETL rule)
        df = _exclude_material_groups(df)

        # 3. Insert into database
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
            df = _exclude_material_groups(df)
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
    months: Optional[str] = None
):
    try:
        from .pdf_generator import generate_pdf_report, generate_dynamic_pdf_report, generate_distributor_strategy_pdf
        df = get_tenant_data(tenant_id, start_date, end_date)
        df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)

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

            # If user didn't select a month, default the distributor report to the previous month
            # (most common usage: generate in March for Feb).
            #
            # Note: the UI often sets a wide date range (e.g. full FY). We still want the default
            # month behavior when `months` isn't selected.
            effective_months = months
            if (not months or not str(months).strip()) and ("MONTH" in df.columns):
                prev_month_day = (datetime.now().replace(day=1) - timedelta(days=1))
                prev_month_label = prev_month_day.strftime("%b-%y").upper()
                prev_df = df[df["MONTH"].astype(str).str.upper() == prev_month_label]
                if not prev_df.empty:
                    df = prev_df
                    effective_months = prev_month_label

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
            pdf_bytes = generate_distributor_strategy_pdf(df, customer_name, analysis_period)
            entity_name = str(customer_name).replace(" ", "_")
        else:
            pdf_bytes = generate_pdf_report(
                df, report_type, tenant_id, specific_entity,
                filter_customer, filter_state, filter_material
            )
            entity_name = str(specific_entity).replace(' ', '_') if specific_entity and specific_entity != "All" else "Summary"

        filename = f"ELETTRO_{report_type.replace(' ', '_')}_{entity_name}_{tenant_id}.pdf"

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
    spec: DynamicReportSpec


@router.post("/reports/dynamic")
def download_dynamic_report(req: DynamicReportRequest):
    try:
        from .pdf_generator import generate_dynamic_pdf_report
        df = get_tenant_data(req.tenant_id, req.start_date, req.end_date)
        df = apply_filters(df, req.states, req.cities, req.customers, req.material_groups, req.fiscal_years, req.months)
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
        )

        safe_title = (req.spec.title or "Dynamic_Report").replace(" ", "_")
        filename = f"ELETTRO_Dynamic_{safe_title}_{req.tenant_id}.pdf"
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
        df = _exclude_material_groups(df)
        response_text = chat_process_query(req.query, df)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")

# ─── FILTER OPTIONS ───

@router.get("/filters/options")
def get_filter_options(tenant_id: str = "default_elettro"):
    """Returns all unique filter values for the sidebar multi-selects."""
    df = get_tenant_data(tenant_id)
    if df.empty:
        return {"states": [], "cities": [], "customers": [], "material_groups": [], "fiscal_years": [], "months": []}

    df = _exclude_material_groups(df)
    # Exclude "State Not Found" / "STATE NOT FOUND ⚠️" from filter options so only real states appear (no duplicate region placeholders)
    raw_states = df["STATE"].dropna().unique().tolist() if "STATE" in df.columns else []
    states = sorted([s for s in raw_states if str(s).strip() and "NOT FOUND" not in str(s).upper()])
    cities = sorted([c for c in df["CITY"].dropna().unique().tolist() if "NOT FOUND" not in str(c).upper() and "UNKNOWN" not in str(c).upper()]) if "CITY" in df.columns else []
    customers = sorted(df["CUSTOMER_NAME"].dropna().unique().tolist()) if "CUSTOMER_NAME" in df.columns else []
    
    grp_col = _material_group_column(df)
    material_groups = sorted(df[grp_col].dropna().unique().tolist()) if grp_col else []
    # Final safeguard: ensure excluded groups never appear in the UI list, even if they exist in raw data.
    def _norm_group(v: object) -> str:
        s = str(v).replace("\u00a0", " ")
        s = " ".join(s.split())  # collapse all whitespace
        return s.strip().upper()

    material_groups = [g for g in material_groups if _norm_group(g) not in EXCLUDED_MATERIAL_GROUPS]
    
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
    
    return {
        "states": states,
        "cities": cities,
        "customers": customers,
        "material_groups": material_groups,
        "fiscal_years": fiscal_years,
        "months": months
    }

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
    trend_limit: int = 36,
    material_limit: int = 10,
    top_customers_limit: int = 10,
    goal_revenue: Optional[float] = None,
    goal_orders: Optional[int] = None,
):
    """Single endpoint: summary + trend + material groups + top customers + previous-period comparison + optional goals."""
    def _empty(msg: str):
        return {
            "summary": {"revenue": 0, "orders": 0, "customers": 0, "average_order_value": 0},
            "previous_summary": None,
            "comparison": None,
            "goals": None,
            "trend": [],
            "material_groups": [],
            "top_customers": [],
            "message": msg,
        }
    try:
        df = get_tenant_data(tenant_id, start_date, end_date)
        df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
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
                df_prev = apply_filters(df_prev, states, cities, customers, material_groups, fiscal_years, months)
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

        goals = None
        if goal_revenue is not None and goal_revenue > 0:
            goals = {"revenue_target": goal_revenue, "revenue_achievement_pct": round(revenue / goal_revenue * 100, 1)}
        if goal_orders is not None and goal_orders > 0:
            goals = goals or {}
            goals["orders_target"] = goal_orders
            goals["orders_achievement_pct"] = round(orders / goal_orders * 100, 1)

        trend = []
        date_col, amount_col = _date_amount_columns(df)
        if date_col and amount_col:
            df_t = df.copy()
            df_t[date_col] = pd.to_datetime(df_t[date_col], errors="coerce")
            df_t = df_t.dropna(subset=[date_col])
            if not df_t.empty:
                t = df_t.groupby(pd.Grouper(key=date_col, freq="M"))[amount_col].sum().reset_index()
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
            material_groups_list = serialize_df(mg)

        top_customers_list = []
        if "CUSTOMER_NAME" in df.columns and amt_col is not None:
            tc = df.groupby("CUSTOMER_NAME")[amt_col].sum().sort_values(ascending=False).head(top_customers_limit).reset_index()
            top_customers_list = serialize_df(tc)

        return {
            "summary": summary,
            "previous_summary": previous_summary,
            "comparison": comparison,
            "goals": goals,
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
def get_kpi_summary(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
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
def get_sales_trend(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
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
            trend = df_t.groupby(pd.Grouper(key=date_col, freq="M"))[amount_col].sum().reset_index()
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
def get_material_groups(tenant_id: str = "default_elettro", limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    if df.empty or grp_col not in df.columns:
        return []
    merged = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(limit).reset_index()
    return serialize_df(merged)

@router.get("/charts/top-customers")
def get_top_customers(tenant_id: str = "default_elettro", limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    if df.empty or "CUSTOMER_NAME" not in df.columns:
        return []
    merged = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(limit).reset_index()
    return serialize_df(merged)

# ─── SALES & GROWTH ───

@router.get("/sales/monthly")
def get_monthly_sales(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
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
def get_daily_sales(tenant_id: str = "default_elettro", days: int = 30, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    if df.empty or "DATE" not in df.columns:
        return []
    df["DAY"] = df["DATE"].dt.strftime("%Y-%m-%d")
    daily = df.groupby("DAY").agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique")
    ).sort_index().tail(days).reset_index()
    return serialize_df(daily)

@router.get("/sales/growth")
def get_growth_metrics(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
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
def get_all_customers(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    if df.empty or "CUSTOMER_NAME" not in df.columns:
        return []
    cust = df.groupby("CUSTOMER_NAME").agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique"),
        AvgOrder=("AMOUNT", "mean"),
        LastOrder=("DATE", "max")
    ).sort_values("Revenue", ascending=False).reset_index()
    cust["LastOrder"] = cust["LastOrder"].dt.strftime("%Y-%m-%d")
    return serialize_df(cust)

@router.get("/customers/rfm")
def get_rfm_segments(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    if df.empty or "CUSTOMER_NAME" not in df.columns or "DATE" not in df.columns:
        return []
    max_date = df["DATE"].max()
    rfm = df.groupby("CUSTOMER_NAME").agg(
        Recency=("DATE", lambda x: (max_date - x.max()).days),
        Frequency=("INVOICE_NO", "nunique"),
        Monetary=("AMOUNT", "sum")
    ).reset_index()
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
def get_state_data(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    if df.empty or "STATE" not in df.columns:
        return []
    # Exclude placeholder so map/region only show real states (avoids "no state found" / duplicate region)
    df = df[~df["STATE"].astype(str).str.upper().str.contains("NOT FOUND", na=False)]
    if df.empty:
        return []
    state = df.groupby("STATE").agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique"),
        Customers=("CUSTOMER_NAME", "nunique")
    ).sort_values("Revenue", ascending=False).reset_index()
    
    # Add market share
    total_rev = state["Revenue"].sum()
    state["MarketShare"] = (state["Revenue"] / total_rev * 100).round(1) if total_rev > 0 else 0
    state["Revenue_Cr"] = (state["Revenue"] / 10000000).round(2)
    
    # Add lat/lon from geo_data
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    try:
        from assets.geo_data import STATE_COORDS
        state["lat"] = state["STATE"].map(lambda x: STATE_COORDS.get(x.title(), [20.5937, 78.9629])[0])
        state["lon"] = state["STATE"].map(lambda x: STATE_COORDS.get(x.title(), [20.5937, 78.9629])[1])
    except:
        state["lat"] = 20.5937
        state["lon"] = 78.9629
    
    return serialize_df(state)

@router.get("/geographic/cities")
def get_city_data(tenant_id: str = "default_elettro", limit: int = 20, start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    col = "CITY" if "CITY" in df.columns else "STATE"
    if df.empty or col not in df.columns:
        return []
    city = df.groupby(col).agg(
        Revenue=("AMOUNT", "sum"),
        Customers=("CUSTOMER_NAME", "nunique")
    ).sort_values("Revenue", ascending=False).head(limit).reset_index()
    return serialize_df(city)

# ─── MATERIAL PERFORMANCE ───

@router.get("/materials/performance")
def get_material_performance(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    if df.empty or grp_col not in df.columns:
        return []
    perf = df.groupby(grp_col).agg(
        Revenue=("AMOUNT", "sum"),
        Orders=("INVOICE_NO", "nunique"),
        Customers=("CUSTOMER_NAME", "nunique"),
        AvgPrice=("AMOUNT", "mean")
    ).sort_values("Revenue", ascending=False).reset_index()
    total = perf["Revenue"].sum()
    perf["Share"] = (perf["Revenue"] / total * 100).round(1)
    perf["CumulativeShare"] = perf["Share"].cumsum().round(1)
    return serialize_df(perf)

@router.get("/materials/pareto")
def get_pareto_data(tenant_id: str = "default_elettro", start_date: Optional[str] = None, end_date: Optional[str] = None, states: Optional[str] = None, cities: Optional[str] = None, customers: Optional[str] = None, material_groups: Optional[str] = None, fiscal_years: Optional[str] = None, months: Optional[str] = None):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    if df.empty or grp_col not in df.columns:
        return []
    pareto = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).reset_index()
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
    months: Optional[str] = None
):
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)
    
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
        
    items = df.groupby([item_col, grp_col]).agg(aggs).reset_index()
    
    items.rename(columns={
        item_col: "Item",
        grp_col: "Category",
        "AMOUNT": "Revenue",
        "INVOICE_NO": "Orders"
    }, inplace=True)
    
    if qty_col:
        items.rename(columns={qty_col: "Quantity"}, inplace=True)
    else:
        items["Quantity"] = 0
        
    return serialize_df(items.sort_values("Revenue", ascending=False))


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
):
    """
    Export the currently filtered dataset as CSV for use by the frontend Export Data button.
    """
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, cities, customers, material_groups, fiscal_years, months)

    if df.empty:
        # Return a valid but empty CSV so the download still works
        csv_bytes = "".encode("utf-8")
    else:
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")

    filename = f"ELETTRO_Export_{tenant_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
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
    drop_threshold_pct: float = 20.0,
):
    """Returns customers or entities with revenue drop vs previous period (for alerts / dashboard)."""
    df = get_tenant_data(tenant_id, start_date, end_date)
    df = apply_filters(df, states, None, customers, material_groups, fiscal_years, months)
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
        df_prev = apply_filters(df_prev, states, None, customers, material_groups, fiscal_years, months)
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
