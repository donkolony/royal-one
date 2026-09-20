import React from 'react';
import { Check } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { claimStatusesFor, useMeta } from '../../lib/meta';
import type { ClaimStatus, Role } from '../../lib/types';

interface Step {
  id: string;
  label: string;
}

interface ClaimStatusStepperProps {
  /** claim.status */
  currentStatus: ClaimStatus | string;
  /**
   * Steps to draw. Leave it out to use the API's ordered claim statuses (GET /meta), labelled for the viewer:
   * client_label for clients, advisor_label for advisers. `draft` is only a step while the claim is a draft.
   */
  statuses?: Step[];
  /** Whose wording to use when `statuses` is not given. Defaults to the signed-in user's role. */
  role?: Role;
}

function Node({ index, state }: { index: number; state: 'done' | 'active' | 'todo' }) {
  const colour =
    state === 'active'
      ? 'bg-brand-500 text-white dark:bg-brand-400 dark:text-charcoal-900'
      : state === 'done'
        ? 'bg-green-500 text-white'
        : 'bg-charcoal-200 dark:bg-charcoal-700 text-charcoal-500 dark:text-charcoal-300';
  return (
    <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 shrink-0 transition-colors ${colour}`}>
      {state === 'done' ? <Check className="w-4 h-4" aria-hidden="true" /> : <span className="text-sm">{index + 1}</span>}
    </div>
  );
}

export function ClaimStatusStepper({ currentStatus, statuses, role }: ClaimStatusStepperProps) {
  const { profile } = useAuth();
  const { data: meta } = useMeta({ enabled: !statuses });
  const viewer: Role = role ?? profile?.role ?? 'client';

  const steps: Step[] =
    statuses ??
    claimStatusesFor(meta, currentStatus === 'draft').map((s) => ({
      id: s.value,
      label: viewer === 'advisor' ? s.advisor_label : s.client_label,
    }));

  const currentIndex = steps.findIndex((s) => s.id === currentStatus);
  const stateOf = (index: number) => (index < currentIndex ? 'done' : index === currentIndex ? 'active' : 'todo');
  const labelClass = (index: number) =>
    `text-sm font-medium ${index === currentIndex ? 'text-brand-600 dark:text-brand-300' : 'text-charcoal-500 dark:text-charcoal-400'}`;

  return (
    <div className="w-full">
      {/* Desktop: horizontal. `isolate` keeps the connector lines (z -10) inside this block, above the card background. */}
      <ol className="hidden md:flex items-start justify-between isolate" aria-label="Claim progress">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className="flex flex-col items-center text-center relative flex-1 px-1"
            aria-current={index === currentIndex ? 'step' : undefined}
          >
            <Node index={index} state={stateOf(index)} />
            <p className={`mt-2 ${labelClass(index)}`}>{step.label}</p>
            {index < steps.length - 1 && (
              <div
                className={`absolute top-4 left-1/2 w-full h-0.5 -z-10 ${
                  index < currentIndex ? 'bg-green-500' : 'bg-charcoal-200 dark:bg-charcoal-700'
                }`}
              />
            )}
          </li>
        ))}
      </ol>

      {/* Mobile: vertical */}
      <ol className="flex md:hidden flex-col isolate" aria-label="Claim progress">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className="relative flex items-start gap-4 pb-6 last:pb-0"
            aria-current={index === currentIndex ? 'step' : undefined}
          >
            <Node index={index} state={stateOf(index)} />
            <p className={`min-h-8 flex items-center ${labelClass(index)}`}>{step.label}</p>
            {index < steps.length - 1 && (
              <div
                className={`absolute left-4 top-8 bottom-0 w-0.5 -translate-x-1/2 -z-10 ${
                  index < currentIndex ? 'bg-green-500' : 'bg-charcoal-200 dark:bg-charcoal-700'
                }`}
              />
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
