# app/pages/sentiment.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.style import metric_card
from data.fetcher import fetch_price_data
from ml.sentiment import (analyse_news, daily_sentiment,
                           sentiment_signals, combined_signals)
from strategies.momentum import momentum_strategy
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


def sentiment_timeline_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Bars coloured by sentiment
    colors = [
        '#10B981' if v > 0.05 else
        '#EF4444' if v < -0.05 else
        '#6B7280'
        for v in daily['compound_mean']
    ]
    fig.add_trace(go.Bar(
        x=daily['date'], y=daily['compound_mean'],
        name='Daily Sentiment',
        marker_color=colors, opacity=0.7
    ))

    # Smoothed line
    fig.add_trace(go.Scatter(
        x=daily['date'], y=daily['compound_smooth'],
        name='3-Day EMA', mode='lines',
        line=dict(color='#1A1A1A', width=2.5)
    ))

    fig.add_hline(y=0, line_color='#6B7280',
                  line_dash='dot', line_width=1)
    fig.update_layout(
        height=280,
        title="Daily Sentiment Score (FinBERT)",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    return fig


def article_volume_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily['date'],
        y=daily['n_articles'],
        name='Articles',
        marker_color='#1A1A1A', opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['bullish'],
        name='Bullish', mode='lines+markers',
        line=dict(color='#10B981', width=2),
        marker=dict(size=5)
    ))
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['bearish'],
        name='Bearish', mode='lines+markers',
        line=dict(color='#EF4444', width=2),
        marker=dict(size=5)
    ))
    fig.update_layout(
        height=240,
        title="News Volume & Sentiment Breakdown",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    return fig


def sentiment_price_chart(daily: pd.DataFrame,
                           price: pd.DataFrame,
                           ticker: str) -> go.Figure:
    close = price['Close'].squeeze()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    fig = go.Figure()

    # Price
    fig.add_trace(go.Scatter(
        x=close.index, y=close,
        name='Price', mode='lines',
        line=dict(color='#1A1A1A', width=2),
        yaxis='y1'
    ))

    # Sentiment overlay
    fig.add_trace(go.Scatter(
        x=daily['date'], y=daily['compound_smooth'],
        name='Sentiment', mode='lines',
        line=dict(color='#3B82F6', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(59,130,246,0.08)',
        yaxis='y2'
    ))

    fig.update_layout(
        height=300,
        title=f"{ticker} Price vs Sentiment",
        yaxis=dict(title="Price ($)", showgrid=True,
                   gridcolor='#F0F0F0', color='#6B7280'),
        yaxis2=dict(title="Sentiment", overlaying='y',
                    side='right', color='#3B82F6',
                    range=[-1, 1], showgrid=False),
        legend=dict(orientation="h"),
        **{k: v for k, v in CHART_THEME.items() if k != 'yaxis'}
    )
    return fig


def equity_comparison_chart(results_dict: dict) -> go.Figure:
    colors = {
        'Sentiment Only': '#3B82F6',
        'Price Only':     '#F59E0B',
        'Combined':       '#1A1A1A',
        'Buy & Hold':     '#10B981',
    }
    fig = go.Figure()
    first = True
    for name, results in results_dict.items():
        if first and name == 'Buy & Hold':
            fig.add_trace(go.Scatter(
                x=results.index, y=results['Buy_Hold_Curve'],
                name='Buy & Hold', mode='lines',
                line=dict(color='#10B981', width=1.5, dash='dash')
            ))
            first = False
        if name != 'Buy & Hold':
            fig.add_trace(go.Scatter(
                x=results.index, y=results['Equity_Curve'],
                name=name, mode='lines',
                line=dict(color=colors.get(name, '#6B7280'), width=2)
            ))
    fig.update_layout(
        height=320,
        title="Strategy Comparison",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def label_color(label: str) -> tuple:
    return {
        'positive': ('#D1FAE5', '#065F46'),
        'negative': ('#FEE2E2', '#991B1B'),
        'neutral':  ('#F3F4F6', '#374151'),
    }.get(label, ('#F3F4F6', '#374151'))


def show():
    st.markdown("""
        <div class='page-title'>Sentiment Signal Engine</div>
        <div class='page-subtitle'>
            FinBERT NLP · Live financial news · 
            Sentiment-price signal blending
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📰 Sentiment Settings**")

        ticker = st.text_input("Ticker", "AAPL").upper().strip()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", pd.to_datetime("2023-01-01"))
        with col2:
            end   = st.date_input("End",   pd.to_datetime("2024-01-01"))

        max_articles = st.slider("Max Articles", 20, 200, 100, 10)

        st.markdown("**Signal Thresholds**")
        bull_thresh = st.slider(
            "Bullish Threshold", 0.05, 0.50, 0.15, 0.05,
            help="Compound score above this = Long signal"
        )
        bear_thresh = st.slider(
            "Bearish Threshold", -0.50, -0.05, -0.15, 0.05,
            help="Compound score below this = Short signal"
        )
        min_articles = st.slider(
            "Min Articles/Day", 1, 5, 1,
            help="Ignore days with fewer articles than this"
        )

        st.markdown("**Blending**")
        sent_weight = st.slider(
            "Sentiment Weight", 0.0, 1.0, 0.4, 0.1,
            help="0 = pure price signal, 1 = pure sentiment"
        )

        capital = st.number_input("Capital ($)", value=100_000, step=10_000)

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888; line-height:1.7;'>
                <b>FinBERT</b> is a BERT transformer
                fine-tuned on 10,000+ financial news
                articles. It classifies text as
                positive, negative, or neutral with
                institutional-grade accuracy.
            </div>
        """, unsafe_allow_html=True)

        run = st.button("▶  Run Sentiment Analysis")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>📰</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    FinBERT Sentiment Engine
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;
                            max-width:450px; margin-left:auto; margin-right:auto;'>
                    Fetches live financial news, runs each headline and
                    summary through FinBERT, aggregates daily sentiment
                    scores, and generates alpha signals. Blends with
                    price-based signals for best results.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # ── Step 1: Fetch & Score News ──
    progress = st.progress(0, text="Fetching financial news...")

    with st.spinner(""):
        scored = analyse_news(ticker, max_articles)

    if scored.empty:
        st.error(f"No news found for {ticker}. Try a more popular ticker.")
        return

    progress.progress(40, text="Aggregating daily sentiment...")
    daily = daily_sentiment(scored)

    if daily.empty:
        st.error("Could not aggregate daily sentiment.")
        return

    progress.progress(55, text="Fetching price data...")
    price_df = fetch_price_data(ticker, str(start), str(end))

    progress.progress(65, text="Generating signals...")
    sent_sig  = sentiment_signals(daily, price_df, bull_thresh,
                                  bear_thresh, min_articles)
    price_sig = momentum_strategy(price_df)
    combo_sig = combined_signals(sent_sig, price_sig, sent_weight)

    progress.progress(80, text="Backtesting strategies...")

    results_dict = {}
    metrics_dict = {}
    for name, sig in [("Sentiment Only", sent_sig),
                      ("Price Only",     price_sig),
                      ("Combined",       combo_sig)]:
        bt  = Backtester(price_df, capital)
        res = bt.run(sig)
        results_dict[name] = res
        metrics_dict[name] = bt.metrics()

    # Add buy & hold reference
    results_dict['Buy & Hold'] = list(results_dict.values())[0]

    progress.progress(100, text="Done!")

    # ── Sentiment Summary Cards ──
    avg_sent  = daily['compound_mean'].mean()
    pos_days  = (daily['compound_mean'] > bull_thresh).sum()
    neg_days  = (daily['compound_mean'] < bear_thresh).sum()
    total_arts = scored.shape[0]
    bull_arts  = (scored['label'] == 'positive').sum()
    bear_arts  = (scored['label'] == 'negative').sum()

    sent_label = (
        "Bullish 🟢" if avg_sent > 0.05 else
        "Bearish 🔴" if avg_sent < -0.05 else
        "Neutral ⚪"
    )

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(metric_card(
        "Overall Sentiment", sent_label,
        positive=avg_sent > 0.05 if avg_sent != 0 else None
    ), unsafe_allow_html=True)
    with c2: st.markdown(metric_card(
        "Avg Compound Score", f"{avg_sent:+.3f}",
        positive=avg_sent > 0
    ), unsafe_allow_html=True)
    with c3: st.markdown(metric_card(
        "Total Articles", str(total_arts)
    ), unsafe_allow_html=True)
    with c4: st.markdown(metric_card(
        "Bullish Articles", str(bull_arts),
        positive=True
    ), unsafe_allow_html=True)
    with c5: st.markdown(metric_card(
        "Bearish Articles", str(bear_arts),
        positive=False
    ), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Sentiment Charts ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(sentiment_timeline_chart(daily),
                    use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(article_volume_chart(daily),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(sentiment_price_chart(daily, price_df, ticker),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Strategy Comparison ──
    st.markdown("**📊 Strategy Comparison**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(equity_comparison_chart(results_dict),
                    use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Metrics comparison table
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("**Performance Summary**")
    rows = []
    for name, m in metrics_dict.items():
        rows.append({
            "Strategy":     name,
            "Total Return": m['Total Return'],
            "CAGR":         m['CAGR'],
            "Sharpe":       m['Sharpe Ratio'],
            "Max Drawdown": m['Max Drawdown'],
            "Win Rate":     m['Win Rate'],
            "Final Equity": m['Final Equity'],
        })
    cmp_df = pd.DataFrame(rows).set_index("Strategy")

    def highlight_best(col):
        styles = [''] * len(col)
        try:
            numeric = col.str.strip('%$').str.replace(',','').astype(float)
            best    = numeric.idxmax()
            styles[col.index.get_loc(best)] = (
                'background-color:#D1FAE5; color:#065F46; font-weight:600'
            )
        except:
            pass
        return styles

    st.dataframe(
        cmp_df.style.apply(highlight_best, subset=['Total Return','CAGR','Win Rate']),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── News Feed ──
    st.markdown("**📰 Scored News Feed**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)

    for _, row in scored.head(20).iterrows():
        bg, color = label_color(row['label'])
        compound  = row['compound']
        arrow     = "▲" if compound > 0 else "▼" if compound < 0 else "◼"
        st.markdown(f"""
            <div style='padding:0.8rem 0;
                        border-bottom:1px solid #F0F0F0;
                        display:flex; gap:1rem; align-items:flex-start;'>
                <div style='background:{bg}; color:{color};
                            border-radius:6px; padding:0.25rem 0.6rem;
                            font-size:0.75rem; font-weight:700;
                            white-space:nowrap; min-width:70px;
                            text-align:center;'>
                    {arrow} {row['label'].upper()}
                </div>
                <div style='flex:1;'>
                    <div style='font-weight:500; font-size:0.88rem;
                                color:#1A1A1A; line-height:1.4;'>
                        {row['title'][:120]}{'...' if len(row['title'])>120 else ''}
                    </div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                margin-top:0.2rem;'>
                        {row['publisher']} ·
                        {row['date'].strftime('%d %b %Y %H:%M')} ·
                        Score: {compound:+.3f}
                    </div>
                </div>
                <div style='text-align:right; min-width:80px;'>
                    <div style='font-size:0.75rem; color:#6B7280;'>Confidence</div>
                    <div style='font-weight:600; font-size:0.9rem;
                                color:{color};'>
                        {max(row['positive'], row['negative'], row['neutral'])*100:.0f}%
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Downloads ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.download_button(
            "⬇️  Download Scored News CSV",
            scored.to_csv(index=False).encode(),
            file_name=f"{ticker}_sentiment_news.csv",
            mime="text/csv"
        )
    with col_r:
        st.download_button(
            "⬇️  Download Daily Sentiment CSV",
            daily.to_csv(index=False).encode(),
            file_name=f"{ticker}_daily_sentiment.csv",
            mime="text/csv"
        )