"""SQLAlchemy repository for Structured Offers and Negotiation (Module 3).

Follows the synchronous session convention per ADR-002.
Does not commit transactions independently; the service layer owns transaction boundaries.
Implements row-level locking with deterministic ascending ID sorting to minimize deadlocks.
"""

import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.chat import Conversation, ConversationParticipant
from app.models.listing import ProduceListing
from app.models.notification import NOTIFICATION_REF_ORDER, Notification
from app.models.offer import (
    OFFER_ITEM_STATUS_PROPOSED,
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_COUNTERED,
    OFFER_STATUS_PENDING,
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
from app.models.requirement import BuyerRequirement
from app.models.user import User


class OfferRepository:
    """Synchronous repository handling data access for offers, items, and atomic orders."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_offer_number(self) -> str:
        """Generate a collision-free human-readable offer code (e.g. OFF-20261030-A1B2)."""
        today_str = date.today().strftime("%Y%m%d")
        for _ in range(10):
            token = secrets.token_hex(2).upper()
            candidate = f"OFF-{today_str}-{token}"
            exists = self.db.scalars(
                select(Offer.id).where(Offer.offer_number == candidate)
            ).first()
            if not exists:
                return candidate
        # Fallback to UUID suffix
        return f"OFF-{today_str}-{uuid.uuid4().hex[:6].upper()}"

    def generate_order_number(self) -> str:
        """Generate a collision-free human-readable order code (e.g. ORD-20261030-A1B2)."""
        today_str = date.today().strftime("%Y%m%d")
        for _ in range(10):
            token = secrets.token_hex(2).upper()
            candidate = f"ORD-{today_str}-{token}"
            exists = self.db.scalars(
                select(Order.id).where(Order.order_number == candidate)
            ).first()
            if not exists:
                return candidate
        return f"ORD-{today_str}-{uuid.uuid4().hex[:6].upper()}"

    def get_by_id(
        self,
        offer_id: uuid.UUID,
        for_update: bool = False,
    ) -> Optional[Offer]:
        """Fetch an offer by primary key with eager-loaded items and participants."""
        stmt = (
            select(Offer)
            .where(Offer.id == offer_id)
            .options(
                selectinload(Offer.items),
                joinedload(Offer.sender),
                joinedload(Offer.recipient),
                joinedload(Offer.conversation),
                joinedload(Offer.order),
            )
        )
        if for_update:
            stmt = stmt.with_for_update(of=Offer).execution_options(populate_existing=True)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_offer_number(self, offer_number: str) -> Optional[Offer]:
        """Fetch an offer by its unique offer number."""
        stmt = (
            select(Offer)
            .where(Offer.offer_number == offer_number)
            .options(
                selectinload(Offer.items),
                joinedload(Offer.sender),
                joinedload(Offer.recipient),
            )
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def get_or_create_conversation(
        self,
        farmer_id: uuid.UUID,
        buyer_id: uuid.UUID,
        context_type: Optional[str] = None,
        context_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        """Retrieve existing reusable conversation between farmer and buyer, or create one atomically."""
        stmt = select(Conversation).where(
            Conversation.farmer_id == farmer_id,
            Conversation.buyer_id == buyer_id,
        )
        conv = self.db.scalars(stmt).one_or_none()
        if conv:
            return conv

        # Create new unique conversation thread
        conv = Conversation(
            farmer_id=farmer_id,
            buyer_id=buyer_id,
            initial_context_type=context_type or "general",
            initial_context_id=context_id,
        )
        self.db.add(conv)
        self.db.flush()

        # Add participants
        p_farmer = ConversationParticipant(
            conversation_id=conv.id,
            user_id=farmer_id,
        )
        p_buyer = ConversationParticipant(
            conversation_id=conv.id,
            user_id=buyer_id,
        )
        self.db.add_all([p_farmer, p_buyer])
        self.db.flush()
        return conv

    def list_offers(
        self,
        user_id: uuid.UUID,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        conversation_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Offer], int]:
        """Retrieve paginated list of offers involving the specified user."""
        base_query = select(Offer)

        # Scoped access: user must be sender or recipient
        if role_filter == "sent":
            base_query = base_query.where(Offer.sender_id == user_id)
        elif role_filter == "received":
            base_query = base_query.where(Offer.recipient_id == user_id)
        else:
            base_query = base_query.where(
                or_(Offer.sender_id == user_id, Offer.recipient_id == user_id)
            )

        if status_filter:
            base_query = base_query.where(Offer.status == status_filter)
        if conversation_id:
            base_query = base_query.where(Offer.conversation_id == conversation_id)

        # Total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Paginated results ordered by creation timestamp descending
        fetch_stmt = (
            base_query.options(
                selectinload(Offer.items),
                joinedload(Offer.sender),
                joinedload(Offer.recipient),
            )
            .order_by(Offer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        offers = list(self.db.scalars(fetch_stmt).unique().all())
        return offers, total

    def create_offer(
        self,
        header_data: dict,
        items_data: List[dict],
    ) -> Offer:
        """Create an offer record and its line items inside the active transaction."""
        offer = Offer(**header_data)
        self.db.add(offer)
        self.db.flush()

        for item_data in items_data:
            item = OfferItem(
                offer_id=offer.id,
                status=OFFER_ITEM_STATUS_PROPOSED,
                **item_data,
            )
            self.db.add(item)

        self.db.flush()
        # Refresh to populate relationships
        return self.get_by_id(offer.id)  # type: ignore

    def get_negotiation_history(self, current_offer: Offer) -> List[Offer]:
        """Traverse counter-offer lineage tree to construct the chronological negotiation chain."""
        # Step 1: Trace up to root offer
        root = current_offer
        visited_up = {root.id}
        while root.parent_offer_id:
            parent = self.get_by_id(root.parent_offer_id)
            if not parent or parent.id in visited_up:
                break
            visited_up.add(parent.id)
            root = parent

        # Step 2: Query all offers in this conversation that share the lineage
        # All counter-offers share the same conversation_id and have parent_offer links
        stmt = (
            select(Offer)
            .where(Offer.conversation_id == current_offer.conversation_id)
            .options(
                selectinload(Offer.items),
                joinedload(Offer.sender),
                joinedload(Offer.recipient),
                joinedload(Offer.order),
            )
            .order_by(Offer.created_at.asc())
        )
        all_conv_offers = list(self.db.scalars(stmt).unique().all())

        # Filter offers that belong to this specific counter-offer chain
        # A chain starts at root.id, and each subsequent offer has parent_offer_id == previous
        chain = [root]
        chain_ids = {root.id}
        changed = True
        while changed:
            changed = False
            for cand in all_conv_offers:
                if cand.parent_offer_id in chain_ids and cand.id not in chain_ids:
                    chain.append(cand)
                    chain_ids.add(cand.id)
                    changed = True

        # Sort chronologically by created_at
        chain.sort(key=lambda o: o.created_at)
        return chain

    def lock_listings(self, listing_ids: List[uuid.UUID]) -> Dict[uuid.UUID, ProduceListing]:
        """Acquire row-level locks on produce listings in ascending UUID order to minimize deadlocks."""
        if not listing_ids:
            return {}
        sorted_ids = sorted(list(set(listing_ids)))
        stmt = (
            select(ProduceListing)
            .where(ProduceListing.id.in_(sorted_ids))
            .order_by(ProduceListing.id.asc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        rows = list(self.db.scalars(stmt).all())
        return {r.id: r for r in rows}

    def lock_requirements(self, requirement_ids: List[uuid.UUID]) -> Dict[uuid.UUID, BuyerRequirement]:
        """Acquire row-level locks on buyer requirements in ascending UUID order to minimize deadlocks."""
        if not requirement_ids:
            return {}
        sorted_ids = sorted(list(set(requirement_ids)))
        stmt = (
            select(BuyerRequirement)
            .where(BuyerRequirement.id.in_(sorted_ids))
            .order_by(BuyerRequirement.id.asc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        rows = list(self.db.scalars(stmt).all())
        return {r.id: r for r in rows}

    def create_order_from_accepted_offer(
        self,
        offer: Offer,
        current_user: User,
        order_number: str,
        delivery_destination_address: Optional[str] = None,
    ) -> Order:
        """Instantiate an Order and snapshot line items atomically upon offer acceptance."""
        order = Order(
            order_number=order_number,
            source_offer_id=offer.id,
            buyer_id=offer.conversation.buyer_id,
            farmer_id=offer.conversation.farmer_id,
            total_amount=offer.total_amount,
            status=ORDER_STATUS_PENDING,
            delivery_status=DELIVERY_STATUS_NOT_ARRANGED,
            delivery_destination_address=delivery_destination_address,
            delivery_arranged_date=offer.proposed_delivery_date,
            delivery_notes=offer.delivery_terms,
        )
        self.db.add(order)
        self.db.flush()

        # Snapshot items
        item_map: Dict[uuid.UUID, OrderItem] = {}
        for item in offer.items:
            order_item = OrderItem(
                order_id=order.id,
                listing_id=item.listing_id,
                buyer_requirement_id=item.buyer_requirement_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                quality_grade=item.quality_grade,
                status=ORDER_ITEM_STATUS_CONFIRMED,
            )
            self.db.add(order_item)
            item_map[item.id] = order_item

        self.db.flush()
        order._item_map = item_map
        return order

