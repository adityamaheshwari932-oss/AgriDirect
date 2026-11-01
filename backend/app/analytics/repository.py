"""SQLAlchemy repository for AgriDirect Module 9: Descriptive Market Analytics.

Implements synchronous, parameterized database queries for:
- Active listed produce supply.
- Realized completed trade transactions.
- Active buyer procurement demand and permanently audited fulfillment approvals.
- Authenticated personal user performance and payment settlement histories.
- Platform-wide administrative GMV, pipeline, and engagement analytics.

Zero data modification: this module executes read queries only.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.listing import (
    ProduceCategory,
    ProduceListing,
    STATUS_ACTIVE,
)
from app.models.order import (
    DELIVERY_STATUS_ARRANGED,
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_ITEM_STATUS_CANCELLED,
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_ITEM_STATUS_DISPUTED,
    ORDER_ITEM_STATUS_FULFILLED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_DISPUTED,
    ORDER_STATUS_PAYMENT_PENDING,
    ORDER_STATUS_PAYMENT_RECORDED,
    ORDER_STATUS_PENDING,
    Order,
    OrderItem,
)
from app.models.payment import (
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    PaymentRecord,
)
from app.models.requirement import (
    BuyerRequirement,
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_EXPIRED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
)
from app.models.requirement_approval import (
    APPROVAL_STATUS_APPROVED,
    RequirementFulfillmentApproval,
)
from app.models.review import RatingReview
from app.models.user import BuyerProfile, FarmerProfile, User


class AnalyticsRepository:
    """Synchronous repository executing read-only analytical aggregations."""

    # -----------------------------------------------------------------------
    # 1. Listed Supply Queries
    # -----------------------------------------------------------------------

    @staticmethod
    def get_listed_supply_records(
        db: Session,
        *,
        product_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        unit: Optional[str] = None,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[ProduceListing]:
        """Fetch active supply listings matching criteria."""
        stmt = (
            select(ProduceListing)
            .where(
                ProduceListing.is_deleted.is_(False),
                ProduceListing.status == STATUS_ACTIVE,
                ProduceListing.expires_at > func.now(),
            )
        )

        if product_name:
            stmt = stmt.where(
                func.lower(ProduceListing.product_name).ilike(f"%{product_name.strip().lower()}%")
            )
        if category_id:
            stmt = stmt.where(ProduceListing.category_id == category_id)
        if state:
            stmt = stmt.where(func.lower(ProduceListing.location_state) == state.strip().lower())
        if city:
            stmt = stmt.where(func.lower(ProduceListing.location_city) == city.strip().lower())
        if unit:
            stmt = stmt.where(func.lower(ProduceListing.unit) == unit.strip().lower())
        if start_dt:
            stmt = stmt.where(ProduceListing.created_at >= start_dt)
        if end_dt:
            stmt = stmt.where(ProduceListing.created_at < end_dt)

        return list(db.scalars(stmt).all())

    # -----------------------------------------------------------------------
    # 2. Realized Trades Queries (Completed Orders)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_realized_trade_line_items(
        db: Session,
        *,
        product_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        unit: Optional[str] = None,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch line items from completed orders (executed trades).

        Includes completed orders regardless of payment acknowledgement or dispute status.
        Excludes cancelled orders.
        """
        stmt = (
            select(
                OrderItem.id.label("item_id"),
                OrderItem.order_id.label("order_id"),
                Order.farmer_id.label("farmer_id"),
                Order.buyer_id.label("buyer_id"),
                OrderItem.product_name.label("product_name"),
                OrderItem.quantity.label("quantity"),
                OrderItem.unit.label("unit"),
                OrderItem.unit_price.label("unit_price"),
                OrderItem.subtotal.label("subtotal"),
                Order.completed_at.label("completed_at"),
                Order.created_at.label("order_created_at"),
                func.coalesce(ProduceListing.location_state, FarmerProfile.state).label("state"),
                func.coalesce(ProduceListing.location_city, FarmerProfile.city).label("city"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .outerjoin(ProduceListing, OrderItem.listing_id == ProduceListing.id)
            .outerjoin(BuyerRequirement, OrderItem.buyer_requirement_id == BuyerRequirement.id)
            .outerjoin(FarmerProfile, Order.farmer_id == FarmerProfile.user_id)
            .where(Order.status == ORDER_STATUS_COMPLETED)
        )

        if product_name:
            stmt = stmt.where(
                func.lower(OrderItem.product_name).ilike(f"%{product_name.strip().lower()}%")
            )
        if category_id:
            stmt = stmt.where(
                or_(
                    ProduceListing.category_id == category_id,
                    BuyerRequirement.category_id == category_id,
                )
            )
        if state:
            stmt = stmt.where(
                func.lower(
                    func.coalesce(ProduceListing.location_state, FarmerProfile.state)
                ) == state.strip().lower()
            )
        if city:
            stmt = stmt.where(
                func.lower(
                    func.coalesce(ProduceListing.location_city, FarmerProfile.city)
                ) == city.strip().lower()
            )
        if unit:
            stmt = stmt.where(func.lower(OrderItem.unit) == unit.strip().lower())

        if start_dt or end_dt:
            # Use Order.completed_at if available, fallback to Order.created_at
            order_timestamp = func.coalesce(Order.completed_at, Order.created_at)
            if start_dt:
                stmt = stmt.where(order_timestamp >= start_dt)
            if end_dt:
                stmt = stmt.where(order_timestamp < end_dt)

        result = db.execute(stmt).mappings().all()
        return [dict(row) for row in result]

    # -----------------------------------------------------------------------
    # 3. Active Demand & Concluded Demand Audit Queries
    # -----------------------------------------------------------------------

    @staticmethod
    def get_active_demand_records(
        db: Session,
        *,
        product_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        unit: Optional[str] = None,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[BuyerRequirement]:
        """Fetch active/open procurement requirements."""
        stmt = (
            select(BuyerRequirement)
            .where(
                BuyerRequirement.is_deleted.is_(False),
                BuyerRequirement.status.in_([
                    REQUIREMENT_STATUS_ACTIVE,
                    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
                ]),
                BuyerRequirement.required_by_date >= func.current_date(),
            )
        )

        if product_name:
            stmt = stmt.where(
                func.lower(BuyerRequirement.product_name).ilike(f"%{product_name.strip().lower()}%")
            )
        if category_id:
            stmt = stmt.where(BuyerRequirement.category_id == category_id)
        if state:
            stmt = stmt.where(func.lower(BuyerRequirement.destination_state) == state.strip().lower())
        if city:
            stmt = stmt.where(func.lower(BuyerRequirement.destination_city) == city.strip().lower())
        if unit:
            stmt = stmt.where(func.lower(BuyerRequirement.unit) == unit.strip().lower())
        if start_dt:
            stmt = stmt.where(BuyerRequirement.created_at >= start_dt)
        if end_dt:
            stmt = stmt.where(BuyerRequirement.created_at < end_dt)

        return list(db.scalars(stmt).all())

    @staticmethod
    def get_concluded_demand_audit(
        db: Session,
        *,
        product_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        unit: Optional[str] = None,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> Tuple[Decimal, int, Decimal]:
        """Compute audited approved fulfillment volume and closed residual forfeited demand.

        Permanent Fulfillment Rule:
        Approved fulfillment records are counted permanently even if the parent
        requirement was later soft-deleted or closed.
        Residual forfeited demand excludes soft-deleted requirements.
        """
        # A. Audited Approved Fulfillment Volume
        approval_stmt = (
            select(
                func.coalesce(func.sum(RequirementFulfillmentApproval.approved_quantity), 0),
                func.count(RequirementFulfillmentApproval.id),
            )
            .join(BuyerRequirement, RequirementFulfillmentApproval.requirement_id == BuyerRequirement.id)
            .where(RequirementFulfillmentApproval.status == APPROVAL_STATUS_APPROVED)
        )

        if product_name:
            approval_stmt = approval_stmt.where(
                func.lower(BuyerRequirement.product_name).ilike(f"%{product_name.strip().lower()}%")
            )
        if category_id:
            approval_stmt = approval_stmt.where(BuyerRequirement.category_id == category_id)
        if state:
            approval_stmt = approval_stmt.where(
                func.lower(BuyerRequirement.destination_state) == state.strip().lower()
            )
        if city:
            approval_stmt = approval_stmt.where(
                func.lower(BuyerRequirement.destination_city) == city.strip().lower()
            )
        if unit:
            approval_stmt = approval_stmt.where(
                func.lower(BuyerRequirement.unit) == unit.strip().lower()
            )
        if start_dt:
            approval_stmt = approval_stmt.where(RequirementFulfillmentApproval.created_at >= start_dt)
        if end_dt:
            approval_stmt = approval_stmt.where(RequirementFulfillmentApproval.created_at < end_dt)

        appr_vol, appr_cnt = db.execute(approval_stmt).one()
        audited_volume = Decimal(str(appr_vol or 0))
        audited_count = int(appr_cnt or 0)

        # B. Closed Residual Unfulfilled Quantity (non-deleted, closed/expired requirements)
        closed_stmt = (
            select(func.coalesce(func.sum(BuyerRequirement.remaining_quantity), 0))
            .where(
                BuyerRequirement.is_deleted.is_(False),
                BuyerRequirement.status.in_([
                    REQUIREMENT_STATUS_CLOSED,
                    REQUIREMENT_STATUS_EXPIRED,
                ]),
            )
        )

        if product_name:
            closed_stmt = closed_stmt.where(
                func.lower(BuyerRequirement.product_name).ilike(f"%{product_name.strip().lower()}%")
            )
        if category_id:
            closed_stmt = closed_stmt.where(BuyerRequirement.category_id == category_id)
        if state:
            closed_stmt = closed_stmt.where(
                func.lower(BuyerRequirement.destination_state) == state.strip().lower()
            )
        if city:
            closed_stmt = closed_stmt.where(
                func.lower(BuyerRequirement.destination_city) == city.strip().lower()
            )
        if unit:
            closed_stmt = closed_stmt.where(
                func.lower(BuyerRequirement.unit) == unit.strip().lower()
            )
        if start_dt:
            closed_stmt = closed_stmt.where(BuyerRequirement.created_at >= start_dt)
        if end_dt:
            closed_stmt = closed_stmt.where(BuyerRequirement.created_at < end_dt)

        residual_res = db.execute(closed_stmt).scalar()
        residual_volume = Decimal(str(residual_res or 0))

        return audited_volume, audited_count, residual_volume

    # -----------------------------------------------------------------------
    # 4. User Performance Queries (Farmer / Buyer)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_farmer_performance_data(db: Session, farmer_id: uuid.UUID) -> Dict[str, Any]:
        """Aggregate personal metrics for a verified farmer."""
        # 1. Listings count
        total_listings = db.scalar(
            select(func.count(ProduceListing.id)).where(ProduceListing.farmer_id == farmer_id)
        ) or 0

        active_listings = db.scalar(
            select(func.count(ProduceListing.id)).where(
                ProduceListing.farmer_id == farmer_id,
                ProduceListing.is_deleted.is_(False),
                ProduceListing.status == STATUS_ACTIVE,
                ProduceListing.expires_at > func.now(),
            )
        ) or 0

        # 2. Orders outcomes
        order_rows = db.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.farmer_id == farmer_id)
            .group_by(Order.status)
        ).all()
        status_counts = {status: count for status, count in order_rows}

        # 3. Realized sales line items from completed orders
        sales_items = db.execute(
            select(
                OrderItem.product_name,
                OrderItem.quantity,
                OrderItem.unit,
                OrderItem.subtotal,
                Order.id.label("order_id"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.farmer_id == farmer_id,
                Order.status == ORDER_STATUS_COMPLETED,
            )
        ).mappings().all()

        # 4. Payment records for this farmer's orders
        payment_rows = db.execute(
            select(
                PaymentRecord.status,
                PaymentRecord.amount,
                PaymentRecord.created_at,
                func.coalesce(PaymentRecord.original_acknowledged_at, PaymentRecord.acknowledged_at).label("ack_at"),
            )
            .join(Order, PaymentRecord.order_id == Order.id)
            .where(Order.farmer_id == farmer_id)
        ).mappings().all()

        # 5. Reviews received
        reviews_stmt = (
            select(
                func.count(RatingReview.id),
                func.coalesce(func.avg(RatingReview.overall_rating), 0),
            )
            .where(RatingReview.reviewed_user_id == farmer_id)
        )
        rev_count, rev_avg = db.execute(reviews_stmt).one()

        return {
            "total_listings": int(total_listings),
            "active_listings": int(active_listings),
            "status_counts": status_counts,
            "sales_items": [dict(r) for r in sales_items],
            "payment_records": [dict(r) for r in payment_rows],
            "reviews_count": int(rev_count or 0),
            "reviews_average": float(rev_avg or 0.0),
        }

    @staticmethod
    def get_buyer_performance_data(db: Session, buyer_id: uuid.UUID) -> Dict[str, Any]:
        """Aggregate personal metrics for a verified commercial buyer."""
        # 1. Requirements count
        total_reqs = db.scalar(
            select(func.count(BuyerRequirement.id)).where(BuyerRequirement.buyer_id == buyer_id)
        ) or 0

        active_reqs = db.scalar(
            select(func.count(BuyerRequirement.id)).where(
                BuyerRequirement.buyer_id == buyer_id,
                BuyerRequirement.is_deleted.is_(False),
                BuyerRequirement.status.in_([
                    REQUIREMENT_STATUS_ACTIVE,
                    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
                ]),
                BuyerRequirement.required_by_date >= func.current_date(),
            )
        ) or 0

        # 2. Orders outcomes
        order_rows = db.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.buyer_id == buyer_id)
            .group_by(Order.status)
        ).all()
        status_counts = {status: count for status, count in order_rows}

        # 3. Realized purchase items from completed orders
        purchase_items = db.execute(
            select(
                OrderItem.product_name,
                OrderItem.quantity,
                OrderItem.unit,
                OrderItem.subtotal,
                Order.id.label("order_id"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.buyer_id == buyer_id,
                Order.status == ORDER_STATUS_COMPLETED,
            )
        ).mappings().all()

        # 4. Payment records for this buyer's orders
        payment_rows = db.execute(
            select(
                PaymentRecord.status,
                PaymentRecord.amount,
                PaymentRecord.created_at,
                func.coalesce(PaymentRecord.original_acknowledged_at, PaymentRecord.acknowledged_at).label("ack_at"),
            )
            .join(Order, PaymentRecord.order_id == Order.id)
            .where(Order.buyer_id == buyer_id)
        ).mappings().all()

        # 5. Reviews received
        reviews_stmt = (
            select(
                func.count(RatingReview.id),
                func.coalesce(func.avg(RatingReview.overall_rating), 0),
            )
            .where(RatingReview.reviewed_user_id == buyer_id)
        )
        rev_count, rev_avg = db.execute(reviews_stmt).one()

        return {
            "total_requirements": int(total_reqs),
            "active_requirements": int(active_reqs),
            "status_counts": status_counts,
            "purchase_items": [dict(r) for r in purchase_items],
            "payment_records": [dict(r) for r in payment_rows],
            "reviews_count": int(rev_count or 0),
            "reviews_average": float(rev_avg or 0.0),
        }

    # -----------------------------------------------------------------------
    # 5. Platform-Wide Administrative Analytics Queries
    # -----------------------------------------------------------------------

    @staticmethod
    def get_platform_analytics_raw(db: Session) -> Dict[str, Any]:
        """Gather unsuppressed platform-wide figures for administrator audit."""
        # A. GMV Figures
        platform_gmv = db.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.status == ORDER_STATUS_COMPLETED
            )
        ) or 0

        pipeline_gmv = db.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.status.in_([
                    ORDER_STATUS_CONFIRMED,
                    ORDER_STATUS_DELIVERY_ARRANGED,
                    ORDER_STATUS_PAYMENT_PENDING,
                    ORDER_STATUS_PAYMENT_RECORDED,
                ])
            )
        ) or 0

        # B. Listed Supply Overview
        active_listings = list(
            db.scalars(
                select(ProduceListing).where(
                    ProduceListing.is_deleted.is_(False),
                    ProduceListing.status == STATUS_ACTIVE,
                    ProduceListing.expires_at > func.now(),
                )
            ).all()
        )

        # C. Buyer Demand Overview
        active_reqs = list(
            db.scalars(
                select(BuyerRequirement).where(
                    BuyerRequirement.is_deleted.is_(False),
                    BuyerRequirement.status.in_([
                        REQUIREMENT_STATUS_ACTIVE,
                        REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
                    ]),
                    BuyerRequirement.required_by_date >= func.current_date(),
                )
            ).all()
        )

        # Permanent approved fulfillment volume grouped by unit
        fulfilled_rows = db.execute(
            select(
                BuyerRequirement.unit,
                func.coalesce(func.sum(RequirementFulfillmentApproval.approved_quantity), 0),
            )
            .join(BuyerRequirement, RequirementFulfillmentApproval.requirement_id == BuyerRequirement.id)
            .where(RequirementFulfillmentApproval.status == APPROVAL_STATUS_APPROVED)
            .group_by(BuyerRequirement.unit)
        ).all()

        # D. Order Outcomes Breakdown
        order_status_counts = dict(
            db.execute(
                select(Order.status, func.count(Order.id)).group_by(Order.status)
            ).all()
        )

        # E. Payment Velocity
        payment_records = list(
            db.execute(
                select(
                    PaymentRecord.status,
                    PaymentRecord.amount,
                    PaymentRecord.created_at,
                    func.coalesce(
                        PaymentRecord.original_acknowledged_at,
                        PaymentRecord.acknowledged_at,
                    ).label("ack_at"),
                )
            ).mappings().all()
        )

        # F. User Engagement
        user_rows = db.execute(
            select(User.role, User.verification_status, func.count(User.id)).group_by(
                User.role, User.verification_status
            )
        ).all()

        return {
            "platform_gmv": Decimal(str(platform_gmv)),
            "pipeline_gmv": Decimal(str(pipeline_gmv)),
            "active_listings": active_listings,
            "active_requirements": active_reqs,
            "approved_fulfillment_by_unit": {row[0]: Decimal(str(row[1])) for row in fulfilled_rows},
            "order_status_counts": order_status_counts,
            "payment_records": [dict(r) for r in payment_records],
            "user_rows": user_rows,
        }

