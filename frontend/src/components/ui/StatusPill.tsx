import React from 'react';
import { Badge } from './Badge';
import { useAuth } from '../../context/AuthContext';
import { claimStatusText, useMeta } from '../../lib/meta';
import { humanize } from '../../lib/utils';
import type { Role } from '../../lib/types';

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info';

/**
 * Colour for every status-like enum the API returns: claim statuses, request statuses, reminder status and
 * urgency. Unknown values render neutral, so a new API value never breaks the page.
 */
const VARIANTS: Record<string, Variant> = {
  // claim status
  draft: 'default',
  submitted: 'info',
  registered: 'info',
  assessment: 'warning',
  quotes: 'warning',
  authorised: 'success',
  in_repair: 'warning',
  completed: 'success',
  closed: 'default',
  // request status (submitted / completed above)
  in_progress: 'warning',
  declined: 'danger',
  // reminder status and urgency
  pending: 'warning',
  done: 'success',
  dismissed: 'default',
  overdue: 'danger',
  due_soon: 'warning',
  upcoming: 'info',
};

const CLAIM_STATUSES = new Set(['draft', 'submitted', 'registered', 'assessment', 'quotes', 'authorised', 'in_repair', 'completed', 'closed']);

interface StatusPillProps {
  /** The raw API value, e.g. claim.status, request.status, reminder.urgency. */
  status: string;
  /** Text to show. Pass the API's label (claim.status_label) whenever you have it: it is already role-appropriate. */
  label?: string;
  /** Wording for claim statuses when no label is passed. Defaults to the signed-in user's role. */
  role?: Role;
}

export function StatusPill({ status, label, role }: StatusPillProps) {
  const { profile } = useAuth();
  const isClaimStatus = CLAIM_STATUSES.has(status);
  // Only needed when no label was passed for a claim status; /meta is fetched once and cached.
  const { data: meta } = useMeta({ enabled: !label && isClaimStatus });

  const text = label ?? (isClaimStatus ? claimStatusText(meta, status, role ?? profile?.role ?? 'client') : humanize(status));
  return <Badge variant={VARIANTS[status] ?? 'default'}>{text}</Badge>;
}
