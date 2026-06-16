// app/backtester/page.tsx
"use client";

import { useState } from "react";
import { runBacktest, BacktestParams } from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import { Chart }      from "@/components/chart";
import {
  Input, Select, Slider,
  DateInput, SidebarSection, RunButton,
} from "@/components/controls";

// ── Types ─────────────────────────────────────────────
interface Metrics {
  "Sharpe Ratio": number;
  "Max Drawdown": string;
  "CAGR":         string;
  "Win Rate":     string;
  "Final Equity": string;
  "Total Return": string;
}

interface BacktestResult {
  metrics:       Metrics;
  equity_curve: {
    strategy: { dates: string[]; values: number[] };
    buy_hold: { dates: string[]; values: number[] };
  };
  drawdown:     { dates: string[]; values: number[] };
  signals: {
    price:  { dates: string[]; values: number[] };
    longs:  { dates: string[]; prices: number[] };
    shorts: { dates: string[]; prices: number[] };
  };
  distributions: {
    bins:     number[];
    strategy: number[];
    market:   number[];
  };
}

// ── Helpers ───────────────────────────────────────────
const STRATEGY_OPTIONS: { label: string; value: BacktestParams["strategy"] }[] = [
  { label: "Momentum",       value: "Momentum"      },
  { label: "Mean Reversion", value: "Mean Reversion"},
  { label: "Combined",       value: "Combined"      },
];

function pct(s: string) { return parseFloat(s.replace("%","").replace("$","").replace(",","")) > 0; }

