// components/chart.tsx
import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";
import type { ComponentType } from "react";

const Plot = dynamic(
  () => import("react-plotly.js"),
  { ssr: false }
) as ComponentType<PlotParams>;

const BASE_LAYOUT: Partial<PlotParams["layout"]> = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor:  "rgba(0,0,0,0)",
  font:          { family: "Inter, sans-serif", color: "#1A1A1A" },
  xaxis:         { showgrid: false, color: "#6B7280" },
  yaxis:         { showgrid: true,  gridcolor: "#F0F0F0", color: "#6B7280" },
  margin:        { l: 0, r: 0, t: 30, b: 0 },
  hovermode:     "x unified",
  legend:        { orientation: "h" as const, yanchor: "bottom", y: 1.02 },
};

export function Chart({
  data, layout = {}, height = 300, className = "",
}: {
  data:      PlotParams["data"];
  layout?:   Partial<PlotParams["layout"]>;
  height?:   number;
  className?: string;
}) {
  return (
    <Plot
      data={data}
      layout={{ ...BASE_LAYOUT, height, ...layout }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%", height }}
      className={className}
    />
  );
}