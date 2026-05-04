import numpy as np

def binomial_tree_price(S, K, T, r, sigma, steps=100, option_type="call", style="european"):
    """
    Cox-Ross-Rubinstein model

    Parameters:
        S:  Spot Price
        K:  Strike Price
        T:  Time to expiry (years)
        r:  Risk-free rate (dec.)
        sigma:  std. dev. (dec.)
        option_type: 'call' or 'put'
        steps: number of time steps
        style: 'european' or 'amercan'

     Returns:
        Option price (float)
    """

    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(r * dt) - d) / (u - d)
    discount = np.exp(-r * dt)

    asset_prices = S * (u ** np.arange(steps, -1, -1)) * (d ** np.arange(0, steps + 1))

    if option_type == "call":
        option_values = np.maximum(asset_prices - K, 0)
    else:
        option_values = np.maximum(K - asset_prices, 0)

    for step in range(steps - 1, -1, -1):
        option_values = discount * (p * option_values[:-1] + (1 - p) * option_values[1:])

        if style == "american":
            current_assets = S * (u ** np.arange(step, -1, -1)) * (d ** np.arange(0, step + 1))
            if option_type == "call":
                intrinsic = np.maximum(current_assets - K, 0)
            else:
                intrinsic = np.maximum(K - current_assets, 0)
            option_values = np.maximum(option_values, intrinsic)

    return float(option_values[0])