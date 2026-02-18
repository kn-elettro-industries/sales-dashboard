import streamlit as st

def render_risk(df):
    st.subheader("⚠️ Revenue Risk")

    customer_sales = (
        df.groupby("CUSTOMER_NAME")["AMOUNT"]
        .sum()
        .sort_values(ascending=False)
    )

    top_5 = customer_sales.head(5).sum()
    total_rev = customer_sales.sum()
    risk_percentage = (top_5 / total_rev) * 100

    st.write(f"Top 5 customers contribute {risk_percentage:.2f}% of revenue")

    if risk_percentage > 60:
        st.error("High concentration risk")
    else:
        st.success("Healthy distribution")
