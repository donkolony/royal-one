import React from 'react';
import { Badge } from './Badge';

export type ClaimStatus = 'submitted' | 'assessment' | 'authorised' | 'declined' | 'paid' | 'closed';

interface StatusPillProps {
  status: ClaimStatus;
  label?: string;
}

export function StatusPill({ status, label }: StatusPillProps) {
  const mapping: Record<ClaimStatus, { variant: any; defaultLabel: string }> = {
    submitted: { variant: 'info', defaultLabel: 'Submitted' },
    assessment: { variant: 'warning', defaultLabel: 'In Assessment' },
    authorised: { variant: 'success', defaultLabel: 'Authorised' },
    declined: { variant: 'danger', defaultLabel: 'Declined' },
    paid: { variant: 'success', defaultLabel: 'Paid' },
    closed: { variant: 'default', defaultLabel: 'Closed' },
  };

  const config = mapping[status] || { variant: 'default', defaultLabel: status };

  return <Badge variant={config.variant}>{label || config.defaultLabel}</Badge>;
}
