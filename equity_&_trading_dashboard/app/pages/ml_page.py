# app/pages/ml_page.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json, os
from app.style import metric_card
from data.fetcher import fetch_price_data
from ml.features import build_features
from ml.model import train_model, load_trained_model
from ml.self_improve import generate_ml_signals, self_improve
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

LOG_PATH = "ml/improvement_log.json"

def load_log() -> list:
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return []

def equity_chart(results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Equity_Curve'],
        name='ML Strategy', mode='lines',
        line=dict(color='#1A1A1A', width=2.5),
        fill='tozeroy', fillcolor='rgba(26,26,26,0.05)'
    ))
    fig.add_trace(go.Scatter(
        x=results.index, y=results['Buy_Hold_Curve'],
        name='Buy & Hold', mode='lines',
        line=dict(color='#10B981', width=2, dash='dash')
    ))
    fig.update_layout(height=300, legend=dict(orientation="h"), **CHART_THEME)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig

def drawdown_chart(results: pd.DataFrame) -> go.Figure:
    equity      = results['Equity_Curve']
    rolling_max = equity.cummax()
    dd          = (equity - rolling_max) / rolling_max * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=dd,
        name='Drawdown', mode='lines',
        line=dict(color='#EF4444', width=1.5),
        fill='tozeroy', fillcolor='rgba(239,68,68,0.08)'
    ))
    fig.update_layout(height=200, **CHART_THEME)
    fig.update_yaxes(ticksuffix="%")
    return fig

def signals_chart(results: pd.DataFrame,
                  ticker: str) -> go.Figure:
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
        marker=dict(symbol='triangle-up', color='#10B981', size=9)
    ))
    fig.add_trace(go.Scatter(
        x=shorts.index, y=shorts['Close'],
        name='Short', mode='markers',
        marker=dict(symbol='triangle-down', color='#EF4444', size=9)
    ))
    fig.update_layout(
        height=280, title=f"{ticker} — ML Signal Overlay",
        legend=dict(orientation="h"), **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$")
    return fig

def feature_importance_chart(features: pd.DataFrame) -> go.Figure:
    cols = [c for c in features.columns if c != 'target']
    corr = features[cols].corrwith(features['target']).abs().sort_values(ascending=True)
    fig  = go.Figure(go.Bar(
        x=corr.values, y=corr.index,
        orientation='h',
        marker_color='#1A1A1A', opacity=0.8,
        text=[f"{v:.3f}" for v in corr.values],
        textposition='outside'
    ))
    fig.update_layout(
        height=400, title="Feature Correlation with Target",
        **CHART_THEME
    )
    return fig

def training_history_chart(history) -> go.Figure:
    fig = go.Figure()
    epochs = list(range(1, len(history.history['loss']) + 1))
    fig.add_trace(go.Scatter(
        x=epochs, y=history.history['loss'],
        name='Train Loss', mode='lines',
        line=dict(color='#1A1A1A', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=history.history['val_loss'],
        name='Val Loss', mode='lines',
        line=dict(color='#EF4444', width=2, dash='dash')
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=history.history['accuracy'],
        name='Train Acc', mode='lines',
        line=dict(color='#10B981', width=2),
        yaxis='y2'
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=history.history['val_accuracy'],
        name='Val Acc', mode='lines',
        line=dict(color='#3B82F6', width=2, dash='dash'),
        yaxis='y2'
    ))
    fig.update_layout(
        height=300,
        title="Training History",
        yaxis=dict(title="Loss", showgrid=True,
                   gridcolor='#F0F0F0', color='#6B7280'),
        yaxis2=dict(title="Accuracy", overlaying='y',
                    side='right', color='#6B7280',
                    tickformat=".0%"),
        legend=dict(orientation="h"),
        **{k: v for k, v in CHART_THEME.items()
           if k not in ['yaxis']}
    )
    return fig

def improvement_log_chart(log: list, ticker: str) -> go.Figure:
    entries = [e for e in log if e['ticker'] == ticker]
    if len(entries) < 2:
        return None
    df = pd.DataFrame(entries)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(df)+1)),
        y=df['accuracy'],
        mode='lines+markers',
        name='Accuracy',
        line=dict(color='#1A1A1A', width=2.5),
        marker=dict(size=8, color='#1A1A1A')
    ))
    fig.update_layout(
        height=220,
        title="Model Accuracy Over Retraining Cycles",
        **CHART_THEME
    )
    fig.update_yaxes(tickformat=".1%")
    return fig

