"""Pydantic v2 schemas for Module 5 chat, messaging, attachments, and contact sharing."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ParticipantSummary(BaseModel):
    """Public summary of a conversation participant."""

    id: uuid.UUID
    role: str
    verification_status: str
    name: str
    entity_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Schema for initiating or retrieving a conversation thread."""

    target_user_id: Optional[uuid.UUID] = Field(None, description="Optional target user UUID")
    listing_id: Optional[uuid.UUID] = Field(None, description="ProduceListing UUID context")
    requirement_id: Optional[uuid.UUID] = Field(None, description="BuyerRequirement UUID context")
    order_id: Optional[uuid.UUID] = Field(None, description="Order UUID context")
    offer_id: Optional[uuid.UUID] = Field(None, description="Offer UUID context")


class ConversationResponse(BaseModel):
    """Schema for listing user conversations."""

    id: uuid.UUID
    farmer_id: uuid.UUID
    buyer_id: uuid.UUID
    initial_context_type: Optional[str] = None
    initial_context_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    status: str
    created_at: datetime
    last_message_at: datetime
    unread_count: int
    other_participant: ParticipantSummary
    last_message_preview: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActiveContactRequestSummary(BaseModel):
    """Summary of active contact sharing request in conversation."""

    id: uuid.UUID
    requester_id: uuid.UUID
    status: str
    requested_at: datetime


class ConversationDetailResponse(BaseModel):
    """Full detail view of a conversation thread."""

    id: uuid.UUID
    farmer_id: uuid.UUID
    buyer_id: uuid.UUID
    initial_context_type: Optional[str] = None
    initial_context_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    status: str
    created_at: datetime
    last_message_at: datetime
    unread_count: int
    other_participant: ParticipantSummary
    contact_sharing_consented: bool
    active_contact_request: Optional[ActiveContactRequestSummary] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    items: List[ConversationResponse]
    total: int
    limit: int
    offset: int


class MessageCreate(BaseModel):
    """Request schema for sending a text message."""

    content: str = Field(..., min_length=1, max_length=5000, description="Message text content")
    order_id: Optional[uuid.UUID] = Field(None, description="Optional order reference")


class MessageAttachmentResponse(BaseModel):
    """Attachment metadata response."""

    id: uuid.UUID
    message_id: uuid.UUID
    file_name: str
    file_mime_type: str
    file_size_bytes: int
    attachment_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Full message response model."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    message_type: str
    delivery_status: str
    is_read: bool
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    order_id: Optional[uuid.UUID] = None
    created_at: datetime
    attachments: List[MessageAttachmentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    """Paginated messages in a conversation."""

    items: List[MessageResponse]
    total: int


class ContactShareRequestCreate(BaseModel):
    """Request schema to request mutual contact sharing."""

    notes: Optional[str] = Field(None, max_length=500, description="Optional note for the request")


class ContactShareRequestResponse(BaseModel):
    """Response schema for contact sharing requests."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    requester_id: uuid.UUID
    recipient_id: uuid.UUID
    status: str
    requested_at: datetime
    responded_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContactDetailsResponse(BaseModel):
    """Disclosed participant contact information after consent."""

    id: uuid.UUID
    role: str
    name: str
    entity_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None


class ReadStatusResponse(BaseModel):
    """Result of marking messages as read."""

    conversation_id: uuid.UUID
    marked_read_count: int


class UnreadCountResponse(BaseModel):
    """Unread message count for a conversation."""

    conversation_id: uuid.UUID
    unread_count: int

