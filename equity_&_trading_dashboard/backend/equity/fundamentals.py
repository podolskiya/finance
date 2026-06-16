# equity/fundamentals.py
import yfinance as yf
import pandas as pd
import numpy as np

def get_fundamentals(ticker: str) -> dict:
    """
    Fetch comprehensive fundamental data for a company.
    Covers valuation, profitability, growth, health, and dividends.
    """
    stock = yf.Ticker(ticker)
    info  = stock.info

    def safe(key, default=None):
        val = info.get(key, default)
        return val if val not in [None, "N/A", float('inf')] else default

    # --- Valuation ---
    valuation = {
        "Market Cap":        safe("marketCap"),
        "Enterprise Value":  safe("enterpriseValue"),
        "P/E (TTM)":         safe("trailingPE"),
        "Forward P/E":       safe("forwardPE"),
        "P/B Ratio":         safe("priceToBook"),
        "P/S Ratio":         safe("priceToSalesTrailing12Months"),
        "EV/EBITDA":         safe("enterpriseToEbitda"),
        "EV/Revenue":        safe("enterpriseToRevenue"),
        "PEG Ratio":         safe("pegRatio"),
    }

    # --- Profitability ---
    profitability = {
        "Gross Margin":      safe("grossMargins"),
        "Operating Margin":  safe("operatingMargins"),
        "Net Margin":        safe("profitMargins"),
        "ROE":               safe("returnOnEquity"),
        "ROA":               safe("returnOnAssets"),
        "ROIC":              safe("returnOnCapital"),
    }

    # --- Growth ---
    growth = {
        "Revenue Growth (YoY)":   safe("revenueGrowth"),
        "Earnings Growth (YoY)":  safe("earningsGrowth"),
        "EPS (TTM)":              safe("trailingEps"),
        "EPS Forward":            safe("forwardEps"),
    }

    # --- Financial Health ---
    health = {
        "Total Cash":           safe("totalCash"),
        "Total Debt":           safe("totalDebt"),
        "Debt/Equity":          safe("debtToEquity"),
        "Current Ratio":        safe("currentRatio"),
        "Quick Ratio":          safe("quickRatio"),
        "Free Cash Flow":       safe("freeCashflow"),
        "Operating Cash Flow":  safe("operatingCashflow"),
    }

    # --- Dividends ---
    dividends = {
        "Dividend Yield":    safe("dividendYield"),
        "Payout Ratio":      safe("payoutRatio"),
        "5Y Avg Yield":      safe("fiveYearAvgDividendYield"),
    }

    # --- Company Info ---
    company = {
        "Name":      safe("longName"),
        "Sector":    safe("sector"),
        "Industry":  safe("industry"),
        "Country":   safe("country"),
        "Employees": safe("fullTimeEmployees"),
        "Summary":   safe("longBusinessSummary"),
    }

    return {
        "company":       company,
        "valuation":     valuation,
        "profitability": profitability,
        "growth":        growth,
        "health":        health,
        "dividends":     dividends,
    }


def get_financial_statements(ticker: str) -> dict:
    """Fetch income statement, balance sheet, and cash flow."""
    stock = yf.Ticker(ticker)
    return {
        "income_statement": stock.financials,
        "balance_sheet":    stock.balance_sheet,
        "cash_flow":        stock.cashflow,
        "quarterly_income": stock.quarterly_financials,
    }