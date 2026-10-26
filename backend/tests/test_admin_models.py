"""Automated unit and integration tests for AdminAuditLog ORM model.

Tests cover:
- Model registration in ``Base.metadata`` for ``admin_audit_logs``
- Expected column definitions, data types, nullabilities, and defaults
- Primary key generation via UUIDPrimaryKeyMixin
- Confirmation of absence of ``updated_at`` (immutable audit log pattern)
- Foreign key definitions and on-delete rules (RESTRICT on admin_user_id)
- Confirmation that target_entity_id has no foreign key constraint (polymorphic pattern)
- Table-level indexes: idx_audit_logs_admin and idx_audit_logs_target
- Absence of restrictive database CHECK constraints on action and target_entity_type (extensibility)
- Database execution:
  - Valid audit log creation targeting different entity types (user, verification_submission, listing)
  - Extensible action names (both canonical and custom domain actions)
  - Database enforcement of NOT NULL constraints on required fields
  - Database enforcement of foreign key constraint on admin_user_id
  - Deletion restriction preventing deletion of an admin user who has audit records (ON DELETE RESTRICT)
  - Bidirectional ORM relationship navigation between User and AdminAuditLog
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.admin import (
    ACTION_REMOVE_LISTING,
    ACTION_SUSPEND_USER,
    ACTION_VERIFY_APPROVE,
    ACTION_VERIFY_REJECT,
    CANONICAL_ADMIN_ACTIONS,
    CANONICAL_TARGET_ENTITIES,
    TARGET_ENTITY_LISTING,
    TARGET_ENTITY_REPORT,
    TARGET_ENTITY_USER,
    TARGET_ENTITY_VERIFICATION_SUBMISSION,
    AdminAuditLog,
)
from app.models.user import User


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
def sample_admin(db_session: Session) -> User:
    """Create and persist an administrator user for audit tests."""
    admin = User(
        email="audit_admin@agridirect.test",
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


class TestAdminAuditLogMetadata:
    """Verify table structure, column definitions, and constraints in Base.metadata."""

    def test_table_registered_in_metadata(self) -> None:
        """admin_audit_logs table must be registered in Base.metadata."""
        assert "admin_audit_logs" in Base.metadata.tables

    def test_column_definitions_and_nullability(self) -> None:
        """admin_audit_logs must have all expected columns and nullabilities."""
        table = Base.metadata.tables["admin_audit_logs"]
        expected_cols = {
            "id": False,
            "admin_user_id": False,
            "action": False,
            "target_entity_type": False,
            "target_entity_id": False,
            "reason": True,
            "ip_address": True,
            "created_at": False,
        }
        for col_name, nullable in expected_cols.items():
            assert col_name in table.c, f"Column '{col_name}' missing from admin_audit_logs"
            assert table.c[col_name].nullable is nullable, (
                f"Column '{col_name}' nullable expected {nullable}, got {table.c[col_name].nullable}"
            )

    def test_absence_of_updated_at(self) -> None:
        """admin_audit_logs must be append-only and not contain an updated_at column."""
        table = Base.metadata.tables["admin_audit_logs"]
        assert "updated_at" not in table.c
        assert not hasattr(AdminAuditLog, "updated_at")

    def test_primary_key_definition(self) -> None:
        """id must be a surrogate UUID primary key."""
        table = Base.metadata.tables["admin_audit_logs"]
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["id"]
        assert isinstance(table.c.id.type, PG_UUID)

    def test_foreign_key_definitions_and_rules(self) -> None:
        """admin_user_id must reference users.id with ON DELETE RESTRICT."""
        table = Base.metadata.tables["admin_audit_logs"]
        fks = {fk.parent.name: fk for fk in table.foreign_keys}

        assert "admin_user_id" in fks
        assert fks["admin_user_id"].column.table.name == "users"
        assert fks["admin_user_id"].column.name == "id"
        assert fks["admin_user_id"].ondelete.upper() == "RESTRICT"

    def test_target_entity_id_has_no_foreign_key(self) -> None:
        """target_entity_id must NOT have a foreign key constraint (polymorphic targeting)."""
        table = Base.metadata.tables["admin_audit_logs"]
        fk_parents = {fk.parent.name for fk in table.foreign_keys}
        assert "target_entity_id" not in fk_parents

    def test_indexes_defined(self) -> None:
        """Only the two specified indexes must be declared on admin_audit_logs."""
        table = Base.metadata.tables["admin_audit_logs"]
        index_map = {idx.name: [c.name for c in idx.columns] for idx in table.indexes}

        assert "idx_audit_logs_admin" in index_map
        assert index_map["idx_audit_logs_admin"] == ["admin_user_id"]

        assert "idx_audit_logs_target" in index_map
        assert index_map["idx_audit_logs_target"] == ["target_entity_type", "target_entity_id"]

    def test_absence_of_restrictive_check_constraints(self) -> None:
        """action and target_entity_type must not be restricted by database CHECK constraints."""
        table = Base.metadata.tables["admin_audit_logs"]
        check_names = [c.name for c in table.constraints if hasattr(c, "sqltext")]
        # Confirm no check constraints restricting action or target_entity_type values
        assert len(check_names) == 0

    def test_canonical_constants_defined(self) -> None:
        """Canonical action and target constants must match specifications."""
        assert ACTION_VERIFY_APPROVE == "verify_approve"
        assert ACTION_VERIFY_REJECT == "verify_reject"
        assert ACTION_SUSPEND_USER == "suspend_user"
        assert ACTION_REMOVE_LISTING == "remove_listing"
        assert set(CANONICAL_ADMIN_ACTIONS) == {
            "verify_approve",
            "verify_reject",
            "suspend_user",
            "remove_listing",
        }
        assert set(CANONICAL_TARGET_ENTITIES) == {
            "user",
            "verification_submission",
            "listing",
            "report",
        }


# ===========================================================================
# 2. Database Integration & Operations Tests
# ===========================================================================


class TestAdminAuditLogDatabaseOperations:
    """Integration tests executing against an isolated test database."""

    def test_create_valid_audit_log(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """Create and persist a standard administrative audit log entry."""
        target_user_id = uuid.uuid4()
        log = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action=ACTION_SUSPEND_USER,
            target_entity_type=TARGET_ENTITY_USER,
            target_entity_id=target_user_id,
            reason="Repeated terms of service violations regarding off-platform payment attempts.",
            ip_address="192.168.1.100",
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.id is not None
        assert isinstance(log.id, uuid.UUID)
        assert log.created_at is not None
        assert log.admin_user_id == sample_admin.id
        assert log.action == ACTION_SUSPEND_USER
        assert log.target_entity_type == TARGET_ENTITY_USER
        assert log.target_entity_id == target_user_id
        assert log.reason is not None
        assert log.ip_address == "192.168.1.100"

    def test_create_audit_log_with_nullable_fields_omitted(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """Create an audit log with optional reason and ip_address set to None."""
        target_sub_id = uuid.uuid4()
        log = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action=ACTION_VERIFY_APPROVE,
            target_entity_type=TARGET_ENTITY_VERIFICATION_SUBMISSION,
            target_entity_id=target_sub_id,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.reason is None
        assert log.ip_address is None

    def test_extensible_action_and_target_entity_type(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """Extensible action and target types can be inserted without constraint errors."""
        custom_target_id = uuid.uuid4()
        log = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action="custom_emergency_intervention",
            target_entity_type="dispute_arbitration_case",
            target_entity_id=custom_target_id,
            reason="Unprecedented dispute requiring custom moderation.",
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.action == "custom_emergency_intervention"
        assert log.target_entity_type == "dispute_arbitration_case"

    def test_target_entity_id_accepts_any_uuid_without_fk_target(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """target_entity_id does not require the referenced entity to exist in any table."""
        non_existent_uuid = uuid.uuid4()
        log = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action=ACTION_REMOVE_LISTING,
            target_entity_type=TARGET_ENTITY_LISTING,
            target_entity_id=non_existent_uuid,
            reason="Listing deleted for counterfeit documentation.",
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.target_entity_id == non_existent_uuid

    def test_missing_required_fields_raises_integrity_error(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """Database NOT NULL constraints reject missing required attributes."""
        # 1. Missing action
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO admin_audit_logs (id, admin_user_id, target_entity_type, target_entity_id, created_at) "
                    "VALUES (:id, :admin_id, 'user', :target_id, datetime('now'))"
                ),
                {"id": uuid.uuid4().hex, "admin_id": sample_admin.id.hex, "target_id": uuid.uuid4().hex},
            )
            db_session.commit()
        db_session.rollback()

        # 2. Missing target_entity_type
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO admin_audit_logs (id, admin_user_id, action, target_entity_id, created_at) "
                    "VALUES (:id, :admin_id, 'suspend_user', :target_id, datetime('now'))"
                ),
                {"id": uuid.uuid4().hex, "admin_id": sample_admin.id.hex, "target_id": uuid.uuid4().hex},
            )
            db_session.commit()
        db_session.rollback()

        # 3. Missing target_entity_id
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO admin_audit_logs (id, admin_user_id, action, target_entity_type, created_at) "
                    "VALUES (:id, :admin_id, 'suspend_user', 'user', datetime('now'))"
                ),
                {"id": uuid.uuid4().hex, "admin_id": sample_admin.id.hex},
            )
            db_session.commit()
        db_session.rollback()

    def test_non_existent_admin_user_raises_foreign_key_violation(
        self, db_session: Session
    ) -> None:
        """Inserting an audit log with an invalid admin_user_id raises an IntegrityError."""
        orphan_log = AdminAuditLog(
            admin_user_id=uuid.uuid4(),
            action=ACTION_SUSPEND_USER,
            target_entity_type=TARGET_ENTITY_USER,
            target_entity_id=uuid.uuid4(),
        )
        db_session.add(orphan_log)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_admin_user_deletion_restricted_when_audit_logs_exist(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """ON DELETE RESTRICT blocks deleting an administrator who has recorded audit logs."""
        log = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action=ACTION_VERIFY_APPROVE,
            target_entity_type=TARGET_ENTITY_VERIFICATION_SUBMISSION,
            target_entity_id=uuid.uuid4(),
        )
        db_session.add(log)
        db_session.commit()

        # Attempting to delete the administrator must fail with an IntegrityError
        with pytest.raises(IntegrityError):
            db_session.delete(sample_admin)
            db_session.commit()
        db_session.rollback()

    def test_bidirectional_relationship_navigation(
        self, db_session: Session, sample_admin: User
    ) -> None:
        """Bidirectional relationship navigates correctly between User and AdminAuditLog."""
        log1 = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action=ACTION_VERIFY_APPROVE,
            target_entity_type=TARGET_ENTITY_VERIFICATION_SUBMISSION,
            target_entity_id=uuid.uuid4(),
        )
        log2 = AdminAuditLog(
            admin_user_id=sample_admin.id,
            action=ACTION_SUSPEND_USER,
            target_entity_type=TARGET_ENTITY_USER,
            target_entity_id=uuid.uuid4(),
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        db_session.refresh(sample_admin)
        assert len(sample_admin.admin_audit_logs) == 2
        assert log1 in sample_admin.admin_audit_logs
        assert log2 in sample_admin.admin_audit_logs
        assert log1.admin_user is sample_admin
        assert log2.admin_user is sample_admin
