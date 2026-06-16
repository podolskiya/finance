# backend/routers/market.py
from fastapi import APIRouter
import yfinance as yf
import pandas as pd

router = APIRouter()

INDEX_TICKERS  = {"sp500": "^GSPC", "nasdaq": "^IXIC",
                  "dow": "^DJI", "vix": "^VIX"}
SECTOR_ETFS    = {"Technology": "XLK", "Healthcare": "XLV",
                  "Financials": "XLF", "Energy": "XLE",
                  "Consumer Disc.": "XLY", "Industrials": "XLI",
                  "Utilities": "XLU", "Materials": "XLB",
                  "Real Estate": "XLRE"}
DEFAULT_WATCHLIST = ["AAPL","MSFT","GOOGL","NVDA","TSLA","AMZN","META"]


@router.get("/indices")
def get_indices():
    """Live index prices + daily change."""
    results = []
    for name, ticker in INDEX_TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if len(hist) >= 2:
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                results.append({
                    "name":   name,
                    "ticker": ticker,
                    "price":  round(float(curr), 2),
                    "change_pct": round(float((curr - prev) / prev * 100), 2),
                })
        except Exception:
            continue
    return {"indices": results}


@router.get("/sparkline/{ticker}")
def get_sparkline(ticker: str, period: str = "1mo"):
    """Mini price series for sparkline charts."""
    hist = yf.Ticker(ticker).history(period=period)
    return {
        "ticker": ticker,
        "dates":  hist.index.strftime("%Y-%m-%d").tolist(),
        "prices": hist['Close'].round(2).tolist(),
    }


@router.get("/performance")
def get_performance(tickers: str = "^GSPC,^IXIC,AAPL,MSFT",
                     period: str = "6mo"):
    """Normalised performance (base=100) for a list of tickers."""
    ticker_list = tickers.split(",")
    series = {}
    for t in ticker_list:
        hist = yf.Ticker(t).history(period=period)['Close']
        if hist.empty:
            continue
        norm = (hist / hist.iloc[0] * 100).round(2)
        series[t] = {
            "dates":  norm.index.strftime("%Y-%m-%d").tolist(),
            "values": norm.tolist(),
        }
    return {"series": series}


@router.get("/watchlist")
def get_watchlist(tickers: str = ",".join(DEFAULT_WATCHLIST)):
    """Live prices + daily change for a watchlist."""
    results = []
    for t in tickers.split(","):
        try:
            info  = yf.Ticker(t).fast_info
            price = info.last_price
            prev  = info.previous_close
            results.append({
                "ticker": t,
                "price":  round(float(price), 2),
                "change_pct": round(float((price - prev) / prev * 100), 2),
            })
        except Exception:
            continue
    return {"watchlist": results}


@router.get("/sectors")
def get_sector_performance(period: str = "1mo"):
    """Sector ETF performance over a period."""
    results = []
    for name, etf in SECTOR_ETFS.items():
        try:
            hist = yf.Ticker(etf).history(period=period)['Close']
            if hist.empty:
                continue
            change = (hist.iloc[-1] / hist.iloc[0] - 1) * 100
            results.append({
                "sector": name,
                "etf":    etf,
                "return_pct": round(float(change), 2),
            })
        except Exception:
            continue
    results.sort(key=lambda x: x['return_pct'])
    return {"sectors": results}