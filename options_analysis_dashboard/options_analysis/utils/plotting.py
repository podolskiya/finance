import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {
    "bs":    "#4F8EF7",   # blue
    "bt":    "#F4A62A",   # amber
    "mc":    "#7C5CFC",   # violet
    "delta": "#3BBFAD",
    "gamma": "#F4A62A",
    "vega":  "#7C5CFC",
    "theta": "#F06B6B",
    "rho":   "#3DBF8C",
}

BG       = "#FFFFFF"
PAPER    = "#FFFFFF"
GRID_COL = "#DDE3F0"
TEXT_COL = "#1A2035"


def _base_layout(title=""):
    return dict(
        title=dict(text=title, font=dict(color=TEXT_COL, size=15)),
        plot_bgcolor=BG,
        paper_bgcolor=PAPER,
        font=dict(color=TEXT_COL, family="DM Sans"),
        xaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL, linecolor=GRID_COL),
        yaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL, linecolor=GRID_COL),
        legend=dict(bgcolor=PAPER, bordercolor=GRID_COL),
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
        plot_bgcolor=BG,
        paper_bgcolor=PAPER,
        font=dict(color=TEXT_COL, family="DM Sans"),
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
                xaxis=dict(title="Time to Expiry (yrs)", backgroundcolor="#F4F6FC",
                        gridcolor=GRID_COL, color=TEXT_COL),
                yaxis=dict(title="Spot Price ($)",        backgroundcolor="#F4F6FC",
                        gridcolor=GRID_COL, color=TEXT_COL),
                zaxis=dict(title=greek_name.capitalize(), backgroundcolor="#F4F6FC",
                        gridcolor=GRID_COL, color=TEXT_COL),
                bgcolor="#F4F6FC",
            ),
            paper_bgcolor=PAPER,
        font=dict(color=TEXT_COL),
        title=dict(text=f"{greek_name.capitalize()} Surface", font=dict(color=TEXT_COL, size=16)),
        margin=dict(l=0, r=0, t=50, b=0),
        height=500,
    )
    return fig

def vol_smile_chart(strikes, ivs, smile_vols, S):
    import plotly.graph_objects as go
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(strikes), y=[v * 100 if v else None for v in ivs],
        mode="lines+markers",
        name="Recovered IV (Brent)",
        line=dict(color="#38BDF8", width=2.5),
        marker=dict(size=5),
    ))

    fig.add_vline(x=S, line=dict(color="#FB7185", dash="dash", width=1.5),
                  annotation_text="ATM", annotation_font_color="#FB7185")

    layout = _base_layout("Volatility Smile — IV vs Strike")
    layout["xaxis"]["title"] = "Strike Price ($)"
    layout["yaxis"]["title"] = "Implied Volatility (%)"
    fig.update_layout(**layout)
    return fig

def pnl_heatmap(S_range, sigma_range, K, T, r, option_type, premium_paid):
    import numpy as np
    from models.black_scholes import black_scholes_price

    Z = np.zeros((len(sigma_range), len(S_range)))
    for i, sig in enumerate(sigma_range):
        for j, s in enumerate(S_range):
            price = black_scholes_price(s, K, T, r, sig, option_type)
            Z[i, j] = price - premium_paid   

    fig = go.Figure(data=go.Heatmap(
        x=[f"${s:.0f}" for s in S_range],
        y=[f"{sig*100:.0f}%" for sig in sigma_range],
        z=Z,
        colorscale=[
            [0.0,  "#7f1d1d"],   
            [0.45, "#ef4444"], 
            [0.5,  "#1E293B"],  
            [0.55, "#4ade80"], 
            [1.0,  "#14532d"],  
        ],
        zmid=0,
        colorbar=dict(title=dict(
            text="P&L ($)",
            font=dict(color=TEXT_COL)
            ),
            tickfont=dict(color=TEXT_COL),
        ),
        hoverongaps=False,
        hovertemplate="Spot: %{x}<br>Vol: %{y}<br>P&L: $%{z:.4f}<extra></extra>",
    ))

    layout = _base_layout(f"P&L Heatmap — {option_type.upper()} | Entry Premium ${premium_paid:.4f}")
    layout["xaxis"]["title"] = "Spot Price at Analysis"
    layout["yaxis"]["title"] = "Volatility"
    layout["height"] = 420
    fig.update_layout(**layout)
    return fig