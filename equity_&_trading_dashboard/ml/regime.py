import numpy as np
import pandas as pd
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Regime Labels #
REGIME_META = {
    0: {"label": "Bear",     "color": "#EF4444", "emoji": "🔴"},
    1: {"label": "Sideways", "color": "#F59E0B", "emoji": "🟡"},
    2: {"label": "Bull",     "color": "#10B981", "emoji": "🟢"},
}


def build_regime_features(data: pd.DataFrame,
                           vol_window: int = 20) -> np.ndarray:
    """
    Build feature matrix for HMM:
      - Daily returns
      - Rolling volatility
      - Momentum (5d, 20d)
      - Volume ratio
    These capture both trend and risk environment.
    """
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close  = df['Close'].squeeze()
    volume = df['Volume'].squeeze() if 'Volume' in df.columns else None

    features = pd.DataFrame(index=df.index)
    features['returns']    = close.pct_change()
    features['volatility'] = features['returns'].rolling(vol_window).std()
    features['momentum_5'] = close.pct_change(5)
    features['momentum_20']= close.pct_change(20)

    if volume is not None:
        features['vol_ratio'] = (
            volume / volume.rolling(20).mean()
        )
    else:
        features['vol_ratio'] = 1.0

    return features.dropna()


def fit_hmm(features: pd.DataFrame,
            n_regimes: int = 3,
            n_iter: int    = 200) -> dict:
    """
    Fit a Gaussian HMM to the feature matrix.
    Automatically sorts regimes by mean return
    so 0=Bear, 1=Sideways, 2=Bull.
    """
    scaler  = StandardScaler()
    X       = scaler.fit_transform(features.values)

    model = hmm.GaussianHMM(
        n_components = n_regimes,
        covariance_type = "full",
        n_iter       = n_iter,
        random_state = 42,
        tol          = 1e-4
    )
    model.fit(X)

    raw_states = model.predict(X)

    mean_returns = [
        features['returns'].values[raw_states == i].mean()
        for i in range(n_regimes)
    ]
    order   = np.argsort(mean_returns)      
    remap   = {old: new for new, old in enumerate(order)}
    states  = np.array([remap[s] for s in raw_states])

    # Transition matrix #
    trans = model.transmat_[order][:, order]

    return {
        "model":        model,
        "scaler":       scaler,
        "states":       states,
        "features":     features,
        "trans_matrix": trans,
        "n_regimes":    n_regimes,
        "mean_returns": sorted(mean_returns),
    }


def regime_series(hmm_result: dict,
                  original_index: pd.Index) -> pd.Series:
    """Return a labelled Series aligned to original price index."""
    features = hmm_result['features']
    states   = hmm_result['states']
    s        = pd.Series(states, index=features.index)
    return s.reindex(original_index).ffill().fillna(1).astype(int)


def regime_statistics(prices: pd.DataFrame,
                      regimes: pd.Series) -> pd.DataFrame:
    """
    Per-regime performance statistics.
    """
    close   = prices['Close'].squeeze()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    returns = close.pct_change().dropna()
    rows    = []

    for r in sorted(regimes.unique()):
        mask = regimes.reindex(returns.index) == r
        r_ret = returns[mask]

        if len(r_ret) == 0:
            continue

        ann_ret  = r_ret.mean() * 252
        ann_vol  = r_ret.std()  * np.sqrt(252)
        sharpe   = ann_ret / ann_vol if ann_vol > 0 else 0
        win_rate = (r_ret > 0).mean()
        n_days   = mask.sum()
        pct_time = n_days / len(regimes) * 100

        meta = REGIME_META.get(r, {"label": f"Regime {r}"})
        rows.append({
            "Regime":       meta['label'],
            "Days":         int(n_days),
            "% of Time":    round(pct_time, 1),
            "Ann. Return":  round(ann_ret  * 100, 2),
            "Ann. Vol":     round(ann_vol  * 100, 2),
            "Sharpe":       round(sharpe,   3),
            "Win Rate":     round(win_rate  * 100, 1),
        })

    return pd.DataFrame(rows).set_index("Regime")


def regime_signals(regimes: pd.Series,
                   mode: str = "bull_only") -> pd.Series:
    """
    Convert regime labels into trading signals.

    Modes:
      bull_only   : Long in Bull, flat otherwise
      bear_short  : Long in Bull, Short in Bear, flat Sideways
      adaptive    : Long in Bull, Short in Bear, out in Sideways
    """
    signals = pd.Series(0, index=regimes.index, dtype=float)

    if mode == "bull_only":
        signals[regimes == 2]  =  1

    elif mode == "bear_short":
        signals[regimes == 2]  =  1
        signals[regimes == 0]  = -1

    elif mode == "adaptive":
        signals[regimes == 2]  =  1
        signals[regimes == 0]  = -1
        signals[regimes == 1]  =  0

    return signals


def predict_current_regime(hmm_result: dict) -> dict:
    """
    Predict the most likely current regime and its probability.
    """
    model   = hmm_result['model']
    scaler  = hmm_result['scaler']
    features = hmm_result['features']

    X_last  = scaler.transform(features.values[-5:])
    log_prob, posteriors = model.score_samples(X_last)
    last_posterior = posteriors[-1]

    mean_returns = hmm_result['mean_returns']
    raw_pred     = np.argmax(last_posterior)

    # Re-sort to match labelling #
    sorted_idx   = np.argsort(
        [features['returns'].values[
            hmm_result['states'] == i
        ].mean() for i in range(hmm_result['n_regimes'])]
    )
    remap        = {old: new for new, old in enumerate(sorted_idx)}
    current      = remap.get(raw_pred, raw_pred)
    probs        = {
        remap.get(i, i): round(last_posterior[i], 4)
        for i in range(len(last_posterior))
    }

    return {
        "regime":       current,
        "label":        REGIME_META[current]['label'],
        "color":        REGIME_META[current]['color'],
        "emoji":        REGIME_META[current]['emoji'],
        "probabilities": probs,
    }