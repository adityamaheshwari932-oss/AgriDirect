"""Automated unit and integration tests for Phase 2, Group 2 Verification ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for ``verification_submissions`` and ``verification_documents``
- Expected column definitions, data types, nullabilities, and defaults
- Foreign key definitions and on-delete rules (RESTRICT, SET NULL, CASCADE)
- Table-level check constraints (status, rejection reason, file size)
- Table-level indexes and the partial unique index on pending submissions
- Python-level validation on status, rejection reason, file size, and file URI
- Database execution of valid submission and document lifecycles
- Enforcement of rejection reason requirement (no empty/whitespace reasons)
- Deletion rule enforcement:
  - User deletion blocked when verification submissions exist (RESTRICT)
  - Admin reviewer deletion sets reviewed_by_admin_id to NULL (SET NULL)
  - Submission deletion cascades to verification documents (CASCADE)
- Partial unique index enforcement:
  - Concurrent pending submissions for the same user are rejected
  - Resubmission succeeds once a previous submission is resolved (rejected/approved)
- Bidirectional ORM relationship navigation and delete-orphan behavior
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, text, update
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User
from app.models.verification import (
    MAX_DOCUMENT_SIZE_BYTES,
    VALID_SUBMISSION_STATUSES,
    VerificationDocument,
    VerificationSubmission,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database engine with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Provide a transactional database session for each test."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create and persist a standard farmer user for verification tests."""
    user = User(
        email="farmer_verify@agridirect.test",
        password_hash="hashed_secret_123",
        role="farmer",
        verification_status="unverified",
        account_status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_admin(db_session: Session) -> User:
    """Create and persist an admin user for verification review tests."""
    admin = User(
        email="admin_verify@agridirect.test",
        password_hash="hashed_secret_admin",
        role="admin",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestVerificationMetadata:
    """Verify table structures, column definitions, and constraints in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """Both verification tables must be registered in Base.metadata."""
        assert "verification_submissions" in Base.metadata.tables
        assert "verification_documents" in Base.metadata.tables

    def test_submission_columns(self) -> None:
        """verification_submissions must have all expected columns and nullabilities."""
        table = Base.metadata.tables["verification_submissions"]
        expected_cols = {
            "id": False,
            "user_id": False,
            "status": False,
            "submission_notes": True,
            "reviewed_by_admin_id": True,
            "reviewed_at": True,
            "rejection_reason": True,
            "created_at": False,
            "updated_at": False,
        }
        for col_name, nullable in expected_cols.items():
            assert col_name in table.c, f"Column '{col_name}' missing from verification_submissions"
            assert table.c[col_name].nullable is nullable, (
                f"Column '{col_name}' nullable expected {nullable}, got {table.c[col_name].nullable}"
            )

    def test_document_columns(self) -> None:
        """verification_documents must have all expected columns and nullabilities."""
        table = Base.metadata.tables["verification_documents"]
        expected_cols = {
            "id": False,
            "submission_id": False,
            "document_type": False,
            "document_number": True,
            "file_uri": False,
            "file_mime_type": False,
            "file_size_bytes": False,
            "created_at": False,
        }
        for col_name, nullable in expected_cols.items():
            assert col_name in table.c, f"Column '{col_name}' missing from verification_documents"
            assert table.c[col_name].nullable is nullable, (
                f"Column '{col_name}' nullable expected {nullable}, got {table.c[col_name].nullable}"
            )
        # Note: VerificationDocument is immutable evidence; it intentionally has no updated_at
        assert "updated_at" not in table.c

    def test_submission_foreign_keys_and_rules(self) -> None:
        """Check foreign key targets and on-delete rules for verification_submissions."""
        table = Base.metadata.tables["verification_submissions"]
        fks = {fk.parent.name: fk for fk in table.foreign_keys}

        assert "user_id" in fks
        assert fks["user_id"].column.table.name == "users"
        assert fks["user_id"].column.name == "id"
        assert fks["user_id"].ondelete.upper() == "RESTRICT"

        assert "reviewed_by_admin_id" in fks
        assert fks["reviewed_by_admin_id"].column.table.name == "users"
        assert fks["reviewed_by_admin_id"].column.name == "id"
        assert fks["reviewed_by_admin_id"].ondelete.upper() == "SET NULL"

    def test_document_foreign_keys_and_rules(self) -> None:
        """Check foreign key targets and on-delete rules for verification_documents."""
        table = Base.metadata.tables["verification_documents"]
        fks = {fk.parent.name: fk for fk in table.foreign_keys}

        assert "submission_id" in fks
        assert fks["submission_id"].column.table.name == "verification_submissions"
        assert fks["submission_id"].column.name == "id"
        assert fks["submission_id"].ondelete.upper() == "CASCADE"

    def test_submission_check_constraints(self) -> None:
        """verification_submissions must define status and rejection check constraints."""
        table = Base.metadata.tables["verification_submissions"]
        constraint_names = {c.name for c in table.constraints if hasattr(c, "sqltext")}

        assert "chk_verification_submissions_status" in constraint_names
        assert "chk_verification_rejection" in constraint_names

    def test_document_check_constraints(self) -> None:
        """verification_documents must define file size check constraint."""
        table = Base.metadata.tables["verification_documents"]
        constraint_names = {c.name for c in table.constraints if hasattr(c, "sqltext")}

        assert "chk_verification_docs_file_size" in constraint_names

    def test_submission_indexes(self) -> None:
        """verification_submissions must define expected indexes and partial unique index."""
        table = Base.metadata.tables["verification_submissions"]
        index_map = {idx.name: idx for idx in table.indexes}

        assert "idx_verification_submissions_user_id" in index_map
        assert "idx_verification_submissions_status" in index_map
        assert "idx_verification_submissions_user_status" in index_map
        assert "uq_verification_submissions_user_pending" in index_map

        pending_idx = index_map["uq_verification_submissions_user_pending"]
        assert pending_idx.unique is True
        assert pending_idx.dialect_options["postgresql"]["where"] is not None


# ===========================================================================
# 2. Python-Level Validator Tests
# ===========================================================================


class TestVerificationValidators:
    """Verify ORM @validates hooks for domain rules and boundaries."""

    def test_valid_submission_statuses(self) -> None:
        """Submission status must accept valid values."""
        for status in VALID_SUBMISSION_STATUSES:
            sub = VerificationSubmission(status=status)
            assert sub.status == status

    def test_invalid_submission_status_raises(self) -> None:
        """Invalid submission status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid verification submission status"):
            VerificationSubmission(status="in_progress")

    def test_rejection_reason_cannot_be_empty_when_rejected(self) -> None:
        """Setting status='rejected' without reason must raise ValueError."""
        sub = VerificationSubmission(status="rejected")
        with pytest.raises(ValueError, match="Rejection reason cannot be empty"):
            sub.rejection_reason = "   "

    def test_rejection_reason_valid_when_rejected(self) -> None:
        """Valid rejection reason passes validation."""
        sub = VerificationSubmission(status="rejected")
        sub.rejection_reason = "Document unreadable or expired."
        assert sub.rejection_reason == "Document unreadable or expired."

    def test_document_file_size_positive_validation(self) -> None:
        """Document file size must be strictly positive."""
        with pytest.raises(ValueError, match="File size must be positive"):
            VerificationDocument(file_size_bytes=0)

        with pytest.raises(ValueError, match="File size must be positive"):
            VerificationDocument(file_size_bytes=-500)

    def test_document_file_size_max_boundary(self) -> None:
        """Document file size exceeding 10 MB must raise ValueError."""
        with pytest.raises(ValueError, match="exceeds maximum permitted"):
            VerificationDocument(file_size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1)

        # Exact maximum size passes
        doc = VerificationDocument(file_size_bytes=MAX_DOCUMENT_SIZE_BYTES)
        assert doc.file_size_bytes == MAX_DOCUMENT_SIZE_BYTES

    def test_document_file_uri_non_empty(self) -> None:
        """Document file_uri must be non-empty."""
        with pytest.raises(ValueError, match="file_uri cannot be empty"):
            VerificationDocument(file_uri="")

        with pytest.raises(ValueError, match="file_uri cannot be empty"):
            VerificationDocument(file_uri="   ")


# ===========================================================================
# 3. Database Lifecycle & Constraint Integration Tests
# ===========================================================================


class TestVerificationDatabaseOperations:
    """Integration tests running against the active test database."""

    def test_create_pending_submission_with_documents(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Create a pending submission with multiple documents attached."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
            submission_notes="Applying as an organic wheat producer in Punjab.",
        )
        doc1 = VerificationDocument(
            document_type="kisan_credit_card",
            document_number="KCC-987654321",
            file_uri="storage/verifications/kcc_987.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=1024 * 500,  # 500 KB
        )
        doc2 = VerificationDocument(
            document_type="land_record",
            document_number="LR-PB-2024-001",
            file_uri="storage/verifications/land_record_001.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=1024 * 1200,  # 1.2 MB
        )
        submission.documents.extend([doc1, doc2])

        db_session.add(submission)
        db_session.commit()
        db_session.refresh(submission)

        assert submission.id is not None
        assert isinstance(submission.id, uuid.UUID)
        assert submission.created_at is not None
        assert submission.updated_at is not None
        assert len(submission.documents) == 2
        assert submission.documents[0].id is not None
        assert submission.documents[0].submission_id == submission.id

    def test_admin_approve_submission(
        self, db_session: Session, sample_user: User, sample_admin: User
    ) -> None:
        """Admin reviews and approves a pending submission."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
        )
        db_session.add(submission)
        db_session.commit()

        # Review action
        now_utc = datetime.now(timezone.utc)
        submission.status = "approved"
        submission.reviewed_by_admin_id = sample_admin.id
        submission.reviewed_at = now_utc
        sample_user.verification_status = "verified"

        db_session.commit()
        db_session.refresh(submission)

        assert submission.status == "approved"
        assert submission.reviewed_by_admin_id == sample_admin.id
        assert submission.admin_reviewer.email == sample_admin.email
        assert submission.reviewed_at is not None

    def test_admin_reject_submission_requires_reason(
        self, db_session: Session, sample_user: User, sample_admin: User
    ) -> None:
        """Rejecting a submission with a valid reason succeeds."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
        )
        db_session.add(submission)
        db_session.commit()

        submission.status = "rejected"
        submission.reviewed_by_admin_id = sample_admin.id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.rejection_reason = "Land record document blurry and missing signature page."
        sample_user.verification_status = "rejected"

        db_session.commit()
        db_session.refresh(submission)

        assert submission.status == "rejected"
        assert submission.rejection_reason == "Land record document blurry and missing signature page."

    def test_db_rejection_check_constraint_rejects_empty_reason(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Database check constraint rejects a rejected submission without a non-empty reason."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
        )
        db_session.add(submission)
        db_session.commit()

        # Attempt update bypassing Python validates hook to test database constraint
        with pytest.raises(IntegrityError):
            db_session.execute(
                update(VerificationSubmission)
                .where(VerificationSubmission.id == submission.id)
                .values(status="rejected", rejection_reason="   ")
            )
            db_session.commit()
        db_session.rollback()

    def test_user_deletion_restricted_when_submissions_exist(
        self, db_session: Session, sample_user: User
    ) -> None:
        """ON DELETE RESTRICT prevents deleting a user who has historical verification submissions."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
        )
        db_session.add(submission)
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.delete(sample_user)
            db_session.commit()
        db_session.rollback()

    def test_admin_deletion_sets_reviewer_to_null(
        self, db_session: Session, sample_user: User, sample_admin: User
    ) -> None:
        """ON DELETE SET NULL preserves submission audit record when admin account is deleted."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="approved",
            reviewed_by_admin_id=sample_admin.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(submission)
        db_session.commit()

        sub_id = submission.id
        db_session.delete(sample_admin)
        db_session.commit()

        refreshed_sub = db_session.get(VerificationSubmission, sub_id)
        assert refreshed_sub is not None
        assert refreshed_sub.reviewed_by_admin_id is None
        assert refreshed_sub.status == "approved"

    def test_submission_deletion_cascades_to_documents(
        self, db_session: Session, sample_user: User
    ) -> None:
        """ON DELETE CASCADE removes all documents when their parent submission is deleted."""
        submission = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
        )
        doc = VerificationDocument(
            document_type="gst_certificate",
            document_number="07AAAAA0000A1Z5",
            file_uri="storage/verifications/gst_01.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=50000,
        )
        submission.documents.append(doc)
        db_session.add(submission)
        db_session.commit()

        doc_id = doc.id
        db_session.delete(submission)
        db_session.commit()

        assert db_session.get(VerificationDocument, doc_id) is None

    def test_partial_unique_index_prevents_duplicate_pending(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Partial unique index uq_verification_submissions_user_pending blocks multiple pending submissions."""
        sub1 = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
            submission_notes="First pending attempt.",
        )
        db_session.add(sub1)
        db_session.commit()

        sub2 = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
            submission_notes="Second duplicate pending attempt.",
        )
        db_session.add(sub2)

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_resubmission_allowed_after_rejection(
        self, db_session: Session, sample_user: User, sample_admin: User
    ) -> None:
        """After rejection, a user can submit a new pending submission (full historical retention)."""
        # 1. First submission rejected
        sub1 = VerificationSubmission(
            user_id=sample_user.id,
            status="rejected",
            reviewed_by_admin_id=sample_admin.id,
            reviewed_at=datetime.now(timezone.utc),
            rejection_reason="Incorrect address on land deed.",
        )
        db_session.add(sub1)
        db_session.commit()

        # 2. Resubmission in pending state
        sub2 = VerificationSubmission(
            user_id=sample_user.id,
            status="pending",
            submission_notes="Corrected land deed attached.",
        )
        db_session.add(sub2)
        db_session.commit()

        # 3. Both submissions exist in user history
        db_session.refresh(sample_user)
        assert len(sample_user.verification_submissions) == 2
        statuses = [s.status for s in sample_user.verification_submissions]
        assert "rejected" in statuses
        assert "pending" in statuses

    def test_bidirectional_relationship_collections(
        self, db_session: Session, sample_user: User, sample_admin: User
    ) -> None:
        """ORM collections populate correctly and support back_populates."""
        sub = VerificationSubmission(
            user_id=sample_user.id,
            status="approved",
            reviewed_by_admin_id=sample_admin.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        doc = VerificationDocument(
            document_type="fssai_license",
            document_number="10012011000123",
            file_uri="storage/verifications/fssai_123.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=250000,
        )
        sub.documents.append(doc)
        db_session.add(sub)
        db_session.commit()

        db_session.refresh(sample_user)
        db_session.refresh(sample_admin)

        assert sub in sample_user.verification_submissions
        assert sub in sample_admin.reviewed_verifications
        assert doc.submission is sub
        assert doc in sub.documents
