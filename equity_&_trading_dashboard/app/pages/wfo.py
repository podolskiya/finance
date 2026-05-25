# app/pages/wfo.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.style import metric_card
from data.fetcher import fetch_price_data
from backtester.walk_forward import walk_forward

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    hovermode="x unified",
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)

FOLD_COLORS = [
    '#1A1A1A','#10B981','#3B82F6',
    '#F59E0B','#8B5CF6','#EF4444','#06B6D4'
]

def combined_equity_chart(combined: pd.DataFrame,
                           fold_results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Buy & hold
    fig.add_trace(go.Scatter(
        x=combined.index, y=combined['Buy_Hold_Curve'],
        name='Buy & Hold', mode='lines',
        line=dict(color='#10B981', width=1.5, dash='dash')
    ))

    # Combined OOS strategy
    fig.add_trace(go.Scatter(
        x=combined.index, y=combined['Equity_Curve'],
        name='WFO Strategy (OOS)', mode='lines',
        line=dict(color='#1A1A1A', width=2.5),
        fill='tozeroy', fillcolor='rgba(26,26,26,0.05)'
    ))

    # Fold boundary lines
    for _, row in fold_results.iterrows():
        fig.add_vline(
            x=row['Test Start'],
            line_dash="dot", line_color="#6B7280",
            line_width=1, opacity=0.5
        )

    fig.update_layout(
        height=320,
        title="Walk-Forward OOS Equity Curve",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def fold_sharpe_chart(fold_results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    folds = fold_results['Fold'].astype(str)

    fig.add_trace(go.Bar(
        x=folds, y=fold_results['Train Sharpe'],
        name='In-Sample Sharpe',
        marker_color='#6B7280', opacity=0.6
    ))
    fig.add_trace(go.Bar(
        x=folds, y=fold_results['OOS Sharpe'],
        name='Out-of-Sample Sharpe',
        marker_color=[
            '#10B981' if v > 0 else '#EF4444'
            for v in fold_results['OOS Sharpe']
        ]
    ))
    fig.add_hline(y=0, line_color='#1A1A1A',
                  line_width=1, line_dash='dot')

    fig.update_layout(
        height=280, barmode='group',
        title="In-Sample vs Out-of-Sample Sharpe per Fold",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    return fig


def drawdown_chart(combined: pd.DataFrame) -> go.Figure:
    equity = combined['Equity_Curve']
    dd     = (equity - equity.cummax()) / equity.cummax() * 100
    fig    = go.Figure()
    fig.add_trace(go.Scatter(
        x=combined.index, y=dd,
        mode='lines', name='Drawdown',
        line=dict(color='#EF4444', width=1.5),
        fill='tozeroy', fillcolor='rgba(239,68,68,0.08)'
    ))
    fig.update_layout(height=200, title="Drawdown (%)", **CHART_THEME)
    fig.update_yaxes(ticksuffix="%")
    return fig


def param_stability_chart(param_df: pd.DataFrame) -> go.Figure:
    if param_df.empty or len(param_df.columns) == 0:
        return None

    fig = go.Figure()
    colors = FOLD_COLORS
    for i, col in enumerate(param_df.columns):
        fig.add_trace(go.Scatter(
            x=list(range(1, len(param_df)+1)),
            y=param_df[col],
            name=col, mode='lines+markers',
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=8)
        ))

    fig.update_layout(
        height=260,
        title="Best Parameters Across Folds (Stability Check)",
        xaxis_title="Fold",
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    return fig


def oos_returns_chart(fold_results: pd.DataFrame) -> go.Figure:
    returns = [
        float(r.strip('%'))
        for r in fold_results['OOS Return']
        if r not in ['N/A', None]
    ]
    folds = [f"Fold {i+1}" for i in range(len(returns))]
    colors = ['#10B981' if r > 0 else '#EF4444' for r in returns]

    fig = go.Figure(go.Bar(
        x=folds, y=returns,
        marker_color=colors, opacity=0.85,
        text=[f"{r:+.1f}%" for r in returns],
        textposition='outside'
    ))
    fig.add_hline(y=0, line_color='#1A1A1A', line_width=1)
    fig.update_layout(
        height=240,
        title="OOS Return per Fold",
        showlegend=False, **CHART_THEME
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def overfitting_score(fold_results: pd.DataFrame) -> dict:
    """
    Measure overfitting: how much does OOS Sharpe
    degrade vs in-sample Sharpe?
    """
    is_sharpe  = fold_results['Train Sharpe'].mean()
    oos_sharpe = fold_results['OOS Sharpe'].mean()
    degradation = (is_sharpe - oos_sharpe) / abs(is_sharpe) * 100 if is_sharpe != 0 else 0
    pct_positive = (fold_results['OOS Sharpe'] > 0).mean() * 100

    if degradation < 20 and pct_positive >= 60:
        label, color = "Low Overfitting ✅",  "#065F46"
        bg            = "#D1FAE5"
    elif degradation < 50 and pct_positive >= 40:
        label, color = "Moderate Overfitting ⚠️", "#92400E"
        bg            = "#FEF3C7"
    else:
        label, color = "High Overfitting ❌",  "#991B1B"
        bg            = "#FEE2E2"

    return {
        "label":        label,
        "color":        color,
        "bg":           bg,
        "is_sharpe":    round(is_sharpe, 3),
        "oos_sharpe":   round(oos_sharpe, 3),
        "degradation":  round(degradation, 1),
        "pct_positive": round(pct_positive, 1),
    }


def show():
    st.markdown("""
        <div class='page-title'>Walk-Forward Optimisation</div>
        <div class='page-subtitle'>
            Out-of-sample parameter optimisation · Overfitting detection ·
            Institutionally credible backtesting
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**⚙️ WFO Settings**")

        ticker   = st.text_input("Ticker", "AAPL").upper().strip()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", pd.to_datetime("2018-01-01"))
        with col2:
            end   = st.date_input("End",   pd.to_datetime("2024-01-01"))

        strategy  = st.selectbox(
            "Strategy",
            ["Momentum", "Mean Reversion", "Combined"]
        )
        n_splits  = st.slider(
            "Number of Folds", 3, 8, 5,
            help="More folds = more robust but slower"
        )
        train_pct = st.slider(
            "Train %", 0.5, 0.85, 0.7, 0.05,
            help="Fraction of each fold used for training"
        ) 
        capital    = st.number_input("Capital ($)", value=100_000, step=10_000)
        commission = st.slider("Commission (%)", 0.0, 0.5, 0.1, 0.01) / 100
        slippage   = st.slider("Slippage (%)",   0.0, 0.5, 0.05, 0.01) / 100

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888; line-height:1.6;'>
                <b>How it works:</b><br>
                Data is split into N folds. For each fold,
                parameters are optimised on the training window
                and tested on the unseen test window.
                Only test results are used in the final curve —
                true out-of-sample performance.
            </div>
        """, unsafe_allow_html=True)

        run = st.button("▶  Run Walk-Forward")

    # ── Explainer ──
    if not run:
        st.markdown("""
            <div class='section-card'>
                <div style='font-size:1rem; font-weight:600; margin-bottom:1rem;'>
                    📖 What is Walk-Forward Optimisation?
                </div>
                <div style='display:flex; gap:1.5rem; flex-wrap:wrap;'>
                    <div style='flex:1; min-width:200px;'>
                        <div style='font-weight:600; color:#1A1A1A; margin-bottom:0.4rem;'>
                            ❌ Standard Backtest
                        </div>
                        <div style='font-size:0.85rem; color:#6B7280; line-height:1.6;'>
                            Optimise parameters on ALL historical data,
                            then test on the SAME data. Results look great
                            but are meaningless — the model has already
                            seen the test data. This is overfitting.
                        </div>
                    </div>
                    <div style='flex:1; min-width:200px;'>
                        <div style='font-weight:600; color:#10B981; margin-bottom:0.4rem;'>
                            ✅ Walk-Forward (WFO)
                        </div>
                        <div style='font-size:0.85rem; color:#6B7280; line-height:1.6;'>
                            Roll a window through time. Optimise on TRAIN,
                            test on unseen TEST data. Concatenate all test
                            results. This is the institutional standard —
                            results you can actually trust.
                        </div>
                    </div>
                    <div style='flex:1; min-width:200px;'>
                        <div style='font-weight:600; color:#3B82F6; margin-bottom:0.4rem;'>
                            📊 What to Look For
                        </div>
                        <div style='font-size:0.85rem; color:#6B7280; line-height:1.6;'>
                            • OOS Sharpe close to in-sample = robust<br>
                            • Consistent params across folds = stable<br>
                            • Majority of folds profitable = real edge<br>
                            • Low IS→OOS degradation = not overfit
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # ── Run WFO ──
    progress = st.progress(0, text="Starting walk-forward optimisation...")

    def progress_cb(fold_i, n_folds, stage):
        pct  = int((fold_i / n_folds) * 90)
        text = f"Fold {fold_i+1}/{n_folds} — {stage} parameters..."
        progress.progress(pct, text=text)

    with st.spinner(""):
        df  = fetch_price_data(ticker, str(start), str(end))
        wfo = walk_forward(
            df, strategy=strategy,
            n_splits=n_splits, train_pct=train_pct,
            capital=capital, commission=commission, slippage=slippage,
            progress_cb=progress_cb
        )

    if "error" in wfo:
        st.error(f"WFO failed: {wfo['error']}")
        return

    progress.progress(100, text="Complete!")

    fold_results = wfo['fold_results']
    combined     = wfo['combined_curve']
    metrics      = wfo['combined_metrics']
    param_df     = wfo['param_stability']
    of_score     = overfitting_score(fold_results)

    # ── Overfitting Score Banner ──
    st.markdown(f"""
        <div style='background:{of_score["bg"]};
                    border-radius:12px; padding:1rem 1.5rem;
                    margin-bottom:1.5rem;
                    border:1px solid {of_score["color"]}20;
                    display:flex; justify-content:space-between;
                    align-items:center;'>
            <div>
                <div style='font-size:0.75rem; color:{of_score["color"]};
                            text-transform:uppercase; font-weight:600;
                            letter-spacing:0.05em;'>
                    Overfitting Assessment
                </div>
                <div style='font-size:1.3rem; font-weight:700;
                            color:{of_score["color"]}; margin-top:0.2rem;'>
                    {of_score["label"]}
                </div>
            </div>
            <div style='display:flex; gap:2rem; text-align:center;'>
                <div>
                    <div style='font-size:0.72rem; color:{of_score["color"]};'>
                        IS Sharpe
                    </div>
                    <div style='font-weight:700; color:{of_score["color"]};'>
                        {of_score["is_sharpe"]}
                    </div>
                </div>
                <div>
                    <div style='font-size:0.72rem; color:{of_score["color"]};'>
                        OOS Sharpe
                    </div>
                    <div style='font-weight:700; color:{of_score["color"]};'>
                        {of_score["oos_sharpe"]}
                    </div>
                </div>
                <div>
                    <div style='font-size:0.72rem; color:{of_score["color"]};'>
                        Degradation
                    </div>
                    <div style='font-weight:700; color:{of_score["color"]};'>
                        {of_score["degradation"]}%
                    </div>
                </div>
                <div>
                    <div style='font-size:0.72rem; color:{of_score["color"]};'>
                        Folds Profitable
                    </div>
                    <div style='font-weight:700; color:{of_score["color"]};'>
                        {of_score["pct_positive"]}%
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Combined Metrics ──
    sharpe = float(metrics['Sharpe Ratio'])
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    cards = [
        (c1, "OOS Total Return", metrics['Total Return'],  None),
        (c2, "OOS CAGR",         metrics['CAGR'],          float(metrics['CAGR'].strip('%'))>0),
        (c3, "OOS Sharpe",       str(sharpe),              sharpe > 0),
        (c4, "Max Drawdown",     metrics['Max Drawdown'],  False),
        (c5, "Win Rate",         metrics['Win Rate'],      float(metrics['Win Rate'].strip('%'))>50),
        (c6, "Final Equity",     metrics['Final Equity'],  None),
    ]
    for col, label, val, pos in cards:
        with col:
            st.markdown(metric_card(label, val, positive=pos),
                        unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Equity Curve ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(combined_equity_chart(combined, fold_results),
                    use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Drawdown ──
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(drawdown_chart(combined),
                    use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Fold Analysis ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(fold_sharpe_chart(fold_results),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(oos_returns_chart(fold_results),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Parameter Stability ──
    fig_ps = param_stability_chart(param_df)
    if fig_ps:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(fig_ps, use_container_width=True,
                        config={"displayModeBar":False})
        st.markdown("""
            <div style='font-size:0.8rem; color:#6B7280; margin-top:0.5rem;'>
                💡 Stable parameters across folds = robust strategy.
                Wildly changing parameters = overfitting to noise.
            </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Fold Table ──
    st.markdown("**📋 Fold-by-Fold Breakdown**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)

    display_cols = ['Fold','Train Start','Train End',
                    'Test Start','Test End',
                    'Train Sharpe','OOS Sharpe',
                    'OOS Return','OOS CAGR','OOS Drawdown']

    def colour_sharpe(val):
        if isinstance(val, float):
            return f'color: {"#10B981" if val > 0 else "#EF4444"}; font-weight:600'
        return ''

    styled = (
        fold_results[display_cols]
        .style
        .applymap(colour_sharpe, subset=['OOS Sharpe','Train Sharpe'])
        .format({'Train Sharpe': '{:.3f}', 'OOS Sharpe': '{:.3f}'})
    )
    st.dataframe(styled, use_container_width=True, height=250)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Downloads ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.download_button(
            "⬇️  Download Fold Results CSV",
            fold_results.to_csv(index=False).encode(),
            file_name=f"{ticker}_{strategy}_wfo_folds.csv",
            mime="text/csv"
        )
    with col_r:
        st.download_button(
            "⬇️  Download OOS Equity Curve CSV",
            combined.to_csv().encode(),
            file_name=f"{ticker}_{strategy}_wfo_equity.csv",
            mime="text/csv"
        )