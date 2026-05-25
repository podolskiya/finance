import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from app.style import metric_card
from arbitrage.cointegration import scan_pairs, get_close_prices, engle_granger_test, johansen_test
from arbitrage.ou_process import calc_hedge_ratio, calc_spread, fit_ou_parameters, zscore
from arbitrage.pairs_strategy import pairs_signals
from backtester.engine import Backtester

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    hovermode="x unified",
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)

PRESET_UNIVERSES = {
    "🖥️  Tech":        ["AAPL","MSFT","GOOGL","META","NVDA","AMD","INTC","ORCL"],
    "🏦  Financials":  ["JPM","BAC","GS","MS","WFC","C","BLK","AXP"],
    "🏥  Healthcare":  ["JNJ","PFE","ABBV","MRK","LLY","TMO","ABT","AMGN"],
    "⚡  Energy":      ["XOM","CVX","COP","SLB","EOG","MPC","VLO","PSX"],
    "🛍️  Consumer":    ["AMZN","WMT","COST","TGT","HD","MCD","NKE","SBUX"],
}

def spread_chart(signals_df: pd.DataFrame, t1: str, t2: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=signals_df.index, y=signals_df['Spread'],
        name='Spread', mode='lines',
        line=dict(color='#1A1A1A', width=1.8)
    ))
    mean = signals_df['Spread'].mean()
    std  = signals_df['Spread'].std()
    for mult, color, label in [(1,'#3B82F6','+1σ'),(-1,'#3B82F6','-1σ'),
                                (2,'#F59E0B','+2σ'),(-2,'#F59E0B','-2σ')]:
        fig.add_hline(y=mean + mult*std, line_dash='dash',
                      line_color=color, opacity=0.6,
                      annotation_text=label, annotation_position="right")
    fig.add_hline(y=mean, line_color='#10B981', line_dash='dot',
                  annotation_text="Mean", annotation_position="right")
    fig.update_layout(height=280, title=f"Spread: {t1} − β·{t2}", **CHART_THEME)
    return fig

def zscore_chart(signals_df: pd.DataFrame,
                 entry_z: float, exit_z: float) -> go.Figure:
    z = signals_df['Z_Score'].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=z.index, y=z,
        name='Z-Score', mode='lines',
        line=dict(color='#1A1A1A', width=2),
        fill='tozeroy', fillcolor='rgba(26,26,26,0.04)'
    ))
    for level, color, label in [
        ( entry_z, '#EF4444', f'+{entry_z}σ entry'),
        (-entry_z, '#10B981', f'-{entry_z}σ entry'),
        ( exit_z,  '#F59E0B', f'+{exit_z}σ exit'),
        (-exit_z,  '#F59E0B', f'-{exit_z}σ exit'),
        (0,        '#6B7280', 'Mean'),
    ]:
        fig.add_hline(y=level, line_dash='dash', line_color=color,
                      opacity=0.7, annotation_text=label,
                      annotation_position="right")

    # Colour signal regions
    long_mask  = signals_df['Signal'] ==  1
    short_mask = signals_df['Signal'] == -1
    fig.add_trace(go.Scatter(
        x=z[long_mask].index,  y=z[long_mask],
        mode='markers', name='Long Spread',
        marker=dict(color='#10B981', size=5, symbol='circle')
    ))
    fig.add_trace(go.Scatter(
        x=z[short_mask].index, y=z[short_mask],
        mode='markers', name='Short Spread',
        marker=dict(color='#EF4444', size=5, symbol='circle')
    ))
    fig.update_layout(height=280, title="Z-Score & Entry/Exit Signals", **CHART_THEME)
    return fig

def price_chart(signals_df: pd.DataFrame, t1: str, t2: str) -> go.Figure:
    fig = go.Figure()
    # Normalise both series to 100
    s1_norm = signals_df['S1'] / signals_df['S1'].iloc[0] * 100
    s2_norm = signals_df['S2'] / signals_df['S2'].iloc[0] * 100
    fig.add_trace(go.Scatter(
        x=s1_norm.index, y=s1_norm,
        name=t1, mode='lines',
        line=dict(color='#1A1A1A', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=s2_norm.index, y=s2_norm,
        name=t2, mode='lines',
        line=dict(color='#10B981', width=2)
    ))
    fig.update_layout(height=250, title="Normalised Price (base=100)",
                      legend=dict(orientation="h"),**CHART_THEME)
    return fig

def equity_chart(results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Equity_Curve'],
        name='Pairs Strategy', mode='lines',
        line=dict(color='#1A1A1A', width=2.5),
        fill='tozeroy', fillcolor='rgba(26,26,26,0.05)'
    ))
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Buy_Hold_Curve'],
        name='Buy & Hold', mode='lines',
        line=dict(color='#10B981', width=2, dash='dash')
    ))
    fig.update_layout(height=280, title="Strategy Equity Curve",
                      legend=dict(orientation="h"), **CHART_THEME)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig

