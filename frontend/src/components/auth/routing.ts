import type { Role } from '../../lib/types';

/** Where each role lands after sign-in ("/" redirects here). */
export function homeFor(role: Role | string): string | null {
  if (role === 'client') return '/dashboard';
  if (role === 'advisor') return '/advisor';
  if (role === 'owner') return '/owner';
  return null;
}

/**
 * The page a signed-out visitor originally asked for (react-router `location.state.from`), if it is a safe
 * in-app path. Never returns an external URL or the sign-in page itself.
 */
export function returnPathFrom(state: unknown): string | null {
  const from = (state as { from?: { pathname?: unknown; search?: unknown; hash?: unknown } } | null)?.from;
  if (!from || typeof from.pathname !== 'string') return null;
  const { pathname } = from;
  if (!pathname.startsWith('/') || pathname.startsWith('//') || pathname === '/sign-in') return null;
  const search = typeof from.search === 'string' ? from.search : '';
  const hash = typeof from.hash === 'string' ? from.hash : '';
  return `${pathname}${search}${hash}`;
}
