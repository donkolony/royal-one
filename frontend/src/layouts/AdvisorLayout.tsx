import React, { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { DarkModeToggle, ErrorBoundary, PageLoader } from "../components/ui";
import {
  LayoutDashboard,
  Users,
  FileText,
  HelpCircle,
  Bell,
  MessageSquare,
  Mail,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { label: "Dashboard", path: "/advisor", icon: <LayoutDashboard className="w-5 h-5" aria-hidden="true" />, end: true },
  { label: "Clients", path: "/advisor/clients", icon: <Users className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Claims", path: "/advisor/claims", icon: <FileText className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Requests", path: "/advisor/requests", icon: <HelpCircle className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Reminders", path: "/advisor/reminders", icon: <Bell className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Assistant", path: "/advisor/assistant", icon: <MessageSquare className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Email", path: "/advisor/email", icon: <Mail className="w-5 h-5" aria-hidden="true" />, end: false },
];

/** Layout route for every adviser page: `<Route element={<AdvisorLayout />}>` renders the matched page in <Outlet />. */
export default function AdvisorLayout() {
  const location = useLocation();
  const { profile, signOut } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close the drawer whenever the route changes (also covers the browser back button).
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 flex">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 bg-brand-500 text-white px-4 py-2 rounded z-[60]"
      >
        Skip to content
      </a>

      {/* Mobile Top Bar */}
      <header className="lg:hidden fixed top-0 w-full bg-white dark:bg-charcoal-800 border-b border-charcoal-200 dark:border-charcoal-700 h-16 flex justify-between items-center px-4 z-50">
        <Link to="/advisor" className="flex items-center">
          <img src="/rs-logo.png" alt="Royal Square Financial Logo" className="h-8 w-auto object-contain mr-2" />
          <span className="text-charcoal-900 dark:text-white font-bold tracking-tight">Adviser Portal</span>
        </Link>
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileMenuOpen}
          aria-controls="adviser-sidebar"
          className="text-charcoal-900 dark:text-white"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" aria-hidden="true" /> : <Menu className="w-6 h-6" aria-hidden="true" />}
        </button>
      </header>

      {/* Sidebar Overlay (Mobile) */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        id="adviser-sidebar"
        className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-charcoal-800
        border-r border-charcoal-200 dark:border-charcoal-700
        transform transition-transform duration-300 ease-in-out
        flex flex-col
        lg:translate-x-0 lg:sticky lg:top-0 lg:h-screen lg:shrink-0
        ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}
      `}
      >
        <div className="h-16 shrink-0 flex items-center px-6 border-b border-charcoal-200 dark:border-charcoal-700">
          <Link to="/advisor" className="flex items-center">
            <img src="/rs-logo.png" alt="Royal Square Financial Logo" className="h-8 w-auto object-contain mr-2" />
            <span className="text-charcoal-900 dark:text-white font-bold text-sm tracking-tight leading-tight">
              Adviser
              <br />
              Portal
            </span>
          </Link>
        </div>

        {profile && (
          <div className="px-6 py-3 border-b border-charcoal-100 dark:border-charcoal-700">
            <p className="text-sm font-medium text-charcoal-800 dark:text-charcoal-100 truncate">{profile.full_name}</p>
            <p className="text-xs text-charcoal-500 dark:text-charcoal-400 truncate">{profile.email}</p>
          </div>
        )}

        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto" aria-label="Adviser navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-600 dark:bg-charcoal-700 dark:text-brand-300"
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
      <main className="flex-1 min-w-0 pt-16 lg:pt-0 overflow-x-auto" id="main-content" tabIndex={-1}>
        <div className="p-4 md:p-8">
          <ErrorBoundary resetKey={location.pathname}>
            <Suspense fallback={<PageLoader fullScreen={false} />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
