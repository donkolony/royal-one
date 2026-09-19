import React, { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import ClientLayout from "./layouts/ClientLayout";
import AdvisorLayout from "./layouts/AdvisorLayout";

// ── Shared ──────────────────────────────────────────────────────────────────
const SignIn = React.lazy(() => import("./pages/auth/SignIn"));
const NotFound = React.lazy(() => import("./pages/NotFound"));
const ServerError = React.lazy(() => import("./pages/ServerError"));

// ── Client pages ────────────────────────────────────────────────────────────
const ClientDashboard = React.lazy(() => import("./pages/client/Dashboard"));
const ClientPolicies = React.lazy(() => import("./pages/client/Policies"));
const ClientGoals = React.lazy(() => import("./pages/client/Goals"));
const ClientReminders = React.lazy(() => import("./pages/client/Reminders"));
const AccidentChecklist = React.lazy(
  () => import("./pages/client/AccidentChecklist"),
);
const RegisterClaim = React.lazy(() => import("./pages/client/RegisterClaim"));
const ClaimTracking = React.lazy(() => import("./pages/client/ClaimTracking"));
const ClientRequests = React.lazy(() => import("./pages/client/Requests"));
const ClientProfile = React.lazy(() => import("./pages/client/Profile"));

// ── Advisor pages ────────────────────────────────────────────────────────────
const AdvisorDashboard = React.lazy(() => import("./pages/advisor/Dashboard"));
const AdvisorClients = React.lazy(() => import("./pages/advisor/Clients"));
const ClientDetail = React.lazy(() => import("./pages/advisor/ClientDetail"));
const ClaimsPipeline = React.lazy(
  () => import("./pages/advisor/ClaimsPipeline"),
);
const ClaimDetail = React.lazy(() => import("./pages/advisor/ClaimDetail"));
const AdvisorRequests = React.lazy(() => import("./pages/advisor/Requests"));
const AdvisorReminders = React.lazy(() => import("./pages/advisor/Reminders"));
const Assistant = React.lazy(() => import("./pages/advisor/Assistant"));
const Email = React.lazy(() => import("./pages/advisor/Email"));

// ── Loading fallback ─────────────────────────────────────────────────────────
function PageLoader() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-charcoal-200 border-t-brand-500" />
    </div>
  );
}

// ── Route guards ─────────────────────────────────────────────────────────────
function RequireAuth({
  role,
  children,
}: {
  role: "client" | "advisor";
  children: React.ReactNode;
}) {
  const { session, profile, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!session || !profile) return <Navigate to="/sign-in" replace />;
  if (profile.role !== role) return <Navigate to="/not-found" replace />;
  return <>{children}</>;
}

function ClientRoutes() {
  return (
    <RequireAuth role="client">
      <ClientLayout>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route index element={<ClientDashboard />} />
            <Route path="policies" element={<ClientPolicies />} />
            <Route path="goals" element={<ClientGoals />} />
            <Route path="reminders" element={<ClientReminders />} />
            <Route path="claims/report" element={<AccidentChecklist />} />
            <Route path="claims/new" element={<RegisterClaim />} />
            <Route path="claims/:id" element={<ClaimTracking />} />
            <Route path="requests" element={<ClientRequests />} />
            <Route path="profile" element={<ClientProfile />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </ClientLayout>
    </RequireAuth>
  );
}

function AdvisorRoutes() {
  return (
    <RequireAuth role="advisor">
      <AdvisorLayout>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route index element={<AdvisorDashboard />} />
            <Route path="clients" element={<AdvisorClients />} />
            <Route path="clients/:clientId" element={<ClientDetail />} />
            <Route path="claims" element={<ClaimsPipeline />} />
            <Route path="claims/:claimId" element={<ClaimDetail />} />
            <Route path="requests" element={<AdvisorRequests />} />
            <Route path="reminders" element={<AdvisorReminders />} />
            <Route path="assistant" element={<Assistant />} />
            <Route path="email" element={<Email />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </AdvisorLayout>
    </RequireAuth>
  );
}

// ── Root redirect ─────────────────────────────────────────────────────────────
function RootRedirect() {
  const { session, profile, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!session || !profile) return <Navigate to="/sign-in" replace />;
  if (profile.role === "client") return <Navigate to="/dashboard" replace />;
  return <Navigate to="/advisor" replace />; // Fix: redirect to /advisor which matches AdvisorRoutes index
}

// ── App router ────────────────────────────────────────────────────────────────
export function Router() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/sign-in" element={<SignIn />} />
        <Route path="/not-found" element={<NotFound />} />
        <Route path="/error" element={<ServerError />} />

        {/* Client app */}
        <Route path="/dashboard/*" element={<ClientRoutes />} />
        <Route path="/policies/*" element={<ClientRoutes />} />
        <Route path="/goals/*" element={<ClientRoutes />} />
        <Route path="/reminders/*" element={<ClientRoutes />} />
        <Route path="/claims/*" element={<ClientRoutes />} />
        <Route path="/requests/*" element={<ClientRoutes />} />
        <Route path="/profile/*" element={<ClientRoutes />} />

        {/* Advisor portal */}
        <Route path="/advisor/*" element={<AdvisorRoutes />} />

        {/* Root */}
        <Route path="/" element={<RootRedirect />} />

        {/* Catch all */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
