import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.style import metric_card
from strategies.portfolio import (get_returns, optimise_all,
                                   portfolio_metrics, annualised_stats)

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)

STRATEGY_COLORS = {
    'Max Sharpe':          '#1A1A1A',
    'Min Volatility':      '#3B82F6',
    'Risk Parity':         '#10B981',
    'Max Diversification': '#F59E0B',
    'Equal Weight':        '#8B5CF6',
}

PRESETS = {
    "🖥️  Tech Giants":    ["AAPL","MSFT","GOOGL","NVDA","META","AMZN"],
    "🌍  Global Macro":   ["SPY","QQQ","GLD","TLT","EEM","VNQ"],
    "💰  Value Mix":      ["BRK-B","JPM","JNJ","PG","KO","XOM"],
    "🚀  Growth":         ["NVDA","TSLA","AMD","CRM","SHOP","NET"],
    "⚖️  Balanced":       ["SPY","TLT","GLD","AAPL","JPM","JNJ"],
}


def frontier_chart(frontier: pd.DataFrame,
                   strategy_points: dict) -> go.Figure:
    fig = go.Figure()

    # Efficient frontier line
    fig.add_trace(go.Scatter(
        x=frontier['Volatility'] * 100,
        y=frontier['Return']     * 100,
        mode='lines',
        name='Efficient Frontier',
        line=dict(color='#6B7280', width=2, dash='dot'),
        hovertemplate='Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<extra></extra>'
    ))

    # Colour frontier by Sharpe
    fig.add_trace(go.Scatter(
        x=frontier['Volatility'] * 100,
        y=frontier['Return']     * 100,
        mode='markers',
        name='Frontier Points',
        marker=dict(
            color=frontier['Sharpe'],
            colorscale='RdYlGn',
            size=6,
            colorbar=dict(title='Sharpe', thickness=12)
        ),
        hovertemplate='Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<extra></extra>'
    ))

    # Strategy points
    for name, data in strategy_points.items():
        m = data['metrics']
        fig.add_trace(go.Scatter(
            x=[m['volatility'] * 100],
            y=[m['return']     * 100],
            mode='markers+text',
            name=name,
            marker=dict(
                color=STRATEGY_COLORS.get(name, '#333'),
                size=14, symbol='star',
                line=dict(color='white', width=1.5)
            ),
            text=[name.split()[0]],
            textposition='top center',
            textfont=dict(size=9),
            hovertemplate=(
                f"<b>{name}</b><br>"
                f"Return: {m['return']*100:.1f}%<br>"
                f"Vol: {m['volatility']*100:.1f}%<br>"
                f"Sharpe: {m['sharpe']:.2f}<extra></extra>"
            )
        ))

    fig.update_layout(
        height=420,
        title="Efficient Frontier & Portfolio Strategies",
        xaxis_title="Annualised Volatility (%)",
        yaxis_title="Annualised Return (%)",
        legend=dict(orientation="v", x=1.12),
        **CHART_THEME
    )
    return fig


def weights_chart(results: dict, selected: str) -> go.Figure:
    w      = results[selected]['weights']
    colors = px.colors.qualitative.Set2
    fig    = go.Figure(go.Pie(
        labels=w.index.tolist(),
        values=w.values.tolist(),
        hole=0.55,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textfont=dict(size=12)
    ))
    fig.update_layout(
        height=300,
        title=f"{selected} — Weights",
        showlegend=False,
        **{k: v for k, v in CHART_THEME.items()
           if k not in ['xaxis','yaxis']}
    )
    return fig


def weights_bar_chart(results: dict) -> go.Figure:
    fig    = go.Figure()
    colors = px.colors.qualitative.Set2

    strategies = list(results.keys())
    tickers    = results[strategies[0]]['weights'].index.tolist()

    for i, ticker in enumerate(tickers):
        vals = [results[s]['weights'][ticker] * 100
                for s in strategies]
        fig.add_trace(go.Bar(
            name=ticker,
            x=strategies, y=vals,
            marker_color=colors[i % len(colors)]
        ))

    fig.update_layout(
        height=300,
        title="Weight Allocation by Strategy",
        barmode='stack',
        legend=dict(orientation="h"),
        yaxis=dict(ticksuffix="%", **CHART_THEME['yaxis']),
        **{k: v for k, v in CHART_THEME.items() if k != 'yaxis'}
    )
    return fig


