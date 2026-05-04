import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {
    "bs":   "#00C9FF",
    "bt":   "#F97316",
    "mc":   "#A855F7",
    "delta":"#22C55E",
    "gamma":"#EAB308",
    "vega": "#EC4899",
    "theta":"#F97316",
    "rho":  "#6366F1",
}

DARK_BG   = "#0F172A"
PANEL_BG  = "#1E293B"
GRID_COL  = "#334155"
TEXT_COL  = "#CBD5E1"


def _base_layout(title=""):
    return dict(
        title=dict(text=title, font=dict(color=TEXT_COL, size=16)),
        plot_bgcolor=PANEL_BG,
        paper_bgcolor=DARK_BG,
        font=dict(color=TEXT_COL),
        xaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL),
        yaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL),
        legend=dict(bgcolor=DARK_BG, bordercolor=GRID_COL),
        margin=dict(l=50, r=30, t=50, b=50),
    )

def pricing_bar_chart(bs_price, bt_price, mc_price, mc_stderr):
    fig = go.Figure()

    labels = ["Black-Scholes", "Binomial Tree", "Monte Carlo"]
    prices = [bs_price, bt_price, mc_price]
    colors = [COLORS["bs"], COLORS["bt"], COLORS["mc"]]

    fig.add_trace(go.Bar(
        x=labels,
        y=prices,
        marker_color=colors,
        error_y=dict(type="data", array=[0, 0, 1.96 * mc_stderr], visible=True,
                     color=TEXT_COL, thickness=2),
        text=[f"${p:.4f}" for p in prices],
        textposition="outside",
        textfont=dict(color=TEXT_COL),
    ))

    layout = _base_layout("Option Price — Model Comparison")
    layout["yaxis"]["title"] = "Price ($)"
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig

def mc_paths_chart(paths, K, T):
    steps = paths.shape[1]
    t_axis = np.linspace(0, T * 252, steps)   

    fig = go.Figure()

    for i, path in enumerate(paths[:50]):      
        fig.add_trace(go.Scatter(
            x=t_axis, y=path,
            mode="lines",
            line=dict(width=0.6, color=f"rgba(168,85,247,0.25)"),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.add_hline(y=K, line=dict(color="#F87171", dash="dash", width=1.5),
                  annotation_text=f"Strike ${K}", annotation_font_color="#F87171")

    layout = _base_layout("Monte Carlo — Simulated Price Paths")
    layout["xaxis"]["title"] = "Trading Days"
    layout["yaxis"]["title"] = "Spot Price ($)"
    fig.update_layout(**layout)
    return fig

def greeks_subplots(x_values, greeks_data, x_label, selected_greeks):
    greek_map = {k: v for k, v in greeks_data.items() if k in selected_greeks}
    n = len(greek_map)
    if n == 0:
        return go.Figure()

    cols = 2
    rows = (n + 1) // cols

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[g.capitalize() for g in greek_map.keys()],
    )

    for idx, (greek_name, values) in enumerate(greek_map.items()):
        row = idx // cols + 1
        col = idx % cols + 1
        fig.add_trace(
            go.Scatter(
                x=list(x_values),
                y=values,
                mode="lines",
                name=greek_name.capitalize(),
                line=dict(color=COLORS.get(greek_name, "#94A3B8"), width=2.5),
            ),
            row=row, col=col,
        )
        fig.update_xaxes(title_text=x_label, row=row, col=col,
                         gridcolor=GRID_COL, zerolinecolor=GRID_COL)
        fig.update_yaxes(gridcolor=GRID_COL, zerolinecolor=GRID_COL, row=row, col=col)

    fig.update_layout(
        plot_bgcolor=PANEL_BG,
        paper_bgcolor=DARK_BG,
        font=dict(color=TEXT_COL),
        showlegend=False,
        margin=dict(l=50, r=30, t=60, b=50),
        height=280 * rows,
    )
    for annotation in fig.layout.annotations:
        annotation.font.color = TEXT_COL

    return fig

def greek_surface_3d(S_range, T_range, Z_matrix, greek_name):
    fig = go.Figure(data=[go.Surface(
        x=list(T_range),
        y=list(S_range),
        z=Z_matrix,
        colorscale="Viridis",
        colorbar=dict(
            title=dict(
                text="Greek Value", 
                font=dict(color=TEXT_COL)),
            tickfont=dict(color=TEXT_COL)
        ),
    )])

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="Time to Expiry (yrs)", backgroundcolor=DARK_BG,
                       gridcolor=GRID_COL, color=TEXT_COL),
            yaxis=dict(title="Spot Price ($)", backgroundcolor=DARK_BG,
                       gridcolor=GRID_COL, color=TEXT_COL),
            zaxis=dict(title=greek_name.capitalize(), backgroundcolor=DARK_BG,
                       gridcolor=GRID_COL, color=TEXT_COL),
            bgcolor=DARK_BG,
        ),
        paper_bgcolor=DARK_BG,
        font=dict(color=TEXT_COL),
        title=dict(text=f"{greek_name.capitalize()} Surface", font=dict(color=TEXT_COL, size=16)),
        margin=dict(l=0, r=0, t=50, b=0),
        height=500,
    )
    return fig