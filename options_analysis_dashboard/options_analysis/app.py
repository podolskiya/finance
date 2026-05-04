import numpy as np
import streamlit as st

from models.black_scholes import black_scholes_price
from models.binomial_tree import binomial_tree_price
from models.monte_carlo import monte_carlo_price
from greeks.greeks import (
    greeks_vs_spot, greeks_vs_vol, greeks_vs_time,
    delta, gamma, vega, theta, rho,
)
from utils.plotting import (
    pricing_bar_chart, mc_paths_chart,
    greeks_subplots, greek_surface_3d,
)

st.set_page_config(
    page_title="Options Pricing Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0F172A; color: #CBD5E1; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1E293B; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
    }
    div[data-testid="metric-container"] label { color: #94A3B8 !important; }
    div[data-testid="metric-container"] div  { color: #F1F5F9 !important; }

    /* Tab styling */
    button[data-baseweb="tab"] { color: #94A3B8 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #00C9FF !important; }

    /* Dividers */
    hr { border-color: #334155; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("Parameters")
st.sidebar.markdown("---")

st.sidebar.subheader("Option Contract")
option_type  = st.sidebar.selectbox("Option Type", ["call", "put"])
option_style = st.sidebar.selectbox("Exercise Style", ["european", "american"],
                                    help="American options allow early exercise (Binomial Tree only)")

st.sidebar.subheader("Market Inputs")
S     = st.sidebar.number_input("Spot Price (S)",      min_value=1.0,   max_value=10_000.0, value=100.0,  step=1.0)
K     = st.sidebar.number_input("Strike Price (K)",    min_value=1.0,   max_value=10_000.0, value=100.0,  step=1.0)
T     = st.sidebar.slider("Time to Expiry (years)",    min_value=0.01,  max_value=5.0,      value=1.0,    step=0.01)
r     = st.sidebar.slider("Risk-Free Rate (%)",        min_value=0.0,   max_value=15.0,     value=5.0,    step=0.1) / 100
sigma = st.sidebar.slider("Volatility / σ (%)",        min_value=1.0,   max_value=100.0,    value=20.0,   step=0.5) / 100

st.sidebar.subheader("Model Settings")
bt_steps = st.sidebar.number_input("Binomial Tree Steps", min_value=10, max_value=1000, value=200, step=10)
mc_sims  = st.sidebar.number_input("MC Simulations",     min_value=1000, max_value=100_000, value=10_000, step=1000)

st.sidebar.markdown("---")
st.sidebar.markdown("*Built with Black-Scholes · CRR Binomial Tree · Monte Carlo GBM*")

bs_price = black_scholes_price(S, K, T, r, sigma, option_type)
bt_price = binomial_tree_price(S, K, T, r, sigma, steps=bt_steps,
                               option_type=option_type, style=option_style)
mc_price, mc_stderr, mc_paths = monte_carlo_price(S, K, T, r, sigma,
                                                   simulations=mc_sims,
                                                   option_type=option_type)

g_delta = delta(S, K, T, r, sigma, option_type)
g_gamma = gamma(S, K, T, r, sigma)
g_vega  = vega(S, K, T, r, sigma)
g_theta = theta(S, K, T, r, sigma, option_type)
g_rho   = rho(S, K, T, r, sigma, option_type)

st.title("Options Pricing & Greeks Dashboard")
st.markdown(
    f"**{option_type.upper()} | {option_style.capitalize()} | "
    f"S=${S:.0f} K=${K:.0f} T={T:.2f}yr σ={sigma*100:.1f}% r={r*100:.1f}%**"
)
st.markdown("---")

st.subheader("Model Price Comparison")

col1, col2, col3 = st.columns(3)
col1.metric("Black-Scholes",  f"${bs_price:.4f}")
col2.metric("Binomial Tree",  f"${bt_price:.4f}",
            delta=f"{bt_price - bs_price:+.4f} vs BS")
col3.metric("Monte Carlo",    f"${mc_price:.4f}",
            delta=f"{mc_price - bs_price:+.4f} vs BS",
            help=f"95% CI: ±${1.96*mc_stderr:.4f}")

st.plotly_chart(pricing_bar_chart(bs_price, bt_price, mc_price, mc_stderr),
                use_container_width=True)

st.markdown("---")

st.subheader("Current Greeks")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Δ Delta",  f"{g_delta:.4f}", help="∂Price/∂Spot")
c2.metric("Γ Gamma",  f"{g_gamma:.4f}", help="∂²Price/∂Spot²")
c3.metric("ν Vega",   f"{g_vega:.4f}",  help="∂Price/∂σ (per 1% vol)")
c4.metric("Θ Theta",  f"{g_theta:.4f}", help="∂Price/∂t (per day)")
c5.metric("ρ Rho",    f"{g_rho:.4f}",   help="∂Price/∂r (per 1% rate)")

st.markdown("---")


st.subheader("Greeks Sensitivity Analysis")

all_greeks = ["delta", "gamma", "vega", "theta", "rho"]
selected_greeks = st.multiselect(
    "Select Greeks to Display",
    options=all_greeks,
    default=["delta", "gamma", "vega"],
    format_func=str.capitalize,
)

tab1, tab2, tab3 = st.tabs(["📍 vs Spot Price", "🌊 vs Volatility", "⏳ vs Time to Expiry"])

with tab1:
    S_min = max(1.0, S * 0.5)
    S_max = S * 1.5
    S_range = np.linspace(S_min, S_max, 200)
    g_data = greeks_vs_spot(S_range, K, T, r, sigma, option_type)
    fig = greeks_subplots(S_range, g_data, x_label="Spot Price ($)", selected_greeks=selected_greeks)
    # Add vertical line for current spot
    for trace in fig.data:
        pass  # Plotly subplots make vlines tricky; we annotate in layout instead
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    sigma_range = np.linspace(0.01, 1.0, 200)   # 1% to 100% vol
    g_data = greeks_vs_vol(S, K, T, r, sigma_range, option_type)
    fig = greeks_subplots(sigma_range * 100, g_data,
                          x_label="Volatility (%)", selected_greeks=selected_greeks)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    T_range = np.linspace(0.01, 2.0, 200)
    g_data = greeks_vs_time(S, K, T_range, r, sigma, option_type)
    fig = greeks_subplots(T_range, g_data,
                          x_label="Time to Expiry (years)", selected_greeks=selected_greeks)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


st.subheader("3-D Greek Surface (Spot × Time)")

col_sel, col_res = st.columns([1, 3])
with col_sel:
    surface_greek = st.selectbox("Greek for Surface", all_greeks, format_func=str.capitalize)
    surface_res   = st.slider("Resolution", min_value=20, max_value=80, value=40, step=10,
                               help="Higher = smoother but slower")

S_surf  = np.linspace(max(1.0, S * 0.5), S * 1.5, surface_res)
T_surf  = np.linspace(0.05, 2.0, surface_res)

from greeks.greeks import delta as _d, gamma as _g, vega as _v, theta as _t, rho as _r
greek_fn_map = {
    "delta":  lambda s, t: _d(s, K, t, r, sigma, option_type),
    "gamma":  lambda s, t: _g(s, K, t, r, sigma),
    "vega":   lambda s, t: _v(s, K, t, r, sigma),
    "theta":  lambda s, t: _t(s, K, t, r, sigma, option_type),
    "rho":    lambda s, t: _r(s, K, t, r, sigma, option_type),
}

fn = greek_fn_map[surface_greek]
Z_matrix = np.array([[fn(s, t) for t in T_surf] for s in S_surf])

with col_res:
    st.plotly_chart(greek_surface_3d(S_surf, T_surf, Z_matrix, surface_greek),
                    use_container_width=True)

st.markdown("---")


st.subheader("Monte Carlo — Simulated Price Paths")
st.caption(f"Showing 50 of {mc_sims:,} simulated paths · 95% CI: ${mc_price - 1.96*mc_stderr:.4f} – ${mc_price + 1.96*mc_stderr:.4f}")
st.plotly_chart(mc_paths_chart(mc_paths, K, T), use_container_width=True)

st.markdown("---")


st.subheader("Binomial Tree Convergence")
st.caption("Watch how the Binomial Tree price converges to Black-Scholes as steps increase")

steps_range = list(range(5, 305, 5))
with st.spinner("Computing convergence..."):
    bt_prices = [binomial_tree_price(S, K, T, r, sigma, steps=n,
                                      option_type=option_type, style="european")
                 for n in steps_range]

import plotly.graph_objects as go
fig_conv = go.Figure()
fig_conv.add_trace(go.Scatter(
    x=steps_range, y=bt_prices,
    mode="lines+markers",
    name="Binomial Tree",
    line=dict(color="#F97316", width=2),
    marker=dict(size=4),
))
fig_conv.add_hline(
    y=bs_price, line=dict(color="#00C9FF", dash="dash", width=2),
    annotation_text=f"BS Price: ${bs_price:.4f}",
    annotation_font_color="#00C9FF",
)
fig_conv.update_layout(
    plot_bgcolor="#1E293B", paper_bgcolor="#0F172A",
    font=dict(color="#CBD5E1"),
    xaxis=dict(title="Number of Steps", gridcolor="#334155"),
    yaxis=dict(title="Option Price ($)", gridcolor="#334155"),
    title=dict(text="Binomial Tree Convergence to Black-Scholes", font=dict(color="#CBD5E1")),
    legend=dict(bgcolor="#0F172A"),
    height=400,
)
st.plotly_chart(fig_conv, use_container_width=True)