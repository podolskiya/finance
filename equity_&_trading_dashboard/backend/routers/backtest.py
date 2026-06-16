# backend/routers/backtest.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from data.fetcher import fetch_price_data
from backtester.engine import Backtester
from strategies.momentum import momentum_strategy
from strategies.mean_reversion import mean_reversion_strategy

router = APIRouter()


# ── Request / Response Schemas ────────────────────────
class BacktestRequest(BaseModel):
    ticker:       str   = "AAPL"
    start:        str   = "2020-01-01"
    end:          str   = "2024-01-01"
    strategy:     Literal["Momentum", "Mean Reversion", "Combined"] = "Momentum"
    capital:      float = 100_000
    commission:   float = 0.001
    slippage:     float = 0.0005
    short_window: int   = 20
    long_window:  int   = 60
    bb_window:    int   = 20
    bb_std:       float = 2.0


def _series_to_payload(s: pd.Series) -> dict:
    """Convert a pandas Series to JSON-safe {dates, values}."""
    s = s.dropna()
    return {
        "dates":  s.index.strftime("%Y-%m-%d").tolist(),
        "values": [round(float(v), 4) for v in s.values],
    }


def _build_signals(df: pd.DataFrame, req: BacktestRequest) -> pd.Series:
    if req.strategy == "Momentum":
        return momentum_strategy(df, req.short_window, req.long_window)
    elif req.strategy == "Mean Reversion":
        return mean_reversion_strategy(df, req.bb_window, req.bb_std)
    else:
        s1  = momentum_strategy(df, req.short_window, req.long_window)
        s2  = mean_reversion_strategy(df, req.bb_window, req.bb_std)
        raw = (s1 + s2) / 2
        return raw.apply(lambda x: 1 if x > 0.4 else (-1 if x < -0.4 else 0))


@router.post("/run")
def run_backtest(req: BacktestRequest):
    try:
        df      = fetch_price_data(req.ticker, req.start, req.end)
        signals = _build_signals(df, req)

        bt      = Backtester(df, req.capital, req.commission, req.slippage)
        results = bt.run(signals)
        metrics = bt.metrics()

        close   = results['Close']
        equity  = results['Equity_Curve']
        bh      = results['Buy_Hold_Curve']
        strat_r = results['Strategy_Return']
        mkt_r   = results['Market_Return']
        sig     = results['Signal']

        # Drawdown
        roll_max = equity.cummax()
        dd       = (equity - roll_max) / roll_max * 100

        # Signal scatter points
        longs  = close[sig ==  1]
        shorts = close[sig == -1]

        # Returns distribution (bucketed for histogram)
        strat_hist, bins = np.histogram(
            strat_r.dropna() * 100, bins=60
        )
        mkt_hist, _      = np.histogram(
            mkt_r.dropna() * 100, bins=bins
        )
        bin_centres = ((bins[:-1] + bins[1:]) / 2).round(3).tolist()

        return {
            "metrics": metrics,
            "equity_curve": {
                "strategy":   _series_to_payload(equity),
                "buy_hold":   _series_to_payload(bh),
            },
            "drawdown":     _series_to_payload(dd),
            "signals": {
                "longs":  {
                    "dates":  longs.index.strftime("%Y-%m-%d").tolist(),
                    "prices": longs.round(2).tolist(),
                },
                "shorts": {
                    "dates":  shorts.index.strftime("%Y-%m-%d").tolist(),
                    "prices": shorts.round(2).tolist(),
                },
                "price":  _series_to_payload(close),
            },
            "distributions": {
                "bins":     bin_centres,
                "strategy": strat_hist.tolist(),
                "market":   mkt_hist.tolist(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
def list_strategies():
    return {
        "strategies": ["Momentum", "Mean Reversion", "Combined"],
        "default_params": {
            "Momentum":      {"short_window": 20, "long_window": 60},
            "Mean Reversion":{"bb_window": 20, "bb_std": 2.0},
            "Combined":      {"short_window": 20, "long_window": 60,
                              "bb_window": 20, "bb_std": 2.0},
        }
    }