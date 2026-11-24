"""Pydantic v2 schemas for Orders, Amendments, Delivery, and Inventory Audit (Module 4).

Enforces strict input validation, decimal precision, pagination boundaries,
and secure response serialization adhering to AgriDirect standards.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.order import (
    AMENDMENT_TYPE_DELIVERY_DATE,
    AMENDMENT_TYPE_PRICE,
    AMENDMENT_TYPE_QUANTITY,
    AMENDMENT_TYPE_TERMS,
    VALID_AMENDMENT_TYPES,
)


class BaseOrderSchema(BaseModel):
    """Base schema rejecting unrecognised attributes."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


# ---------------------------------------------------------------------------
# Order Details & Line Items (Batch 1)
# ---------------------------------------------------------------------------

class OrderParticipantResponse(BaseModel):
    """Safe participant identity snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    business_name: Optional[str] = None
    farm_name: Optional[str] = None


class OrderItemResponse(BaseModel):
    """Immutable line-item snapshot view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    listing_id: Optional[uuid.UUID] = None
    buyer_requirement_id: Optional[uuid.UUID] = None
    product_name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    subtotal: Decimal
    quality_grade: Optional[str] = None
    status: str
    created_at: datetime


class OrderAmendmentResponse(BaseModel):
    """Order amendment record view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    proposed_by_user_id: uuid.UUID
    amendment_type: str
    old_value: str
    new_value: str
    justification: str
    buyer_confirmed: bool
    farmer_confirmed: bool
    status: str
    effective_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class OrderDeliveryAcknowledgementResponse(BaseModel):
    """Delivery receipt acknowledgement record view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    user_id: uuid.UUID
    acknowledged_at: datetime
    notes: Optional[str] = None


class OrderImageResponse(BaseModel):
    """Photographic quality documentation, dispatch verification, or receipt asset attached to an order."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    image_url: str
    mime_type: str
    file_size_bytes: int
    created_at: datetime


class OrderDetailResponse(BaseModel):
    """Detailed order view with items, participants, delivery, images, and amendment lineage."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    source_offer_id: Optional[uuid.UUID] = None
    buyer_id: uuid.UUID
    farmer_id: uuid.UUID
    total_amount: Decimal
    currency: str = "INR"
    status: str
    delivery_method: Optional[str] = None
    delivery_destination_address: Optional[str] = None
    delivery_arranged_date: Optional[date] = None
    delivery_status: str
    delivery_completion_marked_by_user_id: Optional[uuid.UUID] = None
    delivery_completion_marked_at: Optional[datetime] = None
    delivery_acknowledged_by_user_id: Optional[uuid.UUID] = None
    delivery_acknowledged_at: Optional[datetime] = None
    delivery_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancelled_by_user_id: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    items: List[OrderItemResponse] = []
    buyer: Optional[OrderParticipantResponse] = None
    farmer: Optional[OrderParticipantResponse] = None
    amendments: List[OrderAmendmentResponse] = []
    delivery_acknowledgements: List[OrderDeliveryAcknowledgementResponse] = []
    delivery_acknowledgements_pending: List[str] = []
    images: List[OrderImageResponse] = []


