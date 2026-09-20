import React, { ElementType, ReactNode } from 'react';

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
