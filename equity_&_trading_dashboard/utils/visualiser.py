import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np

def plot_backtest(results: pd.DataFrame, metrics: dict, title: str = "Strategy Backtest"):
    """
    Full backtest dashboard:
      - Equity curve vs Buy & Hold
      - Drawdown chart
      - Daily returns distribution
      - Signal overlay on price
    """
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, :])   
    ax2 = fig.add_subplot(gs[1, :])  
    ax3 = fig.add_subplot(gs[2, 0])  
    ax4 = fig.add_subplot(gs[2, 1])   

    # Equity Curve #
    ax1.plot(results.index, results['Equity_Curve'],
             label='Strategy', color='#2196F3', linewidth=1.8)
    ax1.plot(results.index, results['Buy_Hold_Curve'],
             label='Buy & Hold', color='#FF9800', linewidth=1.8, linestyle='--')
    ax1.set_title('Equity Curve', fontweight='bold')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend()
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax1.grid(True, alpha=0.3)

    # Metrics box #
    metrics_text = "\n".join([f"{k}: {v}" for k, v in metrics.items()])
    ax1.text(0.01, 0.05, metrics_text, transform=ax1.transAxes,
             fontsize=8, verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Drawdown #
    equity = results['Equity_Curve']
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max * 100
    ax2.fill_between(results.index, drawdown, 0, color='#F44336', alpha=0.4)
    ax2.plot(results.index, drawdown, color='#F44336', linewidth=0.8)
    ax2.set_title('Drawdown (%)', fontweight='bold')
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(True, alpha=0.3)

    # Returns Distribution #
    strat_returns = results['Strategy_Return'].dropna() * 100
    market_returns = results['Market_Return'].dropna() * 100
    ax3.hist(market_returns, bins=60, alpha=0.5, color='#FF9800', label='Buy & Hold')
    ax3.hist(strat_returns,  bins=60, alpha=0.5, color='#2196F3', label='Strategy')
    ax3.axvline(0, color='black', linewidth=1)
    ax3.set_title('Daily Returns Distribution', fontweight='bold')
    ax3.set_xlabel('Daily Return (%)')
    ax3.set_ylabel('Frequency')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Price + Signals #
    price = results['Close']
    signal = results['Signal']
    ax4.plot(results.index, price, color='gray', linewidth=1, label='Price')
    longs  = results.index[signal == 1]
    shorts = results.index[signal == -1]
    ax4.scatter(longs,  price[longs],  marker='^', color='#4CAF50', s=15, label='Long',  zorder=5)
    ax4.scatter(shorts, price[shorts], marker='v', color='#F44336', s=15, label='Short', zorder=5)
    ax4.set_title('Price + Signals', fontweight='bold')
    ax4.set_ylabel('Price ($)')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    plt.savefig('backtest_result.png', dpi=150, bbox_inches='tight')
    print("[CHART] Saved to backtest_result.png")
    plt.show()