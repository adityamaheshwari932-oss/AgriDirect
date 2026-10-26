"""SQLAlchemy model for administrative audit logging.

Implements Module 8 (Governance and Audit Trail) of AgriDirect:
- ``AdminAuditLog``: Permanent, append-only audit trail capturing privileged administrative operations.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

# Canonical administrative action names defined in schema-design.md and SRS
ACTION_VERIFY_APPROVE = "verify_approve"
ACTION_VERIFY_REJECT = "verify_reject"
ACTION_SUSPEND_USER = "suspend_user"
ACTION_REMOVE_LISTING = "remove_listing"

CANONICAL_ADMIN_ACTIONS = (
    ACTION_VERIFY_APPROVE,
    ACTION_VERIFY_REJECT,
    ACTION_SUSPEND_USER,
    ACTION_REMOVE_LISTING,
)

# Canonical target entity types defined in schema-design.md
TARGET_ENTITY_USER = "user"
TARGET_ENTITY_VERIFICATION_SUBMISSION = "verification_submission"
TARGET_ENTITY_LISTING = "listing"
TARGET_ENTITY_REPORT = "report"

CANONICAL_TARGET_ENTITIES = (
    TARGET_ENTITY_USER,
    TARGET_ENTITY_VERIFICATION_SUBMISSION,
    TARGET_ENTITY_LISTING,
    TARGET_ENTITY_REPORT,
)


class AdminAuditLog(Base, UUIDPrimaryKeyMixin):
    """Permanent audit trail of privileged administrative operations.

    Records who (admin), what (action), which entity (target_entity_type, target_entity_id),
    why (reason), from where (ip_address), and when (created_at).

    Intentionally does not inherit TimestampMixin because audit records are append-only
    and have no updated_at timestamp.

    The target entity is referenced via generic/polymorphic identifier pair
    (target_entity_type, target_entity_id) without a database foreign key constraint,
    enabling audit records to target diverse current and future domain entities.
    """

    __tablename__ = "admin_audit_logs"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    target_entity_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Bidirectional relationship to acting administrator
    admin_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[admin_user_id],
        back_populates="admin_audit_logs",
    )

    __table_args__ = (
        Index("idx_audit_logs_admin", "admin_user_id"),
        Index("idx_audit_logs_target", "target_entity_type", "target_entity_id"),
    )