class OrderListItemResponse(BaseModel):
    """Compact summary view for order listings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    source_offer_id: Optional[uuid.UUID] = None
    buyer_id: uuid.UUID
    farmer_id: uuid.UUID
    total_amount: Decimal
    currency: str = "INR"
    status: str
    delivery_status: str
    delivery_arranged_date: Optional[date] = None
    items_count: int
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """Paginated order list response."""

    model_config = ConfigDict(from_attributes=True)

    items: List[OrderListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderCreateRequest(BaseOrderSchema):
    """Payload for direct order placement against a produce listing."""

    listing_id: uuid.UUID = Field(..., description="ID of the active produce listing to purchase")
    quantity: Decimal = Field(..., gt=Decimal("0"), decimal_places=2, description="Physical volume of produce to purchase")
    delivery_destination_address: Optional[str] = Field(default=None, max_length=500, description="Destination delivery address")
    delivery_arranged_date: Optional[date] = Field(default=None, description="Proposed delivery date")
    delivery_notes: Optional[str] = Field(default=None, max_length=1000, description="Buyer special handling instructions or dispatch requirements")
    idempotency_key: Optional[str] = Field(default=None, max_length=128, description="Client idempotency token preventing duplicate submissions")


# ---------------------------------------------------------------------------
# Order Cancellation (Batch 2)
# ---------------------------------------------------------------------------

class OrderCancelRequest(BaseOrderSchema):
    """Payload for cancelling an eligible active order."""

    reason: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Mandatory reason for cancelling the order.",
    )


# ---------------------------------------------------------------------------
# Order Amendments (Batch 3)
# ---------------------------------------------------------------------------

class OrderAmendmentCreate(BaseOrderSchema):
    """Payload to propose a post-finalization order amendment."""

    amendment_type: str = Field(
        ...,
        description="Amendment type: 'quantity', 'price', 'delivery_date', or 'terms'.",
    )
    order_item_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Mandatory for 'quantity' and 'price' line-item amendments.",
    )
    new_quantity: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0.000"),
        decimal_places=3,
        description="New line-item quantity (mandatory for 'quantity' amendments).",
    )
    new_price: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="New line-item unit price (mandatory for 'price' amendments).",
    )
    new_delivery_date: Optional[date] = Field(
        default=None,
        description="New agreed delivery date (mandatory for 'delivery_date' amendments).",
    )
    new_terms: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=2000,
        description="New trade terms or notes (mandatory for 'terms' amendments).",
    )
    justification: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Commercial explanation justifying the proposed change.",
    )

    @field_validator("amendment_type")
    @classmethod
    def validate_type(cls, val: str) -> str:
        clean = val.strip().lower()
        if clean not in VALID_AMENDMENT_TYPES:
            raise ValueError(f"Invalid amendment type '{clean}'. Valid types: {VALID_AMENDMENT_TYPES}")
        return clean

    @model_validator(mode="after")
    def validate_type_fields(self) -> "OrderAmendmentCreate":
        if self.amendment_type == AMENDMENT_TYPE_QUANTITY:
            if not self.order_item_id:
                raise ValueError("order_item_id is required for quantity amendments")
            if self.new_quantity is None:
                raise ValueError("new_quantity is required for quantity amendments")
        elif self.amendment_type == AMENDMENT_TYPE_PRICE:
            if not self.order_item_id:
                raise ValueError("order_item_id is required for price amendments")
            if self.new_price is None:
                raise ValueError("new_price is required for price amendments")
        elif self.amendment_type == AMENDMENT_TYPE_DELIVERY_DATE:
            if not self.new_delivery_date:
                raise ValueError("new_delivery_date is required for delivery_date amendments")
        elif self.amendment_type == AMENDMENT_TYPE_TERMS:
            if not self.new_terms or not self.new_terms.strip():
                raise ValueError("new_terms is required for terms amendments")
        return self


class OrderAmendmentListResponse(BaseModel):
    """List response for order amendments."""

    model_config = ConfigDict(from_attributes=True)

    items: List[OrderAmendmentResponse]
    total: int


# ---------------------------------------------------------------------------
# Delivery Coordination (Batch 4)
# ---------------------------------------------------------------------------

class DeliveryArrangeRequest(BaseOrderSchema):
    """Payload to schedule and specify physical delivery arrangements."""

    delivery_method: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Logistics method (e.g. 'seller_dispatch', 'buyer_pickup', 'third_party_transport').",
    )
    delivery_destination_address: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Full physical delivery destination address.",
    )
    delivery_arranged_date: date = Field(
        ...,
        description="Scheduled physical delivery or pickup date.",
    )
    delivery_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Special delivery handling or contact instructions.",
    )


class DeliveryAcknowledgeRequest(BaseOrderSchema):
    """Payload to record delivery receipt acknowledgement."""

    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional receipt verification notes, condition remarks, or acceptance comment.",
    )


# ---------------------------------------------------------------------------
# Inventory Audit Ledger (Batch 5)
# ---------------------------------------------------------------------------

class InventoryAdjustmentResponse(BaseModel):
    """Append-only inventory audit ledger entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    amendment_id: Optional[uuid.UUID] = None
    change_type: str
    quantity_delta: Decimal
    recorded_by_user_id: uuid.UUID
    notes: Optional[str] = None
    created_at: datetime


class InventoryAdjustmentListResponse(BaseModel):
    """Paginated inventory adjustments response."""

    model_config = ConfigDict(from_attributes=True)

    items: List[InventoryAdjustmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

