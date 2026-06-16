# equity/model_analyser.py
import os
import re
import json
import numpy as np
import pandas as pd
import anthropic


# ── Derived Metrics ────────────────────────────────────
def compute_metrics(canonical: pd.DataFrame) -> dict:
    """Compute growth, margins, FCF, leverage from canonical table."""
    m = {}
    idx = canonical.index

    if "Revenue" in idx:
        rev = canonical.loc["Revenue"].astype(float)
        m['revenue']        = rev
        m['revenue_growth'] = rev.pct_change() * 100
        valid = rev.dropna()
        if len(valid) > 1 and valid.iloc[0] > 0:
            n = len(valid) - 1
            m['revenue_cagr'] = ((valid.iloc[-1] / valid.iloc[0]) ** (1/n) - 1) * 100

    if "Gross Profit" in idx and "Revenue" in idx:
        m['gross_margin'] = canonical.loc["Gross Profit"] / canonical.loc["Revenue"] * 100
    elif "COGS" in idx and "Revenue" in idx:
        m['gross_margin'] = (canonical.loc["Revenue"] - canonical.loc["COGS"]) \
                             / canonical.loc["Revenue"] * 100

    if "EBITDA" in idx and "Revenue" in idx:
        m['ebitda_margin'] = canonical.loc["EBITDA"] / canonical.loc["Revenue"] * 100

    if "Operating Income" in idx and "Revenue" in idx:
        m['operating_margin'] = canonical.loc["Operating Income"] / canonical.loc["Revenue"] * 100

    if "Net Income" in idx and "Revenue" in idx:
        m['net_margin'] = canonical.loc["Net Income"] / canonical.loc["Revenue"] * 100

    if "Operating Cash Flow" in idx and "CapEx" in idx:
        ocf   = canonical.loc["Operating Cash Flow"].astype(float)
        capex = canonical.loc["CapEx"].astype(float).abs()
        m['fcf'] = ocf - capex
        if "Revenue" in idx:
            m['fcf_margin'] = m['fcf'] / canonical.loc["Revenue"] * 100

    if "Total Debt" in idx and "Total Equity" in idx:
        m['debt_equity'] = canonical.loc["Total Debt"] / canonical.loc["Total Equity"]

    if "Net Income" in idx and "Total Equity" in idx:
        m['roe'] = canonical.loc["Net Income"] / canonical.loc["Total Equity"] * 100

    return m


# ── Automated Sanity Checks (Red Flags) ────────────────
def detect_red_flags(canonical: pd.DataFrame, metrics: dict,
                      historical: list, projected: list) -> list:
    flags = []
    idx   = canonical.index

    # 1. Revenue growth assumption vs history
    if 'revenue_growth' in metrics and historical and projected:
        hist_g = metrics['revenue_growth'].reindex(historical).dropna()
        proj_g = metrics['revenue_growth'].reindex(projected).dropna()
        if not hist_g.empty and not proj_g.empty:
            diff = proj_g.mean() - hist_g.mean()
            if diff > 5:
                flags.append({
                    "severity": "warning",
                    "title": "Aggressive Revenue Growth Assumption",
                    "detail": f"Projected growth averages {proj_g.mean():.1f}% vs "
                              f"historical {hist_g.mean():.1f}% — "
                              f"{diff:.1f}pp above trend."
                })
            elif diff < -10:
                flags.append({
                    "severity": "info",
                    "title": "Conservative Growth Assumption",
                    "detail": f"Projections assume growth slows by "
                              f"{abs(diff):.1f}pp vs historical average."
                })

    # 2. Margin expansion assumption
    if 'gross_margin' in metrics and historical and projected:
        hist_m = metrics['gross_margin'].reindex(historical).dropna()
        proj_m = metrics['gross_margin'].reindex(projected).dropna()
        if not hist_m.empty and not proj_m.empty:
            diff = proj_m.mean() - hist_m.mean()
            if diff > 3:
                flags.append({
                    "severity": "warning",
                    "title": "Gross Margin Expansion Assumption",
                    "detail": f"Projections assume gross margin expands "
                              f"{diff:.1f}pp vs historical average "
                              f"({hist_m.mean():.1f}% → {proj_m.mean():.1f}%)."
                })

    # 3. Balance sheet balance check
    if all(i in idx for i in ["Total Assets","Total Liabilities","Total Equity"]):
        assets = canonical.loc["Total Assets"].astype(float)
        liab_eq = canonical.loc["Total Liabilities"].astype(float) \
                  + canonical.loc["Total Equity"].astype(float)
        diff_pct = ((assets - liab_eq).abs() / assets.replace(0, np.nan)).max()
        if pd.notna(diff_pct) and diff_pct > 0.02:
            flags.append({
                "severity": "error",
                "title": "Balance Sheet Doesn't Balance",
                "detail": f"Assets ≠ Liabilities + Equity by up to "
                          f"{diff_pct*100:.1f}% in at least one period."
            })

    # 4. Negative equity
    if "Total Equity" in idx:
        if (canonical.loc["Total Equity"].astype(float) < 0).any():
            flags.append({
                "severity": "error",
                "title": "Negative Equity Detected",
                "detail": "One or more periods show negative shareholders' equity."
            })

    # 5. Net Income vs EBITDA consistency
    if "Net Income" in idx and "EBITDA" in idx:
        ni, eb = canonical.loc["Net Income"].astype(float), canonical.loc["EBITDA"].astype(float)
        if (ni > eb).any():
            flags.append({
                "severity": "warning",
                "title": "Net Income Exceeds EBITDA",
                "detail": "Net income should normally be lower than EBITDA "
                          "after D&A, interest and tax."
            })

    # 6. FCF vs Net Income divergence
    if 'fcf' in metrics and "Net Income" in idx:
        ni = canonical.loc["Net Income"].astype(float)
        common = metrics['fcf'].index.intersection(ni.index)
        if len(common) > 0:
            ratio = (metrics['fcf'][common] / ni[common].replace(0, np.nan)).dropna()
            if not ratio.empty and ratio.mean() < 0.4:
                flags.append({
                    "severity": "warning",
                    "title": "Low Cash Conversion",
                    "detail": f"FCF averages only {ratio.mean()*100:.0f}% of net "
                              f"income — earnings may not be backed by cash."
                })

    if not flags:
        flags.append({
            "severity": "info",
            "title": "No Major Issues Detected",
            "detail": "Automated checks found no structural inconsistencies. "
                      "Review assumptions manually for plausibility."
        })

    return flags


