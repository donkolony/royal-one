import os
import json

base_dir = "/home/don_kolony/Desktop/developer/hack/afri-hack/royal-one/frontend/src"

files = {
    "components/ui/Button.tsx": """import React, { ButtonHTMLAttributes } from 'react';
import { Spinner } from './Spinner';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  
  const sizeStyles = {
    sm: 'h-8 px-3 text-sm',
    md: 'h-10 px-4 py-2',
    lg: 'h-12 px-6 text-lg',
  };

  const variantStyles = {
    primary: 'bg-brand-500 text-white hover:bg-brand-600 focus:ring-brand-500',
    secondary: 'border border-charcoal-300 text-charcoal-700 hover:bg-charcoal-100 focus:ring-charcoal-500',
    ghost: 'text-charcoal-600 hover:bg-charcoal-100 focus:ring-charcoal-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-600',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner size="sm" className="mr-2" />}
      {children}
    </button>
  );
}
""",

    "components/ui/Spinner.tsx": """import React from 'react';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Spinner({ size = 'md', className = '' }: SpinnerProps) {
  const sizeStyles = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <svg
      className={`animate-spin ${sizeStyles[size]} ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );
}
""",

    "components/ui/Card.tsx": """import React, { ElementType, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  as?: ElementType;
}

export function Card({ children, className = '', padding = 'md', as: Component = 'div' }: CardProps) {
  const paddingStyles = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  return (
    <Component className={`bg-white dark:bg-charcoal-800 rounded-lg shadow-sm border border-charcoal-100 dark:border-charcoal-700 ${paddingStyles[padding]} ${className}`}>
      {children}
    </Component>
  );
}
""",

    "components/ui/Badge.tsx": """import React, { ReactNode } from 'react';

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
  children: ReactNode;
}

export function Badge({ variant = 'default', size = 'sm', children }: BadgeProps) {
  const variantStyles = {
    default: 'bg-charcoal-100 text-charcoal-800 dark:bg-charcoal-700 dark:text-charcoal-200',
    success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-sm',
  };

  return (
    <span className={`inline-flex items-center rounded-full font-medium ${variantStyles[variant]} ${sizeStyles[size]}`}>
      {children}
    </span>
  );
}
""",

    "components/ui/StatusPill.tsx": """import React from 'react';
import { Badge } from './Badge';

export type ClaimStatus = 'submitted' | 'assessment' | 'authorised' | 'declined' | 'paid' | 'closed';

interface StatusPillProps {
  status: ClaimStatus;
  label?: string;
}

export function StatusPill({ status, label }: StatusPillProps) {
  const mapping: Record<ClaimStatus, { variant: any; defaultLabel: string }> = {
    submitted: { variant: 'info', defaultLabel: 'Submitted' },
    assessment: { variant: 'warning', defaultLabel: 'In Assessment' },
    authorised: { variant: 'success', defaultLabel: 'Authorised' },
    declined: { variant: 'danger', defaultLabel: 'Declined' },
    paid: { variant: 'success', defaultLabel: 'Paid' },
    closed: { variant: 'default', defaultLabel: 'Closed' },
  };

  const config = mapping[status] || { variant: 'default', defaultLabel: status };

  return <Badge variant={config.variant}>{label || config.defaultLabel}</Badge>;
}
""",

    "components/ui/ProgressBar.tsx": """import React from 'react';

interface ProgressBarProps {
  percent: number;
  label: string;
  showPercent?: boolean;
  colour?: 'brand' | 'success' | 'warning';
}

export function ProgressBar({ percent, label, showPercent = false, colour = 'brand' }: ProgressBarProps) {
  const clamped = Math.min(Math.max(percent, 0), 100);
  const colorStyles = {
    brand: 'bg-brand-500',
    success: 'bg-green-500',
    warning: 'bg-amber-500',
  };

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-charcoal-700 dark:text-charcoal-300">{label}</span>
        {showPercent && <span className="text-sm text-charcoal-500 dark:text-charcoal-400">{clamped}%</span>}
      </div>
      <div className="w-full bg-charcoal-200 dark:bg-charcoal-700 rounded-full h-2.5" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
        <div className={`h-2.5 rounded-full ${colorStyles[colour]}`} style={{ width: `${clamped}%` }}></div>
      </div>
    </div>
  );
}
""",

    "components/ui/Skeleton.tsx": """import React from 'react';

interface SkeletonProps {
  className?: string;
  lines?: number;
  variant?: 'text' | 'circle' | 'rect';
}

export function Skeleton({ className = '', lines = 1, variant = 'text' }: SkeletonProps) {
  const base = 'animate-pulse bg-charcoal-200 dark:bg-charcoal-700';

  if (variant === 'circle') {
    return <div className={`rounded-full ${base} ${className}`} />;
  }

  if (variant === 'rect') {
    return <div className={`rounded ${base} ${className}`} />;
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`h-4 rounded ${base} ${className} ${i === lines - 1 && lines > 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  );
}
""",

    "components/ui/Modal.tsx": """import React, { useEffect, useRef, ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export function Modal({ open, onClose, title, children, footer, size = 'md' }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose();
    };
    if (open) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'auto';
    };
  }, [open, onClose]);

  if (!open) return null;

  const sizeStyles = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-3xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-charcoal-900/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`relative bg-white dark:bg-charcoal-800 rounded-lg shadow-xl w-full ${sizeStyles[size]} flex flex-col max-h-[90vh]`}
      >
        <div className="px-6 py-4 border-b border-charcoal-100 dark:border-charcoal-700">
          <h2 id="modal-title" className="text-lg font-semibold text-charcoal-900 dark:text-white">{title}</h2>
        </div>
        <div className="px-6 py-4 overflow-y-auto flex-1">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-charcoal-100 dark:border-charcoal-700 bg-charcoal-50 dark:bg-charcoal-800 rounded-b-lg flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
""",

    "components/ui/EmptyState.tsx": """import React, { ReactNode } from 'react';
import { Card } from './Card';
import { Button } from './Button';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Card className="flex flex-col items-center justify-center py-12 text-center" padding="lg">
      <div className="text-charcoal-400 dark:text-charcoal-500 mb-4">{icon}</div>
      <h3 className="text-lg font-medium text-charcoal-900 dark:text-white mb-2">{title}</h3>
      <p className="text-charcoal-500 dark:text-charcoal-400 max-w-sm mb-6">{description}</p>
      {action && (
        <Button onClick={action.onClick} variant="primary">
          {action.label}
        </Button>
      )}
    </Card>
  );
}
""",

    "components/ui/ErrorBanner.tsx": """import React from 'react';
import { Button } from './Button';

interface ErrorBannerProps {
  error: any;
  onRetry?: () => void;
}

export function ErrorBanner({ error, onRetry }: ErrorBannerProps) {
  const message = error?.message || (typeof error === 'string' ? error : 'An unexpected error occurred.');
  const requestId = error?.request_id;

  const handleCopy = () => {
    if (requestId) {
      navigator.clipboard.writeText(`Error: ${message}\\nRequest ID: ${requestId}`);
    }
  };

  return (
    <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded shadow-sm">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="text-red-800 dark:text-red-200 font-medium">Error</h3>
          <p className="text-red-700 dark:text-red-300 text-sm mt-1">{message}</p>
        </div>
        {onRetry && (
          <Button variant="danger" size="sm" onClick={onRetry} className="ml-4">
            Retry
          </Button>
        )}
      </div>
      {requestId && (
        <div className="mt-3 flex items-center justify-between text-xs text-red-600 dark:text-red-400 bg-white/50 dark:bg-black/20 p-2 rounded">
          <span className="font-mono">Req ID: {requestId}</span>
          <button onClick={handleCopy} className="hover:underline focus:outline-none">
            Copy details
          </button>
        </div>
      )}
    </div>
  );
}
""",

    "components/ui/PageTitle.tsx": """import React from 'react';
import { Helmet } from 'react-helmet-async';

export function PageTitle({ title }: { title: string }) {
  return (
    <Helmet>
      <title>{title} | Royal Square Financial</title>
    </Helmet>
  );
}
""",

    "components/ui/DarkModeToggle.tsx": """import React, { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from './Button';

export function DarkModeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const isDark = localStorage.getItem('theme') === 'dark' ||
      (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setIsDark(isDark);
    if (isDark) document.documentElement.classList.add('dark');
  }, []);

  const toggle = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  return (
    <Button variant="ghost" size="sm" onClick={toggle} aria-label="Toggle dark mode">
      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </Button>
  );
}
""",

    "components/ui/NetWorthCard.tsx": """import React from 'react';
import { Card } from './Card';
import { format, parseISO } from 'date-fns';

interface NetWorth {
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  as_of: string;
}

export function NetWorthCard({ netWorth }: { netWorth: NetWorth }) {
  const formatZAR = (cents: number) => {
    const rands = cents / 100;
    return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(rands);
  };

  const isNegative = netWorth.net_worth < 0;

  return (
    <Card>
      <div className="mb-4">
        <h3 className="text-sm font-medium text-charcoal-500 dark:text-charcoal-400">Total Net Worth</h3>
        <p className={`text-3xl font-bold mt-1 ${isNegative ? 'text-red-600 dark:text-red-400' : 'text-charcoal-900 dark:text-white'}`}>
          {formatZAR(netWorth.net_worth)}
        </p>
        <p className="text-xs text-charcoal-400 mt-1">
          As of {format(parseISO(netWorth.as_of), 'dd MMM yyyy')}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 border-t border-charcoal-100 dark:border-charcoal-700 pt-4">
        <div>
          <p className="text-xs text-charcoal-500">Total Assets</p>
          <p className="text-sm font-medium text-charcoal-900 dark:text-white">{formatZAR(netWorth.total_assets)}</p>
        </div>
        <div>
          <p className="text-xs text-charcoal-500">Total Liabilities</p>
          <p className="text-sm font-medium text-charcoal-900 dark:text-white">{formatZAR(netWorth.total_liabilities)}</p>
        </div>
      </div>
    </Card>
  );
}
""",

    "components/ui/GoalCard.tsx": """import React from 'react';
import { Card } from './Card';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';
import { format, parseISO } from 'date-fns';

interface Goal {
  title: string;
  category: string;
  progress_percent: number;
  current_amount: number;
  target_amount: number;
  target_date?: string;
}

export function GoalCard({ goal }: { goal: Goal }) {
  const formatZAR = (cents: number) => {
    return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(cents / 100);
  };

  return (
    <Card>
      <div className="flex justify-between items-start mb-4">
        <h3 className="font-semibold text-charcoal-900 dark:text-white">{goal.title}</h3>
        <Badge variant="info">{goal.category}</Badge>
      </div>
      
      <div className="mb-4">
        <ProgressBar percent={goal.progress_percent} label="Progress" showPercent colour="brand" />
      </div>
      
      <div className="flex justify-between text-sm">
        <div>
          <p className="text-charcoal-500 dark:text-charcoal-400">Current</p>
          <p className="font-medium text-charcoal-900 dark:text-white">{formatZAR(goal.current_amount)}</p>
        </div>
        <div className="text-right">
          <p className="text-charcoal-500 dark:text-charcoal-400">Target</p>
          <p className="font-medium text-charcoal-900 dark:text-white">{formatZAR(goal.target_amount)}</p>
        </div>
      </div>
      
      {goal.target_date && (
        <p className="text-xs text-charcoal-400 dark:text-charcoal-500 mt-4 text-center bg-charcoal-50 dark:bg-charcoal-700/50 py-1 rounded">
          Target Date: {format(parseISO(goal.target_date), 'dd MMM yyyy')}
        </p>
      )}
    </Card>
  );
}
""",

    "components/ui/ReminderRow.tsx": """import React, { useState } from 'react';
import { Button } from './Button';
import { format, parseISO, isPast, isToday, addDays } from 'date-fns';
import { Check } from 'lucide-react';

interface Reminder {
  id: string;
  title: string;
  due_date: string;
  status: 'pending' | 'completed';
}

export function ReminderRow({ reminder, onComplete }: { reminder: Reminder; onComplete: (id: string) => Promise<void> }) {
  const [loading, setLoading] = useState(false);

  const handleComplete = async () => {
    setLoading(true);
    try {
      await onComplete(reminder.id);
    } finally {
      setLoading(false);
    }
  };

  const due = parseISO(reminder.due_date);
  const isOverdue = isPast(due) && !isToday(due);
  const isDueSoon = !isOverdue && due <= addDays(new Date(), 3);

  const urgencyColor = isOverdue ? 'text-red-600' : isDueSoon ? 'text-amber-600' : 'text-charcoal-600';

  return (
    <div className="flex items-center justify-between p-4 bg-white dark:bg-charcoal-800 border border-charcoal-100 dark:border-charcoal-700 rounded-lg shadow-sm">
      <div>
        <h4 className="font-medium text-charcoal-900 dark:text-white">{reminder.title}</h4>
        <p className={`text-sm ${urgencyColor} flex items-center gap-2 mt-1`}>
          {format(due, 'dd MMM yyyy')}
          {isOverdue && <span className="text-xs bg-red-100 text-red-800 px-1.5 py-0.5 rounded">Overdue</span>}
        </p>
      </div>
      {reminder.status !== 'completed' && (
        <Button variant="ghost" size="sm" onClick={handleComplete} loading={loading} aria-label="Mark done">
          <Check className="w-5 h-5 text-green-600" />
        </Button>
      )}
    </div>
  );
}
""",

    "components/ui/ClaimStatusStepper.tsx": """import React from 'react';
import { ClaimStatus } from './StatusPill';
import { Check } from 'lucide-react';

interface ClaimStatusStepperProps {
  currentStatus: ClaimStatus;
  statuses: { id: string; label: string }[];
}

export function ClaimStatusStepper({ currentStatus, statuses }: ClaimStatusStepperProps) {
  const currentIndex = statuses.findIndex((s) => s.id === currentStatus);

  return (
    <div className="w-full">
      <div className="hidden md:flex items-center justify-between">
        {statuses.map((status, index) => {
          const isCompleted = index < currentIndex;
          const isActive = index === currentIndex;
          
          return (
            <div key={status.id} className="flex flex-col items-center relative flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 transition-colors ${
                isActive ? 'bg-brand-500 text-white' : 
                isCompleted ? 'bg-green-500 text-white' : 'bg-charcoal-200 dark:bg-charcoal-700 text-charcoal-500'
              }`}>
                {isCompleted ? <Check className="w-4 h-4" /> : <span className="text-sm">{index + 1}</span>}
              </div>
              <p className={`mt-2 text-sm font-medium ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-charcoal-500'}`}>
                {status.label}
              </p>
              {index < statuses.length - 1 && (
                <div className={`absolute top-4 left-1/2 w-full h-0.5 -z-10 ${
                  isCompleted ? 'bg-green-500' : 'bg-charcoal-200 dark:bg-charcoal-700'
                }`} />
              )}
            </div>
          );
        })}
      </div>
      
      <div className="flex md:hidden flex-col gap-4 relative">
        {statuses.map((status, index) => {
          const isCompleted = index < currentIndex;
          const isActive = index === currentIndex;
          
          return (
            <div key={status.id} className="flex items-center gap-4 relative">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 shrink-0 ${
                isActive ? 'bg-brand-500 text-white' : 
                isCompleted ? 'bg-green-500 text-white' : 'bg-charcoal-200 dark:bg-charcoal-700 text-charcoal-500'
              }`}>
                {isCompleted ? <Check className="w-4 h-4" /> : <span className="text-sm">{index + 1}</span>}
              </div>
              <p className={`text-sm font-medium ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-charcoal-500'}`}>
                {status.label}
              </p>
              {index < statuses.length - 1 && (
                <div className={`absolute top-8 left-4 w-0.5 h-full -ml-px -z-10 ${
                  isCompleted ? 'bg-green-500' : 'bg-charcoal-200 dark:bg-charcoal-700'
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
""",

    "components/ui/index.ts": """export * from './Button';
export * from './Card';
export * from './Badge';
export * from './StatusPill';
export * from './ProgressBar';
export * from './Skeleton';
export * from './Modal';
export * from './EmptyState';
export * from './ErrorBanner';
export * from './Spinner';
export * from './PageTitle';
export * from './DarkModeToggle';
export * from './NetWorthCard';
export * from './GoalCard';
export * from './ReminderRow';
export * from './ClaimStatusStepper';
""",

    "layouts/ClientLayout.tsx": """import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { DarkModeToggle } from '../components/ui';
import { Home, FileText, Target, Bell, HelpCircle, LogOut } from 'lucide-react';

export function ClientLayout() {
  const location = useLocation();

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: <Home className="w-5 h-5" /> },
    { label: 'Claims', path: '/claims', icon: <FileText className="w-5 h-5" /> },
    { label: 'Goals', path: '/goals', icon: <Target className="w-5 h-5" /> },
    { label: 'Reminders', path: '/reminders', icon: <Bell className="w-5 h-5" /> },
    { label: 'Requests', path: '/requests', icon: <HelpCircle className="w-5 h-5" /> },
  ];

  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 flex flex-col md:flex-row">
      {/* Top Bar (Mobile & Desktop) */}
      <header className="md:hidden bg-white dark:bg-charcoal-800 border-b border-charcoal-200 dark:border-charcoal-700 p-4 flex justify-between items-center sticky top-0 z-40">
        <Link to="/dashboard" className="text-xl font-bold text-brand-600 dark:text-brand-500 tracking-tight">
          RS<span className="text-charcoal-900 dark:text-white"> Financial</span>
        </Link>
        <div className="flex items-center gap-2">
          <DarkModeToggle />
          <button className="text-charcoal-600 dark:text-charcoal-300">
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Sidebar (Desktop) */}
      <aside className="hidden md:flex flex-col w-64 bg-white dark:bg-charcoal-800 border-r border-charcoal-200 dark:border-charcoal-700 min-h-screen sticky top-0">
        <div className="p-6">
          <Link to="/dashboard" className="text-2xl font-bold text-brand-600 dark:text-brand-500 tracking-tight">
            RS<span className="text-charcoal-900 dark:text-white"> Financial</span>
          </Link>
        </div>
        <nav className="flex-1 px-4 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-400'
                    : 'text-charcoal-700 hover:bg-charcoal-100 dark:text-charcoal-300 dark:hover:bg-charcoal-700'
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
          <button className="flex items-center gap-2 text-sm font-medium text-charcoal-600 dark:text-charcoal-400 hover:text-red-600 dark:hover:text-red-400 transition-colors">
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 pb-16 md:pb-0 overflow-x-hidden">
        <div className="max-w-7xl mx-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>

      {/* Bottom Nav (Mobile) */}
      <nav className="md:hidden fixed bottom-0 w-full bg-white dark:bg-charcoal-800 border-t border-charcoal-200 dark:border-charcoal-700 pb-safe z-40">
        <div className="flex justify-around items-center h-16">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center justify-center w-full h-full space-y-1 ${
                  isActive ? 'text-brand-600 dark:text-brand-400' : 'text-charcoal-500 dark:text-charcoal-400'
                }`}
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
""",

    "layouts/AdvisorLayout.tsx": """import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { DarkModeToggle } from '../components/ui';
import { Home, Users, FileText, HelpCircle, Bell, MessageSquare, Mail, LogOut, Menu, X } from 'lucide-react';

export function AdvisorLayout() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: <Home className="w-5 h-5" /> },
    { label: 'Clients', path: '/clients', icon: <Users className="w-5 h-5" /> },
    { label: 'Claims', path: '/claims', icon: <FileText className="w-5 h-5" /> },
    { label: 'Requests', path: '/requests', icon: <HelpCircle className="w-5 h-5" /> },
    { label: 'Reminders', path: '/reminders', icon: <Bell className="w-5 h-5" /> },
    { label: 'Assistant', path: '/assistant', icon: <MessageSquare className="w-5 h-5" /> },
    { label: 'Email', path: '/email', icon: <Mail className="w-5 h-5" /> },
  ];

  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 flex">
      {/* Mobile Top Bar */}
      <header className="lg:hidden fixed top-0 w-full bg-white dark:bg-charcoal-800 border-b border-charcoal-200 dark:border-charcoal-700 h-16 flex justify-between items-center px-4 z-50">
        <Link to="/dashboard" className="text-xl font-bold text-brand-600 dark:text-brand-500 tracking-tight">
          RS<span className="text-charcoal-900 dark:text-white"> Advisor</span>
        </Link>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-charcoal-900 dark:text-white">
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
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
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-charcoal-800 border-r border-charcoal-200 dark:border-charcoal-700 
        transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:flex flex-col
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-16 flex items-center px-6 border-b border-charcoal-200 dark:border-charcoal-700 lg:border-none">
          <Link to="/dashboard" className="text-2xl font-bold text-brand-600 dark:text-brand-500 tracking-tight">
            RS<span className="text-charcoal-900 dark:text-white"> Advisor</span>
          </Link>
        </div>
        
        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-400'
                    : 'text-charcoal-700 hover:bg-charcoal-100 dark:text-charcoal-300 dark:hover:bg-charcoal-700'
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
          <button className="flex items-center gap-2 text-sm font-medium text-charcoal-600 dark:text-charcoal-400 hover:text-red-600 dark:hover:text-red-400 transition-colors">
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 pt-16 lg:pt-0 overflow-hidden">
        <div className="flex-1 overflow-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
""",

    "components/auth/ProtectedRoute.tsx": """import React from 'react';
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
""",

    "pages/auth/SignIn.tsx": """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button, ErrorBanner, Card, PageTitle } from '../../components/ui';
import { Eye, EyeOff } from 'lucide-react';

const signInSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type SignInForm = z.infer<typeof signInSchema>;

export function SignIn() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<SignInForm>({
    resolver: zodResolver(signInSchema),
  });

  const onSubmit = async (data: SignInForm) => {
    setLoading(true);
    setError(null);
    try {
      // Mock login
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4">
      <PageTitle title="Sign In" />
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-brand-600 dark:text-brand-500 tracking-tight mb-2">
            RS<span className="text-charcoal-900 dark:text-white"> Financial</span>
          </h1>
          <p className="text-charcoal-500 dark:text-charcoal-400">Sign in to your account</p>
        </div>

        <Card padding="lg">
          {error && <ErrorBanner error={error} className="mb-4" />}
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-charcoal-700 dark:text-charcoal-300 mb-1">
                Email
              </label>
              <input
                type="email"
                {...register('email')}
                className="w-full rounded-md border border-charcoal-300 dark:border-charcoal-600 bg-white dark:bg-charcoal-800 px-3 py-2 text-charcoal-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-charcoal-700 dark:text-charcoal-300 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type="{showPassword ? 'text' : 'password'}"
                  {...register('password')}
                  className="w-full rounded-md border border-charcoal-300 dark:border-charcoal-600 bg-white dark:bg-charcoal-800 px-3 py-2 text-charcoal-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-charcoal-400 hover:text-charcoal-600 dark:hover:text-charcoal-300"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
            </div>

            <Button type="submit" loading={loading} className="w-full mt-6">
              Sign in
            </Button>
          </form>
        </Card>

        <p className="text-center text-sm text-charcoal-500 dark:text-charcoal-400 mt-8">
          &copy; {new Date().getFullYear()} Royal Square Financial. All rights reserved.
        </p>
      </div>
    </div>
  );
}
""",

    "pages/NotFound.tsx": """import React from 'react';
import { Link } from 'react-router-dom';
import { PageTitle, Button } from '../components/ui';

export function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4 text-center">
      <PageTitle title="Page Not Found" />
      <h1 className="text-8xl font-bold text-brand-500 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-charcoal-900 dark:text-white mb-2">Page not found</h2>
      <p className="text-charcoal-500 dark:text-charcoal-400 mb-8 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link to="/">
        <Button variant="primary">Return Home</Button>
      </Link>
    </div>
  );
}
""",

    "pages/ServerError.tsx": """import React from 'react';
import { PageTitle, Button } from '../components/ui';
import { Copy } from 'lucide-react';

interface ServerErrorProps {
  requestId?: string;
}

export function ServerError({ requestId }: ServerErrorProps) {
  const handleCopy = () => {
    if (requestId) navigator.clipboard.writeText(requestId);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4 text-center">
      <PageTitle title="Server Error" />
      <h1 className="text-4xl font-bold text-charcoal-900 dark:text-white mb-4">Oops! Something went wrong</h1>
      <p className="text-charcoal-600 dark:text-charcoal-400 mb-6 max-w-md">
        We encountered an unexpected error on our end. Please try again later.
      </p>
      
      {requestId && (
        <div className="flex items-center gap-2 bg-charcoal-100 dark:bg-charcoal-800 px-4 py-2 rounded mb-8 text-sm">
          <span className="font-mono text-charcoal-700 dark:text-charcoal-300">Request ID: {requestId}</span>
          <button onClick={handleCopy} className="text-brand-600 hover:text-brand-700 focus:outline-none" aria-label="Copy request ID">
            <Copy className="w-4 h-4" />
          </button>
        </div>
      )}

      <Button onClick={() => window.location.reload()} variant="primary">
        Refresh Page
      </Button>
    </div>
  );
}
"""
}

for rel_path, content in files.items():
    full_path = os.path.join(base_dir, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w') as f:
        f.write(content)

print(f"Created {len(files)} files successfully.")
