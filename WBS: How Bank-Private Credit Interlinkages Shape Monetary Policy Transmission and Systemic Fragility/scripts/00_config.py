"""
00_config.py
------------
Central config for the dissertation pipeline. 
All the important paths, constants, and definitions live here.

Import it everywhere with: from config import *
"""

from pathlib import Path

# Project structure #
ROOT = Path(__file__).resolve().parent.parent

RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
OUTPUT = ROOT / "outputs"

for d in [RAW, CLEAN, OUTPUT]:
    d.mkdir(parents=True, exist_ok=True)

# Raw data files #
F_RCFD1 = RAW / "rcfd1.csv"      # rcfd3820, rcfd1764, rcfd1763, rcfd3433, rcfd3819, rcfdj454, full pv-series (NDFI breakdown, 2024Q4+ only) #
F_RCFD2 = RAW / "rcfd2.csv"      # rcfdj457/458/459, rcfd2170, rcfd3210, rcfd3818, rcfd3817 #
# RCONJ454 supplement #
F_RCONJ454 = RAW / "rconj454.csv"

# FRED macro series (manually downloaded) #
F_NFCI = RAW / "NFCI.csv"
F_NFCICREDIT = RAW / "NFCICREDIT.csv"
F_DGS10 = RAW / "DGS10.csv"
F_FEDFUNDS = RAW / "FEDFUNDS.csv"

# Jarocinski-Karadi monetary policy shocks (monthly) - accessible via https://marekjarocinski.github.io/jkshocks/jkshocks.html #
F_SHOCKS_MONTHLY = RAW / "shocks_fed_jk_m.csv"

# DealScan & BDC supplements #
# Manually reviewed DEALSCAN with 4 structurally ambiguous cases and 2 merger-timing cases excluded. See 08_dealscan_lender_match.py #
F_DEALSCAN_FULL_PULL = RAW / "dealscan_full_pull.csv"
F_DEALSCAN_CROSSWALK = RAW / "dealscan_confirmed_crosswalk.csv"

F_BDC_CAPIQ = RAW / "CapitalIQ_BDCs.xlsx"
F_BDC_XBRL = RAW / "Master_BDC_Layer3_Breakouts.csv"

# Cleaned outputs #
F_PANEL_RAW = CLEAN / "panel_raw.parquet"
F_PANEL_CLEAN = CLEAN / "panel_clean.parquet"
F_PANEL_CSV = CLEAN / "panel_clean.csv"           
F_PANEL_MACRO = CLEAN / "panel_macro.parquet"
F_PANEL_MACRO_CSV = CLEAN / "panel_macro.csv"
F_MACRO_QUARTERLY = CLEAN / "macro_quarterly.csv"

# Sample parameters #
FILING_TYPE = 31
START_DATE = "2004-10-01"      # one quarter lag before analysis start #
END_DATE = "2025-12-31"        # latest WRDS pull available #

MIN_ASSETS_USD = 300_000       # $300 million threshold (in WRDS thousands) #
MERGER_JUMP_THRESHOLD = 0.50   # flag big one-quarter jumps of assets #

# Winsorization (used in 02_linkage_index.py) #
WINSOR_LOWER = 0.01
WINSOR_HIGH = 0.99

# ID columns for matching #
ID_COLS = ["rssd9001", "rssd9999"]

# Items that should be treated as zero when missing #
# (FFIEC 031 filers should report these on Schedule RC-L) #
RC_L_ZERO_FILL_COLS = [
    "rcfd3819", "rcfd3433", "rcfd3820",
    "rcfdj457", "rcfdj458", "rcfdj459", "rcfd3817",
    "rconj454",   # zero-filled pre-2010 #
]

# L_it definition (current version) #
# L_it = (rcfd3819 + rcfd3433 + rcfdj458 + rconj454) / rcfd2170
#
# Notes:
#   - rcfdj458 and rconj454 start in 2010 (zero-filled before)
#   - rcfd3819 & rcfd3433 have excellent coverage from 2005
#   - RCFD1520 was never available (Premium subscription needed)
#   - RCONJ454 turned out to be the perfect domestic-office substitute