import pandas as pd
import numpy as np

def build_features(data: pd.DataFrame, lags: int = 5) -> pd.DataFrame:
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close  = df['Close'].squeeze()
    high   = df['High'].squeeze()
    low    = df['Low'].squeeze()
    volume = df['Volume'].squeeze()

    features = pd.DataFrame(index=df.index)

    # E[R] #
    features['return_1d']  = close.pct_change()
    features['return_5d']  = close.pct_change(5)
    features['return_10d'] = close.pct_change(10)
    features['return_20d'] = close.pct_change(20)

    # Vol #
    features['volatility_10d'] = features['return_1d'].rolling(10).std()
    features['volatility_20d'] = features['return_1d'].rolling(20).std()

    # MA #
    for w in [5, 10, 20, 50]:
        features[f'ma_{w}_ratio'] = close / close.rolling(w).mean() - 1

    # Bollinger Band position #
    bb_mean = close.rolling(20).mean()
    bb_std  = close.rolling(20).std()
    features['bb_position'] = (close - bb_mean) / (2 * bb_std)

    # RSI #
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    features['rsi'] = (100 - (100 / (1 + rs))) / 100  # normalised 0-1

    # MACD #
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd  = ema12 - ema26
    features['macd_signal'] = macd / close  # normalised

    # Vol #
    features['volume_ratio'] = volume / volume.rolling(20).mean()

    # High/Low range #
    features['hl_range'] = (high - low) / close

    # Lagged returns (memory for LSTM) #
    for lag in range(1, lags + 1):
        features[f'lag_{lag}'] = features['return_1d'].shift(lag)

    # Next day prediction #
    features['target'] = (close.shift(-1) > close).astype(int)

    return features.dropna()