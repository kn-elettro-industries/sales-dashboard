"""
Single source of truth for invoice DATE parsing and Indian FY labels.

Used by: upload, DB read enrichment, PDF/report helpers. Keeps MONTH/FINANCIAL_YEAR
aligned with DATE and avoids US-centric month-first ambiguity for DD/MM files.
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

# Unambiguous ISO date at start of string (optional time after T)
_RE_ISO_YMD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
# Numeric dates with day first: 06-04-2026 = 6 April (India), not 4 June.
# Pandas often parses 06-04-2026 as June 4 even with dayfirst=True — handle explicitly.
_RE_DMY_NUMERIC = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})")


def _strip_tz_naive(ts: pd.Timestamp) -> pd.Timestamp:
    if ts is None or pd.isna(ts):
        return ts
    if getattr(ts, "tzinfo", None) is not None or getattr(ts, "tz", None) is not None:
        try:
            return ts.tz_convert("UTC").tz_localize(None)
        except Exception:
            try:
                return ts.tz_localize(None)
            except Exception:
                return ts
    return ts


def _parse_invoice_date_scalar(val):
    """Parse one cell: prefer India DD-MM-YYYY / DD/MM/YYYY for ambiguous numeric strings."""
    if val is None:
        return pd.NaT
    try:
        if pd.isna(val):
            return pd.NaT
    except (TypeError, ValueError):
        pass

    if isinstance(val, pd.Timestamp):
        return _strip_tz_naive(val)
    if isinstance(val, datetime):
        return _strip_tz_naive(pd.Timestamp(val))

    if isinstance(val, (int, float)) and not isinstance(val, bool):
        try:
            if pd.isna(val):
                return pd.NaT
        except Exception:
            pass
        fv = float(val)
        # Excel serial (typical range for 2000–2040)
        if 30000 < fv < 120000:
            dt = pd.to_datetime(fv, unit="d", origin="1899-12-30", errors="coerce")
            if pd.notna(dt):
                return _strip_tz_naive(dt)
        return _strip_tz_naive(pd.to_datetime(val, errors="coerce", dayfirst=True))

    st = str(val).strip()
    if not st or st.lower() in ("nat", "none", "nan"):
        return pd.NaT

    m = _RE_ISO_YMD.match(st)
    if m:
        return pd.to_datetime(st[:10], format="%Y-%m-%d", errors="coerce")

    m = _RE_DMY_NUMERIC.match(st)
    if m:
        day_s, month_s, year_s = m.group(1), m.group(2), m.group(3)
        try:
            day, month, year = int(day_s), int(month_s), int(year_s)
            return pd.Timestamp(year=year, month=month, day=day)
        except (ValueError, OverflowError):
            return pd.NaT

    out = pd.to_datetime(st, errors="coerce", dayfirst=True)
    return _strip_tz_naive(out) if pd.notna(out) else pd.NaT


def parse_invoice_dates(series: pd.Series) -> pd.Series:
    """
    Parse invoice/voucher dates for the Indian sales context.

    - **Explicit DD-MM-YYYY / DD/MM/YYYY** for strings like ``06-04-2026`` (6 April), avoiding
      pandas/ dateutil interpreting them as **June 4** (month-first).
    - **ISO YYYY-MM-DD** at the start of the string.
    - **dayfirst=True** fallback for other ambiguous strings.
    - Timezone-aware values are converted to naive local calendar dates.
    """
    out = series.map(_parse_invoice_date_scalar)
    if not isinstance(out, pd.Series):
        out = pd.Series(out, index=series.index)
    out = pd.to_datetime(out, errors="coerce")
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
