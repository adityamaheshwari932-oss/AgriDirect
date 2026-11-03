import React from "react";
import {
  Package,
  DollarSign,
  Percent,
  Star,
} from "lucide-react";
import type { FarmerPerformanceResponse, BuyerPerformanceResponse } from "../../types/analytics";

interface PerformanceMetricsGridProps {
  performance: FarmerPerformanceResponse | BuyerPerformanceResponse;
  role: "farmer" | "buyer";
}

export const PerformanceMetricsGrid: React.FC<PerformanceMetricsGridProps> = ({
  performance,
  role,
}) => {
  const { order_outcomes, payment_settlement } = performance;

  const isFarmer = role === "farmer";
  const farmerPerf = isFarmer ? (performance as FarmerPerformanceResponse) : null;
  const buyerPerf = !isFarmer ? (performance as BuyerPerformanceResponse) : null;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Orders */}
        <div className="bg-card p-4 rounded-xl border border-border shadow-xs space-y-1">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>Total Orders</span>
            <Package className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-foreground">{order_outcomes.total_orders}</div>
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="text-emerald-600 font-semibold">{order_outcomes.completed} completed</span>
            <span>•</span>
            <span>{order_outcomes.active_in_progress} active</span>
          </div>
        </div>

        {/* Completion Rate */}
        <div className="bg-card p-4 rounded-xl border border-border shadow-xs space-y-1">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>Order Completion Rate</span>
            <Percent className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-foreground">
            {order_outcomes.concluded_completion_rate !== null &&
            order_outcomes.concluded_completion_rate !== undefined
              ? `${Math.round(order_outcomes.concluded_completion_rate * 100)}%`
              : "N/A"}
          </div>
          <div className="text-[11px] text-muted-foreground">
            Based on {order_outcomes.concluded_orders} concluded deals
          </div>
        </div>

        {/* Settlement Total */}
        <div className="bg-card p-4 rounded-xl border border-border shadow-xs space-y-1">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>{isFarmer ? "Settlement Recorded" : "Total Procurement Spent"}</span>
            <DollarSign className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-foreground">
            ₹{Number(payment_settlement.total_amount_recorded || 0).toLocaleString("en-IN", {
              maximumFractionDigits: 2,
            })}
          </div>
          <div className="text-[11px] text-emerald-600 font-medium">
            ₹{Number(payment_settlement.acknowledged_amount || 0).toLocaleString("en-IN", {
              maximumFractionDigits: 2,
            })}{" "}
            acknowledged
          </div>
        </div>

        {/* Average Reputation */}
        <div className="bg-card p-4 rounded-xl border border-border shadow-xs space-y-1">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>Marketplace Rating</span>
            <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
          </div>
          <div className="text-2xl font-bold text-foreground">
            {performance.average_rating ? performance.average_rating.toFixed(1) : "0.0"}
          </div>
          <div className="text-[11px] text-muted-foreground">
            From {performance.total_reviews_received} verified{" "}
            {performance.total_reviews_received === 1 ? "review" : "reviews"}
          </div>
        </div>
      </div>

      {/* Detailed Outcome & Fulfillment Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Orders & Settlement Breakdown */}
        <div className="bg-card p-5 rounded-xl border border-border shadow-xs space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Order Status Breakdown
          </h3>
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground">Completed Successfully</span>
              <span className="font-semibold text-emerald-600">{order_outcomes.completed}</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground">Active in Progress</span>
              <span className="font-semibold text-foreground">{order_outcomes.active_in_progress}</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground">Pending Confirmation</span>
              <span className="font-semibold text-foreground">
                {order_outcomes.pending_farmer_confirmation}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground">Cancelled Deals</span>
              <span className="font-semibold text-muted-foreground">{order_outcomes.cancelled}</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-muted-foreground">Disputed Orders</span>
              <span className="font-semibold text-destructive">{order_outcomes.disputed}</span>
            </div>
          </div>
        </div>

        {/* Right: Operational Metrics */}
        <div className="bg-card p-5 rounded-xl border border-border shadow-xs space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            {isFarmer ? "Fulfillment Quality & Inventory" : "Procurement Fulfillment & Efficiency"}
          </h3>
          <div className="space-y-2.5 text-xs">
            {farmerPerf && (
              <>
                <div className="flex justify-between items-center py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Active Listings Count</span>
                  <span className="font-semibold text-foreground">
                    {farmerPerf.active_listings_count}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Total Listings Managed</span>
                  <span className="font-semibold text-foreground">
                    {farmerPerf.total_listings_created}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Total Realized Revenue</span>
                  <span className="font-semibold text-foreground">
                    ₹{Number(farmerPerf.total_realized_revenue || 0).toLocaleString("en-IN", {
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-muted-foreground">Avg Payment Acknowledgement Delay</span>
                  <span className="font-semibold text-foreground">
                    {payment_settlement.average_acknowledgement_delay_hours !== null &&
                    payment_settlement.average_acknowledgement_delay_hours !== undefined
                      ? `${payment_settlement.average_acknowledgement_delay_hours.toFixed(1)} hrs`
                      : "N/A"}
                  </span>
                </div>
              </>
            )}

            {buyerPerf && (
              <>
                <div className="flex justify-between items-center py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Requirements Posted</span>
                  <span className="font-semibold text-foreground">
                    {buyerPerf.total_requirements_posted}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Active Requirements</span>
                  <span className="font-semibold text-foreground">
                    {buyerPerf.active_requirements_count}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Total Procurement Expenditure</span>
                  <span className="font-semibold text-foreground">
                    ₹{Number(buyerPerf.total_realized_expenditure || 0).toLocaleString("en-IN", {
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-muted-foreground">Disputed Payments</span>
                  <span className="font-semibold text-destructive">
                    {payment_settlement.disputed_count}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
