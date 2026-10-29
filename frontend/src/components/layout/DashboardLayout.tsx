import React, { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
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
} from "lucide-react";
import { useAuth } from "../../store/authStore";
import { VERIFICATION_STATUS_CONFIG } from "../../utils/status";
import { PublicFooter } from "./PublicFooter";

export const DashboardLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  if (!user) {
    return null;
  }

  const isFarmer = user.role === "farmer";
  const isBuyer = user.role === "buyer";

  // Role-appropriate display names
  const displayName = isFarmer
    ? user.farmer_profile?.full_name || user.farmer_profile?.farm_name || user.email
    : isBuyer
    ? user.buyer_profile?.contact_person_name ||
      user.buyer_profile?.business_name ||
      user.email
    : user.email;

  const entitySubtitle = isFarmer
    ? user.farmer_profile?.farm_name && user.farmer_profile.farm_name !== displayName
      ? user.farmer_profile.farm_name
      : "Agricultural Producer"
    : isBuyer
    ? user.buyer_profile?.business_name && user.buyer_profile.business_name !== displayName
      ? user.buyer_profile.business_name
      : "Commercial Buyer"
    : "AgriDirect User";

  const verificationConfig =
    VERIFICATION_STATUS_CONFIG[user.verification_status] ||
    VERIFICATION_STATUS_CONFIG.unverified;

  // Nav links tailored by role
  const navItems = [
    {
      label: "Dashboard",
      to: isFarmer ? "/dashboard/farmer" : "/dashboard/buyer",
      icon: isFarmer ? Tractor : Store,
    },
    {
      label: "My Profile",
      to: "/dashboard/profile",
      icon: UserIcon,
    },
    {
      label: "Verification",
      to: "/dashboard/verification",
      icon: ShieldCheck,
      badge: verificationConfig.label,
      badgeClass: verificationConfig.badgeClass,
    },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground antialiased selection:bg-primary/20">
      {/* Top Banner */}
      <div className="bg-primary-900 text-white text-xs py-1.5 px-4 tracking-wide font-medium flex items-center justify-between border-b border-primary-800">
        <div className="mx-auto max-w-7xl w-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block w-2 h-2 rounded-full ${verificationConfig.dotClass}`}
              aria-hidden="true"
            />
            <span>
              {isFarmer ? "Producer Portal" : "Commercial Procurement Portal"} —
              Verification:{" "}
              <span className="font-semibold">{verificationConfig.label}</span>
            </span>
          </div>
          <Link
            to="/"
            className="hidden sm:inline-flex items-center gap-1 text-primary-200 hover:text-white transition-colors text-[11px]"
          >
            <span>Public Marketplace</span>
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {/* Main Authenticated Header */}
      <header className="border-b border-border bg-card/95 backdrop-blur sticky top-0 z-40 transition-colors shadow-xs">
        <div className="mx-auto px-4 sm:px-6 lg:px-8 w-full max-w-7xl">
          <div className="h-16 flex items-center justify-between gap-4">
            {/* Logo / Home */}
            <div className="flex items-center gap-6">
              <Link
                to={isFarmer ? "/dashboard/farmer" : "/dashboard/buyer"}
                className="flex items-center gap-2.5 focus:outline-none focus:ring-2 focus:ring-primary rounded-lg p-1"
                aria-label="AgriDirect Dashboard Home"
              >
                <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-sm">
                  <Sprout className="w-5 h-5" aria-hidden="true" />
                </div>
                <div>
                  <span className="text-lg font-bold tracking-tight text-primary-900 block leading-tight">
                    AgriDirect
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold block">
                    {isFarmer ? "Farmer Dashboard" : "Buyer Dashboard"}
                  </span>
                </div>
              </Link>

              {/* Desktop Navigation Links */}
              <nav
                className="hidden md:flex items-center gap-1 pl-4 border-l border-border"
                aria-label="Dashboard Navigation"
              >
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.to;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-primary text-primary-foreground shadow-xs"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                      }`}
                    >
                      <Icon className="w-4 h-4" aria-hidden="true" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>

            {/* Desktop User Info & Sign Out */}
            <div className="hidden md:flex items-center gap-4">
              <div className="text-right">
                <div className="text-xs font-semibold text-foreground truncate max-w-[180px]">
                  {displayName}
                </div>
                <div className="text-[11px] text-muted-foreground truncate max-w-[180px]">
                  {entitySubtitle}
                </div>
              </div>

              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${verificationConfig.badgeClass}`}
                title={verificationConfig.description}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${verificationConfig.dotClass}`}
                  aria-hidden="true"
                />
                <span>{verificationConfig.label}</span>
              </span>

              <button
                type="button"
                onClick={logout}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors px-3 py-1.5 rounded-md border border-destructive/20 focus:outline-none focus:ring-2 focus:ring-destructive"
                aria-label="Sign out of AgriDirect"
              >
                <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Sign Out</span>
              </button>
            </div>

            {/* Mobile Menu Hamburger */}
            <div className="flex md:hidden items-center gap-2">
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${verificationConfig.badgeClass}`}
              >
                {verificationConfig.label}
              </span>

              <button
                type="button"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
                aria-expanded={mobileMenuOpen}
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border bg-card px-4 pt-3 pb-6 space-y-4 shadow-lg animate-in slide-in-from-top duration-200">
            {/* User Details in Drawer */}
            <div className="p-3 bg-secondary/50 rounded-lg space-y-1">
              <div className="text-sm font-semibold text-foreground">
                {displayName}
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
                <span>Public Marketplace Home</span>
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
              <span>Sign Out</span>
            </button>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col py-8 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl flex-1 flex flex-col">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <PublicFooter />
    </div>
  );
};
