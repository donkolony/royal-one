import { useQuery } from "@tanstack/react-query";
import { get } from "./api";
import { FALLBACK_CLAIM_STATUSES, claimStatusLabel } from "./enums";
import { humanize } from "./utils";
import type { ClaimStatus, ClaimStatusMeta, Meta, Role } from "./types";

export const META_QUERY_KEY = ["meta"] as const;

/**
 * GET /meta: every enumeration and its labels (claim statuses per role, reminder types, request types,
 * categories, attachment limits). It needs no login and never changes during a session, so it is fetched once.
 * `data` is undefined until it loads; use claimStatusesFor() / reminderTypeLabel() which fall back gracefully.
 */
export function useMeta(options?: { enabled?: boolean }) {
  return useQuery<Meta>({
    queryKey: META_QUERY_KEY,
    queryFn: () => get<Meta>("/meta"),
    staleTime: Infinity,
    gcTime: Infinity,
    enabled: options?.enabled ?? true,
  });
}

/** Ordered claim statuses (draft only when asked for), from /meta when loaded, else the built-in fallback. */
export function claimStatusesFor(meta: Meta | undefined, includeDraft = false): ClaimStatusMeta[] {
  const list = meta?.claim_statuses?.length ? meta.claim_statuses : FALLBACK_CLAIM_STATUSES;
  return [...list].sort((a, b) => a.order - b.order).filter((s) => includeDraft || s.value !== "draft");
}

/** Role-appropriate label of a claim status (client_label for clients, advisor_label for advisers). */
export function claimStatusText(meta: Meta | undefined, status: ClaimStatus | string, role: Role): string {
  return claimStatusLabel(status, role, meta?.claim_statuses?.length ? meta.claim_statuses : FALLBACK_CLAIM_STATUSES);
}

/** Label of a reminder type from /meta. Unknown types (the list keeps growing) fall back to a humanised value. */
export function reminderTypeLabel(meta: Meta | undefined, type: string): string {
  return meta?.reminder_types.find((t) => t.type === type)?.label ?? humanize(type);
}

/** Label of a request type from /meta (a ClientRequest already carries `type_label`). */
export function requestTypeLabel(meta: Meta | undefined, type: string): string {
  return meta?.request_types.find((t) => t.type === type)?.label ?? humanize(type);
}
