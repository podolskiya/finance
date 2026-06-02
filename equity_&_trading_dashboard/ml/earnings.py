# ml/earnings.py
import os
import re
import json
import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import anthropic

# ── SEC EDGAR Headers (required by SEC) ──────────────
EDGAR_HEADERS = {
    "User-Agent": "TradeSmart Pro research@tradesmart.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}


def get_earnings_history(ticker: str) -> pd.DataFrame:
    """Fetch historical EPS and revenue from yfinance."""
    stock = yf.Ticker(ticker)
    try:
        earnings = stock.earnings_history
        if earnings is not None and not earnings.empty:
            return earnings
    except:
        pass
    try:
        cal = stock.calendar
        if cal is not None:
            return pd.DataFrame([cal])
    except:
        pass
    return pd.DataFrame()


def get_earnings_estimates(ticker: str) -> dict:
    """Fetch analyst estimates and guidance."""
    stock = yf.Ticker(ticker)
    info  = stock.info
    return {
        "eps_forward":        info.get("forwardEps"),
        "eps_ttm":            info.get("trailingEps"),
        "revenue_estimate":   info.get("revenueEstimate"),
        "earnings_growth":    info.get("earningsGrowth"),
        "revenue_growth":     info.get("revenueGrowth"),
        "analyst_count":      info.get("numberOfAnalystOpinions"),
        "target_mean":        info.get("targetMeanPrice"),
        "target_high":        info.get("targetHighPrice"),
        "target_low":         info.get("targetLowPrice"),
        "recommendation":     info.get("recommendationKey"),
    }


def get_sec_cik(ticker: str) -> str | None:
    """Get SEC CIK number for a ticker."""
    try:
        url  = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=10)
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"]).zfill(10)
    except:
        pass
    return None


def get_recent_filings(ticker: str,
                        form_type: str = "10-K",
                        n: int = 3) -> list:
    """
    Fetch recent SEC filings metadata for a ticker.
    Supports 10-K (annual), 10-Q (quarterly), 8-K (events).
    """
    cik = get_sec_cik(ticker)
    if not cik:
        return []

    try:
        url  = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=10)
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form",        [])
        dates   = filings.get("filingDate",  [])
        accnums = filings.get("accessionNumber", [])
        descs   = filings.get("primaryDocument", [])

        results = []
        for form, date, acc, doc in zip(forms, dates, accnums, descs):
            if form == form_type and len(results) < n:
                acc_fmt = acc.replace("-", "")
                results.append({
                    "form":     form,
                    "date":     date,
                    "accession": acc,
                    "url": (f"https://www.sec.gov/Archives/edgar/full-index/"
                            f"archives/{cik}/{acc_fmt}/{doc}")
                })
        return results
    except:
        return []


