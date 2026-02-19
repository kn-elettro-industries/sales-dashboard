import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
import config
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
from analytics.reporting import render_reporting
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

# --- 2. Login Check ---
import auth
if not auth.check_password():
    st.stop()
    
# ---------------------------------------------------------
# 3. Sidebar & Cloud Upload (MUST BE BEFORE DATA STOP)
# ---------------------------------------------------------
with st.sidebar:
    # Cleanup Sidebar if logged in
    st.markdown(f"**Welcome, {st.session_state.get('user_name', 'User')}**")
    if st.button("Logout", key="logout_btn"):
        auth.logout()
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
        # Fix NULL states
        if "STATE" in df.columns:
            df["STATE"] = df["STATE"].fillna("State Not Found ⚠️")
            
        # Ensure CITY column exists (Safety Net)
        if "CITY" not in df.columns:
            df["CITY"] = "City Not Found ⚠️"
        else:
            df["CITY"] = df["CITY"].fillna("City Not Found ⚠️")

        # Determine Financial Year if missing
        if "FINANCIAL_YEAR" not in df.columns and "DATE" in df.columns:
            df["DATE"] = pd.to_datetime(df["DATE"])
            # Simple FY calc fallback
            df["FINANCIAL_YEAR"] = df["DATE"].apply(lambda x: f"FY{x.year}" if x.month < 4 else f"FY{x.year+1}")
        
        # Ensure Month column exists
        if "MONTH" not in df.columns and "DATE" in df.columns:
            df["MONTH"] = pd.to_datetime(df["DATE"]).dt.to_period("M").astype(str)
            
        # Ensure INVOICE_NO for KPIs
        if "INVOICE_NO" not in df.columns:
            # Create dummy index if missing so KPIs don't crash
            df["INVOICE_NO"] = df.index.astype(str)

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame() 

@st.cache_data
def get_targets():
    """Loads Sales Targets. Creates template if missing."""
    if not os.path.exists(config.TARGETS_FILE):
        # Create Template
        data = {
            "FINANCIAL_YEAR": ["FY2024", "FY2024", "FY2025", "FY2025"],
            "MONTH": ["APR-24", "MAY-24", "APR-25", "MAY-25"],
            "TARGET_AMOUNT": [5000000, 5500000, 6000000, 6500000],
            "CUSTOMER_NAME": ["All", "All", "All", "All"],
            "MATERIAL_GROUP": ["All", "All", "All", "All"]
        }
        df = pd.DataFrame(data)
        try:
            df.to_excel(config.TARGETS_FILE, index=False)
        except: pass
        return df
    
    try:
        return pd.read_excel(config.TARGETS_FILE)
    except:
        return pd.DataFrame()

df = get_data()
targets_df = get_targets()

if df.empty:
    st.warning("⚠️ Application Ready! Upload data in the Sidebar found on the left 👈")
    st.stop()

