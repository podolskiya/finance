// components/sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Zap, GitBranch, Link2, Building2,
         Brain, Newspaper, PieChart, Thermometer, FileSearch,
         Radio, FileSpreadsheet } from "lucide-react";

const NAV_GROUPS = [
  {
    label: "Strategy Lab",
    items: [
      { href: "/overview",     label: "Overview",     icon: LayoutDashboard },
      { href: "/backtester",   label: "Backtester",   icon: Zap },
      { href: "/walk-forward", label: "Walk-Forward", icon: GitBranch },
    ],
  },
  {
    label: "Market Analysis",
    items: [
      { href: "/pairs",  label: "Pairs Trading",  icon: Link2 },
      { href: "/equity", label: "Equity Analysis", icon: Building2 },
      { href: "/model-analyser", label: "Model Analyser", icon: FileSpreadsheet },
    ],
  },
  {
    label: "AI Signals",
    items: [
      { href: "/ml-signals", label: "ML Signals",     icon: Brain },
      { href: "/sentiment",  label: "Sentiment",      icon: Newspaper },
      { href: "/regime",     label: "Regime",         icon: Thermometer },
      { href: "/earnings",   label: "Earnings AI",    icon: FileSearch },
    ],
  },
  {
    label: "Assets",
    items: [
      { href: "/portfolio",    label: "Portfolio",    icon: PieChart },
      { href: "/live-trading", label: "Live Trading", icon: Radio },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-sidebar text-white min-h-screen p-4 flex flex-col">
      <div className="px-2 py-4 mb-4">
        <div className="text-xl font-bold">📈 TradeSmart</div>
        <div className="text-xs text-gray-500 mt-1">Pro Analytics Platform</div>
      </div>

      <nav className="flex-1 overflow-y-auto space-y-6">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="text-[11px] uppercase tracking-wider text-gray-500 px-3 mb-2">
              {group.label}
            </div>
            <div className="space-y-1">
              {group.items.map(({ href, label, icon: Icon }) => {
                const active = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
                        ${active
                          ? "bg-white text-[#1A1A1A] font-semibold"
                          : "text-[#9CA3AF] hover:bg-[#2A2A2A] hover:text-white"
                        }`}
                  >
                    <Icon size={16} />
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="text-[11px] text-gray-500 border-t border-gray-800 pt-3 mt-3">
        Data: Yahoo Finance<br />
        Models: TensorFlow LSTM<br />
        v2.0.0 — TradeSmart Pro
      </div>
    </aside>
  );
}