/**
 * Domain types for AgriDirect Descriptive Market Analytics (Module 9).
 * Aligned with backend Pydantic models in app.analytics.schemas.
 */

export interface ProvenanceMeta {
  generated_at: string;
  query_filters: Record<string, unknown>;
  geographic_level_applied: "city" | "state" | "national";
  geographic_fallback_triggered: boolean;
  category_attribution_source: string;
  is_historical_snapshot: boolean;
}

export interface PrivacyMeta {
  is_suppressed: boolean;
  suppression_reason?: string | null;
  distinct_farmers_band?: string | null;
  distinct_buyers_band?: string | null;
  observations_count_band?: string | null;
  quantity_suppressed: boolean;
  gross_value_suppressed: boolean;
  vwap_suppressed: boolean;
  arithmetic_mean_suppressed: boolean;
  median_suppressed: boolean;
  min_price_suppressed: boolean;
}

export interface ActiveSupplyMetrics {
  total_listings_count: number;
  total_available_quantity?: string | number | null;
  measurement_unit?: string | null;
  estimated_inventory_value?: string | number | null;
}

export interface RealizedTradesMetrics {
  total_orders_count: number;
  total_quantity_traded?: string | number | null;
  measurement_unit?: string | null;
  total_realized_value?: string | number | null;
  vwap?: string | number | null;
  arithmetic_mean?: string | number | null;
  median?: string | number | null;
  min_price?: string | number | null;
  max_price?: string | number | null;
}

export interface MarketSummaryResponse {
  provenance: ProvenanceMeta;
  privacy: PrivacyMeta;
  active_supply: ActiveSupplyMetrics;
  realized_trades: RealizedTradesMetrics;
}

export interface OpenDemandMetrics {
  total_requirements_count: number;
  total_demanded_quantity?: string | number | null;
  total_remaining_demand?: string | number | null;
  measurement_unit?: string | null;
}

export interface ApprovedFulfillmentMetrics {
  total_approvals_count: number;
  total_approved_quantity?: string | number | null;
  measurement_unit?: string | null;
}

export interface DemandSummaryResponse {
  provenance: ProvenanceMeta;
  privacy: PrivacyMeta;
  open_demand: OpenDemandMetrics;
  approved_fulfillment: ApprovedFulfillmentMetrics;
}

export interface OrderOutcomeBreakdown {
  active_in_progress: number;
  pending_farmer_confirmation: number;
  completed: number;
  cancelled: number;
  disputed: number;
  total_orders: number;
  non_pending_orders: number;
  completion_rate?: number | null;
  cancellation_rate?: number | null;
  concluded_orders: number;
  concluded_completion_rate?: number | null;
  concluded_cancellation_rate?: number | null;
}

export interface PaymentSettlementBreakdown {
  total_payments_count: number;
  total_amount_recorded: string;
  acknowledged_count: number;
  acknowledged_amount: string;
  disputed_count: number;
  disputed_amount: string;
  pending_acknowledgement_count: number;
  pending_acknowledgement_amount: string;
  average_acknowledgement_delay_hours?: number | null;
}

export interface TopCommodityPerformance {
  product_name: string;
  completed_orders_count: number;
  volume_sold?: Record<string, string> | null;
  gross_revenue?: string | null;
  gross_expenditure?: string | null;
}

export interface FarmerPerformanceResponse {
  user_id: string;
  role: "farmer";
  total_listings_created: number;
  active_listings_count: number;
  order_outcomes: OrderOutcomeBreakdown;
  realized_sales_volume_by_unit: Record<string, string>;
  total_realized_revenue: string;
  top_commodities: TopCommodityPerformance[];
  payment_settlement: PaymentSettlementBreakdown;
  average_rating?: number | null;
  total_reviews_received: number;
}

export interface BuyerPerformanceResponse {
  user_id: string;
  role: "buyer";
  total_requirements_posted: number;
  active_requirements_count: number;
  order_outcomes: OrderOutcomeBreakdown;
  realized_purchase_volume_by_unit: Record<string, string>;
  total_realized_expenditure: string;
  top_commodities: TopCommodityPerformance[];
  payment_settlement: PaymentSettlementBreakdown;
  average_rating?: number | null;
  total_reviews_received: number;
}

export type MyPerformanceResponse = FarmerPerformanceResponse | BuyerPerformanceResponse;

export interface MarketAnalyticsFilterParams {
  product_name?: string;
  category_id?: string;
  state?: string;
  city?: string;
  unit?: string;
  start_date?: string; // YYYY-MM-DD
  end_date?: string; // YYYY-MM-DD
}

