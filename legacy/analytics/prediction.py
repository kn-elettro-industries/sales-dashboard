import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

def render_churn_prediction(df):
    st.subheader("🔮 AI Predictive Churn Risk")
    st.caption("Using **Random Forest Machine Learning** to predict which customers are likely to stop buying.")

    # 1. Feature Engineering (RFM + Variance)
    reference_date = df["DATE"].max()
    
    features = (
        df.groupby("CUSTOMER_NAME")
        .agg(
            Recency=("DATE", lambda x: (reference_date - x.max()).days),
            Frequency=("INVOICE_NO", "nunique"),
            Monetary=("AMOUNT", "sum"),
            Tenure=("DATE", lambda x: (x.max() - x.min()).days),
            Avg_Order_Value=("AMOUNT", "mean")
        )
        .reset_index()
    )

    # 2. Define "Churn" Label (Proxy)
    # If Recency > 90 days, we consider them "Churned" for training
    churn_threshold = 90
    features["Is_Churned"] = (features["Recency"] > churn_threshold).astype(int)
    
    # 3. Prepare ML Data
    st.markdown("### Model Training Status")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Customers", len(features))
    col2.metric("Churn Threshold", f"> {churn_threshold} Days")
    col3.metric("At Risk Detected", features["Is_Churned"].sum())

    if len(features) < 10:
        st.warning("Not enough data to train AI model (Need 10+ customers).")
        return

    X = features[["Recency", "Frequency", "Monetary", "Tenure", "Avg_Order_Value"]]
    y = features["Is_Churned"]
    
    # Scale Data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. Train Model
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_scaled, y)
    
    # 5. Predict Probabilities
    if len(np.unique(y)) > 1:
        # Standard case: 2 classes
        churn_probs = clf.predict_proba(X_scaled)[:, 1]
    else:
        # Edge case: Only 1 class in training data (e.g., all active or all churned)
        # If the only class is 1, probs are 1.0. If 0, probs are 0.0.
        single_class = np.unique(y)[0]
        churn_probs = np.full(len(features), float(single_class))

    features["Churn_Probability"] = churn_probs * 100
    
    # 6. Interpret Results
    # Filter for active customers (Recency < 90) who have HIGH risk
    # We want to save people who are NOT yet churned but look like they will
    active_mask = features["Recency"] <= churn_threshold
    predictions = features[active_mask].copy()
    
    predictions = predictions.sort_values("Churn_Probability", ascending=False)
    
    # Visualization
    st.markdown("### 🚨 High Risk Customers (Action Required)")
    
    top_risk = predictions.head(10)
    
    fig = px.bar(
        top_risk,
        x="Churn_Probability",
        y="CUSTOMER_NAME",
        orientation="h",
        title="Top 10 Customers at Risk of Churning",
        labels={"Churn_Probability": "Churn Probability (%)", "CUSTOMER_NAME": "Customer"},
        color="Churn_Probability",
        color_continuous_scale="reds",
        template="corporate_black",
        text_auto=".1f"
    )
    fig.update_layout(yaxis=dict(autorange="reversed")) # Top risk at top
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Table
    st.dataframe(
        predictions[["CUSTOMER_NAME", "Churn_Probability", "Recency", "Frequency", "Monetary"]]
        .style.background_gradient(subset=["Churn_Probability"], cmap="Reds"),
        use_container_width=True
    )
    
    st.info("💡 ** Insight:** AI identifies patterns (e.g., declining frequency) that resemble past churned customers.")
