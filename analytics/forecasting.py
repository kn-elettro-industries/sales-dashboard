import streamlit as st
import numpy as np
from sklearn.linear_model import LinearRegression
from .utils import format_indian_currency

def render_forecast(monthly_sales):
    st.subheader("🔮 Sales Forecast")

    if len(monthly_sales) >= 3:
        monthly_df = monthly_sales.reset_index()
        monthly_df["MONTH_INDEX"] = range(len(monthly_df))

        X = monthly_df[["MONTH_INDEX"]]
        y = monthly_df["AMOUNT"]

        model = LinearRegression()
        model.fit(X, y)

        next_month_index = np.array([[len(monthly_df)]])
        forecast = model.predict(next_month_index)[0]

        st.metric("Predicted Next Month Sales", format_indian_currency(forecast))
    else:
        st.info("Need at least 3 months of data.")
