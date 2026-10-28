"""SQLAlchemy ORM models for off-platform payment tracking and payment complaints.

Implements Module 6 (Payment Tracking & Dispute Moderation) of AgriDirect:
- ``PaymentRecord``: External payment acknowledgement records (Table 6.1 / Store D13).
- ``PaymentComplaint``: Payment dispute filing and administrative resolution (Table 6.2 / Sub-store D17).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User

# Canonical payment methods (schema-design.md Table 6.1 & BR-15)
PAYMENT_METHOD_UPI = "upi"
PAYMENT_METHOD_BANK_TRANSFER = "bank_transfer"
PAYMENT_METHOD_CASH = "cash"
PAYMENT_METHOD_OTHER = "other"

VALID_PAYMENT_METHODS = (
    PAYMENT_METHOD_UPI,
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_OTHER,
)

# Canonical payment statuses (schema-design.md Table 6.1)
PAYMENT_STATUS_RECORDED = "payment_recorded"
PAYMENT_STATUS_ACKNOWLEDGED = "acknowledged"
PAYMENT_STATUS_DISPUTED = "disputed"

VALID_PAYMENT_STATUSES = (
    PAYMENT_STATUS_RECORDED,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
)

# Canonical payment complaint statuses (schema-design.md Table 6.2)
PAYMENT_COMPLAINT_STATUS_OPEN = "open"
PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW = "under_review"
PAYMENT_COMPLAINT_STATUS_RESOLVED = "resolved"
PAYMENT_COMPLAINT_STATUS_DISMISSED = "dismissed"

VALID_PAYMENT_COMPLAINT_STATUSES = (
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_DISMISSED,
)


class PaymentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Payment tracking record for transactions conducted outside AgriDirect.

    AgriDirect tracks external payments and receipts without processing or holding funds (BR-15).
    """

    __tablename__ = "payment_records"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    reference_number: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    proof_file_uri: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=PAYMENT_STATUS_RECORDED,
        server_default=PAYMENT_STATUS_RECORDED,
        nullable=False,
    )
    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[order_id],
        back_populates="payment_records",
    )
    recorded_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recorded_by_user_id],
    )
    complaints: Mapped[List["PaymentComplaint"]] = relationship(
        "PaymentComplaint",
        foreign_keys="[PaymentComplaint.payment_record_id]",
        back_populates="payment_record",
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="chk_payments_amount",
        ),
        CheckConstraint(
            "payment_method IN ('upi', 'bank_transfer', 'cash', 'other')",
            name="chk_payments_method",
        ),
        CheckConstraint(
            "status IN ('payment_recorded', 'acknowledged', 'disputed')",
            name="chk_payments_status",
        ),
        Index("idx_payments_order", "order_id"),
    )


class PaymentComplaint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Disputes regarding non-receipt or unacknowledged payments."""

    __tablename__ = "payment_complaints"

    payment_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    complainant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    complaint_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_file_uri: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=PAYMENT_COMPLAINT_STATUS_OPEN,
        server_default=PAYMENT_COMPLAINT_STATUS_OPEN,
        nullable=False,
    )
    admin_resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    resolved_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    payment_record: Mapped["PaymentRecord"] = relationship(
        "PaymentRecord",
        foreign_keys=[payment_record_id],
        back_populates="complaints",
    )
    complainant: Mapped["User"] = relationship(
        "User",
        foreign_keys=[complainant_user_id],
    )
    resolved_by_admin: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[resolved_by_admin_id],
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'under_review', 'resolved', 'dismissed')",
            name="chk_payment_complaints_status",
        ),
        Index("idx_payment_complaints_payment", "payment_record_id"),
    )
