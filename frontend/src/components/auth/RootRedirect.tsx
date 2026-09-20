import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { PageLoader } from '../ui';
import { AuthErrorScreen } from './AuthErrorScreen';
import { homeFor } from './routing';

/** "/": signed out -> /sign-in, client -> /dashboard, advisor -> /advisor, profile failed -> error screen. */
export function RootRedirect() {
  const { session, profile, loading } = useAuth();

  if (loading) return <PageLoader />;
  if (!session) return <Navigate to="/sign-in" replace />;
  const home = profile ? homeFor(profile.role) : null;
  if (!home) return <AuthErrorScreen />;
  return <Navigate to={home} replace />;
}
