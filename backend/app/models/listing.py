"""SQLAlchemy ORM models for produce catalog, farmer listings, and media assets.

Implements Module 2 (Catalog, Listings, and Buyer Requirements) of AgriDirect:
- ``ProduceCategory``: Optional hierarchical produce taxonomy (Table 2.1).
- ``ProduceListing``: Farmer supply ledger entries with strict inventory tracking (Table 2.2 / Store D5).
- ``ListingImage``: Photographic evidence and catalog gallery images (Table 2.3 / Child of D5).
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
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.offer import OfferItem
    from app.models.order import InventoryAdjustment
    from app.models.requirement import BuyerRequirement
    from app.models.user import User

# Canonical listing lifecycle statuses (schema-design.md Table 2.2 & SRS FR-LST-05)
STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_PARTIALLY_FULFILLED = "partially_fulfilled"
STATUS_CLOSED = "closed"
STATUS_EXPIRED = "expired"

VALID_LISTING_STATUSES = (
    STATUS_DRAFT,
    STATUS_ACTIVE,
    STATUS_PARTIALLY_FULFILLED,
    STATUS_CLOSED,
    STATUS_EXPIRED,
)

# Canonical agricultural produce units (extensible; no DB-level check constraint)
UNIT_KG = "kg"
UNIT_QUINTAL = "quintal"
UNIT_METRIC_TON = "metric_ton"
UNIT_BAG = "bag"

CANONICAL_UNITS = (
    UNIT_KG,
    UNIT_QUINTAL,
    UNIT_METRIC_TON,
    UNIT_BAG,
)


class ProduceCategory(Base, UUIDPrimaryKeyMixin):
    """Standardized hierarchical taxonomy to facilitate marketplace faceted search and analytics.

    Self-referencing tree structure where a subcategory points to an optional parent category
    (e.g., Cereals & Grains -> Wheat -> Sharbati Wheat).
    """

    __tablename__ = "produce_categories"

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Self-referencing tree relationship
    parent: Mapped[Optional["ProduceCategory"]] = relationship(
        "ProduceCategory",
        remote_side="ProduceCategory.id",
        foreign_keys=[parent_id],
        back_populates="subcategories",
    )
    subcategories: Mapped[List["ProduceCategory"]] = relationship(
        "ProduceCategory",
        foreign_keys=[parent_id],
        back_populates="parent",
        order_by="ProduceCategory.name",
    )

    # 1:N Relationship with produce listings
    listings: Mapped[List["ProduceListing"]] = relationship(
        "ProduceListing",
        foreign_keys="[ProduceListing.category_id]",
        back_populates="category",
        order_by="ProduceListing.created_at.desc()",
    )
    # 1:N Relationship with buyer procurement requirements
    requirements: Mapped[List["BuyerRequirement"]] = relationship(
        "BuyerRequirement",
        foreign_keys="[BuyerRequirement.category_id]",
        back_populates="category",
        order_by="BuyerRequirement.created_at.desc()",
    )

    __table_args__ = (
        Index("idx_categories_slug", "slug", unique=True),
        Index("idx_categories_parent", "parent_id"),
    )


class ProduceListing(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Farmer supply listing entry.

    Produce names are user-entered free-form text preserving farmer autonomy (Decision #2).
    Category reference is optional taxonomy assistance for faceted search and analytics.

    Enforces strict database-level checks for positive initial quantity, valid available quantity
    bounds (0 <= available <= initial), positive price per unit, and controlled lifecycle statuses.
    """

    __tablename__ = "produce_listings"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
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
    initial_quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    available_quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    quality_grade: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    location_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    location_city: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    harvest_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    available_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=STATUS_ACTIVE,
        server_default=STATUS_ACTIVE,
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

    # Bidirectional relationship with the farmer owner
    farmer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[farmer_id],
        back_populates="listings",
    )

    # Bidirectional relationship with optional produce category
    category: Mapped[Optional["ProduceCategory"]] = relationship(
        "ProduceCategory",
        foreign_keys=[category_id],
        back_populates="listings",
    )

    # 1:N Relationship with gallery images
    images: Mapped[List["ListingImage"]] = relationship(
        "ListingImage",
        foreign_keys="[ListingImage.listing_id]",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingImage.display_order",
    )
    # 1:N Relationship with negotiation offer items
    offer_items: Mapped[List["OfferItem"]] = relationship(
        "OfferItem",
        foreign_keys="[OfferItem.listing_id]",
        back_populates="listing",
    )
    # 1:N Relationship with inventory audit ledger
    inventory_adjustments: Mapped[List["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment",
        foreign_keys="[InventoryAdjustment.listing_id]",
        back_populates="listing",
    )

    __table_args__ = (
        CheckConstraint(
            "initial_quantity > 0",
            name="chk_listings_initial_quantity",
        ),
        CheckConstraint(
            "available_quantity >= 0 AND available_quantity <= initial_quantity",
            name="chk_listings_available_quantity",
        ),
        CheckConstraint(
            "price_per_unit > 0",
            name="chk_listings_price",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'partially_fulfilled', 'closed', 'expired')",
            name="chk_listings_status",
        ),
        Index("idx_listings_farmer_id", "farmer_id"),
        Index("idx_listings_category_status", "category_id", "status", "is_deleted"),
        Index("idx_listings_product_name", "product_name"),
        Index("idx_listings_location", "location_state", "location_city"),
        Index("idx_listings_price", "price_per_unit"),
        Index("idx_listings_created", text("created_at DESC")),
    )


class ListingImage(Base, UUIDPrimaryKeyMixin):
    """Photographs and digital assets attached to produce listings.

    Supports catalog thumbnails via ``is_primary`` and ordered presentation via ``display_order``.
    Cascades delete when parent listing is removed.
    """

    __tablename__ = "listing_images"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce_listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Bidirectional relationship back to parent listing
    listing: Mapped["ProduceListing"] = relationship(
        "ProduceListing",
        foreign_keys=[listing_id],
        back_populates="images",
    )

    __table_args__ = (
        Index("idx_listing_images_listing", "listing_id"),
    )
