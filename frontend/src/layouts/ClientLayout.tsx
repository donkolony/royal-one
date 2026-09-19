import React from "react";
import { Link, useLocation } from "react-router-dom";
import { DarkModeToggle } from "../components/ui";
import { Home, FileText, Target, Bell, HelpCircle, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { supabase, signOut } from "../lib/supabase";

interface ClientLayoutProps {
  children: React.ReactNode;
}

export default function ClientLayout({ children }: ClientLayoutProps) {
  const location = useLocation();
  const { profile } = useAuth();

  async function handleSignOut() {
    await signOut();
  }

  const navItems = [
    {
      label: "Dashboard",
      path: "/dashboard",
      icon: <Home className="w-5 h-5" />,
    },
    {
      label: "Claims",
      path: "/claims",
      icon: <FileText className="w-5 h-5" />,
    },
    { label: "Goals", path: "/goals", icon: <Target className="w-5 h-5" /> },
    {
      label: "Reminders",
      path: "/reminders",
      icon: <Bell className="w-5 h-5" />,
    },
    {
      label: "Requests",
      path: "/requests",
      icon: <HelpCircle className="w-5 h-5" />,
    },
  ];

  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 flex flex-col md:flex-row">
      {/* Top Bar (Mobile) */}
      <header className="md:hidden bg-white dark:bg-charcoal-800 border-b border-charcoal-200 dark:border-charcoal-700 p-4 flex justify-between items-center sticky top-0 z-40">
        <Link to="/dashboard" className="flex items-center">
          <img
            src="/rs-logo.png"
            alt="Royal Square Financial Logo"
            className="h-8 w-auto object-contain"
          />
        </Link>
        <div className="flex items-center gap-2">
          <DarkModeToggle />
          <button
            onClick={handleSignOut}
            aria-label="Sign out"
            className="text-charcoal-600 dark:text-charcoal-300 hover:text-danger transition-colors"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Sidebar (Desktop) */}
      <aside className="hidden md:flex flex-col w-64 bg-white dark:bg-charcoal-800 border-r border-charcoal-200 dark:border-charcoal-700 min-h-screen sticky top-0">
        <div className="p-6">
          <Link to="/dashboard" className="flex items-center mb-2">
            <img
              src="/rs-logo.png"
              alt="Royal Square Financial Logo"
              className="h-10 w-auto object-contain"
            />
          </Link>
          {profile && (
            <p className="mt-1 text-sm text-charcoal-500 dark:text-charcoal-400 truncate">
              {profile.full_name}
            </p>
          )}
        </div>
        <nav className="flex-1 px-4 space-y-1" aria-label="Main navigation">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-600 dark:bg-brand-900/20 dark:text-brand-400"
                    : "text-charcoal-700 hover:bg-charcoal-100 dark:text-charcoal-300 dark:hover:bg-charcoal-700"
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-charcoal-200 dark:border-charcoal-700 flex items-center justify-between">
          <DarkModeToggle />
          <button
            onClick={handleSignOut}
            className="flex items-center gap-2 text-sm font-medium text-charcoal-600 dark:text-charcoal-400 hover:text-danger transition-colors"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main
        className="flex-1 pb-16 md:pb-0 overflow-x-hidden"
        id="main-content"
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-brand-500 text-white px-4 py-2 rounded z-50"
        >
          Skip to content
        </a>
        <div className="max-w-7xl mx-auto p-4 md:p-8">{children}</div>
      </main>

      {/* Bottom Nav (Mobile) */}
      <nav
        className="md:hidden fixed bottom-0 w-full bg-white dark:bg-charcoal-800 border-t border-charcoal-200 dark:border-charcoal-700 z-40"
        aria-label="Mobile navigation"
      >
        <div className="flex justify-around items-center h-16">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center justify-center w-full h-full space-y-1 ${
                  isActive
                    ? "text-brand-500"
                    : "text-charcoal-500 dark:text-charcoal-400"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                {item.icon}
                <span className="text-[10px] font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
