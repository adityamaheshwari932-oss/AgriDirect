"""Business service implementing Module 4 — Orders & Inventory Lifecycle.

Enforces:
- Strict canonical 5-tier lock hierarchy: Order (Tier 2) -> Listing (Tier 3) -> Requirement (Tier 4) -> Approval (Tier 5)
- Idempotent and exact inventory ledger restitution (accounting net-balance = 0)
- Immutable historical requirement fulfillment approval records
- Cumulative non-double-counting buyer demand restitution
- Mutual bilateral delivery coordination and post-finalization amendments
"""

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.listing import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_PARTIALLY_FULFILLED,
    ProduceListing,
)
from app.models.notification import Notification
from app.models.order import (
    AMENDMENT_STATUS_EFFECTIVE,
    AMENDMENT_STATUS_PROPOSED,
    AMENDMENT_STATUS_REJECTED,
    AMENDMENT_TYPE_DELIVERY_DATE,
    AMENDMENT_TYPE_PRICE,
    AMENDMENT_TYPE_QUANTITY,
    AMENDMENT_TYPE_TERMS,
    CHANGE_TYPE_AMENDMENT_DELTA,
    CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
    DELIVERY_STATUS_ARRANGED,
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_COMPLETION_MARKED,
    ORDER_ITEM_STATUS_CANCELLED,
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_ITEM_STATUS_DISPUTED,
    ORDER_ITEM_STATUS_FULFILLED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_DISPUTED,
    ORDER_STATUS_PENDING,
    InventoryAdjustment,
    Order,
    OrderAmendment,
    OrderDeliveryAcknowledgement,
    OrderItem,
)
from app.models.requirement import (
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    BuyerRequirement,
)
from app.models.requirement_approval import (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_VOIDED,
    RequirementFulfillmentApproval,
)
from app.models.user import User
from app.orders.repository import OrderRepository
from app.orders.schemas import (
    DeliveryAcknowledgeRequest,
    DeliveryArrangeRequest,
    InventoryAdjustmentListResponse,
    InventoryAdjustmentResponse,
    OrderAmendmentCreate,
    OrderAmendmentListResponse,
    OrderAmendmentResponse,
    OrderCancelRequest,
    OrderDeliveryAcknowledgementResponse,
    OrderDetailResponse,
    OrderItemResponse,
    OrderListItemResponse,
    OrderListResponse,
    OrderParticipantResponse,
)


