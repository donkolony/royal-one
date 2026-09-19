import React from 'react';
import { PageTitle, Button } from '../components/ui';
import { Copy } from 'lucide-react';

interface ServerErrorProps {
  requestId?: string;
}

export function ServerError({ requestId }: ServerErrorProps) {
  const handleCopy = () => {
    if (requestId) navigator.clipboard.writeText(requestId);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4 text-center">
      <PageTitle title="Server Error" />
      <h1 className="text-4xl font-bold text-charcoal-900 dark:text-white mb-4">Oops! Something went wrong</h1>
      <p className="text-charcoal-600 dark:text-charcoal-400 mb-6 max-w-md">
        We encountered an unexpected error on our end. Please try again later.
      </p>
      
      {requestId && (
        <div className="flex items-center gap-2 bg-charcoal-100 dark:bg-charcoal-800 px-4 py-2 rounded mb-8 text-sm">
          <span className="font-mono text-charcoal-700 dark:text-charcoal-300">Request ID: {requestId}</span>
          <button onClick={handleCopy} className="text-brand-600 hover:text-brand-700 focus:outline-none" aria-label="Copy request ID">
            <Copy className="w-4 h-4" />
          </button>
        </div>
      )}

      <Button onClick={() => window.location.reload()} variant="primary">
        Refresh Page
      </Button>
    </div>
  );
}

export default ServerError
