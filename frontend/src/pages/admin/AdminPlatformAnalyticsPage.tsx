import React, { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  RefreshCw,
  IndianRupee,
  Layers,
  Store,
  CheckCircle2,
  Clock,
  Users,
  TrendingUp,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import type { PlatformAnalyticsResponse } from "../../types/admin";
import { LoadingState, ErrorState, EmptyState } from "../../components/ui/states";

export const AdminPlatformAnalyticsPage: React.FC = () => {
  const [data, setData] = useState<PlatformAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await adminApi.getPlatformAnalytics();
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load platform analytics.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAnalytics();
  }, [fetchAnalytics]);

  const formatCurrency = (val: string | number) => {
    const num = Number(val);
    if (isNaN(num)) return String(val);
    return `₹${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatQuantityMap = (qtyMap: Record<string, string | number>) => {
    const entries = Object.entries(qtyMap);
    if (entries.length === 0) return "0 units";
    return entries
      .map(([unit, val]) => `${Number(val).toLocaleString("en-IN")} ${unit}`)
      .join(", ");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <LineChart className="w-6 h-6 text-primary" aria-hidden="true" />
            Platform Operational Analytics
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Descriptive marketplace statistics, gross transaction metrics, and ecosystem composition.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void fetchAnalytics()}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold border border-border shadow-xs transition-colors self-start sm:self-center"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Analytics</span>
        </button>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <LoadingState message="Computing unsuppressed platform analytics..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void fetchAnalytics()} />
      ) : !data ? (
        <EmptyState title="No analytics data available" description="No platform statistics could be retrieved at this time." />
      ) : (
        <div className="space-y-6">
          {/* GMV Highlight Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-2">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-bold uppercase tracking-wider">
                <span>Realized Platform GMV</span>
                <TrendingUp className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-3xl font-extrabold text-foreground tracking-tight">
                {formatCurrency(data.platform_gmv)}
              </div>
              <p className="text-xs text-muted-foreground">
                Gross Merchandise Value accumulated from realized completed trade orders.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-2">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-bold uppercase tracking-wider">
                <span>Contracted Pipeline GMV</span>
                <IndianRupee className="w-4 h-4 text-blue-600" />
              </div>
              <div className="text-3xl font-extrabold text-foreground tracking-tight">
                {formatCurrency(data.pipeline_gmv)}
              </div>
              <p className="text-xs text-muted-foreground">
                Contracted transaction obligation across active in-progress and pending orders.
              </p>
            </div>
          </div>

          {/* Supply & Demand Overview Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Active Supply */}
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-700">
                    <Layers className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-foreground">Listed Supply Overview</h2>
                    <p className="text-[11px] text-muted-foreground">Farmer Active Produce Inventory</p>
                  </div>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {data.listed_supply_overview.active_listings_count} Active Listings
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Inventory Valuation</span>
                  <div className="text-base font-bold text-foreground">
                    {formatCurrency(data.listed_supply_overview.total_active_listed_value)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Available Volume</span>
                  <div className="text-xs font-semibold text-foreground line-clamp-2">
                    {formatQuantityMap(data.listed_supply_overview.total_active_quantity_by_unit)}
                  </div>
                </div>
              </div>
            </div>

            {/* Buyer Demand */}
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-700">
                    <Store className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-foreground">Buyer Demand Overview</h2>
                    <p className="text-[11px] text-muted-foreground">Open Demands & Audited Ledger</p>
                  </div>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {data.buyer_demand_overview.active_requirements_count} Open Requirements
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Active Demanded Volume</span>
                  <div className="text-xs font-semibold text-foreground line-clamp-2">
                    {formatQuantityMap(data.buyer_demand_overview.total_demanded_quantity_by_unit)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Audited Fulfilled Volume</span>
                  <div className="text-xs font-semibold text-foreground line-clamp-2">
                    {formatQuantityMap(data.buyer_demand_overview.total_approved_fulfilled_quantity_by_unit)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Order Lifecycle Breakdown & Execution Rates */}
          <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-border pb-3">
              <div>
                <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-primary" />
                  Order Lifecycle Outcomes & Execution Rates
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  Two-tier outcome accounting across all placed and concluded trades.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                  Completion Rate: {data.order_outcomes.concluded_completion_rate?.toFixed(1) ?? "0.0"}%
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-rose-50 text-rose-800 font-bold border border-rose-200">
                  Cancellation Rate: {data.order_outcomes.concluded_cancellation_rate?.toFixed(1) ?? "0.0"}%
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-center">
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-foreground block">{data.order_outcomes.total_orders}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Total Placed</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-amber-700 block">{data.order_outcomes.pending_confirmation}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Pending Confirm</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-blue-700 block">{data.order_outcomes.in_progress}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">In Progress</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-emerald-700 block">{data.order_outcomes.completed}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Completed</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-rose-700 block">{data.order_outcomes.cancelled}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Cancelled</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-destructive block">{data.order_outcomes.currently_disputed}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Disputed</span>
              </div>
            </div>
          </div>

          {/* Payment Velocity & User Engagement */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Payment Velocity */}
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary" />
                    Off-Platform Payment Velocity & Disputes
                  </h2>
                  <p className="text-[11px] text-muted-foreground">
                    Settlement timeliness and dispute frequency across recorded claims.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-foreground block">{data.payment_velocity.total_payments}</span>
                  <span className="text-[10px] text-muted-foreground">Total Payments</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-emerald-700 block">{data.payment_velocity.acknowledged_payments}</span>
                  <span className="text-[10px] text-muted-foreground">Acknowledged</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-destructive block">{data.payment_velocity.disputed_payments}</span>
                  <span className="text-[10px] text-muted-foreground">Disputed</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-amber-700 block">{data.payment_velocity.pending_payments}</span>
                  <span className="text-[10px] text-muted-foreground">Pending</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-secondary/30 border border-border flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">Mean Elapsed Settlement Delay</span>
                <span className="font-bold text-foreground">
                  {data.payment_velocity.average_settlement_delay_hours !== null && data.payment_velocity.average_settlement_delay_hours !== undefined
                    ? `${data.payment_velocity.average_settlement_delay_hours.toFixed(1)} hours`
                    : "Insufficient data"}
                </span>
              </div>
            </div>

            {/* User Engagement & Composition */}
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Users className="w-4 h-4 text-primary" />
                    Platform User Base & Verification Status
                  </h2>
                  <p className="text-[11px] text-muted-foreground">
                    Ecosystem trade participants and administrative account distribution.
                  </p>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-secondary text-foreground border border-border">
                  {data.user_engagement.total_users} Total Accounts
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-emerald-700 block">{data.user_engagement.verified_farmers}</span>
                  <span className="text-[10px] text-muted-foreground">Verified Farmers</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-blue-700 block">{data.user_engagement.verified_buyers}</span>
                  <span className="text-[10px] text-muted-foreground">Verified Buyers</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-amber-700 block">{data.user_engagement.unverified_users}</span>
                  <span className="text-[10px] text-muted-foreground">Unverified Users</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-purple-700 block">{data.user_engagement.admin_users}</span>
                  <span className="text-[10px] text-muted-foreground">Admins</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-secondary/30 border border-border flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">Computed Snapshot Timestamp</span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {new Date(data.generated_at).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

