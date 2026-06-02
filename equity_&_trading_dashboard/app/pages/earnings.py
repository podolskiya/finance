# app/pages/earnings.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from app.style import metric_card, verdict_badge
from ml.earnings import full_earnings_analysis, get_earnings_history
import os

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)


def eps_chart(ticker: str) -> go.Figure:
    """EPS history bar chart."""
    try:
        stock = yf.Ticker(ticker)
        hist  = stock.earnings_history
        if hist is None or hist.empty:
            return None

        fig = go.Figure()
        if 'epsEstimate' in hist.columns:
            fig.add_trace(go.Bar(
                x=hist.index.astype(str),
                y=hist['epsEstimate'],
                name='EPS Estimate',
                marker_color='#6B7280',
                opacity=0.6
            ))
        if 'epsActual' in hist.columns:
            beat = hist.get('epsActual', pd.Series()) >= \
                   hist.get('epsEstimate', pd.Series())
            colors = ['#10B981' if b else '#EF4444'
                      for b in beat]
            fig.add_trace(go.Bar(
                x=hist.index.astype(str),
                y=hist['epsActual'],
                name='EPS Actual',
                marker_color=colors,
                opacity=0.9
            ))

        fig.update_layout(
            height=260,
            title="EPS History: Actual vs Estimate",
            barmode='group',
            legend=dict(orientation="h"),
            **CHART_THEME
        )
        return fig
    except:
        return None


