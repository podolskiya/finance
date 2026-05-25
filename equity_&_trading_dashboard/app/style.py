# app/style.py

THEME_CSS = """
<style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #F0F2F5;
        color: #1A1A1A;
    }

    /* ── Hide Streamlit default UI ── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 2rem 2.5rem 2rem 2.5rem;
        max-width: 1400px;
    }

    /* ── Sidebar Base ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebar"] .stSidebar,
    section[data-testid="stSidebar"] {
        background-color: #1A1A1A !important;
    }

    /* ── All Sidebar Text ── */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] small {
        color: #CCCCCC !important;
    }

    /* ── Sidebar Inputs (text, number) ── */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] input[type="text"],
    [data-testid="stSidebar"] input[type="number"] {
        background-color: #2A2A2A !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
        border-radius: 8px !important;
    }

    /* ── Date Inputs ── */
    [data-testid="stSidebar"] input[type="date"],
    [data-testid="stSidebar"] .stDateInput input {
        background-color: #2A2A2A !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
        border-radius: 8px !important;
        color-scheme: dark !important;
    }

    /* ── Selectbox ── */
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #2A2A2A !important;
        border: 1px solid #444444 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="select"] div {
        color: #FFFFFF !important;
        background-color: transparent !important;
    }

    /* ── Dropdown Menu (the popup list) ── */
    [data-baseweb="popover"],
    [data-baseweb="menu"] {
        background-color: #2A2A2A !important;
        border: 1px solid #444 !important;
    }
    [data-baseweb="menu"] li,
    [data-baseweb="menu"] ul {
        background-color: #2A2A2A !important;
        color: #FFFFFF !important;
    }
    [data-baseweb="menu"] li:hover {
        background-color: #3A3A3A !important;
    }

    /* ── Slider ── */
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stSlider div[data-testid="stTickBarMin"],
    [data-testid="stSidebar"] .stSlider div[data-testid="stTickBarMax"] {
        color: #888888 !important;
    }

    /* ── Number Input Buttons ── */
    [data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #2A2A2A !important;
        border-color: #444 !important;
        color: #FFFFFF !important;
    }

    /* ── Sidebar Button ── */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #FFFFFF !important;
        color: #1A1A1A !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #E5E5E5 !important;
    }

    /* ── Dividers ── */
    [data-testid="stSidebar"] hr {
        border-color: #333333 !important;
    }

    /* ── Radio buttons ── */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.2rem !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 0.4rem 0.6rem !important;
        border-radius: 6px !important;
        transition: background 0.15s !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #2A2A2A !important;
        color: #FFFFFF !important;
    }

    /* ── Checkbox ── */
    [data-testid="stSidebar"] .stCheckbox span {
        border-color: #555 !important;
    }

    /* ── Metric Cards ── */
    .metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
        border: 1px solid #F0F0F0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.10);
    }
    .metric-card .label {
        font-size: 0.78rem;
        font-weight: 500;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .metric-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1A1A1A;
        line-height: 1.2;
    }
    .metric-card .sub {
        font-size: 0.78rem;
        color: #6B7280;
        margin-top: 0.3rem;
    }
    .metric-card .positive { color: #10B981; }
    .metric-card .negative { color: #EF4444; }

    /* ── Section Card ── */
    .section-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1.6rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
        border: 1px solid #F0F0F0;
        margin-bottom: 1.2rem;
    }

    /* ── Page Title ── */
    .page-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 0.2rem;
    }
    .page-subtitle {
        font-size: 0.9rem;
        color: #6B7280;
        margin-bottom: 1.8rem;
    }

    /* ── Verdict Badge ── */
    .verdict-badge {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 50px;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: 0.03em;
    }
    .verdict-buy       { background: #D1FAE5; color: #065F46; }
    .verdict-strong-buy{ background: #065F46; color: #FFFFFF; }
    .verdict-hold      { background: #FEF3C7; color: #92400E; }
    .verdict-sell      { background: #FEE2E2; color: #991B1B; }
    .verdict-strong-sell{ background: #991B1B; color: #FFFFFF; }

    /* ── Divider ── */
    .divider {
        border: none;
        border-top: 1px solid #F0F0F0;
        margin: 1rem 0;
    }

    /* ── Inputs ── */
    .stTextInput input, .stSelectbox select, .stDateInput input {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        background: #FAFAFA !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background-color: #1A1A1A;
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: background 0.2s;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #333333;
    }

    /* ── Tables ── */
    .dataframe {
        border-radius: 10px !important;
        border: none !important;
        font-size: 0.85rem !important;
    }
    .dataframe th {
        background: #F9FAFB !important;
        color: #6B7280 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.72rem !important;
        letter-spacing: 0.05em;
    }
</style>
"""


def metric_card(label: str, value: str, sub: str = "", positive: bool = None) -> str:
    """Generate a styled metric card HTML block."""
    sub_class = ""
    if positive is True:  sub_class = "positive"
    if positive is False: sub_class = "negative"
    sub_html = f'<div class="sub {sub_class}">{sub}</div>' if sub else ""
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {sub_html}
    </div>
    """


def verdict_badge(verdict: str) -> str:
    cls_map = {
        "STRONG BUY":  "verdict-strong-buy",
        "BUY":         "verdict-buy",
        "HOLD":        "verdict-hold",
        "SELL":        "verdict-sell",
        "STRONG SELL": "verdict-strong-sell",
    }
    cls = cls_map.get(verdict, "verdict-hold")
    return f'<div class="verdict-badge {cls}">{verdict}</div>'