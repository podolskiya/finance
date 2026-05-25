# app.py  ← root level
import streamlit as st

st.set_page_config(
    page_title="TradeSmart Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

from app.style import THEME_CSS
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ── Sidebar Navigation ──
with st.sidebar:
    st.markdown("""
        <div style='padding: 1rem 0 2rem 0;'>
            <div style='font-size:1.4rem; font-weight:700; color:#FFFFFF;'>
                📈 TradeSmart
            </div>
            <div style='font-size:0.75rem; color:#6B7280; margin-top:0.2rem;'>
                Pro Analytics Platform
            </div>
        </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["🏠  Overview",
        "⚡  Backtester",
        "🔄  Walk-Forward",      
        "🔗  Pairs Trading",
        "🏢  Equity Analysis",
        "🧠  ML Signals",
        "📰  Sentiment Signals",],
        label_visibility="collapsed"
    )
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    st.markdown("""
        <div style='font-size:0.7rem; color:#4B5563; padding-top:1rem;
                    border-top:1px solid #333;'>
            Data: Yahoo Finance<br>
            Models: TensorFlow LSTM<br>
            v1.0.0 — TradeSmart Pro
        </div>
    """, unsafe_allow_html=True)

# ── Page Routing ──
if   "Overview"        in page: from app.pages import overview;   overview.show()
elif "Backtester"      in page: from app.pages import backtester; backtester.show()
elif "Pairs Trading"   in page: from app.pages import pairs;      pairs.show()
elif "Equity Analysis" in page: from app.pages import equity;     equity.show()
elif "ML Signals"      in page: from app.pages import ml_page;    ml_page.show()
elif "Walk-Forward" in page: from app.pages import wfo; wfo.show()
elif "Sentiment" in page: from app.pages import sentiment; sentiment.show()