def signal_distribution_chart(signals: pd.Series) -> go.Figure:
    counts = signals.value_counts().sort_index()
    labels = {-1: 'Short', 0: 'Flat', 1: 'Long'}
    colors = {-1: '#EF4444', 0: '#6B7280', 1: '#10B981'}
    fig = go.Figure(go.Bar(
        x=[labels.get(i, str(i)) for i in counts.index],
        y=counts.values,
        marker_color=[colors.get(i, '#1A1A1A') for i in counts.index],
        text=counts.values, textposition='outside'
    ))
    fig.update_layout(
        height=220, title="Signal Distribution",
        showlegend=False, **CHART_THEME
    )
    return fig

def show():
    st.markdown("""
        <div class='page-title'>ML Signal Engine</div>
        <div class='page-subtitle'>
            TensorFlow LSTM · Self-improving model ·
            Confidence-filtered trading signals
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**🧠 ML Settings**")

        ticker  = st.text_input("Ticker", "AAPL").upper().strip()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start", pd.to_datetime("2020-01-01"))
        with col2:
            end   = st.date_input("End",   pd.to_datetime("2024-01-01"))

        capital   = st.number_input("Capital ($)", value=100_000, step=10_000)
        threshold = st.slider("Confidence Threshold", 0.50, 0.80, 0.60, 0.01,
                              help="Only act on signals above this confidence level")

        st.markdown("**Model Training**")
        epochs   = st.slider("Max Epochs", 10, 100, 50, 5)
        seq_len  = st.slider("Sequence Length", 10, 40, 20,
                             help="Lookback window for LSTM (trading days)")
        force_retrain = st.checkbox("Force Retrain", value=False,
                                    help="Retrain even if a saved model exists")

        st.markdown("**Self-Improvement**")
        auto_improve = st.checkbox("Auto Self-Improve", value=True,
                                   help="Automatically retrain if accuracy degrades")

        run = st.button("▶  Run ML Analysis")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>🧠</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    LSTM Neural Network Engine
                </div>
                <div style='color:#6B7280; margin-top:0.5rem; max-width:400px; margin-left:auto; margin-right:auto;'>
                    Train a deep LSTM on engineered features, generate
                    confidence-filtered signals, and backtest performance.
                    The model self-improves on new data over time.
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Show improvement log if it exists
        log = load_log()
        if log:
            st.markdown("**📋 Previous Training Sessions**")
            log_df = pd.DataFrame(log)
            st.dataframe(
                log_df.style.format({
                    'accuracy': '{:.2%}',
                    'loss':     '{:.4f}'
                }).background_gradient(subset=['accuracy'], cmap='RdYlGn'),
                use_container_width=True
            )
        return

    # ── Step 1: Data ──
    progress = st.progress(0, text="Fetching market data...")
    with st.spinner(""):
        df       = fetch_price_data(ticker, str(start), str(end))
        features = build_features(df)
    progress.progress(20, text="Features engineered...")

    st.markdown(f"""
        <div class='section-card'>
            <div style='display:flex; gap:2rem;'>
                <div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                text-transform:uppercase;'>Data Points</div>
                    <div style='font-size:1.4rem; font-weight:700;'>{len(df):,}</div>
                </div>
                <div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                text-transform:uppercase;'>Features</div>
                    <div style='font-size:1.4rem; font-weight:700;'>
                        {len([c for c in features.columns if c != 'target'])}
                    </div>
                </div>
                <div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                text-transform:uppercase;'>Training Samples</div>
                    <div style='font-size:1.4rem; font-weight:700;'>
                        {int(len(features)*0.8):,}
                    </div>
                </div>
                <div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                text-transform:uppercase;'>Test Samples</div>
                    <div style='font-size:1.4rem; font-weight:700;'>
                        {int(len(features)*0.2):,}
                    </div>
                </div>
                <div>
                    <div style='font-size:0.75rem; color:#6B7280;
                                text-transform:uppercase;'>Sequence Length</div>
                    <div style='font-size:1.4rem; font-weight:700;'>{seq_len}d</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Feature Importance ──
    with st.expander("📊 Feature Analysis", expanded=False):
        st.plotly_chart(feature_importance_chart(features),
                        use_container_width=True,
                        config={"displayModeBar": False})

    # ── Step 2: Train / Load Model ──
    saved_path = f"ml/saved_models/{ticker}_lstm.keras"
    bundle     = None

    if not force_retrain and os.path.exists(saved_path):
        progress.progress(40, text="Loading saved model...")
        st.info(f"✅ Found saved model for {ticker}. Using existing weights. "
                f"Tick 'Force Retrain' to train from scratch.")
        from tensorflow.keras.models import load_model as lm
        model = lm(saved_path)
        from ml.model import build_sequences
        X, y, scaler, feature_cols = build_sequences(features, seq_len)
        bundle = {
            "model": model, "scaler": scaler,
            "feature_cols": feature_cols,
            "accuracy": None, "loss": None,
            "history": None, "seq_len": seq_len
        }
        # Quick eval
        import numpy as np
        split    = int(len(X) * 0.8)
        X_test   = X[split:]
        y_test   = y[split:]
        loss, acc = model.evaluate(X_test, y_test, verbose=0)
        bundle['accuracy'] = round(acc, 4)
        bundle['loss']     = round(loss, 4)
        progress.progress(60, text="Model loaded...")
    else:
        progress.progress(40, text="Training LSTM model...")
        train_placeholder = st.empty()
        train_placeholder.warning("⏳ Training LSTM — this takes 2-5 minutes...")
        bundle = train_model(features, ticker, seq_len=seq_len, epochs=epochs)
        train_placeholder.empty()
        progress.progress(60, text="Model trained...")

    # ── Model Performance Cards ──
    acc  = bundle['accuracy']
    loss = bundle['loss']

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(metric_card(
        "Test Accuracy", f"{acc:.2%}",
        sub="✅ Above random" if acc > 0.52 else "⚠️ Near random",
        positive=acc > 0.52
    ), unsafe_allow_html=True)
    with c2: st.markdown(metric_card(
        "Test Loss", f"{loss:.4f}",
        positive=loss < 0.69
    ), unsafe_allow_html=True)
    with c3: st.markdown(metric_card(
        "Confidence Threshold", f"{threshold:.0%}"
    ), unsafe_allow_html=True)
    with c4: st.markdown(metric_card(
        "Architecture", "3× LSTM"
    ), unsafe_allow_html=True)

    # Training history chart
    if bundle.get('history'):
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(training_history_chart(bundle['history']),
                        use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Step 3: Generate Signals ──
    progress.progress(70, text="Generating ML signals...")
    signals = generate_ml_signals(bundle, df, threshold=threshold)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(signal_distribution_chart(signals),
                        use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_r:
        total   = len(signals)
        n_long  = (signals ==  1).sum()
        n_short = (signals == -1).sum()
        n_flat  = (signals ==  0).sum()
        st.markdown(f"""
            <div class='section-card'>
                <div style='font-weight:600; margin-bottom:1rem;'>
                    Signal Summary
                </div>
                <div style='display:flex; flex-direction:column; gap:0.8rem;'>
                    <div style='display:flex; justify-content:space-between;
                                align-items:center;'>
                        <span style='color:#10B981; font-weight:600;'>▲ Long</span>
                        <span>{n_long} days
                            <span style='color:#6B7280; font-size:0.8rem;'>
                                ({n_long/total*100:.1f}%)
                            </span>
                        </span>
                    </div>
                    <div style='display:flex; justify-content:space-between;
                                align-items:center;'>
                        <span style='color:#EF4444; font-weight:600;'>▼ Short</span>
                        <span>{n_short} days
                            <span style='color:#6B7280; font-size:0.8rem;'>
                                ({n_short/total*100:.1f}%)
                            </span>
                        </span>
                    </div>
                    <div style='display:flex; justify-content:space-between;
                                align-items:center;'>
                        <span style='color:#6B7280; font-weight:600;'>◼ Flat</span>
                        <span>{n_flat} days
                            <span style='color:#6B7280; font-size:0.8rem;'>
                                ({n_flat/total*100:.1f}%)
                            </span>
                        </span>
                    </div>
                    <hr class='divider'>
                    <div style='font-size:0.8rem; color:#6B7280;'>
                        High threshold = fewer but higher-confidence trades.
                        Lower it in the sidebar to trade more actively.
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── Step 4: Backtest ──
    progress.progress(85, text="Backtesting ML strategy...")
    bt      = Backtester(df, initial_capital=capital)
    results = bt.run(signals)
    metrics = bt.metrics()
    progress.progress(95, text="Finalising...")

    st.markdown("**📊 Backtest Performance**")
    sharpe = float(metrics['Sharpe Ratio'])
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    cards = [
        (c1, "Total Return",  metrics['Total Return'],  None),
        (c2, "CAGR",          metrics['CAGR'],          float(metrics['CAGR'].strip('%'))>0),
        (c3, "Sharpe Ratio",  str(sharpe),              sharpe > 0),
        (c4, "Max Drawdown",  metrics['Max Drawdown'],  False),
        (c5, "Win Rate",      metrics['Win Rate'],      float(metrics['Win Rate'].strip('%'))>50),
        (c6, "Final Equity",  metrics['Final Equity'],  None),
    ]
    for col, label, val, pos in cards:
        with col:
            st.markdown(metric_card(label, val, positive=pos),
                        unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(equity_chart(results),
                    use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(drawdown_chart(results),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(signals_chart(results, ticker),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Step 5: Self-Improve ──
    if auto_improve:
        progress.progress(98, text="Running self-improvement check...")
        with st.expander("🔄 Self-Improvement Log", expanded=False):
            updated = self_improve(ticker, df, current_accuracy=acc)
            log     = load_log()
            if log:
                log_df = pd.DataFrame(log)
                st.dataframe(
                    log_df[log_df['ticker']==ticker].style.format({
                        'accuracy': '{:.2%}', 'loss': '{:.4f}'
                    }).background_gradient(subset=['accuracy'], cmap='RdYlGn'),
                    use_container_width=True
                )
                fig_log = improvement_log_chart(log, ticker)
                if fig_log:
                    st.plotly_chart(fig_log, use_container_width=True,
                                    config={"displayModeBar": False})
            if updated:
                st.success(f"✅ Model retrained. New accuracy: {updated['accuracy']:.2%}")
            else:
                st.info("Model is performing well — no retraining needed.")

    progress.progress(100, text="Done!")

    # ── Downloads ──
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    with col_l:
        st.download_button(
            "⬇️  Download Signals CSV",
            pd.DataFrame({'Signal': signals}).to_csv().encode(),
            file_name=f"{ticker}_ml_signals.csv", mime="text/csv"
        )
    with col_r:
        st.download_button(
            "⬇️  Download Backtest CSV",
            results.to_csv().encode(),
            file_name=f"{ticker}_ml_backtest.csv", mime="text/csv"
        )