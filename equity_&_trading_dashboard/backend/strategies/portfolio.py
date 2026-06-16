# strategies/portfolio.py
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from data.fetcher import fetch_price_data

# Data #
def get_returns(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Fetch and align daily returns for a list of tickers."""
    frames = {}
    for t in tickers:
        try:
            df    = fetch_price_data(t, start, end)
            close = df['Close'].squeeze()
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            frames[t] = close.pct_change().dropna()
        except Exception as e:
            print(f"[SKIP] {t}: {e}")

    if not frames:
        return pd.DataFrame()

    returns = pd.DataFrame(frames).dropna()
    return returns


def annualised_stats(returns: pd.DataFrame,
                     rf: float = 0.02) -> dict:
    """Annualised return, volatility, covariance matrix."""
    mu  = returns.mean() * 252
    cov = returns.cov()  * 252
    return {"mu": mu, "cov": cov, "rf": rf}


# Portfolio Metrics #
def portfolio_metrics(weights: np.ndarray, mu: pd.Series,
                      cov: pd.DataFrame, rf: float = 0.02) -> dict:
    w        = np.array(weights)
    ret      = float(w @ mu)
    vol      = float(np.sqrt(w @ cov.values @ w))
    sharpe   = (ret - rf) / vol if vol > 0 else 0
    return {"return": ret, "volatility": vol, "sharpe": sharpe}


# ─Optimisers #
def _constraint_sum_to_one(w):
    return np.sum(w) - 1

def _base_constraints(n: int) -> list:
    return [{'type': 'eq', 'fun': _constraint_sum_to_one}]

def _base_bounds(n: int, long_only: bool = True):
    lb = 0.0 if long_only else -0.3
    return [(lb, 1.0)] * n


def max_sharpe(mu: pd.Series, cov: pd.DataFrame,
               rf: float = 0.02,
               long_only: bool = True) -> np.ndarray:
    """Maximise Sharpe ratio."""
    n  = len(mu)
    w0 = np.ones(n) / n

    def neg_sharpe(w):
        m = portfolio_metrics(w, mu, cov, rf)
        return -m['sharpe']

    res = minimize(
        neg_sharpe, w0,
        method='SLSQP',
        bounds=_base_bounds(n, long_only),
        constraints=_base_constraints(n),
        options={'ftol': 1e-12, 'maxiter': 1000}
    )
    return res.x


def min_volatility(mu: pd.Series, cov: pd.DataFrame,
                   long_only: bool = True) -> np.ndarray:
    """Minimise portfolio volatility."""
    n  = len(mu)
    w0 = np.ones(n) / n

    def port_vol(w):
        return np.sqrt(w @ cov.values @ w)

    res = minimize(
        port_vol, w0,
        method='SLSQP',
        bounds=_base_bounds(n, long_only),
        constraints=_base_constraints(n),
        options={'ftol': 1e-12, 'maxiter': 1000}
    )
    return res.x


def risk_parity(cov: pd.DataFrame) -> np.ndarray:
    """
    Risk Parity: each asset contributes equally to portfolio risk.
    Uses iterative optimisation on risk contribution.
    """
    n  = len(cov)
    w0 = np.ones(n) / n

    def risk_contribution_diff(w):
        w   = np.array(w)
        vol = np.sqrt(w @ cov.values @ w)
        mrc = cov.values @ w / vol        # marginal risk contribution
        rc  = w * mrc                     # risk contribution
        target = vol / n                  # equal risk target
        return np.sum((rc - target) ** 2)

    res = minimize(
        risk_contribution_diff, w0,
        method='SLSQP',
        bounds=[(0.0, 1.0)] * n,
        constraints=_base_constraints(n),
        options={'ftol': 1e-14, 'maxiter': 2000}
    )
    return res.x


def equal_weight(n: int) -> np.ndarray:
    """Naive 1/N equal weighting."""
    return np.ones(n) / n


def max_diversification(cov: pd.DataFrame,
                        long_only: bool = True) -> np.ndarray:
    """
    Maximise the Diversification Ratio:
    DR = (w' * sigma_i) / sqrt(w' * Sigma * w)
    where sigma_i = individual asset volatilities.
    """
    n      = len(cov)
    w0     = np.ones(n) / n
    sigmas = np.sqrt(np.diag(cov.values))

    def neg_dr(w):
        weighted_vol = w @ sigmas
        port_vol     = np.sqrt(w @ cov.values @ w)
        return -(weighted_vol / port_vol) if port_vol > 0 else 0

    res = minimize(
        neg_dr, w0,
        method='SLSQP',
        bounds=_base_bounds(n, long_only),
        constraints=_base_constraints(n),
        options={'ftol': 1e-12, 'maxiter': 1000}
    )
    return res.x


# Efficient Frontier #
def efficient_frontier(mu: pd.Series, cov: pd.DataFrame,
                       n_points: int = 60,
                       long_only: bool = True) -> pd.DataFrame:
    """
    Trace the efficient frontier by minimising volatility
    at each target return level.
    """
    n          = len(mu)
    target_rets = np.linspace(mu.min() * 0.8,
                               mu.max() * 0.8, n_points)
    frontier   = []

    for target in target_rets:
        constraints = [
            {'type': 'eq', 'fun': _constraint_sum_to_one},
            {'type': 'eq', 'fun': lambda w, t=target: w @ mu.values - t}
        ]
        res = minimize(
            lambda w: np.sqrt(w @ cov.values @ w),
            np.ones(n) / n,
            method='SLSQP',
            bounds=_base_bounds(n, long_only),
            constraints=constraints,
            options={'ftol': 1e-12, 'maxiter': 1000}
        )
        if res.success:
            vol    = np.sqrt(res.x @ cov.values @ res.x)
            sharpe = (target - 0.02) / vol if vol > 0 else 0
            frontier.append({
                'Return':     target,
                'Volatility': vol,
                'Sharpe':     sharpe
            })

    return pd.DataFrame(frontier)


# Backttest #
def backtest_portfolio(returns: pd.DataFrame,
                       weights: np.ndarray,
                       rebalance: str = 'M',
                       capital: float = 100_000) -> pd.DataFrame:
    """
    Backtest a portfolio with periodic rebalancing.
    rebalance: 'D'=daily, 'W'=weekly, 'M'=monthly, 'Q'=quarterly
    """
    w          = pd.Series(weights, index=returns.columns)
    port_ret   = pd.Series(dtype=float)

    if rebalance == 'D':
        port_ret = (returns * w).sum(axis=1)
    else:
        for period, group in returns.groupby(
            pd.Grouper(freq=rebalance)
        ):
            period_ret = (group * w).sum(axis=1)
            port_ret   = pd.concat([port_ret, period_ret])

    equity = capital * (1 + port_ret).cumprod()
    return pd.DataFrame({
        'Return': port_ret,
        'Equity': equity
    })

def optimise_all(returns: pd.DataFrame,
                 rf: float      = 0.02,
                 long_only: bool = True,
                 rebalance: str  = 'M',
                 capital: float  = 100_000) -> dict:
    """Run all optimisation strategies and return results."""
    stats = annualised_stats(returns, rf)
    mu    = stats['mu']
    cov   = stats['cov']
    n     = len(mu)

    strategies = {
        'Max Sharpe':         max_sharpe(mu, cov, rf, long_only),
        'Min Volatility':     min_volatility(mu, cov, long_only),
        'Risk Parity':        risk_parity(cov),
        'Max Diversification': max_diversification(cov, long_only),
        'Equal Weight':       equal_weight(n),
    }

    results = {}
    for name, w in strategies.items():
        metrics  = portfolio_metrics(w, mu, cov, rf)
        backtest = backtest_portfolio(returns, w, rebalance, capital)
        results[name] = {
            'weights':  pd.Series(w, index=returns.columns),
            'metrics':  metrics,
            'backtest': backtest,
        }

    frontier = efficient_frontier(mu, cov, long_only=long_only)

    return {
        'strategies': results,
        'frontier':   frontier,
        'mu':         mu,
        'cov':        cov,
        'tickers':    list(returns.columns),
    }