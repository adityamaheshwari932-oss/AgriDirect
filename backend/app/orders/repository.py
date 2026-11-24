"""SQLAlchemy repository for Orders, Line Items, Amendments, and Inventory Adjustments.

Implements database access patterns adhering strictly to the canonical 5-tier
lock hierarchy: Tier 2 (Order) -> Tier 3 (Listing) -> Tier 4 (Requirement) -> Tier 5 (Approval).
"""

import json
import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.listing import ProduceListing
from app.models.order import (
    AMENDMENT_STATUS_EFFECTIVE,
    AMENDMENT_STATUS_PROPOSED,
    AMENDMENT_TYPE_QUANTITY,
    CHANGE_TYPE_AMENDMENT_DELTA,
    CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
    CHANGE_TYPE_ORDER_FULFILLMENT,
    InventoryAdjustment,
    Order,
    OrderAmendment,
    OrderDeliveryAcknowledgement,
    OrderImage,
    OrderItem,
)
from app.models.requirement import BuyerRequirement
from app.models.requirement_approval import RequirementFulfillmentApproval
from app.models.user import User

# Relevant inventory change types affecting order-specific stock deductions
ORDER_INVENTORY_CHANGE_TYPES = (
    CHANGE_TYPE_ORDER_FULFILLMENT,
    CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
    CHANGE_TYPE_AMENDMENT_DELTA,
)


