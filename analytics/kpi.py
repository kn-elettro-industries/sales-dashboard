import streamlit as st
from .utils import format_indian_currency

def render_kpi_card(title, value, delta=None, icon="📊"):
    """
    Renders a premium KPI card using HTML/CSS.
    """
    delta_html = ""
    if delta:
        clean_delta = str(delta).replace("%", "").replace(" MoM", "").replace(" (MTD)", "").replace(" (New)", "")
        try:
            val = float(clean_delta)
        except ValueError:
            val = -1 if "-" in str(delta) else 1
            
        color = "#2ecc71" if "+" in str(delta) or val >= 0 else "#e74c3c"
        delta_html = f'<p style="color: {color}; font-size: 0.9rem; margin: 0;">{delta}</p>'

    html_code = f"""
<div style="background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; min-width: 0; overflow: hidden;"><div style="display: flex; justify-content: space-between; align-items: start; gap: 8px;"><div style="min-width: 0; flex: 1;"><p style="color: #8b949e; font-size: 0.75rem; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500;">{title}</p><h2 style="color: #f0f6fc; margin: 0; font-size: 1.5rem; white-space: nowrap; font-weight: 700; font-variant-numeric: tabular-nums;">{value}</h2>{delta_html}</div><div style="font-size: 1.2rem; color: #FFD700; flex-shrink: 0; font-weight: 700; opacity: 0.4;">{icon}</div></div></div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_kpis(df):
    total_sales = df["AMOUNT"].sum()
    total_qty = df["QTY"].sum()
    total_invoices = df["INVOICE_NO"].nunique()

    # True Month-to-Date (MTD) vs Previous Month-to-Date calculation
    growth = 0
    delta_label = "0% MoM"
    
    if "DATE" in df.columns and not df.empty:
        # Find the absolute latest date in the dataset
        max_date = df["DATE"].max()
        
        try:
            current_month_start = max_date.replace(day=1)
            # Find the same day last month
            if max_date.month == 1:
                prev_month_end_date = max_date.replace(year=max_date.year - 1, month=12)
            else:
                try:
                    prev_month_end_date = max_date.replace(month=max_date.month - 1)
                except ValueError:
                    # E.g. March 31 -> Feb 28
                    import calendar
                    last_day = calendar.monthrange(max_date.year, max_date.month - 1)[1]
                    prev_month_end_date = max_date.replace(month=max_date.month - 1, day=last_day)
                    
            prev_month_start = prev_month_end_date.replace(day=1)

            # Sum revenues for the exact date ranges
            current_mtd_sales = df[(df["DATE"] >= current_month_start) & (df["DATE"] <= max_date)]["AMOUNT"].sum()
            prev_mtd_sales = df[(df["DATE"] >= prev_month_start) & (df["DATE"] <= prev_month_end_date)]["AMOUNT"].sum()

            if prev_mtd_sales > 0:
                growth = ((current_mtd_sales - prev_mtd_sales) / prev_mtd_sales) * 100
                delta_label = f"{growth:+.1f}% (MTD)"
            elif current_mtd_sales > 0:
                delta_label = "+100% (New)"
            else:
                delta_label = "0% (MTD)"
        except Exception as e:
            # Fallback if date logic fails
            pass

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card("Total Revenue", format_indian_currency(total_sales), delta_label, "R")
    
    with col2:
        render_kpi_card("Total Invoices", f"{total_invoices:,}", icon="#")
        
    with col3:
        # Format Qty with K/L/Cr but no symbol
        render_kpi_card("Total Quantity", format_indian_currency(total_qty, ""), icon="Q")
        
    with col4:
        avg_val = (total_sales / total_invoices) if total_invoices else 0
        render_kpi_card("Avg Order Value", format_indian_currency(avg_val), icon="A")
