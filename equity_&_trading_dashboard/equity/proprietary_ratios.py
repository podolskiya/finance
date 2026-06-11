# equity/proprietary_ratios.py
import numpy as np
import pandas as pd
import yfinance as yf

def _safe(val, default=None):
    if val in [None, float('inf'), float('-inf')]:
        return default
    try:
        return float(val)
    except:
        return default


def estimate_wacc(info: dict, financials: pd.DataFrame) -> float:
    """
    Estimate WACC using CAPM for cost of equity.
    WACC = E/(E+D) * CoE + D/(E+D) * CoD * (1 - tax)
    """
    try:
        beta       = _safe(info.get('beta'), 1.0)
        rf         = 0.045
        mrp        = 0.055
        coe        = rf + beta * mrp

        total_debt = _safe(info.get('totalDebt'), 0)
        mkt_cap    = _safe(info.get('marketCap'), 1)
        cash       = _safe(info.get('totalCash'), 0)

        int_exp = 0
        if financials is not None and not financials.empty:
            for label in ['Interest Expense', 'Interest Expense Non Operating']:
                if label in financials.index:
                    int_exp = abs(_safe(
                        financials.loc[label].iloc[0], 0
                    ))
                    break

        cod = int_exp / total_debt if total_debt > 0 else 0.04

        tax = 0.21
        if financials is not None and not financials.empty:
            try:
                pretax = _safe(
                    financials.loc['Pretax Income'].iloc[0], None
                )
                tax_exp = _safe(
                    financials.loc['Tax Provision'].iloc[0], None
                )
                if pretax and tax_exp and pretax > 0:
                    tax = tax_exp / pretax
                    tax = min(max(tax, 0), 0.45)
            except:
                pass

        E = mkt_cap
        D = max(total_debt, 0)
        total = E + D
        if total == 0:
            return coe

        wacc = (E/total)*coe + (D/total)*cod*(1 - tax)
        return max(wacc, 0.04)   # floor at 4% #
    except:
        return 0.09

# Proprietary ratios that aim at addressing some limitations of existing ones #

def estimate_roic(info: dict,
                   financials: pd.DataFrame) -> float | None:
    """
    ROIC = NOPAT / Invested Capital
    NOPAT = EBIT * (1 - tax)
    IC    = Total Equity + Total Debt - Cash
    """
    try:
        ebit = None
        tax  = 0.21
        if financials is not None and not financials.empty:
            for label in ['EBIT', 'Operating Income']:
                if label in financials.index:
                    ebit = _safe(financials.loc[label].iloc[0])
                    break
            try:
                pretax  = _safe(financials.loc['Pretax Income'].iloc[0])
                tax_exp = _safe(financials.loc['Tax Provision'].iloc[0])
                if pretax and tax_exp and pretax > 0:
                    tax = min(max(tax_exp/pretax, 0), 0.45)
            except:
                pass

        if ebit is None:
            return None

        nopat   = ebit * (1 - tax)
        equity  = _safe(info.get('bookValue', 0)) * \
                  _safe(info.get('sharesOutstanding', 1))
        debt    = _safe(info.get('totalDebt'), 0)
        cash    = _safe(info.get('totalCash'), 0)
        ic      = equity + debt - cash
        if ic <= 0:
            return None
        return nopat / ic
    except:
        return None


