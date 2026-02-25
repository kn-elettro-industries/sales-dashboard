import streamlit as st
from .utils import format_indian_currency

def render_kpi_card(title, value, delta=None, icon="📊"):
    """
    Renders a premium KPI card using HTML/CSS.
    """
    delta_html = ""
    if delta:
        color = "#2ecc71" if "+" in str(delta) or float(str(delta).replace("%","").replace(" MoM","")) >= 0 else "#e74c3c"
        delta_html = f'<p style="color: {color}; font-size: 0.9rem; margin: 0;">{delta}</p>'

    html_code = f"""
<div class="css-card"><div style="display: flex; justify-content: space-between; align-items: start;"><div><p style="color: #a1a1aa; font-size: 0.9rem; margin-bottom: 5px;">{title}</p><h2 style="color: #ffffff; margin: 0; font-size: 1.8rem;">{value}</h2>{delta_html}</div><div style="font-size: 2rem; opacity: 0.8;">{icon}</div></div></div>
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
        render_kpi_card("Total Revenue", format_indian_currency(total_sales), delta_label, "💰")
    
    with col2:
        render_kpi_card("Total Invoices", f"{total_invoices:,}", icon="🧾")
        
    with col3:
        # Format Qty with K/L/Cr but no symbol
        render_kpi_card("Total Quantity", format_indian_currency(total_qty, ""), icon="📦")
        
    with col4:
        avg_val = (total_sales / total_invoices) if total_invoices else 0
        render_kpi_card("Avg Order Value", format_indian_currency(avg_val), icon="💎")
