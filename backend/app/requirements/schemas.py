"""Pydantic v2 schemas for buyer procurement requirements.

Enforces strict input validation with extra='forbid', string stripping, numeric bounds,
and sanitizes public marketplace views against private administrative or internal data.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.requirements.models import (
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
    PRICE_CONDITION_RANGE,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_DRAFT,
    VALID_PRICE_CONDITIONS,
    VALID_REQUIREMENT_STATUSES,
)


class CategoryResponse(BaseModel):
    """Produce taxonomy category response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    slug: str
    is_active: bool


class BuyerSummary(BaseModel):
    """Sanitized public summary of the posting commercial buyer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contact_person_name: str
    business_name: str
    business_type: str
    city: str
    state: str


class RequirementCreate(BaseModel):
    """Payload for creating a buyer requirement by a verified commercial buyer.

    Server-controlled fields (id, buyer_id, remaining_quantity, is_deleted,
    deleted_at, created_at, updated_at) are strictly forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Free-form agricultural produce demand (e.g. Processing Potatoes, Basmati Rice)",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Headline description of procurement demand",
    )
    description: Optional[str] = Field(
        None,
        description="Detailed procurement notes, specifications, packaging, or storage requirements",
    )
    category_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional produce category taxonomy reference",
    )
    required_quantity: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=3,
        description="Initial required supply quantity (> 0)",
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=16,
        description="Measurement unit (e.g. kg, quintal, metric_ton, bag)",
    )
    target_price_per_unit: Optional[Decimal] = Field(
        None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Optional target unit purchase price in currency (> 0)",
    )
    price_condition: str = Field(
        PRICE_CONDITION_NEGOTIABLE,
        max_length=32,
        description="Pricing condition: 'exact', 'range', or 'negotiable'",
    )
    quality_grade: Optional[str] = Field(
        None,
        max_length=32,
        description="Desired produce quality classification (e.g. Grade A, Organic, Food-Grade)",
    )
    destination_state: Optional[str] = Field(
        None,
        max_length=64,
        description="Destination state (defaults to buyer profile state if omitted)",
    )
    destination_city: Optional[str] = Field(
        None,
        max_length=64,
        description="Destination city or district (defaults to buyer profile city if omitted)",
    )
    required_by_date: date = Field(
        ...,
        description="Procurement deadline date (must be today or in the future)",
    )
    status: Optional[str] = Field(
        REQUIREMENT_STATUS_ACTIVE,
        description="Initial requirement status ('active' or 'draft')",
    )

    @field_validator("product_name", "title", "unit")
    @classmethod
    def validate_non_blank_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return stripped

    @field_validator("quality_grade", "destination_state", "destination_city")
    @classmethod
    def validate_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value

    @field_validator("price_condition")
    @classmethod
    def validate_price_condition(cls, value: str) -> str:
        stripped = value.strip().lower()
        if stripped not in VALID_PRICE_CONDITIONS:
            raise ValueError(
                f"Invalid price condition '{value}'. Must be one of: {', '.join(VALID_PRICE_CONDITIONS)}"
            )
        return stripped

    @field_validator("required_by_date")
    @classmethod
    def validate_required_by_date(cls, value: date) -> date:
        today = date.today()
        if value < today:
            raise ValueError("Procurement deadline date cannot be in the past")
        return value

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, value: Optional[str]) -> str:
        if value is None:
            return REQUIREMENT_STATUS_ACTIVE
        if value not in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_DRAFT):
            raise ValueError("Initial requirement status must be 'active' or 'draft'")
        return value