class OrderService:
    """Service encapsulating order operations, delivery coordination, amendments, and inventory control."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OrderRepository(db)

    # -----------------------------------------------------------------------
    # Guard Helpers
    # -----------------------------------------------------------------------

    def _ensure_active_verified(self, user: User, required_role: Optional[str] = None) -> None:
        """Validate account status and verification level."""
        if user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended",
            )
        if user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a verified account",
            )
        if required_role and user.role != required_role and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation restricted to '{required_role}' role",
            )

    def _get_user_display_name(self, user: User) -> str:
        """Resolve a friendly display name for a user."""
        if getattr(user, "farmer_profile", None) and user.farmer_profile.full_name:
            return user.farmer_profile.full_name
        if getattr(user, "buyer_profile", None) and user.buyer_profile.contact_person_name:
            return user.buyer_profile.contact_person_name
        return user.email

    def _to_detail_response(self, order: Order) -> OrderDetailResponse:
        """Serialize an Order entity into a detailed API response."""
        buyer_resp = None
        if order.buyer:
            b_profile = getattr(order.buyer, "buyer_profile", None)
            buyer_resp = OrderParticipantResponse(
                id=order.buyer.id,
                full_name=b_profile.contact_person_name if b_profile else order.buyer.email,
                email=order.buyer.email,
                phone=order.buyer.phone_number,
                business_name=b_profile.business_name if b_profile else None,
            )

        farmer_resp = None
        if order.farmer:
            f_profile = getattr(order.farmer, "farmer_profile", None)
            farmer_resp = OrderParticipantResponse(
                id=order.farmer.id,
                full_name=f_profile.full_name if f_profile else order.farmer.email,
                email=order.farmer.email,
                phone=order.farmer.phone_number,
                farm_name=f_profile.farm_name if f_profile else None,
            )

        items_resp = [
            OrderItemResponse(
                id=item.id,
                order_id=item.order_id,
                listing_id=item.listing_id,
                buyer_requirement_id=item.buyer_requirement_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                quality_grade=item.quality_grade,
                status=item.status,
                created_at=item.created_at,
            )
            for item in order.items
        ]

        amendments_resp = [
            OrderAmendmentResponse(
                id=am.id,
                order_id=am.order_id,
                proposed_by_user_id=am.proposed_by_user_id,
                amendment_type=am.amendment_type,
                old_value=am.old_value,
                new_value=am.new_value,
                justification=am.justification,
                buyer_confirmed=am.buyer_confirmed,
                farmer_confirmed=am.farmer_confirmed,
                status=am.status,
                effective_at=am.effective_at,
                created_at=am.created_at,
                updated_at=am.updated_at,
            )
            for am in order.amendments
        ]

        # Convert delivery acknowledgements
        acks_list = getattr(order, "delivery_acknowledgements", []) or []
        acks_resp = [
            OrderDeliveryAcknowledgementResponse(
                id=ack.id,
                order_id=ack.order_id,
                user_id=ack.user_id,
                acknowledged_at=ack.acknowledged_at,
                notes=ack.notes,
            )
            for ack in acks_list
        ]

        # Calculate pending acknowledgements
        pending_roles: List[str] = []
        if order.delivery_status == DELIVERY_STATUS_COMPLETION_MARKED:
            acked_users = {ack.user_id for ack in acks_list}
            if order.delivery_completion_marked_by_user_id == order.farmer_id:
                if order.buyer_id not in acked_users:
                    pending_roles.append("buyer")
            elif order.delivery_completion_marked_by_user_id == order.buyer_id:
                if order.farmer_id not in acked_users:
                    pending_roles.append("farmer")
            else:
                # Admin or third party completion
                if order.farmer_id not in acked_users:
                    pending_roles.append("farmer")
                if order.buyer_id not in acked_users:
                    pending_roles.append("buyer")

        return OrderDetailResponse(
            id=order.id,
            order_number=order.order_number,
            source_offer_id=order.source_offer_id,
            buyer_id=order.buyer_id,
            farmer_id=order.farmer_id,
            total_amount=order.total_amount,
            currency="INR",
            status=order.status,
            delivery_method=order.delivery_method,
            delivery_destination_address=order.delivery_destination_address,
            delivery_arranged_date=order.delivery_arranged_date,
            delivery_status=order.delivery_status,
            delivery_completion_marked_by_user_id=order.delivery_completion_marked_by_user_id,
            delivery_completion_marked_at=order.delivery_completion_marked_at,
            delivery_acknowledged_by_user_id=order.delivery_acknowledged_by_user_id,
            delivery_acknowledged_at=order.delivery_acknowledged_at,
            delivery_notes=order.delivery_notes,
            cancellation_reason=order.cancellation_reason,
            cancelled_by_user_id=order.cancelled_by_user_id,
            cancelled_at=order.cancelled_at,
            completed_at=order.completed_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=items_resp,
            buyer=buyer_resp,
            farmer=farmer_resp,
            amendments=amendments_resp,
            delivery_acknowledgements=acks_resp,
            delivery_acknowledgements_pending=pending_roles,
        )

    # -----------------------------------------------------------------------
    # Batch 1: Order Listing, Details & Farmer Confirmation
    # -----------------------------------------------------------------------

    def list_orders(
        self,
        current_user: User,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> OrderListResponse:
        """Retrieve paginated orders visible to the authenticated user."""
        self._ensure_active_verified(current_user)
        is_admin = (current_user.role == "admin")

        orders, total = self.repo.list_orders(
            user_id=current_user.id,
            is_admin=is_admin,
            role_filter=role_filter,
            status_filter=status_filter,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        items = [
            OrderListItemResponse(
                id=o.id,
                order_number=o.order_number,
                source_offer_id=o.source_offer_id,
                buyer_id=o.buyer_id,
                farmer_id=o.farmer_id,
                total_amount=o.total_amount,
                currency="INR",
                status=o.status,
                delivery_status=o.delivery_status,
                delivery_arranged_date=o.delivery_arranged_date,
                items_count=len(o.items),
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in orders
        ]

        return OrderListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_order_detail(self, current_user: User, order_id: uuid.UUID) -> OrderDetailResponse:
        """Retrieve complete order details with anti-enumeration security."""
        self._ensure_active_verified(current_user)
        order = self.repo.get_order_detail(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        return self._to_detail_response(order)

    def confirm_order(self, current_user: User, order_id: uuid.UUID) -> OrderDetailResponse:
        """Confirm order by the seller (farmer) exclusively."""
        self._ensure_active_verified(current_user, required_role="farmer")

        # Tier 2 Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        if order.farmer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the seller (farmer) can confirm this order",
            )

        if order.status != ORDER_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot confirm order in '{order.status}' status. Only pending orders can be confirmed.",
            )

        now_utc = datetime.now(timezone.utc)
        order.status = ORDER_STATUS_CONFIRMED
        order.updated_at = now_utc

        self.db.add(
            Notification(
                user_id=order.buyer_id,
                event_type="order_confirmed",
                title="Order Confirmed by Farmer",
                body=f"Farmer confirmed fulfillment commitment for Order {order.order_number}.",
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return self.get_order_detail(current_user, order.id)

    # -----------------------------------------------------------------------
    # Batch 2: Atomic Order Cancellation
    # -----------------------------------------------------------------------

    def cancel_order(
        self,
        current_user: User,
        order_id: uuid.UUID,
        payload: OrderCancelRequest,
    ) -> OrderDetailResponse:
        """Atomically cancel an active order with authoritative inventory and demand restitution."""
        self._ensure_active_verified(current_user)

        # 1. Tier 2 Exclusive Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        # State and Item Validations
        if order.status in (ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order is already {order.status} and cannot be cancelled",
            )
        if order.status == ORDER_STATUS_DISPUTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot cancel a disputed order",
            )
        if order.status not in (ORDER_STATUS_PENDING, ORDER_STATUS_CONFIRMED, ORDER_STATUS_DELIVERY_ARRANGED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order in status '{order.status}' cannot be cancelled",
            )

        for item in order.items:
            if item.status in (ORDER_ITEM_STATUS_FULFILLED, ORDER_ITEM_STATUS_DISPUTED):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot cancel order because line item '{item.product_name}' is already {item.status}",
                )

        # 2. Tier 3 Lock on all affected ProduceListings (ascending UUID order)
        listing_ids = [item.listing_id for item in order.items if item.listing_id is not None]
        listings_map = self.repo.lock_listings(listing_ids)

        # 3. Tier 4 Lock on all affected BuyerRequirements (ascending UUID order)
        req_ids = [item.buyer_requirement_id for item in order.items if item.buyer_requirement_id is not None]
        requirements_map = self.repo.lock_requirements(req_ids)

        # 4. Tier 5 Lock on all affected RequirementFulfillmentApprovals (ascending UUID order)
        approvals = self.repo.lock_approvals_by_order(order.id)
        approvals_by_item = {a.order_item_id: a for a in approvals}

        # 5. Inventory Restitution via Historical Ledger
        for lid in set(listing_ids):
            listing = listings_map.get(lid)
            if not listing:
                continue

            net_order_impact = self.repo.get_order_inventory_net_impact(order.id, listing.id)
            outstanding_net_deduction = max(Decimal("0.000"), -net_order_impact)

            if outstanding_net_deduction > Decimal("0.000"):
                listing.available_quantity += outstanding_net_deduction
                if listing.available_quantity >= listing.initial_quantity:
                    listing.status = STATUS_ACTIVE
                elif listing.available_quantity > 0 and listing.status == STATUS_CLOSED:
                    listing.status = STATUS_PARTIALLY_FULFILLED

                self.db.add(
                    InventoryAdjustment(
                        listing_id=listing.id,
                        order_id=order.id,
                        change_type=CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
                        quantity_delta=outstanding_net_deduction,
                        recorded_by_user_id=current_user.id,
                        notes=f"Order cancellation release for order {order.order_number}",
                    )
                )

        # 6. Cumulative Prior Demand Restorations Analysis
        effective_amendments = self.repo.get_effective_quantity_amendments(order.id)
        prior_restored_by_item: Dict[uuid.UUID, Decimal] = {}
        for am in effective_amendments:
            try:
                snapshot = json.loads(am.new_value)
                item_id_str = snapshot.get("order_item_id")
                if item_id_str:
                    item_uuid = uuid.UUID(item_id_str)
                    restored_qty = Decimal(str(snapshot.get("demand_restored", "0.000")))
                    prior_restored_by_item[item_uuid] = (
                        prior_restored_by_item.get(item_uuid, Decimal("0.000")) + restored_qty
                    )
            except (json.JSONDecodeError, ValueError):
                pass

        # 7. Buyer Demand Restitution and Pending Approval Handling
        today = date.today()
        now_utc = datetime.now(timezone.utc)

        for item in order.items:
            if not item.buyer_requirement_id or item.buyer_requirement_id not in requirements_map:
                continue

            req = requirements_map[item.buyer_requirement_id]
            approval = approvals_by_item.get(item.id)

            if approval:
                if approval.status == APPROVAL_STATUS_APPROVED:
                    prior_restored = prior_restored_by_item.get(item.id, Decimal("0.000"))
                    remaining_consumption = max(
                        Decimal("0.000"), approval.approved_quantity - prior_restored
                    )

                    # Only restore if requirement is active/partially fulfilled, unexpired, and not deleted
                    if (
                        not req.is_deleted
                        and req.required_by_date >= today
                        and req.status in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED)
                    ):
                        gap = max(Decimal("0.000"), req.required_quantity - req.remaining_quantity)
                        demand_to_restore = min(remaining_consumption, gap)
                        if demand_to_restore > Decimal("0.000"):
                            req.remaining_quantity += demand_to_restore
                            if req.remaining_quantity == req.required_quantity:
                                req.status = REQUIREMENT_STATUS_ACTIVE
                elif approval.status == APPROVAL_STATUS_PENDING:
                    # Void pending approval cleanly with audit metadata
                    approval.status = APPROVAL_STATUS_VOIDED
                    approval.voided_by_user_id = current_user.id
                    approval.voided_at = now_utc
                    approval.void_reason = f"Order {order.order_number} cancelled: {payload.reason}"
                    approval.updated_at = now_utc

        # 8. Mutate Order and OrderItems Status
        order.status = ORDER_STATUS_CANCELLED
        order.cancelled_by_user_id = current_user.id
        order.cancelled_at = now_utc
        order.cancellation_reason = payload.reason
        order.updated_at = now_utc

        for item in order.items:
            if item.status == ORDER_ITEM_STATUS_CONFIRMED:
                item.status = ORDER_ITEM_STATUS_CANCELLED

        # 9. Notify Counterparty
        counterparty_id = order.farmer_id if current_user.id == order.buyer_id else order.buyer_id
        actor_name = self._get_user_display_name(current_user)
        self.db.add(
            Notification(
                user_id=counterparty_id,
                event_type="order_cancelled",
                title="Order Cancelled",
                body=f"Order {order.order_number} was cancelled by {actor_name}. Reason: {payload.reason}",
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return self.get_order_detail(current_user, order.id)

    # -----------------------------------------------------------------------
    # Batch 3: Order Amendments
    # -----------------------------------------------------------------------

    def propose_amendment(
        self,
        current_user: User,
        order_id: uuid.UUID,
        payload: OrderAmendmentCreate,
    ) -> OrderAmendmentResponse:
        """Submit a post-finalization order amendment proposal."""
        self._ensure_active_verified(current_user)

        # Tier 2 Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )

        if order.status in (ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED, ORDER_STATUS_DISPUTED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot amend order in '{order.status}' status",
            )

        # Only one pending amendment at a time
        pending = self.repo.get_pending_amendment(order.id)
        if pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An amendment is already pending review for this order",
            )

        # Snapshot generation
        now_utc = datetime.now(timezone.utc)
        if payload.amendment_type == AMENDMENT_TYPE_QUANTITY:
            item = self.repo.get_order_item(order.id, payload.order_item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Order item '{payload.order_item_id}' not found in order",
                )
            old_val = json.dumps({"order_item_id": str(item.id), "quantity": str(item.quantity)})
            new_val = json.dumps({"order_item_id": str(item.id), "quantity": str(payload.new_quantity)})

        elif payload.amendment_type == AMENDMENT_TYPE_PRICE:
            item = self.repo.get_order_item(order.id, payload.order_item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Order item '{payload.order_item_id}' not found in order",
                )
            old_val = json.dumps({"order_item_id": str(item.id), "unit_price": str(item.unit_price)})
            new_val = json.dumps({"order_item_id": str(item.id), "unit_price": str(payload.new_price)})

        elif payload.amendment_type == AMENDMENT_TYPE_DELIVERY_DATE:
            old_val = json.dumps({
                "delivery_arranged_date": str(order.delivery_arranged_date) if order.delivery_arranged_date else None
            })
            new_val = json.dumps({"delivery_arranged_date": str(payload.new_delivery_date)})

        elif payload.amendment_type == AMENDMENT_TYPE_TERMS:
            old_val = json.dumps({"terms": order.delivery_notes})
            new_val = json.dumps({"terms": payload.new_terms})

        is_buyer = (current_user.id == order.buyer_id)
        amendment = OrderAmendment(
            order_id=order.id,
            proposed_by_user_id=current_user.id,
            amendment_type=payload.amendment_type,
            old_value=old_val,
            new_value=new_val,
            justification=payload.justification,
            buyer_confirmed=is_buyer,
            farmer_confirmed=not is_buyer,
            status=AMENDMENT_STATUS_PROPOSED,
        )
        self.db.add(amendment)
        self.db.commit()
        self.db.refresh(amendment)

        # Notify counterparty
        counterparty_id = order.farmer_id if is_buyer else order.buyer_id
        actor_name = self._get_user_display_name(current_user)
        self.db.add(
            Notification(
                user_id=counterparty_id,
                event_type="order_amendment_proposed",
                title="Order Amendment Proposed",
                body=(
                    f"{actor_name} proposed a {payload.amendment_type} amendment "
                    f"for Order {order.order_number}."
                ),
                reference_type="order",
                reference_id=order.id,
            )
        )
        self.db.commit()

        return OrderAmendmentResponse(
            id=amendment.id,
            order_id=amendment.order_id,
            proposed_by_user_id=amendment.proposed_by_user_id,
            amendment_type=amendment.amendment_type,
            old_value=amendment.old_value,
            new_value=amendment.new_value,
            justification=amendment.justification,
            buyer_confirmed=amendment.buyer_confirmed,
            farmer_confirmed=amendment.farmer_confirmed,
            status=amendment.status,
            effective_at=amendment.effective_at,
            created_at=amendment.created_at,
            updated_at=amendment.updated_at,
        )

    def list_amendments(self, current_user: User, order_id: uuid.UUID) -> OrderAmendmentListResponse:
        """List all amendments for an order."""
        self._ensure_active_verified(current_user)
        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        amendments = self.repo.get_amendments_for_order(order_id)
        items = [
            OrderAmendmentResponse(
                id=a.id,
                order_id=a.order_id,
                proposed_by_user_id=a.proposed_by_user_id,
                amendment_type=a.amendment_type,
                old_value=a.old_value,
                new_value=a.new_value,
                justification=a.justification,
                buyer_confirmed=a.buyer_confirmed,
                farmer_confirmed=a.farmer_confirmed,
                status=a.status,
                effective_at=a.effective_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in amendments
        ]
        return OrderAmendmentListResponse(items=items, total=len(items))

    def get_amendment(
        self,
        current_user: User,
        order_id: uuid.UUID,
        amendment_id: uuid.UUID,
    ) -> OrderAmendmentResponse:
        """Retrieve a specific amendment record."""
        self._ensure_active_verified(current_user)
        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        amendment = self.repo.get_amendment(order_id, amendment_id)
        if not amendment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Amendment '{amendment_id}' not found",
            )

        return OrderAmendmentResponse(
            id=amendment.id,
            order_id=amendment.order_id,
            proposed_by_user_id=amendment.proposed_by_user_id,
            amendment_type=amendment.amendment_type,
            old_value=amendment.old_value,
            new_value=amendment.new_value,
            justification=amendment.justification,
            buyer_confirmed=amendment.buyer_confirmed,
            farmer_confirmed=amendment.farmer_confirmed,
            status=amendment.status,
            effective_at=amendment.effective_at,
            created_at=amendment.created_at,
            updated_at=amendment.updated_at,
        )

    def accept_amendment(
        self,
        current_user: User,
        order_id: uuid.UUID,
        amendment_id: uuid.UUID,
    ) -> OrderAmendmentResponse:
        """Accept a proposed amendment with strict 5-tier lock acquisition and accounting."""
        self._ensure_active_verified(current_user)

        # 1. Tier 2 Lock on Order
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        if order.status in (ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED, ORDER_STATUS_DISPUTED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot accept amendment on an order in '{order.status}' status",
            )

        amendment = self.repo.get_amendment(order.id, amendment_id)
        if not amendment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Amendment '{amendment_id}' not found")

        if amendment.status != AMENDMENT_STATUS_PROPOSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Amendment has already been reviewed with status: '{amendment.status}'",
            )

        if current_user.id == amendment.proposed_by_user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Proposer cannot accept their own amendment",
            )

        now_utc = datetime.now(timezone.utc)

        # Apply specific amendment type changes under appropriate tier locks
        if amendment.amendment_type == AMENDMENT_TYPE_QUANTITY:
            snapshot = json.loads(amendment.new_value)
            item_id = uuid.UUID(snapshot["order_item_id"])
            new_qty = Decimal(str(snapshot["quantity"]))

            item = self.repo.get_order_item(order.id, item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

            old_qty = item.quantity
            delta = new_qty - old_qty

            # Tier 3 Lock on Listing
            listing = None
            if item.listing_id:
                listings_map = self.repo.lock_listings([item.listing_id])
                listing = listings_map.get(item.listing_id)

            # Tier 4 Lock on Requirement
            req = None
            if item.buyer_requirement_id:
                reqs_map = self.repo.lock_requirements([item.buyer_requirement_id])
                req = reqs_map.get(item.buyer_requirement_id)

            # Tier 5 Lock on Approval
            approval = None
            approvals = self.repo.lock_approvals_by_order(order.id)
            for a in approvals:
                if a.order_item_id == item.id:
                    approval = a
                    break

            # Handle delta accounting
            if delta > Decimal("0.000"):
                # Quantity Increase
                if listing:
                    if listing.available_quantity < delta:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Insufficient listing stock to increase quantity by {delta}. "
                                f"Available: {listing.available_quantity}"
                            ),
                        )
                    listing.available_quantity -= delta
                    if listing.available_quantity == Decimal("0.000"):
                        listing.status = STATUS_CLOSED

                    self.db.add(
                        InventoryAdjustment(
                            listing_id=listing.id,
                            order_id=order.id,
                            amendment_id=amendment.id,
                            change_type=CHANGE_TYPE_AMENDMENT_DELTA,
                            quantity_delta=-delta,
                            recorded_by_user_id=current_user.id,
                            notes=f"Amendment {amendment.id} quantity increase delta",
                        )
                    )

                if approval and approval.status == APPROVAL_STATUS_PENDING:
                    approval.proposed_quantity = new_qty
                    approval.updated_at = now_utc

                snapshot["demand_restored"] = "0.000"
                amendment.new_value = json.dumps(snapshot)

            elif delta < Decimal("0.000"):
                # Quantity Decrease
                release_qty = -delta
                if listing:
                    listing.available_quantity += release_qty
                    if listing.status == STATUS_CLOSED and listing.available_quantity > 0:
                        listing.status = STATUS_PARTIALLY_FULFILLED

                    self.db.add(
                        InventoryAdjustment(
                            listing_id=listing.id,
                            order_id=order.id,
                            amendment_id=amendment.id,
                            change_type=CHANGE_TYPE_AMENDMENT_DELTA,
                            quantity_delta=release_qty,
                            recorded_by_user_id=current_user.id,
                            notes=f"Amendment {amendment.id} quantity decrease release",
                        )
                    )

                actual_restored = Decimal("0.000")
                if approval:
                    if approval.status == APPROVAL_STATUS_PENDING:
                        approval.proposed_quantity = new_qty
                        approval.updated_at = now_utc
                    elif approval.status == APPROVAL_STATUS_APPROVED:
                        # Cumulative accounting
                        effective_ams = self.repo.get_effective_quantity_amendments(order.id)
                        prior_restored = Decimal("0.000")
                        for ea in effective_ams:
                            try:
                                snap = json.loads(ea.new_value)
                                if snap.get("order_item_id") == str(item.id):
                                    prior_restored += Decimal(str(snap.get("demand_restored", "0.000")))
                            except (json.JSONDecodeError, ValueError):
                                pass

                        demand_consumed_before = max(
                            Decimal("0.000"), approval.approved_quantity - prior_restored
                        )
                        raw_demand_to_restore = max(Decimal("0.000"), demand_consumed_before - new_qty)

                        today = date.today()
                        if (
                            req
                            and not req.is_deleted
                            and req.required_by_date >= today
                            and req.status in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED)
                        ):
                            gap = max(Decimal("0.000"), req.required_quantity - req.remaining_quantity)
                            actual_restored = min(raw_demand_to_restore, gap)
                            if actual_restored > Decimal("0.000"):
                                req.remaining_quantity += actual_restored
                                if req.remaining_quantity == req.required_quantity:
                                    req.status = REQUIREMENT_STATUS_ACTIVE

                snapshot["demand_restored"] = str(actual_restored)
                amendment.new_value = json.dumps(snapshot)

            # Update line item and order totals
            item.quantity = new_qty
            item.subtotal = item.quantity * item.unit_price
            order.total_amount = sum(i.subtotal for i in order.items)

        elif amendment.amendment_type == AMENDMENT_TYPE_PRICE:
            snapshot = json.loads(amendment.new_value)
            item_id = uuid.UUID(snapshot["order_item_id"])
            new_pr = Decimal(str(snapshot["unit_price"]))

            item = self.repo.get_order_item(order.id, item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

            item.unit_price = new_pr
            item.subtotal = item.quantity * item.unit_price
            order.total_amount = sum(i.subtotal for i in order.items)

        elif amendment.amendment_type == AMENDMENT_TYPE_DELIVERY_DATE:
            snapshot = json.loads(amendment.new_value)
            new_date_str = snapshot.get("delivery_arranged_date")
            if new_date_str:
                order.delivery_arranged_date = date.fromisoformat(new_date_str)

        elif amendment.amendment_type == AMENDMENT_TYPE_TERMS:
            snapshot = json.loads(amendment.new_value)
            order.delivery_notes = snapshot.get("terms")

        # Mark amendment effective
        amendment.buyer_confirmed = True
        amendment.farmer_confirmed = True
        amendment.status = AMENDMENT_STATUS_EFFECTIVE
        amendment.effective_at = now_utc
        amendment.updated_at = now_utc
        order.updated_at = now_utc

        # Notify proposer
        self.db.add(
            Notification(
                user_id=amendment.proposed_by_user_id,
                event_type="order_amendment_accepted",
                title="Order Amendment Accepted",
                body=f"Your {amendment.amendment_type} amendment for Order {order.order_number} has been accepted.",
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return OrderAmendmentResponse(
            id=amendment.id,
            order_id=amendment.order_id,
            proposed_by_user_id=amendment.proposed_by_user_id,
            amendment_type=amendment.amendment_type,
            old_value=amendment.old_value,
            new_value=amendment.new_value,
            justification=amendment.justification,
            buyer_confirmed=amendment.buyer_confirmed,
            farmer_confirmed=amendment.farmer_confirmed,
            status=amendment.status,
            effective_at=amendment.effective_at,
            created_at=amendment.created_at,
            updated_at=amendment.updated_at,
        )

    def reject_amendment(
        self,
        current_user: User,
        order_id: uuid.UUID,
        amendment_id: uuid.UUID,
    ) -> OrderAmendmentResponse:
        """Reject a proposed amendment."""
        self._ensure_active_verified(current_user)

        # Tier 2 Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        amendment = self.repo.get_amendment(order.id, amendment_id)
        if not amendment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Amendment '{amendment_id}' not found")

        if amendment.status != AMENDMENT_STATUS_PROPOSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Amendment has already been reviewed with status: '{amendment.status}'",
            )

        if current_user.id == amendment.proposed_by_user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Proposer cannot reject their own amendment",
            )

        now_utc = datetime.now(timezone.utc)
        amendment.status = AMENDMENT_STATUS_REJECTED
        amendment.updated_at = now_utc
        order.updated_at = now_utc

        # Notify proposer
        self.db.add(
            Notification(
                user_id=amendment.proposed_by_user_id,
                event_type="order_amendment_rejected",
                title="Order Amendment Rejected",
                body=f"Your {amendment.amendment_type} amendment for Order {order.order_number} was rejected.",
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return OrderAmendmentResponse(
            id=amendment.id,
            order_id=amendment.order_id,
            proposed_by_user_id=amendment.proposed_by_user_id,
            amendment_type=amendment.amendment_type,
            old_value=amendment.old_value,
            new_value=amendment.new_value,
            justification=amendment.justification,
            buyer_confirmed=amendment.buyer_confirmed,
            farmer_confirmed=amendment.farmer_confirmed,
            status=amendment.status,
            effective_at=amendment.effective_at,
            created_at=amendment.created_at,
            updated_at=amendment.updated_at,
        )

    # -----------------------------------------------------------------------
    # Batch 4: Delivery Coordination
    # -----------------------------------------------------------------------

    def arrange_delivery(
        self,
        current_user: User,
        order_id: uuid.UUID,
        payload: DeliveryArrangeRequest,
    ) -> OrderDetailResponse:
        """Schedule and record bilateral delivery arrangements."""
        self._ensure_active_verified(current_user)

        # Tier 2 Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        if order.status in (ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED, ORDER_STATUS_DISPUTED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot arrange delivery for order in '{order.status}' status",
            )

        now_utc = datetime.now(timezone.utc)
        order.delivery_method = payload.delivery_method
        order.delivery_destination_address = payload.delivery_destination_address
        order.delivery_arranged_date = payload.delivery_arranged_date
        if payload.delivery_notes:
            order.delivery_notes = payload.delivery_notes
        order.delivery_status = DELIVERY_STATUS_ARRANGED
        order.status = ORDER_STATUS_DELIVERY_ARRANGED
        order.updated_at = now_utc

        counterparty_id = order.farmer_id if current_user.id == order.buyer_id else order.buyer_id
        self.db.add(
            Notification(
                user_id=counterparty_id,
                event_type="order_delivery_arranged",
                title="Delivery Arranged",
                body=(
                    f"Delivery arrangements scheduled for {payload.delivery_arranged_date} "
                    f"on Order {order.order_number}."
                ),
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return self.get_order_detail(current_user, order.id)

    def mark_delivery_completed(
        self,
        current_user: User,
        order_id: uuid.UUID,
    ) -> OrderDetailResponse:
        """Mark physical delivery completed by one counterparty."""
        self._ensure_active_verified(current_user)

        # Tier 2 Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        if order.status != ORDER_STATUS_DELIVERY_ARRANGED or order.delivery_status != DELIVERY_STATUS_ARRANGED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot mark delivery completed. Order must be in 'delivery_arranged' status "
                    f"(current order status: '{order.status}', delivery status: '{order.delivery_status}')."
                ),
            )

        now_utc = datetime.now(timezone.utc)
        order.delivery_status = DELIVERY_STATUS_COMPLETION_MARKED
        order.delivery_completion_marked_by_user_id = current_user.id
        order.delivery_completion_marked_at = now_utc
        order.updated_at = now_utc

        counterparty_id = order.farmer_id if current_user.id == order.buyer_id else order.buyer_id
        actor_name = self._get_user_display_name(current_user)
        self.db.add(
            Notification(
                user_id=counterparty_id,
                event_type="order_delivery_completion_marked",
                title="Delivery Marked Completed",
                body=(
                    f"{actor_name} has marked delivery completed for Order {order.order_number}. "
                    "Please verify goods and acknowledge receipt."
                ),
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return self.get_order_detail(current_user, order.id)

    def acknowledge_delivery(
        self,
        current_user: User,
        order_id: uuid.UUID,
        payload: Optional[DeliveryAcknowledgeRequest] = None,
    ) -> OrderDetailResponse:
        """Acknowledge delivery receipt adhering to the revised bilateral & admin acknowledgement policy."""
        self._ensure_active_verified(current_user)

        # Tier 2 Order Lock
        order = self.repo.lock_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        # Anti-enumeration and participant authorization
        # Invariant: Administrators cannot provide delivery receipt acknowledgements on behalf of commercial participants.
        if current_user.role == "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot provide delivery receipt acknowledgements on behalf of commercial participants",
            )
        if current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        # Self-acknowledgement prevention: applies universally across all roles
        if current_user.id == order.delivery_completion_marked_by_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The party who marked delivery completion cannot acknowledge their own completion",
            )

        if order.delivery_status != DELIVERY_STATUS_COMPLETION_MARKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Delivery must be marked completed before receipt can be acknowledged",
            )

        # Check duplicate acknowledgement by the same user
        existing_ack = self.repo.get_delivery_acknowledgement(order.id, current_user.id)
        if existing_ack:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already acknowledged delivery for this order",
            )

        now_utc = datetime.now(timezone.utc)
        notes = payload.notes if payload else None

        # Atomically record new delivery acknowledgement
        new_ack = OrderDeliveryAcknowledgement(
            order_id=order.id,
            user_id=current_user.id,
            acknowledged_at=now_utc,
            notes=notes,
        )
        self.repo.add_delivery_acknowledgement(new_ack)
        self.db.flush()

        # Determine required acknowledgements:
        # Scenario A: Farmer marked -> Buyer must acknowledge
        # Scenario B: Buyer marked -> Farmer must acknowledge
        # Scenario C: Admin marked -> Both Farmer and Buyer must independently acknowledge
        required_user_ids = set()
        if order.delivery_completion_marked_by_user_id == order.farmer_id:
            required_user_ids.add(order.buyer_id)
        elif order.delivery_completion_marked_by_user_id == order.buyer_id:
            required_user_ids.add(order.farmer_id)
        else:
            required_user_ids.add(order.farmer_id)
            required_user_ids.add(order.buyer_id)

        all_acks = self.repo.get_delivery_acknowledgements(order.id)
        recorded_user_ids = {a.user_id for a in all_acks}

        all_satisfied = required_user_ids.issubset(recorded_user_ids)

        if all_satisfied:
            # Order transitions to completed
            order.delivery_status = DELIVERY_STATUS_COMPLETED
            order.delivery_acknowledged_by_user_id = current_user.id
            order.delivery_acknowledged_at = now_utc
            order.status = ORDER_STATUS_COMPLETED
            order.completed_at = now_utc

            for item in order.items:
                if item.status == ORDER_ITEM_STATUS_CONFIRMED:
                    item.status = ORDER_ITEM_STATUS_FULFILLED

            order.updated_at = now_utc

            # Send completion notification to counterparties
            for recipient_id in (order.farmer_id, order.buyer_id):
                self.db.add(
                    Notification(
                        user_id=recipient_id,
                        event_type="order_delivery_acknowledged",
                        title="Delivery Acknowledged & Order Completed",
                        body=f"Receipt acknowledged for Order {order.order_number}. Transaction successfully completed.",
                        reference_type="order",
                        reference_id=order.id,
                    )
                )
        else:
            # Partially acknowledged (Scenario C waiting for second counterparty)
            order.updated_at = now_utc
            remaining_ids = required_user_ids - recorded_user_ids
            actor_name = self._get_user_display_name(current_user)
            for waiting_for_id in remaining_ids:
                self.db.add(
                    Notification(
                        user_id=waiting_for_id,
                        event_type="order_delivery_partially_acknowledged",
                        title="Delivery Partially Acknowledged",
                        body=(
                            f"{actor_name} has acknowledged delivery for Order {order.order_number}. "
                            "Your acknowledgement is required to complete the order."
                        ),
                        reference_type="order",
                        reference_id=order.id,
                    )
                )

        self.db.commit()
        return self.get_order_detail(current_user, order.id)

    # -----------------------------------------------------------------------
    # Batch 5: Inventory Audit Endpoints
    # -----------------------------------------------------------------------

    def get_order_inventory_adjustments(
        self,
        current_user: User,
        order_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> InventoryAdjustmentListResponse:
        """Retrieve paginated inventory adjustments linked to an order."""
        self._ensure_active_verified(current_user)
        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' not found")

        adjustments, total = self.repo.get_inventory_adjustments_for_order(order_id, page, page_size)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        items = [
            InventoryAdjustmentResponse(
                id=adj.id,
                listing_id=adj.listing_id,
                order_id=adj.order_id,
                amendment_id=adj.amendment_id,
                change_type=adj.change_type,
                quantity_delta=adj.quantity_delta,
                recorded_by_user_id=adj.recorded_by_user_id,
                notes=adj.notes,
                created_at=adj.created_at,
            )
            for adj in adjustments
        ]

        return InventoryAdjustmentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_listing_inventory_adjustments(
        self,
        current_user: User,
        listing_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> InventoryAdjustmentListResponse:
        """Retrieve paginated inventory adjustments linked to a farmer listing."""
        self._ensure_active_verified(current_user)
        listing = self.db.query(ProduceListing).filter(ProduceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produce listing '{listing_id}' not found",
            )

        if current_user.role != "admin" and listing.farmer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted to the listing owner",
            )

        adjustments, total = self.repo.get_inventory_adjustments_for_listing(listing_id, page, page_size)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        items = [
            InventoryAdjustmentResponse(
                id=adj.id,
                listing_id=adj.listing_id,
                order_id=adj.order_id,
                amendment_id=adj.amendment_id,
                change_type=adj.change_type,
                quantity_delta=adj.quantity_delta,
                recorded_by_user_id=adj.recorded_by_user_id,
                notes=adj.notes,
                created_at=adj.created_at,
            )
            for adj in adjustments
        ]

        return InventoryAdjustmentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
