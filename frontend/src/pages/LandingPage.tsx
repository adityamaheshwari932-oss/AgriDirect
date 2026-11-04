import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sprout,
  ShieldCheck,
  Scale,
  Store,
  Tractor,
  ArrowRight,
  CheckCircle2,
  UserCheck,
  TrendingUp,
  Layers,
  Sparkles,
  ShoppingBag,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { PageContainer } from "../components/layout/PageContainer";

export const LandingPage: React.FC = () => {
  const { status, user } = useAuth();
  const navigate = useNavigate();
  const isAuthenticated = status === "authenticated" && user !== null;

  // Interactive audience toggle
  const [audienceTab, setAudienceTab] = useState<"farmer" | "buyer">("farmer");

  // Sample live commodity market rates ticker data
  const marketTickers = [
    { name: "Sharbati Wheat", variety: "C-306", price: "₹2,850/Qtl", trend: "+2.4%", up: true, location: "Madhya Pradesh" },
    { name: "Basmati Rice", variety: "1121 Pusa", price: "₹4,200/Qtl", trend: "+1.1%", up: true, location: "Punjab / Haryana" },
    { name: "Yellow Soybean", variety: "JS-335", price: "₹4,450/Qtl", trend: "-0.8%", up: false, location: "Maharashtra" },
    { name: "Cotton (Medium Staple)", variety: "Shankar-6", price: "₹6,150/Qtl", trend: "+3.2%", up: true, location: "Gujarat" },
    { name: "Mustard Seed", variety: "Pusa Bold", price: "₹5,400/Qtl", trend: "+1.5%", up: true, location: "Rajasthan" },
  ];

  // Commodity categories for quick B2B exploration
  const commodityCategories = [
    { title: "Grains & Cereals", desc: "Wheat, Basmati & Non-Basmati Paddy, Maize, Barley", icon: Sprout, count: "140+ Lots" },
    { title: "Oilseeds & Pulses", desc: "Soybean, Mustard, Chana (Gram), Tur / Arhar, Moong", icon: Layers, count: "95+ Lots" },
    { title: "Cash Crops & Fiber", desc: "Raw Cotton (Kapas), Sugarcane, Jute, Tobacco", icon: Tractor, count: "60+ Lots" },
    { title: "Spices & Commercial", desc: "Red Chilli, Turmeric, Cumin, Coriander Seed", icon: Sparkles, count: "45+ Lots" },
  ];

  return (
    <div className="flex-1 py-8 sm:py-12 bg-gradient-to-b from-background via-background to-secondary/30">
      <PageContainer>
        {/* Welcome Banner for Authenticated Users */}
        {isAuthenticated && (
          <div className="mb-8 p-5 bg-card border border-primary/20 rounded-2xl shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                <UserCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-foreground">
                    Welcome back, <strong className="font-bold text-foreground">{user.email}</strong>
                  </span>
                  <span className="capitalize px-2.5 py-0.5 rounded-full bg-primary/15 text-primary text-xs font-bold border border-primary/25">
                    {user.role}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    (Status: <span className="font-semibold text-foreground capitalize">{user.verification_status}</span>)
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Your active authenticated B2B session is live. Access your trading workspace, orders, and messages.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2.5 self-stretch md:self-auto">
              <Link
                to={user.role === "admin" ? "/admin/analytics" : user.role === "farmer" ? "/dashboard/farmer" : "/dashboard/buyer"}
                className="w-full md:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary-700 transition-colors shadow-xs"
              >
                <span>Go to {user.role === "admin" ? "Admin Console" : "Dashboard"}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        {/* Hero Section */}
        <div className="max-w-4xl mx-auto text-center mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary-50 text-primary-800 text-xs font-bold uppercase tracking-wider mb-5 border border-primary-200/80 shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-primary-700" />
            Verified B2B Agricultural Trade Engine
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-foreground tracking-tight sm:leading-tight">
            Connecting Farmers Directly with Commercial Buyers
          </h1>

          <p className="mt-5 text-base sm:text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            A transparent agricultural marketplace facilitating direct transactions,
            fair price discovery, and verified commercial relationships without intermediaries.
          </p>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3.5">
            {isAuthenticated ? (
              <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
                <Link
                  to={user.role === "admin" ? "/admin/analytics" : user.role === "farmer" ? "/dashboard/farmer" : "/dashboard/buyer"}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-bold text-sm hover:bg-primary-700 transition-all shadow-sm hover:shadow"
                >
                  <span>Open Active Workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/marketplace"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl border border-border bg-card text-foreground font-bold text-sm hover:bg-secondary/70 transition-colors"
                >
                  <ShoppingBag className="w-4 h-4 text-primary" />
                  <span>Browse Marketplace</span>
                </Link>
              </div>
            ) : (
              <>
                <Link
                  to="/register"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3 rounded-xl bg-primary text-primary-foreground font-bold text-sm hover:bg-primary-700 transition-all shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                >
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/login"
                  className="w-full sm:w-auto inline-flex items-center justify-center px-7 py-3 rounded-xl border border-border bg-card text-foreground font-bold text-sm hover:bg-secondary/80 transition-colors shadow-2xs focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Live Agricultural Market Rates Bar (B2B Ticker) */}
        <div className="mb-16 p-4 rounded-2xl bg-card border border-border shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-3 border-b border-border/80 text-xs">
            <div className="flex items-center gap-2 text-foreground font-bold uppercase tracking-wider text-[11px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Live Mandi Indicative Benchmarks</span>
            </div>
            <span className="text-[11px] text-muted-foreground">
              Market rates aggregated across audited APMC Mandi terminals
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {marketTickers.map((item, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-secondary/30 border border-border/70 hover:border-primary/40 transition-colors"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-foreground truncate">{item.name}</span>
                  <span
                    className={`inline-flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      item.up
                        ? "bg-emerald-500/10 text-emerald-700"
                        : "bg-rose-500/10 text-rose-700"
                    }`}
                  >
                    <TrendingUp className={`w-2.5 h-2.5 ${item.up ? "" : "rotate-180"}`} />
                    {item.trend}
                  </span>
                </div>
                <div className="text-sm font-extrabold text-foreground mt-1 tabular">{item.price}</div>
                <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-0.5">
                  <span>{item.variety}</span>
                  <span>{item.location}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive B2B Role Segmenter */}
        <div className="mb-16 rounded-3xl bg-card border border-border p-6 sm:p-10 shadow-xs">
          <div className="max-w-2xl mx-auto text-center mb-8">
            <span className="text-xs font-bold uppercase tracking-wider text-primary">Tailored Trade Architecture</span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground mt-1">
              Engineered for Both Sides of Agricultural Commerce
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground mt-2">
              Whether you harvest 500 quintals of grain or procure wholesale commodities for food processing plants, AgriDirect provides structured contracts with zero commission deductions.
            </p>

            {/* Toggle Switch */}
            <div className="inline-flex p-1.5 mt-6 rounded-xl bg-secondary border border-border text-xs font-bold">
              <button
                type="button"
                onClick={() => setAudienceTab("farmer")}
                className={`px-5 py-2 rounded-lg transition-all ${
                  audienceTab === "farmer"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                For Agricultural Producers
              </button>
              <button
                type="button"
                onClick={() => setAudienceTab("buyer")}
                className={`px-5 py-2 rounded-lg transition-all ${
                  audienceTab === "buyer"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                For Commercial Buyers
              </button>
            </div>
          </div>

          {/* Dynamic Tab Content */}
          {audienceTab === "farmer" ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              <div className="p-5 rounded-2xl bg-secondary/30 border border-border space-y-2">
                <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold">
                  1
                </div>
                <h3 className="text-sm font-bold text-foreground">Direct Price Sovereignty</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  List your produce with your own minimum lot sizes and target wholesale prices. Reject lowball offers with formal counter-offers.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-secondary/30 border border-border space-y-2">
                <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold">
                  2
                </div>
                <h3 className="text-sm font-bold text-foreground">Guaranteed Buyer Verification</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Only verified institutional buyers with verified GST, PAN, and trade registrations can place binding purchase offers.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-secondary/30 border border-border space-y-2">
                <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold">
                  3
                </div>
                <h3 className="text-sm font-bold text-foreground">Zero Commission Fees</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  AgriDirect is a pure trade facilitation engine. We never deduct commission percentages from your hard-earned harvest sales.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              <div className="p-5 rounded-2xl bg-secondary/30 border border-border space-y-2">
                <div className="w-9 h-9 rounded-xl bg-harvest-500/10 text-harvest-700 flex items-center justify-center font-bold">
                  1
                </div>
                <h3 className="text-sm font-bold text-foreground">Farm-Origin Traceability</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Source directly from audited farm origins with complete transparency into harvest dates, variety seeds, and verified quality grades.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-secondary/30 border border-border space-y-2">
                <div className="w-9 h-9 rounded-xl bg-harvest-500/10 text-harvest-700 flex items-center justify-center font-bold">
                  2
                </div>
                <h3 className="text-sm font-bold text-foreground">Target Procurement Demands</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Post detailed procurement requirements specifying required volumes, maximum price ceilings, delivery timelines, and receiving hubs.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-secondary/30 border border-border space-y-2">
                <div className="w-9 h-9 rounded-xl bg-harvest-500/10 text-harvest-700 flex items-center justify-center font-bold">
                  3
                </div>
                <h3 className="text-sm font-bold text-foreground">Contractual Predictability</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Binding offer acceptances generate traceable orders with recorded amendment history, delivery acknowledgments, and dispute mediation.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Feature Pillars Grid (Required Test Anchors Maintained) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          {/* Farmer Pillar */}
          <div className="bg-card rounded-2xl p-8 border border-border shadow-xs hover:border-primary/50 transition-all duration-200">
            <div className="w-12 h-12 rounded-xl bg-primary-50 text-primary-700 flex items-center justify-center mb-6">
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
          <div className="bg-card rounded-2xl p-8 border border-border shadow-xs hover:border-harvest-500/50 transition-all duration-200">
            <div className="w-12 h-12 rounded-xl bg-harvest-50 text-harvest-700 flex items-center justify-center mb-6">
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
          <div className="bg-card rounded-2xl p-8 border border-border shadow-xs hover:border-emerald-500/50 transition-all duration-200">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-6">
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

        {/* Commodity Categories Quick-Jump Matrix */}
        <div className="mb-16">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
            <div>
              <h2 className="text-xl font-bold text-foreground">Explore High-Volume Commodity Sectors</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Bulk agricultural lots sourced directly from verified farming clusters
              </p>
            </div>
            <Link
              to="/marketplace"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:text-primary-800 transition-colors"
            >
              <span>View Full Marketplace Catalog</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {commodityCategories.map((cat, idx) => {
              const Icon = cat.icon;
              return (
                <div
                  key={idx}
                  onClick={() => navigate("/marketplace")}
                  className="p-5 rounded-2xl bg-card border border-border shadow-2xs hover:border-primary/50 hover:shadow-xs transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-secondary text-foreground">
                      {cat.count}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                    {cat.title}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {cat.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Informational Marketplace Notice (Required Test Disclaimer Maintained) */}
        <div className="rounded-2xl bg-card border border-border p-6 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary flex-shrink-0">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground">
                AgriDirect Trade Facilitation
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5 max-w-3xl leading-relaxed">
                Our platform provides direct agricultural trade connections and legally-binding agreement record-keeping.
                We do not hold produce inventory, process financial transactions, or operate physical logistics.
              </p>
            </div>
          </div>
          {!isAuthenticated && (
            <Link
              to="/register"
              className="px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold hover:bg-primary-700 transition-colors whitespace-nowrap shadow-2xs"
            >
              Get Started →
            </Link>
          )}
        </div>
      </PageContainer>
    </div>
  );
};
