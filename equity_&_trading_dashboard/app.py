import streamlit as st
import os

# --- Configuration ---
favicon_path = os.path.join("assets", "favicon.svg")

st.set_page_config(
    page_title="TradeSmart Pro",
    page_icon=favicon_path, 
    layout="wide",
    initial_sidebar_state="collapsed" # Hide the default sidebar completely
)

# Load custom CSS
from app.style import THEME_CSS
st.markdown(THEME_CSS, unsafe_allow_html=True)

# --- Session State for Navigation ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "Overview"

# --- TOP NAVIGATION BAR ---
# Adjusted ratios: Logo gets more space, menus get equal space
header_cols = st.columns([5, 1, 1, 1, 1])

with header_cols[0]:
    st.image(favicon_path, width=40) 

with header_cols[1]:
    with st.popover("STRATEGY LAB", use_container_width=True):
        if st.button("Overview", use_container_width=True): 
            st.session_state.current_page = "Overview"; st.rerun()
        if st.button("Backtester", use_container_width=True): 
            st.session_state.current_page = "Backtester"; st.rerun()
        if st.button("Walk-Forward", use_container_width=True): 
            st.session_state.current_page = "Walk-Forward"; st.rerun()

with header_cols[2]:
    with st.popover("MARKET ANALYSIS"):
        if st.button("Pairs Trading", use_container_width=True): 
            st.session_state.current_page = "Pairs Trading"; st.rerun()
        if st.button("Equity Analysis", use_container_width=True): 
            st.session_state.current_page = "Equity Analysis"; st.rerun()

with header_cols[3]:
    with st.popover("AI SIGNALS"):
        if st.button("ML Signals", use_container_width=True): 
            st.session_state.current_page = "ML Signals"; st.rerun()
        if st.button("Sentiment Signals", use_container_width=True): 
            st.session_state.current_page = "Sentiment Signals"; st.rerun()
        if st.button("Regime Detection", use_container_width=True):
            st.session_state.current_page = "Regime Detection"; st.rerun()
        if st.button("Earnings Analyser", use_container_width=True):
            st.session_state.current_page = "Earnings Analyser"; st.rerun()

with header_cols[4]:
    with st.popover("ASSETS"):
        if st.button("Portfolio", use_container_width=True): 
            st.session_state.current_page = "Portfolio"; st.rerun()
        if st.button("Live Trading", use_container_width=True):
            st.session_state.current_page = "Live Trading"; st.rerun()

st.markdown("<hr class='nav-divider'>", unsafe_allow_html=True)

# --- Page Routing ---
page_selection = st.session_state.current_page

# Display current page title for context
st.markdown(f"<h1 class='page-title'>{page_selection}</h1>", unsafe_allow_html=True)

if page_selection == "Overview":
    from app.pages import overview; overview.show()
elif page_selection == "Backtester":
    from app.pages import backtester; backtester.show()
elif page_selection == "Walk-Forward":
    from app.pages import wfo; wfo.show()
elif page_selection == "Pairs Trading":
    from app.pages import pairs; pairs.show()
elif page_selection == "Equity Analysis":
    from app.pages import equity; equity.show()
elif page_selection == "ML Signals":
    from app.pages import ml_page; ml_page.show()
elif page_selection == "Sentiment Signals":
    from app.pages import sentiment; sentiment.show()
elif page_selection == "Portfolio":
    from app.pages import portfolio; portfolio.show()
elif page_selection == "Regime Detection":
    from app.pages import regime; regime.show()
elif page_selection == "Earnings Analyser":
    from app.pages import earnings; earnings.show()
elif page_selection == "Live Trading":
    from app.pages import live_trading; live_trading.show()