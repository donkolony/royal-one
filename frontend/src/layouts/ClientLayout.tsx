import React, { Suspense } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { DarkModeToggle, ErrorBoundary, PageLoader } from "../components/ui";
import { Home, FileText, Target, Bell, HelpCircle, LogOut, Shield, User } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: <Home className="w-5 h-5" aria-hidden="true" />, end: true },
  { label: "Policies", path: "/policies", icon: <Shield className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Claims", path: "/claims", icon: <FileText className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Goals", path: "/goals", icon: <Target className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Reminders", path: "/reminders", icon: <Bell className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Requests", path: "/requests", icon: <HelpCircle className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Profile", path: "/profile", icon: <User className="w-5 h-5" aria-hidden="true" />, end: false },
];

/** Layout route for every client page: `<Route element={<ClientLayout />}>` renders the matched page in <Outlet />. */
export default function ClientLayout() {
  const location = useLocation();
  const { profile, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 flex flex-col md:flex-row">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 bg-brand-500 text-white px-4 py-2 rounded z-[60]"
      >
        Skip to content
      </a>

      {/* Top Bar (Mobile) */}
      <header className="md:hidden bg-white dark:bg-charcoal-800 border-b border-charcoal-200 dark:border-charcoal-700 p-4 flex justify-between items-center sticky top-0 z-40">
        <Link to="/dashboard" className="flex items-center">
          <img src="/rs-logo.png" alt="Royal Square Financial Logo" className="h-8 w-auto object-contain" />
        </Link>
        <div className="flex items-center gap-2">
          <DarkModeToggle />
          <button
            type="button"
            onClick={() => void signOut()}
            aria-label="Sign out"
            className="text-charcoal-600 dark:text-charcoal-300 hover:text-danger transition-colors"
          >
            <LogOut className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
      </header>

      {/* Sidebar (Desktop) */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 bg-white dark:bg-charcoal-800 border-r border-charcoal-200 dark:border-charcoal-700 h-screen sticky top-0">
        <div className="p-6">
          <Link to="/dashboard" className="flex items-center mb-2">
            <img src="/rs-logo.png" alt="Royal Square Financial Logo" className="h-10 w-auto object-contain" />
          </Link>
          {profile && (
            <p className="mt-1 text-sm text-charcoal-500 dark:text-charcoal-400 truncate">{profile.full_name}</p>
          )}
        </div>
        <nav className="flex-1 px-4 space-y-1 overflow-y-auto" aria-label="Main navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-600 dark:bg-brand-900/20 dark:text-brand-300"
                    : "text-charcoal-700 hover:bg-charcoal-100 dark:text-charcoal-300 dark:hover:bg-charcoal-700"
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-charcoal-200 dark:border-charcoal-700 flex items-center justify-between">
          <DarkModeToggle />
          <button
            type="button"
            onClick={() => void signOut()}
            className="flex items-center gap-2 text-sm font-medium text-charcoal-600 dark:text-charcoal-400 hover:text-danger transition-colors"
          >
            <LogOut className="w-4 h-4" aria-hidden="true" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0 pb-20 md:pb-0 overflow-x-hidden" id="main-content" tabIndex={-1}>
        <div className="max-w-7xl mx-auto p-4 md:p-8">
          <ErrorBoundary resetKey={location.pathname}>
            <Suspense fallback={<PageLoader fullScreen={false} />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </div>
      </main>

      {/* Bottom Nav (Mobile) */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 bg-white dark:bg-charcoal-800 border-t border-charcoal-200 dark:border-charcoal-700 z-40"
        aria-label="Mobile navigation"
      >
        <div className="flex items-stretch h-16">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `flex flex-1 min-w-0 flex-col items-center justify-center gap-1 px-0.5 ${
                  isActive ? "text-brand-500 dark:text-brand-300" : "text-charcoal-500 dark:text-charcoal-400"
                }`
              }
            >
              {item.icon}
              <span className="text-[10px] font-medium leading-none truncate max-w-full">{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
