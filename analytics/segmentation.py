import streamlit as st
import pandas as pd
import plotly.express as px
from .utils import format_indian_currency

def render_rfm(df):
    st.subheader("RFM Segmentation")

    reference_date = df["DATE"].max()

    rfm = (
        df.groupby("CUSTOMER_NAME")
        .agg(
            Recency=("DATE", lambda x: (reference_date - x.max()).days),
            Frequency=("INVOICE_NO", "nunique"),
            Monetary=("AMOUNT", "sum")
        )
        .reset_index()
    )

    if len(rfm) >= 4:
        # Scoring
        rfm["R_Score"] = pd.qcut(rfm["Recency"], 4, labels=["Active", "At Risk", "Churning", "Lost"])
        rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 4, labels=["One-time", "Rare", "Frequent", "Loyal"])
        rfm["M_Score"] = pd.qcut(rfm["Monetary"], 4, labels=["Low", "Medium", "High", "VIP"])

        # --- 1. RFM Scorecards (New) ---
        # Define segments based on logic (simplified for immediate impact)
        rfm["Segment"] = "Standard"
        rfm.loc[(rfm["R_Score"]=="Active") & (rfm["F_Score"]=="Loyal"), "Segment"] = "Champions"
        rfm.loc[(rfm["R_Score"]=="Active") & (rfm["F_Score"]=="Frequent"), "Segment"] = "Loyal"
        rfm.loc[(rfm["R_Score"]=="At Risk") & (rfm["F_Score"].isin(["Loyal", "Frequent"])), "Segment"] = "At Risk"
        rfm.loc[rfm["R_Score"]=="Lost", "Segment"] = "Lost"
        
        # Calculate Metrics
        seg_metrics = rfm.groupby("Segment").agg(
            Count=("CUSTOMER_NAME", "count"),
            Revenue=("Monetary", "sum")
        ).to_dict("index")
        
        # Display Cards
        c1, c2, c3, c4 = st.columns(4)
        
        def show_card(col, label, key, color):
            data = seg_metrics.get(key, {"Count": 0, "Revenue": 0})
            with col:
                st.markdown(f"""
                <div class="css-card" style="border-top: 3px solid {color}; text-align: center; padding: 10px;">
                    <h3 style="margin:0; font-size: 1.2rem; color: {color};">{label}</h3>
                    <h2 style="margin:5px 0; font-size: 2rem;">{data['Count']}</h2>
                    <p style="color: #888;">{format_indian_currency(data['Revenue'])}</p>
                </div>
                """, unsafe_allow_html=True)
                
        show_card(c1, "🏆 Champions", "Champions", "#FFD700")
        show_card(c2, "💎 Loyal", "Loyal", "#00CC99")
        show_card(c3, "⚠️ At Risk", "At Risk", "#FF9900")
        show_card(c4, "💤 Lost", "Lost", "#FF4444")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Premium 3D Scatter Plot
        # Colors based on our new Segment
        color_map = {
            "Champions": "#FFD700", # Gold
            "Loyal": "#00CC99",     # Emerald
            "Standard": "#C0C0C0",  # Silver
            "At Risk": "#FF9900",   # Orange
            "Lost": "#FF4444"       # Red
        }
        
        fig = px.scatter_3d(
            rfm,
            x="Recency",
            y="Frequency",
            z="Monetary",
            color="Segment",
            size="Monetary",
            size_max=30,
            hover_name="CUSTOMER_NAME",
            hover_data={"Recency": True, "Frequency": True, "Monetary": ":.2f", "Segment": False},
            title="3D Customer Segmentation Universe",
            labels={"Recency": "Days Since Last Order", "Frequency": "Total Orders", "Monetary": "Total Spent"},
            color_discrete_map=color_map,
            template="corporate_black",
            opacity=0.8
        )
        
        fig.update_layout(scene_camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)))
        st.plotly_chart(fig, use_container_width=True)

        # 3. Action Matrix (New)
        st.subheader("🚀 Strategic Action Matrix")
        
        col_act1, col_act2 = st.columns([2, 1])
        
        with col_act1:
            st.info("🎯 **Recommended Actions** based on customer behavior.")
            action_data = [
                {"Segment": "🏆 Champions", "Action": "Upsell New Products", "Strategy": "invite to VIP events, offer exclusive previews."},
                {"Segment": "💎 Loyal", "Action": "Cross-Sell", "Strategy": "Suggest complementary products to increase basket size."},
                {"Segment": "⚠️ At Risk", "Action": "Retention Campaign", "Strategy": "Send personalized discounts or 'We Miss You' emails."},
                {"Segment": "💤 Lost", "Action": "Win-Back / Ignore", "Strategy": "Low effort. Automated re-engagement only."}
            ]
            st.table(pd.DataFrame(action_data).set_index("Segment"))
            
        with col_act2:
             fig_pie = px.donut(
                rfm, 
                names="Segment", 
                values="Monetary", 
                hole=0.4,
                color="Segment",
                color_discrete_map=color_map,
                template="corporate_black",
                title="Revenue Mix"
            )
             fig_pie.update_layout(showlegend=False)
             st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("View Customer Details"):
            display_rfm = rfm.sort_values("Monetary", ascending=False).copy()
            display_rfm["Monetary"] = display_rfm["Monetary"].apply(format_indian_currency)
            st.dataframe(display_rfm, use_container_width=True)
    else:
        st.warning("Not enough data for RFM Analysis")
