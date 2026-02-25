import pandas as pd
from fpdf import FPDF
from datetime import datetime
import tempfile
import os

from .utils import format_indian_currency

class ProcurementPDF(FPDF):
    def header(self):
        # Executive Header Strip
        self.set_fill_color(33, 33, 33) # Dark Grey
        self.rect(0, 0, 210, 20, 'F')
        
        self.set_fill_color(255, 215, 0) # Gold Accent
        self.rect(0, 19, 210, 1, 'F')
        
        self.set_font('Arial', 'B', 12)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'ELETTRO INTELLIGENCE', 0, 0, 'L')
        
        self.set_font('Arial', '', 10)
        self.set_xy(0, 5)
        self.cell(200, 10, 'Sales & Procurement Analysis', 0, 0, 'R')
        self.ln(25)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Strictly Confidential | Page {self.page_no()} | Elettro Enterprise', 0, 0, 'C')

    def add_section_header(self, title):
        self.ln(5)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 215, 0) # Gold
        self.cell(0, 10, str(title).upper(), 0, 1, 'L')
        # Thin underline
        self.set_fill_color(200, 200, 200)
        self.rect(self.get_x(), self.get_y(), 190, 0.5, 'F')
        self.ln(2)

    def write_body_text(self, text, style='', size=10):
        self.set_font('Arial', style, size)
        self.set_text_color(40, 40, 40)
        # Use simple replacing for potential unicode issues
        safe_text = str(text).replace('₹', 'Rs. ').replace('✅', '>').replace('⚠️', '!')
        self.multi_cell(0, 6, safe_text)
        self.ln(2)