// ── Page ──────────────────────────────────────────────
export default function BacktesterPage() {
  // Form state
  const [ticker,      setTicker]      = useState("AAPL");
  const [start,       setStart]       = useState("2020-01-01");
  const [end,         setEnd]         = useState("2024-01-01");
  const [strategy,    setStrategy]    = useState<BacktestParams["strategy"]>("Momentum");
  const [capital,     setCapital]     = useState(100_000);
  const [commission,  setCommission]  = useState(0.1);
  const [slippage,    setSlippage]    = useState(0.05);
  const [shortWindow, setShortWindow] = useState(20);
  const [longWindow,  setLongWindow]  = useState(60);
  const [bbWindow,    setBbWindow]    = useState(20);
  const [bbStd,       setBbStd]       = useState(2.0);

  const [result,  setResult]  = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runBacktest({
        ticker:       ticker.toUpperCase(),
        start, end, strategy, capital,
        commission:   commission / 100,
        slippage:     slippage  / 100,
        short_window: shortWindow,
        long_window:  longWindow,
        bb_window:    bbWindow,
        bb_std:       bbStd,
      });
      setResult(data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const m = result?.metrics;

  return (
    <div className="flex gap-6 h-full">

      {/* ── Left: Controls Panel ── */}
      <aside className="w-64 bg-sidebar rounded-[16px] p-5
                        flex flex-col gap-4 shrink-0 self-start">
        <div className="text-white font-semibold text-sm">
          ⚡ Backtest Settings
        </div>

        <Input
          label="Ticker"
          value={ticker}
          onChange={setTicker}
          placeholder="AAPL"
        />

        <div className="grid grid-cols-2 gap-3">
          <DateInput label="Start" value={start} onChange={setStart} />
          <DateInput label="End"   value={end}   onChange={setEnd}   />
        </div>

        <Select
          label="Strategy"
          value={strategy}
          options={STRATEGY_OPTIONS}
          onChange={setStrategy}
        />

        {(strategy === "Momentum" || strategy === "Combined") && (
          <>
            <SidebarSection title="Momentum Params" />
            <Slider label="Short MA" value={shortWindow}
                    min={5} max={50}
                    onChange={setShortWindow} />
            <Slider label="Long MA"  value={longWindow}
                    min={20} max={200}
                    onChange={setLongWindow} />
          </>
        )}

        {(strategy === "Mean Reversion" || strategy === "Combined") && (
          <>
            <SidebarSection title="Mean Reversion Params" />
            <Slider label="BB Window" value={bbWindow}
                    min={5} max={50}
                    onChange={setBbWindow} />
            <Slider label="BB Std Dev" value={bbStd}
                    min={1.0} max={3.0} step={0.1}
                    format={(v) => v.toFixed(1)}
                    onChange={setBbStd} />
          </>
        )}

        <SidebarSection title="Portfolio" />
        <Slider label="Capital ($)"    value={capital}
                min={10_000} max={1_000_000} step={10_000}
                format={(v) => `$${(v/1000).toFixed(0)}k`}
                onChange={setCapital} />
        <Slider label="Commission (%)" value={commission}
                min={0} max={0.5} step={0.01}
                format={(v) => `${v.toFixed(2)}%`}
                onChange={setCommission} />
        <Slider label="Slippage (%)"   value={slippage}
                min={0} max={0.5} step={0.01}
                format={(v) => `${v.toFixed(2)}%`}
                onChange={setSlippage} />

        <RunButton onClick={handleRun} loading={loading} />
      </aside>

      {/* ── Right: Results ── */}
      <div className="flex-1 space-y-5">

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="card flex flex-col items-center justify-center
                          py-24 text-center">
            <div className="text-5xl mb-4">⚡</div>
            <div className="font-semibold text-lg">Configure & Run a Backtest</div>
            <div className="text-text-secondary text-sm mt-2">
              Set your parameters in the panel and click Run
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="card flex items-center justify-center py-24">
            <div className="text-text-secondary animate-pulse">
              Running {strategy} backtest on {ticker.toUpperCase()}...
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card border-l-4 border-danger bg-danger-bg">
            <div className="font-semibold text-danger-fg">Error</div>
            <div className="text-sm text-danger-fg mt-1">{error}</div>
          </div>
        )}

        {/* Results */}
        {result && m && (
          <>
            {/* Metric Cards */}
            <div className="grid grid-cols-6 gap-3">
              {[
                { label: "Total Return",  value: m["Total Return"],
                  pos: pct(m["Total Return"]) },
                { label: "CAGR",          value: m["CAGR"],
                  pos: pct(m["CAGR"]) },
                { label: "Sharpe Ratio",  value: String(m["Sharpe Ratio"]),
                  pos: m["Sharpe Ratio"] > 0 },
                { label: "Max Drawdown",  value: m["Max Drawdown"],
                  pos: false },
                { label: "Win Rate",      value: m["Win Rate"],
                  pos: pct(m["Win Rate"]) },
                { label: "Final Equity",  value: m["Final Equity"],
                  pos: null },
              ].map(({ label, value, pos }) => (
                <MetricCard
                  key={label} label={label} value={value}
                  positive={pos === null ? undefined : pos}
                />
              ))}
            </div>

            {/* Equity Curve */}
            <div className="card">
              <div className="font-semibold mb-3">
                📈 Equity Curve vs Buy & Hold
              </div>
              <Chart
                height={300}
                data={[
                  {
                    type: "scatter",
                    mode: "lines",
                    name: "Strategy",
                    x: result.equity_curve.strategy.dates,
                    y: result.equity_curve.strategy.values,
                    line: { color: "#1A1A1A", width: 2.5 },
                    fill: "tozeroy",
                    fillcolor: "rgba(26,26,26,0.05)",
                  },
                  {
                    type: "scatter",
                    mode: "lines",
                    name: "Buy & Hold",
                    x: result.equity_curve.buy_hold.dates,
                    y: result.equity_curve.buy_hold.values,
                    line: { color: "#10B981", width: 2, dash: "dash" },
                  },
                ]}
                layout={{
                  yaxis: { tickprefix: "$", tickformat: ",.0f",
                           gridcolor: "#F0F0F0" },
                }}
              />
            </div>

            {/* Drawdown + Distribution */}
            <div className="grid grid-cols-2 gap-5">
              <div className="card">
                <div className="font-semibold mb-3">📉 Drawdown</div>
                <Chart
                  height={220}
                  data={[{
                    type: "scatter",
                    mode: "lines",
                    name: "Drawdown",
                    x: result.drawdown.dates,
                    y: result.drawdown.values,
                    line:      { color: "#EF4444", width: 1.5 },
                    fill:      "tozeroy",
                    fillcolor: "rgba(239,68,68,0.08)",
                  }]}
                  layout={{
                    yaxis: { ticksuffix: "%", gridcolor: "#F0F0F0" },
                  }}
                />
              </div>

              <div className="card">
                <div className="font-semibold mb-3">
                  📊 Returns Distribution
                </div>
                <Chart
                  height={220}
                  data={[
                    {
                      type:   "bar",
                      name:   "Buy & Hold",
                      x:      result.distributions.bins,
                      y:      result.distributions.market,
                      marker: { color: "#10B981", opacity: 0.5 },
                    },
                    {
                      type:   "bar",
                      name:   "Strategy",
                      x:      result.distributions.bins,
                      y:      result.distributions.strategy,
                      marker: { color: "#1A1A1A", opacity: 0.6 },
                    },
                  ]}
                  layout={{
                    barmode: "overlay",
                    xaxis: { ticksuffix: "%" },
                  }}
                />
              </div>
            </div>

            {/* Price + Signals */}
            <div className="card">
              <div className="font-semibold mb-3">🎯 Price & Signals</div>
              <Chart
                height={260}
                data={[
                  {
                    type: "scatter", mode: "lines",
                    name: "Price",
                    x: result.signals.price.dates,
                    y: result.signals.price.values,
                    line: { color: "#6B7280", width: 1.5 },
                  },
                  {
                    type: "scatter", mode: "markers",
                    name: "Long",
                    x: result.signals.longs.dates,
                    y: result.signals.longs.prices,
                    marker: { symbol: "triangle-up", color: "#10B981", size: 8 },
                  },
                  {
                    type: "scatter", mode: "markers",
                    name: "Short",
                    x: result.signals.shorts.dates,
                    y: result.signals.shorts.prices,
                    marker: { symbol: "triangle-down", color: "#EF4444", size: 8 },
                  },
                ]}
                layout={{ yaxis: { tickprefix: "$" } }}
              />
            </div>

            {/* Download */}
            <button
              onClick={() => {
                const rows = result.equity_curve.strategy.dates.map((d, i) => ({
                  date:     d,
                  strategy: result.equity_curve.strategy.values[i],
                  buy_hold: result.equity_curve.buy_hold.values[i],
                  drawdown: result.drawdown.values[i] ?? "",
                }));
                const csv = [
                  Object.keys(rows[0]).join(","),
                  ...rows.map(r => Object.values(r).join(",")),
                ].join("\n");
                const a = document.createElement("a");
                a.href = URL.createObjectURL(
                  new Blob([csv], { type: "text/csv" })
                );
                a.download = `${ticker}_${strategy}_backtest.csv`;
                a.click();
              }}
              className="text-sm text-text-secondary hover:text-text-primary
                         transition-colors underline underline-offset-2"
            >
              ⬇️ Download Results CSV
            </button>
          </>
        )}
      </div>
    </div>
  );
}