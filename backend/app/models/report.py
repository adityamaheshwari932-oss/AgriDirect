"""SQLAlchemy ORM model for user complaints and safety moderation.

Implements Module 8 (Moderation and Administrative Accountability) of AgriDirect:
- ``UserReport``: User complaints regarding conduct, produce quality, or fraud (Table 8.1 / Store D17).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.listing import ProduceListing
    from app.models.user import User

# Canonical report categories (schema-design.md Table 8.1)
REPORT_CATEGORY_PAYMENT = "payment"
REPORT_CATEGORY_QUANTITY_MISMATCH = "quantity_mismatch"
REPORT_CATEGORY_QUALITY_ISSUE = "quality_issue"
REPORT_CATEGORY_FRAUD = "fraud"
REPORT_CATEGORY_HARASSMENT = "harassment"
REPORT_CATEGORY_OTHER = "other"

VALID_REPORT_CATEGORIES = (
    REPORT_CATEGORY_PAYMENT,
    REPORT_CATEGORY_QUANTITY_MISMATCH,
    REPORT_CATEGORY_QUALITY_ISSUE,
    REPORT_CATEGORY_FRAUD,
    REPORT_CATEGORY_HARASSMENT,
    REPORT_CATEGORY_OTHER,
)

# Canonical report review statuses (schema-design.md Table 8.1)
REPORT_STATUS_OPEN = "open"
REPORT_STATUS_UNDER_REVIEW = "under_review"
REPORT_STATUS_ACTION_TAKEN = "action_taken"
REPORT_STATUS_DISMISSED = "dismissed"

VALID_REPORT_STATUSES = (
    REPORT_STATUS_OPEN,
    REPORT_STATUS_UNDER_REVIEW,
    REPORT_STATUS_ACTION_TAKEN,
    REPORT_STATUS_DISMISSED,
)


class UserReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User complaints regarding conduct, produce quality, fraud, or violations."""

    __tablename__ = "user_reports"

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reported_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    listing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=REPORT_STATUS_OPEN,
        server_default=REPORT_STATUS_OPEN,
        nullable=False,
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reporter_id],
        back_populates="reports_filed",
    )
    reported_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reported_user_id],
        back_populates="reports_received",
    )
    listing: Mapped[Optional["ProduceListing"]] = relationship(
        "ProduceListing",
        foreign_keys=[listing_id],
    )
    reviewed_by_admin: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by_admin_id],
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('payment', 'quantity_mismatch', 'quality_issue', 'fraud', 'harassment', 'other')",
            name="chk_user_reports_category",
        ),
        CheckConstraint(
            "status IN ('open', 'under_review', 'action_taken', 'dismissed')",
            name="chk_user_reports_status",
        ),
        Index(
            "idx_user_reports_status",
            "status",
            text("created_at DESC"),
        ),
    )
