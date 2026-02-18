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

        # 2. Premium 3D Scatter Plot
        # Colors: Gold for Champions/Loyal, Greys for others
        color_map = {
            "Loyal": "#FFD700",    # Gold
            "Frequent": "#C0C0C0", # Silver
            "Rare": "#808080",     # Grey
            "One-time": "#333333"  # Dark Grey
        }
        
        fig = px.scatter_3d(
            rfm,
            x="Recency",
            y="Frequency",
            z="Monetary",
            color="F_Score", # Color by Frequency Score
            size="Monetary",
            size_max=20,
            hover_name="CUSTOMER_NAME",
            hover_data={"Recency": True, "Frequency": True, "Monetary": ":.2f", "F_Score": False},
            title="RFM 3D Analysis (Gold = Loyal)",
            labels={"Recency": "Days Since Last Order", "Frequency": "Total Orders", "Monetary": "Total Spent"},
            color_discrete_map=color_map,
            template="corporate_black",
            opacity=0.9
        )
        
        # Clean Axes for Premium Look
        fig.update_layout(
            scene=dict(
                xaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#333", title_font=dict(color="#888")),
                yaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#333", title_font=dict(color="#888")),
                zaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#333", title_font=dict(color="#888")),
            ),
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 3. Segment Distribution Summary
        st.markdown("#### Segment Distribution")
        seg_counts = rfm["F_Score"].value_counts().reset_index()
        seg_counts.columns = ["Segment", "Count"]
        
        fig_bar = px.bar(
            seg_counts, 
            x="Segment", 
            y="Count", 
            color="Segment",
            color_discrete_map=color_map,
            template="corporate_black",
            text="Count"
        )
        fig_bar.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, plot_bgcolor="rgba(0,0,0,0)")
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        with st.expander("View Detailed RFM Data"):
            display_rfm = rfm.sort_values("Monetary", ascending=False).copy()
            display_rfm["Monetary"] = display_rfm["Monetary"].apply(format_indian_currency)
            st.dataframe(display_rfm, use_container_width=True)
    else:
        st.warning("Not enough data for RFM Analysis")
