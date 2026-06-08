"""
02_clean_panel.py
-----------------
PURPOSE
    Apply all sample filters, handle missing values, winsorise, and
    construct L_it and all sensitivity variants.

INPUT   data/clean/panel_raw.parquet
OUTPUT  data/clean/panel_clean.parquet
        data/clean/panel_clean.csv
        data/clean/cleaning_log.txt

CLEANING STEPS
    1.  Keep FFIEC 031 filers only
    2.  Apply minimum asset size filter ($300m)
    3.  Drop observations with missing total assets
    4.  Flag and drop merger quarters (>50pct asset jump in one quarter)
    5.  Fill missing off-balance-sheet items with zero (031 filers all file RC-L)
    6.  Exclude rcfd3818 entirely -- see note below
    7.  Winsorise each component at 1st/99th percentile
    8.  Construct L_it and sensitivity variants
    9.  Winsorise the final L_it ratio itself at 99th percentile
    10. Construct control and outcome variables
    11. Final column selection, sort, and save

L_IT CONSTRUCTION
    Main:   L_it = (rcfd3819 + rcfd3433 + rcfdj458) / rcfd2170
            rcfd3819  Financial standby letters of credit  [2005-2023, full]
            rcfd3433  Securities lent with cash collateral [2005-2023, full]
            rcfdj458  Unused commitments to FIs            [2010-2023; zero for 2005-2009]
            rcfd2170  Total assets (denominator)

    WHY NOT rcfd3818:
            rcfd3818 is the aggregate of ALL unused commitments not classified
            elsewhere. For 031 trust-company filers it routinely exceeds total
            assets (ratio > 1), contaminating L_it with non-NBFI commitments.
            It was retired by FFIEC in 2010 and replaced by rcfdj457/458/459.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    CLEAN, FILING_TYPE, MIN_ASSETS_USD,
    WINSOR_LOWER, WINSOR_HIGH, F_PANEL, F_PANEL_CSV,
)


def _winsorise(series, lower=WINSOR_LOWER, upper=WINSOR_HIGH):
    lo = series.quantile(lower)
    hi = series.quantile(upper)
    return series.clip(lower=lo, upper=hi)


def _log(log, label, df):
    entry = (f"{label:<55} "
             f"rows={len(df):>8,}  "
             f"banks={df['rssd9001'].nunique():>5,}")
    log.append(entry)
    print(f"  {entry}")


def main():
    print("\n" + "=" * 65)
    print("02_clean_panel.py  -  cleaning panel and constructing L_it")
    print("=" * 65)

    log = [
        "CLEANING AUDIT LOG", "=" * 65,
        f"{'Step':<55} {'rows':>8}  {'banks':>5}", "-" * 65,
    ]

    # 0. Load
    print("\n[0] Loading panel_raw.parquet")
    df = pd.read_parquet(CLEAN / "panel_raw.parquet")
    df["rssd9999"] = pd.to_datetime(df["rssd9999"])
    _log(log, "0. Raw panel loaded", df)

    # 1. FFIEC 031 only
    print("\n[1] Keeping FFIEC 031 filers")
    df = df[df["rssdfininstfilingtype"] == FILING_TYPE].copy()
    _log(log, "1. Keep FFIEC 031 filers only", df)

    # 2. Minimum asset size
    print(f"\n[2] Minimum asset filter (>= ${MIN_ASSETS_USD:,}k)")
    df = df[df["rcfd2170"] >= MIN_ASSETS_USD].copy()
    _log(log, f"2. Assets >= $300m ({MIN_ASSETS_USD:,}k)", df)

    # 3. Drop missing denominator
    print("\n[3] Dropping rows with missing total assets")
    before = len(df)
    df = df[df["rcfd2170"].notna()].copy()
    _log(log, f"3. Drop missing rcfd2170 (removed {before - len(df):,})", df)

    # 4. Merger quarters
    print("\n[4] Flagging merger quarters (>50pct one-quarter asset jump)")
    df = df.sort_values(["rssd9001", "rssd9999"]).reset_index(drop=True)
    df["assets_lag"]   = df.groupby("rssd9001")["rcfd2170"].shift(1)
    df["asset_growth"] = (df["rcfd2170"] - df["assets_lag"]) / df["assets_lag"]
    df["merger_flag"]  = (df["asset_growth"] > 0.50) & df["assets_lag"].notna()
    n_flagged = df["merger_flag"].sum()
    print(f"  Merger quarters flagged: {n_flagged:,}")
    log.append(f"  Merger quarters flagged and dropped: {n_flagged:,}")
    df = df[~df["merger_flag"]].copy()
    _log(log, "4. Drop merger quarters", df)

    # 5. Fill missing RC-L items with zero
    print("\n[5] Filling missing RC-L items with zero")
    rc_l_cols = ["rcfd3819", "rcfd3433", "rcfd3820",
                 "rcfdj457", "rcfdj458", "rcfdj459", "rcfd3817"]
    for col in rc_l_cols:
        if col in df.columns:
            n = df[col].isna().sum()
            df[col] = df[col].fillna(0)
            if n > 0:
                print(f"  {col}: {n:,} NaN -> 0")

    # 6. Drop rcfd3818 (contaminated aggregate -- see docstring)
    if "rcfd3818" in df.columns:
        df = df.drop(columns=["rcfd3818"])
        log.append("  rcfd3818 excluded (imprecise aggregate, exceeds assets for trust cos)")
        print("  rcfd3818 dropped")

    # 7. Winsorise components
    print(f"\n[6] Winsorising components at [{WINSOR_LOWER:.0%}, {WINSOR_HIGH:.0%}]")
    for col in ["rcfdj458", "rcfd3819", "rcfd3433", "rcfd2170",
                "rcfd3210", "rcfd1763", "rcfd1764"]:
        if col in df.columns and df[col].notna().sum() > 10:
            lo = df[col].quantile(WINSOR_LOWER)
            hi = df[col].quantile(WINSOR_HIGH)
            df[col] = df[col].clip(lower=lo, upper=hi)
            print(f"  {col:<20} [{lo:>14,.0f},  {hi:>14,.0f}]")

    # 8. Construct L_it and variants
    print("\n[7] Constructing L_it and variants")
    denom = df["rcfd2170"]

    df["L_it"] = (df["rcfd3819"].fillna(0)
                  + df["rcfd3433"].fillna(0)
                  + df["rcfdj458"].fillna(0)) / denom

    df["L_middle"] = (df["rcfd3819"].fillna(0)
                      + df["rcfd3433"].fillna(0)) / denom

    df["L_guarantees"] = df["rcfd3819"].fillna(0) / denom
    df["L_securities"]  = df["rcfd3433"].fillna(0) / denom
    df["L_lines"]       = df["rcfdj458"].fillna(0) / denom

    for col in ["L_it", "L_middle", "L_guarantees", "L_securities", "L_lines"]:
        df[col] = df[col].clip(lower=0)

    # 9. Winsorise L_it at 99th percentile (ratio-level winsorisation)
    print("\n[8] Winsorising L_it ratio at 99th percentile")
    for col in ["L_it", "L_middle", "L_guarantees", "L_securities", "L_lines"]:
        hi = df[col].quantile(WINSOR_HIGH)
        n_clip = (df[col] > hi).sum()
        df[col] = df[col].clip(upper=hi)
        print(f"  {col:<20} 99th={hi:.6f}  clipped {n_clip:,} obs")

    log.append("  L_it = (rcfd3819 + rcfd3433 + rcfdj458) / rcfd2170")
    log.append("  rcfdj458 = 0 for 2005-2009 (FFIEC granularity absent pre-2010)")
    log.append("  L_it and variants winsorised at 99th percentile")

    print(f"\n  L_it distribution:")
    desc = df["L_it"].describe(percentiles=[.01, .05, .25, .50, .75, .95, .99])
    for idx, val in desc.items():
        print(f"    {idx:<8} {val:.6f}")

    # 10. Control and outcome variables
    print("\n[9] Control and outcome variables")
    df["capital_ratio"] = _winsorise(df["rcfd3210"] / df["rcfd2170"])
    df["log_assets"]    = np.log(df["rcfd2170"])
    df["year"]          = df["rssd9999"].dt.year
    df["quarter"]       = df["rssd9999"].dt.quarter
    df["year_quarter"]  = df["year"].astype(str) + "Q" + df["quarter"].astype(str)
    df["post_2010"]     = (df["year"] >= 2010).astype(int)

    df = df.sort_values(["rssd9001", "rssd9999"])
    ci    = df["rcfd1763"].fillna(0) + df["rcfd1764"].fillna(0)
    ci_lg = ci.groupby(df["rssd9001"]).shift(1)
    df["ci_loan_growth"]  = ((ci - ci_lg) / ci_lg).clip(lower=-1, upper=3)
    df["has_sec_lending"] = (df["rcfd3433"] > 0).astype(int)
    print("  Created: capital_ratio, log_assets, ci_loan_growth,")
    print("           has_sec_lending, post_2010, year_quarter")

    # 11. Final column selection
    print("\n[10] Final column selection")
    keep = [
        "rssd9001", "rssd9999", "rssd9017",
        "year", "quarter", "year_quarter", "post_2010",
        "L_it", "L_middle", "L_guarantees", "L_securities", "L_lines",
        "rcfd3819", "rcfd3433", "rcfdj458",
        "rcfdj457", "rcfdj459", "rcfd3820",
        "rcfd2170", "rcfd3210",
        "capital_ratio", "log_assets",
        "ci_loan_growth", "rcfd1763", "rcfd1764",
        "merger_flag", "asset_growth", "has_sec_lending",
        "rcfd3817", "rcfdpv11", "rcfdpv14",
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].sort_values(["rssd9001", "rssd9999"]).reset_index(drop=True)
    _log(log, "10. Final clean panel", df)

    # Save
    print("\n[Saving]")
    df.to_parquet(F_PANEL, index=False)
    df.to_csv(F_PANEL_CSV, index=False)
    print(f"  Parquet -> {F_PANEL}")
    print(f"  CSV     -> {F_PANEL_CSV}")

    # Coverage log
    log += ["", "-" * 65, "FINAL VARIABLE COVERAGE:", ""]
    for col in ["L_it", "L_middle", "L_guarantees", "L_securities", "L_lines",
                "rcfd3819", "rcfd3433", "rcfdj458",
                "rcfd2170", "capital_ratio", "ci_loan_growth"]:
        if col in df.columns:
            nn  = df[col].notna().sum()
            pct = nn / len(df) * 100
            med = df[col].median()
            mn  = df[col].min()
            mx  = df[col].max()
            log.append(f"  {col:<22} {pct:>5.1f}%  "
                       f"median={med:>9.5f}  [{mn:>9.4f}, {mx:>9.4f}]")

    log_text = "\n".join(log)
    log_path = CLEAN / "cleaning_log.txt"
    log_path.write_text(log_text, encoding="utf-8")
    print(f"  Log     -> {log_path}")
    print("\n" + log_text)
    print("\n  Done. Next: python 03_validate_lit.py")


if __name__ == "__main__":
    main()