class RequirementUpdate(BaseModel):
    """Payload for partial update of a buyer requirement by the owner.

    Server-controlled fields (id, buyer_id, created_at, updated_at,
    is_deleted, deleted_at) are strictly forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    product_name: Optional[str] = Field(None, min_length=1, max_length=128)
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None)
    category_id: Optional[uuid.UUID] = Field(None)
    required_quantity: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=3)
    remaining_quantity: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    unit: Optional[str] = Field(None, min_length=1, max_length=16)
    target_price_per_unit: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    price_condition: Optional[str] = Field(None, max_length=32)
    quality_grade: Optional[str] = Field(None, max_length=32)
    destination_state: Optional[str] = Field(None, max_length=64)
    destination_city: Optional[str] = Field(None, max_length=64)
    required_by_date: Optional[date] = Field(None)
    status: Optional[str] = Field(None)

    @field_validator(
        "product_name",
        "title",
        "unit",
        "quality_grade",
        "destination_state",
        "destination_city",
    )
    @classmethod
    def validate_non_blank_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value

    @field_validator("price_condition")
    @classmethod
    def validate_price_condition(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip().lower()
            if stripped not in VALID_PRICE_CONDITIONS:
                raise ValueError(
                    f"Invalid price condition '{value}'. Must be one of: {', '.join(VALID_PRICE_CONDITIONS)}"
                )
            return stripped
        return value

    @field_validator("status")
    @classmethod
    def validate_status_value(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in VALID_REQUIREMENT_STATUSES:
            raise ValueError(
                f"Invalid status '{value}'. Must be one of: {', '.join(VALID_REQUIREMENT_STATUSES)}"
            )
        return value


class RequirementStatusUpdate(BaseModel):
    """Payload specifically for transitioning requirement status."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        ...,
        description="Target lifecycle status ('active', 'draft', 'closed')",
    )

    @field_validator("status")
    @classmethod
    def validate_target_status(cls, value: str) -> str:
        if value not in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_DRAFT, REQUIREMENT_STATUS_CLOSED):
            raise ValueError("Target status must be 'active', 'draft', or 'closed'")
        return value


class BuyerRequirementDetailResponse(BaseModel):
    """Full detail view of a buyer requirement, including category and buyer summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    category: Optional[CategoryResponse] = None
    product_name: str
    title: str
    description: Optional[str] = None
    required_quantity: Decimal
    remaining_quantity: Decimal
    unit: str
    target_price_per_unit: Optional[Decimal] = None
    price_condition: str
    quality_grade: Optional[str] = None
    destination_state: str
    destination_city: str
    required_by_date: date
    status: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    buyer: Optional[BuyerSummary] = None


class BuyerRequirementPublicSummary(BaseModel):
    """Public marketplace card view for a buyer requirement."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    product_name: str
    title: str
    description: Optional[str] = None
    required_quantity: Decimal
    remaining_quantity: Decimal
    unit: str
    target_price_per_unit: Optional[Decimal] = None
    price_condition: str
    quality_grade: Optional[str] = None
    destination_state: str
    destination_city: str
    required_by_date: date
    status: str
    created_at: datetime
    buyer: Optional[BuyerSummary] = None


class BuyerRequirementPublicListResponse(BaseModel):
    """Paginated catalog response for public active buyer requirements."""

    items: List[BuyerRequirementPublicSummary]
    total: int
    page: int
    page_size: int
    total_pages: int

class BuyerRequirementListResponse(BaseModel):
    """Paginated response for buyer's own requirements."""

    items: List[BuyerRequirementDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class ApproveFulfillmentRequest(BaseModel):
    """Payload to approve a requirement fulfillment deduction."""

    approved_quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        decimal_places=3,
        description="Quantity to deduct from requirement remaining demand. If omitted, defaults to proposed quantity.",
    )
    close_requirement: bool = Field(
        default=False,
        description="Explicit instruction to close the requirement. If False, requirement remains open/partially_fulfilled.",
    )


class RejectFulfillmentRequest(BaseModel):
    """Payload to reject a requirement fulfillment deduction."""

    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for rejecting the fulfillment deduction.",
    )


class FulfillmentApprovalResponse(BaseModel):
    """Detailed response for a fulfillment approval record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    proposed_quantity: Decimal
    approved_quantity: Optional[Decimal] = None
    status: str
    reviewed_by_user_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    voided_by_user_id: Optional[uuid.UUID] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Summary enrichment fields for UI/API clients
    requirement_title: Optional[str] = None
    product_name: Optional[str] = None
    unit: Optional[str] = None
    requirement_remaining_quantity: Optional[Decimal] = None
    requirement_status: Optional[str] = None
    order_number: Optional[str] = None


class FulfillmentApprovalListResponse(BaseModel):
    """Paginated list of fulfillment approvals for a buyer."""

    items: List[FulfillmentApprovalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

