import React from 'react';

interface ProgressBarProps {
  /** 0-100 (Goal.progress_percent is already in this range). */
  percent: number;
  label?: string;
  showPercent?: boolean;
  colour?: 'brand' | 'success' | 'warning';
}

export function ProgressBar({ percent, label = 'Progress', showPercent = false, colour = 'brand' }: ProgressBarProps) {
  const clamped = Math.min(Math.max(Number.isFinite(percent) ? percent : 0, 0), 100);
  const colorStyles = {
    brand: 'bg-brand-500 dark:bg-brand-400',
    success: 'bg-green-500',
    warning: 'bg-amber-500',
  };

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-charcoal-700 dark:text-charcoal-300">{label}</span>
        {showPercent && <span className="text-sm text-charcoal-500 dark:text-charcoal-400">{clamped}%</span>}
      </div>
      <div className="w-full bg-charcoal-200 dark:bg-charcoal-700 rounded-full h-2.5" role="progressbar" aria-label={label} aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
        <div className={`h-2.5 rounded-full ${colorStyles[colour]}`} style={{ width: `${clamped}%` }}></div>
      </div>
    </div>
  );
}
