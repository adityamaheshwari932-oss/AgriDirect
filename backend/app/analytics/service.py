"""Domain service for AgriDirect Module 9: Descriptive Market Analytics.

Implements:
- Coarse count banding ("0", "1–2", "3–5", "6–10", "11+").
- Minimum diversity thresholds (k_farmers >= 3, k_buyers >= 3, N_trades >= 3).
- Participant dominance suppression for Quantity (>=50%), Value (>=50%), and joint VWAP.
- Arithmetic mean participant observation share (>=50%) and price-sum share (>=50%).
- Median participant observation share (>=50%) and point ownership check (>=40%).
- Extrema point isolation protection with sample depth (k >= 5) and clustering (>=2 within 2%).
- City-to-state geographic fallback logic.
- Unit-safe partitioning and aggregation.
- Permanent retention of audited approved requirement fulfillment records.
- Role-specific user performance dashboards.
- Platform-wide administrative oversight metrics.
"""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.analytics.schemas import (
    ActiveDemandSummary,
    BuyerPerformanceResponse,
    ConcludedDemandAudit,
    DemandSummaryResponse,
    FarmerPerformanceResponse,
    ListedSupplySummary,
    MarketSummaryResponse,
    OrderOutcomeBreakdown,
    PaymentSettlementBreakdown,
    PlatformAnalyticsResponse,
    PlatformBuyerDemandOverview,
    PlatformListedSupplyOverview,
    PlatformPaymentVelocity,
    PlatformUserEngagement,
    PrivacyMeta,
    ProvenanceMeta,
    RealizedTradesSummary,
    TopCommodityPerformance,
)
from app.models.listing import ProduceListing
from app.models.order import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_DISPUTED,
    ORDER_STATUS_PAYMENT_PENDING,
    ORDER_STATUS_PAYMENT_RECORDED,
    ORDER_STATUS_PENDING,
)
from app.models.payment import (
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
)
from app.models.requirement import (
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
)


def to_count_band(n: int) -> str:
    """Format an exact integer count into an approved privacy-preserving coarse count band.

    Bands:
    - 0 -> "0"
    - 1 to 2 -> "1–2"
    - 3 to 5 -> "3–5"
    - 6 to 10 -> "6–10"
    - 11 or more -> "11+"
    """
    if n <= 0:
        return "0"
    elif n in (1, 2):
        return "1–2"
    elif 3 <= n <= 5:
        return "3–5"
    elif 6 <= n <= 10:
        return "6–10"
    else:
        return "11+"


