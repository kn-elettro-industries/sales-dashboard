import pandas as pd
from datetime import datetime
import os
import tempfile
import gc
import numpy as np
from typing import Dict, List, Optional

from .fiscal_year import fy_selection_to_timeline_month_labels, parse_fy_label_to_apr_mar_years

# ── fpdf2 guard ───────────────────────────────────────────────────────────────
# fpdf and fpdf2 share the same module name. Force fpdf2 2.x.
import fpdf as _fpdf_pkg
_fpdf_ver = getattr(_fpdf_pkg, "__version__", "0")
if not _fpdf_ver.startswith("2"):
    raise ImportError(
        f"fpdf2 2.x required but got fpdf version '{_fpdf_ver}'. "
        "Run: pip uninstall -y fpdf && pip install fpdf2"
    )
from fpdf import FPDF
# ─────────────────────────────────────────────────────────────────────────────

# matplotlib is NOT imported here — loaded lazily inside PDF functions only.
# This saves ~80 MB of RAM at server startup.


def _pdf_to_bytes(pdf: FPDF) -> bytes:
    """Safely extract PDF bytes from any fpdf/fpdf2 version."""
    try:
        raw = pdf.output()
        if isinstance(raw, (bytes, bytearray)):
            return bytes(raw)
        return raw.encode("latin-1")
    except TypeError:
        raw = pdf.output(dest="S")
        if isinstance(raw, (bytes, bytearray)):
            return bytes(raw)
        return raw.encode("latin-1")

