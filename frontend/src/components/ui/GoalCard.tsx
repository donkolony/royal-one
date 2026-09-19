import React from 'react';
import { Card } from './Card';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';
import { format, parseISO } from 'date-fns';

interface Goal {
  title: string;
  category: string;
  progress_percent: number;
  current_amount: number;
  target_amount: number;
  target_date?: string;
}

export function GoalCard({ goal }: { goal: Goal }) {
  const formatZAR = (cents: number) => {
    return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(cents / 100);
  };

  return (
    <Card>
      <div className="flex justify-between items-start mb-4">
        <h3 className="font-semibold text-charcoal-900 dark:text-white">{goal.title}</h3>
        <Badge variant="info">{goal.category}</Badge>
      </div>
      
      <div className="mb-4">
        <ProgressBar percent={goal.progress_percent} label="Progress" showPercent colour="brand" />
      </div>
      
      <div className="flex justify-between text-sm">
        <div>
          <p className="text-charcoal-500 dark:text-charcoal-400">Current</p>
          <p className="font-medium text-charcoal-900 dark:text-white">{formatZAR(goal.current_amount)}</p>
        </div>
        <div className="text-right">
          <p className="text-charcoal-500 dark:text-charcoal-400">Target</p>
          <p className="font-medium text-charcoal-900 dark:text-white">{formatZAR(goal.target_amount)}</p>
        </div>
      </div>
      
      {goal.target_date && (
        <p className="text-xs text-charcoal-400 dark:text-charcoal-500 mt-4 text-center bg-charcoal-50 dark:bg-charcoal-700/50 py-1 rounded">
          Target Date: {format(parseISO(goal.target_date), 'dd MMM yyyy')}
        </p>
      )}
    </Card>
  );
}
