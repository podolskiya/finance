import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf
import time
import os
from app.style import metric_card
from trading.alpaca_client import (
    get_trading_client, get_data_client,
    get_account, get_positions, get_orders,
    place_market_order, place_limit_order,
    close_position, close_all_positions,
    cancel_order, execute_signal,
    get_portfolio_history
)
from data.fetcher import fetch_price_data
from strategies.momentum import momentum_strategy
from strategies.mean_reversion import mean_reversion_strategy

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    hovermode="x unified",
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)


def portfolio_equity_chart(history: pd.DataFrame) -> go.Figure:
    if history.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history.index, y=history['equity'],
        name='Portfolio Value', mode='lines',
        line=dict(color='#1A1A1A', width=2.5),
        fill='tozeroy', fillcolor='rgba(26,26,26,0.05)'
    ))
    fig.update_layout(
        height=280,
        title="Portfolio Equity History",
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def pnl_chart(history: pd.DataFrame) -> go.Figure:
    if history.empty:
        return None
    colors = ['#10B981' if v >= 0 else '#EF4444'
              for v in history['pnl']]
    fig = go.Figure(go.Bar(
        x=history.index, y=history['pnl'],
        marker_color=colors, name='Daily P&L'
    ))
    fig.add_hline(y=0, line_color='#6B7280',
                  line_dash='dot', line_width=1)
    fig.update_layout(
        height=200,
        title="Daily P&L",
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$")
    return fig


def positions_chart(positions: pd.DataFrame) -> go.Figure:
    if positions.empty:
        return None
    pnl    = positions['Unrealised P&L']
    colors = ['#10B981' if v >= 0 else '#EF4444' for v in pnl]
    fig    = go.Figure(go.Bar(
        x=positions.index, y=pnl,
        marker_color=colors,
        text=[f"${v:,.2f}" for v in pnl],
        textposition='outside',
        name='Unrealised P&L'
    ))
    fig.add_hline(y=0, line_color='#6B7280', line_dash='dot')
    fig.update_layout(
        height=240,
        title="Unrealised P&L by Position",
        showlegend=False,
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$")
    return fig


def live_price(ticker: str) -> float | None:
    """Get latest price from yfinance."""
    try:
        return yf.Ticker(ticker).fast_info.last_price
    except:
        return None


def get_latest_signal(ticker: str,
                       strategy: str,
                       lookback: int = 100) -> int:
    """Get the most recent signal from a strategy."""
    try:
        end   = pd.Timestamp.now()
        start = end - pd.Timedelta(days=lookback)
        df    = fetch_price_data(ticker,
                                  str(start.date()),
                                  str(end.date()))
        if strategy == "Momentum":
            signals = momentum_strategy(df)
        else:
            signals = mean_reversion_strategy(df)

        return int(signals.iloc[-1])
    except:
        return 0


def show():
    st.markdown("""
        <div class='page-subtitle'>
            Alpaca Paper Trading · Live signals ·
            Real-time P&L · Order management
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📡 Alpaca Connection**")

        api_key = st.text_input(
            "API Key", type="password",
            value=os.environ.get("ALPACA_API_KEY", "")
        )
        secret_key = st.text_input(
            "Secret Key", type="password",
            value=os.environ.get("ALPACA_SECRET_KEY", "")
        )

        if api_key:
            os.environ["ALPACA_API_KEY"]    = api_key
        if secret_key:
            os.environ["ALPACA_SECRET_KEY"] = secret_key

        connect = st.button("🔌  Connect")

        st.markdown("---")
        st.markdown("**⚙️ Trading Settings**")

        ticker   = st.text_input("Ticker", "AAPL").upper().strip()
        strategy = st.selectbox(
            "Signal Strategy",
            ["Momentum", "Mean Reversion"]
        )
        order_type = st.selectbox(
            "Order Type", ["Market", "Limit"]
        )
        pct_size = st.slider(
            "Position Size (%)",
            1, 30, 10,
            help="% of portfolio per position"
        ) / 100

        manual_qty = st.number_input(
            "Manual Order Qty", min_value=1,
            max_value=10000, value=1, step=1
        )
        if order_type == "Limit":
            limit_offset = st.slider(
                "Limit Offset (%)", -2.0, 2.0, -0.1, 0.05,
                help="% below/above current price"
            ) / 100

        history_period = st.selectbox(
            "History Period",
            ["1W","1M","3M","6M","1A"],
            index=1
        )

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888;
                        line-height:1.7;'>
                🔒 <b>Paper Trading Only</b><br>
                This uses Alpaca's paper trading
                environment — no real money at risk.
                Get your free API keys at
                alpaca.markets
            </div>
        """, unsafe_allow_html=True)

        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)

    # ── Connection ──
    if not (api_key and secret_key):
        st.markdown("""
            <div class='section-card'
                 style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>📡</div>
                <div style='font-size:1.1rem; font-weight:600;
                            margin-top:1rem;'>
                    Live Paper Trading Terminal
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;
                            max-width:480px;
                            margin-left:auto; margin-right:auto;'>
                    Connect your Alpaca paper trading account to
                    execute live signals, monitor positions, and
                    track real-time P&L — with zero real money at risk.
                    <br><br>
                    Get free API keys at
                    <a href='https://alpaca.markets'
                       target='_blank'>alpaca.markets</a>
                    then enter them in the sidebar.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # Connect
    try:
        client = get_trading_client(api_key, secret_key)
        acc    = get_account(client)
        if "error" in acc:
            st.error(f"Connection failed: {acc['error']}")
            return
    except Exception as e:
        st.error(f"Failed to connect: {e}")
        return

    # ── Account Summary Cards ──
    pnl_pos = acc['pnl'] >= 0
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(metric_card(
        "Portfolio Value",
        f"${acc['portfolio_value']:,.2f}"
    ), unsafe_allow_html=True)
    with c2: st.markdown(metric_card(
        "Cash Available",
        f"${acc['cash']:,.2f}"
    ), unsafe_allow_html=True)
    with c3: st.markdown(metric_card(
        "Buying Power",
        f"${acc['buying_power']:,.2f}"
    ), unsafe_allow_html=True)
    with c4: st.markdown(metric_card(
        "Today's P&L",
        f"${acc['pnl']:+,.2f}",
        sub=f"{acc['pnl_pct']:+.2f}%",
        positive=pnl_pos
    ), unsafe_allow_html=True)
    with c5: st.markdown(metric_card(
        "Account Status",
        acc['status'].value
        if hasattr(acc['status'], 'value')
        else str(acc['status'])
    ), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Portfolio History ──
    history = get_portfolio_history(client, history_period)
    if not history.empty:
        col_l, col_r = st.columns([2, 1])
        with col_l:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            fig = portfolio_equity_chart(history)
            if fig:
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar":False})
            st.markdown("</div>", unsafe_allow_html=True)
        with col_r:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            fig2 = pnl_chart(history)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True,
                                config={"displayModeBar":False})
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Signal Panel ──
    st.markdown("**⚡ Live Signal Panel**")
    price = live_price(ticker)

    if price:
        signal = get_latest_signal(ticker, strategy)
        sig_label = {1: "LONG 🟢", -1: "SHORT 🔴", 0: "FLAT ⚪"}
        sig_color = {1: "#10B981", -1: "#EF4444",  0: "#6B7280"}

        st.markdown(f"""
            <div class='section-card'
                 style='display:flex; justify-content:space-between;
                         align-items:center; flex-wrap:wrap; gap:1rem;'>
                <div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                text-transform:uppercase;
                                letter-spacing:0.05em;'>
                        {strategy} Signal for {ticker}
                    </div>
                    <div style='font-size:2rem; font-weight:800;
                                color:{sig_color[signal]};
                                margin-top:0.3rem;'>
                        {sig_label[signal]}
                    </div>
                    <div style='color:#6B7280; font-size:0.85rem;
                                margin-top:0.2rem;'>
                        Current Price: <b>${price:,.2f}</b>
                    </div>
                </div>
                <div style='display:flex; gap:0.8rem; flex-wrap:wrap;'>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ── Order Buttons ──
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            if st.button("🟢  Buy Market", use_container_width=True):
                res = place_market_order(
                    client, ticker, manual_qty, "buy"
                )
                if res.get("success"):
                    st.success(f"✅ Buy order placed: "
                               f"{manual_qty} × {ticker}")
                else:
                    st.error(f"❌ {res.get('error')}")

        with col2:
            if st.button("🔴  Sell Market", use_container_width=True):
                res = place_market_order(
                    client, ticker, manual_qty, "sell"
                )
                if res.get("success"):
                    st.success(f"✅ Sell order placed: "
                               f"{manual_qty} × {ticker}")
                else:
                    st.error(f"❌ {res.get('error')}")

        with col3:
            if st.button("🤖  Execute Signal",
                         use_container_width=True,
                         help="Auto-execute based on strategy signal"):
                res = execute_signal(
                    client, ticker, signal,
                    acc['portfolio_value'], price, pct_size
                )
                if res.get("success"):
                    st.success(f"✅ Signal executed: "
                               f"{sig_label[signal]} {ticker}")
                else:
                    st.error(f"❌ {res.get('error', 'No action needed')}")

        with col4:
            if st.button("⬜  Close Position",
                         use_container_width=True):
                res = close_position(client, ticker)
                if res.get("success"):
                    st.success(f"✅ {ticker} position closed")
                else:
                    st.error(f"❌ {res.get('error')}")

        with col5:
            if st.button("🚨  Close All",
                         use_container_width=True,
                         help="Close all open positions"):
                if st.session_state.get("confirm_close_all"):
                    res = close_all_positions(client)
                    if res.get("success"):
                        st.success("✅ All positions closed")
                    else:
                        st.error(f"❌ {res.get('error')}")
                    st.session_state["confirm_close_all"] = False
                else:
                    st.session_state["confirm_close_all"] = True
                    st.warning("⚠️ Click again to confirm close all")

    # ── Positions ──
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("**📋 Open Positions**")
    positions = get_positions(client)

    if positions.empty:
        st.markdown("""
            <div class='section-card'
                 style='text-align:center; padding:2rem;
                         color:#6B7280;'>
                No open positions
            </div>
        """, unsafe_allow_html=True)
    else:
        col_l, col_r = st.columns([1.5, 1])
        with col_l:
            st.markdown("<div class='section-card'>",
                        unsafe_allow_html=True)

            def style_pnl(val):
                try:
                    v = float(str(val).replace('$','').replace(',',''))
                    return ('color:#10B981; font-weight:600' if v > 0
                            else 'color:#EF4444; font-weight:600')
                except:
                    return ''

            st.dataframe(
                positions.style
                .applymap(style_pnl,
                          subset=['Unrealised P&L', 'Today P&L'])
                .format({
                    'Avg Entry':      '${:.2f}',
                    'Current':        '${:.2f}',
                    'Market Val':     '${:,.2f}',
                    'Unrealised P&L': '${:,.2f}',
                    'Unrealised %':   '{:+.2f}%',
                    'Today P&L':      '${:,.2f}',
                }),
                use_container_width=True
            )

            # Close individual positions
            pos_to_close = st.selectbox(
                "Close specific position",
                ["—"] + list(positions.index)
            )
            if pos_to_close != "—":
                if st.button(f"Close {pos_to_close}",
                             use_container_width=True):
                    res = close_position(client, pos_to_close)
                    st.success(f"✅ Closed {pos_to_close}") \
                        if res.get("success") \
                        else st.error(f"❌ {res.get('error')}")

            st.markdown("</div>", unsafe_allow_html=True)

        with col_r:
            st.markdown("<div class='section-card'>",
                        unsafe_allow_html=True)
            fig = positions_chart(positions)
            if fig:
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar":False})
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Order Blotter ──
    st.markdown("**📜 Order Blotter**")
    order_filter = st.radio(
        "Filter", ["all","open","closed"],
        horizontal=True, label_visibility="collapsed"
    )
    orders = get_orders(client, status=order_filter, limit=50)

    st.markdown("<div class='section-card'>",
                unsafe_allow_html=True)
    if orders.empty or "Error" in orders.columns:
        st.info("No orders found.")
    else:
        def style_side(val):
            return ('color:#10B981; font-weight:600'
                    if val == 'BUY'
                    else 'color:#EF4444; font-weight:600')

        def style_status(val):
            colors = {
                'filled':   'color:#10B981',
                'canceled': 'color:#6B7280',
                'pending':  'color:#F59E0B',
                'new':      'color:#3B82F6',
            }
            return colors.get(val.lower(), '')

        st.dataframe(
            orders.style
            .applymap(style_side,   subset=['Side'])
            .applymap(style_status, subset=['Status'])
            .format({'Fill Px': '${:.2f}', 'Qty': '{:.0f}',
                     'Filled': '{:.0f}'}),
            use_container_width=True,
            height=300
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Multi-Ticker Watchlist ──
    st.markdown("**👁️ Signal Watchlist**")
    watchlist_input = st.text_input(
        "Tickers to watch (comma-separated)",
        "AAPL, MSFT, NVDA, TSLA, SPY",
        label_visibility="collapsed"
    )
    watch_tickers = [t.strip().upper()
                     for t in watchlist_input.split(",")
                     if t.strip()]

    st.markdown("<div class='section-card'>",
                unsafe_allow_html=True)
    cols = st.columns(len(watch_tickers))

    for col, t in zip(cols, watch_tickers):
        px    = live_price(t)
        sig   = get_latest_signal(t, strategy) if px else 0
        slbl  = {1:"LONG", -1:"SHORT", 0:"FLAT"}
        sclr  = {1:"#10B981", -1:"#EF4444", 0:"#6B7280"}

        try:
            info  = yf.Ticker(t).fast_info
            chg   = (info.last_price - info.previous_close
                     ) / info.previous_close * 100
            arrow = "▲" if chg >= 0 else "▼"
            pclr  = "#10B981" if chg >= 0 else "#EF4444"
        except:
            chg, arrow, pclr = 0, "–", "#6B7280"

        with col:
            st.markdown(f"""
                <div style='text-align:center; padding:0.8rem;
                             border-radius:12px;
                             border:1px solid #F0F0F0;
                             background:#FAFAFA;'>
                    <div style='font-weight:700;
                                font-size:1rem;'>{t}</div>
                    <div style='font-size:1.1rem; font-weight:600;
                                margin:0.2rem 0;'>
                        ${px:,.2f if px else 'N/A'}
                    </div>
                    <div style='font-size:0.78rem; color:{pclr};'>
                        {arrow} {abs(chg):.2f}%
                    </div>
                    <div style='font-size:0.78rem; font-weight:700;
                                color:{sclr[sig]};
                                margin-top:0.4rem;'>
                        {slbl[sig]}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Auto Refresh ──
    if auto_refresh:
        st.markdown("""
            <div style='text-align:center; color:#6B7280;
                        font-size:0.8rem; margin-top:1rem;'>
                Auto-refreshing every 30 seconds...
            </div>
        """, unsafe_allow_html=True)
        time.sleep(30)
        st.rerun()