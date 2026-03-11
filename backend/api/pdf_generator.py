import pandas as pd
from fpdf import FPDF
from datetime import datetime
import tempfile
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.cm as cm
import matplotlib
import os
import numpy as np
from typing import Optional

matplotlib.use('Agg')


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
        "–": "-",
        "-": "-",
        "“": "\"",
        "”": "\"",
        "’": "'",
        "•": "-",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


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
) -> bytes:
    """
    Streamlit-like dynamic report: content adapts to selected dimensions + cross-filters.
    Uses the same PDF theming but renders only the requested sections.
    """
    pdf = PDF()
    pdf.alias_nb_pages()

    # Cover
    target_name = tenant.replace("_", " ").title() if tenant else "Management Team"
    pdf.create_cover_page(target_name, f"Dynamic Report: {title}")

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

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
    pdf.cell(0, 6, _pdf_text(f"Generated: {datetime.now().strftime('%d %B %Y')} | Tenant: {tenant}"), 0, 1)
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

    # Trend (monthly)
    if include_trend and "DATE" in df.columns and "AMOUNT" in df.columns:
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "2. Monthly Trend", 0, 1)
        trend = df.groupby(pd.Grouper(key="DATE", freq="ME"))["AMOUNT"].sum().reset_index()
        trend["DATE"] = pd.to_datetime(trend["DATE"], errors="coerce")
        trend = trend.sort_values("DATE").tail(24)
        trend["LABEL"] = trend["DATE"].dt.strftime("%Y-%m")

        fig = Figure(figsize=(8, 3.5))
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.plot(trend["LABEL"], trend["AMOUNT"], marker="o", color="#B8860B", linewidth=2, markersize=4)
        ax.set_title("Revenue (Last 24 months)", fontsize=12, fontweight="bold", pad=10)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        img = create_chart(fig)
        pdf.image(img, x=10, w=190)
        os.remove(img)
        pdf.ln(3)

    # Share chart
    if include_share and primary_col:
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
            pdf.image(img, x=10, w=175)
            os.remove(img)
            pdf.ln(3)

    # Top table
    if include_top_table and primary_col:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, _pdf_text(f"4. Top {max(3, int(top_n))} by Revenue ({primary_col})"), 0, 1)
        grp = df.groupby(primary_col).agg(
            Revenue=("AMOUNT", "sum"),
            Orders=("INVOICE_NO", "nunique") if "INVOICE_NO" in df.columns else ("AMOUNT", "size"),
            Customers=("CUSTOMER_NAME", "nunique") if "CUSTOMER_NAME" in df.columns else ("AMOUNT", "size"),
        ).sort_values("Revenue", ascending=False).head(max(3, int(top_n))).reset_index()

        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(90, 8, _pdf_text(primary_col.replace("_", " ").title()), 0, 0, "L", 1)
        pdf.cell(40, 8, "Revenue", 0, 0, "R", 1)
        pdf.cell(30, 8, "Orders", 0, 0, "R", 1)
        pdf.cell(30, 8, "Customers", 0, 1, "R", 1)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(0, 0, 0)
        fill = False
        for _, row in grp.iterrows():
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(90, 7, _pdf_text(row[primary_col])[:45], 0, 0, "L", fill)
            pdf.cell(40, 7, format_currency_pdf(float(row["Revenue"])), 0, 0, "R", fill)
            pdf.cell(30, 7, str(int(row["Orders"])), 0, 0, "R", fill)
            pdf.cell(30, 7, str(int(row["Customers"])), 0, 1, "R", fill)
            fill = not fill
        pdf.ln(2)

    # Pivot table (primary x secondary)
    if include_pivot and primary_col and secondary_col and secondary_col != primary_col:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, _pdf_text(f"5. Breakdown: {primary_col} -> {secondary_col}"), 0, 1)

        top_primary = df.groupby(primary_col)["AMOUNT"].sum().sort_values(ascending=False).head(8).index.tolist()
        top_secondary = df.groupby(secondary_col)["AMOUNT"].sum().sort_values(ascending=False).head(6).index.tolist()
        sub = df[df[primary_col].isin(top_primary) & df[secondary_col].isin(top_secondary)]
        if not sub.empty:
            pivot = sub.pivot_table(index=primary_col, columns=secondary_col, values="AMOUNT", aggfunc="sum", fill_value=0)
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

    def cell(self, w=None, h=None, txt="", border=0, ln=0, align="", fill=False, link="", **kwargs):
        if w is not None and 0 < abs(w) < _MIN_CELL_W:
            w = _MIN_CELL_W
        txt = _pdf_text(txt)
        super().cell(w=w, h=h, txt=txt, border=border, ln=ln, align=align, fill=fill, link=link, **kwargs)

    def multi_cell(self, w, h=None, txt="", border=0, align="J", fill=False, **kwargs):
        if w is not None and 0 < abs(w) < _MIN_CELL_W:
            w = _MIN_CELL_W
        txt = _pdf_text(txt)
        super().multi_cell(w=w, h=h, txt=txt, border=border, align=align, fill=fill, **kwargs)

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
        self.cell(0, 10, 'ELETTRO INTELLIGENCE', 0, 0, 'L')
        
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
        self.cell(0, 10, f'CONFIDENTIAL | Page {self.page_no()} | Generated by ELETTRO Intelligence', 0, 0, 'C')

    def create_cover_page(self, customer_name, sub_title="Analysis Period: YTD"):
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
        
        # Period info
        self.ln(10)
        self.set_font("Arial", '', 12)
        self.set_text_color(80, 80, 80)
        self.cell(120, 10, sub_title, 0, 1)
        self.cell(120, 8, f"Generated: {datetime.now().strftime('%d %B %Y')}", 0, 1)
        
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
        self.cell(200, 10, "ELETTRO INTELLIGENCE", 0, 0, "R")

        # Title (centered, premium look)
        self.set_text_color(218, 165, 32)
        self.set_font("Arial", "B", 30)
        self.set_xy(0, 95)
        self.cell(210, 12, "DISTRIBUTOR STRATEGY", 0, 1, "C")

        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 20)
        self.set_xy(0, 112)
        self.cell(210, 10, "REPORT", 0, 1, "C")

        # Customer + period
        self.set_text_color(218, 165, 32)
        self.set_font("Arial", "B", 14)
        self.set_xy(0, 140)
        self.cell(210, 8, _pdf_text(customer_name).upper(), 0, 1, "C")

        self.set_text_color(200, 200, 200)
        self.set_font("Arial", "", 10)
        self.set_xy(0, 152)
        self.cell(210, 6, f"Analysis Period: {_pdf_text(analysis_period)}", 0, 1, "C")
        self.set_xy(0, 160)
        self.cell(210, 6, f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}", 0, 1, "C")

        # Subtle footer note (must stay above page-break threshold)
        self.set_text_color(140, 140, 140)
        self.set_font("Arial", "", 8)
        self.set_xy(0, 274)
        self.cell(210, 5, "CONFIDENTIAL • For internal use only", 0, 0, "C")

        # Restore normal page-break behavior for subsequent pages
        self.set_auto_page_break(auto=prev_auto, margin=prev_margin)
        self._suppress_header_footer = False

