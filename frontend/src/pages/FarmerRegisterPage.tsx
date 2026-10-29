import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, AlertCircle, CheckCircle2, ArrowRight, Tractor } from "lucide-react";
import { useAuth } from "../store/authStore";
import { AuthLayout } from "../components/layout/AuthLayout";
import { ApiError } from "../api/errors";
import type { FarmerRegisterRequest, User } from "../types";

export const FarmerRegisterPage: React.FC = () => {
  const { registerFarmer } = useAuth();

  // Form State
  const [formData, setFormData] = useState<FarmerRegisterRequest>({
    full_name: "",
    email: "",
    password: "",
    password_confirm: "",
    phone_number: "",
    farm_name: "",
    farm_location_address: "",
    city: "",
    state: "",
    postal_code: "",
    farm_size_acres: undefined,
    farming_practices: "conventional",
    primary_crops: "",
    bio: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Status & Error Tracking
  const [registeredUser, setRegisteredUser] = useState<User | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.full_name.trim()) {
      errors.full_name = "Full name is required.";
    }

    const trimmedEmail = formData.email.trim();
    if (!trimmedEmail) {
      errors.email = "Email address is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = "Please enter a valid email address.";
    }

    if (!formData.password) {
      errors.password = "Password is required.";
    } else if (formData.password.length < 8) {
      errors.password = "Password must be at least 8 characters long.";
    }

    if (!formData.password_confirm) {
      errors.password_confirm = "Please confirm your password.";
    } else if (formData.password !== formData.password_confirm) {
      errors.password_confirm = "Passwords do not match.";
    }

    if (formData.farm_size_acres !== undefined && formData.farm_size_acres !== null) {
      if (isNaN(Number(formData.farm_size_acres)) || Number(formData.farm_size_acres) <= 0) {
        errors.farm_size_acres = "Farm size must be a positive number of acres.";
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "farm_size_acres" ? (value === "" ? undefined : Number(value)) : value,
    }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload: FarmerRegisterRequest = {
        ...formData,
        email: formData.email.trim().toLowerCase(),
        full_name: formData.full_name.trim(),
        phone_number: formData.phone_number?.trim() || undefined,
        farm_name: formData.farm_name?.trim() || undefined,
        farm_location_address: formData.farm_location_address?.trim() || undefined,
        city: formData.city?.trim() || undefined,
        state: formData.state?.trim() || undefined,
        postal_code: formData.postal_code?.trim() || undefined,
        farming_practices: formData.farming_practices?.trim() || undefined,
        primary_crops: formData.primary_crops?.trim() || undefined,
        bio: formData.bio?.trim() || undefined,
      };

      const user = await registerFarmer(payload);
      setRegisteredUser(user);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isConflict) {
          setFormError(err.message || "An account with this email address or phone number already exists.");
        } else if (err.isValidationError) {
          setFormError("Validation error: please check the highlighted fields.");
          const backendErrors: Record<string, string> = {};
          for (const [key, msgs] of Object.entries(err.fieldErrors)) {
            backendErrors[key] = msgs[0];
          }
          setFieldErrors(backendErrors);
        } else if (err.isNetworkError) {
          setFormError("Network error: Unable to reach the server. Please check your connection.");
        } else {
          setFormError(err.message || "Registration failed. Please check your information and try again.");
        }
      } else {
        setFormError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render Post-Registration Confirmation Screen
  if (registeredUser) {
    return (
      <AuthLayout
        title="Account Created Successfully"
        subtitle="Your agricultural producer registration has been recorded"
      >
        <div className="text-center space-y-6 py-4">
          <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-9 h-9" aria-hidden="true" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-foreground">
              Welcome, {registeredUser.farmer_profile?.full_name || registeredUser.email}!
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-md mx-auto">
              Your farmer account has been created with status{" "}
              <span className="font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-xs">
                {registeredUser.verification_status}
              </span>
              . You may now sign in. Produce listings and buyer communications will be unlocked once administrative identity verification is completed.
            </p>
          </div>

          <div className="pt-4">
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 py-2.5 px-6 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 w-full sm:w-auto"
            >
              <span>Sign in to your account</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Farmer Account Registration"
      subtitle="Join AgriDirect to market agricultural produce directly to commercial buyers"
      maxWidth="wide"
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

        {/* Section 1: Credentials & Primary Identity */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider pb-1 border-b border-border flex items-center gap-2">
            <Tractor className="w-4 h-4 text-primary" aria-hidden="true" />
            <span>Account Credentials (Required)</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Full Name */}
            <div>
              <label htmlFor="farmer-full-name" className="block text-xs font-medium text-foreground mb-1">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                id="farmer-full-name"
                name="full_name"
                type="text"
                autoComplete="name"
                value={formData.full_name}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.full_name ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="e.g. Ramesh Patel"
                aria-invalid={Boolean(fieldErrors.full_name)}
                aria-describedby={fieldErrors.full_name ? "name-error" : undefined}
              />
              {fieldErrors.full_name && (
                <p id="name-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.full_name}
                </p>
              )}
            </div>

            {/* Email Address */}
            <div>
              <label htmlFor="farmer-email" className="block text-xs font-medium text-foreground mb-1">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                id="farmer-email"
                name="email"
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.email ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="farmer@example.com"
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
              />
              {fieldErrors.email && (
                <p id="email-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label htmlFor="farmer-password" className="block text-xs font-medium text-foreground mb-1">
                Password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="farmer-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={formData.password}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  className={`w-full px-3 py-2 pr-10 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                    fieldErrors.password ? "border-red-400 focus:ring-red-400" : "border-border"
                  }`}
                  placeholder="Min. 8 characters"
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={fieldErrors.password ? "pass-error" : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 focus:outline-none focus:ring-2 focus:ring-primary rounded"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {fieldErrors.password && (
                <p id="pass-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="farmer-password-confirm" className="block text-xs font-medium text-foreground mb-1">
                Confirm Password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="farmer-password-confirm"
                  name="password_confirm"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={formData.password_confirm}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  className={`w-full px-3 py-2 pr-10 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                    fieldErrors.password_confirm ? "border-red-400 focus:ring-red-400" : "border-border"
                  }`}
                  placeholder="Re-enter password"
                  aria-invalid={Boolean(fieldErrors.password_confirm)}
                  aria-describedby={fieldErrors.password_confirm ? "confirm-error" : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 focus:outline-none focus:ring-2 focus:ring-primary rounded"
                  aria-label={showConfirmPassword ? "Hide confirmation password" : "Show confirmation password"}
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {fieldErrors.password_confirm && (
                <p id="confirm-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.password_confirm}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Section 2: Farm & Location Profile Details (Optional) */}
        <div className="space-y-4 pt-2">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider pb-1 border-b border-border flex items-center justify-between">
            <span>Farm Details & Location (Optional)</span>
            <span className="text-[11px] font-normal lowercase text-muted-foreground">can be updated later</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Farm Name */}
            <div>
              <label htmlFor="farmer-farm-name" className="block text-xs font-medium text-foreground mb-1">
                Farm or Enterprise Name
              </label>
              <input
                id="farmer-farm-name"
                name="farm_name"
                type="text"
                value={formData.farm_name}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Patel Organic Farms"
              />
            </div>

            {/* Phone Number */}
            <div>
              <label htmlFor="farmer-phone" className="block text-xs font-medium text-foreground mb-1">
                Phone Number
              </label>
              <input
                id="farmer-phone"
                name="phone_number"
                type="tel"
                autoComplete="tel"
                value={formData.phone_number}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.phone_number ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="+91 98765 43210"
                aria-invalid={Boolean(fieldErrors.phone_number)}
                aria-describedby={fieldErrors.phone_number ? "farmer-phone-error" : undefined}
              />
              {fieldErrors.phone_number && (
                <p id="farmer-phone-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.phone_number}
                </p>
              )}
            </div>

            {/* Farm Location Address */}
            <div className="sm:col-span-2">
              <label htmlFor="farmer-address" className="block text-xs font-medium text-foreground mb-1">
                Farm Physical Address
              </label>
              <input
                id="farmer-address"
                name="farm_location_address"
                type="text"
                value={formData.farm_location_address}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Survey / Plot / Village address"
              />
            </div>

            {/* City / Town */}
            <div>
              <label htmlFor="farmer-city" className="block text-xs font-medium text-foreground mb-1">
                City / Nearest Town
              </label>
              <input
                id="farmer-city"
                name="city"
                type="text"
                value={formData.city}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Pune"
              />
            </div>

            {/* State */}
            <div>
              <label htmlFor="farmer-state" className="block text-xs font-medium text-foreground mb-1">
                State / Province
              </label>
              <input
                id="farmer-state"
                name="state"
                type="text"
                value={formData.state}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Maharashtra"
              />
            </div>

            {/* Postal Code */}
            <div>
              <label htmlFor="farmer-postal-code" className="block text-xs font-medium text-foreground mb-1">
                Postal Code
              </label>
              <input
                id="farmer-postal-code"
                name="postal_code"
                type="text"
                value={formData.postal_code}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. 411001"
              />
            </div>

            {/* Farm Size Acres */}
            <div>
              <label htmlFor="farmer-size" className="block text-xs font-medium text-foreground mb-1">
                Total Land Size (Acres)
              </label>
              <input
                id="farmer-size"
                name="farm_size_acres"
                type="number"
                step="0.1"
                min="0.1"
                value={formData.farm_size_acres ?? ""}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.farm_size_acres ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="e.g. 15.5"
                aria-invalid={Boolean(fieldErrors.farm_size_acres)}
                aria-describedby={fieldErrors.farm_size_acres ? "size-error" : undefined}
              />
              {fieldErrors.farm_size_acres && (
                <p id="size-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.farm_size_acres}
                </p>
              )}
            </div>

            {/* Farming Practices */}
            <div>
              <label htmlFor="farmer-practices" className="block text-xs font-medium text-foreground mb-1">
                Farming Practices
              </label>
              <select
                id="farmer-practices"
                name="farming_practices"
                value={formData.farming_practices}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="conventional">Conventional</option>
                <option value="organic">Organic / Bio-dynamic</option>
                <option value="regenerative">Regenerative Agriculture</option>
                <option value="hydroponic">Hydroponic / Protected</option>
                <option value="other">Other</option>
              </select>
            </div>

            {/* Primary Crops */}
            <div>
              <label htmlFor="farmer-crops" className="block text-xs font-medium text-foreground mb-1">
                Primary Crops
              </label>
              <input
                id="farmer-crops"
                name="primary_crops"
                type="text"
                value={formData.primary_crops}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Tomatoes, Onions, Potatoes"
              />
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                <span>Creating Farmer Account...</span>
              </>
            ) : (
              <>
                <span>Complete Farmer Registration</span>
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </>
            )}
          </button>
        </div>

        {/* Existing Account Footer Link */}
        <div className="pt-4 border-t border-border text-center text-xs text-muted-foreground">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-semibold text-primary hover:text-primary-800 underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
          >
            Sign in
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};
