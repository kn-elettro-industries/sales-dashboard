import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def check_anomaly(row):
    """Flags if a row contains obvious data anomalies."""
    if row.get("AMOUNT", 1) <= 0:
        return "Zero/Negative Amount"
    
    state = str(row.get("STATE", "")).upper()
    city = str(row.get("CITY", "")).upper()
    if "UNKNOWN" in state or "NOT FOUND" in state or "UNKNOWN" in city or "NOT FOUND" in city:
        return "Missing Location Data"
        
    return "Clean"

def render_quality_dashboard(df):
    """Renders the Data Quality and Anomaly Detection Interface."""
    st.markdown('<h2 class="main-header">Data Quality Inspector</h2>', unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.warning("No data available to inspect.")
        return
        
    # Analyze Data Health
    total_rows = len(df)
    
    # Check for empty/null critical fields
    missing_customer = df["CUSTOMER_NAME"].isna().sum() if "CUSTOMER_NAME" in df.columns else 0
    missing_item = df["ITEMNAME"].isna().sum() if "ITEMNAME" in df.columns else 0
    
    # Check for Business Logic Anomalies
    # We apply a quick check for Demo Purposes. On 26k rows, apply() is fast enough for Streamlit
    df["Anomaly_Flag"] = df.apply(check_anomaly, axis=1)
    
    total_anomalies = len(df[df["Anomaly_Flag"] != "Clean"])
    health_score = ((total_rows - total_anomalies) / total_rows) * 100 if total_rows > 0 else 0
    
    # Metric Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Database Health", f"{health_score:.1f}%", f"{total_anomalies} Issues Found", delta_color="inverse")
    with col2:
        st.metric("Total Records Scanned", f"{total_rows:,}")
    with col3:
        st.metric("Missing Customers", f"{missing_customer}")
    with col4:
        st.metric("Missing Items", f"{missing_item}")
        
    st.markdown("---")
    
    # Detailed Breakdown Tab
    t1, t2 = st.tabs(["⚠️ Anomaly Report", "📊 Column Completeness"])
    
    with t1:
        st.markdown("### Detected Anomalies")
        anomaly_df = df[df["Anomaly_Flag"] != "Clean"].copy()
        
        if anomaly_df.empty:
            st.success("🎉 No anomalies detected based on current business rules! The data is clean.")
        else:
            # Breakdown of anomaly types
            anomaly_counts = anomaly_df["Anomaly_Flag"].value_counts().reset_index()
            anomaly_counts.columns = ["Issue Type", "Count"]
            
            col_a, col_b = st.columns([1, 2])
            with col_a:
                fig = px.pie(anomaly_counts, names="Issue Type", values="Count", hole=0.5, title="Issue Breakdown", template="corporate_black")
                fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
                
            with col_b:
                st.markdown("#### Problematic Records")
                st.info("Download these records to correct them in the master source system, then re-run the ETL.")
                
                # Show only relevant columns for the report
                view_cols = [c for c in ["DATE", "CUSTOMER_NAME", "INVOICE_NO", "CITY", "STATE", "AMOUNT", "Anomaly_Flag"] if c in anomaly_df.columns]
                st.dataframe(anomaly_df[view_cols], use_container_width=True, height=300)
                
    with t2:
        st.markdown("### Missing Data (Null Values) per Column")
        null_counts = df.isna().sum().reset_index()
        null_counts.columns = ["Column", "Missing Values"]
        null_counts = null_counts[null_counts["Missing Values"] > 0].sort_values("Missing Values", ascending=False)
        
        if null_counts.empty:
            st.success("All primary columns have 100% data completion.")
        else:
            fig2 = px.bar(null_counts, x="Column", y="Missing Values", text="Missing Values", template="corporate_black")
            fig2.update_traces(marker_color="#ff4444")
            st.plotly_chart(fig2, use_container_width=True)
