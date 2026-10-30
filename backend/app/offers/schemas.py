"""Pydantic v2 schemas for Structured Offers and Negotiation (Module 3).

Enforces strict payload validation, extra-attribute rejection, positive quantity
and price bounds, server-side monetary calculations, and UTC timestamp integrity.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.listing import CANONICAL_UNITS
from app.models.offer import (
    OFFER_ITEM_STATUS_PROPOSED,
    OFFER_STATUS_PENDING,
    VALID_OFFER_ITEM_STATUSES,
    VALID_OFFER_STATUSES,
)


class BaseOfferSchema(BaseModel):
    """Base schema rejecting unrecognised attributes."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class OfferItemCreate(BaseOfferSchema):
    """Line-item payload for creating an initial offer or counter-offer."""

    listing_id: uuid.UUID = Field(
        ...,
        description="Mandatory produce listing reference backing the physical goods.",
    )
    buyer_requirement_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional buyer requirement reference being fulfilled by this item.",
    )
    product_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Produce item name. Defaults to listing produce title if omitted.",
    )
    quantity: Decimal = Field(
        ...,
        gt=Decimal("0.000"),
        decimal_places=3,
        description="Physical quantity offered (must be greater than 0).",
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=16,
        description="Measurement unit (e.g. 'kg', 'quintal', 'metric_ton', 'bag').",
    )
    unit_price: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Price per unit in currency units (must be greater than 0.00).",
    )
    quality_grade: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Optional quality grade specification (e.g. 'Grade A').",
    )

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, val: str) -> str:
        clean = val.strip().lower()
        if not clean:
            raise ValueError("Unit cannot be empty")
        return clean


class OfferCreate(BaseOfferSchema):
    """Payload for submitting an initial structured offer."""

    recipient_id: uuid.UUID = Field(
        ...,
        description="Recipient user ID (must be the opposite verified role: buyer or farmer).",
    )
    delivery_terms: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Agreed transport/delivery terms (e.g. 'Farm gate pickup').",
    )
    proposed_delivery_date: Optional[date] = Field(
        default=None,
        description="Target fulfillment date (must be today or in the future).",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Offer validity deadline (UTC timestamp, must be in the future).",
    )
    items: List[OfferItemCreate] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Structured produce line items (minimum 1, maximum 50 items).",
    )

    @field_validator("proposed_delivery_date")
    @classmethod
    def validate_delivery_date(cls, val: Optional[date]) -> Optional[date]:
        if val is not None and val < date.today():
            raise ValueError("Proposed delivery date cannot be in the past")
        return val

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, val: Optional[datetime]) -> Optional[datetime]:
        if val is not None:
            now_utc = datetime.now(timezone.utc)
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            if val <= now_utc:
                raise ValueError("Offer expiration timestamp must be in the future")
        return val

    @model_validator(mode="after")
    def validate_item_references(self) -> "OfferCreate":
        # Disallow duplicate exact items (same listing + same requirement)
        seen = set()
        for idx, item in enumerate(self.items):
            key = (item.listing_id, item.buyer_requirement_id)
            if key in seen:
                raise ValueError(
                    f"Duplicate item reference detected at index {idx} "
                    f"(listing_id={item.listing_id}, requirement_id={item.buyer_requirement_id}). "
                    "Consolidate quantities into a single item line."
                )
            seen.add(key)
        return self


