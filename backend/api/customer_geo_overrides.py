"""Canonical CITY/STATE fixes for known CUSTOMER_NAME ↔ geography mismatches."""

from __future__ import annotations

import pandas as pd

# Normalized customer key (strip + lower) -> (CITY, STATE) as stored in analytics
CUSTOMER_GEO_OVERRIDES: dict[str, tuple[str, str]] = {
    "bharat trading corporation": ("Pune", "Maharashtra"),
    # Add more rows here when audits find bad CITY/STATE in source or master data.
}


def apply_customer_geo_overrides(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "CUSTOMER_NAME" not in df.columns:
        return df
    df = df.copy()
    if "CITY" not in df.columns:
        df["CITY"] = ""
    if "STATE" not in df.columns:
        df["STATE"] = ""

    def norm(name: object) -> str:
        return str(name).strip().lower()

    for key, (city, state) in CUSTOMER_GEO_OVERRIDES.items():
        mask = df["CUSTOMER_NAME"].map(norm) == key
        if mask.any():
            df.loc[mask, "CITY"] = city
            df.loc[mask, "STATE"] = state
    return df
