import React, { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

interface StatTileProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "default" | "danger" | "success" | "brand";
  /** Where the number drills down to. The whole tile becomes a link. */
  to?: string;
  children?: ReactNode;
}

const TONES = {
  default: "text-charcoal-900 dark:text-white",
  danger: "text-accent-600 dark:text-accent-300",
  success: "text-success",
  brand: "text-brand-600 dark:text-brand-300",
};

export function StatTile({ label, value, sub, tone = "default", to, children }: StatTileProps) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-charcoal-500 dark:text-charcoal-400">{label}</p>
        {to && <ChevronRight className="w-4 h-4 text-charcoal-400 shrink-0 mt-0.5" aria-hidden="true" />}
      </div>
      <p className={`mt-1 text-3xl font-bold tabular-nums ${TONES[tone]}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-charcoal-500 dark:text-charcoal-400">{sub}</p>}
      {children}
    </>
  );
  const cls = "block rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 p-4 shadow-sm";
  return to ? (
    <Link to={to} className={`${cls} hover:border-brand-400 transition-colors`}>{body}</Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

/** A labelled horizontal bar made from real numbers (no decoration). */
export function Bar({ label, value, max, right, tone = "brand" }: { label: string; value: number; max: number; right?: ReactNode; tone?: "brand" | "danger" | "success" }) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  const colour = tone === "danger" ? "bg-accent-500" : tone === "success" ? "bg-success" : "bg-brand-500";
  return (
    <div>
      <div className="flex justify-between gap-3 text-xs text-charcoal-600 dark:text-charcoal-300">
        <span className="truncate">{label}</span>
        <span className="tabular-nums shrink-0">{right ?? value}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-charcoal-100 dark:bg-charcoal-700 overflow-hidden" role="presentation">
        <div className={`h-full rounded-full ${colour}`} style={{ width: `${value > 0 ? pct : 0}%` }} />
      </div>
    </div>
  );
}
