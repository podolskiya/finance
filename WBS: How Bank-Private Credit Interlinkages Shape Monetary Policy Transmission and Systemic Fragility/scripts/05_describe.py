"""
05_describe.py
--------------
PURPOSE
    Produce the publication-ready summary statistics table for the
    dissertation data section, plus a correlation matrix and a
    bank-level summary. These are the tables that go directly into
    your Chapter 3 (Data and Methodology).

INPUT   data/clean/panel_macro.parquet

OUTPUT  outputs/table_summary_stats.csv    (machine-readable)
        outputs/table_summary_stats.txt    (formatted for copy-paste into Word)
        outputs/table_correlation.csv
        outputs/table_bank_summary.csv     (one row per bank)
        outputs/fig_lit_histogram.png
"""

import sys
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CLEAN, OUTPUT

warnings.filterwarnings("ignore", category=FutureWarning)

plt.rcParams.update({
    "font.family":       "serif",
    "font.size":         11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":        150,
})

NAVY = "#003366"
BLUE = "#0066cc"


# ── Variable labels (for table display) ───────────────────────────────────

LABELS = {
    # L_it and variants
    "L_it":           "L_it  (main index)",
    "L_middle":       "L_it  (SLCs + sec. lending only)",
    "L_guarantees":   "L_it  (financial SLCs only)",
    "L_securities":   "L_it  (securities lending only)",
    "L_lines":        "L_it  (credit lines to FIs, post-2010)",

    # L_it components (in billions USD for readability)
    "rcfd3819_bn":    "Financial standby LCs  ($bn)",
    "rcfd3433_bn":    "Securities lent w/ cash coll.  ($bn)",
    "rcfdj458_bn":    "Unused commitments to FIs  ($bn)",
    "rcfd2170_bn":    "Total assets  ($bn)",
    "rcfd3210_bn":    "Equity capital  ($bn)",

    # Controls
    "capital_ratio":  "Capital ratio  (equity/assets)",
    "log_assets":     "Log total assets",

    # Outcomes
    "ci_loan_growth": "C&I loan growth  (QoQ)",

    # Macro
    "nfci":           "NFCI  (financial conditions index)",
    "nfci_credit":    "NFCI credit sub-index",
    "dgs10":          "10-year Treasury yield  (%)",
    "fedfunds":       "Federal funds rate  (%)",
    "term_spread":    "Term spread  (DGS10 - FEDFUNDS)",
}


def _fmt(x, decimals=4):
    """Format a number for the summary table."""
    if pd.isna(x):
        return ""
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    if abs(x) >= 1:
        return f"{x:,.{max(2, decimals-2)}f}"
    return f"{x:.{decimals}f}"


