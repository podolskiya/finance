# app/pages/model_upload.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
from app.style import metric_card
from equity.model_parser import (load_workbook_sheets, build_full_model,
                                  build_canonical_from_mapping,
                                  classify_periods, CANONICAL_ITEMS)
from equity.model_analyser import (compute_metrics, detect_red_flags,
                                    ai_model_review, build_reality_check)

CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, color='#6B7280'),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#6B7280'),
    hovermode="x unified",
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)

SEVERITY_STYLE = {
    "error":   ("#FEE2E2", "#991B1B", "❌"),
    "warning": ("#FEF3C7", "#92400E", "⚠️"),
    "info":    ("#DBEAFE", "#1E40AF", "ℹ️"),
}


def line_chart(series_dict: dict, title: str, ticksuffix: str = "") -> go.Figure:
    fig = go.Figure()
    colors = ['#1A1A1A', '#10B981', '#3B82F6', '#F59E0B']
    for (name, series), color in zip(series_dict.items(), colors):
        s = series.dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values,
            name=name, mode='lines+markers',
            line=dict(color=color, width=2)
        ))
    fig.update_layout(height=280, title=title,
                      legend=dict(orientation="h"), **CHART_THEME)
    if ticksuffix:
        fig.update_yaxes(ticksuffix=ticksuffix)
    return fig


