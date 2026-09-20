import React, { Component, ReactNode } from "react";
import { Button } from "./Button";
import { Card } from "./Card";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** When this value changes (e.g. the route), a shown error is cleared so the next page can render. */
  resetKey?: unknown;
  /** true: fills the screen (app root). false (default): sits inside the page area of a layout. */
  fullScreen?: boolean;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches a crash while rendering (for example a page treating a Page<T> as an array) so the layout,
 * navigation and sign-out stay usable instead of the whole app going blank.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Rendering error:", error, info.componentStack);
  }

  componentDidUpdate(prev: ErrorBoundaryProps) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  private reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;

    const body = (
      <Card padding="lg" className="max-w-lg w-full text-center">
        <h2 className="text-lg font-semibold text-charcoal-900 dark:text-white">This page hit a problem</h2>
        <p className="mt-2 text-sm text-charcoal-600 dark:text-charcoal-300">
          Something unexpected went wrong while showing this page. Your data is safe. Try again, or go back to the
          start.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button onClick={this.reset}>Try again</Button>
          <Button variant="secondary" onClick={() => window.location.assign("/")}>
            Go to the start
          </Button>
        </div>
      </Card>
    );

    return this.props.fullScreen ? (
      <div role="alert" className="min-h-screen flex items-center justify-center p-4 bg-charcoal-50 dark:bg-charcoal-900">
        {body}
      </div>
    ) : (
      <div role="alert" className="flex justify-center py-12">
        {body}
      </div>
    );
  }
}
