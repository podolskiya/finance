import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
from app.style import metric_card, verdict_badge
from equity.fundamentals import get_fundamentals, get_financial_statements
from equity.dcf import dcf_valuation
from equity.comparables import get_comparables, investment_verdict

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)

def fmt(val, prefix="", suffix="", decimals=2):
    if val is None: return "N/A"
    if isinstance(val, float) and abs(val) < 1 and suffix != "x":
        return f"{prefix}{val*100:.{decimals}f}%"
    if abs(val) >= 1e9:  return f"{prefix}{val/1e9:.{decimals}f}B{suffix}"
    if abs(val) >= 1e6:  return f"{prefix}{val/1e6:.{decimals}f}M{suffix}"
    return f"{prefix}{val:.{decimals}f}{suffix}"

def price_chart(ticker: str) -> go.Figure:
    hist = yf.Ticker(ticker).history(period="1y")
    ma50 = hist['Close'].rolling(50).mean()
    ma20 = hist['Close'].rolling(20).mean()
    fig  = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'], high=hist['High'],
        low=hist['Low'],   close=hist['Close'],
        name='Price',
        increasing_line_color='#10B981',
        decreasing_line_color='#EF4444'
    ))
    fig.add_trace(go.Scatter(
        x=ma20.index, y=ma20,
        name='MA20', line=dict(color='#3B82F6', width=1.5)
    ))
    fig.add_trace(go.Scatter(
        x=ma50.index, y=ma50,
        name='MA50', line=dict(color='#F59E0B', width=1.5)
    ))
    fig.update_layout(
        height=340,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h"),
        **CHART_THEME
    )
    return fig

def revenue_earnings_chart(statements: dict) -> go.Figure:
    try:
        inc = statements['income_statement']
        if inc is None or inc.empty:
            return None
        rev = inc.loc['Total Revenue'].dropna().sort_index() if 'Total Revenue' in inc.index else None
        net = inc.loc['Net Income'].dropna().sort_index()    if 'Net Income'    in inc.index else None
        fig = go.Figure()
        if rev is not None:
            fig.add_trace(go.Bar(
                x=[str(d.year) for d in rev.index],
                y=rev.values / 1e9,
                name='Revenue ($B)',
                marker_color='#1A1A1A', opacity=0.85
            ))
        if net is not None:
            fig.add_trace(go.Bar(
                x=[str(d.year) for d in net.index],
                y=net.values / 1e9,
                name='Net Income ($B)',
                marker_color='#10B981', opacity=0.85
            ))
        fig.update_layout(
            height=280, barmode='group',
            title="Revenue & Net Income (Annual, $B)",
            **CHART_THEME
        )
        return fig
    except:
        return None

def dcf_chart(dcf: dict) -> go.Figure:
    labels = ['Bear Case', 'Intrinsic Value', 'Bull Case', 'Current Price']
    values = [dcf['bear_case'], dcf['intrinsic_value'],
              dcf['bull_case'], dcf['current_price']]
    colors = ['#EF4444', '#1A1A1A', '#10B981', '#3B82F6']
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"${v:.2f}" for v in values],
        textposition='outside'
    ))
    fig.update_layout(
        height=280, title="DCF Valuation Scenarios",
        showlegend=False, **CHART_THEME
    )
    fig.update_yaxes(tickprefix="$")
    return fig

def comps_chart(comps: pd.DataFrame, metric: str = "P/E") -> go.Figure:
    df = comps[[metric]].dropna().sort_values(metric)
    colors = ['#10B981' if i == df.index.get_loc(df[metric].idxmin())
              else '#1A1A1A' for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df.index, y=df[metric],
        marker_color=['#3B82F6' if t == comps.index[0]
                      else '#1A1A1A' for t in df.index],
        text=[f"{v:.1f}x" for v in df[metric]],
        textposition='outside'
    ))
    fig.update_layout(
        height=260, title=f"{metric} vs Peers",
        showlegend=False, **CHART_THEME
    )
    return fig

def margins_chart(fund: dict) -> go.Figure:
    p = fund['profitability']
    labels, values, colors = [], [], []
    mapping = {
        'Gross Margin':     '#1A1A1A',
        'Operating Margin': '#3B82F6',
        'Net Margin':       '#10B981'
    }
    for k, c in mapping.items():
        v = p.get(k)
        if v is not None:
            labels.append(k)
            values.append(round(v * 100, 2))
            colors.append(c)
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in values],
        textposition='outside'
    ))
    fig.update_layout(
        height=240, title="Profit Margins",
        showlegend=False, **CHART_THEME
    )
    fig.update_yaxes(ticksuffix="%")
    return fig