def create_chart(fig):
    for ax in fig.get_axes():
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, linestyle='--', alpha=0.6, color='#dddddd')
        ax.tick_params(axis='both', which='major', labelsize=10)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        # Lower DPI to reduce PDF generation time while keeping charts readable
        fig.savefig(tmp.name, bbox_inches='tight', dpi=150, facecolor='white')
        return tmp.name


def generate_distributor_strategy_pdf(
    df: pd.DataFrame,
    customer_name: str,
    analysis_period: str = "YTD",
) -> bytes:
    """
    Generates the usual Distributor Strategy Report: cover (DISTRIBUTOR STRATEGY REPORT + customer + FY),
    Efficiency & Consolidation (scatter + zone + Top 10 table), Executive Summary (KPIs, Top Material Groups, Insights).
    """
    # Distributor Strategy Report: cover + performance summary (no consolidation page).
    if df.empty:
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.report_label = "Distributor Strategy Report"
        pdf.create_distributor_cover_page(_pdf_text(customer_name), _pdf_text(analysis_period))
        pdf.set_text_color(200, 200, 200)
        pdf.set_font("Arial", "", 11)
        pdf.set_xy(0, 185)
        pdf.cell(210, 8, "No data available for the selected filters.", 0, 0, "C")
        return _pdf_to_bytes(pdf)

    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.report_label = "Distributor Strategy Report"
    pdf.create_distributor_cover_page(_pdf_text(customer_name), _pdf_text(analysis_period))

    # Page 2: Performance summary (Product mix + recommendations)
    total_rev = float(df["AMOUNT"].sum()) if "AMOUNT" in df.columns else 0.0
    total_orders = int(df["INVOICE_NO"].nunique()) if "INVOICE_NO" in df.columns else 0
    avg_order = total_rev / max(total_orders, 1)
    product_categories = int(df[grp_col].nunique()) if grp_col in df.columns else 0

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

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

    # Product mix analysis
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, "  PRODUCT MIX ANALYSIS", 0, 1, "L", 1)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(218, 165, 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 8, "#", 1, 0, "C", True)
    pdf.cell(120, 8, "Product Category", 1, 0, "L", True)
    pdf.cell(35, 8, "Revenue", 1, 0, "R", True)
    pdf.cell(25, 8, "Share %", 1, 1, "R", True)

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    fill = False
    if grp_col in df.columns and total_rev > 0:
        mix = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(9)
        for i, (cat, amt) in enumerate(mix.items(), 1):
            share = (float(amt) / total_rev * 100.0) if total_rev > 0 else 0.0
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(10, 7, str(i), 1, 0, "C", fill)
            pdf.cell(120, 7, _pdf_text(str(cat))[:60], 1, 0, "L", fill)
            pdf.cell(35, 7, format_currency_pdf(float(amt)), 1, 0, "R", fill)
            pdf.cell(25, 7, f"{share:.1f}%", 1, 1, "R", fill)
            fill = not fill
    else:
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(190, 7, "Insufficient data for product mix analysis.", 1, 1, "L", False)

    pdf.ln(6)

    # Strategic recommendations
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, "  STRATEGIC RECOMMENDATIONS", 0, 1, "L", 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.ln(3)

    recs = []
    if grp_col in df.columns and total_rev > 0:
        top_cat = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(1)
        if len(top_cat) == 1:
            cat_name = _pdf_text(top_cat.index[0])
            cat_share = float(top_cat.iloc[0]) / total_rev * 100.0 if total_rev > 0 else 0.0
            recs.append(f"BALANCED MIX: Well-diversified product portfolio with '{cat_name[:40]}' leading at {cat_share:.1f}%.")
    recs.append(f"ORDER SIZE: Strong per-order commitment at {format_currency_pdf(avg_order)}.")
    recs.append(f"ENGAGEMENT: {total_orders} orders placed during {_pdf_text(analysis_period)}. Maintain regular follow-ups to sustain purchase frequency.")
    recs.append(f"Report generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}")

    for r in recs:
        pdf.multi_cell(0, 6, _pdf_text(r), 0, "L")

    return _pdf_to_bytes(pdf)


