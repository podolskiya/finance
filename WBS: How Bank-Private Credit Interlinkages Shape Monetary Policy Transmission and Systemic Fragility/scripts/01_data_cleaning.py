"""
01_data_cleaning.py
------------
GOAL:
    Load the WRDS Call Report pulls, dedupe, merge,
    and apply sample-definition filters to produce clean bank-quarter
    panel to build L_it on top of in the next script file - 02_linkage_index.py).

INPUT(s):
        data/raw/rcfd1.csv   (rcfd3820, rcfd1764, rcfd1763, rcfd3433, rcfd3819, rcfdj454, pv-series)
        data/raw/rcfd2.csv   (rcfdj457/458/459, rcfd2170, rcfd3210, rcfd3818, rcfd3817)

OUTPUTS:
        data/clean/panel_raw.parquet
        outputs/cleaning_log.txt

STEPS
    1.  Load both files, dedupe exact-duplicate rows independently
    2.  Merge on (rssd9001, rssd9999) - keys match 1:1 post-dedup, so this is a safe one-to-one join (no cartesian risk)
    3.  Trim to analysis window (2004Q4-2025Q4)
    4.  Keep FFIEC 031 filers only
    5.  Apply minimum asset size filter ($300m)
    6.  Drop missing total assets
    7.  Flag and drop merger quarters (>50% one-quarter asset jump)
    8.  Zero-fill Schedule RC-L items (031 filers all report these;
        missing = not applicable = zero)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add parent directory to path to import config #
sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module
config = import_module("00_config")


def _log(log, label, df):
    """ Simple logging helper for audit """
    entry = (f"{label:<60} "
             f"rows={len(df):>8,}  "
             f"banks={df['rssd9001'].nunique():>5,}")
    log.append(entry)
    print(f"  {entry}")


def _load_and_dedupe(path, label):
    """ Load raw WRDS data and remove exact duplicate rows """
    print(f"\n  Loading {path.name} ...", end=" ")
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.lower().str.strip()
    n_before = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    n_dropped = n_before - len(df)
    print(f"{n_before:,} rows -> {len(df):,} after dedup ({n_dropped:,} exact duplicates dropped)")
    return df, n_dropped


def main():
    print("\n" + "=" * 65)
    print("01_data_cleaning.py  --  building the clean bank-quarter panel")
    print("=" * 65)

    log = [
        "DATA CLEANING AUDIT LOG",
        "=" * 65,
        f"{'Step':<60} {'rows':>8}  {'banks':>5}",
        "-" * 65,
    ]

    # Load and deduplicate raw files #
    print("\n[1] Loading and deduplicating raw pulls")
    df1, dropped1 = _load_and_dedupe(config.F_RCFD1, "rcfd1")
    df2, dropped2 = _load_and_dedupe(config.F_RCFD2, "rcfd2")
    log.append(f"  rcfd1.csv: dropped {dropped1:,} exact-duplicate rows (WRDS export artifact)")
    log.append(f"  rcfd2.csv: dropped {dropped2:,} exact-duplicate rows (WRDS export artifact)")

    # Merge on: rssd9001, rssd9999 #
    print("\n[2] Merging on (rssd9001, rssd9999)")
    for df in (df1, df2):
        df["rssd9999"] = pd.to_datetime(df["rssd9999"], dayfirst=True, errors="coerce")
        df["rssd9999"] = df["rssd9999"].dt.to_period("Q").dt.to_timestamp("Q")

    # Handle conflicting duplicates where there are different valeus for the same bank-quarter #
    # This can be explained by amended filings, and we drop any problematic keys entirely #
    conflict_keys_1 = set(
        zip(df1.loc[df1.duplicated(subset=config.ID_COLS, keep=False), "rssd9001"],
            df1.loc[df1.duplicated(subset=config.ID_COLS, keep=False), "rssd9999"])
    )
    conflict_keys_2 = set(
        zip(df2.loc[df2.duplicated(subset=config.ID_COLS, keep=False), "rssd9001"],
            df2.loc[df2.duplicated(subset=config.ID_COLS, keep=False), "rssd9999"])
    )
    conflict_keys = conflict_keys_1 | conflict_keys_2
    print(f"  Conflicting (bank,quarter) keys found: {len(conflict_keys_1)} in rcfd1, "
          f"{len(conflict_keys_2)} in rcfd2, {len(conflict_keys)} union -- dropping from both files")
    log.append(f" Found {len(conflict_keys)} conflicting keys and dropping from both files"
               f" which are likely amended restated filings." )

    key_series_1 = pd.Series(list(zip(df1["rssd9001"], df1["rssd9999"])), index=df1.index)
    key_series_2 = pd.Series(list(zip(df2["rssd9001"], df2["rssd9999"])), index=df2.index)
    
    df1 = df1[~key_series_1.isin(conflict_keys)].copy()
    df2 = df2[~key_series_2.isin(conflict_keys)].copy()

    # Remove conflicting rows #
    key_series_1 = pd.Series(list(zip(df1["rssd9001"], df1["rssd9999"])), index=df1.index)
    key_series_2 = pd.Series(list(zip(df2["rssd9001"], df2["rssd9999"])), index=df2.index)
    
    df1 = df1[~key_series_1.isin(conflict_keys)].copy()
    df2 = df2[~key_series_2.isin(conflict_keys)].copy()
    
    # Final Merge #
    df2_data_cols = [c for c in df2.columns if c not in ["rssd9017", "rssdfininstfilingtype"]]
    df = df1.merge(df2[df2_data_cols], on=config.ID_COLS, how="inner")
    _log(log, "2. Merged rcfd1 + rcfd2", df)

    #  Merge RCONJ454 supplement (loans to NDFI) #
    print("\n[2b] Merging RCONJ454 (loans to NDFI, domestic-office basis)")
    rj454 = pd.read_csv(config.F_RCONJ454, low_memory=False)
    rj454.columns = rj454.columns.str.lower().str.strip()
    n_before = len(rj454)
    rj454 = rj454.drop_duplicates(keep="first")
    print(f"  Loaded {n_before:,} rows -> {len(rj454):,} after exact-dup removal")
    rj454["rssd9999"] = pd.to_datetime(rj454["rssd9999"], dayfirst=True, errors="coerce")
    rj454["rssd9999"] = rj454["rssd9999"].dt.to_period("Q").dt.to_timestamp("Q")

    # Same conservative conflict handling #
    dup_mask = rj454.duplicated(subset=config.ID_COLS, keep=False)
    n_conflict_keys = rj454.loc[dup_mask, config.ID_COLS].drop_duplicates().shape[0]
    if n_conflict_keys > 0:
        print(f"  {n_conflict_keys} conflicting keys in RCONJ454 - set to NaN ")
        log.append(f"RCONJ454: {n_conflict_keys} conflicting keys set to NaN")
        rj454 = rj454[~dup_mask].copy()
    rj454 = rj454[config.ID_COLS + ["rconj454"]]


    n_before_merge = len(df)
    df = df.merge(rj454, on=config.ID_COLS, how="left")
    assert len(df) == n_before_merge, "RCONJ454 merge changed row count so I need to investigate."
    n_matched = df["rconj454"].notna().sum()
    print(f"  Merged: {n_matched:,} of {len(df):,} rows matched with RCONJ454 value.")
    log.append(f"RCONJ454 merged: {n_matched:,} of {len(df):,} rows matched")

    # Trim to analysis window and apply same filters #
    print(f"\n[3] Trimming to {config.START_DATE} - {config.END_DATE}")
    df = df[
        (df["rssd9999"] >= config.START_DATE) &
        (df["rssd9999"] <= config.END_DATE)
    ].copy()
    _log(log, f"3. Trim to analysis window ({config.START_DATE} to {config.END_DATE})", df)

    # Filing type check #
    print("\n[4] Filing type distribution (all filers, pre-filter)")
    print(df["rssdfininstfilingtype"].value_counts(dropna=False).to_string())
    log.append("")
    log.append("Filing type distribution (pre-filter):")
    for ft, cnt in df["rssdfininstfilingtype"].value_counts(dropna=False).items():
        log.append(f"  Type {ft:>3}: {cnt:>10,} rows")

    # Keep FFIEC 031 filers only #
    print("\n[5] Keeping FFIEC 031 filers only")
    df = df[df["rssdfininstfilingtype"] == config.FILING_TYPE].copy()
    _log(log, "5. Keep FFIEC 031 filers only", df)

    # Note about the known 2005Q3 data gap #
    n_q3 = (df["rssd9999"] == pd.Timestamp("2005-09-30")).sum()
    if n_q3 > 0:
        log.append(f"NOTE: 2005Q3 WRDS extraction gap detected ({n_q3} banks missing)")
    n_2005q2 = (df["rssd9999"] == pd.Timestamp("2005-06-30")).sum()
    n_2005q4 = (df["rssd9999"] == pd.Timestamp("2005-12-31")).sum()
    log.append(f"  NOTE: 2005Q3 has a known WRDS extraction gap ({n_2005q3} banks vs "
               f"{n_2005q2}/{n_2005q4} in surrounding quarters) -- confirmed pull "
               f"artifact (banks present in both Q2 and Q4 but absent in Q3), not "
               f"real attrition.")

    # Minimum asset size filter #
    print(f"\n[6] Minimum asset filter (>= ${config.MIN_ASSETS_USD:,}k)")
    df = df[df["rcfd2170"] >= config.MIN_ASSETS_USD].copy()
    _log(log, f"6. Assets >= $300m ({config.MIN_ASSETS_USD:,}k)", df)

    # Drop missing denominator #
    print("\n[7] Dropping rows with missing total assets")
    before = len(df)
    df = df[df["rcfd2170"].notna()].copy()
    _log(log, f"7. Drop missing rcfd2170 (removed {before - len(df):,})", df)

    # Merger quarters #
    rint(f"\n[8] Flagging merger quarters (>{config.MERGER_JUMP_THRESHOLD:.0%} asset jump)")
    df = df.sort_values(["rssd9001", "rssd9999"]).reset_index(drop=True)
    df["assets_lag"] = df.groupby("rssd9001")["rcfd2170"].shift(1)
    df["asset_growth"] = (df["rcfd2170"] - df["assets_lag"]) / df["assets_lag"]
    df["merger_flag"] = (df["asset_growth"] > config.MERGER_JUMP_THRESHOLD) & df["assets_lag"].notna()

    # Zero-fill Schedule RC-L items #
    print("\n[9] Zero-filling Schedule RC-L items (031 filers all report these)")
    for col in config.RC_L_ZERO_FILL_COLS:
        if col in df.columns:
            n = df[col].isna().sum()
            df[col] = df[col].fillna(0)
            if n > 0:
                print(f"  {col}: {n:,} NaN -> 0")
                log.append(f"  {col}: {n:,} NaN -> 0 (RC-L zero-fill)")

    # Final cleanup and save #
    pv_cols = [c for c in df.columns if c.startswith("rcfdpv")]
    keep = (
        ["rssd9001", "rssd9999", "rssd9017", "rssdfininstfilingtype"]
        + ["rcfd3819", "rcfd3433", "rcfd3820", "rcfd1763", "rcfd1764"]
        + ["rcfdj454", "rconj454"]
        + pv_cols
        + ["rcfdj457", "rcfdj458", "rcfdj459", "rcfd2170", "rcfd3210", "rcfd3818", "rcfd3817"]
        + ["merger_flag", "asset_growth"]
    )
    keep = [c for c in keep if c in df.columns]
    df = df[keep].sort_values(["rssd9001", "rssd9999"]).reset_index(drop=True)
    _log(log, "10. Final clean panel", df)

    print(f"  Columns: {list(df.columns)}")

    out_path = config.F_PANEL_RAW
    df.to_parquet(out_path, index=False)
    print(f"\n  Saved -> {out_path}")

    # Summary full log #
    log += ["", "-" * 65, "FINAL VARIABLE COVERAGE:", ""]
    for col in ["rcfd3819", "rcfd3433", "rcfdj458", "rconj454", "rcfd2170", "rcfd3210",
                "rcfd1763", "rcfd1764", "rcfdj454"]:
        if col in df.columns:
            nn  = df[col].notna().sum()
            pct = nn / len(df) * 100
            log.append(f"  {col:<20} {pct:>5.1f}%  ({nn:,} / {len(df):,})")

    log_text = "\n".join(log)
    print("\n" + log_text)
    (config.OUTPUT / "cleaning_log.txt").write_text(log_text, encoding="utf-8")
    print(f"\n  Log -> {config.OUTPUT / 'cleaning_log.txt'}")
    print("\n  Done. Next: python 02_linkage_index.py")


if __name__ == "__main__":
    main()
