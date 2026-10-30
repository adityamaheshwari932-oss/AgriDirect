"""SQLAlchemy ORM models for orders, line-item snapshots, amendments, and inventory adjustments.

Implements Module 5 (Orders, Line Items, Amendments, and Inventory Control) of AgriDirect:
- ``Order``: Formal transactions created upon offer acceptance with integrated delivery coordination (Table 5.1 / Store D10).
- ``OrderItem``: Immutable snapshot line items agreed upon at offer acceptance (Table 5.2 / Snapshot Line Item).
- ``OrderAmendment``: Mutually agreed post-finalization order changes (Table 5.3 / Store D11).
- ``InventoryAdjustment``: Append-only inventory change audit ledger (Table 5.4 / Store D12).
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.listing import ProduceListing
    from app.models.offer import Offer
    from app.models.payment import PaymentRecord
    from app.models.requirement import BuyerRequirement
    from app.models.requirement_approval import RequirementFulfillmentApproval
    from app.models.review import RatingReview
    from app.models.user import User

# Canonical order lifecycle statuses (schema-design.md Table 5.1 & SRS FR-ORD-04)
ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_CONFIRMED = "confirmed"
ORDER_STATUS_PAYMENT_PENDING = "payment_pending"
ORDER_STATUS_PAYMENT_RECORDED = "payment_recorded"
ORDER_STATUS_DELIVERY_ARRANGED = "delivery_arranged"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUS_DISPUTED = "disputed"

VALID_ORDER_STATUSES = (
    ORDER_STATUS_PENDING,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_PAYMENT_PENDING,
    ORDER_STATUS_PAYMENT_RECORDED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_DISPUTED,
)

# Canonical delivery statuses embedded in orders (Decision 3 & schema-design.md Table 5.1)
DELIVERY_STATUS_NOT_ARRANGED = "not_arranged"
DELIVERY_STATUS_ARRANGED = "arranged"
DELIVERY_STATUS_COMPLETION_MARKED = "completion_marked"
DELIVERY_STATUS_COMPLETED = "completed"

VALID_DELIVERY_STATUSES = (
    DELIVERY_STATUS_NOT_ARRANGED,
    DELIVERY_STATUS_ARRANGED,
    DELIVERY_STATUS_COMPLETION_MARKED,
    DELIVERY_STATUS_COMPLETED,
)

# Canonical order item statuses (schema-design.md Table 5.2)
ORDER_ITEM_STATUS_CONFIRMED = "confirmed"
ORDER_ITEM_STATUS_FULFILLED = "fulfilled"
ORDER_ITEM_STATUS_CANCELLED = "cancelled"
ORDER_ITEM_STATUS_DISPUTED = "disputed"

VALID_ORDER_ITEM_STATUSES = (
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_ITEM_STATUS_FULFILLED,
    ORDER_ITEM_STATUS_CANCELLED,
    ORDER_ITEM_STATUS_DISPUTED,
)

# Canonical amendment types (schema-design.md Table 5.3 & SRS FR-ORD-09)
AMENDMENT_TYPE_QUANTITY = "quantity"
AMENDMENT_TYPE_PRICE = "price"
AMENDMENT_TYPE_DELIVERY_DATE = "delivery_date"
AMENDMENT_TYPE_TERMS = "terms"

VALID_AMENDMENT_TYPES = (
    AMENDMENT_TYPE_QUANTITY,
    AMENDMENT_TYPE_PRICE,
    AMENDMENT_TYPE_DELIVERY_DATE,
    AMENDMENT_TYPE_TERMS,
)

# Canonical amendment statuses (schema-design.md Table 5.3)
AMENDMENT_STATUS_PROPOSED = "proposed"
AMENDMENT_STATUS_EFFECTIVE = "effective"
AMENDMENT_STATUS_REJECTED = "rejected"

VALID_AMENDMENT_STATUSES = (
    AMENDMENT_STATUS_PROPOSED,
    AMENDMENT_STATUS_EFFECTIVE,
    AMENDMENT_STATUS_REJECTED,
)

# Canonical inventory adjustment change types (schema-design.md Table 5.4 & SRS FR-INV-08)
CHANGE_TYPE_ORDER_FULFILLMENT = "order_fulfillment"
CHANGE_TYPE_ORDER_CANCELLATION_RELEASE = "order_cancellation_release"
CHANGE_TYPE_AMENDMENT_DELTA = "amendment_delta"
CHANGE_TYPE_MANUAL_RESTOCK = "manual_restock"
CHANGE_TYPE_MANUAL_SHRINKAGE = "manual_shrinkage"

VALID_CHANGE_TYPES = (
    CHANGE_TYPE_ORDER_FULFILLMENT,
    CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
    CHANGE_TYPE_AMENDMENT_DELTA,
    CHANGE_TYPE_MANUAL_RESTOCK,
    CHANGE_TYPE_MANUAL_SHRINKAGE,
)


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Formal trade transaction record created automatically upon offer acceptance.

    Integrates bilateral delivery coordination directly without separate join tables (Decision 3).
    Guarantees idempotency via unique source_offer_id constraint.
    """

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )
    source_offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=ORDER_STATUS_PENDING,
        server_default=ORDER_STATUS_PENDING,
        nullable=False,
    )
    delivery_method: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    delivery_destination_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    delivery_arranged_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    delivery_status: Mapped[str] = mapped_column(
        String(32),
        default=DELIVERY_STATUS_NOT_ARRANGED,
        server_default=DELIVERY_STATUS_NOT_ARRANGED,
        nullable=False,
    )
    delivery_completion_marked_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    delivery_completion_marked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivery_acknowledged_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    delivery_acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivery_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    cancelled_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    source_offer: Mapped["Offer"] = relationship(
        "Offer",
        foreign_keys=[source_offer_id],
        back_populates="order",
    )
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="orders_as_buyer",
    )
    farmer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[farmer_id],
        back_populates="orders_as_farmer",
    )
    delivery_completion_marked_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[delivery_completion_marked_by_user_id],
    )
    delivery_acknowledged_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[delivery_acknowledged_by_user_id],
    )
    cancelled_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[cancelled_by_user_id],
    )
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        foreign_keys="[OrderItem.order_id]",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    amendments: Mapped[List["OrderAmendment"]] = relationship(
        "OrderAmendment",
        foreign_keys="[OrderAmendment.order_id]",
        back_populates="order",
    )
    inventory_adjustments: Mapped[List["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment",
        foreign_keys="[InventoryAdjustment.order_id]",
        back_populates="order",
    )
    payment_records: Mapped[List["PaymentRecord"]] = relationship(
        "PaymentRecord",
        foreign_keys="[PaymentRecord.order_id]",
        back_populates="order",
    )
    ratings_reviews: Mapped[List["RatingReview"]] = relationship(
        "RatingReview",
        foreign_keys="[RatingReview.order_id]",
        back_populates="order",
    )
    fulfillment_approvals: Mapped[List["RequirementFulfillmentApproval"]] = relationship(
        "RequirementFulfillmentApproval",
        foreign_keys="[RequirementFulfillmentApproval.order_id]",
        back_populates="order",
    )

    __table_args__ = (
        CheckConstraint(
            "buyer_id <> farmer_id",
            name="chk_orders_counterparts",
        ),
        CheckConstraint(
            "total_amount > 0",
            name="chk_orders_total_amount",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'payment_pending', 'payment_recorded', 'delivery_arranged', 'completed', 'cancelled', 'disputed')",
            name="chk_orders_status",
        ),
        CheckConstraint(
            "delivery_status IN ('not_arranged', 'arranged', 'completion_marked', 'completed')",
            name="chk_orders_delivery_status",
        ),
        Index("idx_orders_order_number", "order_number", unique=True),
        Index("idx_orders_source_offer", "source_offer_id", unique=True),
        Index("idx_orders_buyer", "buyer_id"),
        Index("idx_orders_farmer", "farmer_id"),
        Index("idx_orders_status", "status"),
    )


