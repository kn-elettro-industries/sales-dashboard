"""
Single source of truth for invoice DATE parsing and Indian FY labels.

Used by: upload, DB read enrichment, PDF/report helpers. Keeps MONTH/FINANCIAL_YEAR
aligned with DATE and avoids US-centric month-first ambiguity for DD/MM files.
"""
from __future__ import annotations

import pandas as pd


def parse_invoice_dates(series: pd.Series) -> pd.Series:
    """
    Parse invoice/voucher dates for the Indian sales context.

    - ``dayfirst=True`` so ``06/03/2026`` reads as 6 March, not June (when ambiguous).
    - ISO ``YYYY-MM-DD`` and Excel datetimes remain unambiguous.
    - Timezone-aware values are converted to naive local calendar dates (strip tz).
    """
    out = pd.to_datetime(series, errors="coerce", dayfirst=True)
    if hasattr(out.dtype, "tz") and getattr(out.dtype, "tz", None) is not None:
        out = out.dt.tz_localize(None)
    return out


def fiscal_year_india(date) -> str:
    """Indian FY label April→March, e.g. Apr 2025–Mar 2026 → ``FY25-26``."""
    if date is None:
        return "UNKNOWN"
    try:
        if pd.isna(date):
            return "UNKNOWN"
    except (TypeError, ValueError):
        return "UNKNOWN"
    try:
        d = pd.to_datetime(date)
        if pd.isna(d):
            return "UNKNOWN"
    except Exception:
        return "UNKNOWN"
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    return f"FY{(d.year - 1) % 100}-{d.year % 100}"


# Calendar month bucket stored in the MONTH column. ISO ``YYYY-MM`` avoids confusion with
# legacy ``MON-YY`` labels (e.g. ``JUN-26`` was often read as "June 26" instead of June 2026).
MONTH_BUCKET_STRFTIME = "%Y-%m"


def parse_month_label_for_sort(val):
    """
    Parse MONTH bucket for chronological ordering. Supports:
    - ``YYYY-MM`` (current)
    - Legacy ``MON-YY`` / ``JUN-26`` (month + 2-digit year from older exports)
    """
    if val is None:
        return pd.NaT
    try:
        if pd.isna(val):
            return pd.NaT
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if not s:
        return pd.NaT
    dt = pd.to_datetime(s, format="%Y-%m", errors="coerce")
    if pd.notna(dt):
        return dt
    try:
        dt = pd.to_datetime(s.title(), format="%b-%y", errors="coerce")
    except Exception:
        dt = pd.NaT
    if pd.notna(dt):
        return dt
    return pd.to_datetime(s, errors="coerce")


def month_filter_match_keys(token: str) -> set:
    """
    Expand one month filter token to all MONTH column values that mean the same calendar month
    (ISO ``2026-06`` vs legacy ``JUN-26``) so saved filters keep working after the format change.
    """
    s = (token or "").strip()
    if not s:
        return set()
    dt = parse_month_label_for_sort(s)
    if pd.isna(dt):
        return {s}
    iso = dt.strftime(MONTH_BUCKET_STRFTIME)
    legacy = dt.strftime("%b-%y").upper()
    return {iso, legacy, s}
