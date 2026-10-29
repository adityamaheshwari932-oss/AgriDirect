import React from "react";
import { Link } from "react-router-dom";
import {
  Store,
  MapPin,
  Building,
  Phone,
  Mail,
  Calendar,
  FileText,
  User as UserIcon,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Truck,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { VerificationSummaryCard } from "../components/ui/VerificationSummaryCard";
import { ProfileCompletionCard } from "../components/ui/ProfileCompletionCard";
import { ACCOUNT_STATUS_CONFIG, BUYER_TYPE_LABELS } from "../utils/status";

export const BuyerDashboardPage: React.FC = () => {
  const { user } = useAuth();

  if (!user || user.role !== "buyer") {
    return null;
  }

  const profile = user.buyer_profile;
  const buyerName =
    profile?.contact_person_name || profile?.business_name || user.email;
  const businessTypeLabel =
    profile?.business_type && BUYER_TYPE_LABELS[profile.business_type]
      ? BUYER_TYPE_LABELS[profile.business_type]
      : profile?.business_type || "Commercial Enterprise";
  const accountStatusConfig =
    ACCOUNT_STATUS_CONFIG[user.account_status] || ACCOUNT_STATUS_CONFIG.active;

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-emerald-950 via-primary-900 to-primary-950 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 bottom-0 translate-x-8 translate-y-8 opacity-10 pointer-events-none">
          <Store className="w-64 h-64" aria-hidden="true" />
        </div>

        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-800/80 border border-primary-700/60 text-xs font-medium text-emerald-200">
            <Sparkles className="w-3.5 h-3.5 text-harvest-400" aria-hidden="true" />
            <span>Commercial Procurement Portal</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Welcome back, {buyerName}
          </h1>

          <p className="text-sm sm:text-base text-primary-100/90 leading-relaxed max-w-2xl">
            Procure fresh agricultural crops directly from verified local
            farmers. Manage your business entity profile and track institutional verification.
          </p>

          <div className="pt-2 flex flex-wrap gap-3">
            <Link
              to="/dashboard/profile"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white text-primary-900 font-semibold text-xs sm:text-sm hover:bg-primary-50 transition-colors shadow-xs"
            >
              <UserIcon className="w-4 h-4 text-primary-700" aria-hidden="true" />
              <span>Update Business Profile</span>
            </Link>

            <Link
              to="/dashboard/verification"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-800/80 border border-primary-700 text-white font-medium text-xs sm:text-sm hover:bg-primary-700 transition-colors"
            >
              <ShieldCheck className="w-4 h-4 text-harvest-400" aria-hidden="true" />
              <span>Verification Status</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Grid: Verification & Profile Completion Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <VerificationSummaryCard
          status={user.verification_status}
          role="buyer"
        />
        <ProfileCompletionCard user={user} />
      </div>

      {/* Business & Commercial Overview Section */}
      <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Building className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 className="text-base font-bold text-foreground">
              Commercial Entity Overview
            </h2>
          </div>
          <Link
            to="/dashboard/profile"
            className="text-xs font-semibold text-primary hover:text-primary-800 transition-colors inline-flex items-center gap-1"
          >
            <span>Edit Profile</span>
            <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Business / Trade Name */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Business / Trade Name
            </span>
            <div className="text-sm font-semibold text-foreground">
              {profile?.business_name || (
                <span className="text-muted-foreground italic font-normal">
                  Not specified
                </span>
              )}
            </div>
          </div>

          {/* Contact Person Name */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Procurement Contact Person
            </span>
            <div className="text-sm font-semibold text-foreground">
              {profile?.contact_person_name || (
                <span className="text-muted-foreground italic font-normal">
                  Not specified
                </span>
              )}
            </div>
          </div>

          {/* Business Type */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Commercial Entity Type
            </span>
            <div>
              <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-foreground border border-border">
                {businessTypeLabel}
              </span>
            </div>
          </div>

          {/* Business Registration Number (Tax/GSTIN/CIN) */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Tax / Registration ID (GSTIN/CIN)
            </span>
            <div className="text-sm font-semibold text-foreground font-mono">
              {profile?.business_registration_number || (
                <span className="text-muted-foreground italic font-normal font-sans">
                  Not provided
                </span>
              )}
            </div>
          </div>

          {/* Primary Facility / Delivery Receiving Address */}
          <div className="space-y-1 sm:col-span-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Truck className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Receiving Dock / Delivery Address</span>
            </span>
            <div className="text-sm text-foreground">
              {profile?.delivery_receiving_address || (
                <span className="text-muted-foreground italic font-normal">
                  No receiving dock specified
                </span>
              )}
            </div>
            {(profile?.city || profile?.state) && (
              <div className="text-xs text-muted-foreground flex items-center gap-1 pt-0.5">
                <MapPin className="w-3 h-3" aria-hidden="true" />
                <span>
                  {[profile.city, profile.state, profile.postal_code]
                    .filter(Boolean)
                    .join(", ")}
                </span>
              </div>
            )}
          </div>

          {/* Contact Details */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Mail className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Commercial Email</span>
            </span>
            <div className="text-sm font-semibold text-foreground truncate">
              {user.email}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Phone className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Contact Phone</span>
            </span>
            <div className="text-sm text-foreground">
              {user.phone_number ? (
                <span className="font-semibold">{user.phone_number}</span>
              ) : (
                <span className="text-muted-foreground italic font-normal">
                  No phone added
                </span>
              )}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Account Status
            </span>
            <div>
              <span
                className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium border ${accountStatusConfig.badgeClass} capitalize`}
              >
                {accountStatusConfig.label}
              </span>
            </div>
          </div>
        </div>

        {/* Procurement Summary (if provided) */}
        {profile?.procurement_summary && (
          <div className="p-6 pt-0 border-t border-border mt-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Procurement Interests & Volume Needs
            </h3>
            <p className="text-sm text-foreground leading-relaxed bg-secondary/30 p-3.5 rounded-lg border border-border">
              {profile.procurement_summary}
            </p>
          </div>
        )}

        {/* Business Bio (if provided) */}
        {profile?.bio && (
          <div className="p-6 pt-0 border-t border-border mt-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Enterprise Overview
            </h3>
            <p className="text-sm text-foreground leading-relaxed bg-secondary/30 p-3.5 rounded-lg border border-border">
              {profile.bio}
            </p>
          </div>
        )}
      </div>

      {/* Practical Next Steps / Quick Actions */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-xs space-y-4">
        <h2 className="text-base font-bold text-foreground">
          Recommended Next Actions
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <FileText className="w-4 h-4" aria-hidden="true" />
              <span>1. Complete Business Details</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Add your corporate registration ID, receiving facility address, and procurement requirements.
            </p>
            <Link
              to="/dashboard/profile"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline pt-1"
            >
              <span>Manage Profile</span>
              <ArrowRight className="w-3 h-3" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <ShieldCheck className="w-4 h-4" aria-hidden="true" />
              <span>2. Commercial Verification</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Submit proof of business registration (GSTIN, trade license, or incorporation certificate) for review.
            </p>
            <Link
              to="/dashboard/verification"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline pt-1"
            >
              <span>Verification Portal</span>
              <ArrowRight className="w-3 h-3" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <Calendar className="w-4 h-4" aria-hidden="true" />
              <span>3. Direct Sourcing</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Once verified, post buyer requirements and issue formal purchase orders directly to verified farmers.
            </p>
            <span className="text-xs text-muted-foreground font-medium pt-1 block">
              Unlocks after verification
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