def price_chart_1y(ticker: str) -> go.Figure:
    """1Y price chart with key events."""
    hist = yf.Ticker(ticker).history(period="1y")
    fig  = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist['Close'],
        name='Price', mode='lines',
        line=dict(color='#1A1A1A', width=2),
        fill='tozeroy',
        fillcolor='rgba(26,26,26,0.05)'
    ))
    fig.update_layout(
        height=220,
        title="12-Month Price Chart",
        **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$")
    return fig


def show():
    st.markdown("""
        <div class='page-subtitle'>
            Claude AI · SEC 10-K/10-Q analysis ·
            Earnings quality · Investment thesis generation
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**🤖 LLM Analyser Settings**")

        ticker = st.text_input("Ticker", "AAPL").upper().strip()

        horizon = st.selectbox(
            "Investment Horizon",
            ["Short (1-3M)", "Medium (3-6M)", "Long (6-12M)"],
            index=1
        )
        risk_profile = st.selectbox(
            "Risk Profile",
            ["Conservative", "Moderate", "Aggressive"],
            index=1
        )

        st.markdown("**🔑 API Key**")
        api_key_input = st.text_input(
            "Anthropic API Key",
            type="password",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            help="Get yours at console.anthropic.com"
        )
        if api_key_input:
            os.environ["ANTHROPIC_API_KEY"] = api_key_input

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888; line-height:1.7;'>
                <b>What Claude analyses:</b><br>
                • SEC 10-K / 10-Q filings<br>
                • Analyst estimates & targets<br>
                • Recent financial news<br>
                • Key financial ratios<br>
                • Management language & tone<br><br>
                Generates a full institutional-grade
                research report in seconds.
            </div>
        """, unsafe_allow_html=True)

        run = st.button("▶  Generate Report")

    if not run:
        st.markdown("""
            <div class='section-card'
                 style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>🤖</div>
                <div style='font-size:1.1rem; font-weight:600;
                            margin-top:1rem;'>
                    LLM Earnings Analyser
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;
                            max-width:480px;
                            margin-left:auto; margin-right:auto;'>
                    Combines SEC filings, earnings history,
                    analyst estimates, and financial news —
                    then sends everything to Claude for a
                    deep institutional-grade investment report.
                    <br><br>
                    Add your Anthropic API key in the sidebar
                    to get started.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("⚠️  Please enter your Anthropic API key in the sidebar.")
        st.markdown("""
            Get a free API key at
            [console.anthropic.com](https://console.anthropic.com)
        """)
        return

    # ── Run Analysis ──
    progress = st.progress(0, text="Starting analysis...")

    def progress_cb(step, msg):
        progress.progress(step, text=msg)

    with st.spinner(""):
        result = full_earnings_analysis(
            ticker       = ticker,
            horizon      = horizon,
            risk_profile = risk_profile,
            api_key      = os.environ.get("ANTHROPIC_API_KEY"),
            progress_cb  = progress_cb
        )

    progress.progress(100, text="Report ready!")

    analysis = result.get("analysis", {})

    if "error" in analysis:
        st.error(f"Analysis error: {analysis['error']}")
        if "raw" in analysis:
            with st.expander("Raw response"):
                st.code(analysis["raw"])
        return

    # ── Report Header ──
    verdict   = analysis.get("verdict", "HOLD")
    conf      = analysis.get("confidence", 50)
    target    = analysis.get("price_target")
    upside    = analysis.get("upside")
    mgmt_tone = analysis.get("management_tone", "Neutral")
    eq        = analysis.get("earnings_quality", "Medium")
    val_asmnt = analysis.get("valuation_assessment", "Fair")
    moat      = analysis.get("moat_strength", "Narrow")

    verdict_colors = {
        "STRONG BUY":  ("#065F46", "#D1FAE5"),
        "BUY":         ("#065F46", "#D1FAE5"),
        "HOLD":        ("#92400E", "#FEF3C7"),
        "SELL":        ("#991B1B", "#FEE2E2"),
        "STRONG SELL": ("#991B1B", "#FEE2E2"),
    }
    vc = verdict_colors.get(verdict, ("#374151", "#F3F4F6"))

    st.markdown(f"""
        <div class='section-card'
             style='background:{vc[1]};
                    border:1px solid {vc[0]}30;'>
            <div style='display:flex; justify-content:space-between;
                        align-items:flex-start; flex-wrap:wrap; gap:1rem;'>
                <div>
                    <div style='font-size:0.75rem; color:{vc[0]};
                                text-transform:uppercase;
                                letter-spacing:0.05em; font-weight:600;'>
                        Claude AI · Equity Research Report
                    </div>
                    <div style='font-size:0.85rem; color:{vc[0]};
                                margin-top:0.2rem;'>
                        {ticker} · {horizon} · {risk_profile} Risk ·
                        Generated {result['generated_at']}
                    </div>
                    <div style='font-size:2.2rem; font-weight:800;
                                color:{vc[0]}; margin-top:0.5rem;'>
                        {verdict}
                    </div>
                </div>
                <div style='display:flex; gap:2rem; flex-wrap:wrap;'>
                    <div style='text-align:center;'>
                        <div style='font-size:0.72rem; color:{vc[0]};'>
                            Confidence
                        </div>
                        <div style='font-size:1.8rem; font-weight:700;
                                    color:{vc[0]};'>{conf}%</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='font-size:0.72rem; color:{vc[0]};'>
                            Price Target
                        </div>
                        <div style='font-size:1.8rem; font-weight:700;
                                    color:{vc[0]};'>
                            ${target:.2f if target else 'N/A'}
                        </div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='font-size:0.72rem; color:{vc[0]};'>
                            Upside
                        </div>
                        <div style='font-size:1.8rem; font-weight:700;
                                    color:{vc[0]};'>
                            {f"{upside:+.1f}%" if upside else "N/A"}
                        </div>
                    </div>
                </div>
            </div>
            <hr style='border-color:{vc[0]}20; margin:1rem 0;'>
            <div style='font-size:0.92rem; color:{vc[0]};
                        line-height:1.6; font-style:italic;'>
                "{analysis.get('investment_thesis','')}"
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Quick Assessment Cards ──
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)

    assessment_colors = {
        "Bullish":    ("#D1FAE5","#065F46"),
        "Cautious":   ("#FEF3C7","#92400E"),
        "Neutral":    ("#F3F4F6","#374151"),
        "Defensive":  ("#FEE2E2","#991B1B"),
        "High":       ("#D1FAE5","#065F46"),
        "Medium":     ("#FEF3C7","#92400E"),
        "Low":        ("#FEE2E2","#991B1B"),
        "Expensive":  ("#FEE2E2","#991B1B"),
        "Fair":       ("#FEF3C7","#92400E"),
        "Cheap":      ("#D1FAE5","#065F46"),
        "Wide":       ("#D1FAE5","#065F46"),
        "Narrow":     ("#FEF3C7","#92400E"),
        "None":       ("#FEE2E2","#991B1B"),
    }

    for col, label, value in [
        (c1, "Management Tone",     mgmt_tone),
        (c2, "Earnings Quality",    eq),
        (c3, "Valuation",           val_asmnt),
        (c4, "Moat Strength",       moat),
    ]:
        bg, fg = assessment_colors.get(value, ("#F3F4F6","#374151"))
        with col:
            st.markdown(f"""
                <div class='metric-card'
                     style='background:{bg}; border:none;'>
                    <div class='label'
                         style='color:{fg}; opacity:0.8;'>{label}</div>
                    <div style='font-size:1.1rem; font-weight:700;
                                color:{fg};'>{value}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Price Chart + EPS ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(price_chart_1y(ticker),
                        use_container_width=True,
                        config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_r:
        eps_fig = eps_chart(ticker)
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if eps_fig:
            st.plotly_chart(eps_fig, use_container_width=True,
                            config={"displayModeBar":False})
        else:
            st.info("EPS history unavailable for this ticker.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Bull / Bear Cases ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"""
            <div class='section-card'
                 style='border-top:3px solid #10B981;'>
                <div style='font-weight:700; color:#10B981;
                            margin-bottom:0.6rem;'>
                    🟢 Bull Case
                </div>
                <div style='font-size:0.88rem; color:#1A1A1A;
                            line-height:1.6;'>
                    {analysis.get('bull_case', 'N/A')}
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_r:
        st.markdown(f"""
            <div class='section-card'
                 style='border-top:3px solid #EF4444;'>
                <div style='font-weight:700; color:#EF4444;
                            margin-bottom:0.6rem;'>
                    🔴 Bear Case
                </div>
                <div style='font-size:0.88rem; color:#1A1A1A;
                            line-height:1.6;'>
                    {analysis.get('bear_case', 'N/A')}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── Strengths, Risks, Catalysts ──
    c1,c2,c3 = st.columns(3)

    def bullet_list(items: list, color: str) -> str:
        if not items:
            return "<div style='color:#6B7280;'>N/A</div>"
        return "".join([
            f"""<div style='display:flex; gap:0.5rem;
                            margin-bottom:0.5rem; font-size:0.85rem;'>
                    <span style='color:{color}; font-weight:700;
                                 flex-shrink:0;'>→</span>
                    <span>{item}</span>
                </div>"""
            for item in items
        ])

    with c1:
        st.markdown(f"""
            <div class='section-card'>
                <div style='font-weight:700; margin-bottom:0.8rem;'>
                    💪 Key Strengths
                </div>
                {bullet_list(analysis.get('key_strengths',[]), '#10B981')}
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class='section-card'>
                <div style='font-weight:700; margin-bottom:0.8rem;'>
                    ⚠️ Key Risks
                </div>
                {bullet_list(analysis.get('key_risks',[]), '#EF4444')}
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class='section-card'>
                <div style='font-weight:700; margin-bottom:0.8rem;'>
                    🚀 Near-Term Catalysts
                </div>
                {bullet_list(analysis.get('catalysts',[]), '#3B82F6')}
            </div>
        """, unsafe_allow_html=True)

    # ── Metrics to Watch ──
    metrics_watch = analysis.get('key_metrics_to_watch', [])
    if metrics_watch:
        st.markdown(f"""
            <div class='section-card'>
                <div style='font-weight:700; margin-bottom:0.8rem;'>
                    📌 Key Metrics to Watch
                </div>
                <div style='display:flex; gap:0.8rem; flex-wrap:wrap;'>
                    {"".join([
                        f'''<span style="background:#F0F2F5;
                                        border-radius:20px;
                                        padding:0.3rem 0.8rem;
                                        font-size:0.82rem;
                                        font-weight:500;">{m}</span>'''
                        for m in metrics_watch
                    ])}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── Recommended Action ──
    action = analysis.get('recommended_action', '')
    if action:
        st.markdown(f"""
            <div class='section-card'
                 style='background:#1A1A1A; border-radius:16px;'>
                <div style='font-size:0.75rem; color:#888;
                            text-transform:uppercase;
                            letter-spacing:0.05em;'>
                    Recommended Action
                </div>
                <div style='font-size:1rem; color:#FFFFFF;
                            margin-top:0.5rem; line-height:1.6;
                            font-weight:500;'>
                    {action}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── Financial Snapshot ──
    with st.expander("📊 Full Financial Snapshot"):
        st.code(result.get("financials", ""), language="text")

    with st.expander("📰 News Context Used"):
        st.text(result.get("news", "No news available."))

    with st.expander("📄 SEC Filings Used"):
        filings = result.get("filings", [])
        if filings:
            for f in filings:
                st.markdown(f"**{f['form']}** · {f['date']} · "
                            f"[View Filing]({f['url']})")
        else:
            st.info("No SEC filings found.")

    # ── Download ──
    import json
    report_json = json.dumps({
        "ticker":   ticker,
        "verdict":  verdict,
        "analysis": analysis,
        "generated_at": result["generated_at"]
    }, indent=2)

    st.download_button(
        "⬇️  Download Full Report JSON",
        report_json.encode(),
        file_name=f"{ticker}_earnings_report.json",
        mime="application/json"
    )