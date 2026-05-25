import pandas as pd
import numpy as np

def mean_reversion_strategy(data: pd.DataFrame,
                             bb_window: int = 20,
                             bb_std: float = 2.0,
                             rsi_period: int = 14,
                             rsi_oversold: int = 35,
                             rsi_overbought: int = 65) -> pd.Series:
    """
    Bollinger Band + RSI mean reversion strategy.

    Logic:
      +1 (Long)  : price touches LOWER band AND RSI oversold  → expect bounce up
      -1 (Short) : price touches UPPER band AND RSI overbought → expect revert down
       0 (Flat)  : price inside bands or RSI neutral
    """
    close = data['Close'].squeeze()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    # Bollinger #
    rolling_mean = close.rolling(bb_window).mean()
    rolling_std  = close.rolling(bb_window).std()
    upper_band   = rolling_mean + (bb_std * rolling_std)
    lower_band   = rolling_mean - (bb_std * rolling_std)

    # RSI #
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(rsi_period).mean()
    loss  = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    # Signals #
    signal = pd.Series(0, index=close.index)

    long_condition  = (close <= lower_band) & (rsi < rsi_oversold)
    short_condition = (close >= upper_band) & (rsi > rsi_overbought)

    signal[long_condition]  =  1
    signal[short_condition] = -1

    signal = signal.replace(0, np.nan).ffill().fillna(0)

    return signal