import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, AlertCircle, ArrowRight } from "lucide-react";
import { useAuth } from "../store/authStore";
import { AuthLayout } from "../components/layout/AuthLayout";
import { ApiError } from "../api/errors";
import { getSafeRedirectUrl } from "../utils/redirect";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Field validation and form errors
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  const validate = (): boolean => {
    const errors: { email?: string; password?: string } = {};

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      errors.email = "Email address is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = "Please enter a valid email address.";
    }

    if (!password) {
      errors.password = "Password is required.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await login({
        email: email.trim().toLowerCase(),
        password,
      });

      const rawFrom = (location.state as { from?: unknown } | null)?.from;
      const safeDestination = getSafeRedirectUrl(rawFrom, "/dashboard");
      navigate(safeDestination, { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isRateLimited) {
          setFormError("Too many login attempts. Please wait a moment before trying again.");
        } else if (err.isUnauthorized) {
          setFormError("Invalid email or password.");
        } else if (err.isForbidden) {
          setFormError("This account is suspended or restricted. Please contact support.");
        } else if (err.isValidationError) {
          setFormError("Validation error: please verify your input.");
          const extracted = err.fieldErrors;
          setFieldErrors({
            email: extracted.email?.[0],
            password: extracted.password?.[0],
          });
        } else if (err.isNetworkError) {
          setFormError("Network error: Unable to connect to the server. Please check your connection.");
        } else {
          setFormError(err.message || "An unexpected error occurred during login.");
        }
      } else {
        setFormError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Sign in to your account"
      subtitle="Access your AgriDirect commercial dashboard and trade negotiations"
    >
      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        {/* Form-Level Error Alert */}
        {formError && (
          <div
            className="p-3.5 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-800 text-sm"
            role="alert"
          >
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <span className="leading-snug">{formError}</span>
          </div>
        )}

        {/* Email Field */}
        <div>
          <label htmlFor="login-email" className="block text-sm font-medium text-foreground mb-1">
            Email address
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (fieldErrors.email) setFieldErrors((prev) => ({ ...prev, email: undefined }));
            }}
            disabled={isSubmitting}
            className={`w-full px-3.5 py-2.5 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary transition-colors ${
              fieldErrors.email ? "border-red-400 focus:ring-red-400" : "border-border"
            }`}
            placeholder="you@example.com"
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? "email-error" : undefined}
          />
          {fieldErrors.email && (
            <p id="email-error" className="mt-1 text-xs text-red-600">
              {fieldErrors.email}
            </p>
          )}
        </div>

        {/* Password Field */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label htmlFor="login-password" className="block text-sm font-medium text-foreground">
              Password
            </label>
            <span className="text-xs text-muted-foreground">
              Admin-managed recovery
            </span>
          </div>
          <div className="relative">
            <input
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: undefined }));
              }}
              disabled={isSubmitting}
              className={`w-full px-3.5 py-2.5 pr-11 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary transition-colors ${
                fieldErrors.password ? "border-red-400 focus:ring-red-400" : "border-border"
              }`}
              placeholder="••••••••"
              aria-invalid={Boolean(fieldErrors.password)}
              aria-describedby={fieldErrors.password ? "password-error" : undefined}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 focus:outline-none focus:ring-2 focus:ring-primary rounded"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Eye className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>
          {fieldErrors.password && (
            <p id="password-error" className="mt-1 text-xs text-red-600">
              {fieldErrors.password}
            </p>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
              <span>Signing in...</span>
            </>
          ) : (
            <>
              <span>Sign in</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </>
          )}
        </button>

        {/* Register Navigation Link */}
        <div className="pt-4 border-t border-border text-center text-xs text-muted-foreground">
          Don&apos;t have an account yet?{" "}
          <Link
            to="/register"
            className="font-semibold text-primary hover:text-primary-800 underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
          >
            Register as a farmer or buyer
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};
