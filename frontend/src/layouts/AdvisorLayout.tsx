import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { DarkModeToggle } from "../components/ui";
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
import { supabase, signOut } from "../lib/supabase";

interface AdvisorLayoutProps {
  children: React.ReactNode;
}

export default function AdvisorLayout({ children }: AdvisorLayoutProps) {
  const location = useLocation();
  const { profile } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  async function handleSignOut() {
    await signOut();
  }

  const navItems = [
    {
      label: "Dashboard",
      path: "/advisor/dashboard",
      icon: <LayoutDashboard className="w-5 h-5" />,
    },
    {
      label: "Clients",
      path: "/advisor/clients",
      icon: <Users className="w-5 h-5" />,
    },
    {
      label: "Claims",
      path: "/advisor/claims",
      icon: <FileText className="w-5 h-5" />,
    },
    {
      label: "Requests",
      path: "/advisor/requests",
      icon: <HelpCircle className="w-5 h-5" />,
    },
    {
      label: "Reminders",
      path: "/advisor/reminders",
      icon: <Bell className="w-5 h-5" />,
    },
    {
      label: "Assistant",
      path: "/advisor/assistant",
      icon: <MessageSquare className="w-5 h-5" />,
    },
    {
      label: "Email",
      path: "/advisor/email",
      icon: <Mail className="w-5 h-5" />,
    },
  ];

  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 flex">
      {/* Mobile Top Bar */}
      <header className="lg:hidden fixed top-0 w-full bg-white dark:bg-charcoal-800 border-b border-charcoal-200 dark:border-charcoal-700 h-16 flex justify-between items-center px-4 z-50">
        <Link to="/advisor/dashboard" className="flex items-center">
          <img
            src="/rs-logo.png"
            alt="Royal Square Financial Logo"
            className="h-8 w-auto object-contain mr-2"
          />
          <span className="text-charcoal-900 dark:text-white font-bold tracking-tight">
            Adviser Portal
          </span>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          className="text-charcoal-900 dark:text-white"
        >
          {mobileMenuOpen ? (
            <X className="w-6 h-6" />
          ) : (
            <Menu className="w-6 h-6" />
          )}
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
        className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-charcoal-800
        border-r border-charcoal-200 dark:border-charcoal-700
        transform transition-transform duration-300 ease-in-out
        flex flex-col
        lg:translate-x-0 lg:static lg:flex
        ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}
      `}
      >
        <div className="h-16 flex items-center px-6 border-b border-charcoal-200 dark:border-charcoal-700">
          <Link to="/advisor/dashboard" className="flex items-center">
            <img
              src="/rs-logo.png"
              alt="Royal Square Financial Logo"
              className="h-8 w-auto object-contain mr-2"
            />
            <span className="text-charcoal-900 dark:text-white font-bold text-sm tracking-tight leading-tight">
              Adviser
              <br />
              Portal
            </span>
          </Link>
        </div>

        {profile && (
          <div className="px-6 py-3 border-b border-charcoal-100 dark:border-charcoal-700">
            <p className="text-sm font-medium text-charcoal-800 dark:text-charcoal-100 truncate">
              {profile.full_name}
            </p>
            <p className="text-xs text-charcoal-500 truncate">
              {profile.email}
            </p>
          </div>
        )}

        <nav
          className="flex-1 px-4 py-4 space-y-1 overflow-y-auto"
          aria-label="Adviser navigation"
        >
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive ? "page" : undefined}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-600 dark:bg-charcoal-700 dark:text-brand-400"
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
        className="flex-1 flex flex-col min-w-0 pt-16 lg:pt-0 overflow-hidden"
        id="main-content"
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-brand-500 text-white px-4 py-2 rounded z-50"
        >
          Skip to content
        </a>
        <div className="flex-1 overflow-auto p-4 md:p-8">{children}</div>
      </main>
    </div>
  );
}
