import React from "react";
import { Link } from "react-router-dom";
import {
  Sprout,
  ShieldCheck,
  Scale,
  Store,
  Tractor,
  ArrowRight,
  CheckCircle2,
  UserCheck,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { PageContainer } from "../components/layout/PageContainer";

export const LandingPage: React.FC = () => {
  const { status, user } = useAuth();
  const isAuthenticated = status === "authenticated" && user !== null;

  return (
    <div className="flex-1 py-12">
      <PageContainer>
        {/* Welcome Banner for Authenticated Users */}
        {isAuthenticated && (
          <div className="mb-8 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-3 text-emerald-900">
            <div className="flex items-center gap-3">
              <UserCheck className="w-5 h-5 text-emerald-700 flex-shrink-0" />
              <div className="text-sm">
                Signed in as <strong className="font-semibold">{user.email}</strong>{" "}
                <span className="capitalize px-2 py-0.5 rounded bg-emerald-200/70 text-emerald-800 text-xs font-semibold ml-1">
                  {user.role}
                </span>
                <span className="text-xs text-emerald-700 block sm:inline sm:ml-2">
                  (Status: {user.verification_status})
                </span>
              </div>
            </div>
            <span className="text-xs font-medium text-emerald-700 bg-white px-2.5 py-1 rounded-md border border-emerald-200">
              Active Session
            </span>
          </div>
        )}

        {/* Hero Section */}
        <div className="max-w-3xl mx-auto text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-harvest-100 text-harvest-800 text-xs font-semibold uppercase tracking-wider mb-4 border border-harvest-200">
            <ShieldCheck className="w-3.5 h-3.5 text-harvest-700" />
            Verified B2B Agricultural Trade
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-foreground tracking-tight sm:leading-tight">
            Connecting Farmers Directly with Commercial Buyers
          </h1>
          <p className="mt-5 text-base sm:text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            A transparent agricultural marketplace facilitating direct transactions,
            fair price discovery, and verified commercial relationships without intermediaries.
          </p>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            {isAuthenticated ? (
              <div className="text-sm text-muted-foreground p-3 bg-secondary rounded-lg border border-border">
                You are currently authenticated. Marketplace listings and order features will activate in upcoming milestones.
              </div>
            ) : (
              <>
                <Link
                  to="/register"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                >
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/login"
                  className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 rounded-lg border border-border text-foreground font-semibold text-sm hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Feature Pillars Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          {/* Farmer Pillar */}
          <div className="bg-card rounded-xl p-8 border border-border shadow-sm hover:border-primary/40 transition-colors">
            <div className="w-12 h-12 rounded-lg bg-primary-50 text-primary-700 flex items-center justify-center mb-6">
              <Tractor className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-3">Verified Farmers</h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              Direct market access for agricultural producers. Set your own prices, manage harvest listings,
              and maintain full control over inventory deductions.
            </p>
            <ul className="text-xs text-muted-foreground space-y-2.5">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
                <span>Verified identity & land documentation</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
                <span>Farmer-approved inventory workflows</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
                <span>Direct structured offers from verified buyers</span>
              </li>
            </ul>
          </div>

          {/* Buyer Pillar */}
          <div className="bg-card rounded-xl p-8 border border-border shadow-sm hover:border-harvest-500/40 transition-colors">
            <div className="w-12 h-12 rounded-lg bg-harvest-50 text-harvest-700 flex items-center justify-center mb-6">
              <Store className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-3">Commercial Buyers</h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              Wholesalers, retailers, food processors, restaurants, and hotels procuring bulk produce
              directly from verified origins.
            </p>
            <ul className="text-xs text-muted-foreground space-y-2.5">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-harvest-600 flex-shrink-0" />
                <span>Post specific procurement requirements</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-harvest-600 flex-shrink-0" />
                <span>Verified commercial entity registration</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-harvest-600 flex-shrink-0" />
                <span>Transparent supply chain traceability</span>
              </li>
            </ul>
          </div>

          {/* Integrity Pillar */}
          <div className="bg-card rounded-xl p-8 border border-border shadow-sm hover:border-primary/40 transition-colors">
            <div className="w-12 h-12 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center mb-6">
              <Scale className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-3">Structured Trade</h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              Binding counter-offers, recorded order amendments, and mutual delivery confirmations
              ensuring commercial predictability.
            </p>
            <ul className="text-xs text-muted-foreground space-y-2.5">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Immutable order records & amendment logs</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Mutual delivery verification confirmations</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Zero hidden fees or silent deductions</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Informational Marketplace Notice */}
        <div className="rounded-xl bg-card border border-border p-6 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-secondary flex items-center justify-center text-primary flex-shrink-0">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                AgriDirect Trade Facilitation
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Our platform provides direct trade connections and agreement record-keeping.
                We do not hold produce inventory, process financial transactions, or operate physical logistics.
              </p>
            </div>
          </div>
          {!isAuthenticated && (
            <Link
              to="/register"
              className="text-xs font-semibold text-primary hover:text-primary-800 transition-colors whitespace-nowrap"
            >
              Get Started →
            </Link>
          )}
        </div>
      </PageContainer>
    </div>
  );
};
