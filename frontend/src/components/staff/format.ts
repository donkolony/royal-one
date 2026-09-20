import { formatDate, formatRand0, humanize } from "../../lib/utils";

/** Evidence is the actual numbers and fields behind an opportunity. Show each as a labelled fact, formatted by its name. */
const HIDDEN = new Set(["goal_id", "policy_id", "event_id", "reason"]);

export function evidenceFacts(evidence: Record<string, unknown>): { label: string; value: string }[] {
  const out: { label: string; value: string }[] = [];
  for (const [key, raw] of Object.entries(evidence)) {
    if (HIDDEN.has(key) || raw === null || raw === undefined || typeof raw === "object") continue;
    const label = humanize(key.replace(/_cents$/, "").replace(/_percent$/, " %"));
    let value: string;
    if (key.endsWith("_cents") && typeof raw === "number") value = formatRand0(raw);
    else if (key.endsWith("_percent") && typeof raw === "number") value = `${raw}%`;
    else if (/(date|occurred_on|since)$/.test(key) && typeof raw === "string") value = formatDate(raw);
    else value = typeof raw === "string" ? humanize(raw) : String(raw);
    out.push({ label, value });
  }
  return out;
}

export const SIGNAL_TONE: Record<string, string> = {
  under_insured_life: "bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-200",
  goal_behind: "bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200",
  life_event: "bg-blue-50 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200",
  missing_cover: "bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200",
  single_product: "bg-charcoal-100 text-charcoal-700 dark:bg-charcoal-700 dark:text-charcoal-200",
  lapsed_cover: "bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-200",
  expiring_document: "bg-green-50 text-green-800 dark:bg-green-900/30 dark:text-green-200",
};
