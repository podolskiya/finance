import numpy as np


def monte_carlo_price(S, K, T, r, sigma, simulations=10_000, steps=252, option_type="call", seed=42):
    """
    Monte Carlo Geometric Brownian Motion.

    Parameters:
        S           : Spot price
        K           : Strike price
        T           : Time to expiry (years)
        r           : Risk-free rate (decimal)
        sigma       : Volatility (decimal)
        simulations : Number of price paths
        steps       : Time steps per path
        option_type : 'call' or 'put'
        seed        : Random seed for reproducibility

    Returns:
        price (float), std_error (float), paths (ndarray for charting)
    """
    rng = np.random.default_rng(seed)

    dt = T / steps
    drift = (r - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)
    
    drift = (r - 0.5 * sigma**2) * dt

    Z = rng.standard_normal((simulations, steps))
    log_returns = drift + diffusion * Z

    log_paths = np.cumsum(log_returns, axis=1)
    paths = S * np.exp(np.hstack([np.zeros((simulations, 1)), log_paths]))

    S_T = paths[:, -1]
    if option_type == "call":
        payoffs = np.maximum(S_T - K, 0)
    else:
        payoffs = np.maximum(K - S_T, 0)

    discounted_payoffs = np.exp(-r * T) * payoffs
    price = float(np.mean(discounted_payoffs))
    std_error = float(np.std(discounted_payoffs) / np.sqrt(simulations))

    sample_paths = paths[:200, :]

    return price, std_error, sample_paths