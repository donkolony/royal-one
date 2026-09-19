import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button, ErrorBanner, Card, PageTitle } from "../../components/ui";
import { Eye, EyeOff } from "lucide-react";

const signInSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

type SignInForm = z.infer<typeof signInSchema>;

export function SignIn() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  // If already authenticated (e.g. via DevLoginBanner), redirect to root (which handles role-based routing)
  if (session) {
    return <Navigate to="/" replace />;
  }

  const [error, setError] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInForm>({
    resolver: zodResolver(signInSchema),
  });

  const onSubmit = async (data: SignInForm) => {
    setLoading(true);
    setError(null);
    try {
      // Mock login
      setTimeout(() => {
        navigate("/dashboard");
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
          <div className="flex justify-center mb-4">
            <img
              src="/rs-logo.png"
              alt="Royal Square Financial Logo"
              className="h-16 w-auto object-contain"
            />
          </div>
          <p className="text-charcoal-500 dark:text-charcoal-400">
            Sign in to your account
          </p>
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
                {...register("email")}
                className="w-full rounded-md border border-charcoal-300 dark:border-charcoal-600 bg-white dark:bg-charcoal-800 px-3 py-2 text-charcoal-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-charcoal-700 dark:text-charcoal-300 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  {...register("password")}
                  className="w-full rounded-md border border-charcoal-300 dark:border-charcoal-600 bg-white dark:bg-charcoal-800 px-3 py-2 text-charcoal-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-charcoal-400 hover:text-charcoal-600 dark:hover:text-charcoal-300"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.password.message}
                </p>
              )}
            </div>

            <Button type="submit" loading={loading} className="w-full mt-6">
              Sign in
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
