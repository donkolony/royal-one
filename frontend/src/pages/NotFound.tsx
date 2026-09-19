import React from 'react';
import { Link } from 'react-router-dom';
import { PageTitle, Button } from '../components/ui';

export function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4 text-center">
      <PageTitle title="Page Not Found" />
      <h1 className="text-8xl font-bold text-brand-500 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-charcoal-900 dark:text-white mb-2">Page not found</h2>
      <p className="text-charcoal-500 dark:text-charcoal-400 mb-8 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link to="/">
        <Button variant="primary">Return Home</Button>
      </Link>
    </div>
  );
}

export default NotFound
