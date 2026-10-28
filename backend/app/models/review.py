"""SQLAlchemy ORM model for mutual transaction-linked ratings and reviews.

Implements Module 7 (Reputation and Notifications) of AgriDirect:
- ``RatingReview``: Bilateral counterparty ratings for completed transactions (Table 7.1 / Store D15).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class RatingReview(Base, UUIDPrimaryKeyMixin):
    """Mutual counterparty rating and testimonial for completed transactions (BR-17).

    Guarantees at most one review per reviewer per order via unique constraint,
    and prevents self-reviews at the database level.
    """

    __tablename__ = "ratings_reviews"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    overall_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quality_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    accuracy_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    communication_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    reliability_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    review_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
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
        back_populates="ratings_reviews",
    )
    reviewer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reviewer_id],
        back_populates="reviews_given",
    )
    reviewed_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reviewed_user_id],
        back_populates="reviews_received",
    )

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "reviewer_id",
            name="uq_order_reviewer",
        ),
        CheckConstraint(
            "reviewer_id <> reviewed_user_id",
            name="chk_reviewer_different",
        ),
        CheckConstraint(
            "overall_rating BETWEEN 1 AND 5",
            name="chk_reviews_overall_rating",
        ),
        CheckConstraint(
            "quality_rating IS NULL OR (quality_rating BETWEEN 1 AND 5)",
            name="chk_reviews_quality_rating",
        ),
        CheckConstraint(
            "accuracy_rating IS NULL OR (accuracy_rating BETWEEN 1 AND 5)",
            name="chk_reviews_accuracy_rating",
        ),
        CheckConstraint(
            "communication_rating IS NULL OR (communication_rating BETWEEN 1 AND 5)",
            name="chk_reviews_communication_rating",
        ),
        CheckConstraint(
            "reliability_rating IS NULL OR (reliability_rating BETWEEN 1 AND 5)",
            name="chk_reviews_reliability_rating",
        ),
        Index("idx_reviews_reviewed_user", "reviewed_user_id", "overall_rating"),
    )
