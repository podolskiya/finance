<h1> Options Pricing & Greeks Dashboard </h1>

A quantitative finance dashboard that prices options across three models simultaneously and visualises how the Greeks evolve as market parameters change in real time.

<img width="1865" height="852" alt="Screenshot 2026-05-05 203449" src="https://github.com/user-attachments/assets/1b99dc65-7aa5-488a-9868-261a391e3b1b" />

Computes option prices and sensitivities using three independent models and displays them side by side so you can see where they agree, where they diverge, and why. Every chart is interactive - adjust any parameter in the sidebar and the entire dashboard updates live.

The project covers vanilla European and American options, Greeks across all five dimensions, implied volatility inversion, exotic options (Asian and Barrier), and live market data via yfinance.

<img width="1881" height="855" alt="Screenshot 2026-05-05 203554" src="https://github.com/user-attachments/assets/96df42a9-0063-4773-88b5-72a8a00b7027" />

<h3>Black-Scholes</h3>
Closed-form solution for European options. Serves as the benchmark that the other two models converge toward. Computed instantly at every parameter change.

<h3>CRR Binomial Tree</h3>
Cox-Ross-Rubinstein lattice model with configurable step count (def. 200). Supports both European and American exercise. The convergence chart shows the tree price locking onto the BS price as steps increase fo sanity check.

<h3>Monte Carlo0</h3>
Geometric Brownian Motion simulation with configurable path count (default 10,000). Returns a price estimate, a standard error, and a set of 200 sample paths for visualisation. The 95% confidence interval included.

<img width="1882" height="814" alt="Screenshot 2026-05-05 202211" src="https://github.com/user-attachments/assets/96de65db-3f1f-425f-b16a-d7e12aca7eac" />

<h2>Other Features</h2>
1) Greeks Dashboard (Delta, Gamma, Vega, Theta, Rho)
2) Greeks Sensitivity Analysis
3) 3D Greek Surface
4) Implied Volatility Solver (function = BS price σ - market price)
5) Volatility Smile (function = BS price σ - market price)
6) Exotic Options (function = BS price σ - market price)
7) Binomial Tree Convergence
8) Monte Carlo Path Visualisation
9) Live Market Data (yfinance)

<h2>Getting Started</h2>
<b>Step 1:</b> Clone the repository 
git clone [https://github.com/podolskiya/finance/tree/main/options_analysis_dashboard/options_analysis]
cd optioniq

<b>Step 2:</b> Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

<b>Step 3:</b> Install dependencies
python -m venv venv

<b>Step 4:</b> Run
streamlit run app.py
