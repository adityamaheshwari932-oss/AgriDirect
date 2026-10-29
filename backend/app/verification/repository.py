"""Repository layer for verification submissions, documents, and administrative review persistence.

Executes parameterized SQLAlchemy queries scoped to User and Admin authorization contexts.
"""

import uuid
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.models.admin import AdminAuditLog
from app.models.user import User
from app.models.verification import VerificationDocument, VerificationSubmission


class VerificationRepository:
    """Encapsulates database access for verification submissions and evidence files."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, submission_id: uuid.UUID) -> Optional[VerificationSubmission]:
        """Retrieve a VerificationSubmission by ID with eager-loaded user and documents."""
        return (
            self.db.query(VerificationSubmission)
            .options(
                joinedload(VerificationSubmission.documents),
                joinedload(VerificationSubmission.user),
            )
            .filter(VerificationSubmission.id == submission_id)
            .first()
        )

    def get_by_id_for_update(
        self, submission_id: uuid.UUID
    ) -> Optional[VerificationSubmission]:
        """Retrieve a VerificationSubmission by ID with a row-level lock (FOR UPDATE)."""
        return (
            self.db.query(VerificationSubmission)
            .options(
                joinedload(VerificationSubmission.documents),
                joinedload(VerificationSubmission.user),
            )
            .filter(VerificationSubmission.id == submission_id)
            .with_for_update(of=VerificationSubmission)
            .first()
        )

    def get_pending_submission_by_user(
        self, user_id: uuid.UUID
    ) -> Optional[VerificationSubmission]:
        """Retrieve the currently active pending submission for a user, if any."""
        return (
            self.db.query(VerificationSubmission)
            .options(joinedload(VerificationSubmission.documents))
            .filter(
                VerificationSubmission.user_id == user_id,
                VerificationSubmission.status == "pending",
            )
            .first()
        )

    def get_latest_submission_by_user(
        self, user_id: uuid.UUID
    ) -> Optional[VerificationSubmission]:
        """Retrieve the most recent verification submission for a user."""
        return (
            self.db.query(VerificationSubmission)
            .options(joinedload(VerificationSubmission.documents))
            .filter(VerificationSubmission.user_id == user_id)
            .order_by(desc(VerificationSubmission.created_at))
            .first()
        )

    def get_all_submissions_by_user(
        self, user_id: uuid.UUID
    ) -> List[VerificationSubmission]:
        """Retrieve complete submission history for an applicant."""
        return (
            self.db.query(VerificationSubmission)
            .options(joinedload(VerificationSubmission.documents))
            .filter(VerificationSubmission.user_id == user_id)
            .order_by(desc(VerificationSubmission.created_at))
            .all()
        )

    def create_submission(
        self, submission: VerificationSubmission
    ) -> VerificationSubmission:
        """Persist a new verification submission and flush to database."""
        self.db.add(submission)
        self.db.flush()
        return submission

    def add_document(self, document: VerificationDocument) -> VerificationDocument:
        """Persist a verification document record."""
        self.db.add(document)
        self.db.flush()
        return document

    def get_document_by_id(
        self, document_id: uuid.UUID
    ) -> Optional[VerificationDocument]:
        """Retrieve a VerificationDocument by primary key with its parent submission."""
        return (
            self.db.query(VerificationDocument)
            .options(joinedload(VerificationDocument.submission))
            .filter(VerificationDocument.id == document_id)
            .first()
        )

    def list_submissions(
        self,
        status: Optional[str] = None,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[VerificationSubmission]:
        """List verification submissions with filtering and pagination for admin queues."""
        query = (
            self.db.query(VerificationSubmission)
            .join(User, VerificationSubmission.user_id == User.id)
            .options(
                joinedload(VerificationSubmission.documents),
                joinedload(VerificationSubmission.user),
            )
        )

        if status:
            query = query.filter(VerificationSubmission.status == status)
        if role:
            query = query.filter(User.role == role)

        return (
            query.order_by(desc(VerificationSubmission.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_submissions(
        self,
        status: Optional[str] = None,
        role: Optional[str] = None,
    ) -> int:
        """Count total submissions matching filter criteria."""
        query = self.db.query(VerificationSubmission).join(
            User, VerificationSubmission.user_id == User.id
        )

        if status:
            query = query.filter(VerificationSubmission.status == status)
        if role:
            query = query.filter(User.role == role)

        return query.count()

    def record_admin_audit(self, audit_entry: AdminAuditLog) -> None:
        """Persist an administrative audit trail record."""
        self.db.add(audit_entry)
        self.db.flush()
