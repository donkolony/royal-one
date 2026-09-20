import React, { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { supabase } from "../../lib/supabase";
import { isMock } from "../../lib/api";
import { friendlyAuthError } from "../../lib/errors";
import { AuthErrorScreen } from "../../components/auth/AuthErrorScreen";
import { returnPathFrom } from "../../components/auth/routing";
import { Button, ErrorBanner, Card, PageTitle } from "../../components/ui";

const signInSchema = z.object({
  email: z.string().trim().min(1, "Enter your email address").email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

type SignInForm = z.infer<typeof signInSchema>;

const inputClasses =
  "w-full rounded-md border border-charcoal-300 dark:border-charcoal-600 bg-white dark:bg-charcoal-800 px-3 py-2 text-charcoal-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60";

export function SignIn() {
  // All hooks first: nothing below may return before every hook has run.
  const location = useLocation();
  const { session, profile, loading } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInForm>({
    resolver: zodResolver(signInSchema),
  });

  const mock = isMock();

  const onSubmit = async (data: SignInForm) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email: data.email, password: data.password });
      if (error) throw error;
      // Success: AuthContext sees the new session, loads GET /me, and this page redirects by role below.
    } catch (err) {
      setSubmitError(friendlyAuthError(err));
    } finally {
      setSubmitting(false);
    }
  };

  // Already signed in: go where the visitor was heading, or "/" (which routes by role).
  if (session && profile) return <Navigate to={returnPathFrom(location.state) ?? "/"} replace />;
  // Signed in but the profile could not be loaded: an error screen, not a redirect (no loop with "/").
  if (session && !loading) return <AuthErrorScreen />;

  // After a successful sign-in the profile is still loading for a moment.
  const busy = submitting || (session !== null && loading);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-charcoal-50 dark:bg-charcoal-900 p-4">
      <PageTitle title="Sign in" />
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <img
              src="/rs-logo.png"
              alt="Royal Square Financial Logo"
              className="h-16 w-auto object-contain"
            />
          </div>
          <h1 className="text-charcoal-500 dark:text-charcoal-400 text-base font-normal">
            Sign in to your account
          </h1>
        </div>

        <Card padding="lg">
          {mock && (
            <p className="mb-4 rounded-md bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
              Offline mock mode is on, so there is nothing to sign in to. Choose a role in the Dev Mode panel.
            </p>
          )}
          {submitError && <ErrorBanner error={submitError} title="Could not sign in" className="mb-4" />}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-charcoal-700 dark:text-charcoal-300 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                inputMode="email"
                autoFocus
                disabled={busy || mock}
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? "email-error" : undefined}
                {...register("email")}
                className={inputClasses}
              />
              {errors.email && (
                <p id="email-error" className="text-red-600 dark:text-red-400 text-xs mt-1">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-charcoal-700 dark:text-charcoal-300 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  disabled={busy || mock}
                  aria-invalid={errors.password ? true : undefined}
                  aria-describedby={errors.password ? "password-error" : undefined}
                  {...register("password")}
                  className={`${inputClasses} pr-10`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-charcoal-400 hover:text-charcoal-600 dark:hover:text-charcoal-300"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" aria-hidden="true" />
                  ) : (
                    <Eye className="w-5 h-5" aria-hidden="true" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p id="password-error" className="text-red-600 dark:text-red-400 text-xs mt-1">
                  {errors.password.message}
                </p>
              )}
            </div>

            <Button type="submit" loading={busy} disabled={mock} className="w-full mt-6">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </Card>

        <p className="text-center text-sm text-charcoal-500 dark:text-charcoal-400 mt-8">
          &copy; {new Date().getFullYear()} Royal Square Financial. All rights
          reserved.
        </p>
      </div>
    </div>
  );
}

export default SignIn;
