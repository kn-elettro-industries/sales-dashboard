import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px

# CORPORATE BLACK PALETTE
# Gold, Dark Gray, Silver, Slate
CORPORATE_BLACK_PALETTE = ["#FFD700", "#555555", "#aaaaaa", "#333333"]

def apply_theme():
    """Applies the Corporate Black theme to Plotly."""
    try:
        # Template
        pio.templates["corporate_black"] = go.layout.Template(
            layout=go.Layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#e0e0e0"),
                title=dict(font=dict(size=16, color="#ffffff", family="Inter", weight="bold")),
                colorway=CORPORATE_BLACK_PALETTE,
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="#333333", 
                    zerolinecolor="#444444",
                    showline=True,
                    linecolor="#444444",
                    tickfont=dict(size=11, color="#a0a0a0")
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor="#333333", 
                    zerolinecolor="#444444",
                    tickfont=dict(size=11, color="#a0a0a0")
                ),
                hoverlabel=dict(
                    bgcolor="#111111",
                    bordercolor="#FFD700",
                    font_size=12,
                    font_family="Inter",
                    font_color="#fff"
                ),
                margin=dict(t=40, l=10, r=10, b=10)
            )
        )
        pio.templates.default = "corporate_black"
    except Exception as e:
        print(f"Error applying theme: {e}")

def get_config():
    return {
        "displayModeBar": False, 
        "scrollZoom": False
    }
