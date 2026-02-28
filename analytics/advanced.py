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
    Renders a premium Geographic Sales Intelligence visualization.
    """
    if "STATE" not in df.columns:
        st.warning("State data not available.")
        return

    # --- 1. State Filter ---
    states = ["All India"] + sorted(df["STATE"].unique().tolist())
    selected_state = st.selectbox("Select Region:", states)

    if selected_state == "All India":
        # === NATIONAL VIEW ===
        state_data = df.groupby("STATE").agg(
            Revenue=("AMOUNT", "sum"),
            Invoices=("INVOICE_NO", "nunique"),
            Quantity=("QTY", "sum")
        ).reset_index()
        
        total_revenue = state_data["Revenue"].sum()
        state_data["Market_Share"] = (state_data["Revenue"] / total_revenue * 100).round(1)
        state_data["Revenue_Cr"] = (state_data["Revenue"] / 10000000).round(2)
        
        # Map coordinates
        state_data["lat"] = state_data["STATE"].map(lambda x: geo_data.STATE_COORDS.get(x.title(), [20.5937, 78.9629])[0])
        state_data["lon"] = state_data["STATE"].map(lambda x: geo_data.STATE_COORDS.get(x.title(), [20.5937, 78.9629])[1])
        
        # --- Quick Stats Row ---
        top_state = state_data.sort_values("Revenue", ascending=False).iloc[0]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Top State", top_state["STATE"], f"{top_state['Market_Share']}% share")
        with c2:
            st.metric("States Active", f"{len(state_data)}", f"of 30+ states")
        with c3:
            avg_per_state = total_revenue / len(state_data) / 10000000
            st.metric("Avg Revenue/State", f"{avg_per_state:.2f} Cr")

        # --- Premium Bubble Map ---
        st.markdown("#### National Sales Map")
        
        fig = px.scatter_mapbox(
            state_data,
            lat="lat",
            lon="lon",
            size="Revenue",
            color="Revenue",
            color_continuous_scale=[
                [0, "#1a1a2e"],
                [0.2, "#16213e"],
                [0.4, "#e2d810"],
                [0.6, "#d4a600"],
                [0.8, "#FFD700"],
                [1, "#ffffff"]
            ],
            size_max=55,
            zoom=3.8,
            center=dict(lat=22.5, lon=80.0),
            mapbox_style="carto-darkmatter",
            hover_name="STATE",
            hover_data={
                "lat": False,
                "lon": False,
                "Revenue": False,
                "Revenue_Cr": True,
                "Invoices": True,
                "Market_Share": True,
                "Quantity": False
            },
            labels={
                "Revenue_Cr": "Revenue (Cr)",
                "Market_Share": "Market Share %",
                "Invoices": "Total Invoices"
            }
        )
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=500,
            coloraxis_colorbar=dict(
                title="Revenue",
                thickness=12,
                len=0.6,
                bgcolor="rgba(0,0,0,0)",
                tickfont=dict(color="white"),
                title_font=dict(color="white")
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        
        fig.update_traces(
            marker=dict(
                opacity=0.85
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- State Rankings Bar Chart ---
        st.markdown("#### State Revenue Rankings")
        
        top_states = state_data.sort_values("Revenue", ascending=True).tail(15)
        
        fig_bar = px.bar(
            top_states,
            x="Revenue",
            y="STATE",
            orientation="h",
            color="Revenue",
            color_continuous_scale="YlOrBr",
            text=top_states["Revenue_Cr"].apply(lambda x: f"{x:.1f} Cr"),
            template="plotly_dark"
        )
        
        fig_bar.update_layout(
            height=450,
            xaxis_title="Revenue",
            yaxis_title=None,
            showlegend=False,
            coloraxis_showscale=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=0, r=20, t=10, b=30)
        )
        
        fig_bar.update_traces(
            textposition="outside",
            textfont=dict(color="#FFD700", size=12),
            marker_line_color="#FFD700",
            marker_line_width=0.5
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        # === STATE DRILLDOWN ===
        state_df = df[df["STATE"] == selected_state]
        
        city_col = next((col for col in ["CITY", "DISTRICT", "TOWN"] if col in state_df.columns), None)
        
        if city_col:
            city_data = state_df.groupby(city_col).agg(
                Revenue=("AMOUNT", "sum"),
                Invoices=("INVOICE_NO", "nunique")
            ).reset_index()
            
            city_data["Revenue_L"] = (city_data["Revenue"] / 100000).round(1)
            
            # Map coordinates
            city_data["lat"] = city_data[city_col].map(lambda x: geo_data.CITY_COORDS.get(str(x).upper(), [None, None])[0])
            city_data["lon"] = city_data[city_col].map(lambda x: geo_data.CITY_COORDS.get(str(x).upper(), [None, None])[1])
            
            map_data = city_data.dropna(subset=["lat", "lon"])
            
            # Quick Stats
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Cities", f"{len(city_data)}")
            with c2:
                st.metric("State Revenue", f"{state_df['AMOUNT'].sum()/10000000:.2f} Cr")
            with c3:
                top_city = city_data.sort_values("Revenue", ascending=False).iloc[0]
                st.metric("Top City", top_city[city_col])
            
            if not map_data.empty:
                state_center = geo_data.STATE_COORDS.get(selected_state, [20.59, 78.96])
                
                st.markdown(f"#### {selected_state} City Map")
                
                fig_map = px.scatter_mapbox(
                    map_data,
                    lat="lat",
                    lon="lon",
                    size="Revenue",
                    color="Revenue",
                    color_continuous_scale="YlOrBr",
                    size_max=40,
                    zoom=6.2,
                    center=dict(lat=state_center[0], lon=state_center[1]),
                    mapbox_style="carto-darkmatter",
                    hover_name=city_col,
                    hover_data={
                        "lat": False, "lon": False,
                        "Revenue_L": True,
                        "Invoices": True,
                        "Revenue": False
                    },
                    labels={"Revenue_L": "Revenue (L)", "Invoices": "Invoices"}
                )
                
                fig_map.update_layout(
                    margin=dict(r=0, t=0, l=0, b=0),
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    coloraxis_colorbar=dict(title="Revenue", thickness=12, tickfont=dict(color="white"), title_font=dict(color="white"))
                )
                
                fig_map.update_traces(marker=dict(opacity=0.85))
                
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.info(f"No coordinate data for cities in {selected_state}. Showing table only.")

            # City Bar Chart
            st.markdown(f"#### Top Cities in {selected_state}")
            top_cities = city_data.sort_values("Revenue", ascending=True).tail(15)
            
            fig_city = px.bar(
                top_cities,
                x="Revenue",
                y=city_col,
                orientation="h",
                color="Revenue",
                color_continuous_scale="YlOrBr",
                text=top_cities["Revenue_L"].apply(lambda x: f"{x:.0f} L"),
                template="plotly_dark"
            )
            
            fig_city.update_layout(
                height=400,
                xaxis_title="Revenue", yaxis_title=None,
                showlegend=False, coloraxis_showscale=False,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
                margin=dict(l=0, r=20, t=10, b=30)
            )
            fig_city.update_traces(textposition="outside", textfont=dict(color="#FFD700", size=11), marker_line_color="#FFD700", marker_line_width=0.5)
            
            st.plotly_chart(fig_city, use_container_width=True)
            
        else:
            st.error("City/District column missing in dataset.")

