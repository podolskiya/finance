# app/pages/regime.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.style import metric_card
from data.fetcher import fetch_price_data
from ml.regime import (build_regime_features, fit_hmm,
                        regime_series, regime_statistics,
                        regime_signals, predict_current_regime,
                        REGIME_META)
from backtester.engine import Backtester
from strategies.momentum import momentum_strategy

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    hovermode="x unified",
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)


def regime_price_chart(prices: pd.DataFrame,
                        regimes: pd.Series,
                        ticker: str) -> go.Figure:
    """Price chart with regime background shading."""
    close = prices['Close'].squeeze()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    fig = go.Figure()

    # Shade regime backgrounds
    prev_regime = None
    start_date  = None

    for date, regime in regimes.items():
        if regime != prev_regime:
            if prev_regime is not None:
                meta = REGIME_META.get(prev_regime, {})
                fig.add_vrect(
                    x0=start_date, x1=date,
                    fillcolor=meta.get('color', '#888'),
                    opacity=0.12, line_width=0
                )
            start_date  = date
            prev_regime = regime

    # Final region
    if prev_regime is not None and start_date is not None:
        meta = REGIME_META.get(prev_regime, {})
        fig.add_vrect(
            x0=start_date, x1=regimes.index[-1],
            fillcolor=meta.get('color', '#888'),
            opacity=0.12, line_width=0
        )

    # Price line
    fig.add_trace(go.Scatter(
        x=close.index, y=close,
        name=ticker, mode='lines',
        line=dict(color='#1A1A1A', width=2)
    ))

    # Invisible traces for legend
    for r, meta in REGIME_META.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            name=meta['label'],
            mode='markers',
            marker=dict(color=meta['color'], size=10, symbol='square'),
        ))

    fig.update_layout(
        height=340,
        title=f"{ticker} Price — Regime Overlay",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$")
    return fig


def regime_timeline_chart(regimes: pd.Series) -> go.Figure:
    """Coloured regime state over time."""
    fig = go.Figure()
    for r, meta in REGIME_META.items():
        mask = regimes == r
        fig.add_trace(go.Scatter(
            x=regimes.index[mask],
            y=[meta['label']] * mask.sum(),
            mode='markers',
            name=meta['label'],
            marker=dict(color=meta['color'], size=4, symbol='square'),
        ))
    fig.update_layout(
        height=160,
        title="Regime Timeline",
        showlegend=False,
        **CHART_THEME
    )
    return fig


def transition_matrix_chart(trans: np.ndarray) -> go.Figure:
    labels = [REGIME_META[i]['label'] for i in range(len(trans))]
    fig    = go.Figure(go.Heatmap(
        z=np.round(trans * 100, 1),
        x=[f"→ {l}" for l in labels],
        y=[f"{l}" for l in labels],
        colorscale='Blues',
        text=np.round(trans * 100, 1),
        texttemplate='%{text}%',
        textfont=dict(size=13, color='white'),
        showscale=False
    ))
    fig.update_layout(
        height=260,
        title="Regime Transition Probabilities (%)",
        **{k: v for k, v in CHART_THEME.items()
           if k not in ['hovermode']}
    )
    return fig


def regime_returns_chart(stats: pd.DataFrame) -> go.Figure:
    colors = [REGIME_META[i]['color']
              for i, row in enumerate(stats.itertuples())]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=stats.index,
        y=stats['Ann. Return'],
        name='Ann. Return (%)',
        marker_color=[REGIME_META[i]['color']
                      for i in range(len(stats))],
        text=[f"{v:+.1f}%" for v in stats['Ann. Return']],
        textposition='outside'
    ))
    fig.update_layout(
        height=240,
        title="Annualised Return by Regime",
        showlegend=False,
        **CHART_THEME
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def regime_vol_chart(stats: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=stats.index,
        y=stats['Ann. Vol'],
        name='Volatility',
        marker_color=[REGIME_META[i]['color']
                      for i in range(len(stats))],
        text=[f"{v:.1f}%" for v in stats['Ann. Vol']],
        textposition='outside',
        opacity=0.8
    ))
    fig.update_layout(
        height=240,
        title="Annualised Volatility by Regime",
        showlegend=False,
        **CHART_THEME
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def equity_comparison_chart(results: dict) -> go.Figure:
    colors = {
        'Bull Only':   '#10B981',
        'Bear Short':  '#3B82F6',
        'Adaptive':    '#1A1A1A',
        'Momentum':    '#F59E0B',
        'Buy & Hold':  '#6B7280',
    }
    fig = go.Figure()
    for name, res in results.items():
        col = colors.get(name, '#888')
        lw  = 2.5 if name == 'Adaptive' else 1.8
        ls  = 'dash' if name == 'Buy & Hold' else 'solid'
        key = 'Buy_Hold_Curve' if name == 'Buy & Hold' else 'Equity_Curve'
        fig.add_trace(go.Scatter(
            x=res.index, y=res[key],
            name=name, mode='lines',
            line=dict(color=col, width=lw, dash=ls)
        ))
    fig.update_layout(
        height=320,
        title="Strategy Comparison by Regime",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def show():
    st.markdown("""
        <div class='page-subtitle'>
            Hidden Markov Model · Bull / Bear / Sideways detection ·
            Regime-adaptive strategy switching
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar Controls ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**🌡️ Regime Settings**")

        ticker = st.text_input("Ticker", "SPY").upper().strip()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", pd.to_datetime("2018-01-01"))
        with col2:
            end   = st.date_input("End",   pd.to_datetime("2024-01-01"))

        n_regimes  = st.slider("Number of Regimes", 2, 4, 3,
                               help="3 is standard: Bear/Sideways/Bull")
        n_iter     = st.slider("HMM Iterations", 50, 500, 200, 50)
        vol_window = st.slider("Volatility Window", 5, 40, 20)
        capital    = st.number_input("Capital ($)", value=100_000, step=10_000)

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888; line-height:1.7;'>
                <b>Hidden Markov Model</b> infers hidden
                market states from observable price behaviour.
                Unlike rule-based filters, it learns the
                statistical signature of each regime and
                adapts automatically to new data.
                <br><br>
                <b>Transition Matrix</b> shows the probability
                of moving from one regime to another —
                key for understanding regime persistence.
            </div>
        """, unsafe_allow_html=True)

        run = st.button("▶  Detect Regimes")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>🌡️</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    Market Regime Detection
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;
                            max-width:480px; margin-left:auto; margin-right:auto;'>
                    Uses a Hidden Markov Model to automatically identify
                    Bull, Bear, and Sideways regimes from price data —
                    then switches trading strategies to match each regime.
                    This is what quant funds use to avoid trading against
                    the prevailing market structure.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # ── Run ──
    progress = st.progress(0, text="Fetching price data...")
    df = fetch_price_data(ticker, str(start), str(end))

    progress.progress(20, text="Engineering features...")
    features = build_regime_features(df, vol_window)

    if len(features) < 60:
        st.error("Not enough data. Use a longer date range.")
        return

    progress.progress(40, text="Fitting Hidden Markov Model...")
    hmm_result = fit_hmm(features, n_regimes=min(n_regimes, 3), n_iter=n_iter)

    progress.progress(65, text="Classifying regimes...")
    regimes = regime_series(hmm_result, df.index)
    stats   = regime_statistics(df, regimes)
    current = predict_current_regime(hmm_result)

    progress.progress(75, text="Generating regime signals...")
    sig_bull    = regime_signals(regimes, 'bull_only')
    sig_bear    = regime_signals(regimes, 'bear_short')
    sig_adapt   = regime_signals(regimes, 'adaptive')
    sig_momentum= momentum_strategy(df)

    progress.progress(85, text="Backtesting strategies...")
    backtest_results = {}
    for name, sig in [
        ('Bull Only',  sig_bull),
        ('Bear Short', sig_bear),
        ('Adaptive',   sig_adapt),
        ('Momentum',   sig_momentum),
    ]:
        bt  = Backtester(df, capital)
        res = bt.run(sig)
        backtest_results[name] = res

    # Add buy & hold
    backtest_results['Buy & Hold'] = list(backtest_results.values())[0]
    progress.progress(100, text="Done!")

    # ── Current Regime Banner ──
    probs = current['probabilities']
    st.markdown(f"""
        <div class='section-card'
             style='background:{current["color"]}18;
                    border:2px solid {current["color"]}40;
                    border-radius:16px; padding:1.2rem 1.6rem;
                    margin-bottom:1.5rem;'>
            <div style='display:flex; justify-content:space-between;
                        align-items:center; flex-wrap:wrap; gap:1rem;'>
                <div>
                    <div style='font-size:0.75rem; color:{current["color"]};
                                text-transform:uppercase; letter-spacing:0.05em;
                                font-weight:600;'>
                        Current Market Regime
                    </div>
                    <div style='font-size:2rem; font-weight:800;
                                color:{current["color"]}; margin-top:0.2rem;'>
                        {current["emoji"]} {current["label"]}
                    </div>
                </div>
                <div style='display:flex; gap:1.5rem;'>
                    {" ".join([
                        f'''<div style="text-align:center;">
                            <div style="font-size:0.72rem; color:#6B7280;">
                                {REGIME_META[r]["emoji"]} {REGIME_META[r]["label"]}
                            </div>
                            <div style="font-weight:700;
                                        font-size:1.1rem;
                                        color:{REGIME_META[r]["color"]};">
                                {probs.get(r, 0)*100:.0f}%
                            </div>
                        </div>'''
                        for r in sorted(probs.keys())
                    ])}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Regime Stats Cards ──
    cols = st.columns(len(stats))
    for col, (regime_name, row) in zip(cols, stats.iterrows()):
        r_id  = [k for k,v in REGIME_META.items()
                 if v['label']==regime_name]
        color = REGIME_META[r_id[0]]['color'] if r_id else '#888'
        with col:
            st.markdown(f"""
                <div class='metric-card'
                     style='border-top:3px solid {color};'>
                    <div class='label'>{regime_name}</div>
                    <div class='value'
                         style='color:{color}; font-size:1.3rem;'>
                        {row["Ann. Return"]:+.1f}%
                    </div>
                    <div class='sub'>
                        {row["% of Time"]}% of time ·
                        {row["Days"]} days<br>
                        Vol: {row["Ann. Vol"]:.1f}% ·
                        Sharpe: {row["Sharpe"]:.2f}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Price + Regime Chart ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        regime_price_chart(df, regimes, ticker),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Timeline ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        regime_timeline_chart(regimes),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Stats Charts ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(
            regime_returns_chart(stats),
            use_container_width=True, config={"displayModeBar":False}
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(
            regime_vol_chart(stats),
            use_container_width=True, config={"displayModeBar":False}
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Transition Matrix ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        transition_matrix_chart(hmm_result['trans_matrix']),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("""
        <div style='font-size:0.8rem; color:#6B7280; margin-top:0.5rem;'>
            💡 High diagonal values = regimes are persistent (good for trading).
            High off-diagonal = regimes flip frequently (harder to trade).
        </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Strategy Backtest ──
    st.markdown("**📊 Regime-Adaptive Strategy Comparison**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(
        equity_comparison_chart(backtest_results),
        use_container_width=True, config={"displayModeBar":False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Metrics table
    rows = []
    for name, res in backtest_results.items():
        if name == 'Buy & Hold':
            continue
        bt  = Backtester(df, capital)
        bt.run(
            sig_bull if name=='Bull Only' else
            sig_bear if name=='Bear Short' else
            sig_adapt if name=='Adaptive' else
            sig_momentum
        )
        m = bt.metrics()
        rows.append({
            "Strategy":     name,
            "Total Return": m['Total Return'],
            "CAGR":         m['CAGR'],
            "Sharpe":       m['Sharpe Ratio'],
            "Max Drawdown": m['Max Drawdown'],
            "Win Rate":     m['Win Rate'],
        })

    cmp = pd.DataFrame(rows).set_index("Strategy")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)

    def color_sharpe(s):
        return [
            'color:#10B981; font-weight:700' if float(v) > 0
            else 'color:#EF4444; font-weight:700'
            for v in s
        ]

    st.dataframe(
        cmp.style.apply(color_sharpe, subset=['Sharpe']),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Stats Table ──
    st.markdown("**📋 Regime Statistics**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.dataframe(
        stats.style.format({
            'Ann. Return': '{:+.2f}%',
            'Ann. Vol':    '{:.2f}%',
            'Sharpe':      '{:.3f}',
            'Win Rate':    '{:.1f}%',
            '% of Time':   '{:.1f}%',
        }).background_gradient(subset=['Ann. Return'], cmap='RdYlGn'),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Downloads ──
    col_l, col_r = st.columns(2)
    with col_l:
        regime_df = pd.DataFrame({
            'Date':   regimes.index,
            'Regime': regimes.values,
            'Label':  [REGIME_META[r]['label'] for r in regimes.values]
        })
        st.download_button(
            "⬇️  Download Regime Labels CSV",
            regime_df.to_csv(index=False).encode(),
            file_name=f"{ticker}_regimes.csv",
            mime="text/csv"
        )
    with col_r:
        st.download_button(
            "⬇️  Download Regime Stats CSV",
            stats.to_csv().encode(),
            file_name=f"{ticker}_regime_stats.csv",
            mime="text/csv"
        )