import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  BarChart3,
  RotateCw,
  TrendingUp,
  UserCheck,
  Layers,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { analyticsApi } from "../api/analytics";
import { PerformanceMetricsGrid } from "../components/analytics/PerformanceMetricsGrid";
import { MarketplaceSummarySection } from "../components/analytics/MarketplaceSummarySection";
import type {
  FarmerPerformanceResponse,
  BuyerPerformanceResponse,
  MarketSummaryResponse,
  DemandSummaryResponse,
} from "../types/analytics";

type AnalyticsTab = "performance" | "market" | "demand";

export const AnalyticsDashboardPage: React.FC = () => {
  const { t } = useTranslation(["analytics", "common"]);
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("performance");

  // Performance state
  const [performance, setPerformance] = useState<
    FarmerPerformanceResponse | BuyerPerformanceResponse | null
  >(null);
  const [isPerfLoading, setIsPerfLoading] = useState(false);
  const [perfError, setPerfError] = useState<string | null>(null);

  // Market Summary state
  const [marketSummary, setMarketSummary] = useState<MarketSummaryResponse | null>(null);
  const [isMarketLoading, setIsMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState<string | null>(null);

  // Demand Summary state
  const [demandSummary, setDemandSummary] = useState<DemandSummaryResponse | null>(null);
  const [isDemandLoading, setIsDemandLoading] = useState(false);
  const [demandError, setDemandError] = useState<string | null>(null);

  const loadPerformance = useCallback(async () => {
    setIsPerfLoading(true);
    setPerfError(null);
    try {
      const data = await analyticsApi.getMyPerformance();
      setPerformance(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("analytics:perf_error", "Failed to load performance metrics.");
      setPerfError(msg);
    } finally {
      setIsPerfLoading(false);
    }
  }, [t]);

  const loadMarketSummary = useCallback(async () => {
    setIsMarketLoading(true);
    setMarketError(null);
    try {
      const data = await analyticsApi.getMarketSummary({});
      setMarketSummary(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("analytics:market_error", "Failed to load market summary.");
      setMarketError(msg);
    } finally {
      setIsMarketLoading(false);
    }
  }, [t]);

  const loadDemandSummary = useCallback(async () => {
    setIsDemandLoading(true);
    setDemandError(null);
    try {
      const data = await analyticsApi.getDemandSummary({});
      setDemandSummary(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("analytics:demand_error", "Failed to load demand summary.");
      setDemandError(msg);
    } finally {
      setIsDemandLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (activeTab === "performance") {
      void loadPerformance();
    } else if (activeTab === "market") {
      void loadMarketSummary();
    } else if (activeTab === "demand") {
      void loadDemandSummary();
    }
  }, [activeTab, loadPerformance, loadMarketSummary, loadDemandSummary]);

  const handleRefresh = () => {
    if (activeTab === "performance") void loadPerformance();
    else if (activeTab === "market") void loadMarketSummary();
    else if (activeTab === "demand") void loadDemandSummary();
  };

  const isCurrentLoading =
    activeTab === "performance"
      ? isPerfLoading
      : activeTab === "market"
      ? isMarketLoading
      : isDemandLoading;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-primary" aria-hidden="true" />
            <span>{t("analytics:dashboard_title", "Market & Operational Analytics")}</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t("analytics:dashboard_subtitle", "Descriptive volume, price benchmark indices and personal fulfillment metrics.")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isCurrentLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-card text-foreground hover:bg-secondary/60 disabled:opacity-50 transition-colors shadow-sm"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isCurrentLoading ? "animate-spin text-primary" : ""}`} />
            {t("common:actions.refresh", "Refresh")}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-6 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setActiveTab("performance")}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "performance"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          {t("analytics:tab_performance", "My Operational Performance")}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("market")}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "market"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          {t("analytics:tab_market", "Market Supply & Price Index")}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("demand")}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "demand"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          {t("analytics:tab_demand", "Commercial Demand Trends")}
        </button>
      </div>

      {/* Content Area */}
      <div>
        {activeTab === "performance" && (
          <div>
            {perfError ? (
              <div className="p-6 text-center space-y-2 bg-card rounded-xl border border-border">
                <AlertCircle className="w-6 h-6 text-destructive mx-auto" />
                <p className="text-xs text-destructive font-medium">{perfError}</p>
                <button
                  type="button"
                  onClick={() => void loadPerformance()}
                  className="text-xs text-primary underline"
                >
                  {t("common:actions.retry", "Retry")}
                </button>
              </div>
            ) : performance ? (
              <PerformanceMetricsGrid
                performance={performance}
                role={(user?.role as "farmer" | "buyer") || "farmer"}
              />
            ) : (
              <div className="py-12 text-center text-xs text-muted-foreground">
                {t("analytics:loading_metrics", "Loading personal metrics...")}
              </div>
            )}
          </div>
        )}

        {activeTab === "market" && (
          <div>
            {marketError ? (
              <div className="p-6 text-center space-y-2 bg-card rounded-xl border border-border">
                <AlertCircle className="w-6 h-6 text-destructive mx-auto" />
                <p className="text-xs text-destructive font-medium">{marketError}</p>
                <button
                  type="button"
                  onClick={() => void loadMarketSummary()}
                  className="text-xs text-primary underline"
                >
                  {t("common:actions.retry", "Retry")}
                </button>
              </div>
            ) : (
              <MarketplaceSummarySection
                marketSummary={marketSummary}
                isLoading={isMarketLoading}
              />
            )}
          </div>
        )}

        {activeTab === "demand" && (
          <div>
            {demandError ? (
              <div className="p-6 text-center space-y-2 bg-card rounded-xl border border-border">
                <AlertCircle className="w-6 h-6 text-destructive mx-auto" />
                <p className="text-xs text-destructive font-medium">{demandError}</p>
                <button
                  type="button"
                  onClick={() => void loadDemandSummary()}
                  className="text-xs text-primary underline"
                >
                  {t("common:actions.retry", "Retry")}
                </button>
              </div>
            ) : (
              <MarketplaceSummarySection
                demandSummary={demandSummary}
                isLoading={isDemandLoading}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

