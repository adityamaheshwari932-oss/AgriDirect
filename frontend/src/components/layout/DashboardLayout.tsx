import React, { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Sprout,
  Tractor,
  Store,
  User as UserIcon,
  ShieldCheck,
  LogOut,
  Menu,
  X,
  ExternalLink,
  Layers,
  ClipboardList,
  MessageSquare,
  BarChart3,
  ShoppingBag,
  Users,
  ShieldAlert,
  CheckSquare,
  History,
  LineChart,
  AlertTriangle,
  Handshake,
} from "lucide-react";
import { useAuth } from "../../store/authStore";
import { getLocalizedVerificationStatus } from "../../utils/status";
import { PublicFooter } from "./PublicFooter";
import { NotificationBell } from "../notifications/NotificationBell";
import { LanguageSelector } from "../ui/LanguageSelector";

export const DashboardLayout: React.FC = () => {
  const { t } = useTranslation(["common", "dashboard"]);
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  if (!user) {
    return null;
  }

  const isFarmer = user.role === "farmer";
  const isBuyer = user.role === "buyer";
  const isAdmin = user.role === "admin";

  // Role-appropriate display names
  const displayName = isFarmer
    ? user.farmer_profile?.full_name || user.farmer_profile?.farm_name || user.email
    : isBuyer
    ? user.buyer_profile?.contact_person_name ||
      user.buyer_profile?.business_name ||
      user.email
    : isAdmin
    ? t("dashboard:layout.admin_subtitle", "Platform Administrator")
    : user.email;

  const entitySubtitle = isFarmer
    ? user.farmer_profile?.farm_name && user.farmer_profile.farm_name !== displayName
      ? user.farmer_profile.farm_name
      : t("dashboard:layout.producer_subtitle", "Agricultural Producer")
    : isBuyer
    ? user.buyer_profile?.business_name && user.buyer_profile.business_name !== displayName
      ? user.buyer_profile.business_name
      : t("dashboard:layout.buyer_subtitle", "Commercial Buyer")
    : isAdmin
    ? user.email
    : t("dashboard:layout.user_subtitle", "AgriDirect User");

  const verificationConfig = getLocalizedVerificationStatus(user.verification_status, t);

  // Role-specific navigation items
  const navItems = isFarmer
    ? [
        { label: t("common:nav.dashboard", "Dashboard"), to: "/dashboard/farmer", icon: Tractor },
        { label: t("common:nav.listings", "My Listings"), to: "/dashboard/listings", icon: Layers },
        { label: t("common:nav.offers", "Offers"), to: "/dashboard/offers", icon: Handshake },
        { label: t("common:nav.orders", "Orders"), to: "/dashboard/orders", icon: ClipboardList },
        { label: t("common:nav.messages", "Messages"), to: "/dashboard/messages", icon: MessageSquare },
        { label: t("common:nav.analytics", "Analytics"), to: "/dashboard/analytics", icon: BarChart3 },
        { label: t("common:nav.reports", "Reports"), to: "/dashboard/reports", icon: ShieldAlert },
        { label: t("common:nav.profile", "Profile"), to: "/dashboard/profile", icon: UserIcon },
        {
          label: t("common:nav.verification", "Verification"),
          to: "/dashboard/verification",
          icon: ShieldCheck,
          badge: verificationConfig.label,
          badgeClass: verificationConfig.badgeClass,
        },
      ]
    : isBuyer
    ? [
        { label: t("common:nav.dashboard", "Dashboard"), to: "/dashboard/buyer", icon: Store },
        { label: t("common:nav.marketplace", "Marketplace"), to: "/dashboard/marketplace", icon: ShoppingBag },
        { label: t("common:nav.requirements", "Requirements"), to: "/dashboard/requirements", icon: Layers },
        { label: t("common:nav.offers", "Offers"), to: "/dashboard/offers", icon: Handshake },
        { label: t("common:nav.orders", "Orders"), to: "/dashboard/orders", icon: ClipboardList },
        { label: t("common:nav.messages", "Messages"), to: "/dashboard/messages", icon: MessageSquare },
        { label: t("common:nav.analytics", "Analytics"), to: "/dashboard/analytics", icon: BarChart3 },
        { label: t("common:nav.reports", "Reports"), to: "/dashboard/reports", icon: ShieldAlert },
        { label: t("common:nav.profile", "Profile"), to: "/dashboard/profile", icon: UserIcon },
        {
          label: t("common:nav.verification", "Verification"),
          to: "/dashboard/verification",
          icon: ShieldCheck,
          badge: verificationConfig.label,
          badgeClass: verificationConfig.badgeClass,
        },
      ]
    : isAdmin
    ? [
        { label: t("common:nav.admin_users", "User Moderation"), to: "/admin/users", icon: Users },
        { label: t("common:nav.admin_content", "Content Moderation"), to: "/admin/content", icon: ShieldAlert },
        { label: t("common:nav.admin_verification", "Verification Queue"), to: "/admin/verification", icon: CheckSquare },
        { label: t("common:nav.admin_audit", "Audit Logs"), to: "/admin/audit-logs", icon: History },
        { label: t("common:nav.admin_analytics", "Platform Analytics"), to: "/admin/analytics", icon: LineChart },
      ]
    : [
        { label: t("common:nav.profile", "Profile"), to: "/dashboard/profile", icon: UserIcon },
      ];

  const homeDestination = isFarmer
    ? "/dashboard/farmer"
    : isBuyer
    ? "/dashboard/buyer"
    : isAdmin
    ? "/admin/analytics"
    : "/dashboard";

  const isRestricted = user.account_status === "restricted";
  const isSuspendedOrBlocked = user.account_status === "suspended" || user.account_status === "blocked";

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground antialiased selection:bg-primary/20">
      {/* Top Banner */}
      <div className="bg-primary-900 text-white text-xs py-1.5 px-4 tracking-wide font-medium flex items-center justify-between border-b border-primary-800">
        <div className="mx-auto max-w-7xl w-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isAdmin ? "bg-purple-400" : verificationConfig.dotClass
              }`}
              aria-hidden="true"
            />
            <span>
              {isAdmin
                ? t("dashboard:layout.admin_banner", "Platform Governance Portal — Administrator Console")
                : isFarmer
                ? t("dashboard:layout.farmer_banner", "Producer Portal — Verification: ")
                : t("dashboard:layout.buyer_banner", "Commercial Procurement Portal — Verification: ")}
              {!isAdmin && <span className="font-semibold">{verificationConfig.label}</span>}
            </span>
          </div>
          <Link
            to="/"
            className="hidden sm:inline-flex items-center gap-1 text-primary-200 hover:text-white transition-colors text-[11px]"
          >
            <span>{t("dashboard:layout.public_marketplace", "Public Marketplace")}</span>
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {/* Account Status Warning Banner */}
      {isRestricted && (
        <div
          role="alert"
          className="bg-amber-500/15 border-b border-amber-500/30 text-amber-950 px-4 py-2.5 text-xs flex items-center justify-center gap-2 text-center"
        >
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" aria-hidden="true" />
          <span>
            <strong>{t("dashboard:layout.account_restricted_title", "Account Restricted:")}</strong>{" "}
            {t("dashboard:layout.account_restricted_desc", "Your account is currently in read-only mode. You can view marketplace records, but creating listings, requirements, or offers is disabled.")}
          </span>
        </div>
      )}

      {isSuspendedOrBlocked && (
        <div
          role="alert"
          className="bg-destructive/15 border-b border-destructive/30 text-destructive px-4 py-2.5 text-xs flex items-center justify-center gap-2 text-center"
        >
          <ShieldAlert className="w-4 h-4 text-destructive shrink-0" aria-hidden="true" />
          <span>
            <strong>
              {user.account_status === "blocked"
                ? t("dashboard:layout.account_blocked_title", "Account Blocked:")
                : t("dashboard:layout.account_suspended_title", "Account Suspended:")}
            </strong>{" "}
            {t("dashboard:layout.account_disabled_desc", "Transactional access has been disabled by platform governance. Contact support for assistance.")}
          </span>
        </div>
      )}

      {/* Main Authenticated Header */}
      <header className="border-b border-border bg-card/95 backdrop-blur sticky top-0 z-40 transition-colors shadow-xs">
        <div className="mx-auto px-4 sm:px-6 lg:px-8 w-full max-w-7xl">
          <div className="h-16 flex items-center justify-between gap-4">
            {/* Logo / Home */}
            <div className="flex items-center gap-4 sm:gap-6">
              <Link
                to={homeDestination}
                className="flex items-center gap-2.5 focus:outline-none focus:ring-2 focus:ring-primary rounded-lg p-1 shrink-0"
                aria-label={t("common:app.dashboard_home_aria", "AgriDirect Dashboard Home")}
              >
                <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-sm">
                  <Sprout className="w-5 h-5" aria-hidden="true" />
                </div>
                <div>
                  <span className="text-lg font-bold tracking-tight text-primary-900 block leading-tight">
                    {t("common:app.name", "AgriDirect")}
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold block">
                    {isAdmin
                      ? t("dashboard:layout.admin_badge", "Admin Console")
                      : isFarmer
                      ? t("dashboard:layout.farmer_badge", "Farmer Dashboard")
                      : t("dashboard:layout.buyer_badge", "Buyer Dashboard")}
                  </span>
                </div>
              </Link>

              {/* Desktop Navigation Links */}
              <nav
                className="hidden lg:flex items-center gap-1 ps-4 border-s border-border overflow-x-auto"
                aria-label="Dashboard Navigation"
              >
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.to;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                        isActive
                          ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>

            {/* Desktop User Info & Sign Out */}
            <div className="hidden lg:flex items-center gap-3">
              <LanguageSelector />
              <NotificationBell />

              <div className="text-end">
                <div className="text-xs font-semibold text-foreground truncate max-w-[160px]">
                  {displayName}
                </div>
                <div className="text-[10px] text-muted-foreground truncate max-w-[160px]">
                  {entitySubtitle}
                </div>
              </div>

              {!isAdmin ? (
                <span
                  className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border ${verificationConfig.badgeClass}`}
                  title={verificationConfig.description}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${verificationConfig.dotClass}`}
                    aria-hidden="true"
                  />
                  <span>{verificationConfig.label}</span>
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                  Admin
                </span>
              )}

              <button
                type="button"
                onClick={logout}
                className="inline-flex items-center gap-1 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors px-2.5 py-1.5 rounded-md border border-destructive/20 focus:outline-none focus:ring-2 focus:ring-destructive"
                aria-label={t("common:nav.sign_out_aria", "Sign out of AgriDirect")}
              >
                <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t("common:nav.sign_out", "Sign Out")}</span>
              </button>
            </div>

            {/* Mobile Menu Hamburger */}
            <div className="flex lg:hidden items-center gap-2">
              <LanguageSelector variant="compact" />
              <NotificationBell />
              <button
                type="button"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label={mobileMenuOpen ? t("common:nav.close_menu", "Close navigation menu") : t("common:nav.open_menu", "Open navigation menu")}
                aria-expanded={mobileMenuOpen}
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-border bg-card px-4 pt-3 pb-6 space-y-4 shadow-lg animate-in slide-in-from-top duration-200">
            {/* User Details in Drawer */}
            <div className="p-3 bg-secondary/50 rounded-lg space-y-1">
              <div className="text-sm font-semibold text-foreground flex items-center justify-between">
                <span>{displayName}</span>
                {isAdmin ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 font-semibold">
                    Admin
                  </span>
                ) : (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full border ${verificationConfig.badgeClass}`}
                  >
                    {verificationConfig.label}
                  </span>
                )}
              </div>
              <div className="text-xs text-muted-foreground">
                {user.email} • {entitySubtitle}
              </div>
            </div>

            {/* Nav Links */}
            <nav className="flex flex-col gap-1" aria-label="Mobile Dashboard Navigation">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.to;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground font-semibold"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4" aria-hidden="true" />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full border ${item.badgeClass}`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </nav>

            {/* Public Marketplace Link */}
            <div className="pt-2 border-t border-border">
              <Link
                to="/"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-between px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
              >
                <span>{t("dashboard:layout.public_marketplace_home", "Public Marketplace Home")}</span>
                <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
              </Link>
            </div>

            {/* Mobile Sign Out */}
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                logout();
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium text-destructive bg-destructive/10 hover:bg-destructive/20 transition-colors"
            >
              <LogOut className="w-4 h-4" aria-hidden="true" />
              <span>{t("common:nav.sign_out", "Sign Out")}</span>
            </button>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col py-6 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl flex-1 flex flex-col">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <PublicFooter />
    </div>
  );
};
