import numpy as np
from scipy.stats import norm

def d1(S, K, T, r, sigma):
    return (np.log(S/K) + (r + 0.5 * sigma **2) * T) / (sigma * np.sqrt(T))

def d2(S, K, T, r, sigma):
    return d1(S, K, T, r, sigma) - sigma * np.sqrt(T)

def black_scholes_price(S, K, T, r, sigma, option_type="call"):
    """
    Black-Scholes option price.

    Parameters:
        S:  Spot Price
        K:  Strike Price
        T:  Time to expiry (years)
        r:  Risk-free rate (dec.)
        sigma:  std. dev. (dec.)
        simulations: # of price paths
        steps: time steps per path
        option_type: 'call' or 'put'
        seed: random

    Returns:
        Option price (float)
    """

    if T <= 0:
        if option_type == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)
        
    _d1 = d1(S, K, T, r, sigma)
    _d2 = d2(S, K, T, r, sigma)

    if option_type == "call":
        price = S * norm.cdf(_d1) - K * np.exp(-r * T) * norm.cdf(_d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-_d2) - S * norm.cdf(-_d1)
    
    return price