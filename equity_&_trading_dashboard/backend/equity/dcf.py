# equity/dcf.py
import numpy as np
import yfinance as yf

def dcf_valuation(ticker: str,
                  growth_rate: float = None,
                  terminal_growth: float = 0.025,
                  discount_rate: float = 0.10,
                  projection_years: int = 5) -> dict:
    """
    Discounted Cash Flow valuation.

    Uses Free Cash Flow as base, projects forward,
    calculates terminal value, discounts to present.

    Returns intrinsic value per share + margin of safety.
    """
    stock = yf.Ticker(ticker)
    info  = stock.info

    # --- Base inputs ---
    fcf          = info.get("freeCashflow", None)
    shares       = info.get("sharesOutstanding", None)
    current_price = info.get("currentPrice", None)
    total_debt   = info.get("totalDebt", 0) or 0
    total_cash   = info.get("totalCash", 0) or 0

    if not all([fcf, shares, current_price]):
        return {"error": "Insufficient data for DCF valuation"}

    # Auto-estimate growth if not provided
    if growth_rate is None:
        rev_growth  = info.get("revenueGrowth", 0.08) or 0.08
        earn_growth = info.get("earningsGrowth", 0.08) or 0.08
        growth_rate = min((rev_growth + earn_growth) / 2, 0.25)  # cap at 25%

    # --- Project FCF ---
    projected_fcf = []
    for year in range(1, projection_years + 1):
        # Gradually fade growth toward terminal rate
        fade   = growth_rate - (growth_rate - terminal_growth) * (year / projection_years)
        if year == 1:
            fcf_proj = fcf * (1 + fade)
        else:
            fcf_proj = projected_fcf[-1] * (1 + fade)
        projected_fcf.append(fcf_proj)

    # --- Discount to present value ---
    pv_fcf = sum(
        cf / (1 + discount_rate) ** (i + 1)
        for i, cf in enumerate(projected_fcf)
    )

    # --- Terminal value (Gordon Growth) ---
    terminal_value    = projected_fcf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal       = terminal_value / (1 + discount_rate) ** projection_years

    # --- Enterprise to Equity ---
    enterprise_value  = pv_fcf + pv_terminal
    equity_value      = enterprise_value - total_debt + total_cash
    intrinsic_value   = equity_value / shares

    # --- Margin of safety ---
    margin_of_safety  = (intrinsic_value - current_price) / intrinsic_value * 100

    # --- Scenarios ---
    bear = intrinsic_value * 0.75
    bull = intrinsic_value * 1.25

    return {
        "ticker":            ticker,
        "current_price":     round(current_price, 2),
        "intrinsic_value":   round(intrinsic_value, 2),
        "margin_of_safety":  round(margin_of_safety, 2),
        "upside_downside":   round((intrinsic_value / current_price - 1) * 100, 2),
        "bear_case":         round(bear, 2),
        "bull_case":         round(bull, 2),
        "assumptions": {
            "growth_rate":      round(growth_rate, 4),
            "terminal_growth":  terminal_growth,
            "discount_rate":    discount_rate,
            "projection_years": projection_years,
            "base_fcf":         round(fcf, 0),
        }
    }