def format_currency_pdf(value):
    """
    Human-friendly INR formatting for PDFs using Indian-style scales.
    - >= 1 Cr: Rs. X.XX Cr
    - >= 1 Lakh: Rs. X.XX L
    - >= 1,000: Rs. XX.X K
    - else: Rs. X
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "Rs. 0"

    abs_v = abs(v)
    if abs_v >= 1e7:  # Crore
        return f"Rs. {v / 1e7:,.2f} Cr"
    if abs_v >= 1e5:  # Lakh
        return f"Rs. {v / 1e5:,.2f} L"
    if abs_v >= 1e3:  # Thousand
        return f"Rs. {v / 1e3:,.1f} K"
    return f"Rs. {v:,.0f}"

def _pdf_text(value: object) -> str:
    """
    FPDF (py-fpdf) is latin-1 based. Sanitize dynamic text coming from data so PDF output
    never crashes on unicode characters (e.g. "→").
    """
    s = "" if value is None else str(value)
    replacements = {
        "→": "->",
        "₹": "Rs.",
        "\u2014": " - ",  # em dash (not in latin-1; was showing as ? in PDFs)
        "\u2013": "-",  # en dash
        "–": "-",
        "-": "-",
        "\u2026": "...",  # ellipsis
        "“": "\"",
        "”": "\"",
        "’": "'",
        "•": "-",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _split_csv_param(s: Optional[str]) -> list:
    if not s or not str(s).strip():
        return []
    return [p.strip() for p in str(s).split(",") if p.strip()]


def _sort_fy_labels_chronologically(fy_labels: List[str]) -> List[str]:
    """Oldest Indian FY first. Labels that do not parse sort last."""

    def _key(fy: str):
        p = parse_fy_label_to_apr_mar_years(fy)
        return (p[0], p[1]) if p else (9999, 9999)

    return sorted([f for f in fy_labels if f and str(f).strip()], key=_key)


def _ensure_financial_year_column(df: pd.DataFrame) -> pd.DataFrame:
    """Match apply_filters / FY comparison: derive FINANCIAL_YEAR from DATE when missing."""
    if df.empty or "FINANCIAL_YEAR" in df.columns:
        return df
    if "DATE" not in df.columns:
        return df
    from .sales_dates import parse_invoice_dates, fiscal_year_india

    out = df.copy()
    dt = parse_invoice_dates(out["DATE"])
    out["FINANCIAL_YEAR"] = dt.apply(lambda x: fiscal_year_india(x) if pd.notna(x) else None)
    return out


def _rev_yoy_pct(prev_rev: float, curr_rev: float) -> str:
    if prev_rev > 0:
        return f"{((curr_rev - prev_rev) / prev_rev * 100.0):+.1f}%"
    if curr_rev > 0:
        return "new"
    return "—"


def _pdf_remaining_mm(pdf: FPDF) -> float:
    """Vertical space left above the bottom margin (mm)."""
    return float(pdf.h - pdf.b_margin - pdf.get_y())


def _pdf_need_space(pdf: FPDF, min_height_mm: float) -> None:
    """Start a new page if less than ``min_height_mm`` remains (avoids images/tables overlapping the footer)."""
    if min_height_mm <= 0:
        return
    if pdf.get_y() + min_height_mm > pdf.h - pdf.b_margin:
        pdf.add_page()


def _pdf_section_rule(pdf: FPDF) -> None:
    """Light separator between major sections."""
    pdf.ln(3)
    pdf.set_draw_color(210, 210, 210)
    y = pdf.get_y()
    pdf.line(10, y, 200, y)
    pdf.ln(5)


def _pdf_draw_aggregate_material_mix_table(
    pdf: FPDF,
    df: pd.DataFrame,
    grp_col: str,
    total_rev: float,
    max_rows: int = 9,
) -> None:
    """Single-period product / material mix: revenue + share of total."""
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(218, 165, 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 8, "#", 1, 0, "C", True)
    pdf.cell(115, 8, "Product Category", 1, 0, "L", True)
    pdf.cell(35, 8, "Revenue", 1, 0, "R", True)
    pdf.cell(25, 8, "Share %", 1, 1, "R", True)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    fill = False
    if grp_col in df.columns and total_rev > 0:
        mix = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(max_rows)
        sub_sum = 0.0
        for i, (cat, amt) in enumerate(mix.items(), 1):
            share = (float(amt) / total_rev * 100.0) if total_rev > 0 else 0.0
            sub_sum += float(amt)
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(10, 7, str(i), 1, 0, "C", fill)
            pdf.cell(115, 7, _pdf_text(str(cat))[:55], 1, 0, "L", fill)
            pdf.cell(35, 7, format_currency_pdf(float(amt)), 1, 0, "R", fill)
            pdf.cell(25, 7, f"{share:.1f}%", 1, 1, "R", fill)
            fill = not fill
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(255, 248, 220)
        pdf.cell(10, 7, "", 1, 0, "C", True)
        pdf.cell(115, 7, _pdf_text("Subtotal (rows above)"), 1, 0, "L", True)
        pdf.cell(35, 7, format_currency_pdf(sub_sum), 1, 0, "R", True)
        agg_pct = (sub_sum / total_rev * 100.0) if total_rev > 0 else 0.0
        pdf.cell(25, 7, f"{agg_pct:.1f}%", 1, 1, "R", True)
        pdf.set_fill_color(218, 235, 242)
        pdf.cell(10, 7, "", 1, 0, "C", True)
        pdf.cell(115, 7, _pdf_text("Total (all categories)"), 1, 0, "L", True)
        pdf.cell(35, 7, format_currency_pdf(total_rev), 1, 0, "R", True)
        pdf.cell(25, 7, "100.0%", 1, 1, "R", True)
        pdf.set_font("Arial", "", 9)
    else:
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(185, 7, "Insufficient data for product mix analysis.", 1, 1, "L", False)


def _pdf_draw_fy_material_group_table(
    pdf: FPDF,
    df_work: pd.DataFrame,
    grp_col: str,
    fy_compare: List[str],
    max_categories: int = 9,
) -> None:
    """
    Material / product category mix with one column per selected FY (revenue + share within that FY)
    and YoY. Expects FINANCIAL_YEAR and AMOUNT on df_work.
    """
    if len(fy_compare) < 2 or grp_col not in df_work.columns or "AMOUNT" not in df_work.columns:
        return
    if "FINANCIAL_YEAR" not in df_work.columns:
        return

    df_mix = df_work.copy()
    df_mix["_FY"] = df_mix["FINANCIAL_YEAR"].astype(str).str.strip()

    if len(fy_compare) == 2:
        fy0, fy1 = fy_compare[0], fy_compare[1]
        fy_totals = {fy: float(df_mix.loc[df_mix["_FY"] == fy, "AMOUNT"].sum()) for fy in (fy0, fy1)}
        mix = df_mix.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(max_categories)
        w_num, w_cat, w_r1, w_s1, w_r2, w_s2, w_y = 7, 60, 27, 15, 27, 15, 20
        row_h = 7
        hdr_h = 9
        footer_block_h = 21.0  # subtotal + total rows (3 x 7mm)

        def fy2_header() -> None:
            pdf.set_font("Arial", "B", 7)
            pdf.set_fill_color(218, 165, 32)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(w_num, hdr_h, "#", 1, 0, "C", True)
            pdf.cell(w_cat, hdr_h, "Product Category", 1, 0, "L", True)
            pdf.cell(w_r1, hdr_h, _pdf_text(f"{fy0} Rev")[:24], 1, 0, "R", True)
            pdf.cell(w_s1, hdr_h, _pdf_text(f"{fy0} %")[:12], 1, 0, "R", True)
            pdf.cell(w_r2, hdr_h, _pdf_text(f"{fy1} Rev")[:24], 1, 0, "R", True)
            pdf.cell(w_s2, hdr_h, _pdf_text(f"{fy1} %")[:12], 1, 0, "R", True)
            pdf.cell(w_y, hdr_h, "YoY Rev %", 1, 1, "R", True)
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(0, 0, 0)

        if not mix.empty and sum(fy_totals.values()) > 0:
            fy2_header()
            for i, cat in enumerate(mix.index, 1):
                if pdf.get_y() + row_h > pdf.h - pdf.b_margin - footer_block_h:
                    pdf.add_page()
                    fy2_header()
                r0 = float(df_mix.loc[(df_mix[grp_col] == cat) & (df_mix["_FY"] == fy0), "AMOUNT"].sum())
                r1 = float(df_mix.loc[(df_mix[grp_col] == cat) & (df_mix["_FY"] == fy1), "AMOUNT"].sum())
                s0 = (r0 / fy_totals[fy0] * 100.0) if fy_totals.get(fy0, 0) > 0 else 0.0
                s1 = (r1 / fy_totals[fy1] * 100.0) if fy_totals.get(fy1, 0) > 0 else 0.0
                yoy = _rev_yoy_pct(r0, r1)
                row_fill = i % 2 == 0
                pdf.set_fill_color(248, 249, 250) if row_fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(w_num, row_h, str(i), 1, 0, "C", row_fill)
                pdf.cell(w_cat, row_h, _pdf_text(str(cat))[:48], 1, 0, "L", row_fill)
                pdf.cell(w_r1, row_h, format_currency_pdf(r0), 1, 0, "R", row_fill)
                pdf.cell(w_s1, row_h, f"{s0:.1f}%", 1, 0, "R", row_fill)
                pdf.cell(w_r2, row_h, format_currency_pdf(r1), 1, 0, "R", row_fill)
                pdf.cell(w_s2, row_h, f"{s1:.1f}%", 1, 0, "R", row_fill)
                pdf.cell(w_y, row_h, _pdf_text(yoy), 1, 1, "R", row_fill)
            _pdf_need_space(pdf, footer_block_h)
            # Subtotal = sum of rows shown; aggregate % = share of each FY total captured by those rows
            cats = list(mix.index)
            sub0 = float(
                df_mix.loc[df_mix[grp_col].isin(cats) & (df_mix["_FY"] == fy0), "AMOUNT"].sum()
            )
            sub1 = float(
                df_mix.loc[df_mix[grp_col].isin(cats) & (df_mix["_FY"] == fy1), "AMOUNT"].sum()
            )
            ss0 = (sub0 / fy_totals[fy0] * 100.0) if fy_totals.get(fy0, 0) > 0 else 0.0
            ss1 = (sub1 / fy_totals[fy1] * 100.0) if fy_totals.get(fy1, 0) > 0 else 0.0
            pdf.set_font("Arial", "B", 8)
            pdf.set_fill_color(255, 248, 220)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(w_num, 7, "", 1, 0, "C", True)
            pdf.cell(w_cat, 7, _pdf_text(f"Subtotal (top {len(cats)} categories)"), 1, 0, "L", True)
            pdf.cell(w_r1, 7, format_currency_pdf(sub0), 1, 0, "R", True)
            pdf.cell(w_s1, 7, f"{ss0:.1f}%", 1, 0, "R", True)
            pdf.cell(w_r2, 7, format_currency_pdf(sub1), 1, 0, "R", True)
            pdf.cell(w_s2, 7, f"{ss1:.1f}%", 1, 0, "R", True)
            pdf.cell(w_y, 7, _pdf_text(_rev_yoy_pct(sub0, sub1)), 1, 1, "R", True)
            pdf.set_fill_color(218, 235, 242)
            pdf.cell(w_num, 7, "", 1, 0, "C", True)
            pdf.cell(w_cat, 7, _pdf_text("Total (FY revenue, all categories)"), 1, 0, "L", True)
            pdf.cell(w_r1, 7, format_currency_pdf(fy_totals[fy0]), 1, 0, "R", True)
            pdf.cell(w_s1, 7, "100.0%", 1, 0, "R", True)
            pdf.cell(w_r2, 7, format_currency_pdf(fy_totals[fy1]), 1, 0, "R", True)
            pdf.cell(w_s2, 7, "100.0%", 1, 0, "R", True)
            pdf.cell(w_y, 7, _pdf_text(_rev_yoy_pct(fy_totals[fy0], fy_totals[fy1])), 1, 1, "R", True)
            pdf.set_font("Arial", "", 8)
        else:
            pdf.set_font("Arial", "", 9)
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(w_num + w_cat + w_r1 + w_s1 + w_r2 + w_s2 + w_y, 7, "Insufficient data for product mix analysis.", 1, 1, "L", False)
        return

    # 3+ fiscal years: revenue per FY + YoY (last vs previous)
    fy_totals = {fy: float(df_mix.loc[df_mix["_FY"] == fy, "AMOUNT"].sum()) for fy in fy_compare}
    mix = df_mix.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(max_categories)
    w_num = 7
    w_cat = 54
    w_yoy = 26
    nfy = len(fy_compare)
    rem = 187 - w_num - w_cat - w_yoy  # 100mm for revenue columns
    w_rev_each = max(20, rem / max(nfy, 1))
    row_h = 7
    hdr_h = 9
    footer_block_h = 21.0
    f_prev, f_last = fy_compare[-2], fy_compare[-1]

    def fyn_header() -> None:
        pdf.set_font("Arial", "B", 7)
        pdf.set_fill_color(218, 165, 32)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(w_num, hdr_h, "#", 1, 0, "C", True)
        pdf.cell(w_cat, hdr_h, "Product Category", 1, 0, "L", True)
        for fy in fy_compare:
            pdf.cell(w_rev_each, hdr_h, _pdf_text(f"{fy} Rev")[:18], 1, 0, "R", True)
        pdf.cell(w_yoy, hdr_h, "YoY %", 1, 1, "R", True)
        pdf.set_font("Arial", "", 7)
        pdf.set_text_color(0, 0, 0)

    if not mix.empty and sum(fy_totals.values()) > 0:
        fyn_header()
        for i, cat in enumerate(mix.index, 1):
            if pdf.get_y() + row_h > pdf.h - pdf.b_margin - footer_block_h:
                pdf.add_page()
                fyn_header()
            row_fill = i % 2 == 0
            pdf.set_fill_color(248, 249, 250) if row_fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(w_num, row_h, str(i), 1, 0, "C", row_fill)
            pdf.cell(w_cat, row_h, _pdf_text(str(cat))[:48], 1, 0, "L", row_fill)
            rv_prev = float(df_mix.loc[(df_mix[grp_col] == cat) & (df_mix["_FY"] == f_prev), "AMOUNT"].sum())
            rv_last = float(df_mix.loc[(df_mix[grp_col] == cat) & (df_mix["_FY"] == f_last), "AMOUNT"].sum())
            for fy in fy_compare:
                r = float(df_mix.loc[(df_mix[grp_col] == cat) & (df_mix["_FY"] == fy), "AMOUNT"].sum())
                pdf.cell(w_rev_each, row_h, format_currency_pdf(r), 1, 0, "R", row_fill)
            yoy = _rev_yoy_pct(rv_prev, rv_last)
            pdf.cell(w_yoy, row_h, _pdf_text(yoy), 1, 1, "R", row_fill)
        _pdf_need_space(pdf, footer_block_h + 14.0)
        cats = list(mix.index)
        pdf.set_font("Arial", "B", 7)
        pdf.set_fill_color(255, 248, 220)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w_num, 7, "", 1, 0, "C", True)
        pdf.cell(w_cat, 7, _pdf_text(f"Subtotal (top {len(cats)} categories)"), 1, 0, "L", True)
        sub_by_fy = {
            fy: float(
                df_mix.loc[df_mix[grp_col].isin(cats) & (df_mix["_FY"] == fy), "AMOUNT"].sum()
            )
            for fy in fy_compare
        }
        for fy in fy_compare:
            pdf.cell(w_rev_each, 7, format_currency_pdf(sub_by_fy[fy]), 1, 0, "R", True)
        pdf.cell(w_yoy, 7, _pdf_text(_rev_yoy_pct(sub_by_fy[f_prev], sub_by_fy[f_last])), 1, 1, "R", True)
        pdf.set_fill_color(218, 235, 242)
        pdf.cell(w_num, 7, "", 1, 0, "C", True)
        pdf.cell(w_cat, 7, _pdf_text("Total (FY revenue, all categories)"), 1, 0, "L", True)
        for fy in fy_compare:
            pdf.cell(w_rev_each, 7, format_currency_pdf(fy_totals[fy]), 1, 0, "R", True)
        pdf.cell(
            w_yoy,
            7,
            _pdf_text(_rev_yoy_pct(fy_totals[f_prev], fy_totals[f_last])),
            1,
            1,
            "R",
            True,
        )
        pdf.set_font("Arial", "", 7)
        pdf.ln(1)
        pdf.set_font("Arial", "I", 6)
        pdf.set_text_color(80, 80, 80)
        cap_parts = []
        for fy in fy_compare:
            den = fy_totals.get(fy, 0)
            pct = (sub_by_fy[fy] / den * 100.0) if den > 0 else 0.0
            cap_parts.append(f"{fy}: subtotal = {pct:.1f}% of FY total")
        pdf.multi_cell(0, 3.5, _pdf_text(" | ".join(cap_parts)), 0, "L")
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_font("Arial", "", 9)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(187, 7, "Insufficient data for product mix analysis.", 1, 1, "L", False)


def _pdf_brand_fallback(tenant_id: Optional[str]) -> str:
    """Default cover name when no customer / filter context (not the raw tenant slug)."""
    tid = (tenant_id or "").strip()
    if not tid:
        return "KN Elettro"
    key = tid.lower().replace(" ", "_")
    if key == "default_elettro":
        return "KN Elettro"
    return tid.replace("_", " ").title()


def _pdf_brand_with_env(tenant_id: Optional[str]) -> str:
    """No filter context: optional env legal/brand name, else KN Elettro / humanized tenant slug."""
    override = (os.environ.get("PDF_PREPARED_FOR") or os.environ.get("ORG_DISPLAY_NAME") or "").strip()
    if override:
        return override
    return _pdf_brand_fallback(tenant_id)


def _pdf_prepared_for_line(
    tenant_id: str,
    *,
    specific_entity: Optional[str] = None,
    filter_customer: Optional[str] = None,
    filter_state: Optional[str] = None,
    filter_material: Optional[str] = None,
    customers: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    material_groups: Optional[str] = None,
    months: Optional[str] = None,
    fiscal_years: Optional[str] = None,
) -> str:
    """
    Cover 'PREPARED FOR': use selected customer or other global filters when present;
    otherwise company brand (KN Elettro for default tenant), or PDF_PREPARED_FOR when nothing is selected.
    """
    se = (specific_entity or "").strip()
    if se and se.lower() != "all":
        return se

    if filter_customer and str(filter_customer).strip() and filter_customer != "All":
        return str(filter_customer).strip()

    custs = _split_csv_param(customers)
    if len(custs) == 1:
        return custs[0]
    if len(custs) > 1:
        head = ", ".join(custs[:4])
        return f"{head} (+{len(custs) - 4} more)" if len(custs) > 4 else head

    if filter_state and filter_state != "All":
        return str(filter_state).strip()

    sts = _split_csv_param(states)
    if len(sts) == 1:
        return sts[0]
    if len(sts) > 1:
        head = ", ".join(sts[:3])
        return f"{head} (+{len(sts) - 3} more)" if len(sts) > 3 else head

    if filter_material and filter_material != "All":
        return str(filter_material).strip()

    mgs = _split_csv_param(material_groups)
    if len(mgs) == 1:
        return mgs[0]
    if len(mgs) > 1:
        head = ", ".join(mgs[:3])
        return f"{head} (+{len(mgs) - 3} more)" if len(mgs) > 3 else head

    cits = _split_csv_param(cities)
    if len(cits) == 1:
        return cits[0]
    if len(cits) > 1:
        return f"{len(cits)} cities"

    mos = _split_csv_param(months)
    if len(mos) == 1:
        return mos[0]
    if len(mos) > 1:
        head = ", ".join(mos[:4])
        return f"{head} (+{len(mos) - 4} more)" if len(mos) > 4 else head

    fys = _split_csv_param(fiscal_years)
    if len(fys) == 1:
        return fys[0]
    if len(fys) > 1:
        head = ", ".join(fys[:3])
        return f"{head} (+{len(fys) - 3} more)" if len(fys) > 3 else head

    return _pdf_brand_with_env(tenant_id)


def _sort_month_labels_chronological(month_labels: list) -> list:
    """Sort MONTH bucket labels (``YYYY-MM`` or legacy ``MON-YY``) oldest-first."""
    from .sales_dates import parse_month_label_for_sort

    if not month_labels:
        return []
    keyed = []
    for raw in month_labels:
        m = str(raw).strip()
        dt = parse_month_label_for_sort(m)
        keyed.append((dt if pd.notna(dt) else pd.Timestamp.min, m))
    keyed.sort(key=lambda x: x[0])
    return [x[1] for x in keyed]


def _normalize_fy_caption_token(s: str) -> str:
    """Avoid 'FY FY25-26' when data already includes an FY prefix."""
    t = str(s).strip()
    if not t:
        return t
    if t.upper().startswith("FY"):
        return t
    return f"FY {t}"


def _fmt_cover_month_only(value) -> str:
    """Cover timeline: month + year only (no day), PDF-safe ASCII month names."""
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return str(value)[:16]
    return dt.strftime("%b %Y")


def _cover_timeline_from_params(
    start_date: Optional[str],
    end_date: Optional[str],
    months: Optional[str],
    fiscal_years: Optional[str],
    df: Optional[pd.DataFrame] = None,
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Build cover timeline caption and bar labels.
    When fiscal year filters are set, uses April-March FY boundaries (same as data FINANCIAL_YEAR).
    Otherwise uses calendar date range (month-only) or inferred data span.
    """
    caption_parts: list = []
    left: Optional[str] = None
    right: Optional[str] = None

    fy_list = _split_csv_param(fiscal_years)
    fy_bar = fy_selection_to_timeline_month_labels(fy_list) if fy_list else None
    used_fy_timeline = False

    if fy_bar:
        left, right = fy_bar
        caption_parts.append(f"{left} - {right}")
        fy_disp = [_normalize_fy_caption_token(x) for x in fy_list[:4]]
        extra = f" (+{len(fy_list) - 4})" if len(fy_list) > 4 else ""
        caption_parts.append(", ".join(fy_disp) + extra)
        used_fy_timeline = True

    sd = (start_date or "").strip() or None
    ed = (end_date or "").strip() or None

    if not used_fy_timeline and df is not None and not df.empty and (not sd or not ed):
        date_col = next((c for c in df.columns if str(c).upper() == "DATE"), None)
        if date_col:
            try:
                dts = pd.to_datetime(df[date_col], errors="coerce").dropna()
                if len(dts) > 0:
                    if not sd:
                        sd = dts.min().strftime("%Y-%m-%d")
                    if not ed:
                        ed = dts.max().strftime("%Y-%m-%d")
            except Exception:
                pass

    if not used_fy_timeline:
        if sd and ed:
            try:
                s = _fmt_cover_month_only(str(sd)[:10])
                e = _fmt_cover_month_only(str(ed)[:10])
                left, right = s, e
                caption_parts.append(f"{s} - {e}" if s != e else s)
            except Exception:
                left, right = str(sd)[:12], str(ed)[:12]
                caption_parts.append(f"{left} - {right}")
        elif sd:
            try:
                left = _fmt_cover_month_only(str(sd)[:10])
                caption_parts.append(f"From {left}")
            except Exception:
                left = str(sd)[:16]
                caption_parts.append(f"From {left}")
        elif ed:
            try:
                right = _fmt_cover_month_only(str(ed)[:10])
                caption_parts.append(f"Through {right}")
            except Exception:
                right = str(ed)[:16]
                caption_parts.append(f"Through {right}")

    if months and str(months).strip():
        mo = [x.strip() for x in str(months).split(",") if x.strip()]
        if mo:
            mo = _sort_month_labels_chronological(mo)
            caption_parts.append(
                "Months: " + ", ".join(mo[:5]) + (" ..." if len(mo) > 5 else "")
            )

    # Use " | " separators — all ASCII-safe for fpdf latin-1
    caption = " | ".join(caption_parts) if caption_parts else "Period: active dashboard filters"
    return caption, left, right


