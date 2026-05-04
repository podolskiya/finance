import numpy as np
from models.iv_solver import implied_volatility

def compute_vol_smile(S, T, r, option_type="call", n_strikes=25, spot_range=(0.7, 1.3)):
    """
    Parameters:
        spot_range: low_fraction, high_fraction of S to sweep

    Returns:
        strikes:  strike prices
        ivs: recovered implied vols
        smile_vols: original market vols (for comparison)
    """
    strikes = np.linspace(S * spot_range[0], S * spot_range[1], n_strikes)

    atm_vol = 0.20
    skew = -0.05
    curvature = 0.10
    moneyness = np.log(strikes / S)  
    smile_vols = atm_vol + skew * moneyness + curvature * moneyness**2

    smile_vols = np.clip(smile_vols, 0.01, 2.0)

    from models.black_scholes import black_scholes_price as bsp
    ivs = []
    for K, vol in zip(strikes, smile_vols):
        market_p = bsp(S, K, T, r, vol, option_type)
        iv = implied_volatility(market_p, S, K, T, r, option_type)
        ivs.append(iv if iv else np.nan)

    return strikes, np.array(ivs), smile_vols