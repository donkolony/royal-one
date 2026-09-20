import React, { ButtonHTMLAttributes } from "react";
import { Spinner } from "./Spinner";
import { buttonClasses, type ButtonSize, type ButtonVariant } from "./buttonStyles";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={buttonClasses({ variant, size, className })}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Spinner size="sm" className="mr-2" />}
      {children}
    </button>
  );
}
