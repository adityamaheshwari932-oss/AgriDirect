"""SQLAlchemy ORM model for commercial buyer procurement requirements.

Implements Module 2 (Catalog, Listings, and Buyer Requirements) of AgriDirect:
- ``BuyerRequirement``: Procurement demands posted by verified commercial buyers (Table 2.4 / Store D6).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.listing import ProduceCategory
    from app.models.offer import OfferItem
    from app.models.order import OrderItem
    from app.models.requirement_approval import RequirementFulfillmentApproval
    from app.models.user import User

# Canonical requirement lifecycle statuses (schema-design.md Table 2.4 & SRS FR-REQ-05)
REQUIREMENT_STATUS_DRAFT = "draft"
REQUIREMENT_STATUS_ACTIVE = "active"
REQUIREMENT_STATUS_PARTIALLY_FULFILLED = "partially_fulfilled"
REQUIREMENT_STATUS_CLOSED = "closed"
REQUIREMENT_STATUS_EXPIRED = "expired"

VALID_REQUIREMENT_STATUSES = (
    REQUIREMENT_STATUS_DRAFT,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_EXPIRED,
)

# Canonical price condition types (schema-design.md Table 2.4 & SRS FR-REQ-04)
PRICE_CONDITION_EXACT = "exact"
PRICE_CONDITION_RANGE = "range"
PRICE_CONDITION_NEGOTIABLE = "negotiable"

VALID_PRICE_CONDITIONS = (
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_RANGE,
    PRICE_CONDITION_NEGOTIABLE,
)


class BuyerRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Procurement demand posted by a verified commercial buyer.

    Product names are user-entered free-form text preserving buyer specification flexibility.
    Category reference is optional taxonomy assistance for faceted matching and analytics.

    Enforces strict database-level check constraints for positive required quantity,
    valid remaining quantity bounds (0 <= remaining <= required), positive target price when specified,
    valid price conditions ('exact', 'range', 'negotiable'), and controlled lifecycle statuses.
    """

    __tablename__ = "buyer_requirements"

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    required_quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    remaining_quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    target_price_per_unit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True,
    )
    price_condition: Mapped[str] = mapped_column(
        String(32),
        default=PRICE_CONDITION_NEGOTIABLE,
        server_default=PRICE_CONDITION_NEGOTIABLE,
        nullable=False,
    )
    quality_grade: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    destination_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    destination_city: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    required_by_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=REQUIREMENT_STATUS_ACTIVE,
        server_default=REQUIREMENT_STATUS_ACTIVE,
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Bidirectional relationship with posting buyer
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="requirements",
    )

    # Bidirectional relationship with optional produce category
    category: Mapped[Optional["ProduceCategory"]] = relationship(
        "ProduceCategory",
        foreign_keys=[category_id],
        back_populates="requirements",
    )

    # 1:N Relationship with negotiation offer items
    offer_items: Mapped[List["OfferItem"]] = relationship(
        "OfferItem",
        foreign_keys="[OfferItem.buyer_requirement_id]",
        back_populates="buyer_requirement",
    )

    # 1:N Relationship with order items snapshot
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        foreign_keys="[OrderItem.buyer_requirement_id]",
        back_populates="buyer_requirement",
    )

    # 1:N Relationship with fulfillment approval records
    fulfillment_approvals: Mapped[List["RequirementFulfillmentApproval"]] = relationship(
        "RequirementFulfillmentApproval",
        foreign_keys="[RequirementFulfillmentApproval.requirement_id]",
        back_populates="requirement",
    )

    __table_args__ = (
        CheckConstraint(
            "required_quantity > 0",
            name="chk_requirements_required_quantity",
        ),
        CheckConstraint(
            "remaining_quantity >= 0 AND remaining_quantity <= required_quantity",
            name="chk_requirements_remaining_quantity",
        ),
        CheckConstraint(
            "target_price_per_unit IS NULL OR target_price_per_unit > 0",
            name="chk_requirements_target_price",
        ),
        CheckConstraint(
            "price_condition IN ('exact', 'range', 'negotiable')",
            name="chk_requirements_price_condition",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'partially_fulfilled', 'closed', 'expired')",
            name="chk_requirements_status",
        ),
        Index("idx_requirements_buyer", "buyer_id"),
        Index("idx_requirements_category_status", "category_id", "status", "is_deleted"),
        Index("idx_requirements_deadline", "required_by_date"),
    )
