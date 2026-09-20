import React, { ReactNode } from 'react';

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
