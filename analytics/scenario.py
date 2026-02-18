import streamlit as st
import pandas as pd
import plotly.express as px

def render_scenario_planner(df):
    st.subheader("🎯 'What-If' Scenario Planner")
    st.caption("Simulate price changes to see the projected impact on **Revenue** based on product elasticity.")

    # Data Check
    if "QTY" not in df.columns or "AMOUNT" not in df.columns:
        st.warning("Data must contain 'QTY' and 'AMOUNT'.")
        return

    # 1. Product Selection
    # Group by Item Group to make simulation meaningful
    if "ITEM_NAME_GROUP" in df.columns:
        prod_col = "ITEM_NAME_GROUP"
    elif "ITEMNAME" in df.columns:
        prod_col = "ITEMNAME"
    else:
        prod_col = "MATERIALGROUP"

    # Get Top Products
    product_stats = df.groupby(prod_col).agg(
        Total_Revenue=("AMOUNT", "sum"),
        Total_Qty=("QTY", "sum")
    ).sort_values("Total_Revenue", ascending=False).head(50)

    top_products = product_stats.index.tolist()
    
    selected_product = st.selectbox("Select Product to Simulate:", top_products)

    if not selected_product:
        return

    # 2. Baseline Metrics
    current_rev = product_stats.loc[selected_product, "Total_Revenue"]
    current_qty = product_stats.loc[selected_product, "Total_Qty"]
    current_avg_price = current_rev / current_qty if current_qty > 0 else 0

    st.markdown("### 📊 Baseline Performance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Revenue", f"₹ {current_rev:,.0f}")
    c2.metric("Current Volume", f"{current_qty:,.0f} units")
    c3.metric("Avg Unit Price", f"₹ {current_avg_price:,.2f}")

    st.markdown("---")

    # 3. Simulation Controls
    st.markdown("### 🎛️ Simulation Controls")
    
    price_change_pct = st.slider(
        "Adjust Price (%)", 
        min_value=-20, 
        max_value=20, 
        value=0, 
        step=1,
        format="%d%%",
        help="Simulate a price increase or decrease."
    )
    
    # Elasticity Assumption (Simplified for MVP)
    # In a real app, this would be calculated per product.
    # Default -1.5 (Elastic)
    elasticity = st.slider(
        "Assumed Price Elasticity", 
        min_value=-3.0, 
        max_value=-0.1, 
        value=-1.5,
        step=0.1,
        help="-1.0 = Unit Elastic. < -1.0 = Elastic (Volume drops faster than price rises)."
    )

    # 4. Calculate Projections
    # Formula: Qty New = Qty Old * (1 + Elasticity * %Price Change)
    pct_decimal = price_change_pct / 100
    
    projected_qty = current_qty * (1 + (elasticity * pct_decimal))
    
    # Ensure non-negative qty
    projected_qty = max(0, projected_qty)
    
    projected_price = current_avg_price * (1 + pct_decimal)
    projected_rev = projected_qty * projected_price
    
    diff_rev = projected_rev - current_rev

    # 5. Visualize Impact
    st.markdown("### 🚀 Projected Impact")
    
    pc1, pc2, pc3 = st.columns(3)
    
    pc1.metric(
        "New Unit Price", 
        f"₹ {projected_price:,.2f}", 
        f"{price_change_pct}%"
    )
    
    pc2.metric(
        "Projected Volume", 
        f"{projected_qty:,.0f}", 
        f"{(projected_qty - current_qty):,.0f} units",
        delta_color="normal" # Context dependent
    )
    
    pc3.metric(
        "Projected Revenue", 
        f"₹ {projected_rev:,.0f}", 
        f"{diff_rev:+,.0f}",
        delta_color="normal"
    )

    # Chart Comparison
    impact_data = pd.DataFrame({
        "Scenario": ["Baseline", "Simulated"],
        "Revenue": [current_rev, projected_rev],
        "Color": ["#555555", "#FFD700" if diff_rev >= 0 else "#ff4b4b"]
    })
    
    fig = px.bar(
        impact_data,
        x="Scenario",
        y="Revenue",
        color="Color",
        color_discrete_map="identity",
        title=f"Revenue Impact: {selected_product}",
        template="corporate_black",
        text_auto=".2s"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    if diff_rev > 0:
        st.success(f"✅ Strategy Win: Increasing price by {price_change_pct}% yields ₹ {diff_rev:,.0f} more revenue.")
    elif diff_rev < 0:
        st.warning(f"⚠️ Strategy Risk: Increasing price by {price_change_pct}% causes volume drop that hurts total revenue.")
