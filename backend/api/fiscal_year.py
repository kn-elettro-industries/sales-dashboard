"""
Indian financial year: April -> March (same convention as ``sales_dates.fiscal_year_india`` / ``routes.calculate_fy``).
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

import pandas as pd


def parse_fy_label_to_apr_mar_years(fy: str) -> Optional[Tuple[int, int]]:
    """
    Parse a FY label into (calendar_year_of_april_start, calendar_year_of_march_end).

    Examples:
        FY25-26, 25-26 -> (2025, 2026)  => Apr 2025 through Mar 2026
        FY2024-2025     -> (2024, 2025)
    """
    if not fy or not str(fy).strip():
        return None
    raw = str(fy).strip().upper().replace("FY", "").strip()
    m = re.match(r"^(\d{2,4})\s*[-/]\s*(\d{2,4})$", raw)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    y_start = int(a) if len(a) > 2 else 2000 + int(a)
    y_end = int(b) if len(b) > 2 else 2000 + int(b)
    if len(a) == 2 and len(b) == 2 and y_end < y_start:
        y_end += 100
    if y_end < y_start:
        return None
    return (y_start, y_end)


def fy_selection_to_timeline_month_labels(fy_labels: List[str]) -> Optional[Tuple[str, str]]:
    """
    Earliest April to latest March across selected FYs; month-only labels for PDF cover.
    Returns e.g. ('Apr 2025', 'Mar 2026') for FY25-26.
    """
    pairs: List[Tuple[int, int]] = []
    for fy in fy_labels:
        p = parse_fy_label_to_apr_mar_years(fy)
        if p:
            pairs.append(p)
    if not pairs:
        return None
    apr_year = min(p[0] for p in pairs)
    mar_year = max(p[1] for p in pairs)
    left = pd.Timestamp(year=apr_year, month=4, day=1).strftime("%b %Y")
    right = pd.Timestamp(year=mar_year, month=3, day=1).strftime("%b %Y")
    return (left, right)
