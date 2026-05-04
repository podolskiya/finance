import yfinance as yf
import pandas as pd
import numpy as np

def get_spot_and_hist_vol(ticker: str, vol_window: int = 30):
    """
    Parameters:
        ticker: e.g. 'AAPL', 'SPY', 'TSLA'
        vol_window: for HV calculation

    Returns:
        spot: float
        hist_vol: float
        info: dict with company name, market cap, etc.
    """

    stock = yf.Ticker(ticker)

    hist = stock.history(period=f"{vol_window * 2}d")
    if hist.empty:
        raise ValueError(f"No data found for ticker: {ticker}")

    spot = float(hist["Close"].iloc[-1])

    log_returns = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
    daily_vol = float(log_returns.std())
    hist_vol = daily_vol * np.sqrt(252)

    return spot, hist_vol


def get_option_chain(ticker: str, expiry_index: int = 0):
    """
    Parameters:
        ticker: 'AAPL'
        expiry_index: expiry to fetch 0 = nearest

    Returns:
        calls_df, puts_df: strike, bid, ask, IV, volume
        expiry: date string of the fetched expiry
    """

    stock = yf.Ticker(ticker)
    expiries = stock.options

    if not expiries:
        raise ValueError(f"No options listed for {ticker}")

    expiry = expiries[min(expiry_index, len(expiries) - 1)]
    chain = stock.option_chain(expiry)

    calls_df = chain.calls[["strike", "bid", "ask", "impliedVolatility", "volume", "openInterest"]].copy()
    puts_df  = chain.puts[["strike", "bid", "ask", "impliedVolatility", "volume", "openInterest"]].copy()

    # Mid price as our market price estimate
    calls_df["mid"] = (calls_df["bid"] + calls_df["ask"]) / 2
    puts_df["mid"]  = (puts_df["bid"]  + puts_df["ask"])  / 2

    return calls_df, puts_df, expiry