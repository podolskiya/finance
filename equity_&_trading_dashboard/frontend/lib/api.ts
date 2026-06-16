// lib/api.ts
import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
});

// ── Market endpoints ──
export const getIndices = () =>
  api.get("/market/indices").then(r => r.data);

export const getWatchlist = (tickers?: string[]) =>
  api.get("/market/watchlist", {
    params: tickers ? { tickers: tickers.join(",") } : {}
  }).then(r => r.data);

export const getPerformance = (tickers: string[], period = "6mo") =>
  api.get("/market/performance", {
    params: { tickers: tickers.join(","), period }
  }).then(r => r.data);

export const getSectors = (period = "1mo") =>
  api.get("/market/sectors", { params: { period } }).then(r => r.data);

// ── Backtest endpoints ──
export interface BacktestParams {
  ticker:        string;
  start:         string;
  end:           string;
  strategy:      "Momentum" | "Mean Reversion" | "Combined";
  capital:       number;
  commission:    number;
  slippage:      number;
  short_window?: number;
  long_window?:  number;
  bb_window?:    number;
  bb_std?:       number;
}

export const runBacktest = (params: BacktestParams) =>
  api.post("/backtest/run", params).then(r => r.data);