def show():
    st.markdown("""
        <div class='page-title'>Equity Analysis</div>
        <div class='page-subtitle'>
            Fundamental analysis · DCF valuation ·
            Comparable companies · Investment verdict
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**🏢 Equity Settings**")
        ticker   = st.text_input("Ticker", "AAPL").upper().strip()
        horizon  = st.selectbox("Investment Horizon",
                                ["Short (1-3M)","Medium (3-6M)","Long (6-12M)"],
                                index=2)
        risk     = st.selectbox("Risk Tolerance",
                                ["Conservative","Moderate","Aggressive"],
                                index=1)
        st.markdown("**DCF Assumptions**")
        discount = st.slider("Discount Rate (%)", 6.0, 15.0, 10.0, 0.5) / 100
        terminal = st.slider("Terminal Growth (%)", 1.0, 4.0, 2.5, 0.25) / 100
        years    = st.slider("Projection Years", 3, 10, 5)
        n_peers  = st.slider("Peer Companies", 3, 8, 5)
        run      = st.button("▶  Analyse")

    if not run:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>🏢</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    Equity Analysis Engine
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;'>
                    Enter a ticker, configure your assumptions,
                    and click Analyse for a full investment report
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    with st.spinner(f"Fetching data for {ticker}..."):
        try:
            fund       = get_fundamentals(ticker)
            statements = get_financial_statements(ticker)
            dcf        = dcf_valuation(ticker, discount_rate=discount,
                                       terminal_growth=terminal,
                                       projection_years=years)
            comps      = get_comparables(ticker, n_peers)
            verdict    = investment_verdict(ticker, dcf, comps)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return

    co = fund['company']

    st.markdown(f"""
        <div class='section-card'>
            <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                <div>
                    <div style='font-size:1.4rem; font-weight:700;'>
                        {co.get('Name','N/A')}
                        <span style='font-size:1rem; color:#6B7280;
                                     font-weight:400; margin-left:0.5rem;'>
                            {ticker}
                        </span>
                    </div>
                    <div style='color:#6B7280; font-size:0.88rem; margin-top:0.3rem;'>
                        {co.get('Sector','N/A')} · {co.get('Industry','N/A')} ·
                        {co.get('Country','N/A')} ·
                        {f"{co.get('Employees',0):,}" if co.get('Employees') else 'N/A'} employees
                    </div>
                </div>
                <div style='text-align:right;'>
                    {verdict_badge(verdict['verdict'])}
                    <div style='color:#6B7280; font-size:0.8rem; margin-top:0.4rem;'>
                        Confidence: {verdict['confidence']} ·
                        Horizon: {horizon}
                    </div>
                </div>
            </div>
            <hr class='divider'>
            <div style='font-size:0.85rem; color:#6B7280; line-height:1.6;'>
                {(co.get('Summary') or '')[:400]}{'...' if len(co.get('Summary') or '') > 400 else ''}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("**📈 Price Chart (1Y) with MA20 & MA50**")
    st.plotly_chart(price_chart(ticker),
                    use_container_width=True, config={"displayModeBar":False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**💰 Valuation**")
    v = fund['valuation']
    c1,c2,c3,c4,c5 = st.columns(5)
    val_cards = [
        (c1, "P/E (TTM)",   fmt(v.get('P/E (TTM)'),   suffix="x", decimals=1)),
        (c2, "Forward P/E", fmt(v.get('Forward P/E'),  suffix="x", decimals=1)),
        (c3, "EV/EBITDA",   fmt(v.get('EV/EBITDA'),    suffix="x", decimals=1)),
        (c4, "P/B Ratio",   fmt(v.get('P/B Ratio'),    suffix="x", decimals=1)),
        (c5, "PEG Ratio",   fmt(v.get('PEG Ratio'),    suffix="x", decimals=2)),
    ]
    for col, label, val in val_cards:
        with col:
            st.markdown(metric_card(label, val), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(margins_chart(fund),
                        use_container_width=True, config={"displayModeBar":False})
        pr = fund['profitability']
        st.markdown(f"""
            <div style='display:flex; gap:1rem; flex-wrap:wrap; margin-top:0.5rem;'>
                <div style='font-size:0.85rem;'>
                    ROE: <b>{fmt(pr.get('ROE'))}</b>
                </div>
                <div style='font-size:0.85rem;'>
                    ROA: <b>{fmt(pr.get('ROA'))}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        fig_re = revenue_earnings_chart(statements)
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if fig_re:
            st.plotly_chart(fig_re, use_container_width=True,
                            config={"displayModeBar":False})
        else:
            st.info("Financial statement data unavailable.")
        g = fund['growth']
        st.markdown(f"""
            <div style='display:flex; gap:1rem; flex-wrap:wrap; margin-top:0.5rem;'>
                <div style='font-size:0.85rem;'>
                    Rev Growth: <b>{fmt(g.get('Revenue Growth (YoY)'))}</b>
                </div>
                <div style='font-size:0.85rem;'>
                    EPS (TTM): <b>${g.get('EPS (TTM)','N/A')}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**🏥 Financial Health**")
    h = fund['health']
    c1,c2,c3,c4,c5 = st.columns(5)
    health_cards = [
        (c1, "Total Cash",     fmt(h.get('Total Cash'),     prefix="$")),
        (c2, "Total Debt",     fmt(h.get('Total Debt'),     prefix="$")),
        (c3, "Debt/Equity",    fmt(h.get('Debt/Equity'),    suffix="x", decimals=2)),
        (c4, "Current Ratio",  fmt(h.get('Current Ratio'),  suffix="x", decimals=2)),
        (c5, "Free Cash Flow", fmt(h.get('Free Cash Flow'), prefix="$")),
    ]
    for col, label, val in health_cards:
        with col:
            st.markdown(metric_card(label, val), unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    st.markdown("**🔢 DCF Intrinsic Value**")
    col_l, col_r = st.columns([1.4, 1])

    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.plotly_chart(dcf_chart(dcf),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        upside = dcf.get('upside_downside', 0)
        mos    = dcf.get('margin_of_safety', 0)
        st.markdown(f"""
            <div class='section-card'>
                <div style='font-size:0.78rem; color:#6B7280;
                            text-transform:uppercase; letter-spacing:0.05em;'>
                    Current Price
                </div>
                <div style='font-size:1.8rem; font-weight:700;'>
                    ${dcf['current_price']:,.2f}
                </div>
                <hr class='divider'>
                <div style='font-size:0.78rem; color:#6B7280;
                            text-transform:uppercase; letter-spacing:0.05em;'>
                    Intrinsic Value
                </div>
                <div style='font-size:1.8rem; font-weight:700;
                            color:{"#10B981" if upside > 0 else "#EF4444"};'>
                    ${dcf['intrinsic_value']:,.2f}
                </div>
                <hr class='divider'>
                <div style='display:flex; justify-content:space-between; margin-top:0.5rem;'>
                    <div>
                        <div style='font-size:0.75rem; color:#6B7280;'>Upside/Downside</div>
                        <div style='font-weight:600;
                                    color:{"#10B981" if upside > 0 else "#EF4444"};'>
                            {upside:+.1f}%
                        </div>
                    </div>
                    <div>
                        <div style='font-size:0.75rem; color:#6B7280;'>Margin of Safety</div>
                        <div style='font-weight:600;
                                    color:{"#10B981" if mos > 0 else "#EF4444"};'>
                            {mos:+.1f}%
                        </div>
                    </div>
                    <div>
                        <div style='font-size:0.75rem; color:#6B7280;'>Bull Case</div>
                        <div style='font-weight:600;'>${dcf['bull_case']:,.2f}</div>
                    </div>
                    <div>
                        <div style='font-size:0.75rem; color:#6B7280;'>Bear Case</div>
                        <div style='font-weight:600;'>${dcf['bear_case']:,.2f}</div>
                    </div>
                </div>
                <hr class='divider'>
                <div style='font-size:0.78rem; color:#6B7280;'>
                    Assumptions: {discount*100:.1f}% discount ·
                    {terminal*100:.1f}% terminal growth ·
                    {years}Y projection
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown("**🏢 Comparable Companies**")
    col_l, col_r = st.columns([1.5, 1])

    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        metric_choice = st.selectbox(
            "Compare by",
            ["P/E","P/B","EV/EBITDA","Net Margin","ROE"],
            label_visibility="collapsed"
        )
        st.plotly_chart(comps_chart(comps, metric_choice),
                        use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**Full Comps Table**")
        display_cols = ["P/E","P/B","EV/EBITDA","Net Margin","ROE","Valuation Score"]
        available    = [c for c in display_cols if c in comps.columns]
        st.dataframe(
            comps[available].style.format(
                {c: "{:.2f}" for c in available if c != "Valuation Score"}
            ).background_gradient(
                subset=["Valuation Score"], cmap="RdYlGn"
            ),
            use_container_width=True, height=260
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    verdict_color = {
        "STRONG BUY":  ("#D1FAE5","#065F46"),
        "BUY":         ("#D1FAE5","#065F46"),
        "HOLD":        ("#FEF3C7","#92400E"),
        "SELL":        ("#FEE2E2","#991B1B"),
        "STRONG SELL": ("#FEE2E2","#991B1B"),
    }.get(verdict['verdict'], ("#F3F4F6","#1A1A1A"))

    st.markdown(f"""
        <div class='section-card'
             style='background:{verdict_color[0]}; border:1px solid {verdict_color[1]}20;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <div style='font-size:0.78rem; color:{verdict_color[1]};
                                text-transform:uppercase; letter-spacing:0.05em;
                                font-weight:600;'>
                        Investment Verdict · {horizon} · {risk} Risk
                    </div>
                    <div style='font-size:2rem; font-weight:800;
                                color:{verdict_color[1]}; margin-top:0.3rem;'>
                        {verdict['verdict']}
                    </div>
                </div>
                <div style='text-align:right;'>
                    <div style='font-size:0.78rem; color:{verdict_color[1]}; font-weight:600;'>
                        CONFIDENCE
                    </div>
                    <div style='font-size:2rem; font-weight:800; color:{verdict_color[1]};'>
                        {verdict['confidence']}
                    </div>
                </div>
            </div>
            <hr style='border-color:{verdict_color[1]}30; margin:1rem 0;'>
            <div style='font-size:0.88rem; color:{verdict_color[1]};'>
                {'<br>'.join([f"→ {r}" for r in verdict['reasoning']])}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    report = {
        "Ticker": ticker, "Company": co.get('Name'),
        "Sector": co.get('Sector'), "Verdict": verdict['verdict'],
        "Confidence": verdict['confidence'],
        "Current Price": dcf['current_price'],
        "Intrinsic Value": dcf['intrinsic_value'],
        "Upside/Downside": f"{dcf['upside_downside']}%",
        **{f"Val_{k}": v for k,v in fund['valuation'].items()},
        **{f"Prof_{k}": v for k,v in fund['profitability'].items()},
    }
    st.download_button(
        "⬇️  Download Full Report CSV",
        pd.DataFrame([report]).to_csv(index=False).encode(),
        file_name=f"{ticker}_equity_report.csv",
        mime="text/csv"
    )

# ════════════════════════════════════════════════
    # ── PROPRIETARY ANALYSIS ──
    # ════════════════════════════════════════════════
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("**🔬 Proprietary Analysis Engine**")

    from equity.proprietary_ratios import compute_all_ratios
    from equity.ratio_scorer import get_scored_ratios, bqm_scores

    sector = fund['company'].get('Sector', 'Default') or 'Default'

    with st.spinner("Computing proprietary ratios..."):
        all_r  = compute_all_ratios(ticker)
        scored = get_scored_ratios(ticker, sector)
        bqm    = bqm_scores(all_r)

    # ── Business Quality Matrix ──
    col_bqm, col_quad = st.columns([1.4, 1])

    with col_bqm:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)

        # Build the 2×2 quadrant chart
        fig_bqm = go.Figure()

        # Background quadrants
        quadrant_config = [
            (50, 100, 50, 100, "#10B981", "Capital Compounder"),
            (0,  50,  50, 100, "#F59E0B", "Zombie Business"),
            (50, 100, 0,  50,  "#3B82F6", "Growth at All Costs"),
            (0,  50,  0,  50,  "#EF4444", "Value Trap"),
        ]
        for x0, x1, y0, y1, color, label in quadrant_config:
            fig_bqm.add_shape(
                type="rect",
                x0=x0, x1=x1, y0=y0, y1=y1,
                fillcolor=color, opacity=0.08, line_width=0
            )
            fig_bqm.add_annotation(
                x=(x0+x1)/2, y=(y0+y1)/2,
                text=label,
                font=dict(size=10, color=color),
                showarrow=False, opacity=0.5
            )

        # Axis lines
        fig_bqm.add_hline(y=50, line_color="#6B7280",
                           line_dash="dot", line_width=1)
        fig_bqm.add_vline(x=50, line_color="#6B7280",
                           line_dash="dot", line_width=1)

        # Company dot
        fig_bqm.add_trace(go.Scatter(
            x=[bqm['capital_efficiency']],
            y=[bqm['earnings_quality']],
            mode='markers+text',
            text=[ticker],
            textposition='top center',
            textfont=dict(size=12, color='#1A1A1A'),
            marker=dict(
                size=18,
                color=bqm['quadrant_color'],
                line=dict(color='white', width=2),
                symbol='star'
            ),
            hovertemplate=(
                f"<b>{ticker}</b><br>"
                f"Capital Efficiency: {bqm['capital_efficiency']}<br>"
                f"Earnings Quality: {bqm['earnings_quality']}<br>"
                f"Quadrant: {bqm['quadrant']}<extra></extra>"
            )
        ))

        fig_bqm.update_layout(
            height=340,
            title="Business Quality Matrix",
            xaxis=dict(
                title="Capital Efficiency →",
                range=[0, 100], showgrid=False,
                color='#6B7280'
            ),
            yaxis=dict(
                title="↑ Earnings Quality",
                range=[0, 100], showgrid=False,
                color='#6B7280'
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=40, b=0),
            font=dict(family="Inter, sans-serif"),
            showlegend=False
        )
        st.plotly_chart(fig_bqm, use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_quad:
        eq  = bqm['earnings_quality']
        ce  = bqm['capital_efficiency']
        qc  = bqm['quadrant_color']
        qn  = bqm['quadrant']

        quadrant_desc = {
            "Capital Compounder":  "High quality earnings backed by real cash flow, deployed efficiently above cost of capital. Rare and valuable — hold.",
            "Zombie Business":     "Real profits but capital is deployed below its cost. Management may be hoarding cash or making poor allocation decisions.",
            "Growth at All Costs": "Capital is working hard but earnings quality is low — growth may be fuelled by aggressive accounting or unsustainable spending.",
            "Value Trap":          "Low earnings quality and poor capital efficiency. Cheap for a reason — avoid until fundamentals improve.",
        }

        st.markdown(f"""
            <div class='section-card'
                 style='background:{qc}12;
                        border:2px solid {qc}30;
                        height:340px;
                        display:flex; flex-direction:column;
                        justify-content:center;'>
                <div style='font-size:0.72rem; color:{qc};
                            text-transform:uppercase;
                            letter-spacing:0.06em; font-weight:600;'>
                    Business Quality Quadrant
                </div>
                <div style='font-size:1.6rem; font-weight:800;
                            color:{qc}; margin:0.5rem 0;'>
                    {qn}
                </div>
                <div style='font-size:0.85rem; color:#374151;
                            line-height:1.6; margin-bottom:1.2rem;'>
                    {quadrant_desc.get(qn, '')}
                </div>
                <hr style='border-color:{qc}20; margin:0.5rem 0;'>
                <div style='display:flex; gap:1.5rem; margin-top:0.5rem;'>
                    <div>
                        <div style='font-size:0.72rem; color:{qc};'>
                            Earnings Quality
                        </div>
                        <div style='font-size:1.4rem; font-weight:700;
                                    color:{qc};'>{eq:.0f}/100</div>
                    </div>
                    <div>
                        <div style='font-size:0.72rem; color:{qc};'>
                            Capital Efficiency
                        </div>
                        <div style='font-size:1.4rem; font-weight:700;
                                    color:{qc};'>{ce:.0f}/100</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── 2 Green / 2 Neutral / 2 Red Ratio Cards ──
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style='font-size:0.85rem; color:#6B7280; margin-bottom:1rem;'>
            Industry-calibrated ratios for
            <b style='color:#1A1A1A;'>{sector}</b> ·
            Ranked by relative strength within sector peers
        </div>
    """, unsafe_allow_html=True)

    bucket_config = [
        ("green",   "✅ Strengths",  "#10B981", "#D1FAE5", "#065F46"),
        ("neutral", "⚠️ Watch",      "#F59E0B", "#FEF3C7", "#92400E"),
        ("red",     "❌ Concerns",   "#EF4444", "#FEE2E2", "#991B1B"),
    ]

    cols = st.columns(3)
    for col, (bucket, label, color, bg, fg) in zip(cols, bucket_config):
        ratios = scored[bucket]
        with col:
            st.markdown(f"""
                <div style='font-size:0.8rem; font-weight:700;
                            color:{fg}; margin-bottom:0.6rem;
                            padding:0.3rem 0.8rem;
                            background:{bg}; border-radius:20px;
                            display:inline-block;'>
                    {label}
                </div>
            """, unsafe_allow_html=True)

            for r in ratios:
                st.markdown(f"""
                    <div class='metric-card'
                         style='border-left:4px solid {color};
                                margin-bottom:0.8rem;'>
                        <div class='label'>{r['name']}</div>
                        <div class='value'
                             style='color:{color};
                                    font-size:1.4rem;'>
                            {r['display']}
                        </div>
                        <div style='font-size:0.78rem; color:#374151;
                                    margin-top:0.4rem; line-height:1.5;'>
                            {r['desc']}
                        </div>
                        <div style='font-size:0.72rem; color:#6B7280;
                                    margin-top:0.3rem; font-style:italic;'>
                            💡 {r['pitfall']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)