import React from 'react';
import { Spinner } from './Spinner';

interface PageLoaderProps {
  label?: string;
  /** true (default): fills the screen (route guards). false: sits inside a page or layout. */
  fullScreen?: boolean;
}

/** Centered spinner shown while the session, the profile or a lazy page is loading. */
export function PageLoader({ label = 'Loading…', fullScreen = true }: PageLoaderProps) {
  return (
    <div
      role="status"
      className={`flex items-center justify-center text-brand-500 dark:text-brand-300 ${
        fullScreen ? 'min-h-screen bg-charcoal-50 dark:bg-charcoal-900' : 'py-24'
      }`}
    >
      <Spinner size="lg" />
      <span className="sr-only">{label}</span>
    </div>
  );
}
