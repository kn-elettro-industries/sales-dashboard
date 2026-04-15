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
