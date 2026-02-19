import streamlit as st
import pandas as pd
import plotly.express as px
import time
import pipeline_monitor
from streamlit_option_menu import option_menu

from database import load_data
from analytics.kpi import render_kpis
from analytics.forecasting import render_forecast
from analytics.segmentation import render_rfm
from analytics.risk import render_risk
from analytics.advanced import render_pareto, render_heatmap
from analytics.elasticity import render_elasticity
from analytics.prediction import render_churn_prediction
from analytics.scenario import render_scenario_planner
from analytics.reporting import render_reporting
from analytics.market_basket import render_market_basket
from analytics.chatbot import process_query
from analytics.theme import apply_theme
from analytics.utils import format_indian_currency

# ---------------------------------------------------------
# 1. Page Configuration & Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="ELETTRO Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS & Theme
def load_css():
    try:
        with open("assets/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. UI might look unstyled.")

load_css()
apply_theme()

# ---------------------------------------------------------
# 2. Sidebar & Cloud Upload (MUST BE BEFORE DATA STOP)
# ---------------------------------------------------------
with st.sidebar:
    # Logo
    try:
        st.image("assets/logo_white_text.png", width=None, use_container_width=True)
    except:
        st.markdown('<h2 style="text-align: center; color: #ffffff; margin-bottom: 20px; font-weight: 700; letter-spacing: 1px;">ELETTRO</h2>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Cloud Data Uploader
    import cloud_data_wrapper
    cloud_data_wrapper.render_cloud_uploader()
    
    st.markdown("---")
    st.caption("v1.2 (Fuzzy Logic)")

    # Navigation (will be rendered later if data exists)
    
# ---------------------------------------------------------
# 3. Data Loading
# ---------------------------------------------------------
@st.cache_data
def get_data():
    try:
        df = load_data()
        # Fix NULL states
        # Fix NULL states
        if "STATE" in df.columns:
            df["STATE"] = df["STATE"].fillna("Unknown")
            
        # Ensure CITY column exists (Safety Net)
        if "CITY" not in df.columns:
            df["CITY"] = "Unknown"
        else:
            df["CITY"] = df["CITY"].fillna("Unknown")

        # Determine Financial Year if missing
        if "FINANCIAL_YEAR" not in df.columns and "DATE" in df.columns:
            df["DATE"] = pd.to_datetime(df["DATE"])
            # Simple FY calc fallback
            df["FINANCIAL_YEAR"] = df["DATE"].apply(lambda x: f"FY{x.year}" if x.month < 4 else f"FY{x.year+1}")
        
        # Ensure Month column exists
        if "MONTH" not in df.columns and "DATE" in df.columns:
            df["MONTH"] = pd.to_datetime(df["DATE"]).dt.to_period("M").astype(str)
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame() 

df = get_data()
if df.empty:
    st.warning("⚠️ Application Ready! Upload data in the Sidebar found on the left 👈")
    st.stop()

# ---------------------------------------------------------
# 4. Navigation & Filters (Requires Data)
# ---------------------------------------------------------
with st.sidebar:
    selected = option_menu(
        "Main Menu", 
        [
            "Executive Home", 
            "Customer Intelligence", 
            "Product Intelligence", 
            "Predictive Churn Risk",
            "Scenario Planner",
            "Geographic Intelligence",
            "Market Basket Analysis",
            "Executive Reporting",
            "Data Management", 
            "System Architecture", 
            "AI Assistant"
        ], 
        icons=['house', 'people', 'box', 'globe', 'table', 'diagram-3', 'cpu'], 
        menu_icon="list", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#FFD700", "font-size": "16px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "--hover-color": "#333333"},
            "nav-link-selected": {"background-color": "#444444", "color": "#FFD700"},
        }
    )
    st.markdown("---")
    
    # Pipeline Monitor
    st.markdown("### System Status")
    status_placeholder = st.empty()
    def check_pipeline_status():
        try:
            status = pipeline_monitor.get_status()
            with status_placeholder.container():
                if status["status"] == "Running":
                    st.info(f"Processing: {status['step']}")
                    st.progress(status["progress"] / 100)
                    time.sleep(1)
                    st.rerun()
                elif status["status"] == "Completed":
                    st.caption(f"Last Update: {status['details']}")
                elif status["status"] == "Failed":
                    st.error(f"Error: {status['details']}")
                else:
                    st.caption("Auto-Watcher: Idle")
        except:
            st.caption("Status unavailable")
    check_pipeline_status()
    st.markdown("---")

    # --- Filters ---
    st.markdown("### Filters")
    if "FINANCIAL_YEAR" in df.columns:
        fy_options = sorted(df["FINANCIAL_YEAR"].unique().tolist())
        selected_fy = st.multiselect("Fiscal Year", fy_options, default=fy_options)
        if selected_fy:
            df = df[df["FINANCIAL_YEAR"].isin(selected_fy)]

    if "MONTH" in df.columns:
        # Sort months chronologically
        try:
            # Create a temporary dataframe to sort
            unique_months = df["MONTH"].unique()
            month_df = pd.DataFrame({"MONTH": unique_months})
            month_df["SortKey"] = pd.to_datetime(month_df["MONTH"], format="%b-%y", errors='coerce')
            month_options = month_df.sort_values("SortKey")["MONTH"].tolist()
        except:
            month_options = sorted(df["MONTH"].unique().tolist())
            
        selected_month = st.multiselect("Month", month_options)
        if selected_month:
            df = df[df["MONTH"].isin(selected_month)]

    if "STATE" in df.columns:
        state_options = sorted(df["STATE"].unique().tolist())
        selected_state = st.multiselect("Region / State", state_options)
        if selected_state:
            df = df[df["STATE"].isin(selected_state)]

    # City Filter (Added based on user request)
    city_col = "CITY" if "CITY" in df.columns else None
    if city_col:
        # Filter cities based on selected state if any
        city_options = sorted(df[city_col].dropna().unique().tolist())
        selected_city = st.multiselect("City", city_options)
        if selected_city:
            df = df[df[city_col].isin(selected_city)]

    # Dynamic filters for Customer and Material
    if "CUSTOMER_NAME" in df.columns:
        # Get unique customers, sorted
        cust_options = sorted(df["CUSTOMER_NAME"].dropna().unique().tolist())
        selected_cust = st.multiselect("Customer", cust_options)
        if selected_cust:
            df = df[df["CUSTOMER_NAME"].isin(selected_cust)]

    grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
    if grp_col in df.columns:
        # Get unique material groups, sorted
        grp_options = sorted(df[grp_col].dropna().unique().tolist())
        selected_grp = st.multiselect("Material Group", grp_options)
        if selected_grp:
            df = df[df[grp_col].isin(selected_grp)]

