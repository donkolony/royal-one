import React from 'react';
import { Link } from 'react-router-dom';
import { PageTitle, buttonClasses } from '../components/ui';

export function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4 text-center">
      <PageTitle title="Page not found" />
      <p className="text-8xl font-bold text-brand-500 dark:text-brand-300 mb-4" aria-hidden="true">404</p>
      <h1 className="text-2xl font-semibold text-charcoal-900 dark:text-white mb-2">Page not found</h1>
      <p className="text-charcoal-500 dark:text-charcoal-400 mb-8 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link to="/" className={buttonClasses({ variant: 'primary' })}>
        Return home
      </Link>
    </div>
  );
}

export default NotFound
