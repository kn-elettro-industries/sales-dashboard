import streamlit as st
import pandas as pd
import plotly.express as px
from .utils import format_indian_currency

def render_elasticity(df):
    """
    Renders Price Elasticity of Demand (PE) Analysis.
    Plots Unit Price vs Quantity to show demand curves.
    """
    st.subheader("📉 Price Elasticity (PE) Analysis")
    st.caption("Analyze how changes in **Unit Price** affect **Sales Volume (Quantity)**. Steeper slopes indicate higher sensitivity.")

    if "QTY" not in df.columns or "AMOUNT" not in df.columns:
        st.warning("Data must contain 'QTY' and 'AMOUNT' columns for PE Analysis.")
        return

    # 1. Calculate Unit Price
    # Filter out returns (negative qty) and zero vals
    pe_df = df[(df["QTY"] > 0) & (df["AMOUNT"] > 0)].copy()
    pe_df["UNIT_PRICE"] = pe_df["AMOUNT"] / pe_df["QTY"]

    # 2. Select Product for Deep Dive
    # Hierarchical Selection: Material Group -> Item Name Group
    
    # Step A: Select Material Group
    if "MATERIALGROUP" in df.columns:
        material_groups = sorted(pe_df["MATERIALGROUP"].unique().tolist())
        selected_material = st.selectbox("Step 1: Select Material Group", material_groups)
        
        # Filter for next step
        pe_df = pe_df[pe_df["MATERIALGROUP"] == selected_material]
    
    # Step B: Select Item Group / Item
    if "ITEM_NAME_GROUP" in df.columns:
        prod_col = "ITEM_NAME_GROUP"
    elif "ITEMNAME" in df.columns:
        prod_col = "ITEMNAME"
    else:
        prod_col = "MATERIALGROUP" # Fallback if no item level info
    
    # Get Top Products within selected Material Group
    top_products = pe_df.groupby(prod_col)["AMOUNT"].sum().sort_values(ascending=False).head(50).index.tolist()
    
    selected_product = st.selectbox("Step 2: Select Item / Item Group", top_products)

    if selected_product:
        prod_data = pe_df[pe_df[prod_col] == selected_product]
        
        if prod_data.empty:
            st.warning(f"No valid transaction data for {selected_product}")
            return
            
        # 3. Create Scatter Plot (Price vs Qty)
        # We group by Unit Price to see total volume at that price point
        # Round price to avoid too much noise (e.g. 10.01 vs 10.02)
        prod_data["PRICE_BIN"] = prod_data["UNIT_PRICE"].round(0)
        
        curve_data = prod_data.groupby("PRICE_BIN").agg(
            TOTAL_QTY=("QTY", "sum"),
            TXN_COUNT=("QTY", "count")
        ).reset_index()

        fig = px.scatter(
            curve_data,
            x="PRICE_BIN",
            y="TOTAL_QTY",
            size="TXN_COUNT",
            title=f"Demand Curve: {selected_product}",
            labels={"PRICE_BIN": "Unit Price (₹)", "TOTAL_QTY": "Total Quantity Sold"},
            trendline="lowess", # Locally Weighted Scatterplot Smoothing
            trendline_color_override="#FFD700",
            template="corporate_black"
        )
        
        fig.update_traces(marker=dict(line=dict(width=1, color='white'), opacity=0.8))
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("""
            <div class="css-card">
                <h4>📊 Analysis Guide</h4>
                <p><strong>Downward Slope:</strong> Normal behavior. Higher price = Lower demand.</p>
                <p><strong>Flat Slope:</strong> Inelastic. Customers buy regardless of price (Essential goods).</p>
                <p><strong>Vertical Slope:</strong> Highly Elastic. Small price change = Huge volume drop.</p>
            </div>
            """, unsafe_allow_html=True)

            avg_price = prod_data["UNIT_PRICE"].mean()
            st.metric("Avg Unit Price", format_indian_currency(avg_price))
            st.metric("Price Variance", format_indian_currency(prod_data['UNIT_PRICE'].std()))
