export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-charcoal-900 disabled:opacity-50 disabled:pointer-events-none";

const sizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 py-2",
  lg: "h-12 px-6 text-lg",
};

const variants: Record<ButtonVariant, string> = {
  primary: "bg-brand-500 text-white hover:bg-brand-600 focus:ring-brand-500 dark:bg-brand-400 dark:text-charcoal-900 dark:hover:bg-brand-300",
  secondary:
    "border border-charcoal-300 text-charcoal-700 hover:bg-charcoal-100 focus:ring-charcoal-500 dark:border-charcoal-600 dark:text-charcoal-200 dark:hover:bg-charcoal-700",
  ghost: "text-charcoal-600 hover:bg-charcoal-100 focus:ring-charcoal-500 dark:text-charcoal-300 dark:hover:bg-charcoal-700",
  danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-600",
};

/**
 * Class names of a Button. Use it on a react-router <Link> to get a link that looks like a button
 * (never nest a <Button> inside a <Link>: that puts a button inside an anchor).
 */
export function buttonClasses({
  variant = "primary",
  size = "md",
  className = "",
}: { variant?: ButtonVariant; size?: ButtonSize; className?: string } = {}): string {
  return `${base} ${sizes[size]} ${variants[variant]} ${className}`.trim();
}
