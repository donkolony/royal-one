import React, { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ClientLayout from "./layouts/ClientLayout";
import StaffLayout from "./layouts/StaffLayout";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { RootRedirect } from "./components/auth/RootRedirect";
import { PageLoader, PageTitle } from "./components/ui";

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

// ── Staff pages shared by advisers and the owner (mounted under /advisor and /owner) ──
const Radar = React.lazy(() => import("./pages/staff/Radar"));
const BusinessHealth = React.lazy(() => import("./pages/staff/BusinessHealth"));
const Drilldown = React.lazy(() => import("./pages/staff/Drilldown"));

// Dev-only kitchen sink for the shared UI kit; import.meta.env.DEV is false in production builds.
const UiPreview = import.meta.env.DEV ? React.lazy(() => import("./components/dev/UiPreview")) : null;

/** Sets a sensible browser-tab title for the route; a page's own <PageTitle> (rendered deeper) refines it. */
function Titled({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <>
      <PageTitle title={title} />
      {children}
    </>
  );
}

// ── App router ────────────────────────────────────────────────────────────────
export function Router() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/sign-in" element={<SignIn />} />
        <Route path="/not-found" element={<NotFound />} />
        <Route path="/error" element={<ServerError />} />
        {UiPreview && <Route path="/__ui" element={<UiPreview />} />}

        {/* "/" sends each role to its own home (or shows the account error screen) */}
        <Route path="/" element={<RootRedirect />} />

        {/* Client app: one guard + one layout, pages render in the layout's <Outlet /> */}
        <Route element={<ProtectedRoute role="client" />}>
          <Route element={<ClientLayout />}>
            <Route path="/dashboard" element={<Titled title="Dashboard"><ClientDashboard /></Titled>} />
            <Route path="/policies" element={<Titled title="Policies"><ClientPolicies /></Titled>} />
            <Route path="/goals" element={<Titled title="Goals"><ClientGoals /></Titled>} />
            <Route path="/reminders" element={<Titled title="Reminders"><ClientReminders /></Titled>} />
            {/* There is no claims list page: "Claims" opens the accident checklist, where a claim can be started */}
            <Route path="/claims" element={<Navigate to="/claims/report" replace />} />
            <Route path="/claims/report" element={<Titled title="Report an accident"><AccidentChecklist /></Titled>} />
            <Route path="/claims/new" element={<Titled title="Register a claim"><RegisterClaim /></Titled>} />
            <Route path="/claims/:id" element={<Titled title="Claim"><ClaimTracking /></Titled>} />
            <Route path="/requests" element={<Titled title="Requests"><ClientRequests /></Titled>} />
            <Route path="/profile" element={<Titled title="My profile"><ClientProfile /></Titled>} />
          </Route>
        </Route>

        {/* Owner: the firm's owner sees every client, read-only where an adviser acts */}
        <Route path="/owner" element={<ProtectedRoute role="owner" />}>
          <Route element={<StaffLayout />}>
            <Route index element={<Titled title="Business health"><BusinessHealth /></Titled>} />
            <Route path="drill/:metric" element={<Titled title="Records"><Drilldown /></Titled>} />
            <Route path="radar" element={<Titled title="Opportunities"><Radar /></Titled>} />
            <Route path="clients" element={<Titled title="Clients"><AdvisorClients /></Titled>} />
            <Route path="clients/:clientId" element={<Titled title="Client"><ClientDetail /></Titled>} />
            <Route path="claims" element={<Titled title="Claims pipeline"><ClaimsPipeline /></Titled>} />
            <Route path="claims/:claimId" element={<Titled title="Claim"><ClaimDetail /></Titled>} />
          </Route>
        </Route>

        {/* Adviser portal */}
        <Route path="/advisor" element={<ProtectedRoute role="advisor" />}>
          <Route element={<StaffLayout />}>
            <Route path="radar" element={<Titled title="Opportunities"><Radar /></Titled>} />
            <Route index element={<Titled title="Adviser dashboard"><AdvisorDashboard /></Titled>} />
            <Route path="dashboard" element={<Navigate to="/advisor" replace />} />
            <Route path="clients" element={<Titled title="Clients"><AdvisorClients /></Titled>} />
            <Route path="clients/:clientId" element={<Titled title="Client"><ClientDetail /></Titled>} />
            <Route path="claims" element={<Titled title="Claims pipeline"><ClaimsPipeline /></Titled>} />
            <Route path="claims/:claimId" element={<Titled title="Claim"><ClaimDetail /></Titled>} />
            <Route path="requests" element={<Titled title="Requests"><AdvisorRequests /></Titled>} />
            <Route path="reminders" element={<Titled title="Reminders"><AdvisorReminders /></Titled>} />
            <Route path="assistant" element={<Titled title="Assistant"><Assistant /></Titled>} />
            <Route path="email" element={<Titled title="Email"><Email /></Titled>} />
          </Route>
        </Route>

        {/* Catch all */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
