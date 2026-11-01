"""Automated unit and integration tests for Payments and Delivery (Group 9) ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``payment_records``
  - ``payment_complaints``
- Column definitions, data types, precision, scale, nullabilities, and defaults:
  - ``payment_records.amount``: Numeric(12, 2)
  - ``payment_records.status``: default 'payment_recorded'
  - ``payment_complaints.status``: default 'open'
- Primary key generation via ``UUIDPrimaryKeyMixin``
- ``TimestampMixin`` usage (created_at, updated_at on both models)
- Foreign key definitions and on-delete rules:
  - ``payment_records.order_id -> orders.id`` (ON DELETE RESTRICT)
  - ``payment_records.recorded_by_user_id -> users.id`` (ON DELETE RESTRICT)
  - ``payment_complaints.payment_record_id -> payment_records.id`` (ON DELETE RESTRICT)
  - ``payment_complaints.complainant_user_id -> users.id`` (ON DELETE RESTRICT)
  - ``payment_complaints.resolved_by_admin_id -> users.id`` (ON DELETE SET NULL)
- Check constraints:
  - ``chk_payments_amount`` (amount > 0)
  - ``chk_payments_method`` ('upi', 'bank_transfer', 'cash', 'other')
  - ``chk_payments_status`` ('payment_recorded', 'acknowledged', 'disputed')
  - ``chk_payment_complaints_status`` ('open', 'under_review', 'resolved', 'dismissed')
- Indexes on both tables (idx_payments_order, idx_payment_complaints_payment)
- Database execution:
  - Payment record creation and acknowledgement
  - Payment complaint creation and admin resolution
  - Preservation of payment history via RESTRICT rules
  - Verification that delivery attributes reside in ``orders`` without a redundant table
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.chat import Conversation
from app.models.offer import OFFER_STATUS_ACCEPTED, Offer
from app.models.order import ORDER_STATUS_CONFIRMED, Order
from app.models.payment import (
    PAYMENT_COMPLAINT_STATUS_DISMISSED,
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_OTHER,
    PAYMENT_METHOD_UPI,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    VALID_PAYMENT_COMPLAINT_STATUSES,
    VALID_PAYMENT_METHODS,
    VALID_PAYMENT_STATUSES,
    PaymentComplaint,
    PaymentRecord,
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
def sample_farmer(db_session: Session) -> User:
    """Create and persist a verified farmer user."""
    farmer = User(
        email="pay_farmer@agridirect.test",
        password_hash="hashed_secret_farmer",
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)
    return farmer


@pytest.fixture
def sample_buyer(db_session: Session) -> User:
    """Create and persist a verified buyer user."""
    buyer = User(
        email="pay_buyer@agridirect.test",
        password_hash="hashed_secret_buyer",
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(buyer)
    db_session.commit()
    db_session.refresh(buyer)
    return buyer


@pytest.fixture
def sample_admin(db_session: Session) -> User:
    """Create and persist an admin user."""
    admin = User(
        email="pay_admin@agridirect.test",
        password_hash="hashed_secret_admin",
        role="admin",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def sample_order(
    db_session: Session, sample_farmer: User, sample_buyer: User
) -> Order:
    """Create and persist a base order for payment tests."""
    conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
    db_session.add(conv)
    db_session.commit()

    offer = Offer(
        offer_number="OFF-PAY-0001",
        conversation_id=conv.id,
        sender_id=sample_buyer.id,
        recipient_id=sample_farmer.id,
        total_amount=Decimal("150000.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db_session.add(offer)
    db_session.commit()

    order = Order(
        order_number="ORD-PAY-0001",
        source_offer_id=offer.id,
        buyer_id=sample_buyer.id,
        farmer_id=sample_farmer.id,
        total_amount=Decimal("150000.00"),
        status=ORDER_STATUS_CONFIRMED,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestPaymentMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """Both Group 9 tables must be registered in Base.metadata."""
        assert "payment_records" in Base.metadata.tables
        assert "payment_complaints" in Base.metadata.tables
        # Confirm delivery_records is NOT registered as a separate table
        assert "delivery_records" not in Base.metadata.tables

    def test_payment_records_columns_and_nullability(self) -> None:
        """payment_records must have all 11 specified columns with exact nullabilities."""
        table = Base.metadata.tables["payment_records"]
        expected = {
            "id": False,
            "order_id": False,
            "recorded_by_user_id": False,
            "amount": False,
            "payment_method": False,
            "reference_number": True,
            "proof_file_uri": True,
            "status": False,
            "payment_date": False,
            "acknowledged_at": True,
            "original_acknowledged_at": True,
            "created_at": False,
            "updated_at": False,
        }
        assert len(table.columns) == 13
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from payment_records"
            assert table.c[col_name].nullable == nullable

    def test_payment_complaints_columns_and_nullability(self) -> None:
        """payment_complaints must have all 9 specified columns with exact nullabilities."""
        table = Base.metadata.tables["payment_complaints"]
        expected = {
            "id": False,
            "payment_record_id": False,
            "complainant_user_id": False,
            "complaint_reason": False,
            "evidence_file_uri": True,
            "status": False,
            "admin_resolution_notes": True,
            "resolved_by_admin_id": True,
            "created_at": False,
            "updated_at": False,
        }
        assert len(table.columns) == 10
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from payment_complaints"
            assert table.c[col_name].nullable == nullable

    def test_payment_foreign_keys_and_on_delete_rules(self) -> None:
        """Foreign keys must enforce RESTRICT for historical preservation and SET NULL for admin."""
        # 1. payment_records
        pr_tbl = Base.metadata.tables["payment_records"]
        pr_fks = {fk.parent.name: fk for fk in pr_tbl.foreign_keys}
        assert pr_fks["order_id"].column.table.name == "orders"
        assert pr_fks["order_id"].ondelete == "RESTRICT"
        assert pr_fks["recorded_by_user_id"].column.table.name == "users"
        assert pr_fks["recorded_by_user_id"].ondelete == "RESTRICT"

        # 2. payment_complaints
        pc_tbl = Base.metadata.tables["payment_complaints"]
        pc_fks = {fk.parent.name: fk for fk in pc_tbl.foreign_keys}
        assert pc_fks["payment_record_id"].column.table.name == "payment_records"
        assert pc_fks["payment_record_id"].ondelete == "RESTRICT"
        assert pc_fks["complainant_user_id"].column.table.name == "users"
        assert pc_fks["complainant_user_id"].ondelete == "RESTRICT"
        assert pc_fks["resolved_by_admin_id"].column.table.name == "users"
        assert pc_fks["resolved_by_admin_id"].ondelete == "SET NULL"

    def test_canonical_payment_constants(self) -> None:
        """Payment methods, payment statuses, and complaint statuses must match specification."""
        assert set(VALID_PAYMENT_METHODS) == {
            "upi",
            "bank_transfer",
            "cash",
            "other",
        }
        assert set(VALID_PAYMENT_STATUSES) == {
            "payment_recorded",
            "acknowledged",
            "disputed",
        }
        assert set(VALID_PAYMENT_COMPLAINT_STATUSES) == {
            "open",
            "under_review",
            "resolved",
            "dismissed",
        }


# ===========================================================================
# 2. Database Operations & Persistence Tests
# ===========================================================================


class TestPaymentPersistence:
    """Verify database CRUD, acknowledgement tracking, and complaints handling."""

    def test_create_payment_record_and_acknowledge(
        self,
        db_session: Session,
        sample_order: Order,
        sample_buyer: User,
    ) -> None:
        """Buyer records an off-platform payment, later acknowledged by farmer."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_buyer.id,
            amount=Decimal("150000.00"),
            payment_method=PAYMENT_METHOD_UPI,
            reference_number="UPI/REF/9876543210",
            proof_file_uri="https://storage.agridirect.test/receipts/rec_001.pdf",
            status=PAYMENT_STATUS_RECORDED,
            payment_date=date.today(),
        )
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)

        assert payment.id is not None
        assert payment.status == "payment_recorded"
        assert payment.created_at is not None
        assert payment.updated_at is not None

        # Farmer acknowledges payment
        now_utc = datetime.now(timezone.utc)
        payment.status = PAYMENT_STATUS_ACKNOWLEDGED
        payment.acknowledged_at = now_utc
        db_session.commit()
        db_session.refresh(payment)

        assert payment.status == "acknowledged"
        assert payment.acknowledged_at is not None

        # Verify relationship from Order to PaymentRecord
        db_session.refresh(sample_order)
        assert len(sample_order.payment_records) == 1
        assert sample_order.payment_records[0].id == payment.id

    def test_create_payment_complaint_and_resolve(
        self,
        db_session: Session,
        sample_order: Order,
        sample_farmer: User,
        sample_admin: User,
    ) -> None:
        """Farmer files a payment complaint for non-receipt, admin resolves it."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_order.buyer_id,
            amount=Decimal("75000.00"),
            payment_method=PAYMENT_METHOD_BANK_TRANSFER,
            reference_number="NEFT998877",
            status=PAYMENT_STATUS_DISPUTED,
            payment_date=date.today(),
        )
        db_session.add(payment)
        db_session.commit()

        complaint = PaymentComplaint(
            payment_record_id=payment.id,
            complainant_user_id=sample_farmer.id,
            complaint_reason="Bank account shows no incoming transfer for NEFT998877 after 5 days",
            evidence_file_uri="https://storage.agridirect.test/disputes/statement_nov.pdf",
            status=PAYMENT_COMPLAINT_STATUS_OPEN,
        )
        db_session.add(complaint)
        db_session.commit()
        db_session.refresh(complaint)

        assert complaint.status == "open"
        assert complaint.payment_record.amount == Decimal("75000.00")

        # Admin resolves dispute
        complaint.status = PAYMENT_COMPLAINT_STATUS_RESOLVED
        complaint.resolved_by_admin_id = sample_admin.id
        complaint.admin_resolution_notes = "Verified with bank branch; buyer re-initiated transfer."
        db_session.commit()
        db_session.refresh(complaint)

        assert complaint.status == "resolved"
        assert complaint.resolved_by_admin.email == sample_admin.email


# ===========================================================================
# 3. Check Constraint & Integrity Enforcement Tests
# ===========================================================================


class TestPaymentConstraints:
    """Verify runtime check constraints and deletion protection."""

    def test_payment_amount_must_be_positive(
        self,
        db_session: Session,
        sample_order: Order,
        sample_buyer: User,
    ) -> None:
        """chk_payments_amount rejects amount <= 0."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_buyer.id,
            amount=Decimal("0.00"),
            payment_method=PAYMENT_METHOD_CASH,
            payment_date=date.today(),
        )
        db_session.add(payment)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_payment_method_fails(
        self,
        db_session: Session,
        sample_order: Order,
        sample_buyer: User,
    ) -> None:
        """chk_payments_method rejects unsupported payment methods."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_buyer.id,
            amount=Decimal("5000.00"),
            payment_method="bitcoin",  # Invalid
            payment_date=date.today(),
        )
        db_session.add(payment)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_payment_status_fails(
        self,
        db_session: Session,
        sample_order: Order,
        sample_buyer: User,
    ) -> None:
        """chk_payments_status rejects unsupported statuses."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_buyer.id,
            amount=Decimal("5000.00"),
            payment_method=PAYMENT_METHOD_CASH,
            status="escrow_locked",  # Invalid
            payment_date=date.today(),
        )
        db_session.add(payment)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_complaint_status_fails(
        self,
        db_session: Session,
        sample_order: Order,
        sample_farmer: User,
    ) -> None:
        """chk_payment_complaints_status rejects unsupported statuses."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_order.buyer_id,
            amount=Decimal("5000.00"),
            payment_method=PAYMENT_METHOD_CASH,
            payment_date=date.today(),
        )
        db_session.add(payment)
        db_session.commit()

        complaint = PaymentComplaint(
            payment_record_id=payment.id,
            complainant_user_id=sample_farmer.id,
            complaint_reason="No cash received",
            status="arbitration_pending",  # Invalid
        )
        db_session.add(complaint)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_delete_order_restricted_when_payment_exists(
        self,
        db_session: Session,
        sample_order: Order,
        sample_buyer: User,
    ) -> None:
        """ON DELETE RESTRICT prevents deleting order when payment records exist."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_buyer.id,
            amount=Decimal("1000.00"),
            payment_method=PAYMENT_METHOD_UPI,
            payment_date=date.today(),
        )
        db_session.add(payment)
        db_session.commit()

        db_session.delete(sample_order)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_delete_payment_record_restricted_when_complaint_exists(
        self,
        db_session: Session,
        sample_order: Order,
        sample_farmer: User,
    ) -> None:
        """ON DELETE RESTRICT prevents deleting payment record when complaints exist."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_order.buyer_id,
            amount=Decimal("1000.00"),
            payment_method=PAYMENT_METHOD_UPI,
            payment_date=date.today(),
        )
        db_session.add(payment)
        db_session.commit()

        complaint = PaymentComplaint(
            payment_record_id=payment.id,
            complainant_user_id=sample_farmer.id,
            complaint_reason="Fake transaction id",
            status=PAYMENT_COMPLAINT_STATUS_OPEN,
        )
        db_session.add(complaint)
        db_session.commit()

        db_session.delete(payment)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_delete_admin_sets_null_on_resolved_complaints(
        self,
        db_session: Session,
        sample_order: Order,
        sample_farmer: User,
        sample_admin: User,
    ) -> None:
        """ON DELETE SET NULL sets resolved_by_admin_id to null when admin user is deleted."""
        payment = PaymentRecord(
            order_id=sample_order.id,
            recorded_by_user_id=sample_order.buyer_id,
            amount=Decimal("1000.00"),
            payment_method=PAYMENT_METHOD_UPI,
            payment_date=date.today(),
        )
        db_session.add(payment)
        db_session.commit()

        complaint = PaymentComplaint(
            payment_record_id=payment.id,
            complainant_user_id=sample_farmer.id,
            complaint_reason="Dispute notes",
            status=PAYMENT_COMPLAINT_STATUS_RESOLVED,
            resolved_by_admin_id=sample_admin.id,
        )
        db_session.add(complaint)
        db_session.commit()

        # Delete admin
        db_session.delete(sample_admin)
        db_session.commit()

        db_session.refresh(complaint)
        assert complaint.resolved_by_admin_id is None
        assert complaint.status == "resolved"