class AnalyticsService:
    """Orchestrates analytics computations with strict statistical privacy controls."""

    # -----------------------------------------------------------------------
    # Date and Filter Normalization Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _normalize_date_boundaries(
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Convert inclusive calendar dates to UTC timestamp half-open interval [start, end + 1 day)."""
        start_dt = (
            datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            if start_date
            else None
        )
        end_dt = (
            datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
            if end_date
            else None
        )
        return start_dt, end_dt

    # -----------------------------------------------------------------------
    # 1. Market Summary (Public / Authenticated)
    # -----------------------------------------------------------------------

    @classmethod
    def get_market_summary(
        cls,
        db: Session,
        *,
        product_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        unit: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> MarketSummaryResponse:
        """Compute privacy-preserved market summary for listed supply and completed trades."""
        start_dt, end_dt = cls._normalize_date_boundaries(start_date, end_date)

        # Geographic fallback resolution
        geo_level: str = "national"
        fallback_triggered: bool = False
        effective_state: Optional[str] = state
        effective_city: Optional[str] = city

        if city:
            # Query candidate trades in this specific city to test diversity
            raw_city_trades = AnalyticsRepository.get_realized_trade_line_items(
                db,
                product_name=product_name,
                category_id=category_id,
                state=state,
                city=city,
                unit=unit,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            distinct_farmers_city = len({t["farmer_id"] for t in raw_city_trades})
            distinct_buyers_city = len({t["buyer_id"] for t in raw_city_trades})

            # If city slice does not satisfy diversity, broaden to state
            if distinct_farmers_city < 3 or distinct_buyers_city < 3:
                # Resolve state if not provided
                if not effective_state and raw_city_trades:
                    effective_state = raw_city_trades[0].get("state")

                if effective_state:
                    effective_city = None
                    fallback_triggered = True
                    geo_level = "state"
                else:
                    geo_level = "city"
            else:
                geo_level = "city"
        elif state:
            geo_level = "state"
        else:
            geo_level = "national"

        # Fetch records using effective geographic filters
        listed_records = AnalyticsRepository.get_listed_supply_records(
            db,
            product_name=product_name,
            category_id=category_id,
            state=effective_state,
            city=effective_city,
            unit=unit,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        trade_items = AnalyticsRepository.get_realized_trade_line_items(
            db,
            product_name=product_name,
            category_id=category_id,
            state=effective_state,
            city=effective_city,
            unit=unit,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        # Evaluate listed supply
        supply_summary = cls._evaluate_listed_supply(listed_records, requested_unit=unit)

        # Evaluate realized trades
        trades_summary = cls._evaluate_realized_trades(trade_items, requested_unit=unit)

        provenance = ProvenanceMeta(
            generated_at=datetime.now(timezone.utc),
            query_filters={
                "product_name": product_name,
                "category_id": str(category_id) if category_id else None,
                "state": state,
                "city": city,
                "unit": unit,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            geographic_level_applied=geo_level,  # type: ignore[arg-type]
            geographic_fallback_triggered=fallback_triggered,
            category_attribution_source="current_listing_metadata_approximate",
            is_historical_snapshot=False,
        )

        return MarketSummaryResponse(
            provenance=provenance,
            listed_supply=supply_summary,
            realized_trades=trades_summary,
        )

    @classmethod
    def _evaluate_listed_supply(
        cls,
        listings: List[ProduceListing],
        requested_unit: Optional[str] = None,
    ) -> ListedSupplySummary:
        """Process supply listings with privacy checks and dominance rules."""
        if not listings:
            return ListedSupplySummary(
                unit=requested_unit,
                total_listings_count=None,
                total_listings_band="0",
                distinct_farmers_count=None,
                distinct_farmers_band="0",
                total_listed_quantity=None,
                average_asking_price=None,
                min_asking_price=None,
                max_asking_price=None,
                privacy=PrivacyMeta(
                    is_suppressed=True,
                    suppression_reason="INSUFFICIENT_PARTICIPANTS",
                    distinct_farmers_band="0",
                    distinct_buyers_band="0",
                    observations_count_band="0",
                    quantity_suppressed=True,
                    gross_value_suppressed=True,
                    vwap_suppressed=True,
                    arithmetic_mean_suppressed=True,
                    median_suppressed=True,
                    min_price_suppressed=True,
                    max_price_suppressed=True,
                ),
            )

        # Unit partitioning: if no unit requested, choose dominant unit
        unit_counts: Dict[str, int] = defaultdict(int)
        for l in listings:
            unit_counts[l.unit] += 1
        active_unit = requested_unit or max(unit_counts.keys(), key=lambda u: unit_counts[u])
        matched_listings = [l for l in listings if l.unit.lower() == active_unit.lower()]

        n_listings = len(matched_listings)
        distinct_farmers = {l.farmer_id for l in matched_listings}
        k_farmers = len(distinct_farmers)

        # Diversity test: >= 3 distinct farmers and >= 3 listings
        if k_farmers < 3 or n_listings < 3:
            return ListedSupplySummary(
                unit=active_unit,
                total_listings_count=None,
                total_listings_band=to_count_band(n_listings),
                distinct_farmers_count=None,
                distinct_farmers_band=to_count_band(k_farmers),
                total_listed_quantity=None,
                average_asking_price=None,
                min_asking_price=None,
                max_asking_price=None,
                privacy=PrivacyMeta(
                    is_suppressed=True,
                    suppression_reason="INSUFFICIENT_PARTICIPANTS",
                    distinct_farmers_band=to_count_band(k_farmers),
                    distinct_buyers_band="0",
                    observations_count_band=to_count_band(n_listings),
                    quantity_suppressed=True,
                    gross_value_suppressed=True,
                    vwap_suppressed=True,
                    arithmetic_mean_suppressed=True,
                    median_suppressed=True,
                    min_price_suppressed=True,
                    max_price_suppressed=True,
                ),
            )

        # Diversity passed: check participant volume concentration
        total_qty = sum((l.available_quantity for l in matched_listings), Decimal("0.000"))
        farmer_quantities: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        for l in matched_listings:
            farmer_quantities[l.farmer_id] += l.available_quantity

        max_farmer_share = (
            max(farmer_quantities.values()) / total_qty if total_qty > 0 else Decimal("0")
        )
        qty_suppressed = max_farmer_share >= Decimal("0.50")

        prices = [Decimal(str(l.price_per_unit)) for l in matched_listings]
        avg_price = round(sum(prices) / len(prices), 2) if prices else None
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None

        return ListedSupplySummary(
            unit=active_unit,
            total_listings_count=n_listings,
            total_listings_band=to_count_band(n_listings),
            distinct_farmers_count=k_farmers,
            distinct_farmers_band=to_count_band(k_farmers),
            total_listed_quantity=None if qty_suppressed else total_qty,
            average_asking_price=avg_price,
            min_asking_price=min_price,
            max_asking_price=max_price,
            privacy=PrivacyMeta(
                is_suppressed=qty_suppressed,
                suppression_reason="PARTICIPANT_DOMINANCE" if qty_suppressed else None,
                distinct_farmers_band=to_count_band(k_farmers),
                distinct_buyers_band=None,
                observations_count_band=to_count_band(n_listings),
                quantity_suppressed=qty_suppressed,
                gross_value_suppressed=False,
                vwap_suppressed=False,
                arithmetic_mean_suppressed=False,
                median_suppressed=False,
                min_price_suppressed=False,
                max_price_suppressed=False,
            ),
        )

    @classmethod
    def _evaluate_realized_trades(
        cls,
        items: List[Dict[str, Any]],
        requested_unit: Optional[str] = None,
    ) -> RealizedTradesSummary:
        """Process completed order line items with full Version 2.5 privacy protections."""
        if not items:
            return RealizedTradesSummary(
                unit=requested_unit,
                total_trades_count=None,
                total_trades_band="0",
                distinct_farmers_count=None,
                distinct_farmers_band="0",
                distinct_buyers_count=None,
                distinct_buyers_band="0",
                total_quantity_traded=None,
                total_gross_value=None,
                vwap=None,
                arithmetic_mean_price=None,
                median_price=None,
                min_price=None,
                max_price=None,
                privacy=PrivacyMeta(
                    is_suppressed=True,
                    suppression_reason="INSUFFICIENT_PARTICIPANTS",
                    distinct_farmers_band="0",
                    distinct_buyers_band="0",
                    observations_count_band="0",
                    quantity_suppressed=True,
                    gross_value_suppressed=True,
                    vwap_suppressed=True,
                    arithmetic_mean_suppressed=True,
                    median_suppressed=True,
                    min_price_suppressed=True,
                    max_price_suppressed=True,
                ),
            )

        # Unit partitioning: if no unit specified, select dominant unit
        unit_counts: Dict[str, int] = defaultdict(int)
        for it in items:
            unit_counts[it["unit"]] += 1
        active_unit = requested_unit or max(unit_counts.keys(), key=lambda u: unit_counts[u])
        matched_items = [it for it in items if it["unit"].lower() == active_unit.lower()]

        if not matched_items:
            return RealizedTradesSummary(
                unit=active_unit,
                total_trades_count=None,
                total_trades_band="0",
                distinct_farmers_count=None,
                distinct_farmers_band="0",
                distinct_buyers_count=None,
                distinct_buyers_band="0",
                total_quantity_traded=None,
                total_gross_value=None,
                vwap=None,
                arithmetic_mean_price=None,
                median_price=None,
                min_price=None,
                max_price=None,
                privacy=PrivacyMeta(
                    is_suppressed=True,
                    suppression_reason="INSUFFICIENT_PARTICIPANTS",
                    distinct_farmers_band="0",
                    distinct_buyers_band="0",
                    observations_count_band="0",
                    quantity_suppressed=True,
                    gross_value_suppressed=True,
                    vwap_suppressed=True,
                    arithmetic_mean_suppressed=True,
                    median_suppressed=True,
                    min_price_suppressed=True,
                    max_price_suppressed=True,
                ),
            )

        distinct_orders = {it["order_id"] for it in matched_items}
        distinct_farmers = {it["farmer_id"] for it in matched_items}
        distinct_buyers = {it["buyer_id"] for it in matched_items}

        n_trades = len(distinct_orders)
        n_items = len(matched_items)
        k_farmers = len(distinct_farmers)
        k_buyers = len(distinct_buyers)

        # -------------------------------------------------------------------
        # Rule 1: Diversity Thresholds (k_f >= 3, k_b >= 3, N_trades >= 3)
        # -------------------------------------------------------------------
        if k_farmers < 3 or k_buyers < 3 or n_trades < 3:
            return RealizedTradesSummary(
                unit=active_unit,
                total_trades_count=None,
                total_trades_band=to_count_band(n_trades),
                distinct_farmers_count=None,
                distinct_farmers_band=to_count_band(k_farmers),
                distinct_buyers_count=None,
                distinct_buyers_band=to_count_band(k_buyers),
                total_quantity_traded=None,
                total_gross_value=None,
                vwap=None,
                arithmetic_mean_price=None,
                median_price=None,
                min_price=None,
                max_price=None,
                privacy=PrivacyMeta(
                    is_suppressed=True,
                    suppression_reason="INSUFFICIENT_PARTICIPANTS",
                    distinct_farmers_band=to_count_band(k_farmers),
                    distinct_buyers_band=to_count_band(k_buyers),
                    observations_count_band=to_count_band(n_trades),
                    quantity_suppressed=True,
                    gross_value_suppressed=True,
                    vwap_suppressed=True,
                    arithmetic_mean_suppressed=True,
                    median_suppressed=True,
                    min_price_suppressed=True,
                    max_price_suppressed=True,
                ),
            )

        # Diversity passed! Unsuppressed participant counts and bands are retained
        total_qty = sum((Decimal(str(it["quantity"])) for it in matched_items), Decimal("0.000"))
        total_val = sum((Decimal(str(it["subtotal"])) for it in matched_items), Decimal("0.00"))

        # -------------------------------------------------------------------
        # Rule 2: Metric-Specific Dominance & Influence Checks
        # -------------------------------------------------------------------

        # A. Traded Quantity Dominance (>= 50%)
        farmer_qty: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        buyer_qty: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        for it in matched_items:
            q = Decimal(str(it["quantity"]))
            farmer_qty[it["farmer_id"]] += q
            buyer_qty[it["buyer_id"]] += q

        max_f_q_share = (
            max(farmer_qty.values()) / total_qty if total_qty > Decimal("0") else Decimal("0")
        )
        max_b_q_share = (
            max(buyer_qty.values()) / total_qty if total_qty > Decimal("0") else Decimal("0")
        )
        quantity_suppressed = max(max_f_q_share, max_b_q_share) >= Decimal("0.50")

        # B. Traded Value Dominance (>= 50%)
        farmer_val: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        buyer_val: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        for it in matched_items:
            v = Decimal(str(it["subtotal"]))
            farmer_val[it["farmer_id"]] += v
            buyer_val[it["buyer_id"]] += v

        max_f_v_share = (
            max(farmer_val.values()) / total_val if total_val > Decimal("0") else Decimal("0")
        )
        max_b_v_share = (
            max(buyer_val.values()) / total_val if total_val > Decimal("0") else Decimal("0")
        )
        gross_value_suppressed = max(max_f_v_share, max_b_v_share) >= Decimal("0.50")

        # C. VWAP (Requires BOTH quantity and monetary dominance to pass)
        vwap_suppressed = quantity_suppressed or gross_value_suppressed or total_qty <= Decimal("0")
        vwap_val = round(total_val / total_qty, 2) if not vwap_suppressed else None

        # D. Arithmetic Mean Influence (Observation share >= 50% OR Price-sum share >= 50%)
        p_sum = sum((Decimal(str(it["unit_price"])) for it in matched_items), Decimal("0.00"))
        f_obs_counts: Dict[uuid.UUID, int] = defaultdict(int)
        b_obs_counts: Dict[uuid.UUID, int] = defaultdict(int)
        f_price_sums: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        b_price_sums: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)

        for it in matched_items:
            p = Decimal(str(it["unit_price"]))
            f_obs_counts[it["farmer_id"]] += 1
            b_obs_counts[it["buyer_id"]] += 1
            f_price_sums[it["farmer_id"]] += p
            b_price_sums[it["buyer_id"]] += p

        max_obs_share = max(
            max(f_obs_counts.values()) / n_items if n_items > 0 else 0,
            max(b_obs_counts.values()) / n_items if n_items > 0 else 0,
        )
        max_price_share = max(
            max(f_price_sums.values()) / p_sum if p_sum > Decimal("0") else Decimal("0"),
            max(b_price_sums.values()) / p_sum if p_sum > Decimal("0") else Decimal("0"),
        )
        arithmetic_mean_suppressed = (max_obs_share >= 0.50) or (max_price_share >= Decimal("0.50"))
        mean_val = round(p_sum / n_items, 2) if not arithmetic_mean_suppressed else None

        # E. Median Dominance & Point Ownership Check
        sorted_items = sorted(matched_items, key=lambda x: Decimal(str(x["unit_price"])))
        median_suppressed: bool = False
        median_val: Optional[Decimal] = None

        if max_obs_share >= 0.50:
            median_suppressed = True
        else:
            if n_items % 2 == 1:
                mid_item = sorted_items[n_items // 2]
                f_mid_share = f_obs_counts[mid_item["farmer_id"]] / n_items
                b_mid_share = b_obs_counts[mid_item["buyer_id"]] / n_items
                if f_mid_share >= 0.40 or b_mid_share >= 0.40:
                    median_suppressed = True
                else:
                    median_val = round(Decimal(str(mid_item["unit_price"])), 2)
            else:
                m1 = sorted_items[n_items // 2 - 1]
                m2 = sorted_items[n_items // 2]
                shares = [
                    f_obs_counts[m1["farmer_id"]] / n_items,
                    b_obs_counts[m1["buyer_id"]] / n_items,
                    f_obs_counts[m2["farmer_id"]] / n_items,
                    b_obs_counts[m2["buyer_id"]] / n_items,
                ]
                if any(s >= 0.40 for s in shares):
                    median_suppressed = True
                else:
                    p1 = Decimal(str(m1["unit_price"]))
                    p2 = Decimal(str(m2["unit_price"]))
                    median_val = round((p1 + p2) / Decimal("2"), 2)

        # F. Extrema Point Isolation Protection (P_min, P_max)
        min_price_suppressed: bool = False
        max_price_suppressed: bool = False
        min_price_val: Optional[Decimal] = None
        max_price_val: Optional[Decimal] = None

        # Sample size depth requirement: k_farmers >= 5 AND k_buyers >= 5
        if k_farmers < 5 or k_buyers < 5:
            min_price_suppressed = True
            max_price_suppressed = True
        else:
            # Check P_min clustering within 2%
            p_min = Decimal(str(sorted_items[0]["unit_price"]))
            threshold_min = p_min * Decimal("1.02")
            min_cluster = [it for it in matched_items if Decimal(str(it["unit_price"])) <= threshold_min]
            distinct_f_min = {it["farmer_id"] for it in min_cluster}
            distinct_b_min = {it["buyer_id"] for it in min_cluster}

            if len(distinct_f_min) >= 2 and len(distinct_b_min) >= 2:
                min_price_val = round(p_min, 2)
            else:
                min_price_suppressed = True

            # Check P_max clustering within 2%
            p_max = Decimal(str(sorted_items[-1]["unit_price"]))
            threshold_max = p_max * Decimal("0.98")
            max_cluster = [it for it in matched_items if Decimal(str(it["unit_price"])) >= threshold_max]
            distinct_f_max = {it["farmer_id"] for it in max_cluster}
            distinct_b_max = {it["buyer_id"] for it in max_cluster}

            if len(distinct_f_max) >= 2 and len(distinct_b_max) >= 2:
                max_price_val = round(p_max, 2)
            else:
                max_price_suppressed = True

        any_metric_suppressed = any([
            quantity_suppressed,
            gross_value_suppressed,
            vwap_suppressed,
            arithmetic_mean_suppressed,
            median_suppressed,
            min_price_suppressed,
            max_price_suppressed,
        ])

        return RealizedTradesSummary(
            unit=active_unit,
            total_trades_count=n_trades,
            total_trades_band=to_count_band(n_trades),
            distinct_farmers_count=k_farmers,
            distinct_farmers_band=to_count_band(k_farmers),
            distinct_buyers_count=k_buyers,
            distinct_buyers_band=to_count_band(k_buyers),
            total_quantity_traded=None if quantity_suppressed else total_qty,
            total_gross_value=None if gross_value_suppressed else total_val,
            vwap=vwap_val,
            arithmetic_mean_price=mean_val,
            median_price=median_val,
            min_price=min_price_val,
            max_price=max_price_val,
            privacy=PrivacyMeta(
                is_suppressed=any_metric_suppressed,
                suppression_reason="PARTICIPANT_DOMINANCE" if any_metric_suppressed else None,
                distinct_farmers_band=to_count_band(k_farmers),
                distinct_buyers_band=to_count_band(k_buyers),
                observations_count_band=to_count_band(n_trades),
                quantity_suppressed=quantity_suppressed,
                gross_value_suppressed=gross_value_suppressed,
                vwap_suppressed=vwap_suppressed,
                arithmetic_mean_suppressed=arithmetic_mean_suppressed,
                median_suppressed=median_suppressed,
                min_price_suppressed=min_price_suppressed,
                max_price_suppressed=max_price_suppressed,
            ),
        )

    # -----------------------------------------------------------------------
    # 2. Demand Summary (Public / Authenticated)
    # -----------------------------------------------------------------------

    @classmethod
    def get_demand_summary(
        cls,
        db: Session,
        *,
        product_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        unit: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> DemandSummaryResponse:
        """Compute active buyer procurement demand and permanently audited fulfillment."""
        start_dt, end_dt = cls._normalize_date_boundaries(start_date, end_date)

        # Geographic resolution
        geo_level: str = "national"
        fallback_triggered: bool = False
        effective_state = state
        effective_city = city

        if city:
            raw_city_reqs = AnalyticsRepository.get_active_demand_records(
                db,
                product_name=product_name,
                category_id=category_id,
                state=state,
                city=city,
                unit=unit,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            distinct_buyers_city = len({r.buyer_id for r in raw_city_reqs})
            if distinct_buyers_city < 3:
                if not effective_state and raw_city_reqs:
                    effective_state = raw_city_reqs[0].destination_state
                if effective_state:
                    effective_city = None
                    fallback_triggered = True
                    geo_level = "state"
                else:
                    geo_level = "city"
            else:
                geo_level = "city"
        elif state:
            geo_level = "state"

        active_reqs = AnalyticsRepository.get_active_demand_records(
            db,
            product_name=product_name,
            category_id=category_id,
            state=effective_state,
            city=effective_city,
            unit=unit,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        # Unit partitioning for active demand
        active_unit = unit
        if not active_unit and active_reqs:
            unit_counts: Dict[str, int] = defaultdict(int)
            for r in active_reqs:
                unit_counts[r.unit] += 1
            active_unit = max(unit_counts.keys(), key=lambda u: unit_counts[u])

        matched_reqs = (
            [r for r in active_reqs if r.unit.lower() == active_unit.lower()]
            if active_unit
            else active_reqs
        )

        n_reqs = len(matched_reqs)
        distinct_buyers = {r.buyer_id for r in matched_reqs}
        k_buyers = len(distinct_buyers)

        if k_buyers < 3 or n_reqs < 3:
            active_demand = ActiveDemandSummary(
                unit=active_unit,
                total_requirements_count=None,
                total_requirements_band=to_count_band(n_reqs),
                distinct_buyers_count=None,
                distinct_buyers_band=to_count_band(k_buyers),
                total_demanded_quantity=None,
                negotiable_requirements_count=None,
                exact_price_requirements_count=None,
                average_target_price=None,
                privacy=PrivacyMeta(
                    is_suppressed=True,
                    suppression_reason="INSUFFICIENT_PARTICIPANTS",
                    distinct_farmers_band="0",
                    distinct_buyers_band=to_count_band(k_buyers),
                    observations_count_band=to_count_band(n_reqs),
                    quantity_suppressed=True,
                    gross_value_suppressed=True,
                    vwap_suppressed=True,
                    arithmetic_mean_suppressed=True,
                    median_suppressed=True,
                    min_price_suppressed=True,
                    max_price_suppressed=True,
                ),
            )
        else:
            total_demanded = sum(
                (r.remaining_quantity for r in matched_reqs), Decimal("0.000")
            )
            # Dominance test on buyer requested volume
            buyer_demand: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
            for r in matched_reqs:
                buyer_demand[r.buyer_id] += r.remaining_quantity
            max_b_share = (
                max(buyer_demand.values()) / total_demanded
                if total_demanded > Decimal("0")
                else Decimal("0")
            )
            demand_qty_suppressed = max_b_share >= Decimal("0.50")

            negotiable_count = sum(
                1 for r in matched_reqs if r.price_condition == PRICE_CONDITION_NEGOTIABLE
            )
            exact_count = sum(
                1 for r in matched_reqs if r.price_condition == PRICE_CONDITION_EXACT
            )

            target_prices = [
                Decimal(str(r.target_price_per_unit))
                for r in matched_reqs
                if r.target_price_per_unit is not None
            ]
            avg_target = (
                round(sum(target_prices) / len(target_prices), 2)
                if target_prices
                else None
            )

            active_demand = ActiveDemandSummary(
                unit=active_unit,
                total_requirements_count=n_reqs,
                total_requirements_band=to_count_band(n_reqs),
                distinct_buyers_count=k_buyers,
                distinct_buyers_band=to_count_band(k_buyers),
                total_demanded_quantity=None if demand_qty_suppressed else total_demanded,
                negotiable_requirements_count=negotiable_count,
                exact_price_requirements_count=exact_count,
                average_target_price=avg_target,
                privacy=PrivacyMeta(
                    is_suppressed=demand_qty_suppressed,
                    suppression_reason="PARTICIPANT_DOMINANCE" if demand_qty_suppressed else None,
                    distinct_farmers_band=None,
                    distinct_buyers_band=to_count_band(k_buyers),
                    observations_count_band=to_count_band(n_reqs),
                    quantity_suppressed=demand_qty_suppressed,
                    gross_value_suppressed=False,
                    vwap_suppressed=False,
                    arithmetic_mean_suppressed=False,
                    median_suppressed=False,
                    min_price_suppressed=False,
                    max_price_suppressed=False,
                ),
            )

        # Permanent Audited Fulfillment & Closed Residuals
        appr_vol, appr_cnt, res_vol = AnalyticsRepository.get_concluded_demand_audit(
            db,
            product_name=product_name,
            category_id=category_id,
            state=effective_state,
            city=effective_city,
            unit=active_unit,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        concluded_audit = ConcludedDemandAudit(
            unit=active_unit,
            audited_approved_fulfillment_quantity=appr_vol,
            approved_fulfillments_count=appr_cnt,
            closed_residual_unfulfilled_quantity=res_vol,
            includes_soft_deleted_requirements=True,
            audit_note=(
                "Approved requirement fulfillments are permanently retained regardless "
                "of parent requirement closure or deletion."
            ),
        )

        provenance = ProvenanceMeta(
            generated_at=datetime.now(timezone.utc),
            query_filters={
                "product_name": product_name,
                "category_id": str(category_id) if category_id else None,
                "state": state,
                "city": city,
                "unit": unit,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            geographic_level_applied=geo_level,  # type: ignore[arg-type]
            geographic_fallback_triggered=fallback_triggered,
            category_attribution_source="current_listing_metadata_approximate",
            is_historical_snapshot=False,
        )

        return DemandSummaryResponse(
            provenance=provenance,
            active_demand=active_demand,
            concluded_demand_audit=concluded_audit,
        )

    # -----------------------------------------------------------------------
    # 3. User Performance (Authenticated Farmer / Buyer)
    # -----------------------------------------------------------------------

    @classmethod
    def get_user_performance(
        cls,
        db: Session,
        *,
        user_id: uuid.UUID,
        role: str,
    ) -> Any:
        """Generate role-specialized performance metrics for farmers or commercial buyers."""
        if role == "farmer":
            return cls._get_farmer_performance(db, user_id)
        elif role == "buyer":
            return cls._get_buyer_performance(db, user_id)
        else:
            raise ValueError(f"Performance analytics unsupported for role: '{role}'")

    @classmethod
    def _compute_order_outcomes(cls, status_counts: Dict[str, int]) -> OrderOutcomeBreakdown:
        """Classify order statuses into Version 2.1 two-tier outcome shares and concluded rates."""
        pending = status_counts.get(ORDER_STATUS_PENDING, 0)
        in_progress = (
            status_counts.get(ORDER_STATUS_CONFIRMED, 0)
            + status_counts.get(ORDER_STATUS_DELIVERY_ARRANGED, 0)
            + status_counts.get(ORDER_STATUS_PAYMENT_PENDING, 0)
            + status_counts.get(ORDER_STATUS_PAYMENT_RECORDED, 0)
        )
        completed = status_counts.get(ORDER_STATUS_COMPLETED, 0)
        cancelled = status_counts.get(ORDER_STATUS_CANCELLED, 0)
        disputed = status_counts.get(ORDER_STATUS_DISPUTED, 0)

        total_orders = pending + in_progress + completed + cancelled + disputed
        concluded_orders = completed + cancelled

        # Tier 1 — All placed orders denominator
        if total_orders > 0:
            comp_share = round((completed / total_orders) * 100.0, 2)
            in_prog_share = round((in_progress / total_orders) * 100.0, 2)
            pend_share = round((pending / total_orders) * 100.0, 2)
            disp_freq = round((disputed / total_orders) * 100.0, 2)
            canc_share = round((cancelled / total_orders) * 100.0, 2)
        else:
            comp_share = None
            in_prog_share = None
            pend_share = None
            disp_freq = None
            canc_share = None

        # Tier 2 — Concluded orders denominator
        if concluded_orders > 0:
            concl_comp_rate = round((completed / concluded_orders) * 100.0, 2)
            concl_canc_rate = round((cancelled / concluded_orders) * 100.0, 2)
        else:
            concl_comp_rate = None
            concl_canc_rate = None

        return OrderOutcomeBreakdown(
            total_orders=total_orders,
            pending_confirmation=pending,
            in_progress=in_progress,
            completed=completed,
            cancelled=cancelled,
            currently_disputed=disputed,
            completed_order_share=comp_share,
            in_progress_share=in_prog_share,
            pending_share=pend_share,
            dispute_frequency=disp_freq,
            cancelled_order_share=canc_share,
            concluded_orders=concluded_orders,
            concluded_completion_rate=concl_comp_rate,
            concluded_cancellation_rate=concl_canc_rate,
        )

    @classmethod
    def _compute_payment_settlement(
        cls,
        records: List[Dict[str, Any]],
    ) -> PaymentSettlementBreakdown:
        """Compute personal external payment settlement metrics and acknowledgement delay."""
        total_count = len(records)
        total_recorded = sum((Decimal(str(r["amount"])) for r in records), Decimal("0.00"))

        ack_records = [r for r in records if r["status"] == PAYMENT_STATUS_ACKNOWLEDGED]
        ack_count = len(ack_records)
        ack_amount = sum((Decimal(str(r["amount"])) for r in ack_records), Decimal("0.00"))

        disp_records = [r for r in records if r["status"] == PAYMENT_STATUS_DISPUTED]
        disp_count = len(disp_records)
        disp_amount = sum((Decimal(str(r["amount"])) for r in disp_records), Decimal("0.00"))

        pend_records = [r for r in records if r["status"] == PAYMENT_STATUS_RECORDED]
        pend_count = len(pend_records)
        pend_amount = sum((Decimal(str(r["amount"])) for r in pend_records), Decimal("0.00"))

        # Elapsed hours from payment creation to acknowledgement
        delays: List[float] = []
        for r in ack_records:
            if r.get("ack_at") and r.get("created_at"):
                diff = (r["ack_at"] - r["created_at"]).total_seconds() / 3600.0
                if diff >= 0:
                    delays.append(diff)

        avg_delay = round(sum(delays) / len(delays), 2) if delays else None

        return PaymentSettlementBreakdown(
            total_payments_count=total_count,
            total_amount_recorded=total_recorded,
            acknowledged_count=ack_count,
            acknowledged_amount=ack_amount,
            disputed_count=disp_count,
            disputed_amount=disp_amount,
            pending_acknowledgement_count=pend_count,
            pending_acknowledgement_amount=pend_amount,
            average_acknowledgement_delay_hours=avg_delay,
        )

    @classmethod
    def _get_farmer_performance(
        cls,
        db: Session,
        farmer_id: uuid.UUID,
    ) -> FarmerPerformanceResponse:
        """Build personal performance report for a farmer."""
        raw = AnalyticsRepository.get_farmer_performance_data(db, farmer_id)
        outcomes = cls._compute_order_outcomes(raw["status_counts"])
        settlement = cls._compute_payment_settlement(raw["payment_records"])

        # Volume by unit & total revenue
        vol_by_unit: Dict[str, Decimal] = defaultdict(Decimal)
        total_revenue = Decimal("0.00")
        crop_stats: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
            lambda: {"quantity": Decimal("0.000"), "gross_amount": Decimal("0.00"), "orders": set()}
        )

        for item in raw["sales_items"]:
            q = Decimal(str(item["quantity"]))
            v = Decimal(str(item["subtotal"]))
            u = item["unit"]
            p_name = item["product_name"]

            vol_by_unit[u] += q
            total_revenue += v

            crop_stats[(p_name, u)]["quantity"] += q
            crop_stats[(p_name, u)]["gross_amount"] += v
            crop_stats[(p_name, u)]["orders"].add(item["order_id"])

        top_commodities: List[TopCommodityPerformance] = []
        for (name, u), stats in sorted(
            crop_stats.items(),
            key=lambda x: x[1]["gross_amount"],
            reverse=True,
        )[:5]:
            top_commodities.append(
                TopCommodityPerformance(
                    product_name=name,
                    unit=u,
                    quantity=stats["quantity"],
                    gross_amount=stats["gross_amount"],
                    order_count=len(stats["orders"]),
                )
            )

        return FarmerPerformanceResponse(
            user_id=farmer_id,
            role="farmer",
            total_listings_created=raw["total_listings"],
            active_listings_count=raw["active_listings"],
            order_outcomes=outcomes,
            realized_sales_volume_by_unit=dict(vol_by_unit),
            total_realized_revenue=total_revenue,
            top_commodities=top_commodities,
            payment_settlement=settlement,
            average_rating=round(raw["reviews_average"], 2) if raw["reviews_count"] > 0 else None,
            total_reviews_received=raw["reviews_count"],
        )

    @classmethod
    def _get_buyer_performance(
        cls,
        db: Session,
        buyer_id: uuid.UUID,
    ) -> BuyerPerformanceResponse:
        """Build personal performance report for a commercial buyer."""
        raw = AnalyticsRepository.get_buyer_performance_data(db, buyer_id)
        outcomes = cls._compute_order_outcomes(raw["status_counts"])
        settlement = cls._compute_payment_settlement(raw["payment_records"])

        vol_by_unit: Dict[str, Decimal] = defaultdict(Decimal)
        total_expenditure = Decimal("0.00")
        crop_stats: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
            lambda: {"quantity": Decimal("0.000"), "gross_amount": Decimal("0.00"), "orders": set()}
        )

        for item in raw["purchase_items"]:
            q = Decimal(str(item["quantity"]))
            v = Decimal(str(item["subtotal"]))
            u = item["unit"]
            p_name = item["product_name"]

            vol_by_unit[u] += q
            total_expenditure += v

            crop_stats[(p_name, u)]["quantity"] += q
            crop_stats[(p_name, u)]["gross_amount"] += v
            crop_stats[(p_name, u)]["orders"].add(item["order_id"])

        top_commodities: List[TopCommodityPerformance] = []
        for (name, u), stats in sorted(
            crop_stats.items(),
            key=lambda x: x[1]["gross_amount"],
            reverse=True,
        )[:5]:
            top_commodities.append(
                TopCommodityPerformance(
                    product_name=name,
                    unit=u,
                    quantity=stats["quantity"],
                    gross_amount=stats["gross_amount"],
                    order_count=len(stats["orders"]),
                )
            )

        return BuyerPerformanceResponse(
            user_id=buyer_id,
            role="buyer",
            total_requirements_posted=raw["total_requirements"],
            active_requirements_count=raw["active_requirements"],
            order_outcomes=outcomes,
            realized_purchase_volume_by_unit=dict(vol_by_unit),
            total_realized_expenditure=total_expenditure,
            top_commodities=top_commodities,
            payment_settlement=settlement,
            average_rating=round(raw["reviews_average"], 2) if raw["reviews_count"] > 0 else None,
            total_reviews_received=raw["reviews_count"],
        )

    # -----------------------------------------------------------------------
    # 4. Platform-Wide Administrative Analytics (Admin Only)
    # -----------------------------------------------------------------------

    @classmethod
    def get_platform_analytics(cls, db: Session) -> PlatformAnalyticsResponse:
        """Compute unsuppressed system-wide analytics for administrator review."""
        raw = AnalyticsRepository.get_platform_analytics_raw(db)

        # 1. Supply overview
        active_listings: List[ProduceListing] = raw["active_listings"]
        supply_qty_by_unit: Dict[str, Decimal] = defaultdict(Decimal)
        total_listed_val = Decimal("0.00")

        for l in active_listings:
            supply_qty_by_unit[l.unit] += l.available_quantity
            total_listed_val += l.available_quantity * l.price_per_unit

        supply_overview = PlatformListedSupplyOverview(
            active_listings_count=len(active_listings),
            total_active_quantity_by_unit=dict(supply_qty_by_unit),
            total_active_listed_value=round(total_listed_val, 2),
        )

        # 2. Demand overview
        active_reqs = raw["active_requirements"]
        demanded_by_unit: Dict[str, Decimal] = defaultdict(Decimal)
        for r in active_reqs:
            demanded_by_unit[r.unit] += r.remaining_quantity

        demand_overview = PlatformBuyerDemandOverview(
            active_requirements_count=len(active_reqs),
            total_demanded_quantity_by_unit=dict(demanded_by_unit),
            total_approved_fulfilled_quantity_by_unit=raw["approved_fulfillment_by_unit"],
        )

        # 3. Order outcomes
        outcomes = cls._compute_order_outcomes(raw["order_status_counts"])

        # 4. Payment velocity
        pay_records = raw["payment_records"]
        tot_pay = len(pay_records)
        ack_pay = sum(1 for p in pay_records if p["status"] == PAYMENT_STATUS_ACKNOWLEDGED)
        disp_pay = sum(1 for p in pay_records if p["status"] == PAYMENT_STATUS_DISPUTED)
        pend_pay = sum(1 for p in pay_records if p["status"] == PAYMENT_STATUS_RECORDED)

        delays = [
            (p["ack_at"] - p["created_at"]).total_seconds() / 3600.0
            for p in pay_records
            if p["status"] == PAYMENT_STATUS_ACKNOWLEDGED and p.get("ack_at") and p.get("created_at")
        ]
        avg_delay = round(sum(delays) / len(delays), 2) if delays else None
        disp_rate = round(disp_pay / tot_pay, 4) if tot_pay > 0 else None

        velocity = PlatformPaymentVelocity(
            total_payments=tot_pay,
            acknowledged_payments=ack_pay,
            disputed_payments=disp_pay,
            pending_payments=pend_pay,
            average_settlement_delay_hours=avg_delay,
            dispute_rate=disp_rate,
        )

        # 5. User engagement
        total_users = 0
        v_farmers = 0
        v_buyers = 0
        unverified = 0
        admins = 0

        for role, v_status, count in raw["user_rows"]:
            total_users += count
            if role == "admin":
                admins += count
            elif role == "farmer":
                if v_status == "verified":
                    v_farmers += count
                else:
                    unverified += count
            elif role == "buyer":
                if v_status == "verified":
                    v_buyers += count
                else:
                    unverified += count
            else:
                unverified += count

        engagement = PlatformUserEngagement(
            total_users=total_users,
            verified_farmers=v_farmers,
            verified_buyers=v_buyers,
            unverified_users=unverified,
            admin_users=admins,
        )

        return PlatformAnalyticsResponse(
            generated_at=datetime.now(timezone.utc),
            platform_gmv=raw["platform_gmv"],
            pipeline_gmv=raw["pipeline_gmv"],
            listed_supply_overview=supply_overview,
            buyer_demand_overview=demand_overview,
            order_outcomes=outcomes,
            payment_velocity=velocity,
            user_engagement=engagement,
        )

