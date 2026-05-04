from scipy.optimize import brentq
from models.black_scholes import black_scholes_price

def implied_volatility(market_price, S, K, T, r, option_type="call", lower=1e-4, upper=10.0, tol=1e-6):
    """
    Returns:
        iv(float)
    """
    if T <= 0:
        return None
    
    intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
    if market_price <= intrinsic:
        return None
    
    def objective(sigma):
        return black_scholes_price(S, K, T, r, sigma, option_type) - market_price
    
    try:
        if objective(lower) * objective(upper) > 0:
            return None
        iv = brentq(objective, lower, upper, xtol=tol, maxiter=500)
        return iv
    except (ValueError, RuntimeError):
        return None
    
def iv_surface(strikes, expiries, market_prices_matrix, S, r, option_type="call"):
    """
    Parameters:
        strikes: strike prices
        expiries: list of expiry times (years)
        market prices matrix: 2D list with [len(expiries)] x2
    
    Returns:
        iv(float)
    """
    iv_matrix = []
    for t_idx, T in enumerate(expiries):
        row = []
        for k_idx, K in enumerate(strikes):
            mp = market_prices_matrix[t_idx][k_idx]
            iv = implied_volatility(mp, S, K, T, r, option_type)
            row.append(iv)
        iv_matrix.append(row)
    return iv_matrix