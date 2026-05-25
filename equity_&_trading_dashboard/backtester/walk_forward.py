# backtester/walk_forward.py
import numpy as np
import pandas as pd
from itertools import product
from typing import Callable
from backtester.engine import Backtester
from strategies.momentum import momentum_strategy
from strategies.mean_reversion import mean_reversion_strategy

# ── Parameter Grids ──
PARAM_GRIDS = {
    "Momentum": {
        "short_window": [10, 15, 20, 30],
        "long_window":  [40, 60, 80, 100],
        "rsi_period":   [14],
    },
    "Mean Reversion": {
        "bb_window": [10, 15, 20, 30],
        "bb_std":    [1.5, 2.0, 2.5],
    },
    "Combined": {
        "short_window": [10, 20, 30],
        "long_window":  [40, 60, 80],
        "bb_window":    [15, 20],
        "bb_std":       [1.5, 2.0],
    }
}

STRATEGY_FN = {
    "Momentum":      momentum_strategy,
    "Mean Reversion": mean_reversion_strategy,
}


def _run_single(data: pd.DataFrame, strategy: str,
                params: dict, capital: float,
                commission: float, slippage: float) -> dict:
    """Run one backtest and return metrics + Sharpe."""
    try:
        if strategy == "Momentum":
            signals = momentum_strategy(data, **params)
        elif strategy == "Mean Reversion":
            signals = mean_reversion_strategy(data, **params)
        else:
            s1 = momentum_strategy(
                data,
                short_window=params.get('short_window', 20),
                long_window=params.get('long_window', 60)
            )
            s2 = mean_reversion_strategy(
                data,
                bb_window=params.get('bb_window', 20),
                bb_std=params.get('bb_std', 2.0)
            )
            raw     = (s1 + s2) / 2
            signals = raw.apply(
                lambda x: 1 if x > 0.4 else (-1 if x < -0.4 else 0)
            )

        bt      = Backtester(data, capital, commission, slippage)
        results = bt.run(signals)
        metrics = bt.metrics()
        sharpe  = float(metrics['Sharpe Ratio'])
        return {"sharpe": sharpe, "metrics": metrics,
                "results": results, "params": params}
    except:
        return {"sharpe": -999, "metrics": {}, "results": None, "params": params}


def grid_search(data: pd.DataFrame, strategy: str,
                capital: float, commission: float,
                slippage: float) -> dict:
    """
    Exhaustive grid search over parameter combinations.
    Returns the best parameter set by Sharpe ratio.
    """
    grid    = PARAM_GRIDS.get(strategy, {})
    keys    = list(grid.keys())
    values  = list(grid.values())
    combos  = list(product(*values))

    best_sharpe = -999
    best_result = None

    for combo in combos:
        params = dict(zip(keys, combo))
        result = _run_single(data, strategy, params,
                             capital, commission, slippage)
        if result['sharpe'] > best_sharpe:
            best_sharpe = result['sharpe']
            best_result = result

    return best_result


def walk_forward(data: pd.DataFrame,
                 strategy: str       = "Momentum",
                 n_splits: int       = 5,
                 train_pct: float    = 0.7,
                 capital: float      = 100_000,
                 commission: float   = 0.001,
                 slippage: float     = 0.0005,
                 progress_cb         = None) -> dict:
    """
    Walk-Forward Optimisation engine.

    For each fold:
      1. Split into train / test window
      2. Grid search best params on TRAIN data only
      3. Apply best params to TEST data (out-of-sample)
      4. Roll window forward

    Returns combined OOS equity curve + per-fold breakdown.
    """
    n       = len(data)
    fold_sz = n // n_splits

    fold_results   = []
    oos_curves     = []
    oos_returns    = []
    best_params    = []

    for i in range(n_splits):
        fold_start = i * fold_sz
        fold_end   = fold_start + fold_sz if i < n_splits - 1 else n

        fold_data  = data.iloc[fold_start:fold_end]
        train_end  = int(len(fold_data) * train_pct)

        train_data = fold_data.iloc[:train_end]
        test_data  = fold_data.iloc[train_end:]

        if len(train_data) < 60 or len(test_data) < 20:
            continue

        if progress_cb:
            progress_cb(i, n_splits, "optimising")

        # ── Optimise on train ──
        best = grid_search(train_data, strategy,
                           capital, commission, slippage)

        if progress_cb:
            progress_cb(i, n_splits, "testing")

        # ── Test on OOS ──
        oos = _run_single(test_data, strategy, best['params'],
                          capital, commission, slippage)

        if oos['results'] is None:
            continue

        oos_result     = oos['results']
        oos_metrics    = oos['metrics']

        # Rescale equity to chain from previous fold
        if oos_curves:
            last_val   = oos_curves[-1]['Equity_Curve'].iloc[-1]
            scale      = last_val / capital
            oos_result = oos_result.copy()
            oos_result['Equity_Curve']   *= scale
            oos_result['Buy_Hold_Curve'] *= scale

        oos_curves.append(oos_result)
        oos_returns.append(oos_result['Strategy_Return'])
        best_params.append(best['params'])

        fold_results.append({
            "Fold":         i + 1,
            "Train Start":  str(train_data.index[0].date()),
            "Train End":    str(train_data.index[-1].date()),
            "Test Start":   str(test_data.index[0].date()),
            "Test End":     str(test_data.index[-1].date()),
            "Train Sharpe": round(best['sharpe'], 3),
            "OOS Sharpe":   float(oos_metrics.get('Sharpe Ratio', 0)),
            "OOS Return":   oos_metrics.get('Total Return', 'N/A'),
            "OOS CAGR":     oos_metrics.get('CAGR', 'N/A'),
            "OOS Drawdown": oos_metrics.get('Max Drawdown', 'N/A'),
            "Best Params":  str(best['params']),
        })

    if not oos_curves:
        return {"error": "No valid folds produced"}

    # ── Combine OOS curves ──
    combined_curve   = pd.concat(oos_curves)
    combined_returns = pd.concat(oos_returns).dropna()

    # ── Combined metrics ──
    excess   = combined_returns - 0.02 / 252
    sharpe   = (excess.mean() / excess.std()) * np.sqrt(252)
    equity   = combined_curve['Equity_Curve']
    dd       = ((equity - equity.cummax()) / equity.cummax()).min()
    n_years  = len(combined_returns) / 252
    cagr     = (equity.iloc[-1] / capital) ** (1/n_years) - 1 if n_years > 0 else 0
    wins     = (combined_returns > 0).sum()
    total_tr = (combined_returns != 0).sum()

    combined_metrics = {
        "Sharpe Ratio": round(sharpe, 3),
        "Max Drawdown": f"{round(dd*100, 2)}%",
        "CAGR":         f"{round(cagr*100, 2)}%",
        "Win Rate":     f"{round(wins/total_tr*100, 2)}%" if total_tr > 0 else "N/A",
        "Final Equity": f"${equity.iloc[-1]:,.2f}",
        "Total Return": f"{round((equity.iloc[-1]/capital-1)*100, 2)}%",
    }

    # ── Parameter stability ──
    param_df = pd.DataFrame(best_params)

    return {
        "fold_results":    pd.DataFrame(fold_results),
        "combined_curve":  combined_curve,
        "combined_metrics": combined_metrics,
        "param_stability": param_df,
        "n_folds":         len(fold_results),
    }