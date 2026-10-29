"""Pydantic v2 schemas for produce categories, listings, and listing images.

Enforces strict validation, prohibits server-controlled attributes via extra='forbid',
and isolates public marketplace data from private administrative or internal details.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.listing import (
    CANONICAL_UNITS,
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_DRAFT,
    VALID_LISTING_STATUSES,
)


class CategoryResponse(BaseModel):
    """Hierarchical produce taxonomy category response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    slug: str
    is_active: bool


class ListingImageResponse(BaseModel):
    """Produce listing photographic asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    image_uri: str
    is_primary: bool
    display_order: int
    created_at: datetime


class FarmerSummary(BaseModel):
    """Sanitized public summary of the listing farmer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    farm_name: str
    city: str
    state: str


class ListingCreate(BaseModel):
    """Payload for creating a produce listing by a verified farmer.

    Server-controlled fields (id, farmer_id, available_quantity, is_deleted,
    deleted_at, created_at, updated_at) are strictly forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Free-form agricultural produce name (e.g. Sharbati Wheat, Alphonso Mango)",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Listing headline narrative",
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of produce quality, storage, and harvest",
    )
    category_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional produce category taxonomy reference",
    )
    initial_quantity: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=3,
        description="Initial available supply quantity (> 0)",
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=16,
        description="Measurement unit (e.g. kg, quintal, metric_ton, bag)",
    )
    price_per_unit: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Price per unit in currency (> 0)",
    )
    quality_grade: Optional[str] = Field(
        None,
        max_length=32,
        description="Produce grade classification (e.g. Grade A, Organic)",
    )
    location_state: Optional[str] = Field(
        None,
        max_length=64,
        description="Sourcing state (defaults to farm profile state if omitted)",
    )
    location_city: Optional[str] = Field(
        None,
        max_length=64,
        description="Sourcing district or city (defaults to farm profile city if omitted)",
    )
    harvest_date: Optional[date] = Field(
        None,
        description="Date when crop was harvested",
    )
    available_from: Optional[date] = Field(
        None,
        description="Dispatch readiness date (defaults to today if omitted)",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Listing expiration timestamp (defaults to 30 days after available_from if omitted)",
    )
    status: Optional[str] = Field(
        STATUS_ACTIVE,
        description="Initial listing status ('active' or 'draft')",
    )

    @field_validator("product_name", "title", "unit")
    @classmethod
    def validate_non_blank_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return stripped

    @field_validator("location_state", "location_city", "quality_grade")
    @classmethod
    def validate_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, value: Optional[str]) -> str:
        if value is None:
            return STATUS_ACTIVE
        if value not in (STATUS_ACTIVE, STATUS_DRAFT):
            raise ValueError("Initial listing status must be 'active' or 'draft'")
        return value


class ListingUpdate(BaseModel):
    """Payload for partial update of a produce listing by the owner.

    Server-controlled fields (id, farmer_id, created_at, updated_at,
    is_deleted, deleted_at) are strictly forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    product_name: Optional[str] = Field(None, min_length=1, max_length=128)
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None)
    category_id: Optional[uuid.UUID] = Field(None)
    initial_quantity: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=3)
    available_quantity: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    unit: Optional[str] = Field(None, min_length=1, max_length=16)
    price_per_unit: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    quality_grade: Optional[str] = Field(None, max_length=32)
    location_state: Optional[str] = Field(None, max_length=64)
    location_city: Optional[str] = Field(None, max_length=64)
    harvest_date: Optional[date] = Field(None)
    available_from: Optional[date] = Field(None)
    expires_at: Optional[datetime] = Field(None)
    status: Optional[str] = Field(None)

    @field_validator("product_name", "title", "unit", "location_state", "location_city", "quality_grade")
    @classmethod
    def validate_non_blank_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value

    @field_validator("status")
    @classmethod
    def validate_status_value(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in VALID_LISTING_STATUSES:
            raise ValueError(
                f"Invalid status '{value}'. Must be one of: {', '.join(VALID_LISTING_STATUSES)}"
            )
        return value


class ListingStatusUpdate(BaseModel):
    """Payload specifically for transitioning listing status."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        ...,
        description="Target listing lifecycle status ('active', 'draft', 'closed')",
    )

    @field_validator("status")
    @classmethod
    def validate_target_status(cls, value: str) -> str:
        if value not in (STATUS_ACTIVE, STATUS_DRAFT, STATUS_CLOSED):
            raise ValueError("Target status must be 'active', 'draft', or 'closed'")
        return value


class ProduceListingDetailResponse(BaseModel):
    """Full detail view of a produce listing, including images and category info."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    category: Optional[CategoryResponse] = None
    product_name: str
    title: str
    description: Optional[str] = None
    initial_quantity: Decimal
    available_quantity: Decimal
    unit: str
    price_per_unit: Decimal
    quality_grade: Optional[str] = None
    location_state: str
    location_city: str
    harvest_date: Optional[date] = None
    available_from: date
    expires_at: datetime
    status: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    images: List[ListingImageResponse] = []
    farmer: Optional[FarmerSummary] = None


class ProduceListingPublicSummary(BaseModel):
    """Public marketplace card view for a produce listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    product_name: str
    title: str
    description: Optional[str] = None
    available_quantity: Decimal
    unit: str
    price_per_unit: Decimal
    quality_grade: Optional[str] = None
    location_state: str
    location_city: str
    harvest_date: Optional[date] = None
    available_from: date
    expires_at: datetime
    status: str
    created_at: datetime
    primary_image_uri: Optional[str] = None
    farmer: Optional[FarmerSummary] = None


class ProduceListingPublicListResponse(BaseModel):
    """Paginated catalog response for public active produce listings."""

    items: List[ProduceListingPublicSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class FarmerListingListResponse(BaseModel):
    """Paginated response for farmer's own produce listings."""

    items: List[ProduceListingDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