# ---------------------------------------------------------
# 4. Main Content Area
# ---------------------------------------------------------

# Header
st.markdown(f'<h2 class="main-header">{selected}</h2>', unsafe_allow_html=True)
st.markdown("---")

# --- A. Executive Home ---
if selected == "Executive Home":
    # 1. Clean Header Section
    # 1. Clean Header Section
    st.markdown("""
    <div style="background-color: #111111; padding: 15px; border-radius: 4px; border-left: 4px solid #FFD700; border: 1px solid #333;">
        <h4 style="margin:0; color: #ffffff; font-weight: 600;">Performance Summary</h4>
        <p style="margin-top: 5px; color: #aaaaaa; font-size: 0.95rem; margin-bottom: 0;">
            Revenue momentum is positive. 
            <span style="color: #FFD700; font-weight: 600;">Maharashtra</span> leads regional sales. 
            Inventory alert for <em>Product Category A</em>.
        </p>
    </div>
    <br>
    """, unsafe_allow_html=True)

    # 2. Key Metrics
    render_kpis(df)
    
    st.markdown("### Revenue Performance")
    
    # 3. Trend Chart
    monthly_sales = df.groupby("MONTH")["AMOUNT"].sum().reset_index()
    # Sort chronologically
    try:
        monthly_sales["SortKey"] = pd.to_datetime(monthly_sales["MONTH"], format="%b-%y", errors='coerce')
        monthly_sales = monthly_sales.sort_values("SortKey")
    except:
        pass # Fallback to existing order
        
    fig_trend = px.area(
        monthly_sales, 
        x="MONTH", 
        y="AMOUNT", 
        title="Monthly Revenue Trend",
        markers=True,
        template="corporate_black"
    )
    fig_trend.update_traces(line_color="#FFD700", fillcolor="rgba(255, 215, 0, 0.25)")
    st.plotly_chart(fig_trend, use_container_width=True)

    # 4. Forecast & Risk (High Level)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        render_forecast(monthly_sales)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        render_risk(df)
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. Business Drivers (Customers & Materials)
    st.markdown("### Top Business Drivers")
    c3, c4 = st.columns(2)
    
    with c3:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("Top 10 Customers")
        top_cust = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().sort_values(ascending=False).head(10).reset_index()
        top_cust["Formatted_Amount"] = top_cust["AMOUNT"].apply(format_indian_currency)
        
        fig_cust = px.bar(
            top_cust, 
            x="AMOUNT", 
            y="CUSTOMER_NAME", 
            orientation='h',
            text="Formatted_Amount",
            title="",
            template="corporate_black",
            color="AMOUNT",
            color_continuous_scale="YlOrBr"
        )
        fig_cust.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Revenue", yaxis_title=None, font=dict(color="white"))
        st.plotly_chart(fig_cust, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("Top Material Groups")
        grp_col = "ITEM_NAME_GROUP" if "ITEM_NAME_GROUP" in df.columns else "MATERIALGROUP"
        if grp_col in df.columns:
            top_mat = df.groupby(grp_col)["AMOUNT"].sum().sort_values(ascending=False).head(10).reset_index()
            # For Pie/Donut, we usually rely on hover or legend, but can add text info
            # Let's keep pie simple but ensure hover has formatted data if possible, or just standard %
            # Plotly Pie text info is usually percent. Customizing it to show 'Cr' might be crowded.
            # Let's stick to default percent for Pie, but bar definitely needs 'Cr'.
            
            fig_mat = px.pie(
                top_mat, 
                values="AMOUNT", 
                names=grp_col, 
                hole=0.4,
                template="corporate_black",
                color_discrete_sequence=px.colors.sequential.YlOrBr
            )
            fig_mat.update_layout(title="", font=dict(color="white"))
            st.plotly_chart(fig_mat, use_container_width=True)
        else:
            st.info("Material Group data unavailable.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- B. Customer Intelligence ---
elif selected == "Customer Intelligence":
    st.markdown("### 360 Customer View")
    st.caption("Analyze customer loyalty, churn risk, and segmentation.")
    
    # RFM Analysis
    render_rfm(df)
    
    st.markdown("---")
    
    # Pareto Analysis
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    render_pareto(df) 
    st.markdown('</div>', unsafe_allow_html=True)

# --- C. Product Intelligence ---
elif selected == "Product Intelligence":
    st.markdown("### Product Portfolio Performance")
    st.caption("Analyze product demand, pricing strategy, and best-sellers.")
    
    # Price Elasticity
    render_elasticity(df)
    
    st.markdown("---")
    
    # Product Pareto
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    render_pareto(df)
    st.markdown('</div>', unsafe_allow_html=True)

# --- D. Predictive Churn Risk ---
elif selected == "Predictive Churn Risk":
    render_churn_prediction(df)

# --- E. Scenario Planner ---
elif selected == "Scenario Planner":
    render_scenario_planner(df)

# --- F. Geographic Intelligence ---
elif selected == "Geographic Intelligence":
    st.markdown("### Regional Sales Performance")
    st.caption("Visualize sales density and regional distribution.")
    
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    render_heatmap(df)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Regional Stats Table
    st.markdown("#### Regional Breakdown")
    region_stats = df.groupby("STATE")["AMOUNT"].sum().sort_values(ascending=False).reset_index()
    region_stats["Market Share"] = (region_stats["AMOUNT"] / region_stats["AMOUNT"].sum()) * 100
    st.dataframe(region_stats, use_container_width=True)

# --- E. Market Basket Analysis ---
elif selected == "Market Basket Analysis":
    render_market_basket(df)

# --- F. Executive Reporting ---
elif selected == "Executive Reporting":
    render_reporting(df)

# --- G. Data Management ---
elif selected == "Data Management":
    st.markdown("### Data Explorer")
    st.dataframe(df, use_container_width=True, height=600)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Full Dataset (CSV)",
        csv,
        "sales_data_export.csv",
        "text/csv",
        key='download-csv'
    )
    
    st.markdown("---")
    st.subheader("🔍 Column Inspector (Debug)")
    st.write("Current Detected Columns:", df.columns.tolist())
    
    # Check for missing critical columns
    missing = []
    for col in ["CITY", "STATE", "CUSTOMER_NAME", "ITEMNAME"]:
        if col not in df.columns:
            missing.append(col)
    
    if missing:
        st.error(f"Missing Critical Columns: {missing}")
        st.info("Ensure your Excel file has columns named 'City', 'Town', 'Location' for City, and 'State', 'Region' for State.")
    else:
        st.success("All critical columns detected!")
        
    st.markdown("---")
    st.subheader("📁 Master Files Status")
    import os
    import config
    
    if os.path.exists(config.CUSTOMER_MASTER_FILE):
        st.success("✅ Customer Master Connected")
        try:
            m_df = pd.read_excel(config.CUSTOMER_MASTER_FILE)
            st.caption(f"Master contains {len(m_df)} records.")
            with st.expander("View Master File Sample"):
                st.dataframe(m_df.head())
        except Exception as e:
            st.error(f"❌ Customer Master corrupted: {e}")
    else:
        st.error("❌ Customer Master NOT FOUND on Cloud")
        # List what IS there
        st.write("Files found in data/masters/:")
        try:
             files = os.listdir(config.MASTER_FOLDER)
             st.write(files)
        except:
             st.write("Could not list directory.")
        st.info("Ensure data/masters/customer_master.xlsx is in your GitHub repo and not ignored.")

    st.markdown("---")
    st.subheader("🕵️ Raw File headers")
    st.caption("Inspect the first file in 'data/raw' to see original column names.")
    try:
        raw_files = [f for f in os.listdir(config.RAW_FOLDER) if f.endswith(".xlsx")]
        if raw_files:
            file_path = os.path.join(config.RAW_FOLDER, raw_files[0])
            raw_preview = pd.read_excel(file_path, nrows=2)
            st.write(f"File: {raw_files[0]}")
            st.write(raw_preview.columns.tolist())
        else:
            st.warning("No raw files found. Upload a file first.")
    except Exception as e:
        st.error(f"Error reading raw file: {e}")
    
    st.markdown("---")
    st.subheader("⚠️ Danger Zone")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear All Data (Reset Dashboard)", type="primary"):
            import database
            try:
                database.clear_all_data()
                st.success("Database cleared! Please re-upload your Excel file to refresh the data.")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing data: {e}")

# --- F. System Architecture ---
elif selected == "System Architecture":
    st.markdown("### Live System Architecture")
    st.caption("Visual representation of your automated pipeline")
    
    graph = """
    digraph {
        bgcolor="white"
        rankdir=LR
        node [shape=box style=filled fillcolor="#f8f9fa" fontcolor="#333" fontname="Inter" color="#dee2e6"]
        edge [color="#adb5bd"]
        
        User [label="User (Excel)" shape=ellipse fillcolor="#FFD700"]
        RawFolder [label="raw/ Folder" shape=folder fillcolor="#fff3cd"]
        Watcher [label="Watcher Bot" fillcolor="#e9ecef"]
        ETL [label="ETL Pipeline" fillcolor="#d4edda" color="#c3e6cb"]
        DB [label="SQLite DB" shape=cylinder fillcolor="#d1ecf1" color="#bee5eb"]
        Dashboard [label="Dashboard" fillcolor="#e2e3e5"]
        
        User -> RawFolder
        RawFolder -> Watcher
        Watcher -> ETL
        ETL -> DB
        DB -> Dashboard
    }
    """
    st.graphviz_chart(graph)
    
    st.markdown("""
    <div class="css-card">
        <h4>How it works</h4>
        <ul>
            <li><strong>Watcher:</strong> Keeps an eye on the folder 24/7.</li>
            <li><strong>ETL Pipeline:</strong> Cleans, transforms, and merges your Excel data automatically.</li>
            <li><strong>Dashboard:</strong> Always displays the latest data from the database.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# --- G. AI Assistant ---
elif selected == "AI Assistant":
    st.markdown("### Data Assistant (NLP Powered)")
    st.caption("Ask questions like: 'Sales in Mumbai', 'Top 5 Customers', 'Total Revenue'")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I can analyze your sales data. Ask me anything."}]

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask a question..."):
        # User message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                time.sleep(0.5) 
                response = process_query(prompt, df)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
