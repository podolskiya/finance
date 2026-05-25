# arbitrage/ou_process.py
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def calc_hedge_ratio(s1: pd.Series, s2: pd.Series) -> float:
    """OLS regression to find the hedge ratio between two series."""
    model = LinearRegression(fit_intercept=True)
    model.fit(s2.values.reshape(-1, 1), s1.values)
    return model.coef_[0]


def calc_spread(s1: pd.Series, s2: pd.Series,
                hedge_ratio: float = None) -> pd.Series:
    """Compute the price spread (s1 - hedge_ratio * s2)."""
    if hedge_ratio is None:
        hedge_ratio = calc_hedge_ratio(s1, s2)
    return s1 - hedge_ratio * s2


def fit_ou_parameters(spread: pd.Series) -> dict:
    """
    Fit Ornstein-Uhlenbeck parameters to a spread series.
    OU: dX = theta*(mu - X)*dt + sigma*dW

    Returns:
      theta : mean reversion speed (higher = faster reversion)
      mu    : long-run mean of spread
      sigma : volatility of spread
      half_life : days to revert halfway to mean
    """
    spread = spread.dropna()
    lag    = spread.shift(1).dropna()
    delta  = spread.diff().dropna()

    # Align
    lag   = lag.iloc[-len(delta):]
    delta = delta.iloc[-len(lag):]

    # Regress delta on lag: delta = a + b*lag
    model = LinearRegression(fit_intercept=True)
    model.fit(lag.values.reshape(-1, 1), delta.values)

    b     = model.coef_[0]
    a     = model.intercept_

    theta     = -b                           # mean reversion speed
    mu        = a / theta if theta > 0 else 0
    sigma     = np.std(delta - model.predict(lag.values.reshape(-1, 1)))
    half_life = np.log(2) / theta if theta > 0 else np.inf

    return {
        "theta":     round(theta, 6),
        "mu":        round(mu, 4),
        "sigma":     round(sigma, 6),
        "half_life": round(half_life, 2)
    }


def zscore(spread: pd.Series, window: int = 30) -> pd.Series:
    """Rolling z-score of the spread."""
    mean = spread.rolling(window).mean()
    std  = spread.rolling(window).std()
    return (spread - mean) / std.replace(0, np.nan)