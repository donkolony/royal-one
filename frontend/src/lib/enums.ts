import type { ClaimStatus, ClaimStatusMeta, Role } from "./types";
import { humanize } from "./utils";

/**
 * Claim statuses with their role-appropriate wording, mirrored from docs/api.md 3.1.
 * The API is the source of truth (GET /meta -> claim_statuses, see lib/meta.ts useMeta()); this table is
 * only the first-paint fallback used before /meta has loaded or if it fails.
 */
export const FALLBACK_CLAIM_STATUSES: ClaimStatusMeta[] = [
  { value: "draft", order: 0, client_label: "Not sent yet", advisor_label: "Draft (not visible)" },
  { value: "submitted", order: 1, client_label: "Sent to Royal Square", advisor_label: "Submitted" },
  { value: "registered", order: 2, client_label: "Registered with your insurer", advisor_label: "Registered (claim no. issued)" },
  { value: "assessment", order: 3, client_label: "Vehicle assessment", advisor_label: "Assessment" },
  { value: "quotes", order: 4, client_label: "Repair quotes", advisor_label: "Quotes with insurer" },
  { value: "authorised", order: 5, client_label: "Repairs approved", advisor_label: "Authorised" },
  { value: "in_repair", order: 6, client_label: "Being repaired", advisor_label: "In repair" },
  { value: "completed", order: 7, client_label: "Repairs finished", advisor_label: "Completed, awaiting client sign-off" },
  { value: "closed", order: 8, client_label: "Closed", advisor_label: "Closed" },
];

/** Label for a claim status in the wording for `role`. Unknown statuses fall back to a humanised value. */
export function claimStatusLabel(
  status: ClaimStatus | string,
  role: Role,
  statuses: ClaimStatusMeta[] = FALLBACK_CLAIM_STATUSES,
): string {
  const found = statuses.find((s) => s.value === status);
  if (!found) return humanize(status);
  return role === "advisor" ? found.advisor_label : found.client_label;
}