# ── Claude Semantic Review ─────────────────────────────
def ai_model_review(canonical: pd.DataFrame, metrics: dict, flags: list,
                     historical: list, projected: list,
                     reality_check: str | None = None,
                     api_key: str | None = None) -> dict:
    """
    Send the parsed model + computed metrics + red flags to Claude
    for a qualitative assessment of assumption quality.
    """
    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    )

    table_str = canonical.round(2).to_string()
    flags_str = "\n".join([
        f"- [{f['severity'].upper()}] {f['title']}: {f['detail']}"
        for f in flags
    ])

    growth_summary = ""
    if 'revenue_growth' in metrics:
        growth_summary = metrics['revenue_growth'].round(1).to_string()

    reality_block = ""
    if reality_check:
        reality_block = f"\n═══ LIVE MARKET DATA (for sanity-checking model vs reality) ═══\n{reality_check}\n"

    prompt = f"""
You are a senior investment banking associate reviewing a financial model
built by a client. Analyse the parsed line items, growth assumptions,
and automated flags below.

═══ PARSED MODEL (canonical line items × periods) ═══
{table_str}

═══ REVENUE GROWTH BY PERIOD (%) ═══
{growth_summary}

═══ HISTORICAL PERIODS ═══
{historical}

═══ PROJECTED PERIODS ═══
{projected}

═══ AUTOMATED FLAGS ═══
{flags_str}
{reality_block}
═══ YOUR TASK ═══
Return ONLY a valid JSON object with this exact structure:

{{
  "overall_assessment": "2-3 sentence summary of model quality",
  "assumption_quality": "Conservative | Realistic | Aggressive | Inconsistent",
  "key_assumptions": ["assumption 1 with your read on it", "assumption 2", "assumption 3"],
  "strengths": ["strength 1", "strength 2"],
  "concerns": ["concern 1", "concern 2", "concern 3"],
  "missing_items": ["any standard line items you'd expect but don't see"],
  "reality_check": "How well do historical periods in the model match live market data? (or 'No ticker provided for comparison')",
  "questions_for_preparer": ["question 1 you'd ask whoever built this model", "question 2"],
  "confidence_in_projections": 65
}}

Be direct and specific — reference actual numbers from the model.
Do not include any text outside the JSON object.
""".strip()

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}", "raw": raw}
    except Exception as e:
        return {"error": str(e)}


def build_reality_check(ticker: str) -> str | None:
    """Fetch live fundamentals for sanity-checking model historicals."""
    try:
        from equity.fundamentals import get_fundamentals
        f = get_fundamentals(ticker)
        v, p = f['valuation'], f['profitability']
        return (
            f"Company: {f['company'].get('Name')}\n"
            f"Current Gross Margin: {p.get('Gross Margin')}\n"
            f"Current Net Margin:   {p.get('Net Margin')}\n"
            f"Current P/E:          {v.get('P/E (TTM)')}\n"
            f"Revenue Growth (YoY): {f['growth'].get('Revenue Growth (YoY)')}"
        )
    except Exception:
        return None