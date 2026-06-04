"""
Merge four large raw WRDS Call Reports into a single one, covering Q1 2025 to Q4 2023

NOTES
    - All monetary values remain in thousands of USD (WRDS convention).
    - Retain all filing types at this stage; the 031-only filter
      is applied in 02_clean_panel.py to audit drop counts.
    - rcfd3818 (unused commitments — other) was retired by FFIEC in 2010Q1
      and replaced by the three-way rcfdj457/j458/j459 breakdown.
      This script preserves both - will change it later.
"""

import sys
import pandas as pd
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from config import (
    RAW, CLEAN, F_OLD, F_RCFD1, F_FIX1, F_RCFD2,
    ID_COLS, FILING_TYPE, START_DATE, END_DATE,
)

# Utility #

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase all column names."""
    df.columns = df.columns.str.lower().str.strip()
    return df


def _parse_date(df: pd.DataFrame, col: str = "rssd9999") -> pd.DataFrame:
    """
    Parse the date column robustly.
    WRDS newer files use ISO strings; legacy files use YYYYMMDD integers.
    """
    raw = df[col]
    if pd.api.types.is_integer_dtype(raw) or raw.dropna().astype(str).str.len().max() == 8:
        df[col] = pd.to_datetime(raw.astype(str), format="%Y%m%d", errors="coerce")
    else:
        df[col] = pd.to_datetime(raw, errors="coerce")
    return df


def _normalise_filing_type(df: pd.DataFrame) -> pd.DataFrame:
    """Convert filing type to integer: '031' / '31' / 31 → 31."""
    if "rssdfininstfilingtype" in df.columns:
        df["rssdfininstfilingtype"] = (
            df["rssdfininstfilingtype"]
            .astype(str).str.strip().str.lstrip("0")
            .replace("", "0")
            .astype(int)
        )
    return df


def _quarter_end(df: pd.DataFrame, col: str = "rssd9999") -> pd.DataFrame:
    """Snap dates to quarter-end (last calendar day of Mar/Jun/Sep/Dec)."""
    df[col] = df[col].dt.to_period("Q").dt.to_timestamp("Q")
    return df


def load_legacy(path) -> pd.DataFrame:
    """
    Load rcfd_old.csv.
    Contains: rcfd1517, rcfd1763, rcfd1764, rcfdj457, rcfdj458, rcfdj459
    Dates in YYYYMMDD integer format.
    No filing-type column — all filers included.
    """
    print("  Loading rcfd_old.csv ...", end=" ")
    df = pd.read_csv(path, low_memory=False)
    df = _normalise_cols(df)
    df = _parse_date(df)
    df = _quarter_end(df)

    # Rename the bank-name column for consistency #
    if "rssd9010" in df.columns:
        df = df.rename(columns={"rssd9010": "rssd9017"})

    # Realised I don't need rssd9469 so remove the column. #
    df = df.drop(columns=["rssd9469"], errors="ignore")

    print(f"{len(df):,} rows, {df['rssd9001'].nunique():,} banks")
    return df


def load_rcfd1(path) -> pd.DataFrame:
    """
    Load rcfd1.csv.
    Contains: rcfd3820, rcfd1764, rcfd1763, rcfd3433, rcfd3819, rcfdpv11, rcfdpv14
    """
    print("  Loading rcfd1.csv ...", end=" ")
    df = pd.read_csv(path, low_memory=False)
    df = _normalise_cols(df)
    df = _parse_date(df)
    df = _quarter_end(df)
    df = _normalise_filing_type(df)
    print(f"{len(df):,} rows, {df['rssd9001'].nunique():,} banks")
    return df


def load_rcfd1_fix(path) -> pd.DataFrame:
    """
    Load rcfd1_fix1.csv.
    Contains: rcfdj454, rcfdpv11, rcfdpv14, rcfdb680
    Supplement for granular loan-to-NBFI series.
    """
    print("  Loading rcfd1_fix1.csv ...", end=" ")
    df = pd.read_csv(path, low_memory=False)
    df = _normalise_cols(df)
    df = _parse_date(df)
    df = _quarter_end(df)
    df = _normalise_filing_type(df)
    keep = ID_COLS + ["rcfdj454", "rcfdb680"]
    keep = [c for c in keep if c in df.columns]
    print(f"{len(df):,} rows | keeping cols: {keep}")
    return df[keep]


def load_rcfd2(path) -> pd.DataFrame:
    """
    Load rcfd2.csv.
    Contains: rcfd2170 (total assets), rcfd3210 (equity), rcfd3818, rcfd3817
    """
    print("  Loading rcfd2.csv ...", end=" ")
    df = pd.read_csv(path, low_memory=False)
    df = _normalise_cols(df)
    df = _parse_date(df)
    df = _quarter_end(df)
    df = _normalise_filing_type(df)
    print(f"{len(df):,} rows, {df['rssd9001'].nunique():,} banks")
    return df


# Main #

def main():
    print("\n" + "="*65)
    print("01_build_raw_panel.py — assembling raw panel")
    print("="*65)

    # Load all files #
    print("\n[1/5] Loading raw files")
    df_old  = load_legacy(F_OLD)
    df_r1   = load_rcfd1(F_RCFD1)
    df_fix  = load_rcfd1_fix(F_FIX1)
    df_r2   = load_rcfd2(F_RCFD2)

    # Merge rcfd1 + rcfd1_fix1 #
    print("\n[2/5] Merging Series 1 files")
    df_new = df_r1.merge(df_fix, on=ID_COLS, how="left")
    print(f"  After merge: {len(df_new):,} rows")

    # Merge Series 2 (assets + equity + rcfd3818) #
    print("\n[3/5] Merging Series 2")
    s2_data_cols = [c for c in df_r2.columns
                    if c not in ["rssd9017", "rssdfininstfilingtype"]]
    df_new = df_new.merge(df_r2[s2_data_cols], on=ID_COLS, how="left")
    print(f"  After merge: {len(df_new):,} rows")

    # Merge legacy. Legacy has rcfd1517, rcfd1763 (for pre-2001 period), rcfdj457, rcfdj458, rcfdj459 #
    print("\n[4/5] Merging legacy file (rcfd_old)")
    legacy_cols = ID_COLS + [
        "rcfd1517",
        "rcfdj457",
        "rcfdj458",
        "rcfdj459",
    ]
    legacy_cols = [c for c in legacy_cols if c in df_old.columns]

    df = df_new.merge(
        df_old[legacy_cols],
        on=ID_COLS,
        how="outer",
        suffixes=("", "_legacy")
    )

    # Where rcfd1763 is NaN in the new pull but present in legacy, fill in
    # (legacy covers all filers; new pull covers 031 only — but we keep all filers for now)
    for col in ["rcfd1763", "rcfd1764"]:
        if f"{col}_legacy" in df.columns:
            df[col] = df[col].fillna(df[f"{col}_legacy"])
            df = df.drop(columns=[f"{col}_legacy"])

    print(f"  After merge: {len(df):,} rows | {df['rssd9001'].nunique():,} unique banks")

    # Trim date window and save #
    print("\n[5/5] Trimming to 2005Q1–2023Q4 and saving")
    df = df[
        (df["rssd9999"] >= START_DATE) &
        (df["rssd9999"] <= END_DATE)
    ].copy()

    print(f"  Rows in window: {len(df):,}")
    print(f"  Unique banks:   {df['rssd9001'].nunique():,}")
    print(f"  Date range:     {df['rssd9999'].min().date()} to {df['rssd9999'].max().date()}")
    print(f"  Columns:        {list(df.columns)}")

    out_path = CLEAN / "panel_raw.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n  Saved → {out_path}")

    # Summary #
    diag_lines = [
        "RAW PANEL DIAGNOSTIC",
        "=" * 60,
        f"Rows:           {len(df):,}",
        f"Unique banks:   {df['rssd9001'].nunique():,}",
        f"Date range:     {df['rssd9999'].min().date()} to {df['rssd9999'].max().date()}",
        "",
        "Filing type distribution:",
    ]
    if "rssdfininstfilingtype" in df.columns:
        for ft, cnt in df["rssdfininstfilingtype"].value_counts().items():
            diag_lines.append(f"  Type {ft:>3}: {cnt:>10,} rows")

    diag_lines += ["", "Variable coverage (non-null count | % of all rows):"]
    skip = {"rssd9001", "rssd9999", "rssd9017", "rssdfininstfilingtype", "rssd9010"}
    for col in df.columns:
        if col in skip:
            continue
        nn = df[col].notna().sum()
        pct = nn / len(df) * 100
        diag_lines.append(f"  {col:<20} {nn:>10,}  ({pct:>5.1f}%)")

    diag_text = "\n".join(diag_lines)
    print("\n" + diag_text)

    diag_path = CLEAN / "panel_raw_diag.txt"
    diag_path.write_text(diag_text)
    print(f"\n  Diagnostic saved → {diag_path}")
    print("\n  ✓ Done. Next: python 02_clean_panel.py")


if __name__ == "__main__":
    main()