def generate_pdf_report(
    df: pd.DataFrame, 
    report_type: str = "Executive Summary", 
    tenant: str = "", 
    specific_entity: str = None,
    filter_customer: str = None,
    filter_state: str = None,
    filter_material: str = None
) -> bytes:
    import sys
    print("PDF_GEN - ENTERED generate_pdf_report", flush=True); sys.stdout.flush()
    
    # 1. Apply Secondary Filters (Advanced Context)
    if filter_customer and filter_customer != "All" and "CUSTOMER_NAME" in df.columns:
        df = df[df["CUSTOMER_NAME"] == filter_customer]
    
    if filter_state and filter_state != "All" and "STATE" in df.columns:
        df = df[df["STATE"] == filter_state]
        
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
                df = df[df[col] == specific_entity]
        elif report_type == "Material Wise":
            col = "ITEMNAME" if "ITEMNAME" in df.columns else "MATERIALGROUP"
            if col in df.columns:
                df = df[df[col] == specific_entity]
        elif report_type == "Material Group Wise":
            col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
            if col in df.columns:
                df = df[df[col] == specific_entity]
        elif report_type == "Month Wise" and "MONTH" in df.columns:
            df = df[df["MONTH"] == specific_entity]
        elif report_type == "State Wise" and "STATE" in df.columns:
            df = df[df["STATE"] == specific_entity]

    print("PDF_GEN - Filters applied. Creating PDF object...", flush=True); sys.stdout.flush()
    # Use the df provided. Don't filter since FastAPI applies frontend filters before passing this DF.
    pdf = PDF()
    pdf.alias_nb_pages()
    
    # Optional Cover Page
    target_name = tenant.replace('_', ' ').title() if tenant else "Management Team"
    if specific_entity and specific_entity != "All":
        target_name = str(specific_entity)

    print("PDF_GEN - Creating cover page...", flush=True); sys.stdout.flush()
    pdf.create_cover_page(target_name, f"Report Type: {report_type}")
    print("PDF_GEN - Cover page done. Adding main page...", flush=True); sys.stdout.flush()
    
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    title_text = f"Report: {report_type}"
    sub_title = "Fiscal Year Overview"
    
    if specific_entity and specific_entity != "All":
        title_text = f"Profile: {str(specific_entity)[:50]}"
        sub_title = f"{report_type} Deep Dive"
    
    # 1. Title Area
    pdf.set_text_color(33, 33, 33)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, title_text.upper(), 0, 1, 'L')
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"{sub_title} | Generated: {datetime.now().strftime('%d %B %Y')}", 0, 1, 'L')
    pdf.ln(5)

    if df.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "No data available for the selected period.", 0, 1)
        return _pdf_to_bytes(pdf)

    # 2. KPI Grid 
    print("PDF Gen - Calculating KPIs...")
    total_rev = df["AMOUNT"].sum() if "AMOUNT" in df.columns else 0
    total_orders = df["INVOICE_NO"].nunique() if "INVOICE_NO" in df.columns else 0
    total_qty = df["QUANTITY"].sum() if "QUANTITY" in df.columns else 0
    avg_order = total_rev / total_orders if total_orders > 0 else 0

    print("PDF Gen - Adding KPI Grid to PDF...")
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
    print("PDF_GEN - Starting Monthly Trend Graph...", flush=True); sys.stdout.flush()
    if "MONTH" in df.columns and "AMOUNT" in df.columns:
        trend = df.groupby("MONTH")["AMOUNT"].sum().reset_index()
        try:
            trend["SortKey"] = pd.to_datetime(trend["MONTH"], format="%b-%y", errors='coerce')
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
        for label in ax.get_xticklabels():
            label.set_ha('right')
            label.set_rotation_mode('anchor')
        # Annotate only when few points to keep render fast
        if len(trend) <= 12:
            for i, (x, y) in enumerate(zip(trend["MONTH"], trend["AMOUNT"])):
                ax.annotate(format_currency_pdf(y), (x, y), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=7,
                            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#dddddd", alpha=0.8))

        print("PDF_GEN - Saving trend chart...", flush=True); sys.stdout.flush()
        img_path = create_chart(fig)
        print("PDF_GEN - Trend chart saved.", flush=True); sys.stdout.flush()
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. Revenue Trend", 0, 1)
        pdf.image(img_path, x=10, w=190)
        os.remove(img_path)
        pdf.ln(5)

    print("PDF_GEN - Starting Page 2: Distribution...", flush=True); sys.stdout.flush()
    # --- Page 2: Distribution ---
    pdf.add_page()
    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    item_col = "ITEMNAME" if "ITEMNAME" in df.columns else "MATERIALGROUP"
    
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
        
        pdf.image(img_path, x=10, w=180)
        os.remove(img_path)
        pdf.ln(5)

    print("PDF_GEN - Starting Horizontal Bar chart...", flush=True); sys.stdout.flush()
    # Top items Horizontal Bar
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
    ax.set_xlabel("Revenue (INR)", fontsize=11, fontweight='bold')
    ax.set_ylabel(None)
    for i, v in enumerate(sorted_items.values):
        ax.text(v + (max(sorted_items.values) * 0.01), i, format_currency_pdf(v), va='center', fontsize=9)
        
    fig.tight_layout()
    img_path = create_chart(fig)
    
    pdf.image(img_path, x=10, w=190)
    os.remove(img_path)
    pdf.ln(10)

    # 6. Detailed Breakdown Table
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "5. Detailed Breakdown", 0, 1)
    
    # Table Header (Dark Theme)
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 10, "Item Description", 0, 0, 'L', 1)
    pdf.cell(45, 10, "Category", 0, 0, 'L', 1)
    pdf.cell(45, 10, "Revenue", 0, 1, 'R', 1)
    
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(0, 0, 0)
    
    # Top 25 items for table
    detailed_data = df.groupby([item_col, grp_col])["AMOUNT"].sum().reset_index().sort_values(by="AMOUNT", ascending=False).head(25)
    
    fill = False
    for idx, row in detailed_data.iterrows():
        pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
        
        name = str(row[item_col])[:55]
        grp = str(row[grp_col])[:20]
        amt = format_currency_pdf(row["AMOUNT"])
        
        pdf.cell(100, 8, name, 0, 0, 'L', fill)
        pdf.cell(45, 8, grp, 0, 0, 'L', fill)
        pdf.cell(45, 8, amt, 0, 1, 'R', fill)
        fill = not fill
        
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # --- Page 3: YoY & Deep Dive ---
    if "FINANCIAL_YEAR" in df.columns:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "5. Fiscal Year (FY) Analysis", 0, 1)
        pdf.ln(2)

        fy_stats = df.groupby("FINANCIAL_YEAR").agg(Revenue=("AMOUNT", "sum"), Orders=("INVOICE_NO", "nunique")).sort_index()

        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(40, 10, "Fiscal Year", 0, 0, 'C', 1)
        pdf.cell(50, 10, "Total Revenue", 0, 0, 'C', 1)
        pdf.cell(40, 10, "Total Orders", 0, 0, 'C', 1)
        pdf.cell(50, 10, "YoY Growth", 0, 1, 'C', 1)
        
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        
        prev_rev = 0
        fill = False
        for fy, row in fy_stats.iterrows():
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            growth = ((row['Revenue'] - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0
            growth_str = f"{growth:+.1f}%" if prev_rev > 0 else "-"
            
            pdf.cell(40, 8, fy, 0, 0, 'C', fill)
            pdf.cell(50, 8, format_currency_pdf(row['Revenue']), 0, 0, 'R', fill)
            pdf.cell(40, 8, str(row['Orders']), 0, 0, 'C', fill)
            pdf.cell(50, 8, growth_str, 0, 1, 'C', fill)
            prev_rev = row['Revenue']
            fill = not fill
        pdf.ln(5)

        # FY Comparison Chart (Multi-line Year-over-Year)
        if "MONTH" in df.columns and "DATE" in df.columns:
            try:
                df['Month_Num'] = pd.to_datetime(df['DATE']).dt.month
                df['Month_Name'] = pd.to_datetime(df['DATE']).dt.strftime('%b')
                
                fy_trend = df.groupby(['FINANCIAL_YEAR', 'Month_Num', 'Month_Name'])['AMOUNT'].sum().reset_index()
                fy_trend.sort_values('Month_Num', inplace=True)
                
                fig = Figure(figsize=(10, 5))
                canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)
                fig.patch.set_facecolor('white')
                ax.set_facecolor('white')
                
                for fy in fy_trend['FINANCIAL_YEAR'].unique():
                    fy_data = fy_trend[fy_trend['FINANCIAL_YEAR'] == fy]
                    ax.plot(fy_data['Month_Name'], fy_data['AMOUNT'], marker='o', label=fy, linewidth=2.5, markersize=6)
                
                ax.set_title("Year-Over-Year Revenue Trends", fontsize=14, fontweight='bold', pad=15)
                ax.legend(fontsize=10)
                ax.set_xlabel("Month", fontsize=11, fontweight='bold')
                ax.set_ylabel("Revenue", fontsize=11, fontweight='bold')
                ax.tick_params(axis='x', rotation=45)
                
                img_path = create_chart(fig)
                
                pdf.image(img_path, x=10, w=190)
                os.remove(img_path)
                pdf.ln(5)
            except Exception:
                pass  # Skip if date parsing fails

    # 8. Material Group Deep Dive
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "6. Material Group Deep Dive", 0, 1)
    pdf.ln(5)

    if grp_col in df.columns:
        group_summary = df.groupby(grp_col).agg(
            Total_Revenue=("AMOUNT", "sum"),
            Top_Item=(item_col, lambda x: x.mode()[0] if not x.mode().empty else "N/A"),
            Order_Count=("INVOICE_NO", "nunique")
        ).sort_values(by="Total_Revenue", ascending=False).head(8) 
        
        for group_name, row in group_summary.iterrows():
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

    # 9. Customer Specific Enhancement: Material Group Preference
    if report_type == "Customer Wise":
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "7. Material Group Preference", 0, 1)
        pdf.ln(5)
        
        mat_grp_data = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(15)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(120, 10, "Material Group", 0, 0, 'L', 1)
        pdf.cell(50, 10, "Revenue", 0, 1, 'R', 1)
        
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        
        fill = False
        for grp, amt in mat_grp_data.items():
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(120, 8, str(grp)[:60], 0, 0, 'L', fill)
            pdf.cell(50, 8, format_currency_pdf(amt), 0, 1, 'R', fill)
            fill = not fill

    # 10. Material Group Specific Enhancement: Top Customers
    if report_type == "Material Group Wise":
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "7. Top 10 Customers", 0, 1)
        pdf.ln(5)
        
        if "CUSTOMER_NAME" in df.columns:
            cust_data = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(15)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(33, 37, 41)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(120, 10, "Customer Name", 0, 0, 'L', 1)
            pdf.cell(50, 10, "Revenue", 0, 1, 'R', 1)
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            
            fill = False
            for cust, amt in cust_data.items():
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(120, 8, str(cust)[:60], 0, 0, 'L', fill)
                pdf.cell(50, 8, format_currency_pdf(amt), 0, 1, 'R', fill)
                fill = not fill

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
    
    # Top 5 Customers
    if "CUSTOMER_NAME" in df.columns:
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "  TOP 5 CUSTOMERS", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        pdf.ln(2)
        
        top5_cust = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(5)
        fill = False
        for i, (cust, amt) in enumerate(top5_cust.items(), 1):
            share = (amt / total_rev * 100) if total_rev > 0 else 0
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(10, 7, f"{i}.", 0, 0, 'C', fill)
            pdf.cell(100, 7, str(cust)[:50], 0, 0, 'L', fill)
            pdf.cell(40, 7, format_currency_pdf(amt), 0, 0, 'R', fill)
            pdf.cell(30, 7, f"{share:.1f}%", 0, 1, 'R', fill)
            fill = not fill
        pdf.ln(5)
    
    # Top 5 Material Groups
    if grp_col in df.columns:
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(33, 37, 41)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "  TOP 5 MATERIAL GROUPS", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        pdf.ln(2)
        
        top5_grp = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(5)
        fill = False
        for i, (grp, amt) in enumerate(top5_grp.items(), 1):
            share = (amt / total_rev * 100) if total_rev > 0 else 0
            pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(10, 7, f"{i}.", 0, 0, 'C', fill)
            pdf.cell(100, 7, str(grp)[:50], 0, 0, 'L', fill)
            pdf.cell(40, 7, format_currency_pdf(amt), 0, 0, 'R', fill)
            pdf.cell(30, 7, f"{share:.1f}%", 0, 1, 'R', fill)
            fill = not fill
        pdf.ln(5)
    
    # Auto-Generated Insights
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

    # Geographic insight
    if "STATE" in df.columns and not df.empty:
        num_states = df["STATE"].nunique()
        top_state = df.groupby("STATE")["AMOUNT"].sum().idxmax()
        insights.append(f"GEOGRAPHY: Active across {num_states} states. Top state: {top_state}.")
    
    insights.append(f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}")

    for insight in insights:
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(5, 7, "", 0, 0)
        if ":" in insight:
            pdf.cell(0, 7, insight, 0, 1, 'L')
        else:
            pdf.set_font("Arial", '', 9)
            pdf.cell(0, 7, insight, 0, 1, 'L')

    return _pdf_to_bytes(pdf)

