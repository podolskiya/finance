import pandas as pd
import numpy as np

def momentum_strategy(data: pd.DataFrame,
                      short_window: int = 20,
                      long_window: int = 60,
                      rsi_period: int = 14,
                      rsi_threshold: tuple = (30, 70)) -> pd.Series:
    """
    Dual moving average crossover + RSI filter momentum strategy.

    logic:
      +1 (Long)  : short MA > long MA AND RSI not overbought
      -1 (Short) : short MA < long MA AND RSI not oversold
       0 (Flat)  : RSI in extreme zone (filter noise)
    """
    close = data['Close'].squeeze()

    short_ma = close.rolling(short_window).mean()
    long_ma  = close.rolling(long_window).mean()

    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(rsi_period).mean()
    loss  = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    raw_signal = pd.Series(0, index=close.index)
    raw_signal[short_ma > long_ma] =  1
    raw_signal[short_ma < long_ma] = -1

    rsi_low, rsi_high = rsi_threshold
    filtered = raw_signal.copy()
    filtered[(raw_signal == -1) & (rsi < rsi_low)]  = 0   # don't short oversold
    filtered[(raw_signal ==  1) & (rsi > rsi_high)] = 0   # don't long overbought

    return filtered.fillna(0)