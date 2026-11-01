"""Pydantic v2 schemas for notifications and operational alerts.

Implements request and response validation for Module 7 / Group 11 (Notifications):
- ``NotificationRead``: Full serialized notification payload
- ``NotificationCreate``: Internal schema for creating notifications
- ``NotificationListResponse``: Paginated notification list with total and unread metrics
- ``NotificationMarkReadResponse``: Confirmation response when a notification is marked read
"""

import math
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    """Shared notification attributes."""

    event_type: str = Field(..., max_length=64, description="Canonical notification event key")
    title: str = Field(..., max_length=128, description="Notification headline")
    body: str = Field(..., description="Notification narrative text")
    reference_type: Optional[str] = Field(
        None, max_length=32, description="Target entity type (order, offer, listing, verification)"
    )
    reference_id: Optional[uuid.UUID] = Field(
        None, description="Primary key of associated entity"
    )


class NotificationCreate(NotificationBase):
    """Payload for creating a new in-app notification."""

    user_id: uuid.UUID = Field(..., description="Recipient user ID")


class NotificationRead(NotificationBase):
    """Public serialized notification view."""

    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Paginated collection of notifications for an authenticated user."""

    items: List[NotificationRead]
    total: int = Field(..., ge=0, description="Total notifications belonging to caller")
    unread_count: int = Field(..., ge=0, description="Total unread notifications for caller")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Page size limit")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")

    @classmethod
    def create(
        cls,
        items: List[NotificationRead],
        total: int,
        unread_count: int,
        page: int,
        page_size: int,
    ) -> "NotificationListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class NotificationMarkReadResponse(BaseModel):
    """Response returned when a notification is marked as read."""

    id: uuid.UUID
    is_read: bool = True
    read_at: datetime
    message: str = "Notification marked as read successfully"


class NotificationUnreadCountResponse(BaseModel):
    """Response containing total unread notification count."""

    unread_count: int = Field(..., ge=0, description="Total unread notifications for caller")


class NotificationMarkAllReadResponse(BaseModel):
    """Response returned when all notifications are marked as read."""

    marked_count: int = Field(..., ge=0, description="Total notifications updated to read")
    message: str = "All notifications marked as read successfully"

