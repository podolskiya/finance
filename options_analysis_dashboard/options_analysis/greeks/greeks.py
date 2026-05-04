import numpy as np
from scipy.stats import norm
from models.black_scholes import d1, d2

def delta(S, K, T, r, sigma, option_type="call"):
    if T <= 0:
        if option_type == "call":
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    _d1 = d1(S, K, T, r, sigma)
    if option_type == "call":
        return norm.cdf(_d1)
    else:
        return norm.cdf(_d1) - 1


def gamma(S, K, T, r, sigma):
    if T <= 0:
        return 0.0
    _d1 = d1(S, K, T, r, sigma)
    return norm.pdf(_d1) / (S * sigma * np.sqrt(T))


def vega(S, K, T, r, sigma):
    if T <= 0:
        return 0.0
    _d1 = d1(S, K, T, r, sigma)
    return S * norm.pdf(_d1) * np.sqrt(T) * 0.01  


def theta(S, K, T, r, sigma, option_type="call"):
    if T <= 0:
        return 0.0
    _d1 = d1(S, K, T, r, sigma)
    _d2 = d2(S, K, T, r, sigma)
    term1 = -(S * norm.pdf(_d1) * sigma) / (2 * np.sqrt(T))
    if option_type == "call":
        return (term1 - r * K * np.exp(-r * T) * norm.cdf(_d2)) / 365
    else:
        return (term1 + r * K * np.exp(-r * T) * norm.cdf(-_d2)) / 365


def rho(S, K, T, r, sigma, option_type="call"):
    if T <= 0:
        return 0.0
    _d2 = d2(S, K, T, r, sigma)
    if option_type == "call":
        return K * T * np.exp(-r * T) * norm.cdf(_d2) * 0.01
    else:
        return -K * T * np.exp(-r * T) * norm.cdf(-_d2) * 0.01



def greeks_vs_spot(S_range, K, T, r, sigma, option_type="call"):
    return {
        "delta":  [delta(S, K, T, r, sigma, option_type) for S in S_range],
        "gamma":  [gamma(S, K, T, r, sigma) for S in S_range],
        "vega":   [vega(S, K, T, r, sigma) for S in S_range],
        "theta":  [theta(S, K, T, r, sigma, option_type) for S in S_range],
        "rho":    [rho(S, K, T, r, sigma, option_type) for S in S_range],
    }


def greeks_vs_vol(S, K, T, r, sigma_range, option_type="call"):
    return {
        "delta":  [delta(S, K, T, r, sig, option_type) for sig in sigma_range],
        "gamma":  [gamma(S, K, T, r, sig) for sig in sigma_range],
        "vega":   [vega(S, K, T, r, sig) for sig in sigma_range],
        "theta":  [theta(S, K, T, r, sig, option_type) for sig in sigma_range],
        "rho":    [rho(S, K, T, r, sig, option_type) for sig in sigma_range],
    }


def greeks_vs_time(S, K, T_range, r, sigma, option_type="call"):
    return {
        "delta":  [delta(S, K, T, r, sigma, option_type) for T in T_range],
        "gamma":  [gamma(S, K, T, r, sigma) for T in T_range],
        "vega":   [vega(S, K, T, r, sigma) for T in T_range],
        "theta":  [theta(S, K, T, r, sigma, option_type) for T in T_range],
        "rho":    [rho(S, K, T, r, sigma, option_type) for T in T_range],
    }