def generate_distributor_vs_target_pdf(report: dict) -> bytes:
    """
    One-page landscape PDF: customer summary + material group actual vs target.
    `report` matches GET /reports/distributor-vs-target JSON.
    """
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _pdf_text("Distributor vs Target Report"), ln=1)
    pdf.set_font("Helvetica", "", 9)
    cust = report.get("customer_name") or ""
    ym = report.get("year_month") or ""
    per = report.get("period") or {}
    pdf.cell(
        0,
        5,
        _pdf_text(f"Customer: {cust}  |  Month: {ym}  |  Period: {per.get('start', '')} to {per.get('end', '')}"),
        ln=1,
    )
    pdf.ln(2)

    msg = report.get("message")
    if msg:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, _pdf_text(str(msg)), ln=1)
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, _pdf_text("Customer summary"), ln=1)
    pdf.set_font("Helvetica", "", 9)
    ca = report.get("customer_actual", 0)
    ct = report.get("customer_target", 0)
    cv = report.get("customer_variance", 0)
    cp = report.get("customer_pct_of_target", 0)
    pdf.cell(0, 5, _pdf_text(f"Actual: {format_currency_pdf(ca)}  |  Target: {format_currency_pdf(ct)}  |  Variance: {format_currency_pdf(cv)}  |  % of target: {cp}%"), ln=1)
    pdf.ln(3)

    rows = report.get("material_groups") or []
    if not rows:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _pdf_text("No material group rows."), ln=1)
        return _pdf_to_bytes(pdf)

    pdf.set_font("Helvetica", "B", 9)
    col_w = [78, 22, 32, 32, 32, 24]
    headers = ["Material group", "Share %", "Actual", "Target", "Variance", "% target"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, _pdf_text(h), border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for r in rows:
        mg = str(r.get("material_group", ""))[:42]
        sp = f"{float(r.get('share_of_customer_pct', 0)):.1f}%"
        act = format_currency_pdf(r.get("actual", 0))
        tgt = format_currency_pdf(r.get("target", 0))
        var = format_currency_pdf(r.get("variance", 0))
        pt = f"{float(r.get('pct_of_target', 0)):.0f}%"
        pdf.cell(col_w[0], 6, _pdf_text(mg), border=1)
        pdf.cell(col_w[1], 6, _pdf_text(sp), border=1, align="R")
        pdf.cell(col_w[2], 6, _pdf_text(act), border=1, align="R")
        pdf.cell(col_w[3], 6, _pdf_text(tgt), border=1, align="R")
        pdf.cell(col_w[4], 6, _pdf_text(var), border=1, align="R")
        pdf.cell(col_w[5], 6, _pdf_text(pt), border=1, align="R")
        pdf.ln()

    return _pdf_to_bytes(pdf)


def _dim_to_col(df: pd.DataFrame, dim: str) -> Optional[str]:
    """
    Map a logical dimension key to a real dataframe column.
    Supported keys: customer, state, city, material_group, item, month, fiscal_year
    """
    if not dim:
        return None
    d = str(dim).strip().lower()
    mapping = {
        "customer": "CUSTOMER_NAME",
        "state": "STATE",
        "city": "CITY",
        "month": "MONTH",
        "fiscal_year": "FINANCIAL_YEAR",
        "fy": "FINANCIAL_YEAR",
        "item": "ITEMNAME",
    }
    if d == "material_group":
        col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
        return col if col in df.columns else None
    col = mapping.get(d)
    return col if col in df.columns else None


def _safe_top_series(df: pd.DataFrame, col: str, value_col: str = "AMOUNT", top_n: int = 10) -> pd.Series:
    if df.empty or col not in df.columns or value_col not in df.columns:
        return pd.Series(dtype=float)
    s = df.groupby(col)[value_col].sum().sort_values(ascending=False)
    if top_n and len(s) > top_n:
        top = s.head(top_n)
        rest = s.iloc[top_n:].sum()
        if rest > 0:
            top = pd.concat([top, pd.Series([rest], index=["Others"])])
        return top
    return s


# ── Zero-sales inclusion helpers ─────────────────────────────────────────────
# When a user explicitly selects entities (e.g. 30 customers) in the global
# filter bar, some may have zero sales in the current date/other-filter window.
# `groupby` drops them. These helpers let us pad the result so every selected
# entity appears (with zero revenue/orders) in the generated PDF sections.

def _selected_values_for_column(
    df: pd.DataFrame,
    col: str,
    customers: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    material_groups: Optional[str] = None,
    months: Optional[str] = None,
    fiscal_years: Optional[str] = None,
) -> List[str]:
    """Return the list of explicit user selections that apply to `col`, or []
    if no explicit filter targets that column. Values are returned verbatim
    (the apply_filters layer already does exact-match filtering)."""
    if not col:
        return []

    def _split(v: Optional[str]) -> List[str]:
        if v is None:
            return []
        return [p.strip() for p in str(v).split(",") if p.strip()]

    col_u = str(col).upper()
    if col_u == "CUSTOMER_NAME":
        return _split(customers)
    if col_u == "STATE":
        return _split(states)
    if col_u == "CITY":
        return _split(cities)
    if col_u in ("ITEM_NAME_GROUP", "MATERIALGROUP"):
        return _split(material_groups)
    if col_u == "MONTH":
        return _split(months)
    if col_u == "FINANCIAL_YEAR":
        return _split(fiscal_years)
    return []


def _pad_groupby_with_zero(
    grp_df: pd.DataFrame,
    key_col: str,
    selected: List[str],
) -> pd.DataFrame:
    """Append zero-valued rows to a reset-index groupby result for every name in
    `selected` that is missing from `grp_df[key_col]`. Numeric columns get 0,
    object columns get an empty string. Returns a new DataFrame."""
    if grp_df is None or not selected:
        return grp_df
    if key_col not in grp_df.columns:
        return grp_df
    existing = {str(x).strip() for x in grp_df[key_col].astype(str).tolist()}
    missing = [s for s in selected if str(s).strip() not in existing]
    if not missing:
        return grp_df
    pad_rows = []
    for m in missing:
        row: Dict[str, object] = {}
        for c in grp_df.columns:
            if c == key_col:
                row[c] = m
            elif pd.api.types.is_numeric_dtype(grp_df[c].dtype):
                row[c] = 0
            else:
                row[c] = ""
        pad_rows.append(row)
    return pd.concat([grp_df, pd.DataFrame(pad_rows)], ignore_index=True)


def _pad_series_with_zero(series: pd.Series, selected: List[str]) -> pd.Series:
    """Append zero entries to a Series (index = entity name) for every missing
    selected name. Preserves original dtype where possible."""
    if series is None or not selected:
        return series
    existing = {str(x).strip() for x in series.index.astype(str).tolist()}
    missing = [s for s in selected if str(s).strip() not in existing]
    if not missing:
        return series
    add = pd.Series([0.0] * len(missing), index=missing)
    return pd.concat([series, add])


def generate_dynamic_pdf_report(
    df: pd.DataFrame,
    title: str,
    tenant: str,
    primary_dimension: str,
    secondary_dimension: Optional[str] = None,
    top_n: int = 12,
    include_trend: bool = True,
    include_share: bool = True,
    include_top_table: bool = True,
    include_pivot: bool = False,
    customers: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    material_groups: Optional[str] = None,
    months: Optional[str] = None,
    fiscal_years: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> bytes:
    """
    Streamlit-like dynamic report: content adapts to selected dimensions + cross-filters.
    Uses the same PDF theming but renders only the requested sections.
    """
    _, Figure, FigureCanvas, cm = _get_matplotlib()
    try:
        return _generate_dynamic_pdf_report_inner(
            df=df,
            title=title,
            tenant=tenant,
            primary_dimension=primary_dimension,
            secondary_dimension=secondary_dimension,
            top_n=top_n,
            include_trend=include_trend,
            include_share=include_share,
            include_top_table=include_top_table,
            include_pivot=include_pivot,
            customers=customers,
            states=states,
            cities=cities,
            material_groups=material_groups,
            months=months,
            fiscal_years=fiscal_years,
            start_date=start_date,
            end_date=end_date,
            Figure=Figure,
            FigureCanvas=FigureCanvas,
            cm=cm,
        )
    finally:
        gc.collect()


def _generate_dynamic_pdf_report_inner(
    df,
    title,
    tenant,
    primary_dimension,
    secondary_dimension,
    top_n,
    include_trend,
    include_share,
    include_top_table,
    include_pivot,
    customers,
    states,
    cities,
    material_groups,
    months,
    fiscal_years,
    start_date,
    end_date,
    Figure,
    FigureCanvas,
    cm,
) -> bytes:
    pdf = PDF()
    pdf.alias_nb_pages()

    prepared = _pdf_prepared_for_line(
        tenant,
        specific_entity=None,
        filter_customer=None,
        filter_state=None,
        filter_material=None,
        customers=customers,
        states=states,
        cities=cities,
        material_groups=material_groups,
        months=months,
        fiscal_years=fiscal_years,
    )
    t_cap, t_left, t_right = _cover_timeline_from_params(
        start_date, end_date, months, fiscal_years, df,
    )
    pdf.create_cover_page(
        prepared,
        f"Dynamic Report: {title}",
        timeline_caption=t_cap,
        timeline_start=t_left,
        timeline_end=t_right,
    )

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=22)

    if df.empty:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "No data available for the selected filters.", 0, 1)
        return _pdf_to_bytes(pdf)

    # KPI summary
    total_rev = float(df["AMOUNT"].sum()) if "AMOUNT" in df.columns else 0.0
    total_orders = int(df["INVOICE_NO"].nunique()) if "INVOICE_NO" in df.columns else 0
    total_qty = float(df["QUANTITY"].sum()) if "QUANTITY" in df.columns else 0.0
    avg_order = total_rev / total_orders if total_orders > 0 else 0.0

    pdf.set_text_color(33, 33, 33)
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, _pdf_text(title).upper(), 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, _pdf_text(f"Prepared for: {prepared}"), 0, 1)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "1. Summary KPIs", 0, 1)

    col_width = 45
    box_height = 22
    y_start = pdf.get_y()
    metrics = [
        ("TOTAL REVENUE", format_currency_pdf(total_rev)),
        ("TOTAL ORDERS", f"{total_orders:,}"),
        ("TOTAL QUANTITY", f"{int(total_qty):,}"),
        ("AVG ORDER VALUE", format_currency_pdf(avg_order)),
    ]
    for i, (label, value) in enumerate(metrics):
        x = 10 + (i * (col_width + 3))
        pdf.set_fill_color(248, 249, 250)
        pdf.rect(x, y_start, col_width, box_height, "F")
        pdf.set_fill_color(218, 165, 32)
        pdf.rect(x, y_start, col_width, 1, "F")
        pdf.set_xy(x, y_start + 4)
        pdf.set_font("Arial", "B", 7)
        pdf.set_text_color(108, 117, 125)
        pdf.cell(col_width, 5, label, 0, 0, "C")
        pdf.set_xy(x, y_start + 10)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(33, 37, 41)
        pdf.cell(col_width, 7, value, 0, 0, "C")
    pdf.set_y(y_start + box_height + 8)

    primary_col = _dim_to_col(df, primary_dimension)
    secondary_col = _dim_to_col(df, secondary_dimension) if secondary_dimension else None

    trend_drawn = False
    share_drawn = False

    # Trend (monthly)
    if include_trend and "DATE" in df.columns and "AMOUNT" in df.columns:
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "2. Monthly Trend", 0, 1)
        _pdf_need_space(pdf, 98.0)
        trend = df.groupby(pd.Grouper(key="DATE", freq="ME"))["AMOUNT"].sum().reset_index()
        trend["DATE"] = pd.to_datetime(trend["DATE"], errors="coerce")
        trend = trend.sort_values("DATE").tail(24)
        trend["LABEL"] = trend["DATE"].dt.strftime("%Y-%m")

        fig = Figure(figsize=(8, 3.5))
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.plot(trend["LABEL"], trend["AMOUNT"], marker="o", color="#B8860B", linewidth=2, markersize=4)
        ax.set_title("Revenue (Last 24 months)", fontsize=12, fontweight="bold", pad=10)
        ax.set_ylabel("Revenue", fontsize=10, fontweight="bold")
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        _configure_matplotlib_revenue_ticks(ax, "y")
        img = create_chart(fig)
        pdf.image(img, x=10, w=185)
        os.remove(img)
        pdf.ln(3)
        trend_drawn = True

    # Share chart
    if include_share and primary_col:
        if trend_drawn:
            _pdf_section_rule(pdf)
            pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, _pdf_text(f"3. Revenue Share by {primary_col}"), 0, 1)
        s = _safe_top_series(df, primary_col, "AMOUNT", top_n=max(3, int(top_n)))
        if not s.empty:
            fig = Figure(figsize=(8, 4.5))
            FigureCanvas(fig)
            ax = fig.add_subplot(111)
            colors = cm.YlOrBr(np.linspace(0.35, 0.9, len(s)))

            def autopct_format(pct): return ("%1.1f%%" % pct) if pct > 4 else ""

            wedges, *_ = ax.pie(
                s.values,
                labels=None,
                autopct=autopct_format,
                startangle=90,
                colors=colors,
                wedgeprops=dict(width=0.45, edgecolor="w"),
                textprops={"fontsize": 9, "weight": "bold"},
                pctdistance=0.82,
            )
            ax.legend(wedges, [str(x)[:22] for x in s.index], loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
            ax.set_title(f"Revenue share by {primary_col}", fontsize=12, fontweight="bold", pad=12)
            img = create_chart(fig)
            _pdf_need_space(pdf, 102.0)
            pdf.image(img, x=10, w=175)
            os.remove(img)
            pdf.ln(3)
            share_drawn = True

    # Top table
    if include_top_table and primary_col:
        if share_drawn or trend_drawn:
            _pdf_section_rule(pdf)
            pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        grp = df.groupby(primary_col).agg(
            Revenue=("AMOUNT", "sum"),
            Orders=("INVOICE_NO", "nunique") if "INVOICE_NO" in df.columns else ("AMOUNT", "size"),
            Customers=("CUSTOMER_NAME", "nunique") if "CUSTOMER_NAME" in df.columns else ("AMOUNT", "size"),
        ).reset_index()
        # Include explicitly selected entities that have zero sales (e.g. a
        # customer picked in the filter bar with no invoices in this period),
        # so every entity the user selected still appears in the PDF table.
        primary_selected = _selected_values_for_column(
            df, primary_col,
            customers=customers, states=states, cities=cities,
            material_groups=material_groups, months=months, fiscal_years=fiscal_years,
        )
        _top_title_n = max(max(3, int(top_n)), len(primary_selected)) if primary_selected else max(3, int(top_n))
        pdf.cell(0, 8, _pdf_text(f"4. Top {_top_title_n} by Revenue ({primary_col})"), 0, 1)
        if primary_selected:
            grp = _pad_groupby_with_zero(grp, primary_col, primary_selected)
        # Honour explicit selections over top_n: when the user selected N
        # specific entities in the filter bar, guarantee all N appear even if
        # top_n is smaller (zero-sales ones still get listed at the bottom).
        _top_n_int = max(3, int(top_n))
        _row_cap = max(_top_n_int, len(primary_selected)) if primary_selected else _top_n_int
        grp = grp.sort_values("Revenue", ascending=False).head(_row_cap).reset_index(drop=True)

        def _dyn_top_header() -> None:
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(33, 37, 41)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(85, 8, _pdf_text(primary_col.replace("_", " ").title()), 0, 0, "L", 1)
            pdf.cell(40, 8, "Revenue", 0, 0, "R", 1)
            pdf.cell(30, 8, "Orders", 0, 0, "R", 1)
            pdf.cell(30, 8, "Customers", 0, 1, "R", 1)
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(0, 0, 0)

        _dyn_top_header()
        tr_i = 0
        for _, row in grp.iterrows():
            if pdf.get_y() + 9 > pdf.h - pdf.b_margin:
                pdf.add_page()
                _dyn_top_header()
            tr_i += 1
            fill = tr_i % 2 == 0
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(85, 7, _pdf_text(row[primary_col])[:45], 0, 0, "L", fill)
            pdf.cell(40, 7, format_currency_pdf(float(row["Revenue"])), 0, 0, "R", fill)
            pdf.cell(30, 7, str(int(row["Orders"])), 0, 0, "R", fill)
            pdf.cell(30, 7, str(int(row["Customers"])), 0, 1, "R", fill)
        pdf.ln(2)

    # Material groups by FY when multiple fiscal years are selected (dynamic report)
    fy_dyn = _sort_fy_labels_chronologically(_split_csv_param(fiscal_years)) if fiscal_years else []
    df_dyn_fy = _ensure_financial_year_column(df)
    grp_m = (
        "ITEM_NAME_GROUP"
        if "ITEM_NAME_GROUP" in df.columns
        else ("MATERIALGROUP" if "MATERIALGROUP" in df.columns else None)
    )
    if len(fy_dyn) >= 2 and grp_m and grp_m in df_dyn_fy.columns and "AMOUNT" in df_dyn_fy.columns:
        pdf.ln(3)
        _pdf_section_rule(pdf)
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Material groups by financial year (comparison)", 0, 1)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 4, "Based on global fiscal year filter (Apr-Mar).", 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)
        _pdf_draw_fy_material_group_table(
            pdf, df_dyn_fy, grp_m, fy_dyn, max_categories=max(3, min(int(top_n), 12))
        )

    # Pivot table (primary x secondary)
    if include_pivot and primary_col and secondary_col and secondary_col != primary_col:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, _pdf_text(f"5. Breakdown: {primary_col} -> {secondary_col}"), 0, 1)

        # Rank primary/secondary by revenue, but guarantee explicitly-selected
        # entities still appear in the breakdown even if they have no sales.
        primary_rank = df.groupby(primary_col)["AMOUNT"].sum().sort_values(ascending=False)
        secondary_rank = df.groupby(secondary_col)["AMOUNT"].sum().sort_values(ascending=False)

        _pivot_primary_selected = _selected_values_for_column(
            df, primary_col,
            customers=customers, states=states, cities=cities,
            material_groups=material_groups, months=months, fiscal_years=fiscal_years,
        )
        _pivot_secondary_selected = _selected_values_for_column(
            df, secondary_col,
            customers=customers, states=states, cities=cities,
            material_groups=material_groups, months=months, fiscal_years=fiscal_years,
        )
        primary_rank = _pad_series_with_zero(primary_rank, _pivot_primary_selected)
        secondary_rank = _pad_series_with_zero(secondary_rank, _pivot_secondary_selected)

        top_primary = primary_rank.sort_values(ascending=False).head(8).index.tolist()
        top_secondary = secondary_rank.sort_values(ascending=False).head(6).index.tolist()
        sub = df[df[primary_col].isin(top_primary) & df[secondary_col].isin(top_secondary)]
        if top_primary and top_secondary:
            if sub.empty:
                pivot = pd.DataFrame(0, index=top_primary, columns=top_secondary)
            else:
                pivot = sub.pivot_table(
                    index=primary_col, columns=secondary_col,
                    values="AMOUNT", aggfunc="sum", fill_value=0,
                )
            # Reindex so every selected primary/secondary shows up, even with zeros.
            pivot = pivot.reindex(index=top_primary, columns=top_secondary, fill_value=0)
            # Limit columns so cell width never too small (fpdf "Not enough horizontal space")
            max_cols = 10
            cols = list(pivot.columns)[:max_cols]
            pivot = pivot[cols] if cols else pivot
            ncols = max(1, len(pivot.columns))
            col_w = max(12.0, 145.0 / ncols)
            # print small pivot as table (truncate)
            pdf.set_font("Arial", "B", 8)
            pdf.set_fill_color(33, 37, 41)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(45, 8, _pdf_text(primary_col)[:14], 0, 0, "L", 1)
            for c in pivot.columns:
                pdf.cell(col_w, 8, _pdf_text(str(c))[:12], 0, 0, "R", 1)
            pdf.ln()
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(0, 0, 0)
            fill = False
            for idx, row in pivot.iterrows():
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(45, 7, _pdf_text(str(idx))[:18], 0, 0, "L", fill)
                for c in pivot.columns:
                    pdf.cell(col_w, 7, f"{float(row[c])/100000:.1f}L", 0, 0, "R", fill)
                pdf.ln()
                fill = not fill

    return _pdf_to_bytes(pdf)

