// components/metric-card.tsx
export function MetricCard({
  label, value, sub, positive,
}: { label: string; value: string; sub?: string; positive?: boolean | null }) {
  const subColor = positive === true ? "text-success"
                  : positive === false ? "text-danger"
                  : "text-text-secondary";
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {sub && <div className={`text-xs mt-1 ${subColor}`}>{sub}</div>}
    </div>
  );
}