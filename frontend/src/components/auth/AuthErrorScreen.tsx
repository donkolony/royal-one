import React, { useState } from 'react';
import { Copy, LogOut, RefreshCw } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button, Card, PageTitle } from '../ui';
import { describeError, isApiError } from '../../lib/errors';
import { homeFor } from './routing';

/**
 * Shown when someone is signed in but we cannot load their profile (GET /me failed) or their account type is
 * not supported. It is a screen, not a redirect, so "/" and "/sign-in" can never bounce between each other.
 * It always offers "Try again" and "Sign out".
 */
export function AuthErrorScreen() {
  const { session, profile, profileError, refreshProfile, signOut } = useAuth();
  const [copied, setCopied] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const info = describeError(profileError);
  const unsupportedRole = Boolean(profile) && homeFor(profile?.role ?? '') === null;
  const status = isApiError(profileError) ? profileError.status : null;

  let title = 'We could not load your account';
  let message = info.message;
  if (unsupportedRole) {
    title = 'This account cannot use this app';
    message = 'Your account type is not supported here. Please contact your adviser.';
  } else if (status === 403) {
    title = 'Your account is not set up yet';
    message = 'You are signed in, but your account has not been set up for Royal Square yet. Please contact your adviser, then try again.';
  } else if (status === 0) {
    title = 'We cannot reach Royal Square';
    message = 'Check your internet connection, then try again.';
  } else if (status !== null && status >= 500) {
    title = 'Royal Square is having trouble';
    message = 'Something went wrong on our side. Please try again in a moment.';
  }

  const email = session?.user?.email;

  const copyDetails = () => {
    const lines = [title, `Code: ${info.code ?? 'unknown'}`];
    if (info.requestId) lines.push(`Request ID: ${info.requestId}`);
    navigator.clipboard
      ?.writeText(lines.join('\n'))
      .then(() => setCopied(true))
      .catch(() => {});
  };

  const handleSignOut = async () => {
    setSigningOut(true);
    try {
      await signOut();
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4">
      <PageTitle title="Account problem" />
      <Card padding="lg" className="w-full max-w-md text-center">
        <img src="/rs-logo.png" alt="Royal Square Financial" className="h-12 w-auto object-contain mx-auto mb-6" />
        <div role="alert">
          <h1 className="text-xl font-semibold text-charcoal-900 dark:text-white">{title}</h1>
          <p className="mt-2 text-sm text-charcoal-600 dark:text-charcoal-300">{message}</p>
          {email && (
            <p className="mt-2 text-xs text-charcoal-500 dark:text-charcoal-400">
              Signed in as <span className="font-medium">{email}</span>
            </p>
          )}
        </div>

        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {!unsupportedRole && (
            <Button onClick={refreshProfile}>
              <RefreshCw className="w-4 h-4 mr-2" aria-hidden="true" />
              Try again
            </Button>
          )}
          <Button variant="secondary" onClick={handleSignOut} loading={signingOut}>
            <LogOut className="w-4 h-4 mr-2" aria-hidden="true" />
            Sign out
          </Button>
        </div>

        {info.requestId && (
          <button
            type="button"
            onClick={copyDetails}
            className="mt-6 inline-flex items-center gap-1.5 text-xs text-charcoal-500 dark:text-charcoal-400 hover:underline"
          >
            <Copy className="w-3.5 h-3.5" aria-hidden="true" />
            {copied ? 'Copied' : `Copy error details (${info.requestId.slice(0, 8)})`}
          </button>
        )}
      </Card>
    </div>
  );
}
