"""SQLAlchemy ORM models for structured proposals, counter-offer lineage, and negotiation line items.

Implements Module 4 (Structured Offers and Negotiation) of AgriDirect:
- ``Offer``: Negotiation proposal headers supporting counter-offer chains (Table 4.1 / Store D9).
- ``OfferItem``: Item-level multi-product negotiation proposals (Table 4.2 / Child of D9).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat import Conversation
    from app.models.listing import ProduceListing
    from app.models.order import Order
    from app.models.requirement import BuyerRequirement
    from app.models.user import User

# Canonical offer lifecycle statuses (schema-design.md Table 4.1 & SRS FR-OFF-03)
OFFER_STATUS_PENDING = "pending"
OFFER_STATUS_COUNTERED = "countered"
OFFER_STATUS_ACCEPTED = "accepted"
OFFER_STATUS_REJECTED = "rejected"
OFFER_STATUS_WITHDRAWN = "withdrawn"
OFFER_STATUS_EXPIRED = "expired"

VALID_OFFER_STATUSES = (
    OFFER_STATUS_PENDING,
    OFFER_STATUS_COUNTERED,
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_REJECTED,
    OFFER_STATUS_WITHDRAWN,
    OFFER_STATUS_EXPIRED,
)

# Canonical offer item statuses (schema-design.md Table 4.2 & SRS FR-OFF-02)
OFFER_ITEM_STATUS_PROPOSED = "proposed"
OFFER_ITEM_STATUS_AGREED = "agreed"
OFFER_ITEM_STATUS_REJECTED = "rejected"
OFFER_ITEM_STATUS_MODIFIED = "modified"

VALID_OFFER_ITEM_STATUSES = (
    OFFER_ITEM_STATUS_PROPOSED,
    OFFER_ITEM_STATUS_AGREED,
    OFFER_ITEM_STATUS_REJECTED,
    OFFER_ITEM_STATUS_MODIFIED,
)


class Offer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Negotiation proposal headers inside chat threads supporting counter-offer chains."""

    __tablename__ = "offers"

    offer_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_offer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    delivery_terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    proposed_delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=OFFER_STATUS_PENDING,
        server_default=OFFER_STATUS_PENDING,
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        back_populates="offers",
    )
    sender: Mapped["User"] = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_offers",
    )
    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_id],
        back_populates="received_offers",
    )
    parent_offer: Mapped[Optional["Offer"]] = relationship(
        "Offer",
        remote_side="Offer.id",
        foreign_keys=[parent_offer_id],
        back_populates="counter_offers",
    )
    counter_offers: Mapped[List["Offer"]] = relationship(
        "Offer",
        foreign_keys=[parent_offer_id],
        back_populates="parent_offer",
        order_by="Offer.created_at.asc()",
    )
    items: Mapped[List["OfferItem"]] = relationship(
        "OfferItem",
        foreign_keys="[OfferItem.offer_id]",
        back_populates="offer",
        cascade="all, delete-orphan",
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys="[Order.source_offer_id]",
        back_populates="source_offer",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint(
            "sender_id <> recipient_id",
            name="chk_offers_counterparts",
        ),
        CheckConstraint(
            "total_amount > 0",
            name="chk_offers_total_amount",
        ),
        CheckConstraint(
            "status IN ('pending', 'countered', 'accepted', 'rejected', 'withdrawn', 'expired')",
            name="chk_offers_status",
        ),
        Index("idx_offers_conversation", "conversation_id"),
        Index("idx_offers_sender", "sender_id"),
        Index("idx_offers_recipient", "recipient_id"),
        Index("idx_offers_parent", "parent_offer_id"),
        Index("idx_offers_status", "status"),
    )


class OfferItem(Base, UUIDPrimaryKeyMixin):
    """Structured line-item proposals allowing multi-product negotiation."""

    __tablename__ = "offer_items"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    buyer_requirement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buyer_requirements.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    quality_grade: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=OFFER_ITEM_STATUS_PROPOSED,
        server_default=OFFER_ITEM_STATUS_PROPOSED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    offer: Mapped["Offer"] = relationship(
        "Offer",
        foreign_keys=[offer_id],
        back_populates="items",
    )
    listing: Mapped[Optional["ProduceListing"]] = relationship(
        "ProduceListing",
        foreign_keys=[listing_id],
        back_populates="offer_items",
    )
    buyer_requirement: Mapped[Optional["BuyerRequirement"]] = relationship(
        "BuyerRequirement",
        foreign_keys=[buyer_requirement_id],
        back_populates="offer_items",
    )

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="chk_offer_items_quantity",
        ),
        CheckConstraint(
            "unit_price > 0",
            name="chk_offer_items_unit_price",
        ),
        CheckConstraint(
            "subtotal > 0",
            name="chk_offer_items_subtotal",
        ),
        CheckConstraint(
            "status IN ('proposed', 'agreed', 'rejected', 'modified')",
            name="chk_offer_items_status",
        ),
        Index("idx_offer_items_offer", "offer_id"),
        Index("idx_offer_items_listing", "listing_id"),
        Index("idx_offer_items_requirement", "buyer_requirement_id"),
    )
