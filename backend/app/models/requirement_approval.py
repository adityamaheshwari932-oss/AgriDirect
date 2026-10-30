"""SQLAlchemy ORM model for requirement fulfillment approvals.

Implements ADR-003: Requirement Fulfillment Approval Workflow.
Decouples commercial offer acceptance & order creation from buyer requirement procurement accounting.
Enforces strict buyer authority, multi-item atomicity, partial fulfillment approval,
and exhaustive terminal-state audit trail.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order, OrderItem
    from app.models.requirement import BuyerRequirement
    from app.models.user import User

# Canonical approval lifecycle statuses (ADR-003 Section 4.1)
APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"
APPROVAL_STATUS_NOT_APPLIED = "not_applied"
APPROVAL_STATUS_VOIDED = "voided"

VALID_APPROVAL_STATUSES = (
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_NOT_APPLIED,
    APPROVAL_STATUS_VOIDED,
)

TERMINAL_APPROVAL_STATUSES = (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_NOT_APPLIED,
    APPROVAL_STATUS_VOIDED,
)


class RequirementFulfillmentApproval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """First-class fulfillment approval record permanently auditing order item to requirement deduction.

    Enforces:
    - 1:1 order item linkage via unique order_item_id.
    - Composite foreign key guaranteeing (order_item_id, order_id, requirement_id) match order_items.
    - Exhaustive CHECK constraint enforcing column NULL / non-NULL invariants across all 5 states.
    - Immutable terminal states (approved, rejected, not_applied, voided).
    """

    __tablename__ = "requirement_fulfillment_approvals"

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buyer_requirements.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    proposed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=False,
    )
    approved_quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=3),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=APPROVAL_STATUS_PENDING,
        server_default=APPROVAL_STATUS_PENDING,
        nullable=False,
    )

    # Buyer review audit fields (populated for approved, rejected, not_applied)
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Voiding audit fields (populated for voided)
    voided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    void_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    requirement: Mapped["BuyerRequirement"] = relationship(
        "BuyerRequirement",
        foreign_keys=[requirement_id],
        back_populates="fulfillment_approvals",
    )
    order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[order_id],
        back_populates="fulfillment_approvals",
    )
    order_item: Mapped["OrderItem"] = relationship(
        "OrderItem",
        foreign_keys=[order_item_id],
        back_populates="fulfillment_approval",
    )
    reviewed_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by_user_id],
    )
    voided_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[voided_by_user_id],
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["order_item_id", "order_id", "requirement_id"],
            ["order_items.id", "order_items.order_id", "order_items.buyer_requirement_id"],
            name="fk_approvals_order_item_composite",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "proposed_quantity > 0",
            name="chk_approval_proposed_quantity",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'not_applied', 'voided')",
            name="chk_approval_status",
        ),
        CheckConstraint(
            """(
                status = 'pending'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NULL
                AND reviewed_at IS NULL
                AND rejection_reason IS NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'approved'
                AND approved_quantity IS NOT NULL
                AND approved_quantity > 0
                AND approved_quantity <= proposed_quantity
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
                AND rejection_reason IS NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'rejected'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'not_applied'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
                AND rejection_reason IS NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'voided'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NULL
                AND reviewed_at IS NULL
                AND rejection_reason IS NULL
                AND voided_at IS NOT NULL
                AND void_reason IS NOT NULL
            )""",
            name="chk_approval_complete_invariants",
        ),
        Index("idx_req_approvals_requirement_status", "requirement_id", "status"),
        Index(
            "idx_req_approvals_buyer_pending",
            "requirement_id",
            postgresql_where=text("status = 'pending'"),
        ),
        Index("idx_req_approvals_order", "order_id"),
        Index(
            "idx_req_approvals_reviewed_by",
            "reviewed_by_user_id",
            postgresql_where=text("reviewed_by_user_id IS NOT NULL"),
        ),
    )

