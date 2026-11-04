import React from "react";
import { Link } from "react-router-dom";
import {
  Tractor,
  MapPin,
  Sprout,
  Phone,
  Mail,
  Calendar,
  FileText,
  User as UserIcon,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Layers,
  Handshake,
  ClipboardList,
  MessageSquare,
  CheckCircle2,
  Clock,
  Truck,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { VerificationSummaryCard } from "../components/ui/VerificationSummaryCard";
import { ProfileCompletionCard } from "../components/ui/ProfileCompletionCard";
import { ACCOUNT_STATUS_CONFIG } from "../utils/status";

export const FarmerDashboardPage: React.FC = () => {
  const { user } = useAuth();

  if (!user || user.role !== "farmer") {
    return null;
  }

  const profile = user.farmer_profile;
  const farmerName = profile?.full_name || profile?.farm_name || user.email;
  const accountStatusConfig =
    ACCOUNT_STATUS_CONFIG[user.account_status] || ACCOUNT_STATUS_CONFIG.active;
  const isVerified = user.verification_status === "verified";

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-primary-900 via-primary-800 to-primary-950 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 bottom-0 translate-x-8 translate-y-8 opacity-10 pointer-events-none">
          <Tractor className="w-64 h-64" aria-hidden="true" />
        </div>

        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-800/80 border border-primary-700/60 text-xs font-medium text-emerald-200">
            <Sparkles className="w-3.5 h-3.5 text-harvest-400" aria-hidden="true" />
            <span>Agricultural Producer Portal</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Welcome back, {farmerName}
          </h1>

          <p className="text-sm sm:text-base text-primary-100/90 leading-relaxed max-w-2xl">
            Manage your farm profile, track identity verification, and prepare
            to connect directly with commercial bulk buyers without intermediary brokers.
          </p>

          <div className="pt-2 flex flex-wrap gap-3">
            <Link
              to="/dashboard/profile"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-primary-900 font-semibold text-xs sm:text-sm hover:bg-primary-50 transition-colors shadow-xs"
            >
              <UserIcon className="w-4 h-4 text-primary-700" aria-hidden="true" />
              <span>Update Farm Profile</span>
            </Link>

            <Link
              to="/dashboard/verification"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-800/80 border border-primary-700 text-white font-medium text-xs sm:text-sm hover:bg-primary-700 transition-colors"
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
          role="farmer"
        />
        <ProfileCompletionCard user={user} />
      </div>

      {/* Direct Trade Operations Fast-Action Hub */}
      <div className="p-6 rounded-2xl bg-card border border-border shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Sprout className="w-4 h-4 text-primary" />
              Farm Trade Operations Navigation
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Quick access to your active harvest listings, buyer negotiations, and fulfillment agreements
            </p>
          </div>
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-secondary text-foreground border border-border self-start sm:self-auto">
            {isVerified ? "Direct Trading Active" : "Verification Pending"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/dashboard/listings"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-700 flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Layers className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                My Harvest Lots
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Create, manage, and monitor your listed wholesale produce lots
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
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-amber-600 group-hover:translate-x-0.5 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-amber-700 transition-colors">
                Buyer Offers & Bids
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Review incoming price offers and submit structured counter-terms
              </p>
            </div>
          </Link>

          <Link
            to="/dashboard/orders"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-blue-500/10 text-blue-700 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <ClipboardList className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-blue-700 transition-colors">
                Trade Agreements
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Coordinate lot dispatches, track deliveries, and manage settlements
              </p>
            </div>
          </Link>

          <Link
            to="/dashboard/messages"
            className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/60 border border-border/80 hover:border-primary/40 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-700 flex items-center justify-center group-hover:bg-purple-600 group-hover:text-white transition-colors">
                <MessageSquare className="w-4 h-4" />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-purple-600 group-hover:translate-x-0.5 transition-all" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground group-hover:text-purple-700 transition-colors">
                Direct Communications
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Coordinate logistics details and share authenticated transport receipts
              </p>
            </div>
          </Link>
        </div>
      </div>

      {/* Visual 5-Stage Wholesale Trade Lifecycle Roadmap */}
      <div className="p-6 rounded-2xl bg-card border border-border shadow-xs space-y-4">
        <div>
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            Direct Agricultural Trade Lifecycle
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            How wholesale deals are formed, fulfilled, and acknowledged on AgriDirect
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2">
          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-primary text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center text-[11px]">1</span>
              <span>Publish Harvest</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Post verified lot with price per quintal, moisture, and available dispatch date.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-amber-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-amber-500/10 flex items-center justify-center text-[11px]">2</span>
              <span>Offer Bidding</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Receive buyer inquiries, review target prices, or send structured counter-offers.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-blue-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-blue-500/10 flex items-center justify-center text-[11px]">3</span>
              <span>Binding Order</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Mutual acceptance generates an atomic, legally-binding trade order with audit trail.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-purple-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-purple-500/10 flex items-center justify-center text-[11px]">4</span>
              <span>Fulfillment & Dock</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Dispatch lot as scheduled; goods arrive at receiving dock for quality check.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-emerald-700 text-xs font-bold">
              <span className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center text-[11px]">5</span>
              <span>Direct Settlement</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Buyer records direct bank transfer; farmer acknowledges receipt and leaves review.
            </p>
          </div>
        </div>
      </div>

      {/* Farm & Account Overview Section */}
      <div className="rounded-2xl border border-border bg-card shadow-xs overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-secondary/20">
          <div className="flex items-center gap-2.5">
            <Tractor className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 className="text-base font-bold text-foreground">
              Farm & Producer Overview
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
          {/* Operation Name */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Operation / Farm Name
            </span>
            <div className="text-sm font-semibold text-foreground">
              {profile?.farm_name || (
                <span className="text-muted-foreground italic font-normal">
                  Not specified
                </span>
              )}
            </div>
          </div>

          {/* Producer Full Name */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Producer Full Name
            </span>
            <div className="text-sm font-semibold text-foreground">
              {profile?.full_name || (
                <span className="text-muted-foreground italic font-normal">
                  Not specified
                </span>
              )}
            </div>
          </div>

          {/* Land Acreage */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Cultivated Area
            </span>
            <div className="text-sm font-semibold text-foreground">
              {profile?.farm_size_acres ? (
                `${profile.farm_size_acres} Acres`
              ) : (
                <span className="text-muted-foreground italic font-normal">
                  Not specified
                </span>
              )}
            </div>
          </div>

          {/* Location */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Location / Region</span>
            </span>
            <div className="text-sm text-foreground">
              {profile?.city || profile?.state ? (
                <span className="font-semibold">
                  {[profile.city, profile.state, profile.postal_code]
                    .filter(Boolean)
                    .join(", ")}
                </span>
              ) : (
                <span className="text-muted-foreground italic font-normal">
                  Not specified
                </span>
              )}
            </div>
            {profile?.farm_location_address && (
              <div className="text-xs text-muted-foreground">
                {profile.farm_location_address}
              </div>
            )}
          </div>

          {/* Primary Crops */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Sprout className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Primary Produce / Crops</span>
            </span>
            <div className="text-sm text-foreground">
              {profile?.primary_crops ? (
                <span className="font-semibold">{profile.primary_crops}</span>
              ) : (
                <span className="text-muted-foreground italic font-normal">
                  No crops specified
                </span>
              )}
            </div>
          </div>

          {/* Farming Practices */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Farming Practices
            </span>
            <div>
              {profile?.farming_practices ? (
                <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 capitalize">
                  {profile.farming_practices}
                </span>
              ) : (
                <span className="text-muted-foreground italic text-sm">
                  Conventional / Standard
                </span>
              )}
            </div>
          </div>

          {/* Contact Details */}
          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Mail className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Registered Email</span>
            </span>
            <div className="text-sm font-semibold text-foreground truncate">
              {user.email}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Phone className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Phone Number</span>
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

        {/* Bio / Farm Narrative (if provided) */}
        {profile?.bio && (
          <div className="p-6 pt-0 border-t border-border mt-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Farm Biography & Capacity
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
              <span>1. Complete Profile</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Ensure farm location, acreage, and crop details are up-to-date so commercial buyers can discover your harvest.
            </p>
            <Link
              to="/dashboard/profile"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline pt-1"
            >
              <span>Manage Profile</span>
              <ArrowRight className="w-3 h-3" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-4 rounded-xl bg-secondary/40 border border-border space-y-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <ShieldCheck className="w-4 h-4" aria-hidden="true" />
              <span>2. Identity Verification</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Submit producer identification and agricultural land documentation to unlock produce listings and negotiations.
            </p>
            <Link
              to="/dashboard/verification"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline pt-1"
            >
              <span>Verification Portal</span>
              <ArrowRight className="w-3 h-3" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-4 rounded-xl bg-secondary/40 border border-border space-y-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <Calendar className="w-4 h-4" aria-hidden="true" />
              <span>3. Marketplace Trading</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Once verified, you will be able to post active harvest listings and respond to buyer procurement requests.
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
