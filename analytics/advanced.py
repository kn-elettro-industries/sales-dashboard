import streamlit as st
import plotly.express as px
import pandas as pd

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
        # === A. National State-Level Heatmap ===
        heatmap_data = df.groupby("STATE")["AMOUNT"].sum().reset_index()
        
        # Load Lat/Lon for Indian States (Hardcoded for simplicity & speed)
        lat_lon = {
            "Maharashtra": [19.7515, 75.7139],
            "Delhi": [28.7041, 77.1025],
            "Karnataka": [15.3173, 75.7139],
            "Gujarat": [22.2587, 71.1924],
            "Tamil Nadu": [11.1271, 78.6569],
            "Uttar Pradesh": [26.8467, 80.9462],
            "West Bengal": [22.9868, 87.8550],
            "Telangana": [18.1124, 79.0193],
            "Rajasthan": [27.0238, 74.2179],
            "Madhya Pradesh": [22.9734, 78.6569],
            "Haryana": [29.0588, 76.0856],
            "Bihar": [25.0961, 85.3131],
            "Punjab": [31.1471, 75.3412],
            "Kerala": [10.8505, 76.2711],
            "Andhra Pradesh": [15.9129, 79.7400],
            "Odisha": [20.9517, 85.0985],
            "Jharkhand": [23.6102, 85.2799],
            "Chhattisgarh": [21.2787, 81.8661],
            "Assam": [26.2006, 92.9376],
            "Uttarakhand": [30.0668, 79.0193],
            "Himachal Pradesh": [31.1048, 77.1734],
            "Tripura": [23.9408, 91.9882],
            "Meghalaya": [25.4670, 91.3662],
            "Manipur": [24.6637, 93.9063],
            "Nagaland": [26.1584, 94.5624],
            "Goa": [15.2993, 74.1240],
            "Arunachal Pradesh": [28.2180, 94.7278],
            "Mizoram": [23.1645, 92.9376],
            "Sikkim": [27.5330, 88.5122],
            "Chandigarh": [30.7333, 76.7794]
        }
        
        heatmap_data["lat"] = heatmap_data["STATE"].map(lambda x: lat_lon.get(x.title(), [20.5937, 78.9629])[0])
        heatmap_data["lon"] = heatmap_data["STATE"].map(lambda x: lat_lon.get(x.title(), [20.5937, 78.9629])[1])

        # Glowing Gold Heatmap
        gold_scale = [
            [0.0, "rgba(0,0,0,0)"],
            [0.2, "#332200"],
            [0.4, "#664400"],
            [0.6, "#CC8800"],
            [0.8, "#FFD700"],  # Gold
            [1.0, "#FFFFFF"]   # White Hot
        ]

        fig = px.density_mapbox(
            heatmap_data, 
            lat='lat', 
            lon='lon', 
            z='AMOUNT', 
            radius=40,  
            center=dict(lat=20.5937, lon=78.9629), 
            zoom=3.5,
            mapbox_style="carto-darkmatter",
            color_continuous_scale=gold_scale,
            opacity=0.8,
            title="<b>National Sales Density (Glowing Gold)</b>"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    else:
        # === B. City-Level Drilldown ===
        state_df = df[df["STATE"] == selected_state]
        
        # Check for City Column
        city_col = next((col for col in ["CITY", "DISTRICT", "TOWN"] if col in state_df.columns), None)
        
        if city_col:
            # Aggregate by City
            city_data = state_df.groupby(city_col)["AMOUNT"].sum().reset_index()
            
            # City Coordinates (Major Cities Fallback)
            # Add more as needed. In production, use geopy or a DB.
            city_coords = {
                "MUMBAI": [19.0760, 72.8777], "PUNE": [18.5204, 73.8567], "NAGPUR": [21.1458, 79.0882],
                "NASHIK": [19.9975, 73.7898], "THANE": [19.2183, 72.9781], "AURANGABAD": [19.8762, 75.3433],
                "DELHI": [28.7041, 77.1025], "NEW DELHI": [28.6139, 77.2090],
                "BANGALORE": [12.9716, 77.5946], "BENGALURU": [12.9716, 77.5946], "MYSORE": [12.2958, 76.6394],
                "CHENNAI": [13.0827, 80.2707], "COIMBATORE": [11.0168, 76.9558], "MADURAI": [9.9252, 78.1198],
                "HYDERABAD": [17.3850, 78.4867], "WARANGAL": [17.9689, 79.5941],
                "KOLKATA": [22.5726, 88.3639], "HOWRAH": [22.5958, 88.2636],
                "AHMEDABAD": [23.0225, 72.5714], "SURAT": [21.1702, 72.8311], "VADODARA": [22.3072, 73.1812],
                "JAIPUR": [26.9124, 75.7873], "UDAIPUR": [24.5854, 73.7125], "JODHPUR": [26.2389, 73.0243],
                "LUCKNOW": [26.8467, 80.9462], "KANPUR": [26.4499, 80.3319], "VARANASI": [25.3176, 82.9739],
                "BHOPAL": [23.2599, 77.4126], "INDORE": [22.7196, 75.8577],
                "PATNA": [25.0961, 85.3131], "RANCHI": [23.3441, 85.3096],
                "CHANDIGARH": [30.7333, 76.7794], "LUDHIANA": [30.9010, 75.8573], "AMRITSAR": [31.6340, 74.8723],
                "THIRUVANANTHAPURAM": [8.5241, 76.9366], "KOCHI": [9.9312, 76.2673],
                "BHUBANESWAR": [20.2961, 85.8245], "CUTTACK": [20.4625, 85.8828],
                "GUWAHATI": [26.1445, 91.7362], "RAIPUR": [21.2514, 81.6296],
                "DEHRADUN": [30.3165, 78.0322], "SHIMLA": [31.1048, 77.1734], "PANAJI": [15.4909, 73.8278]
            }
            
            # Map Lat/Lon
            city_data["lat"] = city_data[city_col].map(lambda x: city_coords.get(str(x).upper(), [None, None])[0])
            city_data["lon"] = city_data[city_col].map(lambda x: city_coords.get(str(x).upper(), [None, None])[1])
            
            # Filter valid coordinates for Map
            map_data = city_data.dropna(subset=["lat", "lon"])
            
            if not map_data.empty:
                # Calculate Center based on valid points
                center_lat = map_data["lat"].mean()
                center_lon = map_data["lon"].mean()
                
                # City Heatmap
                fig_city = px.density_mapbox(
                    map_data, 
                    lat='lat', 
                    lon='lon', 
                    z='AMOUNT', 
                    radius=25,
                    center=dict(lat=center_lat, lon=center_lon), 
                    zoom=6,
                    mapbox_style="carto-darkmatter",
                    color_continuous_scale="solar", # Keep slightly different to distinguish from National
                    opacity=0.8,
                    title=f"<b>{selected_state}: City-Level Sales Density</b>"
                )
                st.plotly_chart(fig_city, use_container_width=True)
            else:
                st.info(f"Geographic coordinates missing for cities in {selected_state}. Showing bar chart only.")

            # Always show Bar Chart for Detail
            st.markdown(f"#### 🏙️ Top Cities in {selected_state}")
            city_bar = px.bar(
                city_data.sort_values("AMOUNT", ascending=False).head(20),
                x=city_col,
                y="AMOUNT",
                color="AMOUNT",
                title=f"Top 20 Cities in {selected_state}",
                template="corporate_black",
                color_continuous_scale="solar"
            )
            city_bar.update_layout(xaxis_title=None, yaxis_title="Revenue")
            st.plotly_chart(city_bar, use_container_width=True)
            
        else:
            st.warning(f"No City/District data found for {selected_state}. Please ensure 'CITY' column exists.")