def equity_curves_chart(results: dict) -> go.Figure:
    fig = go.Figure()
    for name, data in results.items():
        bt = data['backtest']
        fig.add_trace(go.Scatter(
            x=bt.index, y=bt['Equity'],
            name=name, mode='lines',
            line=dict(color=STRATEGY_COLORS.get(name,'#333'), width=2)
        ))
    fig.update_layout(
        height=320,
        title="Portfolio Equity Curves (Rebalanced)",
        legend=dict(orientation="h"),
        hovermode="x unified",
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def correlation_chart(returns: pd.DataFrame) -> go.Figure:
    corr = returns.corr()
    fig  = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale='RdYlGn',
        zmin=-1, zmax=1,
        text=np.round(corr.values, 2),
        texttemplate='%{text}',
        textfont=dict(size=11),
        colorbar=dict(thickness=12)
    ))
    fig.update_layout(
        height=380,
        title="Asset Correlation Matrix",
        **{k: v for k, v in CHART_THEME.items()
           if k not in ['xaxis','yaxis','hovermode']}
    )
    return fig


def drawdown_chart(results: dict) -> go.Figure:
    fig = go.Figure()
    for name, data in results.items():
        eq  = data['backtest']['Equity']
        dd  = (eq - eq.cummax()) / eq.cummax() * 100
        fig.add_trace(go.Scatter(
            x=eq.index, y=dd,
            name=name, mode='lines',
            line=dict(color=STRATEGY_COLORS.get(name,'#333'),
                      width=1.5)
        ))
    fig.update_layout(
        height=240,
        title="Drawdown Comparison",
        legend=dict(orientation="h"),
        hovermode="x unified",
        **CHART_THEME
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def show():
    st.markdown("""
        <div class='page-title'>Portfolio Optimiser</div>
        <div class='page-subtitle'>
            Markowitz · Risk Parity · Max Diversification ·
            Efficient Frontier
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📊 Portfolio Settings**")

        preset  = st.selectbox("Preset Universe", list(PRESETS.keys()))
        custom  = st.text_input(
            "Custom tickers (comma-separated)", ""
        )
        tickers = (
            [t.strip().upper() for t in custom.split(',') if t.strip()]
            if custom else PRESETS[preset]
        )
        st.caption(f"Selected: {', '.join(tickers)}")

        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", pd.to_datetime("2020-01-01"))
        with col2:
            end   = st.date_input("End",   pd.to_datetime("2024-01-01"))

        st.markdown("**Constraints**")
        long_only  = st.checkbox("Long Only", value=True)
        rebalance  = st.selectbox(
            "Rebalance Frequency",
            ["D","W","M","Q"],
            index=2,
            format_func=lambda x: {
                'D':'Daily','W':'Weekly',
                'M':'Monthly','Q':'Quarterly'
            }[x]
        )
        rf      = st.slider("Risk-Free Rate (%)", 0.0, 5.0, 2.0, 0.25) / 100
        capital = st.number_input("Capital ($)", value=100_000, step=10_000)

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888; line-height:1.7;'>
                <b>Max Sharpe:</b> Best risk-adjusted return<br>
                <b>Min Vol:</b> Lowest possible volatility<br>
                <b>Risk Parity:</b> Equal risk per asset<br>
                <b>Max Diversification:</b> Least correlated<br>
                <b>Equal Weight:</b> Naive 1/N baseline
            </div>
        """, unsafe_allow_html=True)

        run = st.button("▶  Optimise Portfolio")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>📊</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    Portfolio Optimisation Engine
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;
                            max-width:450px; margin-left:auto; margin-right:auto;'>
                    Select a universe of assets, choose constraints,
                    and run all five optimisation strategies simultaneously.
                    Compare on the efficient frontier and backtest with
                    realistic rebalancing.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # ── Run ──
    progress = st.progress(0, text="Fetching asset returns...")
    with st.spinner(""):
        returns = get_returns(tickers, str(start), str(end))

    if returns.empty or len(returns.columns) < 2:
        st.error("Need at least 2 valid tickers with overlapping data.")
        return

    actual_tickers = list(returns.columns)
    if len(actual_tickers) < len(tickers):
        st.warning(f"Could not fetch: "
                   f"{set(tickers)-set(actual_tickers)}. "
                   f"Continuing with: {actual_tickers}")

    progress.progress(30, text="Running optimisations...")
    results  = optimise_all(returns, rf, long_only, rebalance, capital)
    strategies = results['strategies']
    frontier   = results['frontier']
    progress.progress(90, text="Building charts...")

    # ── Summary Cards — Best Strategy ──
    sharpes = {
        n: d['metrics']['sharpe']
        for n, d in strategies.items()
    }
    best_name = max(sharpes, key=sharpes.get)
    best      = strategies[best_name]

    st.markdown(f"""
        <div class='section-card'
             style='background:#1A1A1A; color:#FFFFFF;
                    border-radius:16px; padding:1.2rem 1.6rem;
                    margin-bottom:1.5rem;'>
            <div style='font-size:0.75rem; color:#888;
                        text-transform:uppercase; letter-spacing:0.05em;'>
                Best Risk-Adjusted Strategy
            </div>
            <div style='font-size:1.5rem; font-weight:700;
                        color:#FFFFFF; margin-top:0.2rem;'>
                {best_name}
            </div>
            <div style='display:flex; gap:2rem; margin-top:0.8rem;'>
                <div>
                    <div style='font-size:0.72rem; color:#888;'>Return</div>
                    <div style='font-weight:600; color:#10B981;'>
                        {best["metrics"]["return"]*100:.1f}%
                    </div>
                </div>
                <div>
                    <div style='font-size:0.72rem; color:#888;'>Volatility</div>
                    <div style='font-weight:600; color:#FFFFFF;'>
                        {best["metrics"]["volatility"]*100:.1f}%
                    </div>
                </div>
                <div>
                    <div style='font-size:0.72rem; color:#888;'>Sharpe</div>
                    <div style='font-weight:600; color:#FFFFFF;'>
                        {best["metrics"]["sharpe"]:.3f}
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Metrics Table ──
    rows = []
    for name, data in strategies.items():
        m  = data['metrics']
        bt = data['backtest']
        eq = bt['Equity']
        dd = ((eq - eq.cummax()) / eq.cummax()).min() * 100
        rows.append({
            "Strategy":   name,
            "Ann. Return": f"{m['return']*100:.1f}%",
            "Ann. Vol":    f"{m['volatility']*100:.1f}%",
            "Sharpe":      round(m['sharpe'], 3),
            "Max DD":      f"{dd:.1f}%",
            "Final Equity": f"${eq.iloc[-1]:,.0f}",
        })
    cmp_df = pd.DataFrame(rows).set_index("Strategy")

    def highlight_sharpe(s):
        styles = ['']*len(s)
        styles[s.values.argmax()] = (
            'background-color:#1A1A1A; color:#FFFFFF; font-weight:700'
        )
        return styles

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.dataframe(
        cmp_df.style.apply(highlight_sharpe, subset=['Sharpe']),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    progress.progress(100, text="Done!")

    # ── Efficient Frontier ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        frontier_chart(frontier, strategies),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Equity Curves ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        equity_curves_chart(strategies),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Drawdown ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        drawdown_chart(strategies),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Weights ──
    st.markdown("**⚖️ Weight Allocations**")
    col_l, col_r = st.columns(2)

    selected = col_l.selectbox(
        "View weights for",
        list(strategies.keys()),
        label_visibility="collapsed"
    )
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(
            weights_chart(strategies, selected),
            use_container_width=True, config={"displayModeBar":False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(
            weights_bar_chart(strategies),
            use_container_width=True, config={"displayModeBar":False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Correlation Matrix ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        correlation_chart(returns),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Individual Weights Table ──
    st.markdown("**📋 Full Weight Table**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    weight_df = pd.DataFrame(
        {name: (data['weights']*100).round(1)
         for name, data in strategies.items()}
    )
    weight_df.index.name = "Ticker"
    weight_df['Avg Weight %'] = weight_df.mean(axis=1).round(1)

    st.dataframe(
        weight_df.style
        .format("{:.1f}%")
        .background_gradient(cmap='Blues', axis=None),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Downloads ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.download_button(
            "⬇️  Download Weights CSV",
            weight_df.to_csv().encode(),
            file_name="portfolio_weights.csv",
            mime="text/csv"
        )
    with col_r:
        st.download_button(
            "⬇️  Download Metrics CSV",
            cmp_df.to_csv().encode(),
            file_name="portfolio_metrics.csv",
            mime="text/csv"
        )