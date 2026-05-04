import numpy as np

def asian_option_price(S, K, T, r, sigma, simulations=20_000,
                       steps=252, option_type="call", seed=42):
    """
    Call payoff: max(avg(S_t) - K, 0)
    Put payoff:  max(K - avg(S_t), 0)
    """
    rng = np.random.default_rng(seed)
    dt = T / steps
    drift = (r - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)

    Z = rng.standard_normal((simulations, steps))
    log_returns = drift + diffusion * Z
    log_paths = np.cumsum(log_returns, axis=1)
    paths = S * np.exp(np.hstack([np.zeros((simulations, 1)), log_paths]))

    avg_prices = paths.mean(axis=1)

    if option_type == "call":
        payoffs = np.maximum(avg_prices - K, 0)
    else:
        payoffs = np.maximum(K - avg_prices, 0)

    price = float(np.exp(-r * T) * np.mean(payoffs))
    std_err = float(np.std(payoffs) / np.sqrt(simulations))
    return price, std_err


def barrier_option_price(S, K, T, r, sigma, barrier, barrier_type="down-and-out",
                         simulations=20_000, steps=252,
                         option_type="call", seed=42):
    """
    Barrier types:
        'down-and-out': Knocked out if spot FALLS below barrier
        'down-and-in': Activated only if spot FALLS below barrier
        'up-and-out': Knocked out if spot RISES above barrier
        'up-and-in': Activated only if spot RISES above barrier
    """
    rng = np.random.default_rng(seed)
    dt = T / steps
    drift = (r - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)

    Z = rng.standard_normal((simulations, steps))
    log_returns = drift + diffusion * Z
    log_paths = np.cumsum(log_returns, axis=1)
    paths = S * np.exp(np.hstack([np.zeros((simulations, 1)), log_paths]))

    S_T = paths[:, -1]  

    if "down" in barrier_type:
        crossed = np.any(paths <= barrier, axis=1)  
    else:  
        crossed = np.any(paths >= barrier, axis=1)  

    if "out" in barrier_type:
        active = ~crossed
    else:
        active = crossed


    if option_type == "call":
        intrinsic = np.maximum(S_T - K, 0)
    else:
        intrinsic = np.maximum(K - S_T, 0)

    payoffs = intrinsic * active.astype(float)

    price = float(np.exp(-r * T) * np.mean(payoffs))
    std_err = float(np.std(payoffs) / np.sqrt(simulations))
    return price, std_err