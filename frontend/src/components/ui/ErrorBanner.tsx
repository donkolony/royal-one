import React from "react";
import { Button } from "./Button";

export interface ErrorBannerProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

export function ErrorBanner({
  error,
  onRetry,
  className = "",
}: ErrorBannerProps) {
  const message =
    (error as any)?.message ||
    (typeof error === "string" ? error : "An unexpected error occurred.");
  const requestId = (error as any)?.requestId ?? (error as any)?.request_id;

  const handleCopy = () => {
    if (requestId) {
      navigator.clipboard.writeText(
        `Error: ${message}\nRequest ID: ${requestId}`,
      );
    }
  };

  return (
    <div
      className={`bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded shadow-sm ${className}`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="text-red-800 dark:text-red-200 font-medium">Error</h3>
          <p className="text-red-700 dark:text-red-300 text-sm mt-1">
            {message}
          </p>
        </div>
        {onRetry && (
          <Button variant="danger" size="sm" onClick={onRetry} className="ml-4">
            Retry
          </Button>
        )}
      </div>
      {requestId && (
        <div className="mt-3 flex items-center justify-between text-xs text-red-600 dark:text-red-400 bg-white/50 dark:bg-black/20 p-2 rounded">
          <span className="font-mono">Req ID: {requestId}</span>
          <button
            onClick={handleCopy}
            className="hover:underline focus:outline-none"
          >
            Copy details
          </button>
        </div>
      )}
    </div>
  );
}
