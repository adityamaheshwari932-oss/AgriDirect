import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, AlertCircle, CheckCircle2, ArrowRight, Store } from "lucide-react";
import { useAuth } from "../store/authStore";
import { AuthLayout } from "../components/layout/AuthLayout";
import { ApiError } from "../api/errors";
import type { BuyerRegisterRequest, User } from "../types";

const BUSINESS_TYPE_OPTIONS = [
  { value: "restaurant", label: "Restaurant / Dining" },
  { value: "hotel", label: "Hotel / Hospitality" },
  { value: "retailer", label: "Retailer / Supermarket" },
  { value: "wholesaler", label: "Wholesaler / Distributor" },
  { value: "food_processor", label: "Food Processor / Manufacturer" },
  { value: "caterer", label: "Caterer / Institutional Kitchen" },
  { value: "other", label: "Other Commercial Enterprise" },
];

export const BuyerRegisterPage: React.FC = () => {
  const { registerBuyer } = useAuth();

  // Form State
  const [formData, setFormData] = useState<BuyerRegisterRequest>({
    contact_person_name: "",
    email: "",
    password: "",
    password_confirm: "",
    business_name: "",
    business_type: "restaurant",
    business_registration_number: "",
    phone_number: "",
    delivery_receiving_address: "",
    city: "",
    state: "",
    postal_code: "",
    procurement_summary: "",
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

    if (!formData.contact_person_name?.trim()) {
      errors.contact_person_name = "Contact person name is required.";
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

    if (!formData.business_type) {
      errors.business_type = "Please select a commercial business type.";
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
      [name]: value,
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
      const payload: BuyerRegisterRequest = {
        ...formData,
        email: formData.email.trim().toLowerCase(),
        contact_person_name: formData.contact_person_name?.trim(),
        full_name: formData.contact_person_name?.trim(),
        business_name: formData.business_name?.trim() || undefined,
        business_type: formData.business_type,
        business_registration_number: formData.business_registration_number?.trim() || undefined,
        phone_number: formData.phone_number?.trim() || undefined,
        delivery_receiving_address: formData.delivery_receiving_address?.trim() || undefined,
        city: formData.city?.trim() || undefined,
        state: formData.state?.trim() || undefined,
        postal_code: formData.postal_code?.trim() || undefined,
        procurement_summary: formData.procurement_summary?.trim() || undefined,
        bio: formData.bio?.trim() || undefined,
      };

      const user = await registerBuyer(payload);
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
        title="Commercial Account Created"
        subtitle="Your commercial buyer registration has been recorded"
      >
        <div className="text-center space-y-6 py-4">
          <div className="w-16 h-16 rounded-full bg-harvest-100 text-harvest-700 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-9 h-9" aria-hidden="true" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-foreground">
              Welcome, {registeredUser.buyer_profile?.contact_person_name || registeredUser.email}!
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-md mx-auto">
              Your commercial buyer account has been created with status{" "}
              <span className="font-semibold text-harvest-800 bg-harvest-50 px-2 py-0.5 rounded border border-harvest-200 text-xs">
                {registeredUser.verification_status}
              </span>
              . You may now sign in. Produce procurement orders and requirement postings will be unlocked once business entity verification is completed.
            </p>
          </div>

          <div className="pt-4">
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 py-2.5 px-6 rounded-lg bg-harvest-600 text-white font-semibold text-sm hover:bg-harvest-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-harvest-600 focus:ring-offset-2 w-full sm:w-auto"
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
      title="Commercial Buyer Registration"
      subtitle="Register your business enterprise to procure bulk agricultural produce directly"
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

        {/* Section 1: Credentials & Contact Person (Required) */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider pb-1 border-b border-border flex items-center gap-2">
            <Store className="w-4 h-4 text-harvest-600" aria-hidden="true" />
            <span>Account Credentials & Business Type (Required)</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Contact Person Name */}
            <div>
              <label htmlFor="buyer-contact-name" className="block text-xs font-medium text-foreground mb-1">
                Contact Person Name <span className="text-red-500">*</span>
              </label>
              <input
                id="buyer-contact-name"
                name="contact_person_name"
                type="text"
                autoComplete="name"
                value={formData.contact_person_name}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.contact_person_name ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="e.g. Sita Sharma"
                aria-invalid={Boolean(fieldErrors.contact_person_name)}
                aria-describedby={fieldErrors.contact_person_name ? "contact-error" : undefined}
              />
              {fieldErrors.contact_person_name && (
                <p id="contact-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.contact_person_name}
                </p>
              )}
            </div>

            {/* Email Address */}
            <div>
              <label htmlFor="buyer-email" className="block text-xs font-medium text-foreground mb-1">
                Commercial Email <span className="text-red-500">*</span>
              </label>
              <input
                id="buyer-email"
                name="email"
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.email ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="procurement@enterprise.com"
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
              />
              {fieldErrors.email && (
                <p id="email-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            {/* Business Type */}
            <div className="sm:col-span-2">
              <label htmlFor="buyer-business-type" className="block text-xs font-medium text-foreground mb-1">
                Commercial Entity Type <span className="text-red-500">*</span>
              </label>
              <select
                id="buyer-business-type"
                name="business_type"
                value={formData.business_type}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {BUSINESS_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Password */}
            <div>
              <label htmlFor="buyer-password" className="block text-xs font-medium text-foreground mb-1">
                Password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="buyer-password"
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
              <label htmlFor="buyer-password-confirm" className="block text-xs font-medium text-foreground mb-1">
                Confirm Password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="buyer-password-confirm"
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

        {/* Section 2: Business & Receiving Location Details (Optional) */}
        <div className="space-y-4 pt-2">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider pb-1 border-b border-border flex items-center justify-between">
            <span>Business Entity Details (Optional)</span>
            <span className="text-[11px] font-normal lowercase text-muted-foreground">can be updated later</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Business Name */}
            <div>
              <label htmlFor="buyer-business-name" className="block text-xs font-medium text-foreground mb-1">
                Registered Business / Trade Name
              </label>
              <input
                id="buyer-business-name"
                name="business_name"
                type="text"
                value={formData.business_name}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Taj Hospitality Group"
              />
            </div>

            {/* Business Registration Number */}
            <div>
              <label htmlFor="buyer-reg-number" className="block text-xs font-medium text-foreground mb-1">
                Tax / Business Registration ID (GSTIN/CIN)
              </label>
              <input
                id="buyer-reg-number"
                name="business_registration_number"
                type="text"
                value={formData.business_registration_number}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.business_registration_number ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="e.g. 27AAAAA0000A1Z5"
                aria-invalid={Boolean(fieldErrors.business_registration_number)}
                aria-describedby={fieldErrors.business_registration_number ? "buyer-reg-error" : undefined}
              />
              {fieldErrors.business_registration_number && (
                <p id="buyer-reg-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.business_registration_number}
                </p>
              )}
            </div>

            {/* Phone Number */}
            <div>
              <label htmlFor="buyer-phone" className="block text-xs font-medium text-foreground mb-1">
                Contact Phone
              </label>
              <input
                id="buyer-phone"
                name="phone_number"
                type="tel"
                autoComplete="tel"
                value={formData.phone_number}
                onChange={handleChange}
                disabled={isSubmitting}
                className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  fieldErrors.phone_number ? "border-red-400 focus:ring-red-400" : "border-border"
                }`}
                placeholder="+91 22 1234 5678"
                aria-invalid={Boolean(fieldErrors.phone_number)}
                aria-describedby={fieldErrors.phone_number ? "buyer-phone-error" : undefined}
              />
              {fieldErrors.phone_number && (
                <p id="buyer-phone-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.phone_number}
                </p>
              )}
            </div>

            {/* Delivery Receiving Address */}
            <div className="sm:col-span-2">
              <label htmlFor="buyer-delivery-address" className="block text-xs font-medium text-foreground mb-1">
                Receiving Dock / Delivery Address
              </label>
              <input
                id="buyer-delivery-address"
                name="delivery_receiving_address"
                type="text"
                value={formData.delivery_receiving_address}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Dock / Warehouse / Kitchen address"
              />
            </div>

            {/* City */}
            <div>
              <label htmlFor="buyer-city" className="block text-xs font-medium text-foreground mb-1">
                City
              </label>
              <input
                id="buyer-city"
                name="city"
                type="text"
                value={formData.city}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Mumbai"
              />
            </div>

            {/* State */}
            <div>
              <label htmlFor="buyer-state" className="block text-xs font-medium text-foreground mb-1">
                State / Province
              </label>
              <input
                id="buyer-state"
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
              <label htmlFor="buyer-postal-code" className="block text-xs font-medium text-foreground mb-1">
                Postal Code
              </label>
              <input
                id="buyer-postal-code"
                name="postal_code"
                type="text"
                value={formData.postal_code}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. 400001"
              />
            </div>

            {/* Procurement Summary */}
            <div className="sm:col-span-2">
              <label htmlFor="buyer-procurement" className="block text-xs font-medium text-foreground mb-1">
                Procurement Overview & Produce Interests
              </label>
              <input
                id="buyer-procurement"
                name="procurement_summary"
                type="text"
                value={formData.procurement_summary}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Weekly bulk requirements for fresh onions, tomatoes, and leafy greens"
              />
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 rounded-lg bg-harvest-600 text-white font-semibold text-sm hover:bg-harvest-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-harvest-600 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Creating Commercial Account...</span>
              </>
            ) : (
              <>
                <span>Complete Commercial Buyer Registration</span>
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
