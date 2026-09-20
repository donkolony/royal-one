import React from 'react';
import { Card } from './Card';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';
import { formatDate, formatZAR, humanize } from '../../lib/utils';
import type { Goal } from '../../lib/types';

/** Shows the API's Goal object as-is: amounts are integer cents, progress_percent is 0-100. */
export function GoalCard({ goal }: { goal: Goal }) {
  const shared = goal.participants.length > 1;

  return (
    <Card>
      <div className="flex justify-between items-start gap-3 mb-4">
        <h3 className="font-semibold text-charcoal-900 dark:text-white">{goal.title}</h3>
        <Badge variant="info">{humanize(goal.category)}</Badge>
      </div>
      {goal.description && <p className="text-sm text-charcoal-500 dark:text-charcoal-400 mb-4">{goal.description}</p>}

      <div className="mb-4">
        <ProgressBar
          percent={goal.progress_percent}
          label="Progress"
          showPercent
          colour={goal.status === 'achieved' || goal.progress_percent >= 100 ? 'success' : 'brand'}
        />
      </div>

      <div className="flex justify-between text-sm">
        <div>
          <p className="text-charcoal-500 dark:text-charcoal-400">Saved so far</p>
          <p className="font-medium text-charcoal-900 dark:text-white">{formatZAR(goal.current_amount_cents)}</p>
        </div>
        <div className="text-right">
          <p className="text-charcoal-500 dark:text-charcoal-400">Target</p>
          <p className="font-medium text-charcoal-900 dark:text-white">{formatZAR(goal.target_amount_cents)}</p>
        </div>
      </div>

      {(goal.target_date || shared) && (
        <p className="text-xs text-charcoal-400 dark:text-charcoal-500 mt-4 text-center bg-charcoal-50 dark:bg-charcoal-700/50 py-1 rounded">
          {goal.target_date ? `Target date: ${formatDate(goal.target_date)}` : null}
          {goal.target_date && shared ? ' · ' : null}
          {shared ? `Shared by ${goal.participants.length} people` : null}
        </p>
      )}
    </Card>
  );
}
