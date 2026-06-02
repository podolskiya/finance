import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    GetOrdersRequest, GetAssetsRequest
)
from alpaca.trading.enums import (
    OrderSide, TimeInForce, OrderStatus, AssetClass
)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import streamlit as st


# ── Client Factory ────────────────────────────────────
@st.cache_resource
def get_trading_client(api_key: str,
                        secret_key: str) -> TradingClient:
    return TradingClient(
        api_key    = api_key,
        secret_key = secret_key,
        paper      = True          # Always paper trading
    )


@st.cache_resource
def get_data_client(api_key: str,
                     secret_key: str) -> StockHistoricalDataClient:
    return StockHistoricalDataClient(
        api_key    = api_key,
        secret_key = secret_key
    )


# ── Account ───────────────────────────────────────────
def get_account(client: TradingClient) -> dict:
    """Fetch account summary."""
    try:
        acc = client.get_account()
        return {
            "equity":          float(acc.equity),
            "cash":            float(acc.cash),
            "buying_power":    float(acc.buying_power),
            "portfolio_value": float(acc.portfolio_value),
            "daytrade_count":  acc.daytrade_count,
            "status":          acc.status,
            "pnl":             float(acc.equity) - float(acc.last_equity),
            "pnl_pct": (
                (float(acc.equity) - float(acc.last_equity))
                / float(acc.last_equity) * 100
                if float(acc.last_equity) > 0 else 0
            ),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Positions ─────────────────────────────────────────
def get_positions(client: TradingClient) -> pd.DataFrame:
    """Fetch all open positions."""
    try:
        positions = client.get_all_positions()
        if not positions:
            return pd.DataFrame()

        rows = []
        for p in positions:
            rows.append({
                "Symbol":      p.symbol,
                "Qty":         float(p.qty),
                "Side":        "Long" if float(p.qty) > 0 else "Short",
                "Avg Entry":   float(p.avg_entry_price),
                "Current":     float(p.current_price),
                "Market Val":  float(p.market_value),
                "Unrealised P&L": float(p.unrealized_pl),
                "Unrealised %":   float(p.unrealized_plpc) * 100,
                "Today P&L":      float(p.unrealized_intraday_pl),
            })
        return pd.DataFrame(rows).set_index("Symbol")
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})


# ── Orders ────────────────────────────────────────────
def get_orders(client: TradingClient,
               status: str = "all",
               limit: int  = 50) -> pd.DataFrame:
    """Fetch recent orders."""
    try:
        status_map = {
            "all":    OrderStatus.ALL,
            "open":   OrderStatus.OPEN,
            "closed": OrderStatus.CLOSED,
        }
        req    = GetOrdersRequest(
            status = status_map.get(status, OrderStatus.ALL),
            limit  = limit
        )
        orders = client.get_orders(filter=req)
        if not orders:
            return pd.DataFrame()

        rows = []
        for o in orders:
            rows.append({
                "Time":    str(o.created_at)[:19],
                "Symbol":  o.symbol,
                "Side":    o.side.value.upper(),
                "Type":    o.type.value,
                "Qty":     float(o.qty or 0),
                "Filled":  float(o.filled_qty or 0),
                "Fill Px": float(o.filled_avg_price or 0),
                "Status":  o.status.value,
                "ID":      str(o.id)[:8],
            })
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})


# ── Place Orders ──────────────────────────────────────
def place_market_order(client: TradingClient,
                        symbol: str,
                        qty:    float,
                        side:   str) -> dict:
    """Place a market order."""
    try:
        req = MarketOrderRequest(
            symbol       = symbol.upper(),
            qty          = qty,
            side         = OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force= TimeInForce.DAY
        )
        order = client.submit_order(req)
        return {
            "success": True,
            "order_id": str(order.id),
            "symbol":   order.symbol,
            "qty":      float(order.qty),
            "side":     side,
            "status":   order.status.value,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def place_limit_order(client:    TradingClient,
                       symbol:   str,
                       qty:      float,
                       side:     str,
                       limit_px: float) -> dict:
    """Place a limit order."""
    try:
        req = LimitOrderRequest(
            symbol        = symbol.upper(),
            qty           = qty,
            side          = OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force = TimeInForce.DAY,
            limit_price   = round(limit_px, 2)
        )
        order = client.submit_order(req)
        return {
            "success":  True,
            "order_id": str(order.id),
            "symbol":   order.symbol,
            "qty":      float(order.qty),
            "side":     side,
            "limit_px": limit_px,
            "status":   order.status.value,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def close_position(client: TradingClient,
                    symbol: str) -> dict:
    """Close an entire position."""
    try:
        resp = client.close_position(symbol.upper())
        return {"success": True, "symbol": symbol}
    except Exception as e:
        return {"success": False, "error": str(e)}


def close_all_positions(client: TradingClient) -> dict:
    """Close all open positions."""
    try:
        client.close_all_positions(cancel_orders=True)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancel_order(client:   TradingClient,
                  order_id: str) -> dict:
    """Cancel a pending order."""
    try:
        client.cancel_order_by_id(order_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Signal Executor ───────────────────────────────────
def execute_signal(client:    TradingClient,
                    symbol:   str,
                    signal:   int,
                    capital:  float,
                    price:    float,
                    pct_size: float = 0.1) -> dict:
    """
    Convert a strategy signal into a live order.

    signal:   1=long, -1=short, 0=close/flat
    pct_size: fraction of capital per position (default 10%)
    """
    positions  = get_positions(client)
    has_long   = (symbol in positions.index and
                  positions.loc[symbol, 'Side'] == 'Long'
                  if not positions.empty and symbol in positions.index
                  else False)
    has_short  = (symbol in positions.index and
                  positions.loc[symbol, 'Side'] == 'Short'
                  if not positions.empty and symbol in positions.index
                  else False)

    position_value = capital * pct_size
    qty            = max(1, int(position_value / price))

    if signal == 1:
        if has_short:
            close_position(client, symbol)
        if not has_long:
            return place_market_order(client, symbol, qty, "buy")

    elif signal == -1:
        if has_long:
            close_position(client, symbol)
        if not has_short:
            return place_market_order(client, symbol, qty, "sell")

    elif signal == 0:
        if has_long or has_short:
            return close_position(client, symbol)

    return {"success": True, "action": "no_change"}


# ── Portfolio History ─────────────────────────────────
def get_portfolio_history(client: TradingClient,
                           period: str = "1M") -> pd.DataFrame:
    """Fetch portfolio equity history."""
    try:
        history = client.get_portfolio_history(
            period      = period,
            timeframe   = "1D",
            extended_hours = False
        )
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(history.timestamp, unit='s'),
            "equity":    history.equity,
            "pnl":       history.profit_loss,
            "pnl_pct":   history.profit_loss_pct,
        })
        return df.set_index("timestamp")
    except Exception as e:
        return pd.DataFrame()