def compute_all_ratios(ticker: str) -> dict:
    """
    Compute all 20 proprietary ratios for a ticker.
    Returns dict of {ratio_id: {"value": x, "display": "...", "raw": x}}
    """
    stock = yf.Ticker(ticker)
    info  = stock.info
    fin   = stock.financials          # annual income statement
    bal   = stock.balance_sheet       # annual balance sheet
    cf    = stock.cashflow            # annual cash flow

    def fi(df, *labels):
        """Safe financial item fetch."""
        if df is None or df.empty:
            return None
        for label in labels:
            if label in df.index:
                v = df.loc[label]
                for col in v.index:
                    val = _safe(v[col])
                    if val is not None and val != 0:
                        return val
        return None

    def fi2(df, *labels):
        """Fetch two most recent periods."""
        if df is None or df.empty:
            return None, None
        for label in labels:
            if label in df.index:
                row = df.loc[label]
                vals = [_safe(row.iloc[i]) for i in range(min(2, len(row)))]
                while len(vals) < 2:
                    vals.append(None)
                return vals[0], vals[1]
        return None, None

    results = {}

    ocf = fi(cf, 'Operating Cash Flow', 'Cash From Operations')
    ni  = fi(fin, 'Net Income', 'Net Income Common Stockholders')
    if ocf and ni and ni != 0:
        val = ocf / ni
        results[1] = {
            "name":    "Earnings Quality Score",
            "value":   round(val, 2),
            "display": f"{val:.2f}x",
            "desc":    "OCF / Net Income — are profits backed by real cash?",
            "pitfall": "Fixes: EPS can be inflated via accruals; OCF cannot.",
            "green_if": val > 1.0,
            "red_if":   val < 0.7,
        }

    roic = estimate_roic(info, fin)
    wacc = estimate_wacc(info, fin)
    if roic is not None and wacc and wacc > 0:
        val = roic / wacc
        results[2] = {
            "name":    "Capital Efficiency Ratio",
            "value":   round(val, 2),
            "display": f"{val:.2f}x",
            "desc":    "ROIC / WACC — is capital being deployed above its cost?",
            "pitfall": "Fixes: ROIC alone is meaningless without cost of capital context.",
            "green_if": val > 1.5,
            "red_if":   val < 0.8,
        }

    capex = abs(fi(cf, 'Capital Expenditure', 'Purchase Of PPE') or 0)
    rd    = abs(fi(fin, 'Research And Development', 'Research Development') or 0)
    if ocf and ocf > 0:
        val = (capex + rd) / ocf
        results[3] = {
            "name":    "Reinvestment Health",
            "value":   round(val, 2),
            "display": f"{val*100:.0f}%",
            "desc":    "(CapEx + R&D) / OCF — is reinvestment sustainable?",
            "pitfall": "Fixes: CapEx/Revenue ignores whether the company has cash to reinvest.",
            "green_if": 0.2 <= val <= 0.65,
            "red_if":   val < 0.05 or val > 1.0,
        }

    gm0, gm1 = fi2(fin, 'Gross Profit')
    rev0, rev1 = fi2(fin, 'Total Revenue')
    if all(v is not None for v in [gm0, gm1, rev0, rev1]) \
            and rev0 > 0 and rev1 > 0:
        margin_now  = gm0 / rev0
        margin_prev = gm1 / rev1
        val         = (margin_now - margin_prev) * 100  # pp change
        results[4] = {
            "name":    "Pricing Power Index",
            "value":   round(val, 2),
            "display": f"{val:+.1f}pp",
            "desc":    "YoY gross margin change — can they raise prices?",
            "pitfall": "Fixes: Revenue growth masks margin compression from pricing pressure.",
            "green_if": val > 1.0,
            "red_if":   val < -1.5,
        }

    debt    = _safe(info.get('totalDebt'), 0)
    cash_v  = _safe(info.get('totalCash'), 0)
    net_debt = debt - cash_v
    if ocf and ocf > 0:
        val = net_debt / ocf
        results[5] = {
            "name":    "Balance Sheet Stress Score",
            "value":   round(val, 2),
            "display": f"{val:.1f}x",
            "desc":    "Net Debt / OCF — years of cash flow needed to clear debt.",
            "pitfall": "Fixes: D/E distorted by equity buybacks; OCF gives real picture.",
            "green_if": val < 2.0,
            "red_if":   val > 6.0,
        }

    # Proxy: stability of gross margins over time (low std = durable) #
    gm_vals = []
    if fin is not None and not fin.empty:
        for label in ['Gross Profit', 'Gross Margin']:
            if label in fin.index:
                for i in range(min(4, fin.shape[1])):
                    r = _safe(fin.loc[label].iloc[i])
                    rv_label = 'Total Revenue'
                    if rv_label in fin.index:
                        rv = _safe(fin.loc[rv_label].iloc[i])
                        if r and rv and rv > 0:
                            gm_vals.append(r/rv)
                break
    if len(gm_vals) >= 2:
        val = np.std(gm_vals) * 100
        results[6] = {
            "name":    "Revenue Durability",
            "value":   round(val, 2),
            "display": f"{val:.1f}%",
            "desc":    "Gross margin std dev — how stable/predictable is the business?",
            "pitfall": "Fixes: Revenue growth hides volatile, cyclical income streams.",
            "green_if": val < 3.0,
            "red_if":   val > 8.0,
        }

    rev_g  = _safe(info.get('revenueGrowth'))
    de_now = _safe(info.get('debtToEquity'), 0) / 100
    de_bal = fi(bal, 'Total Debt')
    eq_bal = fi(bal, 'Stockholders Equity', 'Common Stock Equity')
    if rev_g is not None and de_now is not None:
        # Penalise growth fuelled by debt expansion
        debt_growth = abs(de_now * 0.1)  # approximate change
        val = rev_g / (1 + debt_growth) if (1 + debt_growth) > 0 else rev_g
        val *= 100
        results[7] = {
            "name":    "Growth Sustainability Ratio",
            "value":   round(val, 2),
            "display": f"{val:.1f}%",
            "desc":    "Revenue growth adjusted for leverage expansion.",
            "pitfall": "Fixes: Raw revenue growth ignores debt-fuelled growth masking weakness.",
            "green_if": val > 12.0,
            "red_if":   val < 0.0,
        }

    ebit0 = fi(fin, 'EBIT', 'Operating Income')
    ebit1, _ = fi2(fin, 'EBIT', 'Operating Income')
    rev0_v, rev1_v = fi2(fin, 'Total Revenue')
    if all(v is not None for v in [ebit0, rev0_v, rev1_v]) \
            and ebit1 is not None \
            and rev1_v and rev1_v != 0 and ebit1 != 0:
        ebit_g = (ebit0 - ebit1) / abs(ebit1)
        rev_g2 = (rev0_v - rev1_v) / rev1_v
        if rev_g2 != 0:
            val = ebit_g / rev_g2
            results[8] = {
                "name":    "Operational Leverage Score",
                "value":   round(val, 2),
                "display": f"{val:.2f}x",
                "desc":    "EBIT growth / Revenue growth — fixed cost operating leverage.",
                "pitfall": "Fixes: Revenue growth doesn't reveal profit scalability.",
                "green_if": 1.2 <= val <= 3.0,
                "red_if":   val < 0.5 or val > 5.0,
            }

    ebitda = _safe(info.get('ebitda'))
    if ocf and ebitda and ebitda > 0:
        val = ocf / ebitda
        results[9] = {
            "name":    "Cash Conversion Quality",
            "value":   round(val, 2),
            "display": f"{val:.2f}x",
            "desc":    "OCF / EBITDA — how much EBITDA converts to real cash?",
            "pitfall": "Fixes: EBITDA ignores CapEx, working capital, and tax — OCF does not.",
            "green_if": val > 0.85,
            "red_if":   val < 0.55,
        }

    rev_v  = _safe(info.get('totalRevenue'))
    assets = fi(bal, 'Total Assets')
    if rev_v and assets and assets > 0:
        val = rev_v / assets
        results[10] = {
            "name":    "Asset Productivity",
            "value":   round(val, 2),
            "display": f"{val:.2f}x",
            "desc":    "Revenue / Total Assets — how efficiently are assets deployed?",
            "pitfall": "Fixes: Return on assets misses asset-light business models.",
            "green_if": val > 0.8,
            "red_if":   val < 0.3,
        }

    insider_pct = _safe(info.get('heldPercentInsiders'), 0) * 100
    buyback     = fi(cf, 'Repurchase Of Capital Stock', 'Common Stock Repurchased')
    mkt_cap_v   = _safe(info.get('marketCap'), 1)
    buyback_y   = abs(buyback) / mkt_cap_v if buyback and mkt_cap_v else 0
    val         = insider_pct + buyback_y * 100
    results[11] = {
        "name":    "Management Alignment",
        "value":   round(val, 2),
        "display": f"{val:.1f}%",
        "desc":    "Insider ownership + buyback yield — skin in the game.",
        "pitfall": "Fixes: Options-heavy comp misaligns management; ownership & buybacks align.",
        "green_if": val > 8.0,
        "red_if":   val < 2.0,
    }

    if roic is not None and wacc:
        val = (roic - wacc) * 100
        results[12] = {
            "name":    "Competitive Moat Indicator",
            "value":   round(val, 2),
            "display": f"{val:+.1f}%",
            "desc":    "ROIC − WACC — sustained excess returns signal a real moat.",
            "pitfall": "Fixes: ROIC alone doesn't show if returns exceed the cost to achieve them.",
            "green_if": val > 5.0,
            "red_if":   val < 0.0,
        }

    try:
        eh = stock.earnings_history
        if eh is not None and not eh.empty \
                and 'epsActual' in eh.columns \
                and 'epsEstimate' in eh.columns:
            beats  = (eh['epsActual'] >= eh['epsEstimate']).astype(int)
            recent = beats.iloc[:4].tolist()
            consec = 0
            for b in recent:
                if b == 1:
                    consec += 1
                else:
                    break
            val = consec
            results[13] = {
                "name":    "Earnings Surprise Momentum",
                "value":   val,
                "display": f"{val}/4 beats",
                "desc":    "Consecutive EPS beats — management credibility signal.",
                "pitfall": "Fixes: Single EPS miss is noise; pattern of beats/misses is signal.",
                "green_if": val >= 3,
                "red_if":   val == 0,
            }
    except:
        pass

    wc0_cur = fi(bal, 'Current Assets')
    wc0_cur_l = fi(bal, 'Current Liabilities')
    if wc0_cur and wc0_cur_l and rev_v and rev_v > 0:
        wc   = wc0_cur - wc0_cur_l
        val  = abs(wc) / rev_v * 100
        results[14] = {
            "name":    "Working Capital Efficiency",
            "value":   round(val, 2),
            "display": f"{val:.1f}%",
            "desc":    "|Working Capital| / Revenue — cash tied up in operations.",
            "pitfall": "Fixes: Current ratio ignores whether WC is proportionate to revenue.",
            "green_if": val < 10.0,
            "red_if":   val > 25.0,
        }

    price_v    = _safe(info.get('currentPrice'))
    fcf_v      = _safe(info.get('freeCashflow'))
    shares_v   = _safe(info.get('sharesOutstanding'), 1)
    tgrowth    = 0.025
    discount   = 0.10
    if fcf_v and shares_v and price_v:
        intrinsic  = (fcf_v * (1 + tgrowth)) / (discount - tgrowth) / shares_v
        val        = (intrinsic - price_v) / price_v * 100
        results[15] = {
            "name":    "Margin Safety Buffer",
            "value":   round(val, 2),
            "display": f"{val:+.0f}%",
            "desc":    "(Intrinsic − Price) / Price — downside cushion vs fair value.",
            "pitfall": "Fixes: P/E doesn't show distance from intrinsic value.",
            "green_if": val > 20.0,
            "red_if":   val < -20.0,
        }

    rev_g_v = _safe(info.get('revenueGrowth'))
    rd_pct  = rd / rev_v if rd and rev_v else None
    if rev_g_v is not None and rd_pct and rd_pct > 0:
        val = rev_g_v / rd_pct
        results[16] = {
            "name":    "R&D Efficiency Score",
            "value":   round(val, 2),
            "display": f"{val:.2f}x",
            "desc":    "Revenue growth / R&D intensity — innovation ROI.",
            "pitfall": "Fixes: R&D spend alone rewards quantity over quality of innovation.",
            "green_if": val > 2.0,
            "red_if":   val < 0.5,
        }

    if fcf_v and mkt_cap_v and mkt_cap_v > 0:
        val = fcf_v / mkt_cap_v * 100
        results[17] = {
            "name":    "Free Cash Flow Yield",
            "value":   round(val, 2),
            "display": f"{val:.1f}%",
            "desc":    "FCF / Market Cap — earnings yield backed by real cash.",
            "pitfall": "Fixes: P/E is distorted by non-cash charges and accrual accounting.",
            "green_if": val > 4.0,
            "red_if":   val < 1.0,
        }

    st_debt = fi(bal, 'Current Debt', 'Short Term Debt',
                 'Current Portion Of Long Term Debt')
    lt_debt = fi(bal, 'Long Term Debt')
    if st_debt is not None and lt_debt is not None:
        total_d = st_debt + lt_debt
        if total_d > 0:
            val = st_debt / total_d * 100
            results[18] = {
                "name":    "Debt Maturity Risk",
                "value":   round(val, 2),
                "display": f"{val:.0f}%",
                "desc":    "Short-term debt / Total debt — near-term refinancing pressure.",
                "pitfall": "Fixes: Total debt ignores WHEN it matures — near-term debt is urgent.",
                "green_if": val < 20.0,
                "red_if":   val > 55.0,
            }

    rd_now, rd_prev = fi2(fin, 'Research And Development',
                           'Research Development')
    rev_n, rev_p    = fi2(fin, 'Total Revenue')
    if all(v is not None and v != 0
           for v in [rd_now, rd_prev, rev_n, rev_p]):
        rd_g  = (rd_now - rd_prev) / abs(rd_prev)
        rev_g3 = (rev_n  - rev_p ) / abs(rev_p )
        if rev_g3 != 0:
            val = rd_g / rev_g3
            results[19] = {
                "name":    "Innovation Pipeline Score",
                "value":   round(val, 2),
                "display": f"{val:.2f}x",
                "desc":    "R&D growth / Revenue growth — investing in the future?",
                "pitfall": "Fixes: R&D as % of revenue misses acceleration vs deceleration.",
                "green_if": val > 1.5,
                "red_if":   val < 0.5,
            }

    fcfy     = results.get(17, {}).get('value', 0) or 0
    by       = (abs(buyback) / mkt_cap_v * 100
                if buyback and mkt_cap_v else 0)
    cod_pct  = (fi(fin, 'Interest Expense') or 0) / (debt or 1) * 100
    val      = fcfy + by - cod_pct
    results[20] = {
        "name":    "Shareholder Value Index",
        "value":   round(val, 2),
        "display": f"{val:+.1f}%",
        "desc":    "FCF Yield + Buyback Yield − Debt Cost — net value returned to shareholders.",
        "pitfall": "Fixes: Dividend yield alone ignores buybacks and debt servicing cost.",
        "green_if": val > 5.0,
        "red_if":   val < 0.0,
    }

    return results