_MIN_CELL_W = 5.0


class PDF(FPDF):

    def cell(self, *args, **kwargs):
        """Override cell() to sanitize text before rendering."""
        args = list(args)
        if "txt" in kwargs:
            kwargs["txt"] = _pdf_text(kwargs["txt"])
        elif "text" in kwargs:
            kwargs["text"] = _pdf_text(kwargs["text"])
        elif len(args) >= 3:
            args[2] = _pdf_text(str(args[2]))
        return super().cell(*args, **kwargs)

    def _truncate_text_to_fit(self, text: str, max_w: float) -> str:
        """
        fpdf2 2.8+ raises 'Not enough horizontal space to render a single character'
        if a single token is wider than `w` in multi_cell.
        Truncates long words to fit within max_w, accounting for c_margin padding.
        """
        if max_w <= 0 or not text:
            return text
        c_margin = getattr(self, 'c_margin', 1.0)
        # effective width after cell padding on each side
        effective_w = max_w - (2 * c_margin) - 0.5
        if effective_w <= 0:
            return text
        suffix = '..' if effective_w > 10 else ''
        words = str(text).replace('\n', ' \n ').split(' ')
        res_words = []
        for word in words:
            if word == '\n':
                res_words.append(word)
            elif self.get_string_width(word) <= effective_w:
                res_words.append(word)
            else:
                trunc = word
                while len(trunc) > 1 and self.get_string_width(trunc + suffix) > effective_w:
                    trunc = trunc[:-1]
                if self.get_string_width(trunc + suffix) <= effective_w:
                    res_words.append(trunc + suffix)
                # else: drop the word entirely (unreachable with any reasonable font/size)
        return ' '.join(res_words).replace(' \n ', '\n').replace('  ', ' ')

    def multi_cell(self, *args, **kwargs):
        """Override multi_cell() to sanitize text and reset x if needed."""
        # Reset x to left margin if cursor is off the page
        if self.x >= self.w - self.r_margin:
            self.set_x(self.l_margin)
        # Support legacy 'txt' kwarg
        if "txt" in kwargs:
            kwargs["txt"] = _pdf_text(kwargs["txt"])
        elif "text" in kwargs:
            raw_text = _pdf_text(kwargs["text"])
            # Get width arg for truncation (first positional arg or kwarg 'w')
            w = args[0] if args else kwargs.get("w", 0)
            w_eff = w if w > 0 else (self.epw - (self.x - self.l_margin))
            if w_eff <= 0:
                w_eff = self.epw
            kwargs["text"] = self._truncate_text_to_fit(raw_text, w_eff)
        elif len(args) >= 3:
            args = list(args)
            raw_text = _pdf_text(args[2])
            w = args[0]
            w_eff = w if w > 0 else (self.epw - (self.x - self.l_margin))
            if w_eff <= 0:
                w_eff = self.epw
            args[2] = self._truncate_text_to_fit(raw_text, w_eff)
            args = tuple(args)
        return super().multi_cell(*args, **kwargs)

    def __init__(self):
        super().__init__()
        # Try to locate a logo image. Prefer absolute paths derived from this file's location
        # so it works whether CWD is repo root (local) or `backend/` (Render Root Directory).
        self.logo_light_bg = None
        self.report_label = "Executive Sales Report"
        self._suppress_header_footer = False
        here = os.path.abspath(os.path.dirname(__file__))  # .../backend/api
        candidates = [
            # Repo root assets/
            os.path.normpath(os.path.join(here, "..", "..", "assets", "logo.png")),
            os.path.normpath(os.path.join(here, "..", "..", "assets", "logo_transparent.png")),
            # Frontend public/
            os.path.normpath(os.path.join(here, "..", "..", "frontend", "public", "logo.png")),
            # Legacy/common relative fallbacks (CWD-dependent)
            "assets/logo.png",
            "assets/logo_transparent.png",
            "../assets/logo.png",
            "../frontend/public/logo.png",
            "frontend/public/logo.png",
        ]
        for path in candidates:
            try:
                if path and os.path.exists(path):
                    self.logo_light_bg = path
                    break
            except Exception:
                continue
    
    def header(self):
        if getattr(self, "_suppress_header_footer", False):
            return
        # Dark header strip
        self.set_fill_color(33, 33, 33)
        self.rect(0, 0, 210, 20, 'F')
        
        # Gold accent line
        self.set_fill_color(255, 215, 0)
        self.rect(0, 19, 210, 1, 'F')
        
        # Company name
        self.set_font('Arial', 'B', 12)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'KN Elettro Intelligence', 0, 0, 'L')
        
        # Report label (right side)
        self.set_font('Arial', '', 10)
        self.set_xy(0, 5)
        self.cell(200, 10, _pdf_text(getattr(self, "report_label", "Executive Sales Report")), 0, 0, 'R')
        
        self.ln(25)

    def footer(self):
        if getattr(self, "_suppress_header_footer", False):
            return
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'CONFIDENTIAL | Page {self.page_no()} | Generated by KN Elettro Intelligence', 0, 0, 'C')

    def create_cover_page(
        self,
        customer_name,
        sub_title="Analysis Period: YTD",
        *,
        timeline_caption: Optional[str] = None,
        timeline_start: Optional[str] = None,
        timeline_end: Optional[str] = None,
    ):
        self.add_page()
        
        # Right dark strip
        self.set_fill_color(22, 27, 34)
        self.rect(140, 0, 70, 297, 'F')
        
        # Logo on cover
        if self.logo_light_bg:
            try:
                self.image(self.logo_light_bg, x=148, y=25, w=50)
            except:
                pass
        
        # Main title
        self.set_xy(10, 70)
        self.set_font("Arial", 'B', 36)
        self.set_text_color(22, 27, 34)
        self.multi_cell(120, 15, "EXECUTIVE\nPERFORMANCE\nREPORT", 0, 'L')
        
        # Subtitle
        self.set_xy(10, self.get_y() + 15)
        self.set_font("Arial", '', 14)
        self.set_text_color(120, 120, 120)
        self.cell(120, 10, "PREPARED FOR:", 0, 1)
        
        self.set_font("Arial", 'B', 22)
        self.set_text_color(218, 165, 32)
        self.multi_cell(120, 11, _pdf_text(customer_name).upper(), 0, 'L')

        # Timeline (analysis period)
        self.ln(6)
        self.set_x(10)
        self.set_font("Arial", "B", 9)
        self.set_text_color(140, 140, 140)
        self.cell(120, 5, "TIMELINE", 0, 1)
        self.set_font("Arial", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(120, 3, "Financial year: April to March", 0, 1)
        self.set_font("Arial", "", 10)
        self.set_text_color(65, 65, 65)
        cap = timeline_caption or "Period: active dashboard filters"
        self.multi_cell(120, 5, _pdf_text(cap), 0, "L")
        ts, te = timeline_start, timeline_end
        if ts and te:
            y_line = self.get_y() + 4
            x0 = 10.0
            w_bar = 110.0
            self.set_draw_color(218, 165, 32)
            self.set_line_width(0.55)
            self.line(x0, y_line, x0 + w_bar, y_line)
            self.line(x0, y_line - 2.5, x0, y_line + 2.5)
            self.line(x0 + w_bar, y_line - 2.5, x0 + w_bar, y_line + 2.5)
            self.set_y(y_line + 5)
            self.set_font("Arial", "", 8)
            self.set_text_color(95, 95, 95)
            self.set_x(x0)
            half = w_bar / 2
            self.cell(half, 4, _pdf_text(ts), 0, 0, "L")
            self.cell(half, 4, _pdf_text(te), 0, 1, "R")
            self.ln(4)
        else:
            y_rule = self.get_y() + 2
            self.set_draw_color(218, 165, 32)
            self.set_line_width(0.35)
            self.line(10, y_rule, 95, y_rule)
            self.ln(8)
        
        # Period info
        self.set_x(10)
        self.set_font("Arial", '', 12)
        self.set_text_color(80, 80, 80)
        self.cell(120, 10, sub_title, 0, 1)
        
        # Intelligence branding
        self.set_xy(145, 100)
        self.set_text_color(218, 165, 32)
        self.set_font("Arial", 'B', 10)
        self.cell(55, 8, "INTELLIGENCE", 0, 1, 'C')
        
        self.set_xy(145, 108)
        self.set_font("Arial", '', 8)
        self.set_text_color(180, 180, 180)
        self.multi_cell(55, 5, "Data-Driven Insights\nfor Strategic Growth", 0, 'C')
        
        # Confidential notice
        self.set_xy(145, 255)
        self.set_font("Arial", '', 8)
        self.set_text_color(120, 120, 120)
        self.multi_cell(55, 4, "Strictly Private\n& Confidential\n\nFor Management\nUse Only", 0, 'R')

    def create_distributor_cover_page(self, customer_name: str, analysis_period: str = "YTD"):
        """Cover for Distributor Strategy Report: title + PREPARED FOR + Analysis Period."""
        # Cover should not have the standard header/footer
        self._suppress_header_footer = True
        # Prevent FPDF auto page-breaks on the cover (this was creating a blank page)
        prev_auto = getattr(self, "auto_page_break", True)
        prev_margin = getattr(self, "b_margin", 20)
        self.set_auto_page_break(auto=False, margin=0)

        self.add_page()
        # Full-page dark cover background
        self.set_fill_color(13, 17, 23)  # GitHub-like dark
        self.rect(0, 0, 210, 297, "F")

        # Top band (white header per request)
        band_h = 26
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, 210, band_h, "F")
        self.set_fill_color(218, 165, 32)
        self.rect(0, band_h, 210, 1, "F")

        if self.logo_light_bg:
            try:
                # Put logo on the band; keep original logo colors (no tinting)
                # Logo is wide, so allocate width and keep vertical padding.
                self.image(self.logo_light_bg, x=10, y=4.5, w=46)
            except Exception:
                pass

        # Brand text on the top band (right aligned)
        self.set_text_color(13, 17, 23)
        self.set_font("Arial", "B", 12)
        self.set_xy(0, 7)
        self.cell(200, 10, "KN Elettro Intelligence", 0, 0, "R")

        # Title (centered, premium look)
        self.set_text_color(218, 165, 32)
        self.set_font("Arial", "B", 30)
        self.set_xy(0, 95)
        self.cell(0, 12, "DISTRIBUTOR STRATEGY", 0, 1, "C")

        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 20)
        self.set_xy(0, 112)
        self.cell(0, 10, "REPORT", 0, 1, "C")

        # Customer + period
        self.set_text_color(218, 165, 32)
        self.set_font("Arial", "B", 14)
        self.set_xy(0, 140)
        self.cell(0, 8, _pdf_text(customer_name).upper(), 0, 1, "C")

        self.set_text_color(200, 200, 200)
        self.set_font("Arial", "", 10)
        self.set_xy(0, 152)
        self.cell(0, 6, f"Analysis Period: {_pdf_text(analysis_period)}", 0, 1, "C")

        # Subtle footer note (must stay above page-break threshold)
        self.set_text_color(140, 140, 140)
        self.set_font("Arial", "", 8)
        self.set_xy(0, 274)
        self.cell(0, 5, "CONFIDENTIAL • For internal use only", 0, 0, "C")

        # Restore normal page-break behavior for subsequent pages
        self.set_auto_page_break(auto=prev_auto, margin=prev_margin)
        self._suppress_header_footer = False

