// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core palette from TradeSmart Pro design system
        background:   "#F0F2F5",
        card:         "#FFFFFF",
        sidebar:      "#1A1A1A",
        "text-primary":   "#1A1A1A",
        "text-secondary": "#6B7280",
        border:       "#E5E7EB",
        success:      "#10B981",
        danger:       "#EF4444",
        warning:      "#F59E0B",
        info:         "#3B82F6",
        "success-bg": "#D1FAE5",
        "success-fg": "#065F46",
        "danger-bg":  "#FEE2E2",
        "danger-fg":  "#991B1B",
        "warning-bg": "#FEF3C7",
        "warning-fg": "#92400E",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};

export default config;