class CounterOfferCreate(BaseOfferSchema):
    """Payload for submitting a counter-offer to an existing pending offer."""

    delivery_terms: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Updated transport/delivery terms.",
    )
    proposed_delivery_date: Optional[date] = Field(
        default=None,
        description="Updated target delivery date (today or future).",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Updated validity deadline (UTC timestamp, future).",
    )
    items: List[OfferItemCreate] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Updated produce line items.",
    )

    @field_validator("proposed_delivery_date")
    @classmethod
    def validate_delivery_date(cls, val: Optional[date]) -> Optional[date]:
        if val is not None and val < date.today():
            raise ValueError("Proposed delivery date cannot be in the past")
        return val

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, val: Optional[datetime]) -> Optional[datetime]:
        if val is not None:
            now_utc = datetime.now(timezone.utc)
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            if val <= now_utc:
                raise ValueError("Offer expiration timestamp must be in the future")
        return val

    @model_validator(mode="after")
    def validate_item_references(self) -> "CounterOfferCreate":
        seen = set()
        for idx, item in enumerate(self.items):
            key = (item.listing_id, item.buyer_requirement_id)
            if key in seen:
                raise ValueError(
                    f"Duplicate item reference at index {idx}. Consolidate quantities."
                )
            seen.add(key)
        return self


class OfferRejectRequest(BaseOfferSchema):
    """Optional payload for rejecting an offer."""

    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional reason for rejecting the proposal.",
    )


class OfferItemResponse(BaseModel):
    """Response representation for an individual line item in an offer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    listing_id: Optional[uuid.UUID]
    buyer_requirement_id: Optional[uuid.UUID]
    product_name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    subtotal: Decimal
    quality_grade: Optional[str]
    status: str
    created_at: datetime


class UserSummary(BaseModel):
    """Compact summary of a negotiation participant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    name: str
    business_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class OfferSummaryResponse(BaseModel):
    """Compact summary representation for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_number: str
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    parent_offer_id: Optional[uuid.UUID]
    delivery_terms: Optional[str]
    proposed_delivery_date: Optional[date]
    total_amount: Decimal
    item_count: int
    status: str
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class OfferDetailResponse(BaseModel):
    """Comprehensive representation of an offer with items and participant info."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_number: str
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    parent_offer_id: Optional[uuid.UUID]
    delivery_terms: Optional[str]
    proposed_delivery_date: Optional[date]
    total_amount: Decimal
    status: str
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    sender: Optional[UserSummary] = None
    recipient: Optional[UserSummary] = None
    items: List[OfferItemResponse] = []
    order_id: Optional[uuid.UUID] = None
    order_number: Optional[str] = None


class OfferListResponse(BaseModel):
    """Paginated response container for offer lists."""

    items: List[OfferSummaryResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OfferHistoryResponse(BaseModel):
    """Chronological negotiation history chain."""

    root_offer_id: uuid.UUID
    current_offer_id: uuid.UUID
    chain_length: int
    history: List[OfferDetailResponse]


class ItemFulfillmentDecision(BaseModel):
    """Granular fulfillment decision for a specific requirement-linked item in an offer."""

    offer_item_id: uuid.UUID = Field(
        description="ID of the specific offer item linked to a buyer requirement."
    )
    apply_to_requirement: bool = Field(
        default=True,
        description="Whether to apply this item's quantity toward requirement fulfillment."
    )
    approved_quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        decimal_places=3,
        description="Quantity to deduct. If omitted and apply_to_requirement=True, defaults to full item quantity."
    )
    close_requirement: bool = Field(
        default=False,
        description="Explicitly mark the linked requirement as 'closed'. Never auto-closed."
    )


class OfferAcceptRequest(BaseModel):
    """Request payload when accepting an offer with optional requirement fulfillment directives."""

    apply_to_requirement: bool = Field(
        default=True,
        description="Default fulfillment action for requirement-linked items if item_fulfillments is omitted."
    )
    approved_quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        decimal_places=3,
        description="Default approved quantity if item_fulfillments is omitted (defaults to full item quantity)."
    )
    close_requirement: bool = Field(
        default=False,
        description="Default close flag if item_fulfillments is omitted."
    )
    item_fulfillments: Optional[List[ItemFulfillmentDecision]] = Field(
        default=None,
        description="Optional granular per-item fulfillment decisions for multi-item offers."
    )


class OfferAcceptResponse(BaseModel):
    """Response payload returned when an offer is accepted and order is instantiated."""

    offer_id: uuid.UUID
    offer_number: str
    order_id: uuid.UUID
    order_number: str
    status: str
    total_amount: Decimal
    message: str

