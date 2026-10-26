"""SQLAlchemy models for Verification submissions and documents.

Implements Module 1 (Verification Management) of AgriDirect:
- ``VerificationSubmission``: Records individual verification attempts, admin review decisions,
  timestamps, notes, and rejection reasons.
- ``VerificationDocument``: Secure storage references and metadata for verification evidence.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

VALID_SUBMISSION_STATUSES = ("pending", "approved", "rejected")
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB (10,485,760 bytes)


class VerificationSubmission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a discrete submission cycle for identity and credentials verification.

    Maintains full historical records of verification attempts. A user may have multiple
    past submissions (e.g. initial rejection followed by a resubmission), but at most
    one submission in 'pending' status at any given time.
    """

    __tablename__ = "verification_submissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    submission_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="verification_submissions",
    )
    admin_reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by_admin_id],
        back_populates="reviewed_verifications",
    )
    documents: Mapped[List["VerificationDocument"]] = relationship(
        "VerificationDocument",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="VerificationDocument.created_at",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="chk_verification_submissions_status",
        ),
        CheckConstraint(
            "(status = 'rejected' AND rejection_reason IS NOT NULL AND length(trim(rejection_reason)) > 0) OR status <> 'rejected'",
            name="chk_verification_rejection",
        ),
        Index("idx_verification_submissions_user_id", "user_id"),
        Index("idx_verification_submissions_status", "status"),
        Index("idx_verification_submissions_user_status", "user_id", "status"),
        Index(
            "uq_verification_submissions_user_pending",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """Validate that submission status matches permitted lifecycle values."""
        if value not in VALID_SUBMISSION_STATUSES:
            raise ValueError(
                f"Invalid verification submission status '{value}'. "
                f"Must be one of: {', '.join(VALID_SUBMISSION_STATUSES)}"
            )
        return value

    @validates("rejection_reason")
    def validate_rejection_reason(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate that a rejection reason is provided if status is rejected."""
        if getattr(self, "status", None) == "rejected" and (value is None or not value.strip()):
            raise ValueError(
                "Rejection reason cannot be empty or whitespace-only when status is 'rejected'."
            )
        return value


class VerificationDocument(Base, UUIDPrimaryKeyMixin):
    """Stores metadata and secure storage references for verification evidence files.

    Documents are immutable evidence attached to a verification submission cycle.
    Raw document contents are never stored in database text fields.
    """

    __tablename__ = "verification_documents"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    document_number: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    file_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    file_mime_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    submission: Mapped["VerificationSubmission"] = relationship(
        "VerificationSubmission",
        back_populates="documents",
    )

    __table_args__ = (
        CheckConstraint(
            "file_size_bytes > 0 AND file_size_bytes <= 10485760",
            name="chk_verification_docs_file_size",
        ),
        Index("idx_verification_docs_submission", "submission_id"),
        Index("idx_verification_docs_type", "document_type"),
    )

    @validates("file_size_bytes")
    def validate_file_size(self, key: str, value: int) -> int:
        """Validate that file size is strictly positive and within 10 MB limit."""
        if value <= 0:
            raise ValueError(f"File size must be positive, got {value} bytes.")
        if value > MAX_DOCUMENT_SIZE_BYTES:
            raise ValueError(
                f"File size exceeds maximum permitted {MAX_DOCUMENT_SIZE_BYTES} bytes (10 MB), got {value} bytes."
            )
        return value

    @validates("file_uri")
    def validate_file_uri(self, key: str, value: str) -> str:
        """Validate that file_uri is non-empty."""
        if not value or not value.strip():
            raise ValueError("file_uri cannot be empty or whitespace-only.")
        return value.strip()
