# equity/comparables.py
import yfinance as yf
import pandas as pd
import numpy as np

# Sector peer groups
SECTOR_PEERS = {
    "Technology":            ["AAPL","MSFT","GOOGL","META","NVDA","AMD","INTC","CRM","ORCL"],
    "Consumer Cyclical":     ["AMZN","TSLA","NKE","MCD","SBUX","HD","TGT","BKNG"],
    "Healthcare":            ["JNJ","PFE","MRNA","ABBV","UNH","LLY","TMO","ABT"],
    "Financials":            ["JPM","BAC","GS","MS","WFC","BRK-B","V","MA"],
    "Energy":                ["XOM","CVX","COP","SLB","EOG","PXD","MPC"],
    "Communication":         ["GOOGL","META","NFLX","DIS","T","VZ","CMCSA"],
    "Industrials":           ["BA","CAT","GE","HON","UPS","FDX","LMT","RTX"],
    "Consumer Staples":      ["PG","KO","PEP","WMT","COST","CL","MDLZ"],
}

METRICS = ["trailingPE","priceToBook","priceToSalesTrailing12Months",
           "enterpriseToEbitda","profitMargins","returnOnEquity",
           "revenueGrowth","debtToEquity"]

LABELS  = ["P/E","P/B","P/S","EV/EBITDA","Net Margin","ROE","Rev Growth","D/E"]


def get_comparables(ticker: str, n_peers: int = 5) -> pd.DataFrame:
    """
    Fetch key valuation multiples for a stock and its sector peers.
    Returns a comparison table ranked by P/E.
    """
    stock   = yf.Ticker(ticker)
    sector  = stock.info.get("sector", "Technology")
    peers   = SECTOR_PEERS.get(sector, SECTOR_PEERS["Technology"])

    # Ensure target is included
    all_tickers = list(set([ticker] + peers))[:n_peers + 1]

    rows = []
    for t in all_tickers:
        try:
            info = yf.Ticker(t).info
            row  = {"Ticker": t}
            for metric, label in zip(METRICS, LABELS):
                val = info.get(metric)
                row[label] = round(val, 3) if val not in [None, float('inf')] else None
            rows.append(row)
        except:
            pass

    df = pd.DataFrame(rows).set_index("Ticker")

    # Z-score to find cheapest/richest vs peers
    numeric = df.select_dtypes(include=[float, int])
    z_scores = (numeric - numeric.mean()) / numeric.std()
    df['Valuation Score'] = -z_scores[['P/E','P/B','EV/EBITDA']].mean(axis=1).round(2)

    return df.sort_values('Valuation Score', ascending=False)


def investment_verdict(ticker: str, dcf: dict, comps: pd.DataFrame) -> dict:
    """
    Combine DCF + comparables + fundamentals into a final verdict.
    Returns: Buy / Hold / Sell with confidence and reasoning.
    """
    signals = []
    reasons = []

    # --- DCF signal ---
    mos = dcf.get("margin_of_safety", 0)
    if mos > 20:
        signals.append(2)
        reasons.append(f"DCF: {mos:.1f}% undervalued (strong buy)")
    elif mos > 0:
        signals.append(1)
        reasons.append(f"DCF: {mos:.1f}% undervalued (mild buy)")
    elif mos > -20:
        signals.append(0)
        reasons.append(f"DCF: {abs(mos):.1f}% overvalued (hold)")
    else:
        signals.append(-1)
        reasons.append(f"DCF: {abs(mos):.1f}% overvalued (sell)")

    # --- Comparables signal ---
    if ticker in comps.index:
        score = comps.loc[ticker, 'Valuation Score']
        if score > 0.5:
            signals.append(1)
            reasons.append(f"Comps: cheaper than peers (score: {score:.2f})")
        elif score < -0.5:
            signals.append(-1)
            reasons.append(f"Comps: expensive vs peers (score: {score:.2f})")
        else:
            signals.append(0)
            reasons.append(f"Comps: fairly valued vs peers (score: {score:.2f})")

    # --- Final verdict ---
    avg = np.mean(signals)
    if avg >= 1.0:
        verdict    = "STRONG BUY"
        confidence = min(95, 60 + avg * 15)
    elif avg >= 0.5:
        verdict    = "BUY"
        confidence = min(80, 55 + avg * 15)
    elif avg >= 0:
        verdict    = "HOLD"
        confidence = 50
    elif avg >= -0.5:
        verdict    = "SELL"
        confidence = min(80, 55 + abs(avg) * 15)
    else:
        verdict    = "STRONG SELL"
        confidence = min(95, 60 + abs(avg) * 15)

    return {
        "verdict":    verdict,
        "confidence": f"{round(confidence)}%",
        "reasoning":  reasons,
        "dcf_value":  dcf.get("intrinsic_value"),
        "upside":     f"{dcf.get('upside_downside', 0)}%"
    }