def _get_matplotlib():
    """Lazy-load matplotlib (OO API only — no pyplot; avoids global state / thread issues under Uvicorn)."""
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    import matplotlib.cm as cm
    return matplotlib, Figure, FigureCanvas, cm


def _configure_matplotlib_revenue_ticks(ax, axis: str = "y") -> None:
    """
    Avoid matplotlib's scientific offset (1e6 / 1e7) on revenue axes; show L/Cr-style ticks.
    axis: 'y' for line charts, 'x' for horizontal bar charts.
    """
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    def _inr_tick(x, _pos):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return ""
        av = abs(v)
        if av < 0.5:
            return "0"
        if av >= 1e7:
            return f"{v / 1e7:.2f} Cr"
        if av >= 1e5:
            return f"{v / 1e5:.1f} L"
        if av >= 1e3:
            return f"{v / 1e3:.0f} K"
        return f"{v:.0f}"

    fmt = FuncFormatter(_inr_tick)
    loc = MaxNLocator(nbins=8)
    if axis == "x":
        ax.xaxis.set_major_formatter(fmt)
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.offsetText.set_visible(False)
    else:
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.set_major_locator(loc)
        ax.yaxis.offsetText.set_visible(False)


def create_chart(fig):
    for ax in fig.get_axes():
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, linestyle='--', alpha=0.6, color='#dddddd')
        ax.tick_params(axis='both', which='major', labelsize=10)
        try:
            ax.yaxis.offsetText.set_visible(False)
            ax.xaxis.offsetText.set_visible(False)
        except Exception:
            pass

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches='tight', dpi=150, facecolor='white')
        return tmp.name


def generate_distributor_strategy_pdf(
    df: pd.DataFrame,
    customer_name: str,
    analysis_period: str = "YTD",
    selected_fiscal_years: Optional[List[str]] = None,
    *,
    include_cover: bool = True,
) -> bytes:
    """
    Generates the usual Distributor Strategy Report: optional cover (DISTRIBUTOR STRATEGY REPORT + customer + period),
    then performance summary (KPIs, product mix, recommendations).
    When ``selected_fiscal_years`` has 2+ entries, product mix is split by FY (revenue + share per FY + YoY).
    matplotlib is lazy-loaded and freed after generation to save RAM."""
    _, Figure, FigureCanvas, cm = _get_matplotlib()
    try:
        return _generate_distributor_strategy_pdf_inner(
            df,
            customer_name,
            analysis_period,
            Figure,
            FigureCanvas,
            cm,
            selected_fiscal_years,
            include_cover=include_cover,
        )
    finally:
        gc.collect()


def _generate_distributor_strategy_pdf_inner(
    df: pd.DataFrame,
    customer_name: str,
    analysis_period: str,
    Figure, FigureCanvas, cm,
    selected_fiscal_years: Optional[List[str]] = None,
    *,
    include_cover: bool = True,
) -> bytes:
    """Inner implementation — matplotlib symbols passed in as arguments.
    """
    # Distributor Strategy Report: optional cover, then performance summary.
    if df.empty:
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.report_label = "Distributor Strategy Report"
        if include_cover:
            pdf.create_distributor_cover_page(_pdf_text(customer_name), _pdf_text(analysis_period))
        else:
            pdf.add_page()
        pdf.set_text_color(200, 200, 200)
        pdf.set_font("Arial", "", 11)
        pdf.set_xy(0, 185)
        pdf.cell(0, 8, "No data available for the selected filters.", 0, 0, "C")
        return _pdf_to_bytes(pdf)

    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.report_label = "Distributor Strategy Report"
    if include_cover:
        pdf.create_distributor_cover_page(_pdf_text(customer_name), _pdf_text(analysis_period))
    pdf.add_page()

    # Performance summary (Product mix + recommendations); page 1 if no cover, else page 2
    total_rev = float(df["AMOUNT"].sum()) if "AMOUNT" in df.columns else 0.0
    total_orders = int(df["INVOICE_NO"].nunique()) if "INVOICE_NO" in df.columns else 0
    avg_order = total_rev / max(total_orders, 1)
    product_categories = int(df[grp_col].nunique()) if grp_col in df.columns else 0

    pdf.set_auto_page_break(auto=True, margin=22)

    # Performance summary header bar
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 9, f"  {_pdf_text(customer_name).upper()} - Performance Summary", 0, 1, "L", 1)
    pdf.ln(3)

    # KPI summary box
    x0 = 12
    y0 = pdf.get_y()
    box_w = 110
    row_h = 7.5
    rows = [
        ("Total Revenue:", format_currency_pdf(total_rev)),
        ("Total Orders:", f"{total_orders:,}"),
        ("Average Order Value:", format_currency_pdf(avg_order)),
        ("Product Categories:", f"{product_categories:,}"),
        ("Analysis Period:", _pdf_text(analysis_period)),
    ]
    pdf.set_fill_color(245, 246, 248)
    pdf.rect(x0, y0, box_w, row_h * len(rows), "F")
    pdf.set_text_color(0, 0, 0)
    for label, val in rows:
        pdf.set_xy(x0 + 2, pdf.get_y())
        pdf.set_font("Arial", "B", 10)
        pdf.cell(62, row_h, _pdf_text(label), 0, 0, "L", False)
        pdf.set_font("Arial", "", 10)
        pdf.cell(box_w - 64, row_h, _pdf_text(val), 0, 1, "R", False)
    pdf.ln(6)

    df_work = _ensure_financial_year_column(df)
    fy_compare = _sort_fy_labels_chronologically(
        [x for x in (selected_fiscal_years or []) if x and str(x).strip()]
    )
    use_fy_breakdown = (
        len(fy_compare) >= 2
        and "FINANCIAL_YEAR" in df_work.columns
        and grp_col in df_work.columns
        and "AMOUNT" in df_work.columns
    )
    _pdf_need_space(pdf, 100.0 if use_fy_breakdown else 72.0)

    # Product mix analysis
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    mix_heading = "  PRODUCT MIX ANALYSIS (BY FINANCIAL YEAR)" if use_fy_breakdown else "  PRODUCT MIX ANALYSIS"
    pdf.cell(0, 9, mix_heading, 0, 1, "L", 1)
    pdf.ln(2)

    if use_fy_breakdown:
        _pdf_draw_fy_material_group_table(pdf, df_work, grp_col, fy_compare, max_categories=9)
    else:
        _pdf_draw_aggregate_material_mix_table(pdf, df, grp_col, total_rev, max_rows=9)

    pdf.ln(6)
    _pdf_section_rule(pdf)
    pdf.add_page()

    # Strategic recommendations
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, "  STRATEGIC RECOMMENDATIONS", 0, 1, "L", 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.ln(3)

    recs = []
    # Partner-facing notes: actionable, order-focused (typical distributor communication)
    if grp_col in df.columns and total_rev > 0:
        top_cat = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(1)
        if len(top_cat) == 1:
            cat_name = _pdf_text(str(top_cat.index[0]))
            cat_share = float(top_cat.iloc[0]) / total_rev * 100.0 if total_rev > 0 else 0.0
            recs.append(
                f"PRIORITY LINES: Your highest share category is '{cat_name[:45]}' "
                f"(about {cat_share:.1f}% of value in this report). Keep healthy stock on this block "
                f"and add adjacent items from the table above to increase basket size on each dispatch."
            )
    if use_fy_breakdown and len(fy_compare) == 2 and "FINANCIAL_YEAR" in df_work.columns:
        fy0, fy1 = fy_compare[0], fy_compare[1]
        dfw = df_work.copy()
        dfw["_FY"] = dfw["FINANCIAL_YEAR"].astype(str).str.strip()
        t0 = float(dfw.loc[dfw["_FY"] == fy0, "AMOUNT"].sum())
        t1 = float(dfw.loc[dfw["_FY"] == fy1, "AMOUNT"].sum())
        if t0 > 0:
            chg = (t1 - t0) / t0 * 100.0
            if chg >= 2.0:
                recs.append(
                    f"TREND: Billed value from {fy0} to {fy1} is up about {chg:.1f}%. "
                    f"Thank you for the momentum — let's firm up the next month's forecast so we can hold stock for you."
                )
            elif chg <= -2.0:
                recs.append(
                    f"TREND: Billed value from {fy0} to {fy1} is lower by about {abs(chg):.1f}%. "
                    f"Please speak with our sales team about schemes, credit days, or SKU mix — we want to help you recover volume."
                )
            else:
                recs.append(
                    f"TREND: Billed value is broadly steady between {fy0} and {fy1}. "
                    f"Share your sales plan so we can suggest the right product push for the next quarter."
                )
        elif t1 > 0:
            recs.append(
                f"TREND: We see activity in {fy1}. Regular ordering helps us plan inventory and pricing for you — confirm your upcoming requirement."
            )
    elif total_rev > 0:
        recs.append(
            "REVIEW THE MIX: Use the category table to pick one or two extra lines for your next indent — "
            "we can advise on fast movers and availability."
        )
    recs.append(
        f"ORDER SIZE: Your average order value is {format_currency_pdf(avg_order)}. "
        f"Where it works for your warehouse, combining requirements into planned purchases can save freight and improve supply security."
    )
    recs.append(
        f"NEXT ORDER: You placed {total_orders:,} purchase cycles in this analysis window "
        f"({_pdf_text(analysis_period)}). To avoid gaps on fast movers, please confirm your next requirement "
        f"with our sales representative and schedule your next delivery."
    )

    for r in recs:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, _pdf_text(r), 0, "L")

    return _pdf_to_bytes(pdf)