# ---------------------------------------------------------
# 4. Navigation & Filters (Requires Data)
# ---------------------------------------------------------
with st.sidebar:
    # Role Selection (Override with Auth Role)
    user_role_auth = st.session_state.get("role", "Viewer")
    
    # Map Auth Role to App Role (Simulating the previous dropdown logic but enforcing it)
    # Admin -> Admin Operations
    # Manager -> Managing Director
    # Viewer -> Sales Team
    
    if user_role_auth == "Admin":
        app_role = "Admin Operations"
    elif user_role_auth == "Manager":
        app_role = "Managing Director"
    else:
        app_role = "Sales Team"
        
    st.caption(f"Access Level: {app_role}")
    st.sidebar.markdown("---")

    # Define Menus based on Role
    if app_role == "Managing Director":
        menu_options = ["Executive Home", "Geographic Intelligence", "Executive Reporting", "AI Assistant"]
        menu_icons = ["house", "globe", "file-earmark-text", "robot"]
    elif app_role == "Sales Team":
        menu_options = ["Customer Intelligence", "Product Intelligence", "Predictive Churn Risk", "AI Assistant"]
        menu_icons = ["people", "box", "graph-down-arrow", "robot"]
    else: # Admin (Show All)
        menu_options = [
            "Executive Home", 
            "Customer Intelligence", 
            "Product Intelligence", 
            "Predictive Churn Risk",
            "Geographic Intelligence",
            "Executive Reporting",
            "Data Management", 
            "System Architecture", 
            "AI Assistant",
            "User Management"
        ]
        menu_icons = ["house", "people", "box", "graph-down-arrow", "globe", "file-earmark-text", "database", "diagram-3", "robot", "people-fill"]

    selected = option_menu(
        "Main Menu", 
        menu_options, 
        icons=menu_icons, 
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
                    if st.button("Reset Status"):
                        pipeline_monitor.reset_status()
                        st.rerun()
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
        raw_options = df[city_col].dropna().unique().tolist()
        # Remove 'Unknown' or 'Not Found' from options to clean up UI
        city_options = sorted([x for x in raw_options if "NOT FOUND" not in str(x).upper() and "UNKNOWN" not in str(x).upper()])
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
    # 1. Clean Header Section (With Target Context)
    
    # Calculate Target Achievement
    target_msg = "Targets not loaded."
    achievement_pct = 0
    total_target = 0
    
    if not targets_df.empty and "MONTH" in df.columns:
        # Filter targets for selected months/FY if possible
        # For now, just sum all matching targets for the current view
        try:
            # Simple matching: Sum targets for months present in the filtered dataframe
            active_months = df["MONTH"].unique()
            relevant_targets = targets_df[targets_df["MONTH"].isin(active_months)]
            total_target = relevant_targets["TARGET_AMOUNT"].sum()
            
            current_revenue = df["AMOUNT"].sum()
            if total_target > 0:
                achievement_pct = (current_revenue / total_target) * 100
                target_msg = f"{achievement_pct:.1f}% of Target Achieved ({format_indian_currency(current_revenue)} / {format_indian_currency(total_target)})"
            else:
                target_msg = "No Targets defined for selected period."
        except Exception as e:
            target_msg = f"Target Error: {e}"

    # Header with Gauge Context
    st.markdown(f"""
    <div style="background-color: #111111; padding: 15px; border-radius: 4px; border-left: 4px solid #FFD700; border: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h4 style="margin:0; color: #ffffff; font-weight: 600;">Performance Summary</h4>
            <p style="margin-top: 5px; color: #aaaaaa; font-size: 0.95rem; margin-bottom: 0;">
                Revenue momentum is positive. 
                <span style="color: #FFD700; font-weight: 600;">Maharashtra</span> leads regional sales. 
            </p>
        </div>
        <div style="text-align: right;">
             <h3 style="margin:0; color: {'#00ff00' if achievement_pct >= 100 else '#FFD700' if achievement_pct >= 80 else '#ff4444'};">{achievement_pct:.1f}%</h3>
             <span style="color: #888; font-size: 0.8rem;">Target Achievement</span>
        </div>
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
        
        # Merge Targets for Chart
        if not targets_df.empty:
            target_trend = targets_df.groupby("MONTH")["TARGET_AMOUNT"].sum().reset_index()
            monthly_sales = pd.merge(monthly_sales, target_trend, on="MONTH", how="left").fillna(0)
    except:
        pass # Fallback to existing order
        
    fig_trend = px.area(
        monthly_sales, 
        x="MONTH", 
        y="AMOUNT", 
        title="Monthly Revenue vs Target",
        markers=True,
        template="corporate_black"
    )
    fig_trend.update_traces(line_color="#FFD700", fillcolor="rgba(255, 215, 0, 0.25)", name="Actual Revenue")
    
    # Add Target Line
    if "TARGET_AMOUNT" in monthly_sales.columns:
        fig_trend.add_scatter(x=monthly_sales["MONTH"], y=monthly_sales["TARGET_AMOUNT"], mode='lines+markers', 
                              name='Target', line=dict(color='white', width=2, dash='dot'))
                              
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
            
        st.markdown("---")
        st.caption("Current Data Distribution (State):")
        if "STATE" in df.columns:
             st.write(df["STATE"].value_counts().head())
        else:
             st.error("STATE column missing in processed data.")
             
    except Exception as e:
        st.error(f"Error reading raw file: {e}")

    st.markdown("---")
    st.subheader("🕵️ Data Quality Inspector")
    st.caption("Find rows where Location data is missing.")
    
    # Filter for Missing Locations
    # Check for 'Unknown' OR the new 'Not Found' label
    unknown_df = df[
        (df["CITY"].astype(str).str.contains("NOT FOUND|UNKNOWN", case=False)) | 
        (df["STATE"].astype(str).str.contains("NOT FOUND|UNKNOWN", case=False)) |
        (df["STATE"].str.upper() == "MAHARASHTRA") # excessive default checking
    ]
    
    if not unknown_df.empty:
        st.warning(f"Found {len(unknown_df)} rows with potential location issues.")
        st.dataframe(unknown_df[["INVOICE_NO", "CUSTOMER_NAME", "CITY", "STATE", "AMOUNT"]].head(20))
    else:
        st.success("✅ No 'Unknown' locations found!")
    
    st.markdown("---")
    st.subheader("⚖️ Data Integrity Checker")
    st.caption("Compare Raw Input vs. Final Output to find missing data.")
    
    col1, col2 = st.columns(2)
    
    # 1. Analyze Raw Data
    raw_metrics = {"rows": 0, "amount": 0, "min_date": None, "max_date": None}
    with col1:
        st.info("📂 Raw Input(s)")
        try:
            raw_files = [f for f in os.listdir(config.RAW_FOLDER) if f.endswith(".xlsx")]
            if raw_files:
                dfs = []
                for f in raw_files:
                    path = os.path.join(config.RAW_FOLDER, f)
                    tmp = pd.read_excel(path)
                    # Standardize just to find AMOUNT column
                    tmp.columns = tmp.columns.str.upper().str.strip()
                    dfs.append(tmp)
                
                raw_combined = pd.concat(dfs)
                raw_metrics["rows"] = len(raw_combined)
                
                # Find Amount Column loosely
                amt_col = next((c for c in raw_combined.columns if "AMOUNT" in c), None)
                if amt_col:
                     raw_metrics["amount"] = raw_combined[amt_col].sum()
                
                st.metric("Total Rows", raw_metrics["rows"])
                st.metric("Total Amount", f"₹{raw_metrics['amount']:,.0f}")
            else:
                st.warning("No raw files.")
        except Exception as e:
            st.error(f"Read Error: {e}")

    # 2. Analyze Processed Data
    processed_metrics = {"rows": 0, "amount": 0}
    with col2:
        st.success("📊 Processed Sales Master")
        if os.path.exists(config.SALES_MASTER_FILE):
             try:
                 proc_df = pd.read_excel(config.SALES_MASTER_FILE)
                 processed_metrics["rows"] = len(proc_df)
                 if "TOTALAMOUNT" in proc_df.columns:
                     processed_metrics["amount"] = proc_df["TOTALAMOUNT"].sum()
                 elif "AMOUNT" in proc_df.columns:
                     processed_metrics["amount"] = proc_df["AMOUNT"].sum()
                     
                 st.metric("Total Rows", processed_metrics["rows"], delta=processed_metrics["rows"] - raw_metrics["rows"])
                 st.metric("Total Amount", f"₹{processed_metrics['amount']:,.0f}", delta=processed_metrics['amount'] - raw_metrics['amount'])
             except:
                 st.error("Could not read Master.")
        else:
             st.warning("No Sales Master found.")
             
    # Diagnosis
    st.write("---")
    diff_rows = raw_metrics["rows"] - processed_metrics["rows"]
    if diff_rows > 0:
        st.error(f"❌ LOST {diff_rows} ROWS! Check 'Excluded Keywords' in Config.")
    elif diff_rows < 0:
        st.warning(f"⚠️ GAINED {abs(diff_rows)} ROWS? Check for duplicates.")
    else:
        st.success("✅ Row Counts Match completely.")
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
    st.markdown("### 🤖 Krishiv (AI Analyst)")
    st.caption("Ask questions like: 'Sales in Mumbai', 'Top 5 Customers', 'Total Revenue'")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I am Krishiv. Ask me anything about your data."}]

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

# --- H. User Management (Admin Only) ---
elif selected == "User Management" and app_role == "Admin Operations":
    st.markdown("## 👥 User Management")
    st.info("Manage access and roles. Changes are saved immediately.")
    
    users = auth.load_users()
    
    # Convert to DataFrame for display
    user_list = []
    for uname, info in users.items():
        user_list.append({
            "Username": uname,
            "Name": info.get("name", "Unknown"),
            "Role": info.get("role", "Viewer"),
            "Status": info.get("status", "Active")
        })
    
    user_df = pd.DataFrame(user_list)
    st.dataframe(user_df, use_container_width=True)
    
    st.markdown("### ✏️ Edit User")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        target_user = st.selectbox("Select User", sorted(users.keys()))
    
    if target_user:
        curr_info = users[target_user]
        with c2:
            new_role = st.selectbox("Assign Role", ["Admin", "Manager", "Viewer"], index=["Admin", "Manager", "Viewer"].index(curr_info.get("role", "Viewer")))
        with c3:
            new_status = st.selectbox("Status", ["Active", "Pending", "Blocked"], index=["Active", "Pending", "Blocked"].index(curr_info.get("status", "Active")))
            
        if st.button("Update User"):
            success, msg = auth.update_user_details(target_user, new_role, new_status)
            if success:
                st.success(f"{msg}: {target_user}")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error: {msg}")

# ---------------------------------------------------------
# FLOATING CHATBOT (Global)
# ---------------------------------------------------------
st.markdown("""
<style>
/* Float the Popover Container */
[data-testid="stPopover"] {
    position: fixed;
    bottom: 30px;
    right: 30px;
    z-index: 10000;
}
/* Style the Button */
[data-testid="stPopover"] button {
    background-color: #FFD700;
    color: black;
    border: none;
    border-radius: 50%;
    width: 60px;
    height: 60px;
    font-size: 24px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
}
[data-testid="stPopover"] button:hover {
    background-color: #FFEE55;
    transform: scale(1.1);
}
</style>
""", unsafe_allow_html=True)

# Popover Chat
with st.popover("💬", use_container_width=False):
    st.markdown("### 🤖 Krishiv (AI Analyst)")
    st.caption("Ask me about Revenue, Targets, or Top Products.")
    
    # Initialize Chat History if not present
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hi! I am Krishiv. How can I help you today?"}]

    # Display Chat History (Limit to last 5 for space)
    for message in st.session_state.messages[-5:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask a question...", key="float_chat"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(0.5)
                response = process_query(prompt, df)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
