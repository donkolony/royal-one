import React from "react";
import type { IdentityState } from "../../lib/typesExt";

const STYLE: Record<IdentityState, [string, string]> = {
  valid: ["Verified", "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200"],
  expiring: ["Expiring soon", "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"],
  expired: ["Expired", "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200"],
  pending: ["Waiting for verification", "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200"],
  stale: ["Out of date", "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"],
  missing: ["Not on file", "bg-charcoal-100 text-charcoal-700 dark:bg-charcoal-700 dark:text-charcoal-200"],
};

export function IdentityStateChip({ state }: { state: IdentityState }) {
  const [label, cls] = STYLE[state];
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{label}</span>;
}
