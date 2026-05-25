# ml/model.py
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
import os

MODEL_DIR = "ml/saved_models"
os.makedirs(MODEL_DIR, exist_ok=True)


def build_sequences(features: pd.DataFrame,
                    seq_len: int = 20) -> tuple:
    """
    Convert flat feature matrix into 3D sequences for LSTM.
    Shape: (samples, timesteps, features)
    """
    feature_cols = [c for c in features.columns if c != 'target']
    X_raw = features[feature_cols].values
    y_raw = features['target'].values

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X_raw)

    X, y = [], []
    for i in range(seq_len, len(X_scaled)):
        X.append(X_scaled[i - seq_len:i])
        y.append(y_raw[i])

    return np.array(X), np.array(y), scaler, feature_cols


def build_lstm(input_shape: tuple) -> tf.keras.Model:
    """
    Advanced LSTM architecture with dropout and batch normalisation.
    """
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        BatchNormalization(),
        Dropout(0.3),

        LSTM(64, return_sequences=True),
        BatchNormalization(),
        Dropout(0.3),

        LSTM(32, return_sequences=False),
        BatchNormalization(),
        Dropout(0.2),

        Dense(16, activation='relu'),
        Dropout(0.1),
        Dense(1, activation='sigmoid')  # binary: up or down
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model


def train_model(features: pd.DataFrame,
                ticker: str,
                seq_len: int = 20,
                epochs: int = 50,
                test_size: float = 0.2) -> dict:
    """
    Train LSTM on feature matrix. Saves model to disk.
    Returns training history and test metrics.
    """
    print(f"\n[ML] Building sequences for {ticker}...")
    X, y, scaler, feature_cols = build_sequences(features, seq_len)

    split = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    print(f"[ML] Train: {len(X_train)} | Test: {len(X_test)} | Features: {X.shape[2]}")

    model = build_lstm(input_shape=(seq_len, X.shape[2]))

    callbacks = [
        EarlyStopping(patience=10, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(factor=0.5, patience=5, verbose=1)
    ]

    print(f"[ML] Training LSTM...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )

    # Evaluate
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\n[ML] Test Accuracy: {accuracy:.4f} | Loss: {loss:.4f}")

    # Save
    save_path = f"{MODEL_DIR}/{ticker}_lstm.keras"
    model.save(save_path)
    print(f"[ML] Model saved to {save_path}")

    return {
        "model":        model,
        "scaler":       scaler,
        "feature_cols": feature_cols,
        "accuracy":     round(accuracy, 4),
        "loss":         round(loss, 4),
        "history":      history,
        "seq_len":      seq_len
    }


def load_trained_model(ticker: str) -> dict | None:
    """Load a previously saved model if it exists."""
    path = f"{MODEL_DIR}/{ticker}_lstm.keras"
    if os.path.exists(path):
        print(f"[ML] Loading existing model for {ticker}")
        return load_model(path)
    return None