class OrderRepository:
    """Synchronous repository handling orders, amendments, and inventory adjustments."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Canonical Lock Hierarchy Implementations
    # -----------------------------------------------------------------------

    def lock_order(self, order_id: uuid.UUID) -> Optional[Order]:
        """Acquire Tier 2 exclusive row lock on Order."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update(of=Order)
            .execution_options(populate_existing=True)
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def lock_listings(self, listing_ids: Sequence[uuid.UUID]) -> Dict[uuid.UUID, ProduceListing]:
        """Acquire Tier 3 exclusive row locks on ProduceListings in ascending UUID order."""
        if not listing_ids:
            return {}
        sorted_ids = sorted(set(listing_ids))
        stmt = (
            select(ProduceListing)
            .where(ProduceListing.id.in_(sorted_ids))
            .order_by(ProduceListing.id.asc())
            .with_for_update(of=ProduceListing)
            .execution_options(populate_existing=True)
        )
        listings = self.db.scalars(stmt).all()
        return {l.id: l for l in listings}

    def lock_requirements(self, requirement_ids: Sequence[uuid.UUID]) -> Dict[uuid.UUID, BuyerRequirement]:
        """Acquire Tier 4 exclusive row locks on BuyerRequirements in ascending UUID order."""
        if not requirement_ids:
            return {}
        sorted_ids = sorted(set(requirement_ids))
        stmt = (
            select(BuyerRequirement)
            .where(BuyerRequirement.id.in_(sorted_ids))
            .order_by(BuyerRequirement.id.asc())
            .with_for_update(of=BuyerRequirement)
            .execution_options(populate_existing=True)
        )
        reqs = self.db.scalars(stmt).all()
        return {r.id: r for r in reqs}

    def lock_approvals_by_ids(
        self,
        approval_ids: Sequence[uuid.UUID],
    ) -> Dict[uuid.UUID, RequirementFulfillmentApproval]:
        """Acquire Tier 5 exclusive row locks on RequirementFulfillmentApprovals in ascending UUID order."""
        if not approval_ids:
            return {}
        sorted_ids = sorted(set(approval_ids))
        stmt = (
            select(RequirementFulfillmentApproval)
            .where(RequirementFulfillmentApproval.id.in_(sorted_ids))
            .order_by(RequirementFulfillmentApproval.id.asc())
            .with_for_update(of=RequirementFulfillmentApproval)
            .execution_options(populate_existing=True)
        )
        approvals = self.db.scalars(stmt).all()
        return {a.id: a for a in approvals}

    def lock_approvals_by_order(
        self,
        order_id: uuid.UUID,
    ) -> List[RequirementFulfillmentApproval]:
        """Acquire Tier 5 exclusive row locks on all approvals for an order in ascending UUID order."""
        stmt = (
            select(RequirementFulfillmentApproval)
            .where(RequirementFulfillmentApproval.order_id == order_id)
            .order_by(RequirementFulfillmentApproval.id.asc())
            .with_for_update(of=RequirementFulfillmentApproval)
            .execution_options(populate_existing=True)
        )
        return list(self.db.scalars(stmt).all())

    # -----------------------------------------------------------------------
    # Order Retrieval and Listing
    # -----------------------------------------------------------------------

    def get_by_id(self, order_id: uuid.UUID, for_update: bool = False) -> Optional[Order]:
        """Fetch an order by ID with optional row locking."""
        stmt = select(Order).where(Order.id == order_id)
        if for_update:
            stmt = stmt.with_for_update(of=Order).execution_options(populate_existing=True)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_order_detail(self, order_id: uuid.UUID) -> Optional[Order]:
        """Fetch an order by ID with eager loading for items, participants, amendments, and images."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.amendments),
                selectinload(Order.delivery_acknowledgements),
                selectinload(Order.images),
                joinedload(Order.buyer).joinedload(User.buyer_profile),
                joinedload(Order.farmer).joinedload(User.farmer_profile),
            )
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Order]:
        """Fetch an order by client-supplied idempotency key."""
        if not idempotency_key:
            return None
        stmt = select(Order).where(Order.idempotency_key == idempotency_key)
        return self.db.scalars(stmt).unique().one_or_none()

    def generate_order_number(self) -> str:
        """Generate a collision-free human-readable order number.

        Format: ORD-YYYYMMDD-XXXXX
        """
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        for _ in range(10):
            suffix = secrets.token_hex(3).upper()[:5]
            candidate = f"ORD-{today}-{suffix}"
            exists = self.db.scalar(
                select(Order.id).where(Order.order_number == candidate)
            )
            if not exists:
                return candidate
        micro = datetime.now(timezone.utc).strftime("%f")[:5]
        return f"ORD-{today}-{micro}"

    def lock_listing(self, listing_id: uuid.UUID) -> Optional[ProduceListing]:
        """Acquire Tier 3 exclusive row lock on a single ProduceListing."""
        stmt = (
            select(ProduceListing)
            .where(ProduceListing.id == listing_id)
            .with_for_update(of=ProduceListing)
            .execution_options(populate_existing=True)
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def add_order_image(
        self,
        order_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID,
        image_uri: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> OrderImage:
        """Insert photographic asset reference for an order."""
        image = OrderImage(
            order_id=order_id,
            uploaded_by_user_id=uploaded_by_user_id,
            image_uri=image_uri,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
        )
        self.db.add(image)
        return image

    def get_order_images(self, order_id: uuid.UUID) -> List[OrderImage]:
        """Retrieve all images attached to an order."""
        stmt = (
            select(OrderImage)
            .where(OrderImage.order_id == order_id)
            .order_by(OrderImage.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_order_image(self, order_id: uuid.UUID, image_id: uuid.UUID) -> Optional[OrderImage]:
        """Retrieve a specific order image by ID."""
        stmt = select(OrderImage).where(
            OrderImage.order_id == order_id,
            OrderImage.id == image_id,
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def list_orders(
        self,
        user_id: uuid.UUID,
        is_admin: bool = False,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Order], int]:
        """List orders with strict role-based visibility, status filtering, and pagination."""
        base_query = select(Order).options(selectinload(Order.items))

        # Authorization filtering: non-admins must be buyer or farmer
        if not is_admin:
            if role_filter == "buyer":
                base_query = base_query.where(Order.buyer_id == user_id)
            elif role_filter == "farmer":
                base_query = base_query.where(Order.farmer_id == user_id)
            else:
                base_query = base_query.where(
                    or_(Order.buyer_id == user_id, Order.farmer_id == user_id)
                )
        else:
            if role_filter == "buyer":
                base_query = base_query.where(Order.buyer_id == user_id)
            elif role_filter == "farmer":
                base_query = base_query.where(Order.farmer_id == user_id)

        if status_filter:
            base_query = base_query.where(Order.status == status_filter)

        # Count total matches
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Stable ordering and pagination
        stmt = (
            base_query
            .order_by(Order.created_at.desc(), Order.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        orders = self.db.scalars(stmt).all()
        return list(orders), total

    def get_order_item(self, order_id: uuid.UUID, item_id: uuid.UUID) -> Optional[OrderItem]:
        """Fetch a specific line item belonging to an order."""
        stmt = select(OrderItem).where(
            OrderItem.order_id == order_id,
            OrderItem.id == item_id,
        )
        return self.db.scalars(stmt).unique().one_or_none()

    # -----------------------------------------------------------------------
    # Amendment Queries
    # -----------------------------------------------------------------------

    def get_amendments_for_order(self, order_id: uuid.UUID) -> List[OrderAmendment]:
        """Retrieve all amendments for an order ordered chronologically."""
        stmt = (
            select(OrderAmendment)
            .where(OrderAmendment.order_id == order_id)
            .order_by(OrderAmendment.created_at.asc(), OrderAmendment.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_amendment(self, order_id: uuid.UUID, amendment_id: uuid.UUID) -> Optional[OrderAmendment]:
        """Retrieve a specific amendment by ID belonging to an order."""
        stmt = select(OrderAmendment).where(
            OrderAmendment.order_id == order_id,
            OrderAmendment.id == amendment_id,
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def get_pending_amendment(self, order_id: uuid.UUID) -> Optional[OrderAmendment]:
        """Retrieve the currently proposed (pending) amendment for an order, if any."""
        stmt = select(OrderAmendment).where(
            OrderAmendment.order_id == order_id,
            OrderAmendment.status == AMENDMENT_STATUS_PROPOSED,
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def get_effective_quantity_amendments(self, order_id: uuid.UUID) -> List[OrderAmendment]:
        """Retrieve all historical effective quantity amendments for cumulative accounting."""
        stmt = (
            select(OrderAmendment)
            .where(
                OrderAmendment.order_id == order_id,
                OrderAmendment.status == AMENDMENT_STATUS_EFFECTIVE,
                OrderAmendment.amendment_type == AMENDMENT_TYPE_QUANTITY,
            )
            .order_by(OrderAmendment.created_at.asc(), OrderAmendment.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    # -----------------------------------------------------------------------
    # Inventory Adjustment Ledger Queries
    # -----------------------------------------------------------------------

    def get_order_inventory_net_impact(
        self,
        order_id: uuid.UUID,
        listing_id: uuid.UUID,
    ) -> Decimal:
        """Calculate authoritative net inventory impact for an order on a specific listing."""
        stmt = select(
            func.coalesce(func.sum(InventoryAdjustment.quantity_delta), Decimal("0.000"))
        ).where(
            InventoryAdjustment.order_id == order_id,
            InventoryAdjustment.listing_id == listing_id,
            InventoryAdjustment.change_type.in_(ORDER_INVENTORY_CHANGE_TYPES),
        )
        return Decimal(str(self.db.scalar(stmt) or Decimal("0.000")))

    def get_inventory_adjustments_for_order(
        self,
        order_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[InventoryAdjustment], int]:
        """Retrieve paginated inventory audit adjustments for an order."""
        base_query = select(InventoryAdjustment).where(InventoryAdjustment.order_id == order_id)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = (
            base_query
            .order_by(InventoryAdjustment.created_at.asc(), InventoryAdjustment.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        adjustments = self.db.scalars(stmt).all()
        return list(adjustments), total

    def get_inventory_adjustments_for_listing(
        self,
        listing_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[InventoryAdjustment], int]:
        """Retrieve paginated inventory audit adjustments for a produce listing."""
        base_query = select(InventoryAdjustment).where(InventoryAdjustment.listing_id == listing_id)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = (
            base_query
            .order_by(InventoryAdjustment.created_at.desc(), InventoryAdjustment.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        adjustments = self.db.scalars(stmt).all()
        return list(adjustments), total

    # -----------------------------------------------------------------------
    # Delivery Acknowledgements
    # -----------------------------------------------------------------------

    def get_delivery_acknowledgements(
        self,
        order_id: uuid.UUID,
    ) -> List[OrderDeliveryAcknowledgement]:
        """Fetch all delivery acknowledgements recorded for an order."""
        stmt = (
            select(OrderDeliveryAcknowledgement)
            .where(OrderDeliveryAcknowledgement.order_id == order_id)
            .order_by(OrderDeliveryAcknowledgement.acknowledged_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_delivery_acknowledgement(
        self,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[OrderDeliveryAcknowledgement]:
        """Fetch an acknowledgement by order and user ID."""
        stmt = select(OrderDeliveryAcknowledgement).where(
            and_(
                OrderDeliveryAcknowledgement.order_id == order_id,
                OrderDeliveryAcknowledgement.user_id == user_id,
            )
        )
        return self.db.scalars(stmt).one_or_none()

    def add_delivery_acknowledgement(
        self,
        ack: OrderDeliveryAcknowledgement,
    ) -> OrderDeliveryAcknowledgement:
        """Persist a new delivery acknowledgement record."""
        self.db.add(ack)
        return ack