def fetch_filing_text(url: str,
                       max_chars: int = 8000) -> str:
    """
    Fetch and clean SEC filing text.
    Strips HTML tags, excessive whitespace, boilerplate.
    """
    try:
        resp = requests.get(
            url, headers={
                "User-Agent": "TradeSmart Pro research@tradesmart.com"
            },
            timeout=15
        )
        text = resp.text

        # Strip HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        # Remove boilerplate headers
        text = re.sub(
            r'UNITED STATES SECURITIES.*?EXCHANGE ACT',
            '', text, flags=re.DOTALL | re.IGNORECASE
        )

        # Take the most informative middle section
        start = max(0, len(text)//4)
        return text[start:start + max_chars].strip()
    except:
        return ""


def get_recent_news_text(ticker: str,
                          n: int = 15) -> str:
    """Fetch recent news headlines + summaries for context."""
    stock = yf.Ticker(ticker)
    news  = stock.news or []
    lines = []
    for item in news[:n]:
        try:
            content = item.get('content', {})
            title   = content.get('title', '')
            summary = content.get('summary', '')
            date    = content.get('pubDate', '')[:10]
            if title:
                lines.append(f"[{date}] {title}. {summary[:200]}")
        except:
            continue
    return "\n".join(lines)


def get_key_financials(ticker: str) -> str:
    """Build a concise financial summary string."""
    stock = yf.Ticker(ticker)
    info  = stock.info

    def s(key, fmt=""):
        v = info.get(key)
        if v is None:
            return "N/A"
        if fmt == "pct":
            return f"{v*100:.1f}%"
        if fmt == "bn":
            return f"${v/1e9:.1f}B"
        if fmt == "x":
            return f"{v:.1f}x"
        return str(round(v, 2))

    return f"""
COMPANY:   {info.get('longName', ticker)} ({ticker})
SECTOR:    {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}
PRICE:     ${info.get('currentPrice', 'N/A')}
MKT CAP:   {s('marketCap', 'bn')}

VALUATION:
  P/E:       {s('trailingPE', 'x')}
  Fwd P/E:   {s('forwardPE', 'x')}
  EV/EBITDA: {s('enterpriseToEbitda', 'x')}
  P/B:       {s('priceToBook', 'x')}

PROFITABILITY:
  Gross Margin: {s('grossMargins', 'pct')}
  Net Margin:   {s('profitMargins', 'pct')}
  ROE:          {s('returnOnEquity', 'pct')}

GROWTH:
  Revenue Growth:  {s('revenueGrowth', 'pct')}
  Earnings Growth: {s('earningsGrowth', 'pct')}

HEALTH:
  Cash:        {s('totalCash', 'bn')}
  Debt:        {s('totalDebt', 'bn')}
  Debt/Equity: {s('debtToEquity')}

ANALYST CONSENSUS:
  Target:         ${s('targetMeanPrice')}
  Recommendation: {info.get('recommendationKey', 'N/A').upper()}
  # Analysts:     {s('numberOfAnalystOpinions')}
""".strip()


# ── Claude Analysis ───────────────────────────────────
def analyse_with_claude(
    ticker:       str,
    financials:   str,
    news_text:    str,
    filing_text:  str,
    estimates:    dict,
    horizon:      str = "Medium (3-6M)",
    risk_profile: str = "Moderate",
    api_key:      str = None
) -> dict:
    """
    Send all gathered data to Claude for deep analysis.
    Returns structured JSON with verdict, thesis, risks, catalysts.
    """
    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    )

    prompt = f"""
You are a senior equity research analyst at a top-tier investment bank.
Analyse the following data for {ticker} and provide a structured
investment report for a {horizon} horizon investor with {risk_profile} risk tolerance.

═══ FINANCIAL SNAPSHOT ═══
{financials}

═══ ANALYST ESTIMATES ═══
Forward EPS:      {estimates.get('eps_forward', 'N/A')}
EPS TTM:          {estimates.get('eps_ttm', 'N/A')}
Revenue Growth:   {estimates.get('revenue_growth', 'N/A')}
Price Target:     ${estimates.get('target_mean', 'N/A')}
High/Low Target:  ${estimates.get('target_high', 'N/A')} / ${estimates.get('target_low', 'N/A')}
Recommendation:   {estimates.get('recommendation', 'N/A')}

═══ RECENT NEWS ═══
{news_text[:2000] if news_text else 'No recent news available.'}

═══ SEC FILING EXCERPT ═══
{filing_text[:3000] if filing_text else 'No filing text available.'}

═══ YOUR TASK ═══
Return ONLY a valid JSON object with this exact structure:

{{
  "verdict": "STRONG BUY | BUY | HOLD | SELL | STRONG SELL",
  "confidence": 75,
  "price_target": 195.00,
  "upside": 12.5,
  "investment_thesis": "2-3 sentence core thesis",
  "bull_case": "Best case scenario in 2-3 sentences",
  "bear_case": "Worst case scenario in 2-3 sentences",
  "key_strengths": ["strength 1", "strength 2", "strength 3"],
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "catalysts": ["near-term catalyst 1", "catalyst 2"],
  "management_tone": "Bullish | Cautious | Neutral | Defensive",
  "earnings_quality": "High | Medium | Low",
  "valuation_assessment": "Expensive | Fair | Cheap",
  "moat_strength": "Wide | Narrow | None",
  "recommended_action": "One clear actionable sentence",
  "key_metrics_to_watch": ["metric 1", "metric 2", "metric 3"]
}}

Be direct, data-driven, and institutional in tone.
Do not include any text outside the JSON object.
""".strip()

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw  = message.content[0].text.strip()
        raw  = re.sub(r'^```json\s*', '', raw)
        raw  = re.sub(r'\s*```$',     '', raw)
        return json.loads(raw)

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}", "raw": raw}
    except Exception as e:
        return {"error": str(e)}


def full_earnings_analysis(
    ticker:       str,
    horizon:      str  = "Medium (3-6M)",
    risk_profile: str  = "Moderate",
    api_key:      str  = None,
    progress_cb         = None
) -> dict:
    """
    Orchestrate the full earnings analysis pipeline.
    """
    def cb(step, msg):
        if progress_cb:
            progress_cb(step, msg)

    cb(10, "Fetching financial snapshot...")
    financials = get_key_financials(ticker)
    estimates  = get_earnings_estimates(ticker)

    cb(25, "Fetching recent news...")
    news_text  = get_recent_news_text(ticker)

    cb(40, "Fetching SEC filings...")
    filings    = get_recent_filings(ticker, "10-K", n=1)
    if not filings:
        filings = get_recent_filings(ticker, "10-Q", n=1)

    filing_text = ""
    if filings:
        cb(55, f"Reading {filings[0]['form']} filing...")
        filing_text = fetch_filing_text(filings[0]['url'])

    cb(70, "Sending to Claude for analysis...")
    analysis = analyse_with_claude(
        ticker, financials, news_text,
        filing_text, estimates,
        horizon, risk_profile, api_key
    )

    cb(95, "Finalising report...")
    return {
        "ticker":       ticker,
        "analysis":     analysis,
        "financials":   financials,
        "estimates":    estimates,
        "news":         news_text,
        "filings":      filings,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }