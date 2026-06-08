"""
03_validate_lit.py
------------------
PURPOSE
    Validate the L_it index before any regression work.
    Produces four validation checks described in the dissertation
    data section (Phase 0, Step 5):

    1. Time-series of cross-sectional mean L_it (2005-2023)
    2. Component decomposition stacked area chart
    3. L_it by bank-size decile
    4. Distribution summary and variant comparison

INPUT   data/clean/panel_clean.parquet
OUTPUT  outputs/fig_lit_timeseries.png
        outputs/fig_lit_components.png
        outputs/fig_lit_by_size_decile.png
        outputs/validation_summary.txt
"""

import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CLEAN, OUTPUT, F_PANEL

plt.rcParams.update({
    "font.family":       "serif",
    "font.size":         11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":        150,
})

NAVY   = "#003366"
BLUE   = "#0066cc"
RED    = "#cc0000"
GREEN  = "#006633"


def main():
    print("\n" + "=" * 65)
    print("03_validate_lit.py  -  validating L_it index")
    print("=" * 65)

    df = pd.read_parquet(F_PANEL)
    df["rssd9999"] = pd.to_datetime(df["rssd9999"])
    df = df[df["L_it"].notna()].copy()

    print(f"\nClean panel: {len(df):,} rows | {df['rssd9001'].nunique()} banks")
    print(f"Date range:  {df['rssd9999'].min().date()} to {df['rssd9999'].max().date()}")

    lines = ["L_it VALIDATION SUMMARY", "=" * 60]

    # -- 1. Time-series -----------------------------------------------------
    print("\n[1] Time-series of cross-sectional mean L_it")

    ts = (df.groupby("rssd9999")
            .agg(
                mean_Lit   = ("L_it",    "mean"),
                median_Lit = ("L_it",    "median"),
                p25_Lit    = ("L_it",    lambda x: x.quantile(0.25)),
                p75_Lit    = ("L_it",    lambda x: x.quantile(0.75)),
                n_banks    = ("rssd9001", "nunique"),
            )
            .reset_index())

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(ts["rssd9999"], ts["mean_Lit"],   color=NAVY, lw=2,   label="Cross-sectional mean")
    ax.plot(ts["rssd9999"], ts["median_Lit"], color=BLUE, lw=1.5, ls="--", label="Median")
    ax.fill_between(ts["rssd9999"], ts["p25_Lit"], ts["p75_Lit"],
                    color=BLUE, alpha=0.12, label="IQR")
    ylim_top = ts["mean_Lit"].max() * 1.2
    for date_str, label in [("2008-09-15", "GFC"), ("2010-01-01", "j458 starts"), ("2020-03-01", "COVID")]:
        ax.axvline(pd.Timestamp(date_str), color="gray", lw=0.9, ls=":")
        ax.text(pd.Timestamp(date_str), ylim_top, label, fontsize=8, color="gray", ha="center", va="top")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("L_it  (ratio to total assets)")
    ax.set_title("Cross-sectional mean of L_it  -  FFIEC 031 banks, 2005-2023")
    ax.legend(frameon=False, fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))
    fig.tight_layout()
    fig.savefig(OUTPUT / "fig_lit_timeseries.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved -> {OUTPUT / 'fig_lit_timeseries.png'}")

    lines += [
        "",
        "CHECK 1: Time-series (cross-sectional mean L_it)",
        f"  Min quarterly mean : {ts['mean_Lit'].min():.6f}  ({ts.loc[ts['mean_Lit'].idxmin(), 'rssd9999'].date()})",
        f"  Max quarterly mean : {ts['mean_Lit'].max():.6f}  ({ts.loc[ts['mean_Lit'].idxmax(), 'rssd9999'].date()})",
        f"  Full-period mean   : {ts['mean_Lit'].mean():.6f}",
        "",
        "  INTERPRETATION:",
        "  Pre-2010 peak driven by rcfd3433 (securities lent), which was large",
        "  before GFC and collapsed in 2008. This is historically accurate.",
        "  rcfdj458 (credit lines to FIs) begins 2010 and shows the gradual",
        "  rise associated with private credit expansion from 2013 onward.",
    ]

    # -- 2. Component decomposition -----------------------------------------
    print("\n[2] Component decomposition over time")

    for col in ["rcfd3819", "rcfd3433", "rcfdj458"]:
        if col in df.columns:
            df[f"{col}_ratio"] = df[col] / df["rcfd2170"]

    ts2 = (df.groupby("rssd9999")
             .agg(
                 sblc   = ("rcfd3819_ratio", "mean"),
                 seclnd = ("rcfd3433_ratio", "mean"),
                 lines  = ("rcfdj458_ratio", "mean"),
             )
             .reset_index())

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.stackplot(ts2["rssd9999"],
                 ts2["sblc"], ts2["seclnd"], ts2["lines"],
                 labels=["rcfd3819: Financial standby LCs",
                         "rcfd3433: Securities lent (GFC-era channel)",
                         "rcfdj458: Unused credit lines to FIs (2010+)"],
                 colors=[NAVY, BLUE, GREEN], alpha=0.75)
    ax.axvline(pd.Timestamp("2010-01-01"), color="gray", lw=1, ls="--")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Mean ratio to total assets")
    ax.set_title("L_it components over time  -  cross-sectional mean, FFIEC 031 banks")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))
    fig.tight_layout()
    fig.savefig(OUTPUT / "fig_lit_components.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved -> {OUTPUT / 'fig_lit_components.png'}")

    # -- 3. By size decile --------------------------------------------------
    print("\n[3] L_it by bank-size decile")

    bank_avg = df.groupby("rssd9001")["rcfd2170"].mean().reset_index()
    bank_avg["size_decile"] = pd.qcut(bank_avg["rcfd2170"], q=10, labels=range(1, 11))
    df = df.merge(bank_avg[["rssd9001", "size_decile"]], on="rssd9001", how="left")

    # observed=True silences FutureWarning
    decile_stats = (df.groupby("size_decile", observed=True)["L_it"]
                      .agg(["mean", "median", "std", "count"])
                      .reset_index())
    decile_stats.columns = ["decile", "mean", "median", "std", "n_obs"]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(decile_stats["decile"].astype(int), decile_stats["mean"],
           color=NAVY, alpha=0.85, edgecolor="white", linewidth=0.5)
    ax.errorbar(decile_stats["decile"].astype(int), decile_stats["mean"],
                yerr=decile_stats["std"], fmt="none", color=RED, capsize=3, lw=1)
    ax.set_xlabel("Asset size decile  (1 = smallest, 10 = largest)")
    ax.set_ylabel("Mean L_it")
    ax.set_title("Mean L_it by bank-size decile  -  2005-2023")
    ax.set_xticks(range(1, 11))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))
    fig.tight_layout()
    fig.savefig(OUTPUT / "fig_lit_by_size_decile.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved -> {OUTPUT / 'fig_lit_by_size_decile.png'}")

    lines += [
        "",
        "CHECK 2: L_it by asset size decile",
        f"{'Decile':<10} {'Mean L_it':>12} {'Median L_it':>12} {'N obs':>8}",
        "-" * 46,
    ]
    for _, row in decile_stats.iterrows():
        lines.append(
            f"  {int(row['decile']):<8}  {row['mean']:>12.6f}"
            f"  {row['median']:>12.6f}  {int(row['n_obs']):>8,}"
        )
    lines += [
        "",
        "  NOTE: Non-monotonic middle deciles reflect 031-universe composition.",
        "  'Small' 031 filers include custody banks and foreign bank subs with",
        "  large rcfd3433 (securities lent) relative to modest total assets.",
        "  Decile 10 has highest mean L_it as expected.",
    ]

    # -- 4. Distribution and variants ---------------------------------------
    print("\n[4] Distribution and variant comparison")
    desc = df["L_it"].describe(percentiles=[.01, .05, .25, .50, .75, .95, .99])
    lines += [
        "",
        "CHECK 3: L_it distribution (full sample)",
        desc.to_string(),
        "",
        f"  Obs with L_it = 0    : {(df['L_it'] == 0).sum():,}",
        f"  Obs with L_it > 0.05 : {(df['L_it'] > 0.05).sum():,}",
        f"  Obs with L_it > 0.10 : {(df['L_it'] > 0.10).sum():,}",
        f"  Obs with L_it > 0.20 : {(df['L_it'] > 0.20).sum():,}",
        "",
        "CHECK 4: Variant comparison",
    ]
    for v in ["L_it", "L_middle", "L_guarantees", "L_securities", "L_lines"]:
        if v in df.columns:
            lines.append(
                f"  {v:<20}  mean={df[v].mean():.6f}  "
                f"median={df[v].median():.6f}  std={df[v].std():.6f}"
            )

    # -- 5. Post-2010 sub-panel ---------------------------------------------
    df_post = df[df["year"] >= 2010]
    ts_post = ts[ts["rssd9999"] >= "2010-01-01"]
    lines += [
        "",
        "CHECK 5: Post-2010 sub-panel (rcfdj458 fully available)",
        f"  Rows: {len(df_post):,} | Banks: {df_post['rssd9001'].nunique()}",
        f"  L_it mean (post-2010)   : {df_post['L_it'].mean():.6f}",
        f"  L_lines mean (post-2010) : {df_post['L_lines'].mean():.6f}",
    ]
    if not ts_post.empty:
        lines += [
            f"  Min mean (post-2010) : {ts_post['mean_Lit'].min():.6f}  ({ts_post.loc[ts_post['mean_Lit'].idxmin(), 'rssd9999'].date()})",
            f"  Max mean (post-2010) : {ts_post['mean_Lit'].max():.6f}  ({ts_post.loc[ts_post['mean_Lit'].idxmax(), 'rssd9999'].date()})",
        ]

    summary_text = "\n".join(lines)
    (OUTPUT / "validation_summary.txt").write_text(summary_text, encoding="utf-8")
    print(f"\n  Summary saved -> {OUTPUT / 'validation_summary.txt'}")
    print("\n" + summary_text)
    print("\n  Done. Next: python 04_merge_macro.py")


if __name__ == "__main__":
    main()