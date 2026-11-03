import React from "react";
import {
  TrendingUp,
  Package,
  Layers,
  BarChart3,
  MapPin,
} from "lucide-react";
import { PrivacySuppressionBadge } from "./PrivacySuppressionBadge";
import type { MarketSummaryResponse, DemandSummaryResponse } from "../../types/analytics";

interface MarketplaceSummarySectionProps {
  marketSummary?: MarketSummaryResponse | null;
  demandSummary?: DemandSummaryResponse | null;
  isLoading?: boolean;
}

export const MarketplaceSummarySection: React.FC<MarketplaceSummarySectionProps> = ({
  marketSummary,
  demandSummary,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-44 bg-card rounded-xl border border-border p-5 space-y-3">
            <div className="h-4 bg-secondary rounded w-1/3" />
            <div className="h-8 bg-secondary rounded w-2/3" />
            <div className="h-4 bg-secondary rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (!marketSummary && !demandSummary) {
    return (
      <div className="p-8 text-center text-xs text-muted-foreground bg-card rounded-xl border border-border">
        No aggregate market data available for the selected filters.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Privacy and Provenance Header Banner */}
      {marketSummary?.privacy && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-secondary/30 border border-border text-xs">
          <PrivacySuppressionBadge privacy={marketSummary.privacy} />
          {marketSummary.provenance && (
            <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5" />
              <span>
                Geographic scope:{" "}
                <span className="font-semibold capitalize text-foreground">
                  {marketSummary.provenance.geographic_level_applied}
                </span>
              </span>
            </div>
          )}
        </div>
      )}

      {/* Realized Market Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Active Supply */}
        {marketSummary && (
          <div className="bg-card p-5 rounded-xl border border-border shadow-xs space-y-3">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <span>Active Supply</span>
              <Package className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <div className="text-3xl font-extrabold text-foreground">
                {marketSummary.active_supply.total_listings_count}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Active produce listings</p>
            </div>
            {marketSummary.active_supply.total_available_quantity && (
              <div className="text-xs text-foreground pt-2 border-t border-border/50">
                <span className="text-muted-foreground">Available volume: </span>
                <span className="font-semibold">
                  {Number(marketSummary.active_supply.total_available_quantity).toLocaleString()}{" "}
                  {marketSummary.active_supply.measurement_unit || "kg"}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Realized Trades & Volume */}
        {marketSummary && (
          <div className="bg-card p-5 rounded-xl border border-border shadow-xs space-y-3">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <span>Settled Trades</span>
              <BarChart3 className="w-4 h-4 text-primary" />
            </div>
            <div>
              <div className="text-3xl font-extrabold text-foreground">
                {marketSummary.realized_trades.total_orders_count}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Concluded orders</p>
            </div>
            {marketSummary.realized_trades.total_quantity_traded && (
              <div className="text-xs text-foreground pt-2 border-t border-border/50">
                <span className="text-muted-foreground">Volume traded: </span>
                <span className="font-semibold">
                  {Number(marketSummary.realized_trades.total_quantity_traded).toLocaleString()}{" "}
                  {marketSummary.realized_trades.measurement_unit || "kg"}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Realized Price Indices / VWAP */}
        {marketSummary && (
          <div className="bg-card p-5 rounded-xl border border-border shadow-xs space-y-3">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <span>VWAP Benchmark</span>
              <TrendingUp className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              {marketSummary.privacy.vwap_suppressed || !marketSummary.realized_trades.vwap ? (
                <div className="text-base font-bold text-amber-600 py-1">
                  [Suppressed for Confidentiality]
                </div>
              ) : (
                <div className="text-3xl font-extrabold text-foreground">
                  ₹{Number(marketSummary.realized_trades.vwap).toLocaleString("en-IN", {
                    maximumFractionDigits: 2,
                  })}
                  <span className="text-xs font-normal text-muted-foreground">
                    /{marketSummary.realized_trades.measurement_unit || "kg"}
                  </span>
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-0.5">
                Volume-weighted average realized price
              </p>
            </div>
            {marketSummary.realized_trades.arithmetic_mean &&
              !marketSummary.privacy.arithmetic_mean_suppressed && (
                <div className="text-xs text-foreground pt-2 border-t border-border/50 flex justify-between">
                  <span className="text-muted-foreground">Mean Price: </span>
                  <span className="font-semibold">
                    ₹{Number(marketSummary.realized_trades.arithmetic_mean).toFixed(2)}
                  </span>
                </div>
              )}
          </div>
        )}

        {/* Open Demand & Requirements */}
        {demandSummary && (
          <div className="bg-card p-5 rounded-xl border border-border shadow-xs space-y-3 md:col-span-3">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <span>Commercial Demand Summary</span>
              <Layers className="w-4 h-4 text-purple-600" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
              <div>
                <span className="text-xs text-muted-foreground block">Active Requirements</span>
                <span className="text-2xl font-bold text-foreground">
                  {demandSummary.open_demand.total_requirements_count}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Demanded Volume</span>
                <span className="text-2xl font-bold text-foreground">
                  {demandSummary.open_demand.total_demanded_quantity
                    ? `${Number(demandSummary.open_demand.total_demanded_quantity).toLocaleString()} ${
                        demandSummary.open_demand.measurement_unit || "kg"
                      }`
                    : "N/A"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Approved Fulfillments</span>
                <span className="text-2xl font-bold text-emerald-600">
                  {demandSummary.approved_fulfillment.total_approvals_count}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

