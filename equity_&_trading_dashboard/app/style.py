# app/style.py

# app/style.py

THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important;
        color: #1A1A1A !important;
    }

    /* ── Hide default header & padding to make navbar flush ── */
    [data-testid="stHeader"] {
        display: none;
    }
    .block-container {
        padding-top: 2rem !important;
        max-width: 95% !important;
    }

    /* ── Logo Text Styling (If not using an image for the full logo) ── */
    .logo-text {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0000FF;
        letter-spacing: 0.1rem;
        margin-top: -5px;
    }

    /* ── Top Navbar Popover Triggers (The main menu links) ── */
    [data-testid="stPopover"] > button {
        background: transparent !important;
        background-color: transparent !important;
        border: 0px solid transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        min-height: 0 !important;
        height: auto !important;
    }
    
    /* 2. Format the text and strictly prevent wrapping */
    [data-testid="stPopover"] > button p,
    [data-testid="stPopover"] > button div,
    [data-testid="stPopover"] > button span {
        white-space: nowrap !important;
        color: #1A1A1A !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
        padding: 0.3rem 0.5rem !important;
    }
    
    /* 3. Handle hover states so the box doesn't magically reappear */
    [data-testid="stPopover"] > button:hover,
    [data-testid="stPopover"] > button:focus,
    [data-testid="stPopover"] > button:active {
        background: transparent !important;
        background-color: transparent !important;
        border: 0px solid transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* 4. Change ONLY the text color on hover */
    [data-testid="stPopover"] > button:hover p,
    [data-testid="stPopover"] > button:focus p,
    [data-testid="stPopover"] > button:hover div,
    [data-testid="stPopover"] > button:hover span {
        color: #0000FF !important; /* Your blue highlight */
    }

    /* ── Dropdown Menu Styling (Inside the popover) ── */
    div[data-testid="stPopover"] > button,
    div[data-testid="stPopover"] > div > button {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        min-height: 0 !important;
        height: auto !important;
        /* ── ANTI-SQUISH MAGIC ── */
        min-width: max-content !important;
        flex-shrink: 0 !important;
    }
    
    /* 2. Format the text, lock the size, and strictly prevent wrapping */
    div[data-testid="stPopover"] p,
    div[data-testid="stPopover"] span {
        white-space: nowrap !important;
        word-break: keep-all !important;
        color: #1A1A1A !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important; /* Locks font size so it doesn't get tiny */
        margin: 0 !important;
        padding: 0.2rem 0.4rem !important;
    }
    
    /* 3. Handle hover states so the box doesn't magically reappear on mobile */
    div[data-testid="stPopover"] > button:hover,
    div[data-testid="stPopover"] > button:focus,
    div[data-testid="stPopover"] > button:active,
    div[data-testid="stPopover"] > div > button:hover {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* 4. Change ONLY the text color on hover */
    div[data-testid="stPopover"] > button:hover p,
    div[data-testid="stPopover"] > button:focus p,
    div[data-testid="stPopover"] > button:hover span,
    div[data-testid="stPopover"] > button:focus span {
        color: #0000FF !important; /* Your blue highlight */
    }

    /* ── Divider below navigation ── */
    .nav-divider {
        border: none;
        border-bottom: 1px solid #F0F0F0;
        margin-top: 0.5rem;
        margin-bottom: 2rem;
    }

    /* ── General Content Styling ── */
    .page-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E5E7EB;
    }

    /* ── Top Nav Alignment & Responsive Overlap Fix (Aggressive Override) ── */

    /* 1. Force the row to behave like a true Flexbox, allowing items to wrap safely */
    [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        gap: 10px !important; 
    }

    /* 2. Strip Streamlit's strict inline percentage widths from ALL columns in this row */
    [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div {
        width: auto !important;
        min-width: max-content !important; 
        flex: 0 0 auto !important; 
        display: flex !important;
        justify-content: flex-end !important;
    }

    /* 3. Make the first column (Logo) grow to fill empty space, naturally pushing menus right */
    [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child {
        flex: 1 1 auto !important; 
        justify-content: flex-start !important;
        margin-right: auto !important;
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