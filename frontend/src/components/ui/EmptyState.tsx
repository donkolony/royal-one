import React, { ReactNode } from "react";
import { Card } from "./Card";
import { Button } from "./Button";

interface EmptyStateProps {
  /** Full-featured usage */
  icon?: ReactNode;
  title?: string;
  description?: string;
  /** Shorthand: renders just the message as description */
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  icon,
  title,
  description,
  message,
  action,
}: EmptyStateProps) {
  const resolvedTitle = title ?? "Nothing here yet";
  const resolvedDescription = description ?? message ?? "";

  return (
    <Card
      className="flex flex-col items-center justify-center py-12 text-center"
      padding="lg"
    >
      {icon && (
        <div className="text-charcoal-400 dark:text-charcoal-500 mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-charcoal-900 dark:text-white mb-2">
        {resolvedTitle}
      </h3>
      {resolvedDescription && (
        <p className="text-charcoal-500 dark:text-charcoal-400 max-w-sm mb-6">
          {resolvedDescription}
        </p>
      )}
      {action && (
        <Button onClick={action.onClick} variant="primary">
          {action.label}
        </Button>
      )}
    </Card>
  );
}
