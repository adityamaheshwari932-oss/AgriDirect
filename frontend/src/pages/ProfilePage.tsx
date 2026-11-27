import React, { useContext, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  User as UserIcon,
  Tractor,
  Store,
  ShieldCheck,
  Edit3,
  X,
  Save,
  AlertCircle,
  CheckCircle2,
  Lock,
  MapPin,
  Calendar,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { usersApi } from "../api/users";
import { ApiError } from "../api/errors";
import { ToastContext } from "../components/ui/toast/toastContextDef";
import {
  ACCOUNT_STATUS_CONFIG,
  BUYER_TYPE_LABELS,
  VERIFICATION_STATUS_CONFIG,
} from "../utils/status";
import { formatDate } from "../utils/formatters";
import type {
  BuyerProfileUpdate,
  FarmerProfileUpdate,
} from "../types";

const BUYER_TYPE_OPTIONS = [
  { value: "restaurant", label: "Restaurant / Dining" },
  { value: "hotel", label: "Hotel / Hospitality" },
  { value: "retailer", label: "Retailer / Supermarket" },
  { value: "wholesaler", label: "Wholesaler / Distributor" },
  { value: "food_processor", label: "Food Processor / Manufacturer" },
  { value: "caterer", label: "Caterer / Institutional Kitchen" },
  { value: "other", label: "Other Commercial Enterprise" },
];

export const ProfilePage: React.FC = () => {
  const { t } = useTranslation(["profile", "validation", "common"]);
  const { user, setUser } = useAuth();
  const toast = useContext(ToastContext);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Farmer form state
  const [farmerForm, setFarmerForm] = useState<FarmerProfileUpdate>({
    full_name: user?.farmer_profile?.full_name || "",
    farm_name: user?.farmer_profile?.farm_name || "",
    phone_number: user?.phone_number || "",
    farm_location_address: user?.farmer_profile?.farm_location_address || "",
    city: user?.farmer_profile?.city || "",
    state: user?.farmer_profile?.state || "",
    postal_code: user?.farmer_profile?.postal_code || "",
    farm_size_acres: user?.farmer_profile?.farm_size_acres ?? undefined,
    farming_practices: user?.farmer_profile?.farming_practices || "conventional",
    primary_crops: user?.farmer_profile?.primary_crops || "",
    bio: user?.farmer_profile?.bio || "",
  });

  // Buyer form state
  const [buyerForm, setBuyerForm] = useState<BuyerProfileUpdate>({
    contact_person_name: user?.buyer_profile?.contact_person_name || "",
    business_name: user?.buyer_profile?.business_name || "",
    business_type: user?.buyer_profile?.business_type || "restaurant",
    business_registration_number:
      user?.buyer_profile?.business_registration_number || "",
    phone_number: user?.phone_number || "",
    delivery_receiving_address:
      user?.buyer_profile?.delivery_receiving_address || "",
    city: user?.buyer_profile?.city || "",
    state: user?.buyer_profile?.state || "",
    postal_code: user?.buyer_profile?.postal_code || "",
    procurement_summary: user?.buyer_profile?.procurement_summary || "",
    bio: user?.buyer_profile?.bio || "",
  });

  if (!user) {
    return null;
  }

  const isFarmer = user.role === "farmer";

  const resetFormToCurrent = () => {
    setFarmerForm({
      full_name: user.farmer_profile?.full_name || "",
      farm_name: user.farmer_profile?.farm_name || "",
      phone_number: user.phone_number || "",
      farm_location_address: user.farmer_profile?.farm_location_address || "",
      city: user.farmer_profile?.city || "",
      state: user.farmer_profile?.state || "",
      postal_code: user.farmer_profile?.postal_code || "",
      farm_size_acres: user.farmer_profile?.farm_size_acres ?? undefined,
      farming_practices: user.farmer_profile?.farming_practices || "conventional",
      primary_crops: user.farmer_profile?.primary_crops || "",
      bio: user.farmer_profile?.bio || "",
    });

    setBuyerForm({
      contact_person_name: user.buyer_profile?.contact_person_name || "",
      business_name: user.buyer_profile?.business_name || "",
      business_type: user.buyer_profile?.business_type || "restaurant",
      business_registration_number:
        user.buyer_profile?.business_registration_number || "",
      phone_number: user.phone_number || "",
      delivery_receiving_address:
        user.buyer_profile?.delivery_receiving_address || "",
      city: user.buyer_profile?.city || "",
      state: user.buyer_profile?.state || "",
      postal_code: user.buyer_profile?.postal_code || "",
      procurement_summary: user.buyer_profile?.procurement_summary || "",
      bio: user.buyer_profile?.bio || "",
    });
    setFieldErrors({});
    setFormError(null);
  };

  const handleFarmerChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFarmerForm((prev) => ({
      ...prev,
      [name]:
        name === "farm_size_acres"
          ? value === ""
            ? undefined
            : Number(value)
          : value,
    }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleBuyerChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setBuyerForm((prev) => ({
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

  const validateFarmerForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!farmerForm.full_name?.trim()) {
      errors.full_name = t("validation:full_name_required", "Full name is required.");
    }

    if (
      farmerForm.farm_size_acres !== undefined &&
      farmerForm.farm_size_acres !== null &&
      Number(farmerForm.farm_size_acres) <= 0
    ) {
      errors.farm_size_acres = t("validation:acres_positive", "Farm size must be a positive number of acres.");
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateBuyerForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!buyerForm.contact_person_name?.trim()) {
      errors.contact_person_name = t("validation:contact_person_required", "Contact person name is required.");
    }

    if (!buyerForm.business_type?.trim()) {
      errors.business_type = t("validation:business_type_required", "Please select a commercial entity type.");
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveFarmer = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage(null);
    setFormError(null);

    if (!validateFarmerForm()) {
      return;
    }

    setIsSaving(true);
    try {
      const payload: FarmerProfileUpdate = {
        full_name: farmerForm.full_name?.trim() || undefined,
        farm_name: farmerForm.farm_name?.trim() || undefined,
        phone_number: farmerForm.phone_number?.trim() || undefined,
        farm_location_address: farmerForm.farm_location_address?.trim() || undefined,
        city: farmerForm.city?.trim() || undefined,
        state: farmerForm.state?.trim() || undefined,
        postal_code: farmerForm.postal_code?.trim() || undefined,
        farm_size_acres: farmerForm.farm_size_acres ?? undefined,
        farming_practices: farmerForm.farming_practices?.trim() || undefined,
        primary_crops: farmerForm.primary_crops?.trim() || undefined,
        bio: farmerForm.bio?.trim() || undefined,
      };

      const updatedUser = await usersApi.updateFarmerProfile(payload);
      setUser(updatedUser);
      setSuccessMessage(t("profile:toast_farmer_updated", "Farm profile updated successfully."));
      toast?.success(t("profile:toast_farmer_updated", "Farm profile updated successfully."), "Profile Updated");
      setIsEditing(false);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isConflict) {
          const msg = err.message || t("validation:phone_conflict", "This phone number is already registered to another account.");
          setFormError(msg);
          setFieldErrors({ phone_number: t("validation:phone_in_use", "Phone number already in use") });
          toast?.error(msg, "Conflict Error");
        } else if (err.isValidationError) {
          setFormError(t("validation:error_highlighted", "Validation error: please check highlighted fields."));
          toast?.warning(t("validation:error_highlighted", "Validation error: please check highlighted fields."), "Validation Failed");
          const backendErrors: Record<string, string> = {};
          for (const [key, msgs] of Object.entries(err.fieldErrors)) {
            backendErrors[key] = msgs[0];
          }
          setFieldErrors(backendErrors);
        } else if (err.isNetworkError) {
          setFormError(t("common:errors.network", "Network error: Unable to reach AgriDirect servers. Please check your connection."));
        } else {
          setFormError(err.message || t("profile:error_update", "Failed to update profile. Please try again."));
        }
      } else {
        setFormError(t("common:errors.unexpected", "An unexpected error occurred while saving your profile."));
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveBuyer = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage(null);
    setFormError(null);

    if (!validateBuyerForm()) {
      return;
    }

    setIsSaving(true);
    try {
      const payload: BuyerProfileUpdate = {
        contact_person_name: buyerForm.contact_person_name?.trim() || undefined,
        business_name: buyerForm.business_name?.trim() || undefined,
        business_type: buyerForm.business_type?.trim() || undefined,
        business_registration_number:
          buyerForm.business_registration_number?.trim() || undefined,
        phone_number: buyerForm.phone_number?.trim() || undefined,
        delivery_receiving_address:
          buyerForm.delivery_receiving_address?.trim() || undefined,
        city: buyerForm.city?.trim() || undefined,
        state: buyerForm.state?.trim() || undefined,
        postal_code: buyerForm.postal_code?.trim() || undefined,
        procurement_summary: buyerForm.procurement_summary?.trim() || undefined,
        bio: buyerForm.bio?.trim() || undefined,
      };

      const updatedUser = await usersApi.updateBuyerProfile(payload);
      setUser(updatedUser);
      setSuccessMessage(t("profile:toast_buyer_updated", "Commercial business profile updated successfully."));
      toast?.success(t("profile:toast_buyer_updated", "Commercial business profile updated successfully."), "Profile Updated");
      setIsEditing(false);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isConflict) {
          const msg = err.message || t("validation:phone_conflict", "This phone number is already registered to another account.");
          setFormError(msg);
          setFieldErrors({ phone_number: t("validation:phone_in_use", "Phone number already in use") });
          toast?.error(msg, "Conflict Error");
        } else if (err.isValidationError) {
          setFormError(t("validation:error_highlighted", "Validation error: please check highlighted fields."));
          toast?.warning(t("validation:error_highlighted", "Validation error: please check highlighted fields."), "Validation Failed");
          const backendErrors: Record<string, string> = {};
          for (const [key, msgs] of Object.entries(err.fieldErrors)) {
            backendErrors[key] = msgs[0];
          }
          setFieldErrors(backendErrors);
        } else if (err.isNetworkError) {
          setFormError(t("common:errors.network", "Network error: Unable to reach AgriDirect servers. Please check your connection."));
        } else {
          setFormError(err.message || t("profile:error_update", "Failed to update profile. Please try again."));
        }
      } else {
        setFormError(t("common:errors.unexpected", "An unexpected error occurred while saving your profile."));
      }
    } finally {
      setIsSaving(false);
    }
  };

  const verificationConfig =
    VERIFICATION_STATUS_CONFIG[user.verification_status] ||
    VERIFICATION_STATUS_CONFIG.unverified;
  const accountStatusConfig =
    ACCOUNT_STATUS_CONFIG[user.account_status] || ACCOUNT_STATUS_CONFIG.active;

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            {t("profile:title", "Account & Commercial Profile")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("profile:subtitle", "Manage your personal credentials, contact details, and commercial trading information")}
          </p>
        </div>

        {!isEditing ? (
          <button
            type="button"
            onClick={() => {
              setSuccessMessage(null);
              setIsEditing(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs sm:text-sm hover:bg-primary-700 transition-colors shadow-xs focus:outline-none focus:ring-2 focus:ring-primary self-start sm:self-auto"
          >
            <Edit3 className="w-4 h-4" aria-hidden="true" />
            <span>{t("profile:edit_profile", "Edit Profile")}</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={() => {
              resetFormToCurrent();
              setIsEditing(false);
            }}
            disabled={isSaving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card text-foreground font-medium text-xs sm:text-sm hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary self-start sm:self-auto"
          >
            <X className="w-4 h-4" aria-hidden="true" />
            <span>{t("common:actions.cancel", "Cancel")}</span>
          </button>
        )}
      </div>

      {/* Success Banner */}
      {successMessage && (
        <div
          className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3 text-emerald-800 text-sm animate-in fade-in"
          role="status"
        >
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" aria-hidden="true" />
          <span className="font-medium">{successMessage}</span>
        </div>
      )}

      {/* Error Alert */}
      {formError && (
        <div
          className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-800 text-sm animate-in fade-in"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>{formError}</span>
        </div>
      )}

      {/* Protected Server-Controlled Information Card */}
      <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 bg-secondary/30 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
            <Lock className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
            <span>{t("profile:server_attributes", "Server-Managed Security Attributes")}</span>
          </div>
          <span className="text-xs text-muted-foreground font-normal">
            {t("profile:server_attributes_desc", "Controlled by system authorization")}
          </span>
        </div>

        <div className="p-5 sm:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 text-sm">
          {/* User ID */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
              {t("profile:account_id", "Account ID")}
            </span>
            <div className="font-mono text-xs text-foreground truncate" title={user.id}>
              {user.id}
            </div>
          </div>

          {/* Email Address */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
              {t("profile:registered_email", "Registered Email")}
            </span>
            <div className="font-medium text-foreground truncate" title={user.email}>
              {user.email}
            </div>
          </div>

          {/* Verification Status */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
              {t("profile:verification_status", "Verification Status")}
            </span>
            <div>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${verificationConfig.badgeClass}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${verificationConfig.dotClass}`} aria-hidden="true" />
                <span>{verificationConfig.label}</span>
              </span>
              <Link
                to="/dashboard/verification"
                className="text-[11px] font-semibold text-primary hover:text-primary-800 hover:underline block mt-1"
              >
                {t("profile:view_verification_evidence", "View Verification Evidence →")}
              </Link>
            </div>
          </div>

          {/* Account Status */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
              {t("profile:account_status", "Account Status")}
            </span>
            <div>
              <span
                className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium border ${accountStatusConfig.badgeClass} capitalize`}
              >
                {accountStatusConfig.label}
              </span>
            </div>
          </div>

          {/* Role */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
              {t("profile:authorized_role", "Authorized Role")}
            </span>
            <div className="font-semibold capitalize text-foreground flex items-center gap-1.5">
              {isFarmer ? (
                <>
                  <Tractor className="w-4 h-4 text-primary" aria-hidden="true" />
                  <span>{t("profile:agricultural_producer", "Agricultural Producer")}</span>
                </>
              ) : (
                <>
                  <Store className="w-4 h-4 text-harvest-600" aria-hidden="true" />
                  <span>{t("profile:commercial_bulk_buyer", "Commercial Bulk Buyer")}</span>
                </>
              )}
            </div>
          </div>

          {/* Member Since */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
              {t("profile:member_since", "Member Since")}
            </span>
            <div className="text-foreground text-xs flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
              <span>{formatDate(user.created_at)}</span>
            </div>
          </div>

          {/* Verification Portal Action */}
          <div className="sm:col-span-2 flex items-center">
            <Link
              to="/dashboard/verification"
              className="text-xs font-semibold text-primary hover:text-primary-800 transition-colors inline-flex items-center gap-1"
            >
              <span>{t("profile:view_verification_requirements", "View Verification Requirements")}</span>
              <ShieldCheck className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>

      {/* View Mode */}
      {!isEditing ? (
        <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden">
          <div className="p-5 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <UserIcon className="w-5 h-5 text-primary" aria-hidden="true" />
              <h2 className="text-base font-bold text-foreground">
                {isFarmer ? "Producer & Farm Information" : "Commercial Entity Information"}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => {
                setSuccessMessage(null);
                setIsEditing(true);
              }}
              className="text-xs font-semibold text-primary hover:text-primary-800 transition-colors inline-flex items-center gap-1"
            >
              <span>Edit Attributes</span>
              <Edit3 className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>

          {isFarmer ? (
            <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 text-sm">
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Farmer Full Name
                </span>
                <div className="font-semibold text-foreground">
                  {user.farmer_profile?.full_name || <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Farm Name
                </span>
                <div className="font-semibold text-foreground">
                  {user.farmer_profile?.farm_name || <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Cultivated Acres
                </span>
                <div className="font-semibold text-foreground">
                  {user.farmer_profile?.farm_size_acres ? `${user.farmer_profile.farm_size_acres} Acres` : <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Phone Number
                </span>
                <div className="font-semibold text-foreground">
                  {user.phone_number || <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1 sm:col-span-2">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Farm Location & Address
                </span>
                <div className="text-foreground">
                  {user.farmer_profile?.farm_location_address || <span className="text-muted-foreground italic font-normal">Address not specified</span>}
                </div>
                {(user.farmer_profile?.city || user.farmer_profile?.state) && (
                  <div className="text-xs text-muted-foreground flex items-center gap-1 pt-0.5">
                    <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>
                      {[user.farmer_profile.city, user.farmer_profile.state, user.farmer_profile.postal_code].filter(Boolean).join(", ")}
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Primary Crops Produced
                </span>
                <div className="text-foreground">
                  {user.farmer_profile?.primary_crops || <span className="text-muted-foreground italic font-normal">None specified</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Farming Practices
                </span>
                <div>
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-foreground capitalize">
                    {user.farmer_profile?.farming_practices || "Conventional"}
                  </span>
                </div>
              </div>

              {user.farmer_profile?.bio && (
                <div className="space-y-1 sm:col-span-3 pt-4 border-t border-border">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Farm Overview & Biography
                  </span>
                  <p className="text-sm text-foreground bg-secondary/30 p-3.5 rounded-lg border border-border leading-relaxed">
                    {user.farmer_profile.bio}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 text-sm">
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Procurement Contact Person
                </span>
                <div className="font-semibold text-foreground">
                  {user.buyer_profile?.contact_person_name || <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Business / Trade Name
                </span>
                <div className="font-semibold text-foreground">
                  {user.buyer_profile?.business_name || <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Commercial Entity Type
                </span>
                <div>
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-foreground border border-border">
                    {user.buyer_profile?.business_type && BUYER_TYPE_LABELS[user.buyer_profile.business_type]
                      ? BUYER_TYPE_LABELS[user.buyer_profile.business_type]
                      : user.buyer_profile?.business_type || "Commercial Enterprise"}
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Contact Phone
                </span>
                <div className="font-semibold text-foreground">
                  {user.phone_number || <span className="text-muted-foreground italic font-normal">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Tax / Registration ID (GSTIN/CIN)
                </span>
                <div className="font-mono text-xs text-foreground">
                  {user.buyer_profile?.business_registration_number || <span className="text-muted-foreground italic font-normal font-sans">Not provided</span>}
                </div>
              </div>

              <div className="space-y-1 sm:col-span-2">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Delivery Receiving Address
                </span>
                <div className="text-foreground">
                  {user.buyer_profile?.delivery_receiving_address || <span className="text-muted-foreground italic font-normal">Address not specified</span>}
                </div>
                {(user.buyer_profile?.city || user.buyer_profile?.state) && (
                  <div className="text-xs text-muted-foreground flex items-center gap-1 pt-0.5">
                    <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>
                      {[user.buyer_profile.city, user.buyer_profile.state, user.buyer_profile.postal_code].filter(Boolean).join(", ")}
                    </span>
                  </div>
                )}
              </div>

              {user.buyer_profile?.procurement_summary && (
                <div className="space-y-1 sm:col-span-3 pt-4 border-t border-border">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Procurement Requirements Summary
                  </span>
                  <p className="text-sm text-foreground bg-secondary/30 p-3.5 rounded-lg border border-border leading-relaxed">
                    {user.buyer_profile.procurement_summary}
                  </p>
                </div>
              )}

              {user.buyer_profile?.bio && (
                <div className="space-y-1 sm:col-span-3 pt-2">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Business Bio / Overview
                  </span>
                  <p className="text-sm text-foreground bg-secondary/30 p-3.5 rounded-lg border border-border leading-relaxed">
                    {user.buyer_profile.bio}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Edit Mode */
        <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden">
          <div className="p-5 border-b border-border flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Edit3 className="w-4 h-4 text-primary" aria-hidden="true" />
              <span>{isFarmer ? "Edit Farm & Producer Attributes" : "Edit Commercial Entity Attributes"}</span>
            </h2>
            <span className="text-xs text-muted-foreground">* indicates required field</span>
          </div>

          {isFarmer ? (
            <form onSubmit={handleSaveFarmer} className="p-6 space-y-6" noValidate>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Farmer Full Name */}
                <div>
                  <label htmlFor="edit-farmer-name" className="block text-xs font-medium text-foreground mb-1">
                    Producer Full Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="edit-farmer-name"
                    name="full_name"
                    type="text"
                    value={farmerForm.full_name || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                      fieldErrors.full_name ? "border-red-400 focus:ring-red-400" : "border-border"
                    }`}
                    aria-invalid={Boolean(fieldErrors.full_name)}
                    aria-describedby={fieldErrors.full_name ? "farmer-name-error" : undefined}
                  />
                  {fieldErrors.full_name && (
                    <p id="farmer-name-error" className="mt-1 text-xs text-red-600">
                      {fieldErrors.full_name}
                    </p>
                  )}
                </div>

                {/* Farm Name */}
                <div>
                  <label htmlFor="edit-farm-name" className="block text-xs font-medium text-foreground mb-1">
                    Farm or Enterprise Name
                  </label>
                  <input
                    id="edit-farm-name"
                    name="farm_name"
                    type="text"
                    value={farmerForm.farm_name || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Green Valley Organic"
                  />
                </div>

                {/* Phone Number */}
                <div>
                  <label htmlFor="edit-farmer-phone" className="block text-xs font-medium text-foreground mb-1">
                    Contact Phone Number
                  </label>
                  <input
                    id="edit-farmer-phone"
                    name="phone_number"
                    type="tel"
                    value={farmerForm.phone_number || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
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

                {/* Land Size (Acres) */}
                <div>
                  <label htmlFor="edit-farmer-acres" className="block text-xs font-medium text-foreground mb-1">
                    Cultivated Area (Acres)
                  </label>
                  <input
                    id="edit-farmer-acres"
                    name="farm_size_acres"
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={farmerForm.farm_size_acres ?? ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                      fieldErrors.farm_size_acres ? "border-red-400 focus:ring-red-400" : "border-border"
                    }`}
                    placeholder="e.g. 25.5"
                    aria-invalid={Boolean(fieldErrors.farm_size_acres)}
                    aria-describedby={fieldErrors.farm_size_acres ? "farmer-acres-error" : undefined}
                  />
                  {fieldErrors.farm_size_acres && (
                    <p id="farmer-acres-error" className="mt-1 text-xs text-red-600">
                      {fieldErrors.farm_size_acres}
                    </p>
                  )}
                </div>

                {/* Farming Practices */}
                <div>
                  <label htmlFor="edit-farmer-practices" className="block text-xs font-medium text-foreground mb-1">
                    Farming Practices
                  </label>
                  <select
                    id="edit-farmer-practices"
                    name="farming_practices"
                    value={farmerForm.farming_practices || "conventional"}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
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
                  <label htmlFor="edit-farmer-crops" className="block text-xs font-medium text-foreground mb-1">
                    Primary Produce & Crops
                  </label>
                  <input
                    id="edit-farmer-crops"
                    name="primary_crops"
                    type="text"
                    value={farmerForm.primary_crops || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Wheat, Basmati Rice, Tomatoes"
                  />
                </div>

                {/* Farm Location Address */}
                <div className="sm:col-span-2">
                  <label htmlFor="edit-farmer-address" className="block text-xs font-medium text-foreground mb-1">
                    Physical Farm / Survey Address
                  </label>
                  <input
                    id="edit-farmer-address"
                    name="farm_location_address"
                    type="text"
                    value={farmerForm.farm_location_address || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Plot / Survey / Village details"
                  />
                </div>

                {/* City */}
                <div>
                  <label htmlFor="edit-farmer-city" className="block text-xs font-medium text-foreground mb-1">
                    City / Nearest Town
                  </label>
                  <input
                    id="edit-farmer-city"
                    name="city"
                    type="text"
                    value={farmerForm.city || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Nashik"
                  />
                </div>

                {/* State */}
                <div>
                  <label htmlFor="edit-farmer-state" className="block text-xs font-medium text-foreground mb-1">
                    State / Province
                  </label>
                  <input
                    id="edit-farmer-state"
                    name="state"
                    type="text"
                    value={farmerForm.state || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Maharashtra"
                  />
                </div>

                {/* Postal Code */}
                <div>
                  <label htmlFor="edit-farmer-postal" className="block text-xs font-medium text-foreground mb-1">
                    Postal Code
                  </label>
                  <input
                    id="edit-farmer-postal"
                    name="postal_code"
                    type="text"
                    value={farmerForm.postal_code || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. 422001"
                  />
                </div>

                {/* Bio */}
                <div className="sm:col-span-2">
                  <label htmlFor="edit-farmer-bio" className="block text-xs font-medium text-foreground mb-1">
                    Farm Overview & Narrative
                  </label>
                  <textarea
                    id="edit-farmer-bio"
                    name="bio"
                    rows={3}
                    value={farmerForm.bio || ""}
                    onChange={handleFarmerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
                    placeholder="Briefly describe your agricultural operation and cultivation philosophy..."
                  />
                </div>
              </div>

              {/* Form Actions */}
              <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    resetFormToCurrent();
                    setIsEditing(false);
                  }}
                  disabled={isSaving}
                  className="px-4 py-2 rounded-lg border border-border bg-card text-foreground font-medium text-xs sm:text-sm hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {t("common:actions.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs sm:text-sm hover:bg-primary-700 transition-colors shadow-xs focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isSaving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                      <span>{t("profile:saving_changes", "Saving Changes...")}</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" aria-hidden="true" />
                      <span>{t("profile:save_changes", "Save Changes")}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleSaveBuyer} className="p-6 space-y-6" noValidate>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Contact Person Name */}
                <div>
                  <label htmlFor="edit-buyer-contact" className="block text-xs font-medium text-foreground mb-1">
                    Contact Person Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="edit-buyer-contact"
                    name="contact_person_name"
                    type="text"
                    value={buyerForm.contact_person_name || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className={`w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                      fieldErrors.contact_person_name ? "border-red-400 focus:ring-red-400" : "border-border"
                    }`}
                    aria-invalid={Boolean(fieldErrors.contact_person_name)}
                    aria-describedby={fieldErrors.contact_person_name ? "buyer-contact-error" : undefined}
                  />
                  {fieldErrors.contact_person_name && (
                    <p id="buyer-contact-error" className="mt-1 text-xs text-red-600">
                      {fieldErrors.contact_person_name}
                    </p>
                  )}
                </div>

                {/* Business / Trade Name */}
                <div>
                  <label htmlFor="edit-buyer-business-name" className="block text-xs font-medium text-foreground mb-1">
                    Registered Business / Trade Name
                  </label>
                  <input
                    id="edit-buyer-business-name"
                    name="business_name"
                    type="text"
                    value={buyerForm.business_name || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Apex Hospitality"
                  />
                </div>

                {/* Commercial Entity Type */}
                <div>
                  <label htmlFor="edit-buyer-type" className="block text-xs font-medium text-foreground mb-1">
                    Commercial Entity Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="edit-buyer-type"
                    name="business_type"
                    value={buyerForm.business_type || "restaurant"}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {BUYER_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Tax / Registration ID */}
                <div>
                  <label htmlFor="edit-buyer-reg-number" className="block text-xs font-medium text-foreground mb-1">
                    Tax / Registration ID (GSTIN/CIN)
                  </label>
                  <input
                    id="edit-buyer-reg-number"
                    name="business_registration_number"
                    type="text"
                    value={buyerForm.business_registration_number || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. 27AAAAA0000A1Z5"
                  />
                </div>

                {/* Contact Phone */}
                <div>
                  <label htmlFor="edit-buyer-phone" className="block text-xs font-medium text-foreground mb-1">
                    Contact Phone Number
                  </label>
                  <input
                    id="edit-buyer-phone"
                    name="phone_number"
                    type="tel"
                    value={buyerForm.phone_number || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
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
                  <label htmlFor="edit-buyer-address" className="block text-xs font-medium text-foreground mb-1">
                    Delivery Receiving Address / Facility Dock
                  </label>
                  <input
                    id="edit-buyer-address"
                    name="delivery_receiving_address"
                    type="text"
                    value={buyerForm.delivery_receiving_address || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Warehouse / Dock / Kitchen delivery address"
                  />
                </div>

                {/* City */}
                <div>
                  <label htmlFor="edit-buyer-city" className="block text-xs font-medium text-foreground mb-1">
                    City / Municipality
                  </label>
                  <input
                    id="edit-buyer-city"
                    name="city"
                    type="text"
                    value={buyerForm.city || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Mumbai"
                  />
                </div>

                {/* State */}
                <div>
                  <label htmlFor="edit-buyer-state" className="block text-xs font-medium text-foreground mb-1">
                    State / Province
                  </label>
                  <input
                    id="edit-buyer-state"
                    name="state"
                    type="text"
                    value={buyerForm.state || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Maharashtra"
                  />
                </div>

                {/* Postal Code */}
                <div>
                  <label htmlFor="edit-buyer-postal" className="block text-xs font-medium text-foreground mb-1">
                    Postal Code
                  </label>
                  <input
                    id="edit-buyer-postal"
                    name="postal_code"
                    type="text"
                    value={buyerForm.postal_code || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. 400001"
                  />
                </div>

                {/* Procurement Summary */}
                <div className="sm:col-span-2">
                  <label htmlFor="edit-buyer-procurement" className="block text-xs font-medium text-foreground mb-1">
                    Procurement Interests & Volume Needs
                  </label>
                  <input
                    id="edit-buyer-procurement"
                    name="procurement_summary"
                    type="text"
                    value={buyerForm.procurement_summary || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g. Weekly bulk requirements for fresh onions, tomatoes, and leafy greens"
                  />
                </div>

                {/* Bio */}
                <div className="sm:col-span-2">
                  <label htmlFor="edit-buyer-bio" className="block text-xs font-medium text-foreground mb-1">
                    Commercial Entity Overview / Bio
                  </label>
                  <textarea
                    id="edit-buyer-bio"
                    name="bio"
                    rows={3}
                    value={buyerForm.bio || ""}
                    onChange={handleBuyerChange}
                    disabled={isSaving}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
                    placeholder="Brief overview of your commercial business or restaurant chain..."
                  />
                </div>
              </div>

              {/* Form Actions */}
              <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    resetFormToCurrent();
                    setIsEditing(false);
                  }}
                  disabled={isSaving}
                  className="px-4 py-2 rounded-lg border border-border bg-card text-foreground font-medium text-xs sm:text-sm hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {t("common:actions.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-harvest-600 text-white font-semibold text-xs sm:text-sm hover:bg-harvest-700 transition-colors shadow-xs focus:outline-none focus:ring-2 focus:ring-harvest-600 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isSaving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>{t("profile:saving_changes", "Saving Changes...")}</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" aria-hidden="true" />
                      <span>{t("profile:save_changes", "Save Changes")}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
};
