import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px

# CORPORATE BLACK PALETTE
# Rich Gold, Titanium, Silver, Deep Red (for contrast), Emerald
CORPORATE_BLACK_PALETTE = ["#FFD700", "#e0e0e0", "#888888", "#ff4444", "#00CC99", "#A67C00"]

def apply_theme():
    """Applies the Premium Glassmorphism theme to Plotly."""
    try:
        # Template
        pio.templates["corporate_black"] = go.layout.Template(
            layout=go.Layout(
                # Fully transparent background to let CSS glass show through
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#e0e0e0"),
                title=dict(font=dict(size=18, color="#ffffff", family="Inter", weight="bold")),
                colorway=CORPORATE_BLACK_PALETTE,
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(255, 255, 255, 0.05)", # Faint gridlines
                    zerolinecolor="rgba(255, 255, 255, 0.1)",
                    showline=True,
                    linecolor="rgba(255, 255, 255, 0.1)",
                    tickfont=dict(size=12, color="#a0a0a0")
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(255, 255, 255, 0.05)", 
                    zerolinecolor="rgba(255, 255, 255, 0.1)",
                    tickfont=dict(size=12, color="#a0a0a0")
                ),
                hoverlabel=dict(
                    bgcolor="rgba(20, 20, 22, 0.9)",
                    bordercolor="rgba(255, 215, 0, 0.5)",
                    font_size=13,
                    font_family="Inter",
                    font_color="#fff"
                ),
                margin=dict(t=50, l=10, r=10, b=20)
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
