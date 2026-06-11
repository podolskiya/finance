# equity/ratio_scorer.py
from equity.proprietary_ratios import compute_all_ratios

# ── Industry → Ratio ID Mapping ──────────────────────
# Each sector gets exactly 6 ratio IDs, ordered by importance
INDUSTRY_MAP = {
    "Technology":           [1, 16, 19, 2,  3,  6 ],
    "Healthcare":           [16, 19, 4,  2,  5,  1 ],
    "Financial Services":   [5,  14, 17, 11, 1,  9 ],
    "Financials":           [5,  14, 17, 11, 1,  9 ],
    "Consumer Cyclical":    [4,  6,  7,  8,  17, 14],
    "Consumer Defensive":   [4,  6,  17, 11, 7,  5 ],
    "Consumer Staples":     [4,  6,  17, 11, 7,  5 ],
    "Energy":               [3,  5,  8,  17, 1,  10],
    "Industrials":          [10, 8,  3,  2,  5,  14],
    "Real Estate":          [5,  17, 11, 9,  14, 18],
    "Communication Services":[1, 4,  16, 2,  6,  7 ],
    "Utilities":            [5,  17, 18, 9,  11, 3 ],
    "Materials":            [4,  8,  10, 5,  3,  2 ],
    "Default":              [1,  2,  4,  17, 5,  7 ],
}

# ── Scoring ──────────────────────────────────────────
def score_ratio(ratio: dict) -> int:
    """Return +1 (green), 0 (neutral), -1 (red)."""
    if ratio.get('green_if'):
        return 1
    if ratio.get('red_if'):
        return -1
    return 0


def get_scored_ratios(ticker: str, sector: str) -> dict:
    """
    Compute the 6 sector-relevant ratios and classify
    exactly 2 as Green, 2 as Neutral, 2 as Red.

    Always returns 2/2/2 split — even great companies
    show relative weaknesses; poor ones show strengths.
    This is the key design choice.
    """
    all_ratios = compute_all_ratios(ticker)

    # Get the right 6 IDs for this sector
    sector_key = next(
        (k for k in INDUSTRY_MAP if k.lower() in sector.lower()),
        "Default"
    )
    ids = INDUSTRY_MAP[sector_key]

    # Collect available ratios in sector order
    available = []
    for rid in ids:
        if rid in all_ratios:
            r          = all_ratios[rid].copy()
            r['id']    = rid
            r['score'] = score_ratio(r)
            available.append(r)

    # Pad with defaults if not enough data
    while len(available) < 6:
        for rid, r in all_ratios.items():
            if rid not in [a['id'] for a in available]:
                r2          = r.copy()
                r2['id']    = rid
                r2['score'] = score_ratio(r2)
                available.append(r2)
                if len(available) == 6:
                    break

    available = available[:6]

    # Sort by score descending (best to worst)
    available.sort(key=lambda x: x['score'], reverse=True)

    # Always assign exactly 2/2/2
    green   = available[:2]
    neutral = available[2:4]
    red     = available[4:6]

    for r in green:   r['bucket'] = 'green'
    for r in neutral: r['bucket'] = 'neutral'
    for r in red:     r['bucket'] = 'red'

    return {
        "green":   green,
        "neutral": neutral,
        "red":     red,
        "sector":  sector_key,
        "all":     available,
    }


# ── Business Quality Matrix Scores ───────────────────
def bqm_scores(all_ratios: dict) -> dict:
    """
    Compute the two BQM axis scores (0–100 each).

    Earnings Quality axis:
      Composite of EQS(1), CCQ(9), FCFY(17)

    Capital Efficiency axis:
      Composite of CER(2), CMI(12), AP(10)
    """
    def normalise(val, low, high):
        if val is None:
            return 50.0
        return max(0, min(100, (val - low) / (high - low) * 100))

    # Earnings Quality components
    eq_scores = []
    if 1  in all_ratios:
        eq_scores.append(normalise(all_ratios[1]['value'],  0.4, 1.8))
    if 9  in all_ratios:
        eq_scores.append(normalise(all_ratios[9]['value'],  0.4, 1.0))
    if 17 in all_ratios:
        eq_scores.append(normalise(all_ratios[17]['value'], 0.0, 8.0))

    # Capital Efficiency components
    ce_scores = []
    if 2  in all_ratios:
        ce_scores.append(normalise(all_ratios[2]['value'],  0.3, 3.0))
    if 12 in all_ratios:
        ce_scores.append(normalise(all_ratios[12]['value'],-5.0,15.0))
    if 10 in all_ratios:
        ce_scores.append(normalise(all_ratios[10]['value'], 0.1, 1.5))

    eq = float(sum(eq_scores) / len(eq_scores)) if eq_scores else 50.0
    ce = float(sum(ce_scores) / len(ce_scores)) if ce_scores else 50.0

    # Quadrant label
    if   eq >= 50 and ce >= 50: quad = ("Capital Compounder", "#10B981")
    elif eq >= 50 and ce <  50: quad = ("Zombie Business",    "#F59E0B")
    elif eq <  50 and ce >= 50: quad = ("Growth at All Costs","#3B82F6")
    else:                        quad = ("Value Trap",         "#EF4444")

    return {
        "earnings_quality":   round(eq, 1),
        "capital_efficiency": round(ce, 1),
        "quadrant":           quad[0],
        "quadrant_color":     quad[1],
    }