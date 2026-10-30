"""Service layer orchestrating Structured Offers and Negotiation (Module 3).

Enforces:
- Strict role verification (Verified Farmer vs. Verified Buyer).
- 7-point dual-reference item validation (listing stock + requirement demand).
- Immutable counter-offer lineage without branching.
- Pessimistic row-level locking with ascending ID sort order.
- Atomic acceptance: listing inventory deduction, requirement fulfillment calculation,
  immutable Order & OrderItem instantiation, and audit ledger persistence.
- Timezone-aware UTC lazy expiry under row lock.
- Atomic in-app notifications and non-blocking post-commit email dispatch.
"""

import logging
import math
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.listing import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_PARTIALLY_FULFILLED,
    ProduceListing,
)
from app.models.notification import (
    NOTIFICATION_REF_OFFER,
    NOTIFICATION_REF_ORDER,
    Notification,
)
from app.models.offer import (
    OFFER_ITEM_STATUS_PROPOSED,
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_COUNTERED,
    OFFER_STATUS_EXPIRED,
    OFFER_STATUS_PENDING,
    OFFER_STATUS_REJECTED,
    OFFER_STATUS_WITHDRAWN,
    Offer,
    OfferItem,
)
from app.models.order import (
    CHANGE_TYPE_ORDER_FULFILLMENT,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_STATUS_PENDING,
    InventoryAdjustment,
    Order,
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
    APPROVAL_STATUS_NOT_APPLIED,
    APPROVAL_STATUS_PENDING,
    RequirementFulfillmentApproval,
)
from app.models.user import User
from app.notifications.email import send_email_notification
from app.offers.repository import OfferRepository
from app.offers.schemas import (
    CounterOfferCreate,
    ItemFulfillmentDecision,
    OfferAcceptRequest,
    OfferAcceptResponse,
    OfferCreate,
    OfferDetailResponse,
    OfferHistoryResponse,
    OfferItemResponse,
    OfferListResponse,
    OfferRejectRequest,
    OfferSummaryResponse,
    UserSummary,
)


