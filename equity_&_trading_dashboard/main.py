# main.py
from equity.fundamentals import get_fundamentals
from equity.dcf import dcf_valuation
from equity.comparables import get_comparables, investment_verdict

TICKER = "AAPL"

print(f"\n{'='*50}")
print(f"  EQUITY ANALYSIS: {TICKER}")
print(f"{'='*50}")

# Fundamentals
print("\n[1/3] Fetching fundamentals...")
fund = get_fundamentals(TICKER)
print(f"\n  Company : {fund['company']['Name']}")
print(f"  Sector  : {fund['company']['Sector']}")
for k, v in fund['valuation'].items():
    if v: print(f"  {k}: {v}")

# DCF
print("\n[2/3] Running DCF valuation...")
dcf = dcf_valuation(TICKER)
print(f"\n  Current Price   : ${dcf['current_price']}")
print(f"  Intrinsic Value : ${dcf['intrinsic_value']}")
print(f"  Margin of Safety: {dcf['margin_of_safety']}%")
print(f"  Bull Case       : ${dcf['bull_case']}")
print(f"  Bear Case       : ${dcf['bear_case']}")

# Comparables
print("\n[3/3] Running comparables analysis...")
comps = get_comparables(TICKER)
print(f"\n{comps.to_string()}")

# Verdict
verdict = investment_verdict(TICKER, dcf, comps)
print(f"\n{'='*50}")
print(f"  VERDICT  : {verdict['verdict']}")
print(f"  CONFIDENCE: {verdict['confidence']}")
print(f"  UPSIDE   : {verdict['upside']}")
print(f"\n  Reasoning:")
for r in verdict['reasoning']:
    print(f"    → {r}")
print(f"{'='*50}")