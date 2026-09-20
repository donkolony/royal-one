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
  Gauge,
  Target,
  ShieldCheck,
  ScrollText,
  Lock,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NotificationBell } from "../components/NotificationBell";
import { useMediaQuery } from "../lib/hooks";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../lib/types";

const ICON = "w-5 h-5";
type NavItem = { label: string; path: string; icon: React.ReactNode; end: boolean };

/** One layout for both staff roles. The owner starts on Business Health; an adviser starts on their dashboard. */
function navFor(role: Role): NavItem[] {
  const base = role === "owner" ? "/owner" : "/advisor";
  const i = (C: LucideIcon) => <C className={ICON} aria-hidden="true" />;
  if (role === "owner") {
    return [
      { label: "Business health", path: base, icon: i(Gauge), end: true },
      { label: "Opportunities", path: `${base}/radar`, icon: i(Target), end: false },
      { label: "Clients", path: `${base}/clients`, icon: i(Users), end: false },
      { label: "Claims", path: `${base}/claims`, icon: i(FileText), end: false },
      { label: "Compliance", path: `${base}/compliance`, icon: i(ShieldCheck), end: false },
      { label: "Audit log", path: `${base}/audit`, icon: i(ScrollText), end: false },
      { label: "Privacy", path: `${base}/privacy`, icon: i(Lock), end: false },
    ];
  }
  return [
    { label: "Dashboard", path: base, icon: i(LayoutDashboard), end: true },
    { label: "Opportunities", path: `${base}/radar`, icon: i(Target), end: false },
    { label: "Clients", path: `${base}/clients`, icon: i(Users), end: false },
    { label: "Claims", path: `${base}/claims`, icon: i(FileText), end: false },
    { label: "Requests", path: `${base}/requests`, icon: i(HelpCircle), end: false },
    { label: "Reminders", path: `${base}/reminders`, icon: i(Bell), end: false },
    { label: "Assistant", path: `${base}/assistant`, icon: i(MessageSquare), end: false },
    { label: "Email", path: `${base}/email`, icon: i(Mail), end: false },
    { label: "Compliance", path: `${base}/compliance`, icon: i(ShieldCheck), end: false },
    { label: "Audit log", path: `${base}/audit`, icon: i(ScrollText), end: false },
    { label: "Privacy", path: `${base}/privacy`, icon: i(Lock), end: false },
  ];
}

/** Layout route for every staff page (adviser or owner): `<Route element={<StaffLayout />}>` renders the matched page in <Outlet />. */
export default function StaffLayout() {
  const location = useLocation();
  const { profile, signOut } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const desktop = useMediaQuery("(min-width: 1024px)");
  const role: Role = profile?.role ?? "advisor";
  const navItems = navFor(role);
  const home = role === "owner" ? "/owner" : "/advisor";
  const portal = role === "owner" ? "Owner" : "Adviser";

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
        <Link to={home} className="flex items-center">
          <img src="/rs-logo.png" alt="Royal Square Financial Logo" className="h-8 w-auto object-contain mr-2" />
          <span className="text-charcoal-900 dark:text-white font-bold tracking-tight">{portal} Portal</span>
        </Link>
        <div className="flex items-center gap-1">
        {!desktop && <NotificationBell />}
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
        </div>
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
          <Link to={home} className="flex items-center">
            <img src="/rs-logo.png" alt="Royal Square Financial Logo" className="h-8 w-auto object-contain mr-2" />
            <span className="text-charcoal-900 dark:text-white font-bold text-sm tracking-tight leading-tight">
              {portal}
              <br />
              Portal
            </span>
          </Link>
        </div>

        {profile && (
          <div className="px-6 py-3 border-b border-charcoal-100 dark:border-charcoal-700 flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-charcoal-800 dark:text-charcoal-100 truncate">{profile.full_name}</p>
              <p className="text-xs text-charcoal-500 dark:text-charcoal-400 truncate">{profile.email}</p>
            </div>
            {desktop && <NotificationBell />}
          </div>
        )}

        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto" aria-label={`${portal} navigation`}>
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
