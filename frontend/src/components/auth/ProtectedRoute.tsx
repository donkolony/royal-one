import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { PageLoader } from '../ui';
import type { Role } from '../../lib/types';
import { AuthErrorScreen } from './AuthErrorScreen';
import { homeFor } from './routing';

/**
 * Route guard. Use as a layout route: `<Route element={<ProtectedRoute role="client" />}>...children...</Route>`.
 *  - still resolving the session / profile  -> spinner (never redirect while loading)
 *  - signed out                             -> /sign-in, remembering where the visitor was going
 *  - signed in but no profile (GET /me failed) -> error screen with "Try again" / "Sign out" (NOT a redirect)
 *  - signed in with the wrong role          -> the not-found page (this section is outside their account's scope,
 *    same as a 403/404 from the API per docs/DESIGN.md §6 "Forbidden or missing -> a neutral 'not found' page")
 */
export function ProtectedRoute({ role }: { role: Role }) {
  const { session, profile, loading } = useAuth();
  const location = useLocation();

  if (loading) return <PageLoader />;
  if (!session) return <Navigate to="/sign-in" replace state={{ from: location }} />;
  if (!profile || homeFor(profile.role) === null) return <AuthErrorScreen />;
  if (profile.role !== role) return <Navigate to="/not-found" replace />;
  return <Outlet />;
}
