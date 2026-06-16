# app/pages/overview.py
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from app.style import metric_card

def get_market_data(indices: dict):
    """Fetch live market indices."""
    results = {}
    for name, ticker in indices.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                curr  = hist['Close'].iloc[-1]
                prev  = hist['Close'].iloc[-2]
                chg   = (curr - prev) / prev * 100
                results[name] = {"price": curr, "change": chg, "ticker": ticker}
        except:
            pass
    return results

def sparkline(ticker: str, period: str = "1mo") -> go.Figure:
    """Mini sparkline chart for a ticker."""
    hist = yf.Ticker(ticker).history(period=period)
    colour = "#10B981" if hist['Close'].iloc[-1] >= hist['Close'].iloc[0] else "#EF4444"
    fig = go.Figure(go.Scatter(
        x=hist.index, y=hist['Close'],
        mode='lines',
        line=dict(color=colour, width=2),
        fill='tozeroy',
        fillcolor=colour.replace("1)", "0.08)").replace("#10B981", "rgba(16,185,129,0.08)").replace("#EF4444","rgba(239,68,68,0.08)")
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=60, paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False
    )
    return fig

def market_chart(tickers: dict, period: str = "6mo") -> go.Figure:
    """Normalised performance chart for multiple tickers."""
    fig = go.Figure()
    colours = ["#1A1A1A","#10B981","#3B82F6","#F59E0B"]
    for (name, ticker), colour in zip(tickers.items(), colours):
        hist = yf.Ticker(ticker).history(period=period)['Close']
        norm = hist / hist.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm.values,
            name=name, mode='lines',
            line=dict(color=colour, width=2)
        ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, color='#6B7280'),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280',
                   ticksuffix=""),
        hovermode="x unified"
    )
    return fig

def show():
    now = datetime.now().strftime("%A, %d %B %Y")
    st.markdown(f"<div class='page-subtitle' style='color: #6B7280; font-size: 0.95rem; margin-top: -1rem; margin-bottom: 2rem;'>{now} · Live market data</div>", unsafe_allow_html=True)

    # 2. Section Header
    st.markdown("<h2 style='margin-bottom: 1rem;'>Market Overview</h2>", unsafe_allow_html=True)
    # ── Header ──    
    AVAILABLE_MARKETS = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW": "^DJI",
        "VIX": "^VIX",
        "Russell 2000": "^RUT",
        "Crude Oil": "CL=F",
        "Gold": "GC=F",
        "Bitcoin": "BTC-USD"
    }

    default_markets = ["S&P 500", "NASDAQ", "DOW", "VIX"]

    selected_markets = st.multiselect(
        label="Markets",
        options=list(AVAILABLE_MARKETS.keys()),
        default=default_markets,
        max_selections=4,
        label_visibility="collapsed"
    )

    # Fallback to default if the user clears all selections
    if not selected_markets:
        selected_markets = default_markets
        
    # Build a dictionary of just the selected markets to pass to our data fetcher
    selected_dict = {market: AVAILABLE_MARKETS[market] for market in selected_markets}

    # ── Market Indices Cards ──
    with st.spinner("Fetching live market data..."):
        market = get_market_data(selected_dict)

    # Create exactly the number of columns needed (1 to 4)
    cols = st.columns(len(selected_markets))

    for col, (name, data) in zip(cols, market.items()):
        chg   = data['change']
        pos   = chg >= 0
        arrow = "▲" if pos else "▼"
        with col:
            st.markdown("<div class='market-card-trigger'></div>", unsafe_allow_html=True)
            
            st.markdown(metric_card(
                label    = name,
                value    = f"{data['price']:,.2f}",
                sub      = f"{arrow} {abs(chg):.2f}% today",
                positive = pos
            ), unsafe_allow_html=True)
            
            st.plotly_chart(sparkline(data['ticker']), use_container_width=True,
                            config={"displayModeBar": False})

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Performance Chart + Watchlist ──
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        period = st.select_slider(
            "Period",
            options=["1mo","3mo","6mo","1y"],
            value="6mo", label_visibility="collapsed"
        )
        st.markdown("**Normalised Performance** (base = 100)")
        watch = {"S&P 500":"^GSPC","NASDAQ":"^IXIC","AAPL":"AAPL","MSFT":"MSFT"}
        fig = market_chart(watch, period=period)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**📋 Quick Watchlist**")
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        watchlist = ["AAPL","MSFT","GOOGL","NVDA","TSLA","AMZN","META"]
        for t in watchlist:
            try:
                info  = yf.Ticker(t).fast_info
                price = info.last_price
                prev  = info.previous_close
                chg   = (price - prev) / prev * 100
                arrow = "▲" if chg >= 0 else "▼"
                color = "#10B981" if chg >= 0 else "#EF4444"
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between;
                                align-items:center; padding:0.5rem 0;
                                border-bottom:1px solid #F5F5F5;'>
                        <span style='font-weight:600; font-size:0.9rem;'>{t}</span>
                        <span style='font-size:0.9rem;'>${price:,.2f}</span>
                        <span style='color:{color}; font-size:0.82rem;
                                     font-weight:500;'>{arrow}{abs(chg):.2f}%</span>
                    </div>
                """, unsafe_allow_html=True)
            except:
                pass
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Sector Heatmap ──
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("**📊 Sector Performance (1 Month)**")

    sector_etfs = {
        "Technology":"XLK","Healthcare":"XLV","Financials":"XLF",
        "Energy":"XLE","Consumer Disc.":"XLY","Industrials":"XLI",
        "Utilities":"XLU","Materials":"XLB","Real Estate":"XLRE"
    }
    perf = {}
    for name, etf in sector_etfs.items():
        try:
            hist = yf.Ticker(etf).history(period="1mo")['Close']
            perf[name] = round((hist.iloc[-1]/hist.iloc[0]-1)*100, 2)
        except:
            perf[name] = 0

    perf_df = pd.DataFrame(list(perf.items()), columns=["Sector","Return (%)"])
    perf_df = perf_df.sort_values("Return (%)", ascending=True)

    fig2 = go.Figure(go.Bar(
        x=perf_df["Return (%)"],
        y=perf_df["Sector"],
        orientation='h',
        marker_color=["#10B981" if v >= 0 else "#EF4444"
                      for v in perf_df["Return (%)"]],
        text=[f"{v:+.2f}%" for v in perf_df["Return (%)"]],
        textposition='outside'
    ))
    fig2.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=60, t=0, b=0), height=280,
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False, color='#1A1A1A', tickfont=dict(size=12))
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)