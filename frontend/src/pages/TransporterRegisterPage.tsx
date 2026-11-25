import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff, AlertCircle, CheckCircle2, ArrowRight, Truck } from "lucide-react";
import { useAuth } from "../store/authStore";
import { AuthLayout } from "../components/layout/AuthLayout";
import { ApiError } from "../api/errors";
import type { TransporterRegisterRequest, User } from "../types";

export const TransporterRegisterPage: React.FC = () => {
  const { t } = useTranslation(["auth", "validation", "common", "delivery"]);
  const { registerTransporter } = useAuth();

  // Form state
  const [formData, setFormData] = useState<TransporterRegisterRequest & { password_confirm: string }>({
    email: "",
    password: "",
    password_confirm: "",
    phone_number: "",
    business_name: "",
    contact_name: "",
    transport_type: "mini_truck",
    vehicle_capacity_kg: 2000,
    vehicle_registration_number: "",
    experience_years: 2,
    operating_states: "",
    bio: "",
    initial_service_areas: [
      {
        state: "",
        district: "",
        coverage_type: "both",
        is_active: true,
      },
    ],
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Status & error tracking
  const [registeredUser, setRegisteredUser] = useState<User | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.contact_name.trim()) {
      errors.contact_name = t("validation:contact_name_required", "Contact person name is required.");
    }

    if (!formData.business_name.trim()) {
      errors.business_name = t("validation:business_name_required", "Business name is required.");
    }

    const trimmedEmail = formData.email.trim();
    if (!trimmedEmail) {
      errors.email = t("validation:email_required", "Email address is required.");
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = t("validation:invalid_email", "Please enter a valid email address.");
    }

    if (!formData.phone_number.trim()) {
      errors.phone_number = t("validation:phone_required", "Phone number is required.");
    }

    if (!formData.password) {
      errors.password = t("validation:password_required", "Password is required.");
    } else if (formData.password.length < 8) {
      errors.password = t("validation:password_too_short", "Password must be at least 8 characters long.");
    }

    if (formData.password !== formData.password_confirm) {
      errors.password_confirm = t("validation:password_mismatch", "Passwords do not match.");
    }

    if (!formData.vehicle_registration_number.trim()) {
      errors.vehicle_registration_number = t("validation:vehicle_reg_required", "Vehicle registration plate is required.");
    }

    if (!formData.vehicle_capacity_kg || formData.vehicle_capacity_kg <= 0) {
      errors.vehicle_capacity_kg = t("validation:capacity_positive", "Payload capacity must be greater than 0 kg.");
    }

    const primaryArea = formData.initial_service_areas?.[0];
    if (primaryArea && (!primaryArea.state.trim() || !primaryArea.district.trim())) {
      errors.service_area = t("validation:service_area_required", "Primary operating state and district are required.");
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
      const user = await registerTransporter({
        email: formData.email.trim(),
        password: formData.password,
        phone_number: formData.phone_number.trim(),
        business_name: formData.business_name.trim(),
        contact_name: formData.contact_name.trim(),
        transport_type: formData.transport_type,
        vehicle_capacity_kg: Number(formData.vehicle_capacity_kg),
        vehicle_registration_number: formData.vehicle_registration_number.trim(),
        experience_years: Number(formData.experience_years) || 0,
        operating_states: formData.operating_states?.trim() || undefined,
        bio: formData.bio?.trim() || undefined,
        initial_service_areas: formData.initial_service_areas?.filter(
          (a) => a.state.trim() && a.district.trim()
        ),
      });
      setRegisteredUser(user);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError(t("common:error_generic", "An unexpected error occurred during registration."));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (registeredUser) {
    return (
      <AuthLayout
        title={t("register.success_title", "Registration Successful!")}
        subtitle={t(
          "register.success_subtitle",
          "Your transportation provider account has been initialized"
        )}
      >
        <div className="space-y-6">
          <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-lg flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-emerald-800 dark:text-emerald-200 space-y-1">
              <p className="font-semibold">
                {t("register.account_created", "Account created for")}{" "}
                <span className="font-mono">{registeredUser.email}</span>
              </p>
              <p>
                {t(
                  "register.transporter_success_desc",
                  "You can now sign in to configure your service areas, manage fleet availability, and coordinate agricultural cargo transport with farmers and buyers."
                )}
              </p>
            </div>
          </div>

          <Link
            to="/login"
            className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            <span>{t("register.proceed_to_login", "Sign In to Your Account")}</span>
            <ArrowRight className="w-4 h-4 rtl:rotate-180" />
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={t("register.transporter_title", "Register as Transportation Provider")}
      subtitle={t(
        "register.transporter_page_subtitle",
        "Offer agricultural transport services directly to commercial buyers and farm producers"
      )}
      maxWidth="wide"
    >
      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        {formError && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-xs text-destructive">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        {/* Section 1: Business & Contact Info */}
        <div className="space-y-4">
          <div className="border-b border-border pb-2 flex items-center gap-2 text-foreground font-semibold text-sm">
            <Truck className="w-4 h-4 text-primary" />
            <span>{t("register.section_business", "Logistics & Contact Profile")}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.business_name", "Business / Fleet Name")} *
              </label>
              <input
                type="text"
                value={formData.business_name}
                onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Kisan Super Transport"
                disabled={isSubmitting}
              />
              {fieldErrors.business_name && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.business_name}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.contact_name", "Contact Person Name")} *
              </label>
              <input
                type="text"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Rajesh Patil"
                disabled={isSubmitting}
              />
              {fieldErrors.contact_name && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.contact_name}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.email", "Email Address")} *
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="transporter@example.com"
                disabled={isSubmitting}
              />
              {fieldErrors.email && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.email}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.phone", "Phone Number")} *
              </label>
              <input
                type="tel"
                value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="+91 98765 43210"
                disabled={isSubmitting}
              />
              {fieldErrors.phone_number && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.phone_number}</p>
              )}
            </div>
          </div>
        </div>

        {/* Section 2: Vehicle & Fleet Specifications */}
        <div className="space-y-4">
          <div className="border-b border-border pb-2 text-foreground font-semibold text-sm">
            {t("register.section_vehicle", "Vehicle & Fleet Capabilities")}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.transport_type", "Vehicle Type")} *
              </label>
              <select
                value={formData.transport_type}
                onChange={(e) => setFormData({ ...formData, transport_type: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              >
                <option value="mini_truck">{t("delivery:type_mini_truck", "Mini Truck (e.g. Tata Ace, Bolero Maxi)")}</option>
                <option value="open_body">{t("delivery:type_open_body", "Open Body Truck")}</option>
                <option value="refrigerated">{t("delivery:type_refrigerated", "Refrigerated / Cold-Chain Van")}</option>
                <option value="covered_truck">{t("delivery:type_covered_truck", "Covered Container Truck")}</option>
                <option value="tempo">{t("delivery:type_tempo", "Tempo / Three-Wheeler Loader")}</option>
                <option value="trailer">{t("delivery:type_trailer", "Trailer / Heavy Hauler")}</option>
                <option value="other">{t("delivery:type_other", "Other Commercial Vehicle")}</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.vehicle_capacity", "Payload Capacity (kg)")} *
              </label>
              <input
                type="number"
                min="50"
                step="50"
                value={formData.vehicle_capacity_kg}
                onChange={(e) => setFormData({ ...formData, vehicle_capacity_kg: Number(e.target.value) })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              />
              {fieldErrors.vehicle_capacity_kg && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.vehicle_capacity_kg}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.vehicle_reg", "Registration Plate Number")} *
              </label>
              <input
                type="text"
                value={formData.vehicle_registration_number}
                onChange={(e) => setFormData({ ...formData, vehicle_registration_number: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="MH-12-AB-1234"
                disabled={isSubmitting}
              />
              {fieldErrors.vehicle_registration_number && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.vehicle_registration_number}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.experience", "Years of Transport Experience")}
              </label>
              <input
                type="number"
                min="0"
                value={formData.experience_years}
                onChange={(e) => setFormData({ ...formData, experience_years: Number(e.target.value) })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.operating_states", "Operating States / Regions")}
              </label>
              <input
                type="text"
                value={formData.operating_states}
                onChange={(e) => setFormData({ ...formData, operating_states: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Maharashtra, Karnataka, Gujarat"
                disabled={isSubmitting}
              />
            </div>
          </div>
        </div>

        {/* Section 3: Primary Service Area */}
        <div className="space-y-4">
          <div className="border-b border-border pb-2 text-foreground font-semibold text-sm">
            {t("register.section_service_area", "Primary Operating Area")}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.state", "Base State")} *
              </label>
              <input
                type="text"
                value={formData.initial_service_areas?.[0]?.state || ""}
                onChange={(e) => {
                  const updated = [...(formData.initial_service_areas || [])];
                  if (!updated[0]) {
                    updated[0] = { state: "", district: "", coverage_type: "both", is_active: true };
                  }
                  updated[0].state = e.target.value;
                  setFormData({ ...formData, initial_service_areas: updated });
                }}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Maharashtra"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.district", "Base District")} *
              </label>
              <input
                type="text"
                value={formData.initial_service_areas?.[0]?.district || ""}
                onChange={(e) => {
                  const updated = [...(formData.initial_service_areas || [])];
                  if (!updated[0]) {
                    updated[0] = { state: "", district: "", coverage_type: "both", is_active: true };
                  }
                  updated[0].district = e.target.value;
                  setFormData({ ...formData, initial_service_areas: updated });
                }}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g. Pune"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.coverage_type", "Coverage Scope")}
              </label>
              <select
                value={formData.initial_service_areas?.[0]?.coverage_type || "both"}
                onChange={(e) => {
                  const updated = [...(formData.initial_service_areas || [])];
                  if (!updated[0]) {
                    updated[0] = { state: "", district: "", coverage_type: "both", is_active: true };
                  }
                  updated[0].coverage_type = e.target.value as "pickup_only" | "delivery_only" | "both";
                  setFormData({ ...formData, initial_service_areas: updated });
                }}
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              >
                <option value="both">Both Pickup & Delivery</option>
                <option value="pickup_only">Origin / Pickup Only</option>
                <option value="delivery_only">Destination / Delivery Only</option>
              </select>
            </div>
          </div>
          {fieldErrors.service_area && (
            <p className="text-xs text-destructive">{fieldErrors.service_area}</p>
          )}
        </div>

        {/* Section 4: Security Credentials */}
        <div className="space-y-4">
          <div className="border-b border-border pb-2 text-foreground font-semibold text-sm">
            {t("register.section_security", "Security Credentials")}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.password", "Password")} *
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary pe-9"
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute end-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {fieldErrors.password && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.password}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("register.confirm_password", "Confirm Password")} *
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={formData.password_confirm}
                  onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary pe-9"
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute end-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {fieldErrors.password_confirm && (
                <p className="mt-1 text-xs text-destructive">{fieldErrors.password_confirm}</p>
              )}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <span>{t("common:submitting", "Creating Account...")}</span>
          ) : (
            <>
              <span>{t("register.submit_transporter", "Complete Transporter Registration")}</span>
              <ArrowRight className="w-4 h-4 rtl:rotate-180" />
            </>
          )}
        </button>

        <div className="pt-2 text-center text-xs text-muted-foreground">
          {t("register.already_registered", "Already have an account?")}{" "}
          <Link to="/login" className="font-semibold text-primary hover:underline">
            {t("register.sign_in_link", "Sign in")}
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};
