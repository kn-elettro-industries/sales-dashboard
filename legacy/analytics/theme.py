import plotly.io as pio
import plotly.graph_objects as go

# Industrial Dark Palette — clean, professional, high contrast
CORPORATE_PALETTE = ["#FFD700", "#58a6ff", "#3fb950", "#f85149", "#bc8cff", "#79c0ff", "#d2a8ff", "#ffa657"]

def apply_theme():
    """Applies clean industrial dark theme to Plotly charts."""
    try:
        pio.templates["corporate_black"] = go.layout.Template(
            layout=go.Layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, -apple-system, sans-serif", color="#e6eaf0", size=12),
                title=dict(font=dict(size=14, color="#f0f6fc", family="Inter")),
                colorway=CORPORATE_PALETTE,
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(255,255,255,0.06)",
                    zerolinecolor="rgba(255,255,255,0.08)",
                    showline=False,
                    tickfont=dict(size=11, color="#8b949e")
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(255,255,255,0.06)",
                    zerolinecolor="rgba(255,255,255,0.08)",
                    tickfont=dict(size=11, color="#8b949e")
                ),
                hoverlabel=dict(
                    bgcolor="#161b22",
                    bordercolor="#30363d",
                    font_size=12,
                    font_family="Inter",
                    font_color="#f0f6fc"
                ),
                margin=dict(t=40, l=10, r=10, b=20)
            )
        )
        pio.templates.default = "corporate_black"
    except Exception as e:
        print(f"Theme error: {e}")

def get_config():
    return {
        "displayModeBar": False, 
        "scrollZoom": False
    }
