// components/controls.tsx
"use client";

import { ChangeEvent } from "react";

// ── Text Input ────────────────────────────────────────
export function Input({
  label, value, onChange, placeholder = "", className = "",
}: {
  label:       string;
  value:       string;
  onChange:    (v: string) => void;
  placeholder?: string;
  className?:  string;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className="text-[11px] uppercase tracking-wider text-[#9CA3AF] font-medium">
        {label}
      </label>
      <input
        className="bg-[#2A2A2A] text-white border border-[#444] rounded-[8px]
                   px-3 py-2 text-sm w-full outline-none focus:border-[#666]
                   transition-colors"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

// ── Select ────────────────────────────────────────────
export function Select<T extends string>({
  label, value, options, onChange, className = "",
}: {
  label:     string;
  value:     T;
  options:   { label: string; value: T }[];
  onChange:  (v: T) => void;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className="text-[11px] uppercase tracking-wider text-[#9CA3AF] font-medium">
        {label}
      </label>
      <select
        className="bg-[#2A2A2A] text-white border border-[#444] rounded-[8px]
                   px-3 py-2 text-sm w-full outline-none focus:border-[#666]
                   transition-colors cursor-pointer"
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// ── Slider ────────────────────────────────────────────
export function Slider({
  label, value, min, max, step = 1, onChange, format, className = "",
}: {
  label:     string;
  value:     number;
  min:       number;
  max:       number;
  step?:     number;
  onChange:  (v: number) => void;
  format?:   (v: number) => string;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className="flex justify-between items-center">
        <label className="text-[11px] uppercase tracking-wider text-[#9CA3AF] font-medium">
          {label}
        </label>
        <span className="text-xs text-white font-semibold">
          {format ? format(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-white h-1 cursor-pointer"
      />
    </div>
  );
}

// ── Date Input ────────────────────────────────────────
export function DateInput({
  label, value, onChange, className = "",
}: {
  label:     string;
  value:     string;
  onChange:  (v: string) => void;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className="text-[11px] uppercase tracking-wider text-[#9CA3AF] font-medium">
        {label}
      </label>
      <input
        type="date"
        className="bg-[#2A2A2A] text-white border border-[#444] rounded-[8px]
                   px-3 py-2 text-sm w-full outline-none focus:border-[#666]
                   [color-scheme:dark] transition-colors"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

// ── Section Divider ───────────────────────────────────
export function SidebarSection({ title }: { title: string }) {
  return (
    <div className="border-t border-[#333] pt-4 mt-4">
      <div className="text-[11px] uppercase tracking-wider text-[#6B7280] font-semibold mb-3">
        {title}
      </div>
    </div>
  );
}

// ── Run Button ────────────────────────────────────────
export function RunButton({
  onClick, loading, label = "▶  Run",
}: {
  onClick:  () => void;
  loading:  boolean;
  label?:   string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full bg-white text-[#1A1A1A] font-semibold text-sm
                 py-2.5 rounded-[10px] mt-2 transition-all
                 hover:bg-gray-100 disabled:opacity-50
                 disabled:cursor-not-allowed"
    >
      {loading ? "Running..." : label}
    </button>
  );
}