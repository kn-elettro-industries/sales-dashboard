"""Canonical CUSTOMER_NAME, CITY, and STATE fixes for known data-entry mismatches."""

from __future__ import annotations

import re

import pandas as pd

# Normalized customer key (strip + lower) -> canonical CUSTOMER_NAME as shown in the app
CUSTOMER_NAME_CANONICAL: dict[str, str] = {
    "anina tools & electricals; n": "ANINA TOOLS & ELECTRICALS",
}


# Director groups: multiple billing entities run by the same director are merged
# into one customer so revenue, orders, filters, and reports roll up together.
# Key   -> canonical merged name as it should appear in the app.
# Value -> list of source CUSTOMER_NAME variants that should be rewritten to the
#          key. Matching is case-insensitive on a normalized form (stripped, all
#          punctuation/dots/whitespace collapsed), so minor spelling differences
#          like "R.D ASSOCIATES" vs "R D ASSOCIATES" vs "RD ASSOCIATES" all hit.
CUSTOMER_DIRECTOR_GROUPS: dict[str, list[str]] = {
    # DB names: 'SINGHI ELECTRIC CO'  +  'P B ENTERPRISE'
    "SINGHI ELECTRIC CO / P B ENTERPRISE": [
        "SINGHI ELECTRIC CO",
        "SINGHI ELECTRIC CO.",
        "SINGHI ELECTRIC COMPANY",
        "P B ENTERPRISE",
        "P B ENTERPRISES",
        "P.B ENTERPRISE",
        "P.B ENTERPRISES",
        "P.B. ENTERPRISE",
        "P.B. ENTERPRISES",
        "PB ENTERPRISE",
        "PB ENTERPRISES",
    ],
    # DB names: 'R.D.ASSOCIATES'  +  'V.V.ENGINEERS'
    "R.D. ASSOCIATES / V.V. ENGINEERS": [
        "R.D.ASSOCIATES",
        "R.D ASSOCIATES",
        "R D ASSOCIATES",
        "RD ASSOCIATES",
        "R.D. ASSOCIATES",
        "V.V.ENGINEERS",
        "V.V ENGINEERS",
        "V V ENGINEERS",
        "VV ENGINEERS",
        "V.V. ENGINEERS",
    ],
    # DB names: 'SHAH ENTERPRISES'  +  'LASER ENTERPRISES'
    "SHAH ENTERPRISES / LASER ENTERPRISES": [
        "SHAH ENTERPRISES",
        "LASER ENTERPRISES",
    ],
}


def _norm_customer_key(name: object) -> str:
    """Normalize for matching: lowercase, strip, collapse whitespace, drop dots."""
    if name is None:
        return ""
    s = str(name).strip().lower()
    s = s.replace(".", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Pre-built lookup: normalized alias -> canonical merged name
_DIRECTOR_GROUP_ALIAS_MAP: dict[str, str] = {
    _norm_customer_key(alias): canonical
    for canonical, aliases in CUSTOMER_DIRECTOR_GROUPS.items()
    for alias in aliases
}

# Normalized customer key (strip + lower) -> (CITY, STATE) as stored in analytics
CUSTOMER_GEO_OVERRIDES: dict[str, tuple[str, str]] = {
    "bharat trading corporation": ("Pune", "Maharashtra"),
    # Add more rows here when audits find bad CITY/STATE in source or master data.
}


def apply_customer_name_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Merge duplicate/wrong spellings of the same customer into one canonical name."""
    if df is None or df.empty or "CUSTOMER_NAME" not in df.columns:
        return df
    if not CUSTOMER_NAME_CANONICAL:
        return df
    df = df.copy()

    def norm(name: object) -> str:
        return str(name).strip().lower()

    for bad_key, canonical in CUSTOMER_NAME_CANONICAL.items():
        mask = df["CUSTOMER_NAME"].map(norm) == bad_key
        if mask.any():
            df.loc[mask, "CUSTOMER_NAME"] = canonical
    return df


def apply_customer_director_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Merge sibling companies (same director, multiple billing entities) into
    a single combined CUSTOMER_NAME so they roll up together everywhere in the
    app (KPIs, filter lists, PDFs, charts)."""
    if df is None or df.empty or "CUSTOMER_NAME" not in df.columns:
        return df
    if not _DIRECTOR_GROUP_ALIAS_MAP:
        return df
    df = df.copy()
    norm_col = df["CUSTOMER_NAME"].map(_norm_customer_key)
    mapped = norm_col.map(_DIRECTOR_GROUP_ALIAS_MAP)
    mask = mapped.notna()
    if mask.any():
        df.loc[mask, "CUSTOMER_NAME"] = mapped[mask]
    return df


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