def generate_pdf_report(
    df: pd.DataFrame,
    report_type: str = "Executive Summary",
    tenant: str = "",
    specific_entity: str = None,
    filter_customer: str = None,
    filter_state: str = None,
    filter_city: str = None,
    filter_material: str = None,
    customers: Optional[str] = None,
    states: Optional[str] = None,
    cities: Optional[str] = None,
    material_groups: Optional[str] = None,
    months: Optional[str] = None,
    fiscal_years: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> bytes:
    _, Figure, FigureCanvas, cm = _get_matplotlib()
    try:
        return _generate_pdf_report_inner(
            df=df, report_type=report_type, tenant=tenant,
            specific_entity=specific_entity, filter_customer=filter_customer,
            filter_state=filter_state, filter_city=filter_city, filter_material=filter_material,
            customers=customers, states=states, cities=cities,
            material_groups=material_groups, months=months, fiscal_years=fiscal_years,
            start_date=start_date, end_date=end_date,
            Figure=Figure, FigureCanvas=FigureCanvas, cm=cm,
        )
    finally:
        gc.collect()


def _generate_pdf_report_inner(
    df: pd.DataFrame,
    report_type: str,
    tenant: str,
    specific_entity,
    filter_customer,
    filter_state,
    filter_city,
    filter_material,
    customers,
    states,
    cities,
    material_groups,
    months,
    fiscal_years,
    start_date,
    end_date,
    Figure, FigureCanvas, cm,
) -> bytes:
    import sys

    # UI / API may send alternate labels; normalize so filters match and layout is consistent
    _rt_raw = (report_type or "").strip()
    _report_aliases = {
        "Region Wise": "State Wise",
        "Regional": "State Wise",
        "State / Region Wise": "State Wise",
        "State/Region Wise": "State Wise",
    }
    report_type = _report_aliases.get(_rt_raw, _rt_raw)
    
    # 1. Apply Secondary Filters (Advanced Context)
    if filter_customer and filter_customer != "All" and "CUSTOMER_NAME" in df.columns:
        df = df[df["CUSTOMER_NAME"] == filter_customer]
    
    if filter_state and filter_state != "All" and "STATE" in df.columns:
        df = df[df["STATE"] == filter_state]

    if filter_city and filter_city != "All":
        city_col_fc = "CITY" if "CITY" in df.columns else None
        if city_col_fc:
            fc = str(filter_city).strip()
            df = df[df[city_col_fc].astype(str).str.strip().str.upper() == fc.upper()]

    if filter_material and filter_material != "All":
        material_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
        if material_col in df.columns:
            df = df[df[material_col] == filter_material]

    # 2. Deep Dive Target Filtering (Primary Axis)
    if specific_entity and specific_entity != "All":
        if report_type == "Customer Wise" and "CUSTOMER_NAME" in df.columns:
            df = df[df["CUSTOMER_NAME"] == specific_entity]
        elif report_type == "City Wise":
            col = "CITY" if "CITY" in df.columns else "STATE"
            if col in df.columns:
                se = str(specific_entity).strip()
                nm = df[col].astype(str).str.strip().str.upper()
                df = df[nm == se.upper()]
        elif report_type == "Material Wise":
            col = "ITEMNAME" if "ITEMNAME" in df.columns else "MATERIALGROUP"
            if col in df.columns:
                se = str(specific_entity).strip()
                nm = df[col].astype(str).str.strip().str.upper()
                df = df[nm == se.upper()]
        elif report_type == "Material Group Wise":
            col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
            if col in df.columns:
                se = str(specific_entity).strip()
                nm = df[col].astype(str).str.strip().str.upper()
                df = df[nm == se.upper()]
        elif report_type == "Month Wise" and "MONTH" in df.columns:
            df = df[df["MONTH"] == specific_entity]
        elif report_type == "State Wise" and "STATE" in df.columns:
            se = str(specific_entity).strip()
            nm = df["STATE"].astype(str).str.strip().str.upper()
            df = df[nm == se.upper()]

    # Use the df provided. Don't filter since FastAPI applies frontend filters before passing this DF.
    pdf = PDF()
    pdf.alias_nb_pages()
    
    # Cover: report entity + global filters → name; else Elettro (or env when no selection)
    target_name = _pdf_prepared_for_line(
        tenant,
        specific_entity=specific_entity,
        filter_customer=filter_customer,
        filter_state=filter_state,
        filter_material=filter_material,
        customers=customers,
        states=states,
        cities=cities,
        material_groups=material_groups,
        months=months,
        fiscal_years=fiscal_years,
    )

    t_cap, t_left, t_right = _cover_timeline_from_params(
        start_date, end_date, months, fiscal_years, df,
    )
    pdf.create_cover_page(
        target_name,
        f"Report Type: {report_type}",
        timeline_caption=t_cap,
        timeline_start=t_left,
        timeline_end=t_right,
    )
    
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=22)
    
    title_text = f"Report: {report_type}"
    sub_title = "Performance Overview" if report_type == "Executive Summary" else "Fiscal Year Overview"

    if specific_entity and specific_entity != "All":
        title_text = f"Profile: {str(specific_entity)[:50]}"
        sub_title = f"{report_type} Deep Dive"
    
    # 1. Title Area
    pdf.set_text_color(33, 33, 33)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, title_text.upper(), 0, 1, 'L')
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, sub_title, 0, 1, 'L')
    pdf.ln(5)

    if df.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "No data available for the selected period.", 0, 1)
        return _pdf_to_bytes(pdf)

    _fy_filter_list = _sort_fy_labels_chronologically(_split_csv_param(fiscal_years)) if fiscal_years else []
    _df_fy = _ensure_financial_year_column(df)

    # 2. KPI Grid 
    total_rev = df["AMOUNT"].sum() if "AMOUNT" in df.columns else 0
    total_orders = df["INVOICE_NO"].nunique() if "INVOICE_NO" in df.columns else 0
    total_qty = df["QUANTITY"].sum() if "QUANTITY" in df.columns else 0
    avg_order = total_rev / total_orders if total_orders > 0 else 0

    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "1. Executive Summary", 0, 1)
    
    col_width = 45
    box_height = 25
    y_start = pdf.get_y()
    
    metrics = [
        ("TOTAL REVENUE", format_currency_pdf(total_rev)),
        ("TOTAL ORDERS", f"{total_orders:,}"),
        ("TOTAL QUANTITY", f"{int(total_qty):,}"),
        ("AVG ORDER VALUE", format_currency_pdf(avg_order))
    ]
    
    for i, (label, value) in enumerate(metrics):
        x = 10 + (i * (col_width + 3)) 
        pdf.set_fill_color(248, 249, 250)
        pdf.rect(x, y_start, col_width, box_height, 'F')
        pdf.set_fill_color(218, 165, 32) 
        pdf.rect(x, y_start, col_width, 1, 'F')
        
        pdf.set_xy(x, y_start + 4)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(108, 117, 125) 
        pdf.cell(col_width, 5, label, 0, 0, 'C')
        
        pdf.set_xy(x, y_start + 11)
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(33, 37, 41) 
        pdf.cell(col_width, 8, value, 0, 0, 'C')

    pdf.set_y(y_start + box_height + 10)

    # 3. Monthly Trend Graph (limit to last 24 months for speed)
    if "MONTH" in df.columns and "AMOUNT" in df.columns:
        trend = df.groupby("MONTH")["AMOUNT"].sum().reset_index()
        try:
            from .sales_dates import parse_month_label_for_sort

            trend["SortKey"] = trend["MONTH"].map(parse_month_label_for_sort)
            trend = trend.sort_values("SortKey").tail(24)
        except Exception:
            trend = trend.tail(24)

        fig = Figure(figsize=(8, 3.5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')

        ax.plot(trend["MONTH"], trend["AMOUNT"], marker='o', color='#B8860B', linewidth=2, markersize=5)
        ax.set_title("Monthly Revenue Trend", fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel("Month", fontsize=10, fontweight='bold')
        ax.set_ylabel("Revenue", fontsize=10, fontweight='bold')
        ax.tick_params(axis='x', rotation=45, labelsize=9)
        _configure_matplotlib_revenue_ticks(ax, "y")
        for label in ax.get_xticklabels():
            label.set_ha('right')
            label.set_rotation_mode('anchor')
        # Annotate only when few points to keep render fast
        if len(trend) <= 12:
            for i, (x, y) in enumerate(zip(trend["MONTH"], trend["AMOUNT"])):
                ax.annotate(format_currency_pdf(y), (x, y), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=7,
                            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#dddddd", alpha=0.8))

        img_path = create_chart(fig)
        
        _pdf_need_space(pdf, 118.0)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. Revenue Trend", 0, 1)
        pdf.image(img_path, x=10, w=185)
        os.remove(img_path)
        pdf.ln(5)

    # --- Page 2+: Distribution (category pie optional) ---
    pdf.add_page()
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    item_col = "ITEMNAME" if "ITEMNAME" in df.columns else "MATERIALGROUP"
    pie_drawn = False
    
    if grp_col in df.columns:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "3. Category Distribution", 0, 1)
        
        grp_data = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False)
        if len(grp_data) > 5:
            top_5 = grp_data.head(5)
            others = pd.Series([grp_data.iloc[5:].sum()], index=["Others"])
            final_data = pd.concat([top_5, others])
        else:
            final_data = grp_data

        fig = Figure(figsize=(10, 6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        colors = cm.YlOrBr(np.linspace(0.4, 0.9, len(final_data)))
        
        def autopct_format(pct): return ('%1.1f%%' % pct) if pct > 4 else ''
        wedges, texts, autotexts = ax.pie(final_data, autopct=autopct_format, startangle=90, 
                                          colors=colors, wedgeprops=dict(width=0.4, edgecolor='w'),
                                          textprops={'fontsize': 10, 'weight': 'bold'}, pctdistance=0.85)
        
        ax.legend(wedges, final_data.index, title="Categories", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)
        ax.set_title(f"Revenue by {grp_col}", fontsize=14, fontweight='bold', pad=20)
        
        img_path = create_chart(fig)
        
        _pdf_need_space(pdf, 125.0)
        pdf.image(img_path, x=10, w=180)
        os.remove(img_path)
        pdf.ln(5)
        _pdf_section_rule(pdf)
        pie_drawn = True

    # Top 10 bar: new page only after a pie chart (otherwise use the same page)
    if pie_drawn:
        pdf.add_page()
    else:
        _pdf_need_space(pdf, 115.0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"4. Top 10 High Volume Items", 0, 1)
    top_items = df.groupby(item_col)["AMOUNT"].sum().sort_values(ascending=False).head(10)
    
    fig = Figure(figsize=(10, 5))
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    # Use direct ax.barh instead of pandas .plot() which internally uses pyplot
    sorted_items = top_items.sort_values()
    ax.barh(range(len(sorted_items)), sorted_items.values, color='#333333', edgecolor='#FFD700', height=0.7)
    ax.set_yticks(range(len(sorted_items)))
    ax.set_yticklabels([str(label)[:40] for label in sorted_items.index])
    
    ax.set_title(f"Top 10 Performers by Revenue", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Revenue", fontsize=11, fontweight='bold')
    ax.set_ylabel(None)
    _configure_matplotlib_revenue_ticks(ax, "x")
    for i, v in enumerate(sorted_items.values):
        ax.text(v + (max(sorted_items.values) * 0.01), i, format_currency_pdf(v), va='center', fontsize=9)
        
    fig.tight_layout()
    img_path = create_chart(fig)
    
    _pdf_need_space(pdf, 108.0)
    pdf.image(img_path, x=10, w=185)
    os.remove(img_path)
    pdf.ln(10)
    _pdf_section_rule(pdf)

    # Detailed Breakdown Table (dedicated page; long tables use header repeat on overflow)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "5. Detailed Breakdown", 0, 1)
    
    # Top 25 items for table (header repeated after each automatic page break)
    detailed_data = df.groupby([item_col, grp_col])["AMOUNT"].sum().reset_index().sort_values(by="AMOUNT", ascending=False).head(25)

    def _detailed_table_header() -> None:
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(95, 10, "Item Description", 0, 0, 'L', 1)
        pdf.cell(45, 10, "Category", 0, 0, 'L', 1)
        pdf.cell(45, 10, "Revenue", 0, 1, 'R', 1)
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0, 0, 0)

    _detailed_table_header()
    row_i = 0
    for idx, row in detailed_data.iterrows():
        if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
            pdf.add_page()
            _detailed_table_header()
        row_i += 1
        fill = row_i % 2 == 0
        name = str(row[item_col])[:55]
        grp = str(row[grp_col])[:20]
        amt = format_currency_pdf(row["AMOUNT"])
        pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(95, 8, name, 0, 0, 'L', fill)
        pdf.cell(45, 8, grp, 0, 0, 'L', fill)
        pdf.cell(45, 8, amt, 0, 1, 'R', fill)
        
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # --- Page 3: FY comparison table + YoY chart (all report types, including Executive Summary) ---
    if "FINANCIAL_YEAR" in df.columns:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "6. Fiscal Year (FY) Analysis", 0, 1)
        pdf.ln(2)

        fy_stats = df.groupby("FINANCIAL_YEAR").agg(Revenue=("AMOUNT", "sum"), Orders=("INVOICE_NO", "nunique")).sort_index()

        def _fy_stats_header() -> None:
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(33, 37, 41)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(40, 10, "Fiscal Year", 0, 0, 'C', 1)
            pdf.cell(50, 10, "Total Revenue", 0, 0, 'C', 1)
            pdf.cell(40, 10, "Total Orders", 0, 0, 'C', 1)
            pdf.cell(50, 10, "YoY Growth", 0, 1, 'C', 1)
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)

        _fy_stats_header()
        prev_rev = 0
        fy_i = 0
        for fy, row in fy_stats.iterrows():
            if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                pdf.add_page()
                _fy_stats_header()
            fy_i += 1
            fill = fy_i % 2 == 0
            growth = ((row["Revenue"] - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0
            growth_str = f"{growth:+.1f}%" if prev_rev > 0 else "-"

            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(40, 8, fy, 0, 0, "C", fill)
            pdf.cell(50, 8, format_currency_pdf(row["Revenue"]), 0, 0, "R", fill)
            pdf.cell(40, 8, str(row["Orders"]), 0, 0, "C", fill)
            pdf.cell(50, 8, growth_str, 0, 1, "C", fill)
            prev_rev = row["Revenue"]
        pdf.ln(5)

        # FY Comparison Chart (Multi-line Year-over-Year)
        if "MONTH" in df.columns and "DATE" in df.columns:
            try:
                df["Month_Num"] = pd.to_datetime(df["DATE"]).dt.month
                df["Month_Name"] = pd.to_datetime(df["DATE"]).dt.strftime("%b")

                fy_trend = df.groupby(["FINANCIAL_YEAR", "Month_Num", "Month_Name"])["AMOUNT"].sum().reset_index()
                fy_trend.sort_values("Month_Num", inplace=True)

                fig = Figure(figsize=(10, 5))
                canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)
                fig.patch.set_facecolor("white")
                ax.set_facecolor("white")

                for fy in fy_trend["FINANCIAL_YEAR"].unique():
                    fy_data = fy_trend[fy_trend["FINANCIAL_YEAR"] == fy]
                    ax.plot(fy_data["Month_Name"], fy_data["AMOUNT"], marker="o", label=fy, linewidth=2.5, markersize=6)

                ax.set_title("Year-Over-Year Revenue Trends", fontsize=14, fontweight="bold", pad=15)
                ax.legend(fontsize=10)
                ax.set_xlabel("Month", fontsize=11, fontweight="bold")
                ax.set_ylabel("Revenue", fontsize=11, fontweight="bold")
                ax.tick_params(axis="x", rotation=45)
                _configure_matplotlib_revenue_ticks(ax, "y")

                img_path = create_chart(fig)

                _pdf_need_space(pdf, 108.0)
                pdf.image(img_path, x=10, w=185)
                os.remove(img_path)
                pdf.ln(5)
            except Exception:
                pass  # Skip if date parsing fails

    # Material groups: FY-by-FY comparison (all report types when 2+ FYs selected in global filter)
    if (
        len(_fy_filter_list) >= 2
        and grp_col in _df_fy.columns
        and "AMOUNT" in _df_fy.columns
    ):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "7. Material groups by financial year (comparison)", 0, 1)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(
            0,
            5,
            "Revenue and share % are per financial year (Apr-Mar). YoY compares the newer FY to the older FY in your selection.",
            0,
            1,
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        _pdf_draw_fy_material_group_table(pdf, _df_fy, grp_col, _fy_filter_list, max_categories=9)
        pdf.ln(5)

    # Material Group Deep Dive (always start on a new page so it never runs under the FY tables/charts)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "8. Material Group Deep Dive", 0, 1)
    pdf.ln(5)

    if grp_col in df.columns:
        group_summary = df.groupby(grp_col).agg(
            Total_Revenue=("AMOUNT", "sum"),
            Top_Item=(item_col, lambda x: x.mode()[0] if not x.mode().empty else "N/A"),
            Order_Count=("INVOICE_NO", "nunique")
        ).sort_values(by="Total_Revenue", ascending=False).head(8) 
        
        for group_name, row in group_summary.iterrows():
            _pdf_need_space(pdf, 24.0)
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(33, 37, 41)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, f" {group_name}", 0, 1, 'L', 1)
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            
            rev_share = (row["Total_Revenue"] / total_rev) * 100 if total_rev > 0 else 0
            
            pdf.set_fill_color(248, 249, 250)
            details = (f" Revenue: {format_currency_pdf(row['Total_Revenue'])} ({rev_share:.1f}% Share) | "
                       f"Orders: {row['Order_Count']} | "
                       f"Best Seller: {str(row['Top_Item'])[:40]}")
            
            pdf.cell(0, 8, details, 0, 1, 'L', 1)
            pdf.ln(3)

    # 9. State/Region Deep Dive (State Wise report only)
    if report_type == "State Wise" and "STATE" in df.columns:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "9. State / Region Revenue Breakdown", 0, 1)
        pdf.ln(5)

        # Exclude the "State Not Found" placeholder from state analytics
        state_df = df[~df["STATE"].astype(str).str.upper().str.contains("NOT FOUND", na=False)].copy()

        if not state_df.empty:
            state_agg = state_df.groupby("STATE").agg(
                Revenue=("AMOUNT", "sum"),
                Orders=("INVOICE_NO", "nunique"),
                Customers=("CUSTOMER_NAME", "nunique") if "CUSTOMER_NAME" in state_df.columns else ("INVOICE_NO", "count"),
            ).sort_values("Revenue", ascending=False)

            total_state_rev = state_agg["Revenue"].sum()

            # Horizontal bar chart — top 15 states by revenue
            top_states = state_agg.head(15)
            chart_h = max(3.5, len(top_states) * 0.45)
            fig = Figure(figsize=(10, chart_h))
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            sorted_st = top_states["Revenue"].sort_values()
            ax.barh(range(len(sorted_st)), sorted_st.values, color="#333333", edgecolor="#FFD700", height=0.65)
            ax.set_yticks(range(len(sorted_st)))
            ax.set_yticklabels([str(s)[:30] for s in sorted_st.index], fontsize=9)
            ax.set_title("State Revenue Ranking (Top 15)", fontsize=13, fontweight="bold", pad=12)
            ax.set_xlabel("Revenue", fontsize=10, fontweight="bold")
            _configure_matplotlib_revenue_ticks(ax, "x")
            _max_val = sorted_st.values[-1] if len(sorted_st) else 1
            for i, v in enumerate(sorted_st.values):
                ax.text(v + (_max_val * 0.01), i, format_currency_pdf(v), va="center", fontsize=8)
            fig.tight_layout()
            img_path = create_chart(fig)
            _pdf_need_space(pdf, 110.0)
            pdf.image(img_path, x=10, w=185)
            os.remove(img_path)
            pdf.ln(6)

            # State summary table (all states)
            def _state_tbl_header() -> None:
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(33, 37, 41)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(65, 10, "State", 0, 0, "L", 1)
                pdf.cell(45, 10, "Revenue", 0, 0, "R", 1)
                pdf.cell(25, 10, "Share %", 0, 0, "R", 1)
                pdf.cell(25, 10, "Orders", 0, 0, "R", 1)
                pdf.cell(25, 10, "Customers", 0, 1, "R", 1)
                pdf.set_font("Arial", "", 9)
                pdf.set_text_color(0, 0, 0)

            _state_tbl_header()
            st_i = 0
            for state_name, row in state_agg.iterrows():
                if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                    _state_tbl_header()
                st_i += 1
                fill = st_i % 2 == 0
                share = (row["Revenue"] / total_state_rev * 100) if total_state_rev > 0 else 0
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(65, 8, _pdf_text(str(state_name)[:32]), 0, 0, "L", fill)
                pdf.cell(45, 8, format_currency_pdf(row["Revenue"]), 0, 0, "R", fill)
                pdf.cell(25, 8, f"{share:.1f}%", 0, 0, "R", fill)
                pdf.cell(25, 8, str(int(row["Orders"])), 0, 0, "R", fill)
                pdf.cell(25, 8, str(int(row["Customers"])), 0, 1, "R", fill)
            pdf.ln(5)

            # If a specific state is selected via filter_state, show top customers for it
            _focused_state = None
            if filter_state and str(filter_state).strip() and str(filter_state).strip().lower() != "all":
                _focused_state = str(filter_state).strip()
            elif specific_entity and str(specific_entity).strip() and str(specific_entity).strip().lower() != "all":
                _focused_state = str(specific_entity).strip()

            if _focused_state and "CUSTOMER_NAME" in state_df.columns:
                state_rows = state_df[state_df["STATE"].astype(str).str.strip().str.upper() == _focused_state.upper()]
                if not state_rows.empty:
                    _pdf_need_space(pdf, 24.0)
                    pdf.set_font("Arial", "B", 12)
                    pdf.set_fill_color(33, 37, 41)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 8, f"  Top Customers - {_focused_state}", 0, 1, "L", 1)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.ln(2)

                    cust_st = state_rows.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(20)

                    def _st_cust_header() -> None:
                        pdf.set_font("Arial", "B", 9)
                        pdf.set_fill_color(33, 37, 41)
                        pdf.set_text_color(255, 255, 255)
                        pdf.cell(130, 10, "Customer", 0, 0, "L", 1)
                        pdf.cell(55, 10, "Revenue", 0, 1, "R", 1)
                        pdf.set_font("Arial", "", 9)
                        pdf.set_text_color(0, 0, 0)

                    _st_cust_header()
                    sc_i = 0
                    for cust, amt in cust_st.items():
                        if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                            pdf.add_page()
                            _st_cust_header()
                        sc_i += 1
                        fill = sc_i % 2 == 0
                        pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                        pdf.cell(130, 8, _pdf_text(str(cust)[:65]), 0, 0, "L", fill)
                        pdf.cell(55, 8, format_currency_pdf(amt), 0, 1, "R", fill)
        else:
            pdf.set_font("Arial", "", 11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, "No state/region data found in the selected dataset.", 0, 1)
            pdf.set_text_color(0, 0, 0)

    # 9b. City Deep Dive (City Wise report only)
    if report_type == "City Wise":
        city_col = "CITY" if "CITY" in df.columns else None
        if city_col:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "9. City Revenue Breakdown", 0, 1)
            pdf.ln(5)

            city_df = df[~df[city_col].astype(str).str.upper().str.contains("NOT FOUND", na=False)].copy()

            if not city_df.empty:
                city_agg = city_df.groupby(city_col).agg(
                    Revenue=("AMOUNT", "sum"),
                    Orders=("INVOICE_NO", "nunique"),
                    Customers=("CUSTOMER_NAME", "nunique") if "CUSTOMER_NAME" in city_df.columns else ("INVOICE_NO", "count"),
                ).sort_values("Revenue", ascending=False)

                total_city_rev = city_agg["Revenue"].sum()

                # Horizontal bar chart — top 15 cities by revenue
                top_cities = city_agg.head(15)
                chart_h = max(3.5, len(top_cities) * 0.45)
                fig = Figure(figsize=(10, chart_h))
                canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)
                fig.patch.set_facecolor("white")
                ax.set_facecolor("white")
                sorted_ct = top_cities["Revenue"].sort_values()
                ax.barh(range(len(sorted_ct)), sorted_ct.values, color="#333333", edgecolor="#FFD700", height=0.65)
                ax.set_yticks(range(len(sorted_ct)))
                ax.set_yticklabels([str(c)[:30] for c in sorted_ct.index], fontsize=9)
                ax.set_title("City Revenue Ranking (Top 15)", fontsize=13, fontweight="bold", pad=12)
                ax.set_xlabel("Revenue", fontsize=10, fontweight="bold")
                _configure_matplotlib_revenue_ticks(ax, "x")
                _max_val = sorted_ct.values[-1] if len(sorted_ct) else 1
                for i, v in enumerate(sorted_ct.values):
                    ax.text(v + (_max_val * 0.01), i, format_currency_pdf(v), va="center", fontsize=8)
                fig.tight_layout()
                img_path = create_chart(fig)
                _pdf_need_space(pdf, 110.0)
                pdf.image(img_path, x=10, w=185)
                os.remove(img_path)
                pdf.ln(6)

                # City summary table (all cities)
                def _city_tbl_header() -> None:
                    pdf.set_font("Arial", "B", 9)
                    pdf.set_fill_color(33, 37, 41)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(65, 10, "City", 0, 0, "L", 1)
                    pdf.cell(45, 10, "Revenue", 0, 0, "R", 1)
                    pdf.cell(25, 10, "Share %", 0, 0, "R", 1)
                    pdf.cell(25, 10, "Orders", 0, 0, "R", 1)
                    pdf.cell(25, 10, "Customers", 0, 1, "R", 1)
                    pdf.set_font("Arial", "", 9)
                    pdf.set_text_color(0, 0, 0)

                _city_tbl_header()
                ct_i = 0
                for city_name, row in city_agg.iterrows():
                    if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                        pdf.add_page()
                        _city_tbl_header()
                    ct_i += 1
                    fill = ct_i % 2 == 0
                    share = (row["Revenue"] / total_city_rev * 100) if total_city_rev > 0 else 0
                    pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                    pdf.cell(65, 8, _pdf_text(str(city_name)[:32]), 0, 0, "L", fill)
                    pdf.cell(45, 8, format_currency_pdf(row["Revenue"]), 0, 0, "R", fill)
                    pdf.cell(25, 8, f"{share:.1f}%", 0, 0, "R", fill)
                    pdf.cell(25, 8, str(int(row["Orders"])), 0, 0, "R", fill)
                    pdf.cell(25, 8, str(int(row["Customers"])), 0, 1, "R", fill)
                pdf.ln(5)

                # If a specific city is focused, show top customers for it
                _focused_city = None
                if filter_city and str(filter_city).strip() and str(filter_city).strip().lower() != "all":
                    _focused_city = str(filter_city).strip()
                elif specific_entity and str(specific_entity).strip() and str(specific_entity).strip().lower() != "all":
                    _focused_city = str(specific_entity).strip()

                if _focused_city and "CUSTOMER_NAME" in city_df.columns:
                    city_rows = city_df[city_df[city_col].astype(str).str.strip().str.upper() == _focused_city.upper()]
                    if not city_rows.empty:
                        _pdf_need_space(pdf, 24.0)
                        pdf.set_font("Arial", "B", 12)
                        pdf.set_fill_color(33, 37, 41)
                        pdf.set_text_color(255, 255, 255)
                        pdf.cell(0, 8, f"  Top Customers - {_focused_city}", 0, 1, "L", 1)
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", "", 10)
                        pdf.ln(2)

                        cust_ct = city_rows.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(20)

                        def _ct_cust_header() -> None:
                            pdf.set_font("Arial", "B", 9)
                            pdf.set_fill_color(33, 37, 41)
                            pdf.set_text_color(255, 255, 255)
                            pdf.cell(130, 10, "Customer", 0, 0, "L", 1)
                            pdf.cell(55, 10, "Revenue", 0, 1, "R", 1)
                            pdf.set_font("Arial", "", 9)
                            pdf.set_text_color(0, 0, 0)

                        _ct_cust_header()
                        cc_i = 0
                        for cust, amt in cust_ct.items():
                            if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                                pdf.add_page()
                                _ct_cust_header()
                            cc_i += 1
                            fill = cc_i % 2 == 0
                            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                            pdf.cell(130, 8, _pdf_text(str(cust)[:65]), 0, 0, "L", fill)
                            pdf.cell(55, 8, format_currency_pdf(amt), 0, 1, "R", fill)
            else:
                pdf.set_font("Arial", "", 11)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 10, "No city data found in the selected dataset.", 0, 1)
                pdf.set_text_color(0, 0, 0)

    # 10. Customer Specific Enhancement: Material Group Preference
    if report_type == "Customer Wise":
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "9. Material Group Preference", 0, 1)
        pdf.ln(5)

        if len(_fy_filter_list) >= 2 and grp_col in _df_fy.columns:
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "Comparison across selected financial years (same as Executive Summary material mix).", 0, 1)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            _pdf_draw_fy_material_group_table(pdf, _df_fy, grp_col, _fy_filter_list, max_categories=15)
        else:
            mat_grp_data = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(15)

            def _cust_pref_mg_header() -> None:
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(33, 37, 41)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(120, 10, "Material Group", 0, 0, 'L', 1)
                pdf.cell(50, 10, "Revenue", 0, 1, 'R', 1)
                pdf.set_font("Arial", '', 10)
                pdf.set_text_color(0, 0, 0)

            _cust_pref_mg_header()
            mg_i = 0
            for grp, amt in mat_grp_data.items():
                if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                    _cust_pref_mg_header()
                mg_i += 1
                fill = mg_i % 2 == 0
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(120, 8, str(grp)[:60], 0, 0, 'L', fill)
                pdf.cell(50, 8, format_currency_pdf(amt), 0, 1, 'R', fill)

    # 10. Material Group Specific Enhancement: Top Customers
    if report_type == "Material Group Wise":
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        _selected_customers_list = _selected_values_for_column(
            df, "CUSTOMER_NAME",
            customers=customers, states=states, cities=cities,
            material_groups=material_groups, months=months, fiscal_years=fiscal_years,
        )
        _cust_section_title = (
            f"9. Selected Customers ({len(_selected_customers_list)})"
            if _selected_customers_list
            else "9. Top 10 Customers"
        )
        pdf.cell(0, 10, _cust_section_title, 0, 1)
        pdf.ln(5)
        
        if "CUSTOMER_NAME" in df.columns:
            cust_data = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False)
            # Keep every customer the user picked in the filter bar, even if
            # they have zero sales in this period.
            if _selected_customers_list:
                cust_data = _pad_series_with_zero(cust_data, _selected_customers_list)
                cust_data = cust_data.sort_values(ascending=False).head(
                    max(15, len(_selected_customers_list))
                )
            else:
                cust_data = cust_data.head(15)
            
            def _mg_top_cust_header() -> None:
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(33, 37, 41)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(120, 10, "Customer Name", 0, 0, 'L', 1)
                pdf.cell(50, 10, "Revenue", 0, 1, 'R', 1)
                pdf.set_font("Arial", '', 10)
                pdf.set_text_color(0, 0, 0)

            _mg_top_cust_header()
            cu_i = 0
            for cust, amt in cust_data.items():
                if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                    _mg_top_cust_header()
                cu_i += 1
                fill = cu_i % 2 == 0
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(120, 8, str(cust)[:60], 0, 0, 'L', fill)
                pdf.cell(50, 8, format_currency_pdf(amt), 0, 1, 'R', fill)

    # --- Final Page: Insights ---
    # ── SUMMARY ANALYSIS PAGE (All Report Types) ──
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(33, 37, 41)
    pdf.cell(0, 10, "MANAGEMENT SUMMARY & ANALYSIS", 0, 1, 'L')
    pdf.set_draw_color(218, 165, 32)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(8)
    
    # Key Metrics Box
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "  KEY PERFORMANCE INDICATORS", 0, 1, 'L', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.ln(3)
    
    total_rev = df["AMOUNT"].sum() if "AMOUNT" in df.columns else 0
    total_orders = df["INVOICE_NO"].nunique() if "INVOICE_NO" in df.columns else 0
    avg_order = total_rev / max(total_orders, 1)
    unique_cust = df["CUSTOMER_NAME"].nunique() if "CUSTOMER_NAME" in df.columns else 0
    unique_items = df["ITEMNAME"].nunique() if "ITEMNAME" in df.columns else 0
    
    kpi_data = [
        ("Total Revenue", format_currency_pdf(total_rev)),
        ("Total Orders", f"{total_orders:,}"),
        ("Average Order Value", format_currency_pdf(avg_order)),
        ("Unique Customers", f"{unique_cust:,}"),
        ("Unique Products", f"{unique_items:,}"),
    ]
    
    pdf.set_fill_color(248, 249, 250)
    for label, value in kpi_data:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(80, 8, f"  {label}", 0, 0, 'L', 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(100, 8, value, 0, 1, 'R', 1)
    pdf.ln(5)
    
    # Top 5 Customers (or every selected customer when the user picked specific
    # customers in the global filter — so zero-sales companies still appear).
    if "CUSTOMER_NAME" in df.columns:
        _mgmt_selected_customers = _selected_values_for_column(
            df, "CUSTOMER_NAME",
            customers=customers, states=states, cities=cities,
            material_groups=material_groups, months=months, fiscal_years=fiscal_years,
        )
        _mgmt_cust_heading = (
            f"  SELECTED CUSTOMERS ({len(_mgmt_selected_customers)})"
            if _mgmt_selected_customers
            else "  TOP 5 CUSTOMERS"
        )

        def _mgmt_top5_cust_header() -> None:
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(33, 37, 41)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, _mgmt_cust_heading, 0, 1, 'L', 1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 10)
            pdf.ln(2)

        _mgmt_top5_cust_header()
        _mgmt_cust_series = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False)
        if _mgmt_selected_customers:
            _mgmt_cust_series = _pad_series_with_zero(_mgmt_cust_series, _mgmt_selected_customers)
            top5_cust = _mgmt_cust_series.sort_values(ascending=False).head(
                max(5, len(_mgmt_selected_customers))
            )
        else:
            top5_cust = _mgmt_cust_series.head(5)
        tc_i = 0
        for i, (cust, amt) in enumerate(top5_cust.items(), 1):
            if pdf.get_y() + 9 > pdf.h - pdf.b_margin:
                pdf.add_page()
                _mgmt_top5_cust_header()
            tc_i += 1
            fill = tc_i % 2 == 0
            share = (amt / total_rev * 100) if total_rev > 0 else 0
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(10, 7, f"{i}.", 0, 0, 'C', fill)
            pdf.cell(100, 7, str(cust)[:50], 0, 0, 'L', fill)
            pdf.cell(40, 7, format_currency_pdf(amt), 0, 0, 'R', fill)
            pdf.cell(30, 7, f"{share:.1f}%", 0, 1, 'R', fill)
        pdf.ln(5)
    
    # Top 5 Material Groups (or FY comparison when multiple FYs selected)
    if grp_col in df.columns:
        _pdf_need_space(pdf, 55.0)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        title_mg = "  TOP 5 MATERIAL GROUPS (BY FY)" if len(_fy_filter_list) >= 2 else "  TOP 5 MATERIAL GROUPS"
        pdf.cell(0, 8, title_mg, 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        pdf.ln(2)

        if len(_fy_filter_list) >= 2 and grp_col in _df_fy.columns:
            _pdf_draw_fy_material_group_table(pdf, _df_fy, grp_col, _fy_filter_list, max_categories=5)
        else:
            top5_grp = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(5)
            tg_i = 0
            for i, (grp, amt) in enumerate(top5_grp.items(), 1):
                if pdf.get_y() + 9 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 12)
                    pdf.set_fill_color(33, 37, 41)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 8, "  TOP 5 MATERIAL GROUPS (continued)", 0, 1, 'L', 1)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", '', 10)
                    pdf.ln(2)
                tg_i += 1
                fill = tg_i % 2 == 0
                share = (amt / total_rev * 100) if total_rev > 0 else 0
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(10, 7, f"{i}.", 0, 0, 'C', fill)
                pdf.cell(100, 7, str(grp)[:50], 0, 0, 'L', fill)
                pdf.cell(40, 7, format_currency_pdf(amt), 0, 0, 'R', fill)
                pdf.cell(30, 7, f"{share:.1f}%", 0, 1, 'R', fill)
        pdf.ln(5)
    
    # Auto-Generated Insights
    _pdf_need_space(pdf, 28.0)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "  KEY INSIGHTS & STRATEGIC RECOMMENDATIONS", 0, 1, 'L', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.ln(3)
    
    insights = []
    
    if "CUSTOMER_NAME" in df.columns and total_rev > 0:
        top3_rev = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(3).sum()
        top3_pct = top3_rev / total_rev * 100
        if top3_pct > 60:
            insights.append(f"HIGH CONCENTRATION: Top 3 customers account for {top3_pct:.1f}% of revenue. Consider diversifying the customer base.")
        else:
            insights.append(f"HEALTHY MIX: Top 3 customers account for {top3_pct:.1f}% of revenue, indicating a well-diversified portfolio.")
    
    if grp_col in df.columns:
        num_cats = df[grp_col].nunique()
        top_cat = df.groupby(grp_col)["AMOUNT"].sum().idxmax()
        top_cat_share = df.groupby(grp_col)["AMOUNT"].sum().max() / total_rev * 100 if total_rev > 0 else 0
        insights.append(f"PORTFOLIO: {num_cats} material groups active. '{str(top_cat)[:30]}' leads with {top_cat_share:.1f}% share.")
    
    if avg_order > 0:
        if avg_order < 50000:
            insights.append(f"ORDER SIZE: Average order value is {format_currency_pdf(avg_order)} - consider bundling strategies to increase order size.")
        else:
            insights.append(f"ORDER SIZE: Average order value is {format_currency_pdf(avg_order)} - strong per-order commitment.")

    # Geographic insight (exclude placeholder values)
    if "STATE" in df.columns and not df.empty:
        _geo_df = df[~df["STATE"].astype(str).str.upper().str.contains("NOT FOUND", na=False)]
        if not _geo_df.empty:
            num_states = _geo_df["STATE"].nunique()
            top_state = _geo_df.groupby("STATE")["AMOUNT"].sum().idxmax()
            insights.append(f"GEOGRAPHY: Active across {num_states} states. Top state: {top_state}.")

    for insight in insights:
        _pdf_need_space(pdf, 14.0)
        pdf.set_x(10)
        if ":" in insight:
            pdf.set_font("Arial", 'B', 9)
            pdf.multi_cell(0, 5, _pdf_text(insight), 0, 'L')
        else:
            pdf.set_font("Arial", '', 9)
            pdf.multi_cell(0, 5, _pdf_text(insight), 0, 'L')
        pdf.ln(1)

    return _pdf_to_bytes(pdf)

