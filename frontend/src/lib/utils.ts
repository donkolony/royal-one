import { formatDistanceToNow } from "date-fns";
import type { Page } from "./types";

/** Combine class names — no external clsx/tailwind-merge dep needed */
export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

/** Alias */
export const clsx = cn;

// ---------------------------------------------------------------------------
// Money. The API sends integer CENTS in fields ending `_cents` (currency is always ZAR).
// ---------------------------------------------------------------------------

/**
 * Format ZAR cents as "R 1 234,56" (South African style). Pass the `_cents` value straight from the API.
 * null / undefined / NaN (an amount that does not apply) renders as an em dash, never "R NaN".
 */
export function formatZAR(cents: number | null | undefined): string {
  if (cents === null || cents === undefined || !Number.isFinite(cents)) return "—";
  const rands = centsToDec(cents);
  const formatted = Math.abs(rands).toLocaleString("en-ZA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${rands < 0 ? "-" : ""}R ${formatted}`;
}

/** Cents to decimal */
export function centsToDec(cents: number): number {
  return cents / 100;
}

/**
 * Parse what a person typed into a rand amount and return integer CENTS for the API, or null when it is
 * not a valid amount. Accepts "1234", "1 234,50", "1,234.50", "R 1234.5". Never send floats to the API.
 */
export function randsToCents(input: string | number | null | undefined): number | null {
  if (input === null || input === undefined) return null;
  if (typeof input === "number") return Number.isFinite(input) ? Math.round(input * 100) : null;
  const cleaned = input
    .replace(/[R\s]/gi, "") // \s already covers spaces and non-breaking spaces
    .replace(/,(?=\d{1,2}$)/, ".") // "1234,50" -> decimal comma
    .replace(/,/g, ""); // remaining commas are thousands separators
  if (!/^-?\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  return Math.round(parseFloat(cleaned) * 100);
}

// ---------------------------------------------------------------------------
// Dates. Timestamps from the API are UTC ISO strings ending in Z; dates are YYYY-MM-DD (no time zone).
// Everything is displayed in South African time (Africa/Johannesburg, UTC+2) whatever the viewer's locale.
// ---------------------------------------------------------------------------

const SAST = "Africa/Johannesburg";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;
const sastFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: SAST,
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

interface Parts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
}

function sastParts(value: string): Parts | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const parts = sastFormatter.formatToParts(date);
  const pick = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  return { year: pick("year"), month: pick("month"), day: pick("day"), hour: pick("hour"), minute: pick("minute") };
}

const pad = (n: number) => String(n).padStart(2, "0");

/** "2026-09-19" or "2026-09-19T14:30:00Z" -> "19 Sep 2026" (South African date for timestamps). */
export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "";
  const dateOnly = DATE_ONLY.exec(isoDate);
  if (dateOnly) {
    const month = Number(dateOnly[2]);
    if (month < 1 || month > 12) return isoDate;
    return `${pad(Number(dateOnly[3]))} ${MONTHS[month - 1]} ${dateOnly[1]}`;
  }
  const p = sastParts(isoDate);
  return p ? `${pad(p.day)} ${MONTHS[p.month - 1]} ${p.year}` : isoDate;
}

/**
 * "2026-09-19T14:30:00Z" -> "19 Sep 2026, 16:30" (SAST). A date-only value ("2026-09-19") is shown as a
 * plain date with no invented time.
 */
export function formatDateTime(isoDateTime: string | null | undefined): string {
  if (!isoDateTime) return "";
  if (DATE_ONLY.test(isoDateTime)) return formatDate(isoDateTime);
  const p = sastParts(isoDateTime);
  return p ? `${pad(p.day)} ${MONTHS[p.month - 1]} ${p.year}, ${pad(p.hour)}:${pad(p.minute)}` : isoDateTime;
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

// ---------------------------------------------------------------------------
// Text and misc
// ---------------------------------------------------------------------------

/** Truncate string */
export function truncate(
  str: string | null | undefined,
  maxLen: number,
): string {
  if (!str) return "";
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}

/** "in_repair" -> "In repair". Fallback label for an enum value the UI has no wording for. */
export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** 482113 -> "471 KB" */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Items of an API list response. Real list endpoints return a Page<T> ({ items, total, limit, offset });
 * this also tolerates a bare array or an empty result so `.map` can never throw.
 */
export function itemsOf<T>(data: Page<T> | { items: T[] } | T[] | null | undefined): T[] {
  if (Array.isArray(data)) return data;
  return Array.isArray(data?.items) ? data.items : [];
}

/**
 * Turn a dashboard "needs attention" link ({ resource, id }) into an adviser-portal route.
 * The API's `resource` is not a route: "claim" -> /advisor/claims/:id, "email_thread" -> /advisor/email, ...
 */
export function advisorLinkFor(link: { resource: string; id: string }): string {
  switch (link.resource) {
    case "claim":
      return `/advisor/claims/${link.id}`;
    case "client":
      return `/advisor/clients/${link.id}`;
    case "request":
      return "/advisor/requests";
    case "reminder":
      return "/advisor/reminders";
    case "email_thread":
      return "/advisor/email";
    default:
      return "/advisor";
  }
}
