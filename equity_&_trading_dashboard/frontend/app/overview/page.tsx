"use client";

import { useQuery } from "@tanstack/react-query";
import { getIndices, getWatchlist, getSectors } from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";
import type { ComponentType } from "react";

// ── Typed dynamic import ──────────────────────────────
const Plot = dynamic(
  () => import("react-plotly.js"),
  { ssr: false }
) as ComponentType<PlotParams>;

export default function OverviewPage() {
  const { data: indices, isLoading: loadingIndices } = useQuery({
    queryKey: ["indices"],
    queryFn: getIndices,
  });

  const { data: watchlist } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => getWatchlist(),
  });

  const { data: sectors } = useQuery({
    queryKey: ["sectors"],
    queryFn: () => getSectors(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Market Overview</h1>
        <p className="text-text-secondary text-sm mt-1">Live market data</p>
      </div>

      {/* Index Cards */}
      <div className="grid grid-cols-4 gap-4">
        {loadingIndices && (
          <div className="text-text-secondary col-span-4">Loading...</div>
        )}
        {indices?.indices.map((idx: any) => (
          <MetricCard
            key={idx.ticker}
            label={idx.name.toUpperCase()}
            value={idx.price.toLocaleString()}
            sub={`${idx.change_pct >= 0 ? "▲" : "▼"} ${Math.abs(idx.change_pct)}% today`}
            positive={idx.change_pct >= 0}
          />
        ))}
      </div>

      {/* Watchlist */}
      <div className="card">
        <h2 className="font-semibold mb-3">📋 Quick Watchlist</h2>
        <div className="space-y-2">
          {watchlist?.watchlist.map((w: any) => (
            <div
              key={w.ticker}
              className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0"
            >
              <span className="font-semibold">{w.ticker}</span>
              <span>${w.price.toFixed(2)}</span>
              <span className={w.change_pct >= 0 ? "text-success" : "text-danger"}>
                {w.change_pct >= 0 ? "▲" : "▼"} {Math.abs(w.change_pct).toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Sector Performance */}
      <div className="card">
        <h2 className="font-semibold mb-3">📊 Sector Performance (1 Month)</h2>
        {sectors && (
          <Plot
            data={[
              {
                type: "bar",
                orientation: "h" as const,
                x: sectors.sectors.map((s: any) => s.return_pct),
                y: sectors.sectors.map((s: any) => s.sector),
                marker: {
                  color: sectors.sectors.map((s: any) =>
                    s.return_pct >= 0 ? "#10B981" : "#EF4444"
                  ),
                },
                text: sectors.sectors.map(
                  (s: any) => `${s.return_pct.toFixed(2)}%`
                ),
                textposition: "outside" as const,
              },
            ]}
            layout={{
              height: 320,
              margin: { l: 120, r: 60, t: 10, b: 30 },
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)",
              xaxis: { visible: false },
              yaxis: { color: "#6B7280" },
              font: { family: "Inter, sans-serif", color: "#1A1A1A" },
            }}
            config={{ displayModeBar: false }}
            style={{ width: "100%" }}
          />
        )}
      </div>
    </div>
  );
}