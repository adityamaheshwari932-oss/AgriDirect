import React, { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
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
import { formatCurrency as formatCurrencyUtil, formatNumber, formatDateTime } from "../../utils/formatters";

export const AdminPlatformAnalyticsPage: React.FC = () => {
  const { t } = useTranslation(["admin", "analytics", "common"]);
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
      const msg = err instanceof Error ? err.message : t("admin:load_analytics_error", "Failed to load platform analytics.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void fetchAnalytics();
  }, [fetchAnalytics]);

  const formatCurrency = (val: string | number) => {
    return formatCurrencyUtil(val, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatQuantityMap = (qtyMap: Record<string, string | number>) => {
    const entries = Object.entries(qtyMap);
    if (entries.length === 0) return t("common:zero_units", "0 units");
    return entries
      .map(([unit, val]) => `${formatNumber(val)} ${unit}`)
      .join(", ");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <LineChart className="w-6 h-6 text-primary" aria-hidden="true" />
            <span>{t("admin:platform_analytics_title", "Platform Operational Analytics")}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("admin:platform_analytics_subtitle", "Descriptive marketplace statistics, gross transaction metrics, and ecosystem composition.")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void fetchAnalytics()}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold border border-border shadow-xs transition-colors self-start sm:self-center"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>{t("admin:refresh_analytics", "Refresh Analytics")}</span>
        </button>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <LoadingState message={t("admin:computing_analytics", "Computing unsuppressed platform analytics...")} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void fetchAnalytics()} />
      ) : !data ? (
        <EmptyState title={t("admin:empty_analytics_title", "No analytics data available")} description={t("admin:empty_analytics_desc", "No platform statistics could be retrieved at this time.")} />
      ) : (
        <div className="space-y-6">
          {/* GMV Highlight Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-2">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-bold uppercase tracking-wider">
                <span>{t("admin:realized_gmv", "Realized Platform GMV")}</span>
                <TrendingUp className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-3xl font-extrabold text-foreground tracking-tight">
                {formatCurrency(data.platform_gmv)}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("admin:realized_gmv_desc", "Gross Merchandise Value accumulated from realized completed trade orders.")}
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-2">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-bold uppercase tracking-wider">
                <span>{t("admin:pipeline_gmv", "Contracted Pipeline GMV")}</span>
                <IndianRupee className="w-4 h-4 text-blue-600" />
              </div>
              <div className="text-3xl font-extrabold text-foreground tracking-tight">
                {formatCurrency(data.pipeline_gmv)}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("admin:pipeline_gmv_desc", "Contracted transaction obligation across active in-progress and pending orders.")}
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
                    <h2 className="text-sm font-bold text-foreground">{t("admin:listed_supply_title", "Listed Supply Overview")}</h2>
                    <p className="text-[11px] text-muted-foreground">{t("admin:listed_supply_subtitle", "Farmer Active Produce Inventory")}</p>
                  </div>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {t("admin:active_listings_count", "{{count}} Active Listings", { count: data.listed_supply_overview.active_listings_count })}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:inventory_valuation", "Inventory Valuation")}</span>
                  <div className="text-base font-bold text-foreground">
                    {formatCurrency(data.listed_supply_overview.total_active_listed_value)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:available_volume", "Available Volume")}</span>
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
                    <h2 className="text-sm font-bold text-foreground">{t("admin:buyer_demand_title", "Buyer Demand Overview")}</h2>
                    <p className="text-[11px] text-muted-foreground">{t("admin:buyer_demand_subtitle", "Open Demands & Audited Ledger")}</p>
                  </div>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {t("admin:open_requirements_count", "{{count}} Open Requirements", { count: data.buyer_demand_overview.active_requirements_count })}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:active_demanded_volume", "Active Demanded Volume")}</span>
                  <div className="text-xs font-semibold text-foreground line-clamp-2">
                    {formatQuantityMap(data.buyer_demand_overview.total_demanded_quantity_by_unit)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:audited_fulfilled_volume", "Audited Fulfilled Volume")}</span>
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
                  <span>{t("admin:lifecycle_outcomes_title", "Order Lifecycle Outcomes & Execution Rates")}</span>
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  {t("admin:lifecycle_outcomes_subtitle", "Two-tier outcome accounting across all placed and concluded trades.")}
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                  {t("admin:completion_rate", "Completion Rate: {{rate}}%", { rate: data.order_outcomes.concluded_completion_rate?.toFixed(1) ?? "0.0" })}
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-rose-50 text-rose-800 font-bold border border-rose-200">
                  {t("admin:cancellation_rate", "Cancellation Rate: {{rate}}%", { rate: data.order_outcomes.concluded_cancellation_rate?.toFixed(1) ?? "0.0" })}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-center">
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-foreground block">{data.order_outcomes.total_orders}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:orders_total_placed", "Total Placed")}</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-amber-700 block">{data.order_outcomes.pending_confirmation}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:orders_pending_confirm", "Pending Confirm")}</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-blue-700 block">{data.order_outcomes.in_progress}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:orders_in_progress", "In Progress")}</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-emerald-700 block">{data.order_outcomes.completed}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:orders_completed", "Completed")}</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-rose-700 block">{data.order_outcomes.cancelled}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:orders_cancelled", "Cancelled")}</span>
              </div>
              <div className="p-3 rounded-xl bg-secondary/30 border border-border">
                <span className="text-xl font-bold text-destructive block">{data.order_outcomes.currently_disputed}</span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("admin:orders_disputed", "Disputed")}</span>
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
                    <span>{t("admin:payment_velocity_title", "Off-Platform Payment Velocity & Disputes")}</span>
                  </h2>
                  <p className="text-[11px] text-muted-foreground">
                    {t("admin:payment_velocity_subtitle", "Settlement timeliness and dispute frequency across recorded claims.")}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-foreground block">{data.payment_velocity.total_payments}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:pay_total", "Total Payments")}</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-emerald-700 block">{data.payment_velocity.acknowledged_payments}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:pay_acknowledged", "Acknowledged")}</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-destructive block">{data.payment_velocity.disputed_payments}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:pay_disputed", "Disputed")}</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-amber-700 block">{data.payment_velocity.pending_payments}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:pay_pending", "Pending")}</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-secondary/30 border border-border flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">{t("admin:mean_delay", "Mean Elapsed Settlement Delay")}</span>
                <span className="font-bold text-foreground">
                  {data.payment_velocity.average_settlement_delay_hours !== null && data.payment_velocity.average_settlement_delay_hours !== undefined
                    ? t("admin:hours_stat", "{{val}} hours", { val: data.payment_velocity.average_settlement_delay_hours.toFixed(1) })
                    : t("admin:insufficient_data", "Insufficient data")}
                </span>
              </div>
            </div>

            {/* User Engagement & Composition */}
            <div className="p-5 rounded-2xl bg-card border border-border shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Users className="w-4 h-4 text-primary" />
                    <span>{t("admin:user_base_title", "Platform User Base & Verification Status")}</span>
                  </h2>
                  <p className="text-[11px] text-muted-foreground">
                    {t("admin:user_base_subtitle", "Ecosystem trade participants and administrative account distribution.")}
                  </p>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-secondary text-foreground border border-border">
                  {t("admin:total_accounts_count", "{{count}} Total Accounts", { count: data.user_engagement.total_users })}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-emerald-700 block">{data.user_engagement.verified_farmers}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:users_verified_farmers", "Verified Farmers")}</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-blue-700 block">{data.user_engagement.verified_buyers}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:users_verified_buyers", "Verified Buyers")}</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-amber-700 block">{data.user_engagement.unverified_users}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:users_unverified", "Unverified Users")}</span>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-lg font-bold text-purple-700 block">{data.user_engagement.admin_users}</span>
                  <span className="text-[10px] text-muted-foreground">{t("admin:users_admins", "Admins")}</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-secondary/30 border border-border flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">{t("admin:snapshot_timestamp", "Computed Snapshot Timestamp")}</span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {formatDateTime(data.generated_at)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

