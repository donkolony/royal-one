import React from 'react';

interface SkeletonProps {
  className?: string;
  lines?: number;
  variant?: 'text' | 'circle' | 'rect';
}

/** True when the caller already sized that axis (e.g. "h-20", "w-3/4"), so our default must not fight it. */
const hasClass = (className: string, prefix: 'h' | 'w') => new RegExp(`(^|\\s)${prefix}-`).test(className);

export function Skeleton({ className = '', lines = 1, variant = 'text' }: SkeletonProps) {
  const base = 'animate-pulse bg-charcoal-200 dark:bg-charcoal-700';

  if (variant === 'circle') {
    return <div aria-hidden="true" className={`rounded-full ${base} ${className}`} />;
  }

  if (variant === 'rect') {
    return <div aria-hidden="true" className={`rounded ${base} ${className}`} />;
  }

  const height = hasClass(className, 'h') ? '' : 'h-4';
  const width = hasClass(className, 'w') ? '' : 'w-full';

  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`${height} rounded ${base} ${className} ${i === lines - 1 && lines > 1 ? 'w-2/3' : width}`}
        />
      ))}
    </div>
  );
}