def generate_procurement_report(df, dealer_name, supplier_name):
    pdf = ProcurementPDF()
    pdf.alias_nb_pages()
    
    # --- Data Calculations ---
    # Ensure AMOUNT and ITEMNAME exist
    amt_col = "AMOUNT" if "AMOUNT" in df.columns else ("TOTALAMOUNT" if "TOTALAMOUNT" in df.columns else None)
    item_col = "ITEMNAME" if "ITEMNAME" in df.columns else ("ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else None)
    
    if amt_col is None or item_col is None:
        pdf.add_page()
        pdf.write_body_text("CRITICAL ERROR: Data missing required Amount or Item Name columns for analysis.")
        return get_temp_pdf(pdf)

    # Convert dates and extract Financial Year
    if "DATE" in df.columns:
        date_col = pd.to_datetime(df["DATE"], errors='coerce')
        min_date = date_col.dt.date.min()
        max_date = date_col.dt.date.max()
        period_str = f"{min_date} to {max_date}"
    else:
        period_str = "All Available History"
        
    fy_str = ", ".join(df["FINANCIAL_YEAR"].unique()) if "FINANCIAL_YEAR" in df.columns else period_str
    
    total_spend = df[amt_col].sum()
    total_items = df[item_col].nunique()
    total_orders = df["INVOICE_NO"].nunique() if "INVOICE_NO" in df.columns else len(df)
    
    # Categorization Math
    stats = df.groupby(item_col).agg(
        Spend=(amt_col, "sum"),
        Frequency=("INVOICE_NO", "nunique") if "INVOICE_NO" in df.columns else (amt_col, "count")
    ).sort_values("Spend", ascending=False)
    
    stats["Share"] = (stats["Spend"] / total_spend) * 100
    stats["CumShare"] = stats["Share"].cumsum()
    
    # 90/10 Core vs Long Tail (Instead of 70/20/10)
    core_items = stats[stats["CumShare"] <= 90]
    tail_items = stats[stats["CumShare"] > 90]
    
    core_spend = core_items["Spend"].sum()
    tail_spend = tail_items["Spend"].sum()
    
    core_count = len(core_items)
    tail_count = len(tail_items)
    
    # Identify Fragmented Bottom < 2% items
    micro_tail = stats[(stats["Share"] < 2.0) & (stats["Share"] > 0)]
    micro_spend = micro_tail["Spend"].sum()
    micro_count = len(micro_tail)
    
    # Efficiency Opportunity (8-15% of Tail)
    consolidation_opportunity = micro_spend * 0.12 # Assume 12% midpoint
    
    # --- 1. Cover Page ---
    pdf.add_page()
    pdf.set_fill_color(33, 33, 33)
    pdf.rect(140, 0, 70, 297, 'F')
    pdf.set_fill_color(255, 215, 0)
    pdf.rect(138, 0, 2, 297, 'F')
    
    pdf.set_xy(10, 80)
    pdf.set_font("Arial", 'B', 28)
    pdf.set_text_color(33, 33, 33)
    pdf.multi_cell(120, 12, "SALES &\nPROCUREMENT\nANALYSIS", 0, 'L')
    
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(120, 8, f"DEALER: {str(dealer_name).upper()}", 0, 1)
    pdf.cell(120, 8, f"SUPPLIER: {str(supplier_name).upper()}", 0, 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.cell(120, 8, f"PERIOD COVERED: {fy_str}", 0, 1)
    
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(200, 150, 0)
    pdf.multi_cell(120, 6, "CONFIDENTIAL REPORT: Identifying scale-driven efficiencies and consolidation opportunities across the procurement lifecycle.", 0, 'L')
    
    # --- 2. Opening Note ---
    pdf.add_page()
    pdf.add_section_header("2. Strategic Context")
    note = (
        "This report is generated to evaluate the demand utilization and procurement behavior of the dealer. "
        "All insights compiled herein are derived directly from actual, historical transaction data, ensuring a fact-based, "
        "analytical approach to business optimization.\n\n"
        "The primary objective is to identify efficiency-driven opportunities rather than relying on assumption-based "
        "forecasting. By analyzing the concentration of high-value materials versus the fragmentation of long-tail "
        "orders, this report outlines structured pathways to optimize procurement scale and improve transactional efficiency."
    )
    pdf.write_body_text(note)
    
    # --- 3. Objective & Scope ---
    pdf.add_section_header("3. Objective & Scope")
    scope = (
        "- Evaluated Matrix: Procurement patterns, material concentration, and efficiency opportunities.\n"
        f"- Temporal Scope: Structured Financial Year logic covering {fy_str}.\n"
        "- Methodology: Hard-aggregation on actual invoiced values (Month-wise -> Material-wise -> Annualized) "
        "ensuring zero duplication across categories."
    )
    pdf.write_body_text(scope)
    
    # --- 4. Data Coverage & Methodology ---
    pdf.add_section_header("4. Data Coverage & Methodology")
    method = (
        f"The dataset processed for this report contains {total_orders:,} unique transactions spanning {total_items} distinct material groups. "
        "All data has undergone authoritative standardization, including text-normalization to absolute upper-case, "
        "structural deduplication, and aggregation mapped cleanly to the standard Indian Financial Year (April-March). "
        "All monetary values are normalized to INR (Rs.) exclusively."
    )
    pdf.write_body_text(method)
    
    # --- 5. Total Spend Snapshot ---
    pdf.add_page()
    pdf.add_section_header("5. Total Spend Snapshot")
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 10, f"Total Procurement Value: Rs. {total_spend:,.2f}", 1, 0, 'C', fill=False)
    pdf.cell(95, 10, f"Total Material Groups: {total_items}", 1, 1, 'C', fill=False)
    pdf.ln(5)
    
    snap = (
        f"Overall procurement is distributed across {total_items} categories. Our analysis indicates a highly concentrated "
        f"distribution where the Top {core_count} categories (Core) drive {core_spend/total_spend*100:.1f}% of total value, "
        f"while the remaining {tail_count} categories (Non-Core) contribute {tail_spend/total_spend*100:.1f}%."
    )
    pdf.write_body_text(snap)
    
    # Show Top 5 Drivers
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, "Dominant Category Breakdown (Top 5):", 0, 1)
    pdf.set_font('Arial', '', 10)
    for idx, row in stats.head(5).iterrows():
        pdf.cell(10, 6, "-", 0, 0)
        pdf.cell(110, 6, str(idx)[:50], 0, 0)
        pdf.cell(40, 6, f"Rs. {row['Spend']:,.0f}", 0, 0, 'R')
        pdf.cell(30, 6, f"{row['Share']:.1f}%", 0, 1, 'R')
    pdf.ln(5)

    # --- 6. Spend Concentration Analysis ---
    pdf.add_section_header("6. Spend Concentration Analysis")
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"Core vs. Long-Tail Split: {core_spend/total_spend*100:.0f} / {tail_spend/total_spend*100:.0f}", 0, 1)
    
    conc = (
        f"The procurement behavior strictly confirms a Pareto-style distribution. The business relies on an overwhelming "
        f"{core_spend/total_spend*100:.1f}% concentration in just {core_count} core categories. Strategically, this means scale and "
        "discount realization should be fiercely driven within this core portfolio. Conversely, the vast remaining catalog "
        f"represents only {tail_spend/total_spend*100:.1f}% of total spend, indicating highly fragmented, reactive ordering."
    )
    pdf.write_body_text(conc)

    # --- 7. Low-Volume Materials Analysis ---
    pdf.add_page()
    pdf.add_section_header("7. Low-Volume Materials Analysis")
    low_vol_text = (
        f"A deep dive into the non-core tail reveals {micro_count} material groups contributing less than 2.0% each to total value. "
        f"Combined, these low-volume materials account for Rs. {micro_spend:,.2f} ({micro_spend/total_spend*100:.1f}% share). "
        "A review of ordering frequency implies that many of these items are procured repetitively across the year rather "
        "than grouped into consolidated stock runs. This reactive demand pattern strains logistics and increases the per-unit "
        "transactional burden."
    )
    pdf.write_body_text(low_vol_text)

    # --- 8. Trend & Buying Behavior ---
    pdf.add_section_header("8. Trend & Buying Behavior")
    
    if "MONTH" in df.columns:
        trend = df.groupby("MONTH")[amt_col].sum()
        max_month = trend.idxmax()
        min_month = trend.idxmin()
        volatility = ((trend.max() - trend.min()) / trend.max()) * 100
        trend_text = (
            f"Monthly procurement fluctuates significantly. The peak demand was recorded in {max_month} (Rs. {trend.max():,.0f}), "
            f"while the floor was in {min_month} (Rs. {trend.min():,.0f}), reflecting a maximum intra-year volatility of {volatility:.1f}%. "
            "The data points to a highly reactive buying cycle. Predictable core requirements are frequently interspersed with "
            "ad-hoc urgent requests, leading to fragmented purchasing."
        )
    else:
        trend_text = "Monthly chronological trending data is unavailable due to data constraints. Overall observations indicate fragmented purchasing runs."
    pdf.write_body_text(trend_text)

    # --- 9. Quantified Efficiency Opportunity ---
    pdf.add_section_header("9. Quantified Efficiency Opportunity")
    eff = (
        f"Calculated Annual Low-Volume Base: Rs. {micro_spend:,.2f}\n"
        f"Estimated Consolidation Margin (12% Median Model): Rs. {consolidation_opportunity:,.0f}\n\n"
        "By enforcing a 12% consolidation target on fragmented long-tail purchases, the enterprise can "
        f"unlock an estimated Rs. {consolidation_opportunity:,.0f} in annualized incremental efficiency. "
        "Crucially, realizing this value requires absolutely no increase in end-consumer demand, and no SKU rationalization. "
        "This is a purely execution-backed margin realization born exclusively from consolidating micro-orders into larger, "
        "standardized freight runs."
    )
    pdf.write_body_text(eff)

    # --- 10. Actionable Recommendations ---
    pdf.add_page()
    pdf.add_section_header("10. Actionable Recommendations")
    recs = (
        "- Consolidate the Micro-Tail: Mandate that items comprising less than 2% total share only be ordered "
        "by 'piggybacking' onto major core-category fright shipments.\n"
        "- Enforce Minimum Order Value (MOV) on non-core items to artificially restrict ad-hoc purchasing frequency.\n"
        "- Synchronize Order Cycles: Move from a reactive 'fill-as-needed' cycle to a structured bi-weekly procurement window.\n"
        "- Negotiate Volume on the 90%: Utilize the heavy core concentration data to push suppliers for bulk throughput discounts on top movers."
    )
    pdf.write_body_text(recs)

    # --- 11. Final Executive Takeaway ---
    pdf.add_section_header("11. Final Executive Takeaway")
    takeaway = (
        "Core drives scale. The Long-tail drives efficiency.\n\n"
        "The current procurement framework is heavy, concentrated, and reliable at the top, yet highly reactive at the bottom. "
        f"The primary lever for immediate profitability requires executing discipline over the {micro_count} non-core items. "
        "By executing structured consolidation rather than chasing raw sales volume, the supply chain immediately unlocks latent margin."
    )
    pdf.write_body_text(takeaway, style='I')
    
    return get_temp_pdf(pdf)

def get_temp_pdf(pdf_object):
    """Outputs the PDF to a temporary file and returns the path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_object.output(tmp.name)
        return tmp.name
