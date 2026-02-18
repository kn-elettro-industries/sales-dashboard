import streamlit as st
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import plotly.express as px

def render_market_basket(df):
    st.subheader("🛍️ Market Basket Analysis (Cross-Selling)")
    st.caption("Identify product bundles and cross-selling opportunities using the **Apriori Algorithm**.")

    # Data Prep
    if "INVOICE_NO" not in df.columns or "ITEMNAME" not in df.columns:
        st.warning("Data must contain 'INVOICE_NO' and 'ITEMNAME'.")
        return

    # User Configuration
    c1, c2, c3 = st.columns(3)
    with c1:
        min_support = st.slider("Min Support", 0.001, 0.1, 0.01, format="%.3f", help="Minimum frequency of itemset")
    with c2:
        min_lift = st.slider("Min Lift", 0.5, 5.0, 1.0, help="Lift > 1 implies positive correlation")
    with c3:
        metric = st.selectbox("Sort By", ["lift", "confidence", "support"])

    # 1. Prepare Transactions (One-Hot Encoding)
    # Group items by invoice
    basket = (df.groupby(['INVOICE_NO', 'ITEMNAME'])['QTY']
              .sum().unstack().reset_index().fillna(0)
              .set_index('INVOICE_NO'))
    
    # Analyze only valid transactions (items with >0 qty)
    # Convert to boolean (bought or not)
    basket_sets = basket.apply(lambda x: x > 0)

    if basket_sets.empty:
        st.warning("No valid transactions found.")
        return

    try:
        with st.spinner("Running Apriori Algorithm..."):
            # 2. Find Frequent Itemsets
            frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)
            
            if frequent_itemsets.empty:
                st.info("No itemsets found. Try lowering 'Min Support'.")
                return

            # 3. Generate Rules
            rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
            
            if rules.empty:
                st.info("No association rules found. Try lowering 'Min Lift'.")
                return
            
            # Formatting
            rules["antecedents"] = rules["antecedents"].apply(lambda x: list(x)[0])
            rules["consequents"] = rules["consequents"].apply(lambda x: list(x)[0])
            rules = rules.sort_values(metric, ascending=False)
            
            # Display Top Rules
            st.markdown("### 🔗 Top Association Rules")
            
            # Formatted Table for Business Users
            display_rules = rules[["antecedents", "consequents", "support", "confidence", "lift"]].copy()
            display_rules.columns = ["If Customer Buys...", "...They Also Buy", "Support", "Confidence", "Lift (Strength)"]
            
            st.dataframe(
                display_rules.head(20).style.background_gradient(cmap="YlOrRd", subset=["Lift (Strength)"]),
                use_container_width=True
            )
            
            # Scatter Plot visualization
            st.markdown("### 📈 Rules Visualization")
            fig = px.scatter(
                rules,
                x="support",
                y="confidence",
                size="lift",
                color="lift",
                hover_data=["antecedents", "consequents"],
                title="Market Basket Rules (Color = Lift)",
                template="corporate_black",
                color_continuous_scale="solar",
                labels={"support": "Support (Frequency)", "confidence": "Confidence (Reliability)", "lift": "Lift (Strength)"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("""
            <div class="css-card">
                <h4>🧠 Cheat Sheet</h4>
                <ul>
                    <li><strong>Support:</strong> How often items appear together.</li>
                    <li><strong>Confidence:</strong> If they buy A, how likely are they to buy B?</li>
                    <li><strong>Lift:</strong> The strength of the rule. Lift > 1 means they are linked.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Analysis Failed: {e}")
        st.caption("Tip: Ensure you have enough data and appropriate thresholds.")