class OfferService:
    """Orchestrates structured negotiation workflows, validation, and atomic transactions."""

    def __init__(self, db: Session, repository: Optional[OfferRepository] = None) -> None:
        self.db = db
        self.repo = repository or OfferRepository(db)
        self.settings = get_settings()

    # -----------------------------------------------------------------------
    # Helper / Validation methods
    # -----------------------------------------------------------------------

    def _ensure_active_verified(self, user: User, role_name: str) -> None:
        """Verify user is active and has verified verification status."""
        if getattr(user, "is_deleted", False) or getattr(user, "account_status", "active") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{role_name.capitalize()} account is not active",
            )
        if getattr(user, "verification_status", "unverified") != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{role_name.capitalize()} must be verified to participate in negotiation",
            )

    def _check_and_apply_lazy_expiry(self, offer: Offer) -> bool:
        """Check if a pending offer has expired; if so, persist expired status and return True."""
        if offer.status == OFFER_STATUS_PENDING and offer.expires_at:
            now_utc = datetime.now(timezone.utc)
            exp = offer.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= now_utc:
                offer.status = OFFER_STATUS_EXPIRED
                self.db.flush()
                return True
        return False

    def _effective_status(self, offer: Offer) -> str:
        """Evaluate effective status in-memory for read operations without mutating database."""
        if offer.status == OFFER_STATUS_PENDING and offer.expires_at:
            now_utc = datetime.now(timezone.utc)
            exp = offer.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= now_utc:
                return OFFER_STATUS_EXPIRED
        return offer.status

    def _validate_items_and_calculate_totals(
        self,
        farmer_id: uuid.UUID,
        buyer_id: uuid.UUID,
        items_payload: List,
    ) -> Tuple[List[dict], Decimal]:
        """Enforce 7-point dual-reference item validation and calculate server-side subtotals."""
        listing_ids = [item.listing_id for item in items_payload]
        requirement_ids = [item.buyer_requirement_id for item in items_payload if item.buyer_requirement_id]

        # Query listings and requirements
        listings_map = self.repo.lock_listings(listing_ids)
        requirements_map = self.repo.lock_requirements(requirement_ids)

        now_utc = datetime.now(timezone.utc)
        today = date.today()

        listing_demand: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        requirement_supply: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)

        prepared_items = []
        total_amount = Decimal("0.00")

        for idx, item_in in enumerate(items_payload):
            lid = item_in.listing_id
            rid = item_in.buyer_requirement_id

            # 1. Listing existence and farmer ownership
            listing = listings_map.get(lid)
            if not listing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Produce listing with ID '{lid}' at item {idx} not found",
                )
            if listing.farmer_id != farmer_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Farmer does not own produce listing '{listing.product_name}' at item {idx}",
                )
            if listing.is_deleted or listing.status not in (STATUS_ACTIVE, STATUS_PARTIALLY_FULFILLED):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Produce listing '{listing.product_name}' is not currently active",
                )
            listing_exp = listing.expires_at
            if listing_exp.tzinfo is None:
                listing_exp = listing_exp.replace(tzinfo=timezone.utc)
            if listing_exp <= now_utc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Produce listing '{listing.product_name}' has expired",
                )

            # 2. Requirement existence and buyer ownership (if provided)
            if rid:
                req = requirements_map.get(rid)
                if not req:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Buyer requirement with ID '{rid}' at item {idx} not found",
                    )
                if req.buyer_id != buyer_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Buyer does not own requirement '{req.title}' at item {idx}",
                    )
                if req.is_deleted or req.status not in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Buyer requirement '{req.title}' is not currently active",
                    )
                if req.required_by_date < today:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Buyer requirement '{req.title}' procurement deadline has passed",
                    )

                # 3. Category compatibility (if both specify categories)
                if listing.category_id and req.category_id and listing.category_id != req.category_id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Category mismatch between listing '{listing.product_name}' and requirement '{req.title}'",
                    )

                # 4. Unit compatibility
                if item_in.unit.strip().lower() != req.unit.strip().lower():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Unit '{item_in.unit}' at item {idx} does not match requirement unit '{req.unit}'",
                    )
                requirement_supply[rid] += item_in.quantity

            # Validate listing unit compatibility
            if item_in.unit.strip().lower() != listing.unit.strip().lower():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Unit '{item_in.unit}' at item {idx} does not match listing unit '{listing.unit}'",
                )

            listing_demand[lid] += item_in.quantity

            # Server-calculated subtotal: quantity * unit_price rounded to 2 decimal places
            subtotal = Decimal(str(round(item_in.quantity * item_in.unit_price, 2)))
            total_amount += subtotal

            product_title = item_in.product_name or listing.product_name

            prepared_items.append({
                "listing_id": lid,
                "buyer_requirement_id": rid,
                "product_name": product_title,
                "quantity": item_in.quantity,
                "unit": item_in.unit.strip().lower(),
                "unit_price": item_in.unit_price,
                "subtotal": subtotal,
                "quality_grade": item_in.quality_grade or listing.quality_grade,
            })

        # Check total aggregated quantities against available stocks
        for lid, needed_qty in listing_demand.items():
            listing = listings_map[lid]
            if listing.available_quantity < needed_qty:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Offered quantity ({needed_qty}) exceeds available stock "
                        f"({listing.available_quantity}) for listing '{listing.product_name}'"
                    ),
                )

        for rid, offered_qty in requirement_supply.items():
            req = requirements_map[rid]
            if req.remaining_quantity < offered_qty:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Offered quantity ({offered_qty}) exceeds remaining demand "
                        f"({req.remaining_quantity}) for requirement '{req.title}'"
                    ),
                )

        return prepared_items, total_amount

    # -----------------------------------------------------------------------
    # Main Workflow Operations
    # -----------------------------------------------------------------------

    def create_offer(self, current_user: User, payload: OfferCreate) -> OfferDetailResponse:
        """Create an initial structured offer inside a conversation."""
        self._ensure_active_verified(current_user, current_user.role)

        if current_user.id == payload.recipient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Self-negotiation is forbidden: sender and recipient cannot be the same user",
            )

        recipient = self.db.query(User).filter(User.id == payload.recipient_id).first()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipient user with ID '{payload.recipient_id}' not found",
            )
        self._ensure_active_verified(recipient, recipient.role)

        # Opposite role validation
        if current_user.role == recipient.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Offers must be bilateral between a farmer and a buyer. Both users have role '{current_user.role}'",
            )

        if current_user.role == "farmer":
            farmer_id = current_user.id
            buyer_id = recipient.id
        elif current_user.role == "buyer":
            buyer_id = current_user.id
            farmer_id = recipient.id
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified farmers and buyers can initiate offers",
            )

        # Conversation handling: reuse existing or create atomically
        conv = self.repo.get_or_create_conversation(farmer_id=farmer_id, buyer_id=buyer_id)

        # Item validation and financial calculations
        prepared_items, total_amount = self._validate_items_and_calculate_totals(
            farmer_id=farmer_id,
            buyer_id=buyer_id,
            items_payload=payload.items,
        )

        # Default expiration window if not specified
        expires_at = payload.expires_at
        if not expires_at:
            hours = getattr(self.settings, "default_offer_expiry_hours", 72)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

        offer_number = self.repo.generate_offer_number()

        header_data = {
            "offer_number": offer_number,
            "conversation_id": conv.id,
            "sender_id": current_user.id,
            "recipient_id": recipient.id,
            "parent_offer_id": None,
            "delivery_terms": payload.delivery_terms,
            "proposed_delivery_date": payload.proposed_delivery_date,
            "total_amount": total_amount,
            "status": OFFER_STATUS_PENDING,
            "expires_at": expires_at,
        }

        offer = self.repo.create_offer(header_data, prepared_items)

        # Add atomic in-app notification for recipient
        self.db.add(Notification(
            user_id=recipient.id,
            event_type="offer_received",
            title="New Offer Received",
            body=f"You received an offer ({offer_number}) totaling ₹{total_amount:.2f}.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer.id,
        ))

        self.db.commit()

        # Non-blocking post-commit email dispatch
        try:
            if getattr(recipient, "email", None):
                send_email_notification(
                    to_email=recipient.email,
                    subject=f"[AgriDirect] New Offer {offer_number}",
                    body=f"You have received a new offer {offer_number} totaling ₹{total_amount:.2f}. Log in to review.",
                )
        except Exception as email_err:
            logger.warning("Non-blocking post-commit email dispatch failed: %s", email_err)

        return self._to_detail_response(offer)

    def counter_offer(
        self,
        current_user: User,
        parent_offer_id: uuid.UUID,
        payload: CounterOfferCreate,
    ) -> OfferDetailResponse:
        """Submit a counter-proposal to an existing pending offer."""
        self._ensure_active_verified(current_user, current_user.role)

        # Lock parent offer FOR UPDATE to serialize concurrent counter/accept attempts
        parent = self.repo.get_by_id(parent_offer_id, for_update=True)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent offer with ID '{parent_offer_id}' not found",
            )

        # Authorization: Only the recipient of the pending offer can counter it
        if parent.recipient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient of a pending offer can submit a counter-offer",
            )

        # State check
        if self._check_and_apply_lazy_expiry(parent):
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Parent offer {parent.offer_number} has expired and cannot be countered",
            )

        if parent.status != OFFER_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot counter offer in '{parent.status}' status (must be 'pending')",
            )

        # Roles reverse: new sender is current recipient, new recipient is parent sender
        new_sender = current_user
        new_recipient_id = parent.sender_id
        recipient = self.db.query(User).filter(User.id == new_recipient_id).first()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Counterparty user not found",
            )
        self._ensure_active_verified(recipient, recipient.role)

        if parent.conversation.farmer_id == new_sender.id:
            farmer_id = new_sender.id
            buyer_id = recipient.id
        else:
            farmer_id = recipient.id
            buyer_id = new_sender.id

        # Validate items under lock
        prepared_items, total_amount = self._validate_items_and_calculate_totals(
            farmer_id=farmer_id,
            buyer_id=buyer_id,
            items_payload=payload.items,
        )

        # Expiry
        expires_at = payload.expires_at
        if not expires_at:
            hours = getattr(self.settings, "default_offer_expiry_hours", 72)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

        # Update parent offer to countered (preventing concurrent branches)
        parent.status = OFFER_STATUS_COUNTERED

        new_offer_number = self.repo.generate_offer_number()
        header_data = {
            "offer_number": new_offer_number,
            "conversation_id": parent.conversation_id,
            "sender_id": new_sender.id,
            "recipient_id": recipient.id,
            "parent_offer_id": parent.id,
            "delivery_terms": payload.delivery_terms or parent.delivery_terms,
            "proposed_delivery_date": payload.proposed_delivery_date or parent.proposed_delivery_date,
            "total_amount": total_amount,
            "status": OFFER_STATUS_PENDING,
            "expires_at": expires_at,
        }

        counter_offer = self.repo.create_offer(header_data, prepared_items)

        # Notification for counterparty
        self.db.add(Notification(
            user_id=recipient.id,
            event_type="counter_offer_received",
            title="Counter-Offer Received",
            body=f"You received a counter-offer ({new_offer_number}) on offer {parent.offer_number}.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=counter_offer.id,
        ))

        self.db.commit()

        try:
            if getattr(recipient, "email", None):
                send_email_notification(
                    to_email=recipient.email,
                    subject=f"[AgriDirect] Counter-Offer Received: {new_offer_number}",
                    body=f"A counter-offer {new_offer_number} was submitted. Review the modified terms online.",
                )
        except Exception as email_err:
            logger.warning("Non-blocking post-commit email dispatch failed: %s", email_err)

        return self._to_detail_response(counter_offer)

    def accept_offer(
        self,
        current_user: User,
        offer_id: uuid.UUID,
        payload: Optional[OfferAcceptRequest] = None,
        approve_requirement_update: Optional[bool] = True,
        close_requirement: Optional[bool] = None,
    ) -> OfferAcceptResponse:
        """Atomically accept an offer, deduct stock, update requirement fulfillment, and instantiate Order."""
        self._ensure_active_verified(current_user, current_user.role)

        # 1. Lock the offer row FOR UPDATE (Tier 1)
        offer = self.repo.get_by_id(offer_id, for_update=True)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID '{offer_id}' not found",
            )

        # 2. Authorization: only the recipient can accept
        if offer.recipient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient of a pending offer can accept it",
            )

        # 3. Status and expiry check under lock
        if self._check_and_apply_lazy_expiry(offer):
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Offer {offer.offer_number} has expired and cannot be accepted",
            )

        if offer.status != OFFER_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot accept offer in '{offer.status}' status (must be 'pending')",
            )

        # 4. Check if order was somehow already created (idempotency guard)
        existing_order = self.db.query(Order).filter(Order.source_offer_id == offer.id).first()
        if existing_order:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An order ({existing_order.order_number}) has already been generated for this offer",
            )

        # 5. Lock listings in deterministic ascending UUID order (Tier 3)
        listing_ids = [item.listing_id for item in offer.items if item.listing_id]
        listings_map = self.repo.lock_listings(listing_ids)

        # 6. Lock requirements in deterministic ascending UUID order (Tier 4)
        requirement_ids = [item.buyer_requirement_id for item in offer.items if item.buyer_requirement_id]
        requirements_map = self.repo.lock_requirements(requirement_ids)

        # Resolve acceptance fulfillment parameters
        default_apply = payload.apply_to_requirement if payload is not None else (approve_requirement_update is not False)
        default_approved_qty = payload.approved_quantity if payload is not None else None
        default_close = payload.close_requirement if payload is not None else bool(close_requirement)

        item_decisions_map: Dict[uuid.UUID, ItemFulfillmentDecision] = {}
        if payload and payload.item_fulfillments:
            for item_dec in payload.item_fulfillments:
                item_decisions_map[item_dec.offer_item_id] = item_dec

        # 7. Aggregate and validate quantities
        listing_demand: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        requirement_supply: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        buyer_req_approved_demand: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)

        for item in offer.items:
            if item.listing_id:
                listing_demand[item.listing_id] += item.quantity
            if item.buyer_requirement_id:
                requirement_supply[item.buyer_requirement_id] += item.quantity
                req = requirements_map.get(item.buyer_requirement_id)
                is_buyer = (current_user.id == req.buyer_id) if req else False
                if is_buyer:
                    dec = item_decisions_map.get(item.id)
                    item_apply = dec.apply_to_requirement if dec else default_apply
                    item_approved_qty = dec.approved_quantity if dec else default_approved_qty
                    if item_apply:
                        eff_qty = item_approved_qty if item_approved_qty is not None else item.quantity
                        if eff_qty <= Decimal("0"):
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Approved quantity must be positive",
                            )
                        if eff_qty > item.quantity:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"Approved quantity ({eff_qty}) cannot exceed proposed quantity ({item.quantity})",
                            )
                        buyer_req_approved_demand[item.buyer_requirement_id] += eff_qty

        now_utc = datetime.now(timezone.utc)
        today = date.today()

        for lid, needed_qty in listing_demand.items():
            listing = listings_map.get(lid)
            if not listing or listing.is_deleted or listing.status not in (STATUS_ACTIVE, STATUS_PARTIALLY_FULFILLED):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Listing '{listing.product_name if listing else lid}' is no longer active",
                )
            lexp = listing.expires_at
            if lexp.tzinfo is None:
                lexp = lexp.replace(tzinfo=timezone.utc)
            if lexp <= now_utc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Listing '{listing.product_name}' has expired",
                )
            if listing.available_quantity < needed_qty:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Insufficient stock for '{listing.product_name}'. "
                        f"Available: {listing.available_quantity}, Required: {needed_qty}"
                    ),
                )

        for rid, offered_qty in requirement_supply.items():
            req = requirements_map.get(rid)
            if not req or req.is_deleted or req.status not in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Requirement '{req.title if req else rid}' is no longer active",
                )
            if req.required_by_date < today:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Requirement '{req.title}' deadline has passed",
                )
            is_buyer = (current_user.id == req.buyer_id)
            if is_buyer:
                total_approved = buyer_req_approved_demand.get(rid, Decimal("0.000"))
                if total_approved > req.remaining_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Approved quantity ({total_approved}) exceeds current remaining demand "
                            f"({req.remaining_quantity}) for requirement '{req.title}'. No quantity clamped."
                        ),
                    )
            else:
                if req.remaining_quantity < offered_qty:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Offered quantity ({offered_qty}) exceeds remaining demand "
                            f"({req.remaining_quantity}) for requirement '{req.title}'"
                        ),
                    )

        # 8. Create Order and snapshot OrderItems (Tier 2)
        order_number = self.repo.generate_order_number()
        order = self.repo.create_order_from_accepted_offer(
            offer=offer,
            current_user=current_user,
            order_number=order_number,
        )

        # 9. Apply listing deductions and append InventoryAdjustment audit rows
        for lid, needed_qty in listing_demand.items():
            listing = listings_map[lid]
            listing.available_quantity -= needed_qty
            listing.status = STATUS_CLOSED if listing.available_quantity == 0 else STATUS_PARTIALLY_FULFILLED

            self.db.add(InventoryAdjustment(
                listing_id=listing.id,
                order_id=order.id,
                change_type=CHANGE_TYPE_ORDER_FULFILLMENT,
                quantity_delta=-needed_qty,
                recorded_by_user_id=current_user.id,
                notes=f"Order fulfillment for offer {offer.offer_number}",
            ))

        # 10. Apply requirement fulfillment and create RequirementFulfillmentApproval records (Tier 5)
        order_item_map = getattr(order, "_item_map", {})

        for item in offer.items:
            if not item.buyer_requirement_id:
                continue

            req = requirements_map[item.buyer_requirement_id]
            order_item = order_item_map.get(item.id)
            if not order_item:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Order item snapshot missing for offer item {item.id}",
                )

            # Defensive verification of cross-table consistency (ADR-003 Section 5.2)
            if order_item.buyer_requirement_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cannot create fulfillment approval for order item without buyer_requirement_id",
                )
            if order_item.buyer_requirement_id != req.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Requirement ID mismatch between order item and approval request",
                )
            if order_item.order_id != order.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Order ID mismatch between order item and approval request",
                )

            is_buyer = (current_user.id == req.buyer_id)

            if is_buyer:
                dec = item_decisions_map.get(item.id)
                item_apply = dec.apply_to_requirement if dec else default_apply
                item_approved_qty = dec.approved_quantity if dec else default_approved_qty
                item_close = dec.close_requirement if dec else default_close

                if item_apply:
                    effective_qty = item_approved_qty if item_approved_qty is not None else item.quantity
                    req.remaining_quantity -= effective_qty
                    if item_close:
                        req.status = REQUIREMENT_STATUS_CLOSED
                    elif req.status == REQUIREMENT_STATUS_ACTIVE:
                        req.status = REQUIREMENT_STATUS_PARTIALLY_FULFILLED

                    approval = RequirementFulfillmentApproval(
                        requirement_id=req.id,
                        order_id=order.id,
                        order_item_id=order_item.id,
                        proposed_quantity=item.quantity,
                        approved_quantity=effective_qty,
                        status=APPROVAL_STATUS_APPROVED,
                        reviewed_by_user_id=current_user.id,
                        reviewed_at=now_utc,
                    )
                    self.db.add(approval)

                    notification_body = (
                        f"Order {order_number} has fulfilled {effective_qty} {req.unit} of your requirement '{req.title}'. "
                        f"Approved remaining demand is now {req.remaining_quantity} {req.unit}. "
                        f"Final status is '{req.status}'."
                    )
                else:
                    # Buyer explicitly instructed not to apply fulfillment
                    if item_close:
                        req.status = REQUIREMENT_STATUS_CLOSED

                    approval = RequirementFulfillmentApproval(
                        requirement_id=req.id,
                        order_id=order.id,
                        order_item_id=order_item.id,
                        proposed_quantity=item.quantity,
                        approved_quantity=None,
                        status=APPROVAL_STATUS_NOT_APPLIED,
                        reviewed_by_user_id=current_user.id,
                        reviewed_at=now_utc,
                    )
                    self.db.add(approval)

                    notification_body = (
                        f"Order {order_number} created for {item.quantity} {req.unit} against requirement '{req.title}'. "
                        f"Per your instruction, remaining quantity was not reduced and remains {req.remaining_quantity} {req.unit}."
                    )
            else:
                # Farmer accepted offer: requirement remains untouched, pending approval record created
                approval = RequirementFulfillmentApproval(
                    requirement_id=req.id,
                    order_id=order.id,
                    order_item_id=order_item.id,
                    proposed_quantity=item.quantity,
                    approved_quantity=None,
                    status=APPROVAL_STATUS_PENDING,
                    reviewed_by_user_id=None,
                    reviewed_at=None,
                )
                self.db.add(approval)

                notification_body = (
                    f"Farmer accepted offer for Order {order_number} fulfilling {item.quantity} {req.unit} of requirement '{req.title}'. "
                    f"Pending your review and approval under BR-07."
                )

            self.db.add(Notification(
                user_id=req.buyer_id,
                event_type="requirement_fulfillment_calculated",
                title="Requirement Fulfillment Update",
                body=notification_body,
                reference_type=NOTIFICATION_REF_ORDER,
                reference_id=order.id,
            ))

        # 11. Mark offer accepted
        offer.status = OFFER_STATUS_ACCEPTED

        # 12. Add in-app notifications for counterparties
        sender_id = offer.sender_id
        recipient_id = offer.recipient_id

        self.db.add(Notification(
            user_id=sender_id,
            event_type="offer_accepted",
            title="Offer Accepted",
            body=f"Your offer {offer.offer_number} was accepted. Order {order_number} has been created.",
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=order.id,
        ))

        # Atomic commit
        self.db.commit()

        # Non-blocking post-commit emails
        try:
            sender_user = self.db.query(User).filter(User.id == sender_id).first()
            if sender_user and getattr(sender_user, "email", None):
                send_email_notification(
                    to_email=sender_user.email,
                    subject=f"[AgriDirect] Offer Accepted: {offer.offer_number}",
                    body=f"Your offer {offer.offer_number} was accepted! Order {order_number} has been created.",
                )
        except Exception as email_err:
            logger.warning("Non-blocking post-commit email notification failed: %s", email_err)

        return OfferAcceptResponse(
            offer_id=offer.id,
            offer_number=offer.offer_number,
            order_id=order.id,
            order_number=order.order_number,
            status=offer.status,
            total_amount=offer.total_amount,
            message="Offer accepted successfully and order generated atomically.",
        )

    def reject_offer(
        self,
        current_user: User,
        offer_id: uuid.UUID,
        payload: OfferRejectRequest,
    ) -> OfferDetailResponse:
        """Reject a pending offer."""
        self._ensure_active_verified(current_user, current_user.role)

        offer = self.repo.get_by_id(offer_id, for_update=True)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID '{offer_id}' not found",
            )

        if offer.recipient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient of a pending offer can reject it",
            )

        if self._check_and_apply_lazy_expiry(offer):
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Offer {offer.offer_number} has expired and cannot be rejected",
            )

        if offer.status != OFFER_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot reject offer in '{offer.status}' status",
            )

        offer.status = OFFER_STATUS_REJECTED

        # Notification for sender
        reason_text = f" Reason: {payload.reason}" if payload.reason else ""
        self.db.add(Notification(
            user_id=offer.sender_id,
            event_type="offer_rejected",
            title="Offer Rejected",
            body=f"Your offer {offer.offer_number} was rejected.{reason_text}",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer.id,
        ))

        self.db.commit()

        try:
            sender = self.db.query(User).filter(User.id == offer.sender_id).first()
            if sender and getattr(sender, "email", None):
                send_email_notification(
                    to_email=sender.email,
                    subject=f"[AgriDirect] Offer Rejected: {offer.offer_number}",
                    body=f"Your offer {offer.offer_number} was rejected by the counterparty.{reason_text}",
                )
        except Exception as email_err:
            logger.warning("Non-blocking post-commit email dispatch failed: %s", email_err)

        return self._to_detail_response(offer)

    def withdraw_offer(
        self,
        current_user: User,
        offer_id: uuid.UUID,
    ) -> OfferDetailResponse:
        """Withdraw an offer previously sent by the current user."""
        self._ensure_active_verified(current_user, current_user.role)

        offer = self.repo.get_by_id(offer_id, for_update=True)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID '{offer_id}' not found",
            )

        if offer.sender_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the sender can withdraw a pending offer",
            )

        if self._check_and_apply_lazy_expiry(offer):
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Offer {offer.offer_number} has expired and cannot be withdrawn",
            )

        if offer.status != OFFER_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot withdraw offer in '{offer.status}' status",
            )

        offer.status = OFFER_STATUS_WITHDRAWN

        self.db.add(Notification(
            user_id=offer.recipient_id,
            event_type="offer_withdrawn",
            title="Offer Withdrawn",
            body=f"The sender has withdrawn offer {offer.offer_number}.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer.id,
        ))

        self.db.commit()

        try:
            recipient = self.db.query(User).filter(User.id == offer.recipient_id).first()
            if recipient and getattr(recipient, "email", None):
                send_email_notification(
                    to_email=recipient.email,
                    subject=f"[AgriDirect] Offer Withdrawn: {offer.offer_number}",
                    body=f"Offer {offer.offer_number} was withdrawn by the sender.",
                )
        except Exception as email_err:
            logger.warning("Non-blocking post-commit email dispatch failed: %s", email_err)

        return self._to_detail_response(offer)

    def get_offer(self, current_user: User, offer_id: uuid.UUID) -> OfferDetailResponse:
        """Retrieve detailed view of an offer with authorization checks."""
        offer = self.repo.get_by_id(offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID '{offer_id}' not found",
            )

        # Scoped access: Participant or Admin only
        is_participant = current_user.id in (offer.sender_id, offer.recipient_id)
        is_admin = getattr(current_user, "role", "") == "admin"

        if not is_participant and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You are not authorized to view this negotiation proposal",
            )

        # Pure read-only view; lazy effective status calculated in memory
        return self._to_detail_response(offer)

    def get_offer_history(self, current_user: User, offer_id: uuid.UUID) -> OfferHistoryResponse:
        """Retrieve the complete chronological negotiation lineage chain."""
        offer = self.repo.get_by_id(offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID '{offer_id}' not found",
            )

        is_participant = current_user.id in (offer.sender_id, offer.recipient_id)
        is_admin = getattr(current_user, "role", "") == "admin"
        if not is_participant and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You are not authorized to view this negotiation history",
            )

        chain = self.repo.get_negotiation_history(offer)
        root_id = chain[0].id if chain else offer.id

        history_details = [self._to_detail_response(o) for o in chain]
        return OfferHistoryResponse(
            root_offer_id=root_id,
            current_offer_id=offer.id,
            chain_length=len(chain),
            history=history_details,
        )

    def list_user_offers(
        self,
        current_user: User,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        conversation_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> OfferListResponse:
        """List offers involving the current authenticated user."""
        self._ensure_active_verified(current_user, current_user.role)

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        offers, total = self.repo.list_offers(
            user_id=current_user.id,
            role_filter=role_filter,
            status_filter=status_filter,
            conversation_id=conversation_id,
            skip=skip,
            limit=page_size,
        )

        summaries = []
        for o in offers:
            summaries.append(
                OfferSummaryResponse(
                    id=o.id,
                    offer_number=o.offer_number,
                    conversation_id=o.conversation_id,
                    sender_id=o.sender_id,
                    recipient_id=o.recipient_id,
                    parent_offer_id=o.parent_offer_id,
                    delivery_terms=o.delivery_terms,
                    proposed_delivery_date=o.proposed_delivery_date,
                    total_amount=o.total_amount,
                    item_count=len(o.items),
                    status=self._effective_status(o),
                    expires_at=o.expires_at,
                    created_at=o.created_at,
                    updated_at=o.updated_at,
                )
            )

        pages = math.ceil(total / page_size) if total > 0 else 0
        return OfferListResponse(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # -----------------------------------------------------------------------
    # Response Mapper
    # -----------------------------------------------------------------------

    def _to_detail_response(self, offer: Offer) -> OfferDetailResponse:
        """Convert SQLAlchemy Offer instance to Pydantic OfferDetailResponse."""
        sender_summary = None
        if offer.sender:
            farmer_p = getattr(offer.sender, "farmer_profile", None)
            buyer_p = getattr(offer.sender, "buyer_profile", None)
            p = farmer_p or buyer_p
            name = getattr(p, "contact_person_name", None) or getattr(p, "farm_name", None) or "User"
            biz = getattr(p, "business_name", None) or getattr(p, "farm_name", None)
            city = getattr(p, "city", None)
            state = getattr(p, "state", None)
            sender_summary = UserSummary(
                id=offer.sender.id,
                role=offer.sender.role,
                name=name,
                business_name=biz,
                city=city,
                state=state,
            )

        recipient_summary = None
        if offer.recipient:
            farmer_p = getattr(offer.recipient, "farmer_profile", None)
            buyer_p = getattr(offer.recipient, "buyer_profile", None)
            p = farmer_p or buyer_p
            name = getattr(p, "contact_person_name", None) or getattr(p, "farm_name", None) or "User"
            biz = getattr(p, "business_name", None) or getattr(p, "farm_name", None)
            city = getattr(p, "city", None)
            state = getattr(p, "state", None)
            recipient_summary = UserSummary(
                id=offer.recipient.id,
                role=offer.recipient.role,
                name=name,
                business_name=biz,
                city=city,
                state=state,
            )

        items_resp = [
            OfferItemResponse(
                id=item.id,
                offer_id=item.offer_id,
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
            for item in offer.items
        ]

        order_id = offer.order.id if offer.order else None
        order_number = offer.order.order_number if offer.order else None

        return OfferDetailResponse(
            id=offer.id,
            offer_number=offer.offer_number,
            conversation_id=offer.conversation_id,
            sender_id=offer.sender_id,
            recipient_id=offer.recipient_id,
            parent_offer_id=offer.parent_offer_id,
            delivery_terms=offer.delivery_terms,
            proposed_delivery_date=offer.proposed_delivery_date,
            total_amount=offer.total_amount,
            status=self._effective_status(offer),
            expires_at=offer.expires_at,
            created_at=offer.created_at,
            updated_at=offer.updated_at,
            sender=sender_summary,
            recipient=recipient_summary,
            items=items_resp,
            order_id=order_id,
            order_number=order_number,
        )
