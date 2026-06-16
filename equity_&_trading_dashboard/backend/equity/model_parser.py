# equity/model_parser.py
import pandas as pd
import numpy as np
import re
from difflib import SequenceMatcher

YEAR_PATTERN = re.compile(r'(19|20)\d{2}')
PROJECTION_PATTERN = re.compile(r'(e|est|proj|f|fcst)\s*$', re.IGNORECASE)

# ── 24 Canonical Financial Line Items ─────────────────
CANONICAL_ITEMS = {
    "Revenue":             ["total revenue","revenue","net revenue","net sales","sales","turnover"],
    "COGS":                ["cost of goods sold","cost of revenue","cogs","cost of sales"],
    "Gross Profit":        ["gross profit","gross income","gross margin"],
    "SG&A":                ["sg&a","selling general and administrative","selling general & administrative","opex","operating expenses"],
    "R&D":                 ["research and development","r&d","research & development"],
    "EBITDA":              ["ebitda","adjusted ebitda"],
    "D&A":                 ["depreciation and amortization","depreciation & amortization","d&a","depreciation"],
    "Operating Income":    ["operating income","ebit","income from operations","operating profit"],
    "Interest Expense":    ["interest expense","net interest expense","finance costs"],
    "Pretax Income":       ["pretax income","income before tax","earnings before tax","ebt","income before taxes"],
    "Tax Expense":         ["income tax","tax provision","income tax expense","taxes"],
    "Net Income":          ["net income","net earnings","net profit","profit for the year","profit attributable"],
    "EPS":                 ["eps","earnings per share","diluted eps","basic eps"],
    "Shares Outstanding":  ["shares outstanding","diluted shares","weighted average shares","share count","diluted weighted average"],
    "Total Assets":        ["total assets"],
    "Total Liabilities":   ["total liabilities"],
    "Total Equity":        ["total equity","total stockholders equity","shareholders equity","stockholders' equity","total shareholders'"],
    "Cash":                ["cash and cash equivalents","cash & equivalents","cash and equivalents"],
    "Total Debt":          ["total debt","long term debt","total borrowings"],
    "Current Assets":      ["total current assets","current assets"],
    "Current Liabilities": ["total current liabilities","current liabilities"],
    "CapEx":               ["capital expenditure","capex","purchases of property","capital expenditures","ppe purchases"],
    "Operating Cash Flow": ["cash from operations","operating cash flow","net cash provided by operating","cash flow from operations","cfo"],
    "Dividends":           ["dividends paid","dividends","total dividends","dividend payments"],
}


# ── Sheet Parsing ──────────────────────────────────────
def load_workbook_sheets(file) -> dict:
    """Load all sheets as raw DataFrames (no header assumption)."""
    xls = pd.ExcelFile(file)
    return {name: pd.read_excel(xls, sheet_name=name, header=None)
            for name in xls.sheet_names}


def detect_header_row(df: pd.DataFrame, max_scan: int = 15) -> int | None:
    """Find the row containing the most year-like values (period header)."""
    best_row, best_count = None, 0
    for i in range(min(max_scan, len(df))):
        row = df.iloc[i]
        count = sum(1 for v in row if YEAR_PATTERN.search(str(v)))
        if count > best_count:
            best_count, best_row = count, i
    return best_row if best_count >= 2 else None


def extract_year(period: str) -> int:
    m = YEAR_PATTERN.search(str(period))
    return int(m.group()) if m else 0


def parse_sheet(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    Detect period header row + label column, then extract
    every labelled row with its time-series values.
    """
    header_row = detect_header_row(df)
    if header_row is None:
        return pd.DataFrame(), []

    header = df.iloc[header_row]
    period_cols = [j for j, v in enumerate(header)
                    if YEAR_PATTERN.search(str(v))]
    non_period   = [j for j in range(len(header)) if j not in period_cols]
    label_col    = min(non_period) if non_period else 0
    periods      = [str(header[j]).strip() for j in period_cols]

    rows = []
    for i in range(header_row + 1, len(df)):
        label = df.iloc[i, label_col]
        if pd.isna(label) or str(label).strip() == "":
            continue
        label = str(label).strip()

        values = []
        for j in period_cols:
            v = df.iloc[i, j]
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                values.append(np.nan)

        if all(np.isnan(v) for v in values):
            continue
        rows.append([label] + values)

    if not rows:
        return pd.DataFrame(), []

    return pd.DataFrame(rows, columns=["Label"] + periods), periods


# ── Fuzzy Label Matching ───────────────────────────────
def _clean(text: str) -> str:
    return re.sub(r'[^a-z0-9 &]', '', text.lower().strip())


def match_label(label: str) -> tuple[str | None, float]:
    """Match a row label to a canonical item, return (item, confidence)."""
    label_clean = _clean(label)
    best_item, best_score = None, 0.0

    for canonical, synonyms in CANONICAL_ITEMS.items():
        for syn in synonyms:
            score = SequenceMatcher(None, label_clean, syn).ratio()
            if syn in label_clean or label_clean in syn:
                score = max(score, 0.85)
            if score > best_score:
                best_score, best_item = score, canonical

    return best_item, round(best_score, 2)


def build_mapping(parsed_df: pd.DataFrame, threshold: float = 0.55) -> pd.DataFrame:
    """Add Mapped Item + Confidence columns to a parsed sheet."""
    mapped, conf = [], []
    for label in parsed_df['Label']:
        item, score = match_label(label)
        mapped.append(item if score >= threshold else None)
        conf.append(score)

    out = parsed_df.copy()
    out.insert(1, 'Mapped Item', mapped)
    out.insert(2, 'Confidence',  conf)
    return out


# ── Combine Multiple Sheets into One Model ────────────
def build_full_model(sheets_dict: dict) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """
    Parse + map every sheet, then build a single canonical
    (item × period) table using the highest-confidence match
    for each canonical item.

    Returns: (canonical_table, combined_mapping_df, period_cols)
    """
    all_mapped = []
    all_periods = set()

    for name, raw_df in sheets_dict.items():
        parsed, periods = parse_sheet(raw_df)
        if parsed.empty:
            continue
        mapped = build_mapping(parsed)
        mapped['Sheet'] = name
        all_mapped.append(mapped)
        all_periods.update(periods)

    if not all_mapped:
        return pd.DataFrame(), pd.DataFrame(), []

    combined    = pd.concat(all_mapped, ignore_index=True, sort=False)
    period_cols = sorted(all_periods, key=extract_year)

    canonical = build_canonical_from_mapping(combined, period_cols)
    return canonical, combined, period_cols


def build_canonical_from_mapping(combined: pd.DataFrame,
                                  period_cols: list) -> pd.DataFrame:
    """Build item × period table from a (possibly user-edited) mapping."""
    rows = {}
    for item in CANONICAL_ITEMS:
        candidates = combined[combined['Mapped Item'] == item]
        if candidates.empty:
            continue
        best = candidates.sort_values('Confidence', ascending=False).iloc[0]
        rows[item] = [
            best[p] if p in best.index and pd.notna(best.get(p)) else np.nan
            for p in period_cols
        ]
    return pd.DataFrame(rows, index=period_cols).T


def classify_periods(periods: list) -> tuple[list, list]:
    """Split periods into historical vs projected based on suffix."""
    hist, proj = [], []
    for p in periods:
        if PROJECTION_PATTERN.search(str(p).strip()):
            proj.append(p)
        else:
            hist.append(p)
    return hist, proj