def main():
    print("\n" + "=" * 65)
    print("05_describe.py  -  summary statistics")
    print("=" * 65)

    # ── Load ───────────────────────────────────────────────────────────────
    df = pd.read_parquet(CLEAN / "panel_macro.parquet")
    df["rssd9999"] = pd.to_datetime(df["rssd9999"])
    print(f"\nPanel: {len(df):,} obs | {df['rssd9001'].nunique()} banks | "
          f"{df['rssd9999'].min().date()} to {df['rssd9999'].max().date()}")

    # ── Create billion-dollar versions of monetary variables ───────────────
    for col in ["rcfd3819", "rcfd3433", "rcfdj458", "rcfd2170", "rcfd3210"]:
        if col in df.columns:
            df[f"{col}_bn"] = df[col] / 1_000_000   # thousands -> billions

    # ── 1. Summary statistics table ────────────────────────────────────────
    print("\n[1] Building summary statistics table")

    stat_cols = [
        "L_it", "L_middle", "L_guarantees", "L_securities", "L_lines",
        "rcfd3819_bn", "rcfd3433_bn", "rcfdj458_bn",
        "rcfd2170_bn", "rcfd3210_bn",
        "capital_ratio", "log_assets", "ci_loan_growth",
        "nfci", "nfci_credit", "dgs10", "fedfunds", "term_spread",
    ]
    stat_cols = [c for c in stat_cols if c in df.columns]

    rows = []
    for col in stat_cols:
        s = df[col].dropna()
        rows.append({
            "Variable":  LABELS.get(col, col),
            "N":         len(s),
            "Mean":      s.mean(),
            "Std":       s.std(),
            "p1":        s.quantile(0.01),
            "p25":       s.quantile(0.25),
            "Median":    s.median(),
            "p75":       s.quantile(0.75),
            "p99":       s.quantile(0.99),
        })

    stats = pd.DataFrame(rows)

    # Save machine-readable CSV
    stats.to_csv(OUTPUT / "table_summary_stats.csv", index=False, float_format="%.6f")
    print(f"  CSV saved -> {OUTPUT / 'table_summary_stats.csv'}")

    # ── Formatted text table ───────────────────────────────────────────────
    col_widths = {"Variable": 38, "N": 7, "Mean": 10, "Std": 10,
                  "p1": 10, "p25": 10, "Median": 10, "p75": 10, "p99": 10}
    header = (f"{'Variable':<38} {'N':>7} {'Mean':>10} {'Std':>10} "
              f"{'p1':>10} {'p25':>10} {'Median':>10} {'p75':>10} {'p99':>10}")
    sep    = "-" * len(header)

    txt_lines = [
        "TABLE: Summary Statistics",
        f"Sample: FFIEC 031 commercial banks, 2005Q1-2023Q4",
        f"Observations: {len(df):,}  |  Banks: {df['rssd9001'].nunique()}",
        "",
        header,
        sep,
    ]

    section_breaks = {
        "L_it": "-- L_it index and variants --",
        "rcfd3819_bn": "-- L_it components (USD billions) --",
        "capital_ratio": "-- Bank-level controls --",
        "nfci": "-- Macro variables --",
    }

    for _, row in stats.iterrows():
        # Find matching col key for section break lookup
        col_key = next((k for k, v in LABELS.items() if v == row["Variable"]), None)
        if col_key in section_breaks:
            txt_lines += ["", f"  {section_breaks[col_key]}", ""]

        line = (
            f"{row['Variable']:<38} "
            f"{int(row['N']):>7,} "
            f"{_fmt(row['Mean']):>10} "
            f"{_fmt(row['Std']):>10} "
            f"{_fmt(row['p1']):>10} "
            f"{_fmt(row['p25']):>10} "
            f"{_fmt(row['Median']):>10} "
            f"{_fmt(row['p75']):>10} "
            f"{_fmt(row['p99']):>10}"
        )
        txt_lines.append(line)

    txt_lines += [
        sep,
        "",
        "Notes: L_it = (rcfd3819 + rcfd3433 + rcfdj458) / rcfd2170.",
        "rcfdj458 (unused commitments to financial institutions) is zero for",
        "2005-2009 (FFIEC did not require this breakdown before 2010Q1).",
        "Monetary variables in billions USD (WRDS reports in thousands).",
        "L_it and variants winsorised at 99th percentile.",
        "Capital ratio winsorised at [1%, 99%].",
        "C&I loan growth clipped at [-1, 3].",
    ]

    txt = "\n".join(txt_lines)
    (OUTPUT / "table_summary_stats.txt").write_text(txt, encoding="utf-8")
    print(f"  TXT saved -> {OUTPUT / 'table_summary_stats.txt'}")
    print("\n" + txt)

    # ── 2. Correlation matrix ──────────────────────────────────────────────
    print("\n[2] Correlation matrix")

    corr_cols = [
        "L_it", "L_middle", "L_lines",
        "capital_ratio", "log_assets",
        "ci_loan_growth",
        "nfci", "dgs10", "term_spread",
    ]
    corr_cols = [c for c in corr_cols if c in df.columns]
    corr = df[corr_cols].corr().round(4)
    corr.to_csv(OUTPUT / "table_correlation.csv")
    print(f"  Correlation matrix saved -> {OUTPUT / 'table_correlation.csv'}")
    print(corr.to_string())

    # ── 3. Bank-level summary ──────────────────────────────────────────────
    print("\n[3] Bank-level summary (one row per bank)")

    bank = (df.groupby(["rssd9001", "rssd9017"])
              .agg(
                  quarters      = ("rssd9999", "count"),
                  mean_L_it     = ("L_it",     "mean"),
                  max_L_it      = ("L_it",     "max"),
                  mean_assets_bn= ("rcfd2170", lambda x: x.mean() / 1e6),
                  mean_cap_ratio= ("capital_ratio", "mean"),
                  first_quarter = ("rssd9999", "min"),
                  last_quarter  = ("rssd9999", "max"),
              )
              .reset_index()
              .sort_values("mean_L_it", ascending=False))

    bank.to_csv(OUTPUT / "table_bank_summary.csv", index=False, float_format="%.6f")
    print(f"  Bank summary saved -> {OUTPUT / 'table_bank_summary.csv'}")
    print(f"\n  Top 20 banks by mean L_it:")
    pd.set_option("display.max_colwidth", 35)
    print(bank.head(20)[["rssd9017", "quarters", "mean_L_it",
                          "mean_assets_bn", "mean_cap_ratio"]].to_string(index=False))

    # ── 4. L_it histogram ─────────────────────────────────────────────────
    print("\n[4] L_it distribution histogram")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # Left: full distribution (excluding zeros)
    nonzero = df["L_it"][df["L_it"] > 0]
    axes[0].hist(nonzero, bins=60, color=NAVY, alpha=0.8, edgecolor="white", linewidth=0.3)
    axes[0].axvline(nonzero.mean(),   color=BLUE, lw=1.5, ls="--", label=f"Mean = {nonzero.mean():.4f}")
    axes[0].axvline(nonzero.median(), color="gray", lw=1.5, ls=":",  label=f"Median = {nonzero.median():.4f}")
    axes[0].set_xlabel("L_it  (non-zero observations)")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title(f"L_it distribution  (n = {len(nonzero):,}, excl. zeros)")
    axes[0].legend(frameon=False, fontsize=9)

    # Right: log scale to show full range
    axes[1].hist(nonzero, bins=80, color=NAVY, alpha=0.8, edgecolor="white", linewidth=0.3,
                 log=True)
    axes[1].set_xlabel("L_it  (non-zero observations)")
    axes[1].set_ylabel("Frequency  (log scale)")
    axes[1].set_title("L_it distribution  (log-scale frequency)")

    fig.suptitle("Distribution of L_it  -  FFIEC 031 banks, 2005-2023", y=1.01)
    fig.tight_layout()
    fig.savefig(OUTPUT / "fig_lit_histogram.png", bbox_inches="tight")
    plt.close()
    print(f"  Histogram saved -> {OUTPUT / 'fig_lit_histogram.png'}")

    # ── 5. Pre/post 2010 comparison ────────────────────────────────────────
    print("\n[5] Pre/post-2010 comparison")
    for period, label in [
        (df["year"] < 2010,  "2005-2009 (rcfdj458 absent)"),
        (df["year"] >= 2010, "2010-2023 (rcfdj458 present)"),
    ]:
        sub = df[period]
        print(f"\n  {label}  n={len(sub):,}  banks={sub['rssd9001'].nunique()}")
        for col in ["L_it", "L_middle", "L_lines"]:
            if col in sub.columns:
                print(f"    {col:<20}  mean={sub[col].mean():.6f}  "
                      f"median={sub[col].median():.6f}")

    print("\n  Done. Phase 0 data preparation complete.")
    print("  All outputs in:", OUTPUT)
    print("\n  Files produced:")
    for f in sorted(OUTPUT.glob("*")):
        print(f"    {f.name}")


if __name__ == "__main__":
    main()