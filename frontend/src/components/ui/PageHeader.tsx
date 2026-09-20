import React, { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  badge?: ReactNode;
}

/** The one page heading. Title, an optional plain-language line under it, and actions on the right (they wrap on a phone). */
export function PageHeader({ title, subtitle, actions, badge }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold text-charcoal-900 dark:text-white">{title}</h1>
          {badge}
        </div>
        {subtitle && <p className="mt-1 text-sm text-charcoal-500 dark:text-charcoal-400 max-w-3xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
