import React from 'react';

interface SkeletonProps {
  className?: string;
  lines?: number;
  variant?: 'text' | 'circle' | 'rect';
}

export function Skeleton({ className = '', lines = 1, variant = 'text' }: SkeletonProps) {
  const base = 'animate-pulse bg-charcoal-200 dark:bg-charcoal-700';

  if (variant === 'circle') {
    return <div className={`rounded-full ${base} ${className}`} />;
  }

  if (variant === 'rect') {
    return <div className={`rounded ${base} ${className}`} />;
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`h-4 rounded ${base} ${className} ${i === lines - 1 && lines > 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  );
}
