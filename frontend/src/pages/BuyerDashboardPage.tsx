import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
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
  Layers,
  ShoppingBag,
  Handshake,
  ClipboardList,
  CheckCircle2,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { VerificationSummaryCard } from "../components/ui/VerificationSummaryCard";
import { ProfileCompletionCard } from "../components/ui/ProfileCompletionCard";
import { ACCOUNT_STATUS_CONFIG, BUYER_TYPE_LABELS } from "../utils/status";

export const BuyerDashboardPage: React.FC = () => {
  const { t } = useTranslation(["dashboard", "profile", "common"]);
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
  const isVerified = user.verification_status === "verified";

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-emerald-950 via-primary-900 to-primary-950 text-white shadow-md relative overflow-hidden">
        <div className="absolute end-0 bottom-0 rtl:-translate-x-8 translate-x-8 translate-y-8 opacity-10 pointer-events-none">
          <Store className="w-64 h-64" aria-hidden="true" />
        </div>

        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-800/80 border border-primary-700/60 text-xs font-medium text-emerald-200">
            <Sparkles className="w-3.5 h-3.5 text-harvest-400" aria-hidden="true" />
            <span>{t("dashboard:buyer.portal_title", "Commercial Procurement Portal")}</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            {t("dashboard:buyer.welcome_back", "Welcome back, {{name}}", { name: buyerName })}
          </h1>

          <p className="text-sm sm:text-base text-primary-100/90 leading-relaxed max-w-2xl">
            Procure fresh agricultural crops directly from verified local
            farmers. Manage your business entity profile and track institutional verification.
          </p>

          <div className="pt-2 flex flex-wrap gap-3">
            <Link
              to="/dashboard/profile"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-primary-900 font-semibold text-xs sm:text-sm hover:bg-primary-50 transition-colors shadow-xs"
            >
              <UserIcon className="w-4 h-4 text-primary-700" aria-hidden="true" />
              <span>{t("profile:overview.edit_profile", "Update Business Profile")}</span>
            </Link>

            <Link
              to="/dashboard/verification"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-800/80 border border-primary-700 text-white font-medium text-xs sm:text-sm hover:bg-primary-700 transition-colors"
            >
              <ShieldCheck className="w-4 h-4 text-harvest-400" aria-hidden="true" />
              <span>{t("common:nav.verification", "Verification Status")}</span>
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

      {/* Commercial Sourcing Operations Fast-Action Hub */}
      <div className="p-6 rounded-2xl bg-card border border-border shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Building className="w-4 h-4 text-primary" />
              {t("dashboard:buyer.procurement_nav_title", "Commercial Sourcing Navigation")}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {t(
                "dashboard:buyer.procurement_nav_desc",
                "Quick access to your published procurement demands, wholesale discovery, and supplier agreements"
              )}
            </p>
          </div>
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-secondary text-foreground border border-border self-start sm:self-auto">
            {isVerified
              ? t("dashboard:buyer.status_verified", "Commercial Purchasing Active")
              : t("dashboard:buyer.status_unverified", "Verification Pending")}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/dashboard/requirements"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-blue-500/10 text-blue-700 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Layers className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-blue-600 group-hover:translate-x-0.5 rtl:rotate-180 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-blue-700 transition-colors">
                Procurement Demands
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Publish and manage your bulk crop volume requirements
              </p>
            </div>
          </Link>

          <Link
            to="/dashboard/marketplace"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-700 flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <ShoppingBag className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 rtl:rotate-180 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                Wholesale Marketplace
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Browse verified farm harvest lots across India with grade filters
              </p>
            </div>
          </Link>

          <Link
            to="/dashboard/offers"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 text-amber-700 flex items-center justify-center group-hover:bg-amber-600 group-hover:text-white transition-colors">
                <Handshake className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-amber-600 group-hover:translate-x-0.5 rtl:rotate-180 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-amber-700 transition-colors">
                Supplier Negotiations
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Review farmer bids, negotiate lot prices, and finalize delivery
              </p>
            </div>
          </Link>

          <Link
            to="/dashboard/orders"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-700 flex items-center justify-center group-hover:bg-purple-600 group-hover:text-white transition-colors">
                <ClipboardList className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-purple-600 group-hover:translate-x-0.5 rtl:rotate-180 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-purple-700 transition-colors">
                Purchase Agreements
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Track incoming lot shipments, inspect docks, and record payments
              </p>
            </div>
          </Link>
        </div>
      </div>

      {/* Visual 5-Stage Commercial Procurement Lifecycle */}
      <div className="p-6 rounded-2xl bg-card border border-border shadow-xs space-y-4">
        <div>
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            Institutional Procurement Lifecycle
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            End-to-end milestone progression for commercial commodity purchases
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2">
          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-blue-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-blue-500/10 flex items-center justify-center text-[11px]">1</span>
              <span>Demand / Search</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Post required crop specs and dock destination or search verified supply lots.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-amber-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-amber-500/10 flex items-center justify-center text-[11px]">2</span>
              <span>Rate Bidding</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Negotiate price per unit, lot volume, and freight terms directly with farmers.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-primary text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center text-[11px]">3</span>
              <span>Binding Agreement</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Agreed terms lock into a legally-binding commercial trade agreement.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-purple-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-purple-500/10 flex items-center justify-center text-[11px]">4</span>
              <span>Dock Verification</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Inspect arrived lot at your delivery dock and acknowledge physical receipt.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-emerald-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center text-[11px]">5</span>
              <span>Direct Transfer</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Execute bank settlement directly to farmer; counterparty acknowledges and reviews.
            </p>
          </div>
        </div>
      </div>

      {/* Business & Commercial Overview Section */}
      <div className="rounded-2xl border border-border bg-card shadow-xs overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-secondary/20">
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
            <ArrowRight className="w-3 h-3 rtl:rotate-180" aria-hidden="true" />
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
            <p className="text-sm text-foreground leading-relaxed bg-secondary/30 p-3.5 rounded-xl border border-border">
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
            <p className="text-sm text-foreground leading-relaxed bg-secondary/30 p-3.5 rounded-xl border border-border">
              {profile.bio}
            </p>
          </div>
        )}
      </div>

      {/* Practical Next Steps / Quick Actions */}
      <div className="p-6 rounded-2xl border border-border bg-card shadow-xs space-y-4">
        <h2 className="text-base font-bold text-foreground">
          Recommended Next Actions
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-secondary/40 border border-border space-y-2">
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
              <ArrowRight className="w-3 h-3 rtl:rotate-180" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-4 rounded-xl bg-secondary/40 border border-border space-y-2">
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
              <ArrowRight className="w-3 h-3 rtl:rotate-180" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-4 rounded-xl bg-secondary/40 border border-border space-y-2">
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
