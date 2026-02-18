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

    monthly_sales = df.groupby("MONTH")["AMOUNT"].sum().sort_index()
    
    growth = 0
    if len(monthly_sales) > 1:
        last_month = monthly_sales.iloc[-1]
        prev_month = monthly_sales.iloc[-2]
        growth = ((last_month - prev_month) / prev_month) * 100 if prev_month != 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card("Total Revenue", format_indian_currency(total_sales), f"{growth:+.1f}% MoM", "💰")
    
    with col2:
        render_kpi_card("Total Invoices", f"{total_invoices:,}", icon="🧾")
        
    with col3:
        # Format Qty with K/L/Cr but no symbol
        render_kpi_card("Total Quantity", format_indian_currency(total_qty, ""), icon="📦")
        
    with col4:
        avg_val = (total_sales / total_invoices) if total_invoices else 0
        render_kpi_card("Avg Order Value", format_indian_currency(avg_val), icon="💎")
