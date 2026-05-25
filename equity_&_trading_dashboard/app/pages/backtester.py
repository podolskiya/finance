import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.style import metric_card
from data.fetcher import fetch_price_data
from backtester.engine import Backtester
from strategies.momentum import momentum_strategy
from strategies.mean_reversion import mean_reversion_strategy

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    hovermode="x unified",
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)

def equity_curve_chart(results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Equity_Curve'],
        name='Strategy', mode='lines',
        line=dict(color='#1A1A1A', width=2.5),
        fill='tozeroy',
        fillcolor='rgba(26,26,26,0.05)'
    ))
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Buy_Hold_Curve'],
        name='Buy & Hold', mode='lines',
        line=dict(color='#10B981', width=2, dash='dash')
    ))
    fig.update_layout(height=320, **CHART_THEME)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig

def drawdown_chart(results: pd.DataFrame) -> go.Figure:
    equity      = results['Equity_Curve']
    rolling_max = equity.cummax()
    drawdown    = (equity - rolling_max) / rolling_max * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=drawdown,
        name='Drawdown', mode='lines',
        line=dict(color='#EF4444', width=1.5),
        fill='tozeroy', fillcolor='rgba(239,68,68,0.1)'
    ))
    fig.update_layout(height=200, **CHART_THEME)
    fig.update_yaxes(ticksuffix="%")
    return fig

def returns_dist_chart(results: pd.DataFrame) -> go.Figure:
    r = results['Strategy_Return'].dropna() * 100
    m = results['Market_Return'].dropna() * 100
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=m, name='Buy & Hold', nbinsx=60,
        marker_color='#10B981', opacity=0.5
    ))
    fig.add_trace(go.Histogram(
        x=r, name='Strategy', nbinsx=60,
        marker_color='#1A1A1A', opacity=0.6
    ))
    fig.add_vline(x=0, line_color='#6B7280', line_dash='dash')
    fig.update_layout(
        height=250, barmode='overlay',
        **{**CHART_THEME, 'hovermode': 'x'}
    )
    fig.update_xaxes(ticksuffix="%")
    return fig

def signals_chart(results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Close'],
        name='Price', mode='lines',
        line=dict(color='#6B7280', width=1.5)
    ))
    longs  = results[results['Signal'] ==  1]
    shorts = results[results['Signal'] == -1]
    fig.add_trace(go.Scatter(
        x=longs.index, y=longs['Close'],
        name='Long', mode='markers',
        marker=dict(symbol='triangle-up', color='#10B981', size=8)
    ))
    fig.add_trace(go.Scatter(
        x=shorts.index, y=shorts['Close'],
        name='Short', mode='markers',
        marker=dict(symbol='triangle-down', color='#EF4444', size=8)
    ))
    fig.update_layout(height=280, **CHART_THEME)
    fig.update_yaxes(tickprefix="$")
    return fig

def show():
    st.markdown("""
        <div class='page-title'>Strategy Backtester</div>
        <div class='page-subtitle'>
            Test momentum and mean-reversion strategies on historical data
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar Controls ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**⚙️ Backtest Settings**")

        ticker = st.text_input("Ticker", value="AAPL").upper().strip()

        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", value=pd.to_datetime("2020-01-01"))
        with col2:
            end   = st.date_input("End",   value=pd.to_datetime("2024-01-01"))

        strategy = st.selectbox(
            "Strategy",
            ["Momentum", "Mean Reversion", "Combined"]
        )

        capital  = st.number_input("Capital ($)", value=100_000, step=10_000)
        commission = st.slider("Commission (%)", 0.0, 0.5, 0.1, 0.01) / 100
        slippage   = st.slider("Slippage (%)",   0.0, 0.5, 0.05, 0.01) / 100

        if strategy in ["Momentum", "Combined"]:
            st.markdown("**Momentum Params**")
            short_w = st.slider("Short MA", 5,  50,  20)
            long_w  = st.slider("Long MA",  20, 200, 60)
        else:
            short_w, long_w = 20, 60

        if strategy in ["Mean Reversion", "Combined"]:
            st.markdown("**Mean Reversion Params**")
            bb_window = st.slider("BB Window", 5, 50, 20)
            bb_std    = st.slider("BB Std Dev", 1.0, 3.0, 2.0, 0.1)
        else:
            bb_window, bb_std = 20, 2.0

        run = st.button("▶  Run Backtest")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>⚡</div>
                <div style='font-size:1.1rem; font-weight:600;
                            margin-top:1rem;'>Configure & Run a Backtest</div>
                <div style='color:#6B7280; margin-top:0.5rem;'>
                    Set your parameters in the sidebar and click Run Backtest
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    with st.spinner(f"Running {strategy} backtest on {ticker}..."):
        try:
            df = fetch_price_data(ticker, str(start), str(end))

            if strategy == "Momentum":
                signals = momentum_strategy(df, short_w, long_w)
            elif strategy == "Mean Reversion":
                signals = mean_reversion_strategy(df, bb_window, bb_std)
            else:
                s1 = momentum_strategy(df, short_w, long_w)
                s2 = mean_reversion_strategy(df, bb_window, bb_std)
                raw = (s1 + s2) / 2
                signals = raw.apply(lambda x: 1 if x > 0.4 else (-1 if x < -0.4 else 0))

            bt      = Backtester(df, capital, commission, slippage)
            results = bt.run(signals)
            metrics = bt.metrics()

        except Exception as e:
            st.error(f"Error: {e}")
            return

    sharpe = float(metrics['Sharpe Ratio'])
    mdd    = metrics['Max Drawdown']
    cagr   = metrics['CAGR']
    wr     = metrics['Win Rate']
    equity = metrics['Final Equity']
    ret    = metrics['Total Return']

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    cards = [
        (col1, "Total Return",   ret,    None),
        (col2, "CAGR",          cagr,   float(cagr.strip('%')) > 0),
        (col3, "Sharpe Ratio",  str(sharpe), sharpe > 0),
        (col4, "Max Drawdown",  mdd,    False),
        (col5, "Win Rate",      wr,     float(wr.strip('%')) > 50),
        (col6, "Final Equity",  equity, None),
    ]
    for col, label, value, pos in cards:
        with col:
            st.markdown(metric_card(label, value, positive=pos),
                        unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("**📈 Equity Curve vs Buy & Hold**")
    st.plotly_chart(equity_curve_chart(results),
                    use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**📉 Drawdown**")
        st.plotly_chart(drawdown_chart(results),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**📊 Returns Distribution**")
        st.plotly_chart(returns_dist_chart(results),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("**🎯 Price & Signals**")
    st.plotly_chart(signals_chart(results),
                    use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    csv = results.to_csv().encode()
    st.download_button(
        label="⬇️  Download Results CSV",
        data=csv,
        file_name=f"{ticker}_{strategy}_backtest.csv",
        mime="text/csv"
    )