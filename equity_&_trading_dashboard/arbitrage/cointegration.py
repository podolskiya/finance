# arbitrage/cointegration.py
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint, adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from itertools import combinations
from data.fetcher import fetch_price_data

def get_close_prices(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Fetch and align close prices for multiple tickers."""
    frames = {}
    for t in tickers:
        try:
            df = fetch_price_data(t, start, end)
            close = df['Close'].squeeze()
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            frames[t] = close
        except Exception as e:
            print(f"[SKIP] {t}: {e}")
    return pd.DataFrame(frames).dropna()


def engle_granger_test(s1: pd.Series, s2: pd.Series,
                        significance: float = 0.05) -> dict:
    """
    Engle-Granger cointegration test between two price series.
    Returns test stats and whether the pair is cointegrated.
    """
    score, pvalue, _ = coint(s1, s2)
    return {
        "score":         round(score, 4),
        "p_value":       round(pvalue, 4),
        "cointegrated":  pvalue < significance
    }


def johansen_test(prices: pd.DataFrame, significance: str = "95%") -> dict:
    """
    Johansen cointegration test for 2+ series.
    More powerful than Engle-Granger for multiple assets.
    """
    sig_map = {"90%": 0, "95%": 1, "99%": 2}
    sig_idx = sig_map.get(significance, 1)

    result = coint_johansen(prices, det_order=0, k_ar_diff=1)

    trace_stats = result.lr1
    crit_vals   = result.cvt[:, sig_idx]
    rejections  = trace_stats > crit_vals

    return {
        "trace_stats":    [round(x, 4) for x in trace_stats],
        "critical_vals":  [round(x, 4) for x in crit_vals],
        "cointegrated":   bool(rejections[0]),
        "n_relations":    int(rejections.sum()),
        "eigenvectors":   result.evec
    }


def scan_pairs(tickers: list, start: str, end: str,
               significance: float = 0.05) -> pd.DataFrame:
    """
    Scan all ticker combinations for cointegrated pairs.
    Returns a ranked DataFrame of the best pairs.
    """
    prices = get_close_prices(tickers, start, end)
    valid  = list(prices.columns)
    pairs  = list(combinations(valid, 2))

    print(f"[SCAN] Testing {len(pairs)} pairs for cointegration...")
    results = []

    for t1, t2 in pairs:
        eg = engle_granger_test(prices[t1], prices[t2], significance)
        if eg["cointegrated"]:
            results.append({
                "Pair":      f"{t1}/{t2}",
                "Ticker_1":  t1,
                "Ticker_2":  t2,
                "P_Value":   eg["p_value"],
                "Score":     eg["score"]
            })

    if not results:
        print("[INFO] No cointegrated pairs found at this significance level.")
        return pd.DataFrame()

    df = pd.DataFrame(results).sort_values("P_Value")
    print(f"[FOUND] {len(df)} cointegrated pairs")
    return df