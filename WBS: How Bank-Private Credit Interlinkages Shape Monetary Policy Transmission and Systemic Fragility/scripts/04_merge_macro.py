"""
04_merge_macro.py
-----------------
PURPOSE
    Load manually downloaded FRED CSVs, aggregate to quarterly frequency,
    and merge into the clean panel.

MANUAL DOWNLOAD REQUIRED
    Download each series from fred.stlouisfed.org and save to data/raw/:

    File name        FRED URL
    NFCI.csv         https://fred.stlouisfed.org/series/NFCI
    NFCICREDIT.csv   https://fred.stlouisfed.org/series/NFCICREDIT
    DGS10.csv        https://fred.stlouisfed.org/series/DGS10
    FEDFUNDS.csv     https://fred.stlouisfed.org/series/FEDFUNDS

    Each CSV has two columns: DATE and the series value.
    Download using: Download -> File Format: CSV (default settings).

INPUT   data/clean/panel_clean.parquet
        data/raw/NFCI.csv, NFCICREDIT.csv, DGS10.csv, FEDFUNDS.csv

OUTPUT  data/clean/panel_macro.parquet
        data/clean/panel_macro.csv
        data/clean/macro_quarterly.csv   (quarterly macro series, for inspection)

VARIABLES CONSTRUCTED
    nfci          NFCI level (higher = tighter financial conditions)
    nfci_credit   NFCI credit sub-index
    dgs10         10-year Treasury yield (pct)
    fedfunds      Federal funds rate (pct)
    term_spread   dgs10 - fedfunds (yield curve slope; negative = inverted)
    nfci_change   Quarter-on-quarter change in NFCI (tightening indicator)
"""

import sys
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAW, CLEAN, F_PANEL

warnings.filterwarnings("ignore", category=FutureWarning)


# ── Helper: load one FRED CSV ──────────────────────────────────────────────

def _load_fred_csv(filename: str, value_col: str) -> pd.Series:
    """
    Load a FRED CSV downloaded from fred.stlouisfed.org.
    Returns a pd.Series indexed by date, named value_col.
    """
    path = RAW / filename
    if not path.exists():
        print(f"  MISSING: {path}")
        print(f"    -> Download from https://fred.stlouisfed.org/series/{filename.replace('.csv','')}")
        print(f"    -> Save to data/raw/{filename}")
        return pd.Series(dtype=float, name=value_col)

    # Read without parsing dates initially to avoid name-matching errors
    df = pd.read_csv(path)
    
    # Rename the first column to "date" and the second to the value_col
    df.columns = ["date", value_col]
    
    # Convert the date column to datetime objects
    df["date"] = pd.to_datetime(df["date"])
    
    # Set the index and extract the Series
    df = df.set_index("date")[value_col]
    df = pd.to_numeric(df.replace(".", np.nan), errors="coerce")
    
    print(f"  Loaded {filename:<20} {df.notna().sum():>5} obs  "
          f"{df.first_valid_index().date()} to {df.last_valid_index().date()}")
    return df

