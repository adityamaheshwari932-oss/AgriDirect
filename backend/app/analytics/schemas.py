"""Pydantic v2 schemas for AgriDirect Module 9: Descriptive Market Analytics.

Enforces:
- Strict statistical privacy metadata and coarse count banding.
- Explicit metric-specific suppression status flags.
- Complete separation of trade completion from payment settlement.
- Separation of pending farmer confirmations from in-progress orders.
- Permanent retention of audited approved requirement fulfillment.
- Traceable provenance and category attribution disclosures.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Privacy & Provenance Metadata Schemas
# ---------------------------------------------------------------------------

class ProvenanceMeta(BaseModel):
    """Execution provenance and filter resolution metadata."""

    generated_at: datetime = Field(
        ...,
        description="Timestamp in UTC when this analytical query was computed.",
    )
    query_filters: Dict[str, Any] = Field(
        ...,
        description="Normalized user query parameters applied to this analysis.",
    )
    geographic_level_applied: Literal["city", "state", "national"] = Field(
        ...,
        description="Effective geographic aggregation level used for this response.",
    )
    geographic_fallback_triggered: bool = Field(
        default=False,
        description="True if city query lacked sufficient diversity and was broadened to state.",
    )
    category_attribution_source: str = Field(
        default="current_listing_metadata_approximate",
        description="Audit disclaimer explaining line-item category linkage.",
    )
    is_historical_snapshot: bool = Field(
        default=False,
        description="False indicating current parent category metadata is referenced.",
    )

    model_config = ConfigDict(from_attributes=True)


class PrivacyMeta(BaseModel):
    """Statistical privacy disclosure and dominance suppression diagnostics."""

    is_suppressed: bool = Field(
        default=False,
        description="True if any sensitive metric or participant count in this slice was suppressed.",
    )
    suppression_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic reason: 'INSUFFICIENT_PARTICIPANTS', 'PARTICIPANT_DOMINANCE', etc.",
    )
    distinct_farmers_band: Optional[str] = Field(
        default=None,
        description="Coarse count band for distinct farmers ('0', '1–2', '3–5', '6–10', '11+').",
    )
    distinct_buyers_band: Optional[str] = Field(
        default=None,
        description="Coarse count band for distinct buyers ('0', '1–2', '3–5', '6–10', '11+').",
    )
    observations_count_band: Optional[str] = Field(
        default=None,
        description="Coarse count band for total observations or orders.",
    )
    quantity_suppressed: bool = Field(
        default=False,
        description="True if quantity traded or listed was suppressed due to participant concentration.",
    )
    gross_value_suppressed: bool = Field(
        default=False,
        description="True if transaction value was suppressed due to participant concentration.",
    )
    vwap_suppressed: bool = Field(
        default=False,
        description="True if VWAP was suppressed due to quantity or value concentration.",
    )
    arithmetic_mean_suppressed: bool = Field(
        default=False,
        description="True if arithmetic mean was suppressed due to observation or price share >= 50%.",
    )
    median_suppressed: bool = Field(
        default=False,
        description="True if median was suppressed due to observation share >= 50% or point ownership >= 40%.",
    )
    min_price_suppressed: bool = Field(
        default=False,
        description="True if min price was suppressed due to sample depth or point isolation.",
    )
    max_price_suppressed: bool = Field(
        default=False,
        description="True if max price was suppressed due to sample depth or point isolation.",
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Market Summary Schemas (Public / Authenticated)
# ---------------------------------------------------------------------------

class ListedSupplySummary(BaseModel):
    """Aggregated farmer supply metrics for active listings."""

    unit: Optional[str] = Field(
        default=None,
        description="Produce measurement unit (e.g. 'kg', 'quintal'). None if empty.",
    )
    total_listings_count: Optional[int] = Field(
        default=None,
        description="Exact count of active listings when unsuppressed; None when suppressed.",
    )
    total_listings_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of active listings ('0', '1–2', '3–5', '6–10', '11+').",
    )
    distinct_farmers_count: Optional[int] = Field(
        default=None,
        description="Exact count of distinct listing farmers when unsuppressed.",
    )
    distinct_farmers_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of distinct listing farmers.",
    )
    total_listed_quantity: Optional[Decimal] = Field(
        default=None,
        description="Sum of available produce quantity; None if suppressed or no data.",
    )
    average_asking_price: Optional[Decimal] = Field(
        default=None,
        description="Mean asking price per unit across active listings.",
    )
    min_asking_price: Optional[Decimal] = Field(
        default=None,
        description="Minimum asking price per unit.",
    )
    max_asking_price: Optional[Decimal] = Field(
        default=None,
        description="Maximum asking price per unit.",
    )
    privacy: PrivacyMeta = Field(
        ...,
        description="Privacy evaluation metadata for listed supply.",
    )

    model_config = ConfigDict(from_attributes=True)


class RealizedTradesSummary(BaseModel):
    """Aggregated transaction statistics from completed orders."""

    unit: Optional[str] = Field(
        default=None,
        description="Produce measurement unit for realized trade volume.",
    )
    total_trades_count: Optional[int] = Field(
        default=None,
        description="Exact completed trade items count when unsuppressed; None when suppressed.",
    )
    total_trades_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of completed trades.",
    )
    distinct_farmers_count: Optional[int] = Field(
        default=None,
        description="Exact distinct farmer count when unsuppressed.",
    )
    distinct_farmers_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of distinct selling farmers.",
    )
    distinct_buyers_count: Optional[int] = Field(
        default=None,
        description="Exact distinct buyer count when unsuppressed.",
    )
    distinct_buyers_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of distinct purchasing buyers.",
    )
    total_quantity_traded: Optional[Decimal] = Field(
        default=None,
        description="Realized volume traded; None if suppressed by diversity or dominance.",
    )
    total_gross_value: Optional[Decimal] = Field(
        default=None,
        description="Realized gross trade value; None if suppressed by diversity or dominance.",
    )
    vwap: Optional[Decimal] = Field(
        default=None,
        description="Volume-Weighted Average Price per unit; None if suppressed.",
    )
    arithmetic_mean_price: Optional[Decimal] = Field(
        default=None,
        description="Simple arithmetic mean trade price; None if suppressed.",
    )
    median_price: Optional[Decimal] = Field(
        default=None,
        description="Median trade price; None if suppressed.",
    )
    min_price: Optional[Decimal] = Field(
        default=None,
        description="Minimum trade price; protected against point isolation.",
    )
    max_price: Optional[Decimal] = Field(
        default=None,
        description="Maximum trade price; protected against point isolation.",
    )
    privacy: PrivacyMeta = Field(
        ...,
        description="Privacy evaluation metadata for realized trades.",
    )

    model_config = ConfigDict(from_attributes=True)


class MarketSummaryResponse(BaseModel):
    """Full response schema for GET /api/v1/analytics/market-summary."""

    provenance: ProvenanceMeta = Field(
        ...,
        description="Query provenance and filter resolution details.",
    )
    listed_supply: ListedSupplySummary = Field(
        ...,
        description="Summary of active marketplace listings.",
    )
    realized_trades: RealizedTradesSummary = Field(
        ...,
        description="Summary of completed trade transactions (no payment totals).",
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Demand Summary Schemas (Public / Authenticated)
# ---------------------------------------------------------------------------

class ActiveDemandSummary(BaseModel):
    """Aggregated buyer demand from active requirements."""

    unit: Optional[str] = Field(
        default=None,
        description="Produce measurement unit for active demand.",
    )
    total_requirements_count: Optional[int] = Field(
        default=None,
        description="Exact count of active requirements when unsuppressed.",
    )
    total_requirements_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of active requirements.",
    )
    distinct_buyers_count: Optional[int] = Field(
        default=None,
        description="Exact count of distinct active buyers when unsuppressed.",
    )
    distinct_buyers_band: Optional[str] = Field(
        default=None,
        description="Coarse count band of distinct buyers posting active requirements.",
    )
    total_demanded_quantity: Optional[Decimal] = Field(
        default=None,
        description="Sum of remaining demanded quantity across active requirements.",
    )
    negotiable_requirements_count: Optional[int] = Field(
        default=None,
        description="Count of active requirements with price_condition = 'negotiable'.",
    )
    exact_price_requirements_count: Optional[int] = Field(
        default=None,
        description="Count of active requirements with price_condition = 'exact'.",
    )
    average_target_price: Optional[Decimal] = Field(
        default=None,
        description="Average target price per unit across requirements with target price set.",
    )
    privacy: PrivacyMeta = Field(
        ...,
        description="Privacy metadata for active buyer demand.",
    )

    model_config = ConfigDict(from_attributes=True)


class ConcludedDemandAudit(BaseModel):
    """Audited fulfillment and closed residual demand accounting."""

    unit: Optional[str] = Field(
        default=None,
        description="Produce measurement unit for audited demand fulfillment.",
    )
    audited_approved_fulfillment_quantity: Decimal = Field(
        default=Decimal("0.000"),
        description="Permanently retained volume from approved requirement fulfillment records.",
    )
    approved_fulfillments_count: int = Field(
        default=0,
        description="Number of distinct approved fulfillment approval records.",
    )
    closed_residual_unfulfilled_quantity: Decimal = Field(
        default=Decimal("0.000"),
        description="Residual forfeited quantity from requirements that reached closed/expired status.",
    )
    includes_soft_deleted_requirements: bool = Field(
        default=True,
        description="Affirms approved fulfillment volume includes soft-deleted requirements.",
    )
    audit_note: str = Field(
        default="Approved requirement fulfillments are permanently retained regardless of parent requirement closure or deletion.",
        description="Accounting policy explanation for fulfillment preservation.",
    )

    model_config = ConfigDict(from_attributes=True)


class DemandSummaryResponse(BaseModel):
    """Full response schema for GET /api/v1/analytics/demand-summary."""

    provenance: ProvenanceMeta = Field(
        ...,
        description="Query provenance and filter resolution details.",
    )
    active_demand: ActiveDemandSummary = Field(
        ...,
        description="Summary of current open buyer procurement demands.",
    )
    concluded_demand_audit: ConcludedDemandAudit = Field(
        ...,
        description="Audited fulfillment volume and closed residual demand ledger.",
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# User Performance Schemas (Authenticated Farmer / Buyer)
# ---------------------------------------------------------------------------

class TopCommodityPerformance(BaseModel):
    """Performance breakdown for a single produce commodity."""

    product_name: str = Field(..., description="Name of produce commodity.")
    unit: str = Field(..., description="Measurement unit.")
    quantity: Decimal = Field(..., description="Total volume transacted.")
    gross_amount: Decimal = Field(..., description="Total monetary value.")
    order_count: int = Field(..., description="Number of distinct orders.")

    model_config = ConfigDict(from_attributes=True)


class OrderOutcomeBreakdown(BaseModel):
    """Exhaustive two-tier order lifecycle outcome classification and performance rates."""

    total_orders: int = Field(..., description="All orders associated with this user or platform.")
    pending_confirmation: int = Field(
        ...,
        description="Orders awaiting initial farmer acceptance/confirmation.",
    )
    in_progress: int = Field(
        ...,
        description="Active orders undergoing delivery coordination or payment recording.",
    )
    completed: int = Field(..., description="Successfully executed trades.")
    cancelled: int = Field(..., description="Cancelled orders.")
    currently_disputed: int = Field(..., description="Orders in active dispute resolution.")

    # Tier 1: All placed orders denominator
    completed_order_share: Optional[float] = Field(
        default=None,
        description="Completed share of all placed orders: (completed / total_orders) * 100.",
    )
    in_progress_share: Optional[float] = Field(
        default=None,
        description="In-progress share of all placed orders: (in_progress / total_orders) * 100.",
    )
    pending_share: Optional[float] = Field(
        default=None,
        description="Pending confirmation share of all placed orders: (pending_confirmation / total_orders) * 100.",
    )
    dispute_frequency: Optional[float] = Field(
        default=None,
        description="Active dispute frequency of all placed orders: (currently_disputed / total_orders) * 100.",
    )
    cancelled_order_share: Optional[float] = Field(
        default=None,
        description="Cancelled share of all placed orders: (cancelled / total_orders) * 100.",
    )

    # Tier 2: Concluded orders denominator
    concluded_orders: int = Field(
        ...,
        description="Denominator for concluded outcomes: completed + cancelled.",
    )
    concluded_completion_rate: Optional[float] = Field(
        default=None,
        description="Concluded execution rate: (completed / concluded_orders) * 100.",
    )
    concluded_cancellation_rate: Optional[float] = Field(
        default=None,
        description="Concluded cancellation rate: (cancelled / concluded_orders) * 100.",
    )

    model_config = ConfigDict(from_attributes=True)


class PaymentSettlementBreakdown(BaseModel):
    """Authenticated personal or administrative payment tracking analytics."""

    total_payments_count: int = Field(..., description="Total payment records logged.")
    total_amount_recorded: Decimal = Field(..., description="Gross amount of all recorded payments.")
    acknowledged_count: int = Field(..., description="Payments acknowledged by payee.")
    acknowledged_amount: Decimal = Field(..., description="Total acknowledged payment value.")
    disputed_count: int = Field(..., description="Payments with active complaints/disputes.")
    disputed_amount: Decimal = Field(..., description="Total disputed payment value.")
    pending_acknowledgement_count: int = Field(
        ...,
        description="Payments recorded but not yet acknowledged or disputed.",
    )
    pending_acknowledgement_amount: Decimal = Field(
        ...,
        description="Total unacknowledged payment value.",
    )
    average_acknowledgement_delay_hours: Optional[float] = Field(
        default=None,
        description="Mean elapsed hours from payment creation to acknowledgement.",
    )

    model_config = ConfigDict(from_attributes=True)


class FarmerPerformanceResponse(BaseModel):
    """Personal performance dashboard for verified farmers."""

    user_id: uuid.UUID = Field(..., description="Farmer user ID.")
    role: Literal["farmer"] = Field(default="farmer", description="User role discriminator.")
    total_listings_created: int = Field(..., description="Lifetime listings created.")
    active_listings_count: int = Field(..., description="Currently active supply listings.")
    order_outcomes: OrderOutcomeBreakdown = Field(
        ...,
        description="Classification of received customer orders.",
    )
    realized_sales_volume_by_unit: Dict[str, Decimal] = Field(
        ...,
        description="Total volume sold in completed orders, grouped by unit.",
    )
    total_realized_revenue: Decimal = Field(
        ...,
        description="Gross revenue from completed orders.",
    )
    top_commodities: List[TopCommodityPerformance] = Field(
        ...,
        description="Top selling crops by gross revenue.",
    )
    payment_settlement: PaymentSettlementBreakdown = Field(
        ...,
        description="External payment acknowledgement audit.",
    )
    average_rating: Optional[float] = Field(
        default=None,
        description="Mean reputation score from counterparty reviews.",
    )
    total_reviews_received: int = Field(
        ...,
        description="Total verified reviews received from buyers.",
    )

    model_config = ConfigDict(from_attributes=True)


class BuyerPerformanceResponse(BaseModel):
    """Personal performance dashboard for verified commercial buyers."""

    user_id: uuid.UUID = Field(..., description="Buyer user ID.")
    role: Literal["buyer"] = Field(default="buyer", description="User role discriminator.")
    total_requirements_posted: int = Field(..., description="Lifetime procurement requirements posted.")
    active_requirements_count: int = Field(..., description="Currently active buyer requirements.")
    order_outcomes: OrderOutcomeBreakdown = Field(
        ...,
        description="Classification of placed orders.",
    )
    realized_purchase_volume_by_unit: Dict[str, Decimal] = Field(
        ...,
        description="Total volume purchased in completed orders, grouped by unit.",
    )
    total_realized_expenditure: Decimal = Field(
        ...,
        description="Gross expenditure from completed orders.",
    )
    top_commodities: List[TopCommodityPerformance] = Field(
        ...,
        description="Top purchased crops by gross expenditure.",
    )
    payment_settlement: PaymentSettlementBreakdown = Field(
        ...,
        description="External payment acknowledgement audit.",
    )
    average_rating: Optional[float] = Field(
        default=None,
        description="Mean reputation score received from farmers.",
    )
    total_reviews_received: int = Field(
        ...,
        description="Total verified reviews received from farmers.",
    )

    model_config = ConfigDict(from_attributes=True)


# Polymorphic response type for /my-performance
MyPerformanceResponse = Union[FarmerPerformanceResponse, BuyerPerformanceResponse]


# ---------------------------------------------------------------------------
# Platform-Wide Administrative Analytics Schemas (Admin Only)
# ---------------------------------------------------------------------------

class PlatformListedSupplyOverview(BaseModel):
    """Marketplace-wide supply volume and inventory valuation."""

    active_listings_count: int = Field(..., description="Count of active marketplace listings.")
    total_active_quantity_by_unit: Dict[str, Decimal] = Field(
        ...,
        description="Available inventory volume grouped by unit.",
    )
    total_active_listed_value: Decimal = Field(
        ...,
        description="Total gross asking value of active inventory.",
    )

    model_config = ConfigDict(from_attributes=True)


class PlatformBuyerDemandOverview(BaseModel):
    """Marketplace-wide buyer demand and fulfillment totals."""

    active_requirements_count: int = Field(..., description="Count of open buyer requirements.")
    total_demanded_quantity_by_unit: Dict[str, Decimal] = Field(
        ...,
        description="Total remaining quantity demanded grouped by unit.",
    )
    total_approved_fulfilled_quantity_by_unit: Dict[str, Decimal] = Field(
        ...,
        description="Total fulfilled quantity permanently retained from approved records.",
    )

    model_config = ConfigDict(from_attributes=True)


class PlatformPaymentVelocity(BaseModel):
    """Platform-wide settlement timeliness and dispute tracking."""

    total_payments: int = Field(..., description="Total payment records logged across all orders.")
    acknowledged_payments: int = Field(..., description="Total payments confirmed acknowledged.")
    disputed_payments: int = Field(..., description="Total payments with complaints filed.")
    pending_payments: int = Field(..., description="Total recorded payments awaiting response.")
    average_settlement_delay_hours: Optional[float] = Field(
        default=None,
        description="Mean hours between payment record creation and acknowledgement.",
    )
    dispute_rate: Optional[float] = Field(
        default=None,
        description="Proportion of payments disputed: disputed_payments / total_payments.",
    )

    model_config = ConfigDict(from_attributes=True)


class PlatformUserEngagement(BaseModel):
    """User account distribution and verification status."""

    total_users: int = Field(..., description="Total registered platform users.")
    verified_farmers: int = Field(..., description="Active verified farmers.")
    verified_buyers: int = Field(..., description="Active verified commercial buyers.")
    unverified_users: int = Field(..., description="Users pending or without verification.")
    admin_users: int = Field(..., description="Administrative accounts.")

    model_config = ConfigDict(from_attributes=True)


class PlatformAnalyticsResponse(BaseModel):
    """Full response schema for GET /api/v1/analytics/admin/platform."""

    generated_at: datetime = Field(..., description="UTC timestamp of platform analysis calculation.")
    platform_gmv: Decimal = Field(
        ...,
        description="Gross Merchandise Value realized from completed orders.",
    )
    pipeline_gmv: Decimal = Field(
        ...,
        description="Contracted transaction value in active uncompleted orders.",
    )
    listed_supply_overview: PlatformListedSupplyOverview = Field(
        ...,
        description="Marketplace supply inventory overview.",
    )
    buyer_demand_overview: PlatformBuyerDemandOverview = Field(
        ...,
        description="Marketplace buyer demand and fulfillment overview.",
    )
    order_outcomes: OrderOutcomeBreakdown = Field(
        ...,
        description="System-wide order lifecycle execution status breakdown.",
    )
    payment_velocity: PlatformPaymentVelocity = Field(
        ...,
        description="External payment settlement velocities and dispute proportions.",
    )
    user_engagement: PlatformUserEngagement = Field(
        ...,
        description="Platform user base verification and role composition.",
    )

    model_config = ConfigDict(from_attributes=True)

