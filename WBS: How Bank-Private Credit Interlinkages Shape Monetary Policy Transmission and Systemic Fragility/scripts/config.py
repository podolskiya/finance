"""
config.py
---------
Central configuration for the dissertation pipeline.
All paths, constants, and variable definitions live here.
Import this from every script: from config import *
"""

from pathlib import Path

# ── Project root (one level up from scripts/) ─────────────────────────────
ROOT   = Path(__file__).resolve().parent.parent
RAW    = ROOT / "data" / "raw"
CLEAN  = ROOT / "data" / "clean"
OUTPUT = ROOT / "outputs"

for d in [RAW, CLEAN, OUTPUT]:
    d.mkdir(parents=True, exist_ok=True)

# ── Raw file names ─────────────────────────────────────────────────────────
F_OLD   = RAW / "rcfd_old.csv"
F_RCFD1 = RAW / "rcfd1.csv"
F_FIX1  = RAW / "rcfd1_fix1.csv"
F_RCFD2 = RAW / "rcfd2.csv"

# ── Clean output files ─────────────────────────────────────────────────────
F_PANEL     = CLEAN / "panel_clean.parquet"
F_PANEL_CSV = CLEAN / "panel_clean.csv"

# ── Sample definition ──────────────────────────────────────────────────────
FILING_TYPE    = 31
START_DATE     = "2005-01-01"
END_DATE       = "2023-12-31"
MIN_ASSETS_USD = 300_000     # $300m in WRDS thousands

# ── Winsorisation ──────────────────────────────────────────────────────────
WINSOR_LOWER = 0.01
WINSOR_HIGH  = 0.99

# ── Identifier columns ─────────────────────────────────────────────────────
ID_COLS = ["rssd9001", "rssd9999"]

# ── L_it construction notes ────────────────────────────────────────────────
#
# MAIN DEFINITION:
#   L_it = (rcfd3819 + rcfd3433 + rcfdj458) / rcfd2170
#
#   rcfd3819  Financial standby letters of credit  [2005-2023, 100% coverage]
#   rcfd3433  Securities lent with cash collateral [2005-2023, 100% coverage]
#   rcfdj458  Unused commitments to FIs            [2010-2023; zero for 2005-2009]
#   rcfd2170  Total assets (denominator)
#
# WHY NOT rcfd3818 (unused commitments — other, aggregate):
#   rcfd3818 is the aggregate of ALL unused commitments not classified elsewhere.
#   For FFIEC 031 trust-company filers it routinely exceeds total assets (ratio>1),
#   contaminating L_it with non-NBFI commitments. It was retired by FFIEC in 2010
#   and replaced by the precise rcfdj457/458/459 breakdown. We exclude it entirely.
#
# ROBUSTNESS VARIANTS:
#   L_2010    2010-2023 sub-panel (all four components available)
#   L_noJ458  rcfd3819 + rcfd3433 only (2005-2023 continuous, two components)
#
# SENSITIVITY VARIANTS (for regression robustness tables):
#   L_conservative  rcfd3819 only  (guarantees only)
#   L_securities    rcfd3433 only  (securities lending only)
#   L_middle        rcfd3819 + rcfd3433  (two continuous components, full period)
#   L_full          rcfd3819 + rcfd3433 + rcfdj458  (= L_it, three components)