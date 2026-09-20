import React, { useEffect, useRef, useState } from "react";
import { Button } from "./Button";
import { describeError } from "../../lib/errors";

export interface ErrorBannerProps {
  /** Anything thrown: an ApiError (from lib/api), an Error, a string, a stored { error: {...} } body. */
  error: unknown;
  onRetry?: () => void;
  className?: string;
  /** Override the heading (defaults to one derived from the error, e.g. "Access denied"). */
  title?: string;
}

/**
 * Shows an error without ever printing "[object Object]". For an ApiError it shows the API's message (4xx)
 * or a generic one (5xx), the field-level problems of a validation error, a "try again in N seconds" hint
 * for rate limits / LLM outages, and the request id with a copy button.
 */
export function ErrorBanner({ error, onRetry, className = "", title }: ErrorBannerProps) {
  const info = describeError(error);
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  const handleCopy = () => {
    const lines = [`Error: ${info.message}`];
    if (info.code) lines.push(`Code: ${info.code}`);
    if (info.requestId) lines.push(`Request ID: ${info.requestId}`);
    navigator.clipboard
      ?.writeText(lines.join("\n"))
      .then(() => {
        setCopied(true);
        clearTimeout(timer.current);
        timer.current = setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {});
  };

  return (
    <div
      role="alert"
      className={`bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded shadow-sm ${className}`}
    >
      <div className="flex flex-wrap justify-between items-start gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-red-800 dark:text-red-200 font-medium">{title ?? info.title}</h3>
          <p className="text-red-700 dark:text-red-300 text-sm mt-1 break-words">{info.message}</p>
          {info.details.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm text-red-700 dark:text-red-300 space-y-0.5">
              {info.details.map((d, i) => (
                <li key={`${d.field}-${i}`} className="break-words">
                  {d.field ? <span className="font-mono text-xs">{d.field}: </span> : null}
                  {d.message}
                </li>
              ))}
            </ul>
          )}
        </div>
        {onRetry && (
          <Button variant="danger" size="sm" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
      {info.requestId && (
        <div className="mt-3 flex items-center justify-between gap-3 text-xs text-red-600 dark:text-red-400 bg-white/50 dark:bg-black/20 p-2 rounded">
          <span className="font-mono break-all">Request ID: {info.requestId}</span>
          <button type="button" onClick={handleCopy} className="shrink-0 hover:underline focus:outline-none focus:underline">
            {copied ? "Copied" : "Copy details"}
          </button>
        </div>
      )}
    </div>
  );
}