def _to_quarter_end(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.to_period("Q").to_timestamp("Q")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 65)
    print("04_merge_macro.py  -  loading and merging macro variables")
    print("=" * 65)

    # ── 1. Load FRED CSVs ─────────────────────────────────────────────────
    print("\n[1] Loading FRED CSV files from data/raw/")

    series = {
        "NFCI.csv":       "nfci",
        "NFCICREDIT.csv": "nfci_credit",
        "DGS10.csv":      "dgs10",
        "FEDFUNDS.csv":   "fedfunds",
    }

    frames = {}
    missing = []
    for filename, col in series.items():
        s = _load_fred_csv(filename, col)
        if s.empty:
            missing.append(filename)
        else:
            frames[col] = s

    if missing:
        print(f"\n  WARNING: {len(missing)} file(s) missing: {missing}")
        print("  The script will continue but affected variables will be NaN.")
        print("  Download missing files and re-run to get full coverage.")

    if not frames:
        print("\n  ERROR: No macro files found in data/raw/.")
        print("  Download all four FRED CSVs and place in data/raw/ then re-run.")
        return

    # ── 2. Combine into wide daily/weekly frame ───────────────────────────
    print("\n[2] Combining into wide frame")
    macro_daily = pd.DataFrame(frames)
    macro_daily.index = pd.to_datetime(macro_daily.index)
    macro_daily = macro_daily.sort_index()
    print(f"  Combined shape: {macro_daily.shape}")

    # ── 3. Aggregate to quarter-end ───────────────────────────────────────
    print("\n[3] Aggregating to quarterly (mean within quarter)")
    macro_q = macro_daily.copy()
    macro_q.index = _to_quarter_end(macro_q.index)
    macro_q = macro_q.groupby(macro_q.index).mean()
    macro_q.index.name = "rssd9999"
    macro_q = macro_q.reset_index()

    # ── 4. Derived variables ──────────────────────────────────────────────
    print("\n[4] Constructing derived macro variables")

    if "dgs10" in macro_q.columns and "fedfunds" in macro_q.columns:
        macro_q["term_spread"] = macro_q["dgs10"] - macro_q["fedfunds"]
        print("  term_spread = dgs10 - fedfunds (yield curve slope)")

    if "nfci" in macro_q.columns:
        macro_q = macro_q.sort_values("rssd9999")
        macro_q["nfci_change"] = macro_q["nfci"].diff()
        print("  nfci_change = quarter-on-quarter change in NFCI")

    # Filter to dissertation window plus one lag quarter
    macro_q = macro_q[macro_q["rssd9999"] >= "2004-10-01"].copy()

    print(f"\n  Quarterly macro series: {len(macro_q)} quarters")
    print(f"  Date range: {macro_q['rssd9999'].min().date()} to {macro_q['rssd9999'].max().date()}")

    # Preview
    show_cols = ["rssd9999"] + [c for c in ["nfci", "nfci_credit", "dgs10",
                                              "fedfunds", "term_spread"] if c in macro_q.columns]
    print(f"\n  Sample (first 6 quarters from 2005):")
    sample = macro_q[macro_q["rssd9999"] >= "2005-01-01"].head(6)
    print(sample[show_cols].to_string(index=False))

    # Save quarterly macro for inspection
    macro_q.to_csv(CLEAN / "macro_quarterly.csv", index=False)
    print(f"\n  Quarterly macro saved -> {CLEAN / 'macro_quarterly.csv'}")

    # ── 5. Load clean panel and merge ─────────────────────────────────────
    print("\n[5] Merging with clean panel")
    df = pd.read_parquet(F_PANEL)
    df["rssd9999"] = pd.to_datetime(df["rssd9999"])

    n_before = len(df)
    df = df.merge(macro_q, on="rssd9999", how="left")
    assert len(df) == n_before, "Row count changed after merge — investigate duplicate dates"
    print(f"  Panel rows: {n_before:,} -> {len(df):,} (unchanged, as expected)")

    # ── 6. Coverage check ─────────────────────────────────────────────────
    print("\n[6] Macro variable coverage in merged panel")
    check_cols = ["nfci", "nfci_credit", "dgs10", "fedfunds",
                  "term_spread", "nfci_change"]
    for col in check_cols:
        if col in df.columns:
            nn  = df[col].notna().sum()
            pct = nn / len(df) * 100
            mn  = df[col].min()
            mx  = df[col].max()
            med = df[col].median()
            print(f"  {col:<16} {pct:>5.1f}%  "
                  f"median={med:>7.4f}  [{mn:.4f}, {mx:.4f}]")

    # ── 7. Correlations with L_it ──────────────────────────────────────────
    print("\n[7] Correlations with L_it")
    corr_cols = ["L_it"] + [c for c in check_cols if c in df.columns]
    corr = df[corr_cols].corr()["L_it"].drop("L_it")
    for col, val in corr.items():
        print(f"  corr(L_it, {col:<16}) = {val:>7.4f}")

    # ── 8. Save ───────────────────────────────────────────────────────────
    print("\n[8] Saving")
    out_parquet = CLEAN / "panel_macro.parquet"
    out_csv     = CLEAN / "panel_macro.csv"
    df.to_parquet(out_parquet, index=False)
    df.to_csv(out_csv, index=False)
    print(f"  Parquet -> {out_parquet}")
    print(f"  CSV     -> {out_csv}")
    print(f"  Final panel shape: {df.shape}")
    print(f"  Final columns: {list(df.columns)}")

    print("\n  Done. Next: python 05_describe.py")


if __name__ == "__main__":
    main()