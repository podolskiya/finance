# ml/self_improve.py
import numpy as np
import pandas as pd
from ml.features import build_features
from ml.model import train_model, build_sequences
import json, os

LOG_PATH = "ml/improvement_log.json"

def generate_ml_signals(model_bundle: dict,
                         new_data: pd.DataFrame,
                         threshold: float = 0.6) -> pd.Series:
    """
    Use trained LSTM to generate trading signals on new data.
    Only signals above confidence threshold are acted on.
    """
    from sklearn.preprocessing import RobustScaler
    features    = build_features(new_data)
    feature_cols = model_bundle['feature_cols']
    seq_len     = model_bundle['seq_len']
    scaler      = model_bundle['scaler']
    model       = model_bundle['model']

    available = [c for c in feature_cols if c in features.columns]
    X_raw     = features[available].values
    X_scaled  = scaler.transform(X_raw)

    signals = pd.Series(0, index=features.index)

    for i in range(seq_len, len(X_scaled)):
        seq  = X_scaled[i - seq_len:i].reshape(1, seq_len, -1)
        prob = model.predict(seq, verbose=0)[0][0]

        if prob > threshold:
            signals.iloc[i] = 1    # confident long
        elif prob < (1 - threshold):
            signals.iloc[i] = -1   # confident short

    return signals


def self_improve(ticker: str, data: pd.DataFrame,
                 current_accuracy: float) -> dict:
    """
    Retrain model on latest data if performance has degraded.
    Logs improvement history to disk.
    """
    log = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            log = json.load(f)

    prev_entries  = [e for e in log if e['ticker'] == ticker]
    prev_accuracy = prev_entries[-1]['accuracy'] if prev_entries else 0

    print(f"\n[SELF-IMPROVE] {ticker}")
    print(f"  Previous accuracy : {prev_accuracy:.4f}")
    print(f"  Current accuracy  : {current_accuracy:.4f}")

    if current_accuracy < prev_accuracy - 0.02 or not prev_entries:
        print(f"  → Performance degraded or no prior model. Retraining...")
        features = build_features(data)
        bundle   = train_model(features, ticker)

        entry = {
            "ticker":   ticker,
            "accuracy": bundle['accuracy'],
            "loss":     bundle['loss'],
            "n_samples": len(data)
        }
        log.append(entry)
        with open(LOG_PATH, 'w') as f:
            json.dump(log, f, indent=2)

        print(f"  → New accuracy: {bundle['accuracy']:.4f}. Log updated.")
        return bundle
    else:
        print(f"  → Model is healthy. No retraining needed.")
        return None