class OrderItem(Base, UUIDPrimaryKeyMixin):
    """Immutable snapshot line item agreed upon at the moment of offer acceptance."""

    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
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
        default=ORDER_ITEM_STATUS_CONFIRMED,
        server_default=ORDER_ITEM_STATUS_CONFIRMED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[order_id],
        back_populates="items",
    )
    listing: Mapped[Optional["ProduceListing"]] = relationship(
        "ProduceListing",
        foreign_keys=[listing_id],
    )
    buyer_requirement: Mapped[Optional["BuyerRequirement"]] = relationship(
        "BuyerRequirement",
        foreign_keys=[buyer_requirement_id],
        back_populates="order_items",
    )
    fulfillment_approval: Mapped[Optional["RequirementFulfillmentApproval"]] = relationship(
        "RequirementFulfillmentApproval",
        foreign_keys="[RequirementFulfillmentApproval.order_item_id]",
        back_populates="order_item",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "id",
            "order_id",
            "buyer_requirement_id",
            name="uq_order_items_identity_requirement",
        ),
        CheckConstraint(
            "quantity > 0",
            name="chk_order_items_quantity",
        ),
        CheckConstraint(
            "unit_price > 0",
            name="chk_order_items_unit_price",
        ),
        CheckConstraint(
            "subtotal > 0",
            name="chk_order_items_subtotal",
        ),
        CheckConstraint(
            "status IN ('confirmed', 'fulfilled', 'cancelled', 'disputed')",
            name="chk_order_items_status",
        ),
        Index("idx_order_items_order", "order_id"),
        Index("idx_order_items_listing", "listing_id"),
        Index("idx_order_items_requirement", "buyer_requirement_id"),
    )


