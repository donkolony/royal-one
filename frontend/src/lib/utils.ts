import { format, parseISO, formatDistanceToNow } from "date-fns";

/** Combine class names — no external clsx/tailwind-merge dep needed */
export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

/** Alias */
export const clsx = cn;

/**
 * Format ZAR cents as "R 1 234.56"
 * South African format: space as thousands separator, dot as decimal
 */
export function formatZAR(cents: number): string {
  const rands = centsToDec(cents);
  // Use ZA locale then swap commas (thousands) for spaces
  const formatted = rands.toLocaleString("en-ZA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `R ${formatted}`;
}

/** Format ISO date string "YYYY-MM-DD" → "19 Sep 2026" */
export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "";
  try {
    return format(parseISO(isoDate), "dd MMM yyyy");
  } catch {
    return isoDate;
  }
}

/**
 * Format ISO UTC datetime → SAST display
 * API returns UTC (Z). The browser in South Africa will naturally show SAST.
 * We explicitly add +2h offset to ensure SAST regardless of viewer locale.
 */
export function formatDateTime(isoDateTime: string | null | undefined): string {
  if (!isoDateTime) return "";
  try {
    const date = new Date(isoDateTime);
    // Add 2 hours for SAST (UTC+2)
    const sast = new Date(date.getTime() + 2 * 60 * 60 * 1000);
    return format(sast, "dd MMM yyyy, HH:mm");
  } catch {
    return isoDateTime;
  }
}

/** Relative time: "2 hours ago", "3 days ago" */
export function relativeTime(isoDateTime: string | null | undefined): string {
  if (!isoDateTime) return "";
  try {
    return formatDistanceToNow(new Date(isoDateTime), { addSuffix: true });
  } catch {
    return "";
  }
}

/** Cents to decimal */
export function centsToDec(cents: number): number {
  return cents / 100;
}

/** Truncate string */
export function truncate(
  str: string | null | undefined,
  maxLen: number,
): string {
  if (!str) return "";
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}