def show():
    st.markdown("""
        <div class='page-title'>Pairs Trading</div>
        <div class='page-subtitle'>
            Cointegration-based statistical arbitrage with
            Ornstein-Uhlenbeck spread modelling
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**⚙️ Pairs Settings**")

        mode = st.radio("Mode", ["🔍  Scan for Pairs", "📐  Analyse a Pair"])

        st.markdown("**Universe**")
        preset = st.selectbox("Preset", list(PRESET_UNIVERSES.keys()))
        custom = st.text_input("Or custom tickers (comma-separated)", "")
        tickers = (
            [t.strip().upper() for t in custom.split(",") if t.strip()]
            if custom else PRESET_UNIVERSES[preset]
        )

        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", pd.to_datetime("2021-01-01"))
        with col2:
            end   = st.date_input("End",   pd.to_datetime("2024-01-01"))

        sig_level = st.slider("Significance", 0.01, 0.10, 0.05, 0.01)

        if "Analyse" in mode:
            st.markdown("**Pair Selection**")
            t1 = st.text_input("Ticker 1", "AAPL")
            t2 = st.text_input("Ticker 2", "MSFT")
            st.markdown("**Signal Parameters**")
            zw      = st.slider("Z-Score Window", 10, 60, 30)
            entry_z = st.slider("Entry Z", 1.0, 3.0, 2.0, 0.1)
            exit_z  = st.slider("Exit Z",  0.1, 1.5, 0.5, 0.1)
            capital = st.number_input("Capital ($)", value=100_000, step=10_000)

        run = st.button("▶  Run Analysis")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>🔗</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    Statistical Arbitrage Engine
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;'>
                    Scan a universe for cointegrated pairs or analyse
                    a specific pair with full OU modelling
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # ════════════════════════════════
    # MODE 1 — SCAN
    # ════════════════════════════════
    if "Scan" in mode:
        with st.spinner(f"Scanning {len(tickers)} tickers for cointegration..."):
            pairs_df = scan_pairs(tickers, str(start), str(end), sig_level)

        if pairs_df.empty:
            st.warning("No cointegrated pairs found. Try a lower significance level or different universe.")
            return

        st.markdown(f"""
            <div class='section-card'>
                <div style='font-size:1rem; font-weight:600;'>
                    ✅ Found {len(pairs_df)} cointegrated pair(s)
                </div>
                <div style='color:#6B7280; font-size:0.85rem; margin-top:0.3rem;'>
                    Ranked by p-value · significance level: {sig_level}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Style the table
        def highlight_pval(val):
            if isinstance(val, float):
                if val < 0.01: return 'background-color:#D1FAE5; color:#065F46'
                if val < 0.05: return 'background-color:#FEF3C7; color:#92400E'
            return ''

        styled = pairs_df.style.applymap(
            highlight_pval, subset=['P_Value']
        ).format({'P_Value': '{:.4f}', 'Score': '{:.4f}'})

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.dataframe(styled, use_container_width=True, height=350)
        st.markdown("</div>", unsafe_allow_html=True)

        # Show price chart for top 3 pairs
        st.markdown("**📈 Top Pairs — Normalised Price Comparison**")
        for _, row in pairs_df.head(3).iterrows():
            t1, t2 = row['Ticker_1'], row['Ticker_2']
            try:
                prices = get_close_prices([t1, t2], str(start), str(end))
                with st.expander(f"{t1} / {t2}  —  p-value: {row['P_Value']:.4f}"):
                    col_l, col_r = st.columns(2)
                    s1 = prices[t1]
                    s2 = prices[t2]
                    spread = calc_spread(s1, s2)
                    ou     = fit_ou_parameters(spread)
                    sig_df, _ = pairs_signals(s1, s2)

                    with col_l:
                        st.plotly_chart(price_chart(sig_df, t1, t2),
                                        use_container_width=True,
                                        config={"displayModeBar": False})
                    with col_r:
                        st.plotly_chart(spread_chart(sig_df, t1, t2),
                                        use_container_width=True,
                                        config={"displayModeBar": False})

                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.markdown(metric_card(
                        "Half-Life", f"{ou['half_life']} days"), unsafe_allow_html=True)
                    with c2: st.markdown(metric_card(
                        "Mean Rev. Speed", str(ou['theta'])), unsafe_allow_html=True)
                    with c3: st.markdown(metric_card(
                        "Spread Volatility", str(ou['sigma'])), unsafe_allow_html=True)
                    with c4: st.markdown(metric_card(
                        "Long-Run Mean", str(ou['mu'])), unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{t1}/{t2}: {e}")

        # Download
        st.download_button("⬇️  Download Pairs CSV",
                           pairs_df.to_csv(index=False).encode(),
                           file_name="cointegrated_pairs.csv", mime="text/csv")

    # ════════════════════════════════
    # MODE 2 — ANALYSE A PAIR
    # ════════════════════════════════
    else:
        t1 = t1.strip().upper()
        t2 = t2.strip().upper()

        with st.spinner(f"Analysing {t1} / {t2}..."):
            try:
                prices = get_close_prices([t1, t2], str(start), str(end))
                s1, s2 = prices[t1], prices[t2]

                # Cointegration tests
                eg  = engle_granger_test(s1, s2)
                joh = johansen_test(prices[[t1, t2]])

                # OU + signals
                hedge  = calc_hedge_ratio(s1, s2)
                spread = calc_spread(s1, s2, hedge)
                ou     = fit_ou_parameters(spread)
                sig_df, _ = pairs_signals(s1, s2, zw, entry_z, exit_z)

                # Backtest
                bt      = Backtester(s1.to_frame('Close'), capital)
                results = bt.run(sig_df['Signal'])
                metrics = bt.metrics()

            except Exception as e:
                st.error(f"Error: {e}")
                return

        # ── Cointegration Results ──
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("**🧪 Engle-Granger Test**")
            coint_color = "#D1FAE5" if eg['cointegrated'] else "#FEE2E2"
            coint_text  = "#065F46" if eg['cointegrated'] else "#991B1B"
            coint_label = "✅ Cointegrated" if eg['cointegrated'] else "❌ Not Cointegrated"
            st.markdown(f"""
                <div style='background:{coint_color}; color:{coint_text};
                            border-radius:10px; padding:0.6rem 1rem;
                            font-weight:600; margin-bottom:1rem;'>
                    {coint_label}
                </div>
                <div style='color:#6B7280; font-size:0.88rem;'>
                    P-Value: <b style='color:#1A1A1A'>{eg['p_value']}</b><br>
                    Test Score: <b style='color:#1A1A1A'>{eg['score']}</b>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_r:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("**🧪 Johansen Test**")
            joh_color = "#D1FAE5" if joh['cointegrated'] else "#FEE2E2"
            joh_text  = "#065F46" if joh['cointegrated'] else "#991B1B"
            joh_label = "✅ Cointegrated" if joh['cointegrated'] else "❌ Not Cointegrated"
            st.markdown(f"""
                <div style='background:{joh_color}; color:{joh_text};
                            border-radius:10px; padding:0.6rem 1rem;
                            font-weight:600; margin-bottom:1rem;'>
                    {joh_label} · {joh['n_relations']} relation(s)
                </div>
                <div style='color:#6B7280; font-size:0.88rem;'>
                    Trace Stat: <b style='color:#1A1A1A'>{joh['trace_stats'][0]}</b><br>
                    Critical Val (95%):
                    <b style='color:#1A1A1A'>{joh['critical_vals'][0]}</b>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── OU Parameters ──
        st.markdown("**⚙️ Ornstein-Uhlenbeck Parameters**")
        c1, c2, c3, c4 = st.columns(4)
        hl_ok = ou['half_life'] < 30
        with c1: st.markdown(metric_card(
            "Half-Life", f"{ou['half_life']} days",
            sub="✅ Tradeable" if hl_ok else "⚠️ Slow reversion",
            positive=hl_ok), unsafe_allow_html=True)
        with c2: st.markdown(metric_card(
            "Reversion Speed θ", str(ou['theta'])), unsafe_allow_html=True)
        with c3: st.markdown(metric_card(
            "Spread Volatility σ", str(ou['sigma'])), unsafe_allow_html=True)
        with c4: st.markdown(metric_card(
            "Hedge Ratio β", str(round(hedge, 4))), unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── Charts ──
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(price_chart(sig_df, t1, t2),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.plotly_chart(spread_chart(sig_df, t1, t2),
                            use_container_width=True, config={"displayModeBar":False})
            st.markdown("</div>", unsafe_allow_html=True)
        with col_r:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.plotly_chart(zscore_chart(sig_df, entry_z, exit_z),
                            use_container_width=True, config={"displayModeBar":False})
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Backtest Results ──
        st.markdown("**📊 Backtest Performance**")
        sharpe = float(metrics['Sharpe Ratio'])
        cols   = st.columns(6)
        data   = [
            ("Total Return",  metrics['Total Return'],  None),
            ("CAGR",          metrics['CAGR'],          float(metrics['CAGR'].strip('%')) > 0),
            ("Sharpe Ratio",  str(sharpe),              sharpe > 0),
            ("Max Drawdown",  metrics['Max Drawdown'],  False),
            ("Win Rate",      metrics['Win Rate'],      float(metrics['Win Rate'].strip('%')) > 50),
            ("Final Equity",  metrics['Final Equity'],  None),
        ]
        for col, (label, val, pos) in zip(cols, data):
            with col:
                st.markdown(metric_card(label, val, positive=pos),
                            unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(equity_chart(results),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Download ──
        st.download_button(
            "⬇️  Download Signals CSV",
            sig_df.to_csv().encode(),
            file_name=f"pairs_{t1}_{t2}_signals.csv",
            mime="text/csv"
        )