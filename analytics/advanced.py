import streamlit as st
import plotly.express as px
import pandas as pd
import assets.geo_data as geo_data

def render_pareto(df):
    """
    Renders a Pareto Analysis (80/20 Rule) for Customers or Products.
    """
    st.subheader("Pareto Analysis (80/20 Rule)")
    
    analysis_type = st.radio("Analyze by:", ["Customer", "Product"], horizontal=True)
    col_name = "CUSTOMER_NAME" if analysis_type == "Customer" else "ITEMNAME"

    # Aggregate Sales
    data = df.groupby(col_name)["AMOUNT"].sum().reset_index()
    data = data.sort_values("AMOUNT", ascending=False)
    
    # Calculate Cumulative Percentage
    data["cum_percent"] = data["AMOUNT"].cumsum() / data["AMOUNT"].sum() * 100
    
    # Create Chart
    fig = px.bar(
        data.head(50), 
        x=col_name, 
        y="AMOUNT", 
        title=f"Top 50 {analysis_type}s by Revenue",
        color="AMOUNT",
        color_continuous_scale="solar",
        template="corporate_black"
    )
    
    # Add Cumulative Line
    fig.add_scatter(
        x=data.head(50)[col_name], 
        y=data.head(50)["cum_percent"], 
        yaxis="y2", 
        name="Cumulative %",
        marker=dict(color="#FFD700"),
        line=dict(width=3)
    )
    
    fig.update_layout(
        yaxis2=dict(overlaying="y", side="right", range=[0, 100], title="Cumulative %"),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Top 20% Stats
    top_20_count = int(len(data) * 0.2)
    top_20_revenue = data.iloc[:top_20_count]["AMOUNT"].sum()
    total_revenue = data["AMOUNT"].sum()
    
    st.markdown(f"""
    <div class="css-card" style="border-left: 5px solid #d4ff00;">
        <h4 style="margin:0;">Pareto Insight</h4>
        <p>The top <strong>20% ({top_20_count})</strong> of {analysis_type}s generate 
        <strong>{top_20_revenue/total_revenue*100:.1f}%</strong> of total revenue.</p>
    </div>
    """, unsafe_allow_html=True)

def render_heatmap(df):
    """
    Renders a Sales Density Heatmap using Mapbox.
    """
    st.subheader("Sales Density Heatmap")
    
    if "STATE" not in df.columns:
        st.warning("State data not available.")
        return

    # --- 1. State Filter ---
    states = ["All India"] + sorted(df["STATE"].unique().tolist())
    selected_state = st.selectbox("Select Region to Analyze:", states)

    if selected_state == "All India":
        # === A. National Visualization ===
        heatmap_data = df.groupby("STATE")["AMOUNT"].sum().reset_index()
        
        # Map Lat/Lon
        heatmap_data["lat"] = heatmap_data["STATE"].map(lambda x: geo_data.STATE_COORDS.get(x.title(), [20.5937, 78.9629])[0])
        heatmap_data["lon"] = heatmap_data["STATE"].map(lambda x: geo_data.STATE_COORDS.get(x.title(), [20.5937, 78.9629])[1])
        
        # 1. Overview Map (Choropleth or Density)
        st.markdown("#### 🇮🇳 National Sales Overview")
        
        fig = px.density_mapbox(
            heatmap_data, 
            lat='lat', 
            lon='lon', 
            z='AMOUNT', 
            radius=45,  
            center=dict(lat=22.5937, lon=82.9629), 
            zoom=3.8,
            mapbox_style="carto-darkmatter",
            color_continuous_scale="Viridis",
            opacity=0.7,
            title="<b>Heatmap Density</b>"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        # === B. High-Fidelity Drilldown (Google Earth Style) ===
        state_df = df[df["STATE"] == selected_state]
        
        # Check for City Column
        city_col = next((col for col in ["CITY", "DISTRICT", "TOWN"] if col in state_df.columns), None)
        
        if city_col:
            # Aggregate by City
            city_data = state_df.groupby(city_col)["AMOUNT"].sum().reset_index()
            
            # Map Lat/Lon using Expanded Database
            city_data["lat"] = city_data[city_col].map(lambda x: geo_data.CITY_COORDS.get(str(x).upper(), [None, None])[0])
            city_data["lon"] = city_data[city_col].map(lambda x: geo_data.CITY_COORDS.get(str(x).upper(), [None, None])[1])
            
            # Filter valid coordinates
            map_data = city_data.dropna(subset=["lat", "lon"])
            
            if not map_data.empty:
                # Dynamic Center & Zoom
                state_center = geo_data.STATE_COORDS.get(selected_state, [20.59, 78.96])
                
                # Detailed Satellite-Like View (using OpenStreetMap/Positron for detail)
                st.markdown(f"#### 🛰️ {selected_state} Detail Map")
                
                fig_map = px.scatter_mapbox(
                    map_data,
                    lat="lat",
                    lon="lon",
                    size="AMOUNT",
                    color="AMOUNT",
                    color_continuous_scale="Plasma",
                    size_max=40,
                    zoom=6.5,
                    center=dict(lat=state_center[0], lon=state_center[1]),
                    mapbox_style="carto-positron", # High detail light map
                    title=f"<b>{selected_state} Sales Network</b>",
                    hover_name=city_col,
                    hover_data={"lat": False, "lon": False, "AMOUNT": ":.2f"}
                )
                
                fig_map.update_layout(
                    margin={"r":0,"t":40,"l":0,"b":0},
                    coloraxis_colorbar=dict(title="Revenue")
                )
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning(f"📍 No coordinate data found for cities in {selected_state}. Please check spelling or update `geo_data.py`.")

            # Bar Chart Detail
            st.markdown(f"#### 📊 Top Performing Cities")
            city_bar = px.bar(
                city_data.sort_values("AMOUNT", ascending=False).head(15),
                x="AMOUNT", 
                y=city_col,
                orientation='h',
                color="AMOUNT",
                template="corporate_black",
                color_continuous_scale="Plasma"
            )
            city_bar.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Revenue", yaxis_title=None)
            st.plotly_chart(city_bar, use_container_width=True)
            
        else:
            st.error("⚠️ City/District column missing in dataset.")