class OrderAmendment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mutually agreed post-finalization order changes."""

    __tablename__ = "order_amendments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amendment_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    old_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    new_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    justification: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    buyer_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    farmer_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=AMENDMENT_STATUS_PROPOSED,
        server_default=AMENDMENT_STATUS_PROPOSED,
        nullable=False,
    )
    effective_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[order_id],
        back_populates="amendments",
    )
    proposed_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[proposed_by_user_id],
    )
    inventory_adjustments: Mapped[List["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment",
        foreign_keys="[InventoryAdjustment.amendment_id]",
        back_populates="amendment",
    )

    __table_args__ = (
        CheckConstraint(
            "amendment_type IN ('quantity', 'price', 'delivery_date', 'terms')",
            name="chk_amendments_type",
        ),
        CheckConstraint(
            "status IN ('proposed', 'effective', 'rejected')",
            name="chk_amendments_status",
        ),
        Index("idx_amendments_order", "order_id"),
    )


class InventoryAdjustment(Base, UUIDPrimaryKeyMixin):
    """Append-only audit ledger governing all inventory changes."""

    __tablename__ = "inventory_adjustments"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce_listings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    amendment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_amendments.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    quantity_delta: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    listing: Mapped["ProduceListing"] = relationship(
        "ProduceListing",
        foreign_keys=[listing_id],
        back_populates="inventory_adjustments",
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id],
        back_populates="inventory_adjustments",
    )
    amendment: Mapped[Optional["OrderAmendment"]] = relationship(
        "OrderAmendment",
        foreign_keys=[amendment_id],
        back_populates="inventory_adjustments",
    )
    recorded_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recorded_by_user_id],
    )

    __table_args__ = (
        CheckConstraint(
            "change_type IN ('order_fulfillment', 'order_cancellation_release', 'amendment_delta', 'manual_restock', 'manual_shrinkage')",
            name="chk_inv_adjustments_change_type",
        ),
        Index("idx_inv_adjustments_listing", "listing_id", "change_type"),
        Index("idx_inv_adjustments_order", "order_id"),
    )
