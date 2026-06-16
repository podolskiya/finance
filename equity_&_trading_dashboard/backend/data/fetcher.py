# data/fetcher.py
import yfinance as yf
import pandas as pd
import os

DATA_CACHE_DIR = "data/cache"
os.makedirs(DATA_CACHE_DIR, exist_ok=True)


def fetch_price_data(ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance.
    Caches results locally as parquet to avoid repeated API calls.
    """
    cache_path = f"{DATA_CACHE_DIR}/{ticker}_{start}_{end}_{interval}.parquet"

    if os.path.exists(cache_path):
        print(f"[CACHE] Loading {ticker} from disk...")
        return pd.read_parquet(cache_path)

    print(f"[FETCH] Downloading {ticker} from Yahoo Finance...")
    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True)

    if df.empty:
        raise ValueError(f"No data returned for {ticker}")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df.to_parquet(cache_path)
    print(f"[SAVED] {ticker} cached to {cache_path}")
    return df


def fetch_multiple(tickers: list, start: str, end: str) -> dict:
    """Fetch data for multiple tickers, return as a dict of DataFrames."""
    return {ticker: fetch_price_data(ticker, start, end) for ticker in tickers}

