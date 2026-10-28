"""SQLAlchemy ORM model for user operational alerts and notifications.

Implements Module 7 (Reputation and Notifications) of AgriDirect:
- ``Notification``: Operational alerts for platform users (Table 7.2 / Store D16).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

# Canonical notification reference entity types
NOTIFICATION_REF_ORDER = "order"
NOTIFICATION_REF_OFFER = "offer"
NOTIFICATION_REF_LISTING = "listing"
NOTIFICATION_REF_VERIFICATION = "verification"

VALID_NOTIFICATION_REF_TYPES = (
    NOTIFICATION_REF_ORDER,
    NOTIFICATION_REF_OFFER,
    NOTIFICATION_REF_LISTING,
    NOTIFICATION_REF_VERIFICATION,
)


class Notification(Base, UUIDPrimaryKeyMixin):
    """Operational alert and in-app message for platform users."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="notifications",
    )

    __table_args__ = (
        Index(
            "idx_notifications_user_unread",
            "user_id",
            "is_read",
            text("created_at DESC"),
        ),
    )
