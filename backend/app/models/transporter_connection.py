"""SQLAlchemy ORM model for Transport Connection Requests.

Facilitates bilateral connection and coordination workflows between
farmers, buyers, and independent commercial transportation providers.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.offer import Offer
    from app.models.order import Order
    from app.models.user import User

# Canonical connection request statuses
TRANSPORT_REQUEST_STATUS_PENDING = "pending"
TRANSPORT_REQUEST_STATUS_ACCEPTED = "accepted"
TRANSPORT_REQUEST_STATUS_DECLINED = "declined"
TRANSPORT_REQUEST_STATUS_CANCELLED = "cancelled"

VALID_TRANSPORT_REQUEST_STATUSES = (
    TRANSPORT_REQUEST_STATUS_PENDING,
    TRANSPORT_REQUEST_STATUS_ACCEPTED,
    TRANSPORT_REQUEST_STATUS_DECLINED,
    TRANSPORT_REQUEST_STATUS_CANCELLED,
)


class TransportConnectionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a formal transportation service request from a farmer or buyer to a transporter."""

    __tablename__ = "transport_connection_requests"

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    transporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    offer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="SET NULL"),
        nullable=True,
    )

    pickup_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pickup_district: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pickup_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    delivery_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    delivery_district: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cargo_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    required_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        default=TRANSPORT_REQUEST_STATUS_PENDING,
        server_default=TRANSPORT_REQUEST_STATUS_PENDING,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
    )
    transporter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[transporter_id],
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id],
    )
    offer: Mapped[Optional["Offer"]] = relationship(
        "Offer",
        foreign_keys=[offer_id],
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_TRANSPORT_REQUEST_STATUSES}",
            name="chk_transport_request_status",
        ),
        Index("idx_transport_req_transporter_status", "transporter_id", "status"),
        Index("idx_transport_req_requester_status", "requester_id", "status"),
        Index("idx_transport_req_order", "order_id"),
        Index("idx_transport_req_offer", "offer_id"),
    )
