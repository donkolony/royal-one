import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Spinner } from '../ui';

// Mocked Auth Context for layout logic
const useAuth = () => {
  return { session: true, loading: false, role: 'client' }; // Mock for now
};

export function ProtectedRoute({ allowedRole }: { allowedRole?: string }) {
  const { session, loading, role } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-charcoal-50 dark:bg-charcoal-900">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/sign-in" replace />;
  }

  if (allowedRole && role !== allowedRole) {
    return <Navigate to="/not-found" replace />;
  }

  return <Outlet />;
}
