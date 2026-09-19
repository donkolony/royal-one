import React, { useState } from 'react';
import { Check } from 'lucide-react';
import { Button } from './Button';
import { StatusPill } from './StatusPill';
import { formatDate } from '../../lib/utils';
import type { Reminder } from '../../lib/types';

interface ReminderRowProps {
  reminder: Reminder;
  /** Called with the reminder id when "Mark done" is pressed. Leave it out for a read-only row. */
  onComplete?: (id: string) => Promise<unknown> | void;
  /** Show the client's name (adviser views). */
  showClient?: boolean;
}

/** One reminder from the API. Urgency comes from the server (reminder.urgency), never recomputed here. */
export function ReminderRow({ reminder, onComplete, showClient = false }: ReminderRowProps) {
  const [loading, setLoading] = useState(false);

  const handleComplete = async () => {
    if (!onComplete) return;
    setLoading(true);
    try {
      await onComplete(reminder.id);
    } finally {
      setLoading(false);
    }
  };

  const pending = reminder.status === 'pending';
  const URGENCY_LABEL = { overdue: 'Overdue', due_soon: 'Due soon', upcoming: 'Upcoming' } as const;
  const pill = pending ? (
    <StatusPill status={reminder.urgency} label={URGENCY_LABEL[reminder.urgency] ?? undefined} />
  ) : (
    <StatusPill status={reminder.status} label={reminder.status === 'done' ? 'Done' : 'Dismissed'} />
  );
  const dateColour =
    pending && reminder.urgency === 'overdue'
      ? 'text-red-600 dark:text-red-400'
      : pending && reminder.urgency === 'due_soon'
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-charcoal-600 dark:text-charcoal-300';

  return (
    <div className="flex items-center justify-between gap-3 p-4 bg-white dark:bg-charcoal-800 border border-charcoal-100 dark:border-charcoal-700 rounded-lg shadow-sm">
      <div className="min-w-0">
        <h4 className="font-medium text-charcoal-900 dark:text-white">{reminder.title}</h4>
        {showClient && <p className="text-sm text-charcoal-500 dark:text-charcoal-400">{reminder.client.full_name}</p>}
        <p className={`text-sm ${dateColour} flex flex-wrap items-center gap-2 mt-1`}>
          {formatDate(reminder.due_date)}
          {pill}
        </p>
      </div>
      {pending && onComplete && (
        <Button variant="ghost" size="sm" onClick={handleComplete} loading={loading} aria-label={`Mark "${reminder.title}" as done`}>
          <Check className="w-5 h-5 text-green-600" aria-hidden="true" />
        </Button>
      )}
    </div>
  );
}
