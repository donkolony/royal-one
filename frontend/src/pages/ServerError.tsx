import React, { useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { PageTitle, Button, buttonClasses } from '../components/ui';
import { Copy } from 'lucide-react';

interface ServerErrorProps {
  /** The server request id to show. Falls back to `?request_id=` in the URL or `location.state.requestId`. */
  requestId?: string;
}

export function ServerError({ requestId }: ServerErrorProps) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const [copied, setCopied] = useState(false);

  const stateId = (location.state as { requestId?: unknown } | null)?.requestId;
  const id = requestId ?? searchParams.get('request_id') ?? (typeof stateId === 'string' ? stateId : undefined);

  const handleCopy = () => {
    if (!id) return;
    navigator.clipboard
      ?.writeText(id)
      .then(() => setCopied(true))
      .catch(() => {});
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4 text-center">
      <PageTitle title="Server error" />
      <h1 className="text-4xl font-bold text-charcoal-900 dark:text-white mb-4">Oops! Something went wrong</h1>
      <p className="text-charcoal-600 dark:text-charcoal-400 mb-6 max-w-md">
        We encountered an unexpected error on our end. Please try again in a moment.
      </p>

      {id && (
        <div className="flex items-center gap-2 bg-charcoal-100 dark:bg-charcoal-800 px-4 py-2 rounded mb-8 text-sm max-w-full">
          <span className="font-mono text-charcoal-700 dark:text-charcoal-300 break-all">Request ID: {id}</span>
          <button type="button" onClick={handleCopy} className="text-brand-600 dark:text-brand-300 hover:text-brand-700 focus:outline-none" aria-label={copied ? 'Request ID copied' : 'Copy request ID'}>
            <Copy className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      )}

      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={() => window.location.reload()} variant="primary">
          Try again
        </Button>
        <Link to="/" className={buttonClasses({ variant: 'secondary' })}>
          Go home
        </Link>
      </div>
    </div>
  );
}

export default ServerError
