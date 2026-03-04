from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import pandas as pd
import json

from .db import get_tenant_data

router = APIRouter()

def serialize_df(df: pd.DataFrame) -> list:
    """Helper to cleanly serialize pandas dataframes to JSON."""
    return json.loads(df.to_json(orient="records", date_format="iso"))

@router.get("/metrics/summary")
def get_kpi_summary(tenant_id: str = "default_elettro"):
    """Returns top-level KPIs: Total Revenue, Orders, Unique Customers."""
    df = get_tenant_data(tenant_id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found for this tenant.")
        
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
def get_sales_trend(tenant_id: str = "default_elettro"):
    """Returns monthly sales trend data."""
    df = get_tenant_data(tenant_id)
    if df.empty or "DATE" not in df.columns or "AMOUNT" not in df.columns:
        return []
        
    trend = df.groupby(pd.Grouper(key="DATE", freq="M"))["AMOUNT"].sum().reset_index()
    trend["DATE"] = trend["DATE"].dt.strftime("%Y-%m")
    
    return serialize_df(trend)

@router.get("/charts/material-groups")
def get_material_groups(tenant_id: str = "default_elettro", limit: int = 10):
    """Returns top material groups by revenue."""
    df = get_tenant_data(tenant_id)
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    
    if df.empty or grp_col not in df.columns or "AMOUNT" not in df.columns:
        return []
        
    merged = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(limit).reset_index()
    return serialize_df(merged)

@router.get("/charts/top-customers")
def get_top_customers(tenant_id: str = "default_elettro", limit: int = 10):
    """Returns top customers by revenue."""
    df = get_tenant_data(tenant_id)
    
    if df.empty or "CUSTOMER_NAME" not in df.columns or "AMOUNT" not in df.columns:
        return []
        
    merged = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(limit).reset_index()
    return serialize_df(merged)
