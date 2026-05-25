# arbitrage/pairs_strategy.py
import pandas as pd
import numpy as np
from arbitrage.ou_process import calc_hedge_ratio, calc_spread, fit_ou_parameters, zscore


def pairs_signals(s1: pd.Series, s2: pd.Series,
                  zscore_window: int = 30,
                  entry_z: float = 2.0,
                  exit_z: float = 0.5) -> pd.DataFrame:
    """
    Generate long/short signals for a cointegrated pair.

    When spread z-score > +entry_z : SHORT spread (short s1, long s2)
    When spread z-score < -entry_z : LONG spread  (long s1, short s2)
    When |z-score| < exit_z        : CLOSE position
    """
    hedge_ratio = calc_hedge_ratio(s1, s2)
    spread      = calc_spread(s1, s2, hedge_ratio)
    ou_params   = fit_ou_parameters(spread)
    z           = zscore(spread, window=zscore_window)

    signal = pd.Series(0, index=s1.index)
    signal[z >  entry_z] = -1   # short spread
    signal[z < -entry_z] =  1   # long spread
    signal[z.abs() < exit_z] = 0

    # Hold until exit (forward fill)
    signal = signal.replace(0, np.nan).ffill().fillna(0)

    return pd.DataFrame({
        "S1":         s1,
        "S2":         s2,
        "Spread":     spread,
        "Z_Score":    z,
        "Signal":     signal,
        "Hedge_Ratio": hedge_ratio
    }), ou_params