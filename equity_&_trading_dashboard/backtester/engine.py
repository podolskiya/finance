# backtester/engine.py
import numpy as np
import pandas as pd

class Backtester:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100_000.0,
                 commission: float = 0.001, slippage: float = 0.0005):
        """
        data         : DataFrame with at least a 'Close' column
        commission   : e.g. 0.001 = 0.1% per trade
        slippage     : e.g. 0.0005 = 0.05% price impact
        """
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.results = None

    def run(self, signals: pd.Series) -> pd.DataFrame:
        """
        signals : Series of 1 (long), -1 (short), 0 (flat) aligned to data index
        Returns : DataFrame of portfolio performance over time
        """
        # --- FIX: flatten MultiIndex columns from yfinance ---
        data = self.data.copy()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        close = data['Close'].squeeze()
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        signals = signals.reindex(close.index).fillna(0)

        portfolio = pd.DataFrame(index=close.index)
        portfolio['Close']          = close.values
        portfolio['Signal']         = signals.values
        portfolio['Position']       = signals.shift(1).fillna(0).values

        # Raw returns
        portfolio['Market_Return']   = portfolio['Close'].pct_change()

        # Transaction costs on position changes
        position_change              = portfolio['Position'].diff().abs()
        cost                         = position_change * (self.commission + self.slippage)

        portfolio['Strategy_Return'] = (
            portfolio['Position'] * portfolio['Market_Return'] - cost
        )

        # Cumulative equity curves
        portfolio['Equity_Curve']   = (
            self.initial_capital * (1 + portfolio['Strategy_Return']).cumprod()
        )
        portfolio['Buy_Hold_Curve'] = (
            self.initial_capital * (1 + portfolio['Market_Return']).cumprod()
        )

        self.results = portfolio
        return portfolio

    def metrics(self) -> dict:
        """Calculate key performance metrics."""
        if self.results is None:
            raise RuntimeError("Run backtest first with .run(signals)")

        r = self.results['Strategy_Return'].dropna()
        equity = self.results['Equity_Curve'].dropna()

        # Sharpe Ratio (annualised, risk-free = 2%)
        excess = r - 0.02 / 252
        sharpe = (excess.mean() / excess.std()) * np.sqrt(252)

        # Max Drawdown
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = drawdown.min()

        # CAGR
        n_years = len(r) / 252
        cagr = (equity.iloc[-1] / self.initial_capital) ** (1 / n_years) - 1

        # Win rate
        wins = (r > 0).sum()
        total_trades = (r != 0).sum()
        win_rate = wins / total_trades if total_trades > 0 else 0

        return {
            "Sharpe Ratio":     round(sharpe, 3),
            "Max Drawdown":     f"{round(max_dd * 100, 2)}%",
            "CAGR":             f"{round(cagr * 100, 2)}%",
            "Win Rate":         f"{round(win_rate * 100, 2)}%",
            "Final Equity":     f"${equity.iloc[-1]:,.2f}",
            "Total Return":     f"{round((equity.iloc[-1]/self.initial_capital - 1)*100, 2)}%"
        }