def show():
    st.markdown("""
        <div class='page-subtitle'>
            Upload your financial model · Automatic line-item mapping ·
            Sanity checks · AI-powered assumption review
        </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📁 Model Upload**")

        uploaded = st.file_uploader(
            "Excel Model (.xlsx)", type=["xlsx", "xls"]
        )

        st.markdown("**🔍 Reality Check (optional)**")
        ticker = st.text_input(
            "Ticker for live comparison", "",
            help="Compares model's historical figures vs live market data"
        ).upper().strip()

        st.markdown("**🤖 AI Review**")
        api_key_input = st.text_input(
            "Anthropic API Key", type="password",
            value=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if api_key_input:
            os.environ["ANTHROPIC_API_KEY"] = api_key_input

        st.markdown("---")
        st.markdown("""
            <div style='font-size:0.78rem; color:#888; line-height:1.7;'>
                <b>How it works:</b><br>
                1. Upload any Excel model<br>
                2. We auto-detect periods & map row
                labels to 24 standard line items<br>
                3. Review/correct the mapping<br>
                4. Get instant metrics, charts & red flags<br>
                5. Optional: Claude reviews assumption quality
            </div>
        """, unsafe_allow_html=True)

    if uploaded is None:
        st.markdown("""
            <div class='section-card' style='text-align:center; padding:4rem 2rem;'>
                <div style='font-size:2.5rem;'>📊</div>
                <div style='font-size:1.1rem; font-weight:600; margin-top:1rem;'>
                    Financial Model Analyser
                </div>
                <div style='color:#6B7280; margin-top:0.5rem;
                            max-width:480px; margin-left:auto; margin-right:auto;'>
                    Upload an Excel financial model — income statement,
                    balance sheet, cash flow, or all three across sheets.
                    We'll detect time periods, map every line item, compute
                    growth/margin/leverage metrics, run automated sanity
                    checks, and optionally have Claude review your
                    assumptions for quality.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # ── Parse ──
    progress = st.progress(0, text="Reading workbook...")
    try:
        sheets = load_workbook_sheets(uploaded)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    progress.progress(30, text="Detecting periods & mapping line items...")
    canonical, combined, period_cols = build_full_model(sheets)

    if canonical.empty:
        st.error("Could not detect a usable structure. Make sure your "
                "model has a row of years (e.g. 2021, 2022, 2023E) "
                "as a header somewhere in the first 15 rows.")
        return

    progress.progress(60, text="Computing metrics...")

    # ── Sheet info ──
    st.markdown(f"""
        <div class='section-card'>
            <div style='display:flex; gap:2rem; flex-wrap:wrap;'>
                <div>
                    <div class='label'>Sheets Found</div>
                    <div class='value' style='font-size:1.3rem;'>{len(sheets)}</div>
                </div>
                <div>
                    <div class='label'>Rows Parsed</div>
                    <div class='value' style='font-size:1.3rem;'>{len(combined)}</div>
                </div>
                <div>
                    <div class='label'>Periods Detected</div>
                    <div class='value' style='font-size:1.3rem;'>{len(period_cols)}</div>
                </div>
                <div>
                    <div class='label'>Items Mapped</div>
                    <div class='value' style='font-size:1.3rem;'>
                        {combined['Mapped Item'].notna().sum()} / {len(combined)}
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Mapping Review ──
    st.markdown("**🗂️ Review & Correct Line Item Mapping**")
    st.markdown("""
        <div style='font-size:0.82rem; color:#6B7280; margin-bottom:0.5rem;'>
            Each row label was auto-matched to a standard financial line
            item. Correct any mismatches using the dropdown — the
            canonical table below updates automatically.
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    edited = st.data_editor(
        combined[['Label', 'Mapped Item', 'Confidence', 'Sheet']],
        column_config={
            "Label":       st.column_config.TextColumn(disabled=True),
            "Sheet":       st.column_config.TextColumn(disabled=True),
            "Confidence":  st.column_config.NumberColumn(format="%.2f", disabled=True),
            "Mapped Item": st.column_config.SelectboxColumn(
                options=[None] + list(CANONICAL_ITEMS.keys())
            ),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        height=300,
        key="mapping_editor"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Rebuild canonical table from edited mapping
    combined_edited = combined.copy()
    combined_edited['Mapped Item'] = edited['Mapped Item'].values
    canonical = build_canonical_from_mapping(combined_edited, period_cols)

    if canonical.empty:
        st.warning("No line items mapped — adjust the mapping above to continue.")
        return

    # ── Period Classification ──
    st.markdown("**📅 Historical vs Projected Periods**")
    auto_hist, auto_proj = classify_periods(period_cols)

    col1, col2 = st.columns(2)
    with col1:
        historical = st.multiselect(
            "Historical periods", period_cols, default=auto_hist
        )
    with col2:
        projected = st.multiselect(
            "Projected periods", period_cols,
            default=[p for p in auto_proj if p not in historical]
        )

    progress.progress(75, text="Running analysis...")
    metrics = compute_metrics(canonical)
    flags   = detect_red_flags(canonical, metrics, historical, projected)
    progress.progress(100, text="Done!")

    # ── Canonical Table ──
    st.markdown("**📋 Canonical Financial Model**")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.dataframe(
        canonical.style.format("{:,.1f}", na_rep="—"),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Summary Cards ──
    cols = st.columns(4)
    with cols[0]:
        cagr = metrics.get('revenue_cagr')
        st.markdown(metric_card(
            "Revenue CAGR",
            f"{cagr:.1f}%" if cagr is not None else "N/A",
            positive=(cagr or 0) > 0
        ), unsafe_allow_html=True)
    with cols[1]:
        if 'gross_margin' in metrics:
            v = metrics['gross_margin'].dropna()
            st.markdown(metric_card(
                "Latest Gross Margin",
                f"{v.iloc[-1]:.1f}%" if len(v) else "N/A"
            ), unsafe_allow_html=True)
        else:
            st.markdown(metric_card("Gross Margin", "N/A"), unsafe_allow_html=True)
    with cols[2]:
        if 'fcf' in metrics:
            v = metrics['fcf'].dropna()
            st.markdown(metric_card(
                "Latest FCF",
                f"${v.iloc[-1]:,.0f}" if len(v) else "N/A",
                positive=(v.iloc[-1] > 0) if len(v) else None
            ), unsafe_allow_html=True)
        else:
            st.markdown(metric_card("FCF", "N/A"), unsafe_allow_html=True)
    with cols[3]:
        if 'debt_equity' in metrics:
            v = metrics['debt_equity'].dropna()
            st.markdown(metric_card(
                "Latest Debt/Equity",
                f"{v.iloc[-1]:.2f}x" if len(v) else "N/A"
            ), unsafe_allow_html=True)
        else:
            st.markdown(metric_card("Debt/Equity", "N/A"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Charts ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if 'revenue' in metrics:
            st.plotly_chart(
                line_chart({"Revenue": metrics['revenue']}, "Revenue ($)"),
                use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.info("Revenue not mapped.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        margin_series = {
            k.replace('_', ' ').title(): v
            for k, v in metrics.items()
            if k.endswith('_margin')
        }
        if margin_series:
            st.plotly_chart(
                line_chart(margin_series, "Margins (%)", ticksuffix="%"),
                use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.info("No margin data available.")
        st.markdown("</div>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if 'revenue_growth' in metrics:
            st.plotly_chart(
                line_chart({"Revenue Growth": metrics['revenue_growth']},
                          "YoY Growth (%)", ticksuffix="%"),
                use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.info("Growth data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if 'fcf' in metrics:
            st.plotly_chart(
                line_chart({"Free Cash Flow": metrics['fcf']}, "FCF ($)"),
                use_container_width=True, config={"displayModeBar": False}
            )
        elif 'debt_equity' in metrics:
            st.plotly_chart(
                line_chart({"Debt/Equity": metrics['debt_equity']}, "Leverage (x)"),
                use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.info("FCF / leverage data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Red Flags ──
    st.markdown("**🚩 Automated Sanity Checks**")
    for f in flags:
        bg, fg, icon = SEVERITY_STYLE.get(f['severity'], SEVERITY_STYLE['info'])
        st.markdown(f"""
            <div class='section-card' style='background:{bg}; border:none;'>
                <div style='font-weight:700; color:{fg}; margin-bottom:0.3rem;'>
                    {icon} {f['title']}
                </div>
                <div style='font-size:0.85rem; color:{fg};'>
                    {f['detail']}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── AI Review ──
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown("**🤖 AI Model Review**")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.info("Enter your Anthropic API key in the sidebar to get "
               "Claude's qualitative review of your model's assumptions.")
    else:
        if st.button("▶  Generate AI Review", use_container_width=False):
            with st.spinner("Claude is reviewing your model..."):
                reality = build_reality_check(ticker) if ticker else None
                review  = ai_model_review(
                    canonical, metrics, flags,
                    historical, projected,
                    reality_check=reality,
                    api_key=os.environ.get("ANTHROPIC_API_KEY")
                )

            if "error" in review:
                st.error(f"AI review error: {review['error']}")
            else:
                qual_colors = {
                    "Conservative": ("#D1FAE5","#065F46"),
                    "Realistic":    ("#DBEAFE","#1E40AF"),
                    "Aggressive":   ("#FEF3C7","#92400E"),
                    "Inconsistent": ("#FEE2E2","#991B1B"),
                }
                qc = qual_colors.get(review.get('assumption_quality'),
                                     ("#F3F4F6","#374151"))

                st.markdown(f"""
                    <div class='section-card'
                         style='background:{qc[0]}; border:none;'>
                        <div style='display:flex; justify-content:space-between;
                                    align-items:flex-start; flex-wrap:wrap; gap:1rem;'>
                            <div style='flex:1; min-width:250px;'>
                                <div style='font-size:0.75rem; color:{qc[1]};
                                            text-transform:uppercase; font-weight:600;
                                            letter-spacing:0.05em;'>
                                    Assumption Quality
                                </div>
                                <div style='font-size:1.6rem; font-weight:800;
                                            color:{qc[1]}; margin:0.2rem 0 0.8rem 0;'>
                                    {review.get('assumption_quality','N/A')}
                                </div>
                                <div style='font-size:0.9rem; color:{qc[1]};
                                            line-height:1.6; font-style:italic;'>
                                    "{review.get('overall_assessment','')}"
                                </div>
                            </div>
                            <div style='text-align:center;'>
                                <div style='font-size:0.72rem; color:{qc[1]};'>
                                    Confidence in Projections
                                </div>
                                <div style='font-size:2rem; font-weight:800;
                                            color:{qc[1]};'>
                                    {review.get('confidence_in_projections','N/A')}%
                                </div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                        <div class='section-card' style='border-top:3px solid #10B981;'>
                            <div style='font-weight:700; color:#10B981; margin-bottom:0.6rem;'>
                                💪 Strengths
                            </div>
                            {''.join(f"<div style='font-size:0.85rem; margin-bottom:0.4rem;'>→ {s}</div>" for s in review.get('strengths',[]))}
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                        <div class='section-card' style='border-top:3px solid #EF4444;'>
                            <div style='font-weight:700; color:#EF4444; margin-bottom:0.6rem;'>
                                ⚠️ Concerns
                            </div>
                            {''.join(f"<div style='font-size:0.85rem; margin-bottom:0.4rem;'>→ {s}</div>" for s in review.get('concerns',[]))}
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                    <div class='section-card'>
                        <div style='font-weight:700; margin-bottom:0.6rem;'>
                            🔑 Key Assumptions
                        </div>
                        {''.join(f"<div style='font-size:0.85rem; margin-bottom:0.5rem;'>• {s}</div>" for s in review.get('key_assumptions',[]))}
                    </div>
                """, unsafe_allow_html=True)

                if review.get('missing_items'):
                    st.markdown(f"""
                        <div class='section-card'>
                            <div style='font-weight:700; margin-bottom:0.6rem;'>
                                📭 Items Not Found in Model
                            </div>
                            <div style='display:flex; gap:0.6rem; flex-wrap:wrap;'>
                                {''.join(f'<span style="background:#F0F2F5; border-radius:20px; padding:0.3rem 0.8rem; font-size:0.8rem;">{m}</span>' for m in review.get('missing_items',[]))}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                if review.get('reality_check'):
                    st.markdown(f"""
                        <div class='section-card'>
                            <div style='font-weight:700; margin-bottom:0.6rem;'>
                                🔍 Reality Check
                            </div>
                            <div style='font-size:0.85rem; line-height:1.6;'>
                                {review['reality_check']}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                if review.get('questions_for_preparer'):
                    st.markdown(f"""
                        <div class='section-card'
                             style='background:#1A1A1A;'>
                            <div style='font-weight:700; color:#FFFFFF; margin-bottom:0.6rem;'>
                                ❓ Questions for the Model's Preparer
                            </div>
                            {''.join(f"<div style='font-size:0.85rem; color:#CCCCCC; margin-bottom:0.4rem;'>→ {q}</div>" for q in review.get('questions_for_preparer',[]))}
                        </div>
                    """, unsafe_allow_html=True)

                import json
                st.download_button(
                    "⬇️  Download AI Review JSON",
                    json.dumps(review, indent=2).encode(),
                    file_name="model_ai_review.json",
                    mime="application/json"
                )

    # ── Downloads ──
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️  Download Canonical Model CSV",
            canonical.to_csv().encode(),
            file_name="canonical_model.csv", mime="text/csv"
        )
    with col2:
        st.download_button(
            "⬇️  Download Mapping CSV",
            combined_edited.to_csv(index=False).encode(),
            file_name="line_item_mapping.csv", mime="text/csv"
        )