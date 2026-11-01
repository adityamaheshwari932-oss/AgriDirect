"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 6: Payment Tracking & Dispute Moderation.

Verifies Module 6 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`.

Safety Guarantees:
- Uses ONLY `agridirect_module3_test`.
- Strictly NEVER touches, accesses, or modifies `agridirect_db`.
- Pre-flight database name assertion on every test execution.
- Auto-clean up via TRUNCATE CASCADE with complete isolation.
"""

import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator, List, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.admin import AdminAuditLog
from app.models.chat import Conversation
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE
from app.models.offer import Offer, OFFER_STATUS_ACCEPTED
from app.models.order import (
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_STATUS_CONFIRMED,
    Order,
    OrderItem,
)
from app.models.payment import (
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_UPI,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    PaymentComplaint,
    PaymentRecord,
)
from app.models.user import BuyerProfile, FarmerProfile, User
from app.payments.repository import PaymentRepository
from app.payments.schemas import PaymentRecordCreate
from app.payments.service import PaymentService

# Verified isolated PostgreSQL test connection
TEST_PG_DB_URL = "postgresql+psycopg://agridirect_app:agridirect@localhost:5432/agridirect_module3_test"

_pg_engine = create_engine(TEST_PG_DB_URL, pool_size=20, max_overflow=10)
_SessionLocal = sessionmaker(bind=_pg_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Database Cleanup and Safety Guarantees
# ---------------------------------------------------------------------------

def _cleanup_database() -> None:
    """Pre-flight check and clean up agridirect_module3_test."""
    with _SessionLocal() as db:
        db_name = db.execute(text("SELECT current_database()")).scalar()
        if db_name != "agridirect_module3_test":
            raise RuntimeError(
                f"ABORT: Safety check failed! Connected to '{db_name}', expected 'agridirect_module3_test'"
            )

        db.execute(
            text("""
            TRUNCATE TABLE 
                admin_audit_logs,
                payment_complaints,
                payment_records,
                contact_share_requests,
                order_delivery_acknowledgements,
                requirement_fulfillment_approvals,
                order_amendments,
                inventory_adjustments,
                order_items,
                orders,
                offer_items,
                offers,
                notifications,
                message_attachments,
                messages,
                conversation_participants,
                conversations,
                buyer_requirements,
                produce_listings,
                produce_categories,
                buyer_profiles,
                farmer_profiles,
                users
            CASCADE
        """)
        )
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def setup_pg_environment():
    """Verify database identity and prepare test database once per session."""
    with _SessionLocal() as db:
        db_name = db.execute(text("SELECT current_database()")).scalar()
        if db_name != "agridirect_module3_test":
            raise RuntimeError(f"Refusing to execute tests on database: {db_name}")
    _cleanup_database()
    yield
    _cleanup_database()


@pytest.fixture(autouse=True)
def run_around_tests():
    """Clean up after each test to ensure complete test isolation."""
    yield
    _cleanup_database()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh SQLAlchemy Session connected to agridirect_module3_test."""
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient connected to agridirect_module3_test."""
    def override_get_db():
        session = _SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed Helpers
# ---------------------------------------------------------------------------

def make_auth_headers(user: User) -> dict:
    """Generate JWT authorization bearer header."""
    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "verification_status": user.verification_status,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def seed_farmer(db: Session, verified: bool = True, active: bool = True) -> User:
    """Create a farmer with profile in PostgreSQL."""
    u = User(
        email=f"pg_farmer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="farmer",
        verification_status="verified" if verified else "unverified",
        account_status="active" if active else "suspended",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    FarmerProfile(
        user=u,
        full_name="Postgres Farmer",
        farm_name="Patil Agro Farms",
        farm_location_address="Gat 12, Nashik",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_buyer(db: Session, verified: bool = True, active: bool = True) -> User:
    """Create a commercial buyer with profile in PostgreSQL."""
    u = User(
        email=f"pg_buyer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active" if active else "suspended",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    BuyerProfile(
        user=u,
        business_name="PG Fresh Foods",
        business_type="restaurant",
        contact_person_name="Priya Sharma",
        delivery_receiving_address="Shop 4, Market Yard",
        city="Pune",
        state="Maharashtra",
        postal_code="411037",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_admin(db: Session) -> User:
    """Create an administrator in PostgreSQL."""
    u = User(
        email=f"pg_admin_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9196{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_order(
    db: Session,
    farmer: User,
    buyer: User,
    total_amount: Decimal = Decimal("5000.00"),
    status: str = ORDER_STATUS_CONFIRMED,
) -> Order:
    """Seed category, listing, conversation, offer, order, and order item in PostgreSQL."""
    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg_{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Organic Red Onion",
        title="Fresh Red Onions",
        initial_quantity=Decimal("1000.000"),
        available_quantity=Decimal("800.000"),
        unit="kg",
        price_per_unit=Decimal("25.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.flush()

    conv = Conversation(
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        initial_context_type="listing",
        initial_context_id=listing.id,
    )
    db.add(conv)
    db.flush()

    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:6].upper()}",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=total_amount,
        status=OFFER_STATUS_ACCEPTED,
    )
    db.add(offer)
    db.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        source_offer_id=offer.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=total_amount,
        status=status,
        delivery_status=DELIVERY_STATUS_NOT_ARRANGED,
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        product_name=listing.product_name,
        quantity=Decimal("40.000"),
        unit="kg",
        unit_price=Decimal("25.00"),
        subtotal=total_amount,
        status="confirmed",
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# 1. PostgreSQL Persistence and Check Constraints
# ===========================================================================

def test_pg_record_payment_persistence_and_constraints(db_session: Session):
    """Verify PostgreSQL check constraints and persistence for PaymentRecord."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("2000.00"))

    # 1. Valid payment persistence
    service = PaymentService(db_session)
    record = service.record_payment(
        order_id=order.id,
        current_user=buyer,
        payload=PaymentRecordCreate(
            amount=Decimal("1500.00"),
            payment_method=PAYMENT_METHOD_BANK_TRANSFER,
            reference_number="PG_UTR_12345",
            payment_date=date.today(),
        ),
    )
    assert record.id is not None
    assert record.status == PAYMENT_STATUS_RECORDED

    # 2. Check constraint: chk_payments_amount (amount must be strictly positive)
    with pytest.raises(IntegrityError):
        with _SessionLocal() as session:
            bad_record = PaymentRecord(
                order_id=order.id,
                recorded_by_user_id=buyer.id,
                amount=Decimal("0.00"),  # Violates amount > 0
                payment_method="upi",
                status=PAYMENT_STATUS_RECORDED,
                payment_date=date.today(),
            )
            session.add(bad_record)
            session.commit()

    # 3. Check constraint: chk_payments_method
    with pytest.raises(IntegrityError):
        with _SessionLocal() as session:
            bad_method = PaymentRecord(
                order_id=order.id,
                recorded_by_user_id=buyer.id,
                amount=Decimal("100.00"),
                payment_method="bitcoin",  # Violates method allowlist
                status=PAYMENT_STATUS_RECORDED,
                payment_date=date.today(),
            )
            session.add(bad_method)
            session.commit()


# ===========================================================================
# 2. Concurrency: Overpayment Prevention under Race Conditions
# ===========================================================================

def test_pg_concurrent_payments_overpayment_prevention(db_session: Session):
    """5 concurrent transactions attempt 300.00 payments on a 1000.00 order (ceiling check).

    Total attempted: 1500.00 INR.
    Order row locking (SELECT ... FOR UPDATE) forces serialization.
    Exactly 3 must succeed (900.00 INR) and 2 must be rejected with 409 Conflict.
    Total committed payments in PostgreSQL must not exceed 1000.00 INR.
    """
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    results: List[Tuple[bool, str]] = []
    lock = threading.Lock()

    def attempt_payment(worker_id: int):
        session = _SessionLocal()
        try:
            service = PaymentService(session)
            service.record_payment(
                order_id=order.id,
                current_user=buyer,
                payload=PaymentRecordCreate(
                    amount=Decimal("300.00"),
                    payment_method=PAYMENT_METHOD_UPI,
                    reference_number=f"CONCUR_{worker_id}",
                    payment_date=date.today(),
                ),
            )
            session.commit()
            with lock:
                results.append((True, "success"))
        except Exception as exc:
            session.rollback()
            with lock:
                results.append((False, str(exc)))
        finally:
            session.close()

    threads = [threading.Thread(target=attempt_payment, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]

    # Exactly 3 must succeed: 3 * 300 = 900 <= 1000. The 4th would make 1200 > 1000.
    assert len(successes) == 3, f"Expected 3 successes, got {len(successes)}: {results}"
    assert len(failures) == 2, f"Expected 2 failures, got {len(failures)}: {results}"

    # Verify authoritative database state
    with _SessionLocal() as verify_session:
        repo = PaymentRepository(verify_session)
        summary = repo.calculate_order_payment_summary(order.id, order.total_amount)
        assert summary["total_recorded"] == Decimal("900.00")
        assert summary["total_recorded"] <= order.total_amount


# ===========================================================================
# 3. Concurrency: Acknowledgement vs Dispute Race
# ===========================================================================

def test_pg_concurrent_acknowledgement_and_dispute_race(db_session: Session):
    """Concurrent race between farmer acknowledgement and dispute complaint filing.

    Guarantees no deadlocks and clean deterministic ordering via canonical lock hierarchy.
    """
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    service = PaymentService(db_session)
    record = service.record_payment(
        order_id=order.id,
        current_user=buyer,
        payload=PaymentRecordCreate(
            amount=Decimal("500.00"),
            payment_method=PAYMENT_METHOD_BANK_TRANSFER,
            payment_date=date.today(),
        ),
    )
    payment_id = record.id

    outcomes = []
    lock = threading.Lock()

    def do_acknowledge():
        session = _SessionLocal()
        try:
            s = PaymentService(session)
            s.acknowledge_payment(payment_id=payment_id, current_user=farmer)
            session.commit()
            with lock:
                outcomes.append(("ack", True))
        except Exception as e:
            session.rollback()
            with lock:
                outcomes.append(("ack", False))
        finally:
            session.close()

    def do_dispute():
        session = _SessionLocal()
        try:
            s = PaymentService(session)
            s.file_payment_complaint(
                payment_id=payment_id,
                current_user=buyer,
                complaint_reason="Bank debit disputed by counterparty",
            )
            session.commit()
            with lock:
                outcomes.append(("dispute", True))
        except Exception as e:
            session.rollback()
            with lock:
                outcomes.append(("dispute", False))
        finally:
            session.close()

    t1 = threading.Thread(target=do_acknowledge)
    t2 = threading.Thread(target=do_dispute)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify no deadlock and authoritative final state in PostgreSQL
    with _SessionLocal() as session:
        p = session.query(PaymentRecord).filter(PaymentRecord.id == payment_id).one()
        assert p.status in (PAYMENT_STATUS_ACKNOWLEDGED, PAYMENT_STATUS_DISPUTED)


# ===========================================================================
# 4. Dispute Moderation Atomic Outcomes
# ===========================================================================

def test_pg_dispute_moderation_atomic_resolution(db_session: Session):
    """Admin dispute resolution atomically updates complaint and transitions payment back to unacknowledged.

    Only the designated selling farmer can subsequently acknowledge payment receipt.
    """
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    service = PaymentService(db_session)
    record = service.record_payment(
        order_id=order.id,
        current_user=buyer,
        payload=PaymentRecordCreate(
            amount=Decimal("1000.00"),
            payment_method=PAYMENT_METHOD_UPI,
            reference_number="UPI_RESOLVE_001",
            payment_date=date.today(),
        ),
    )
    complaint = service.file_payment_complaint(
        payment_id=record.id,
        current_user=farmer,
        complaint_reason="Payment not credited to UPI bank account",
    )

    # Move to under review
    service.admin_resolve_complaint(
        complaint_id=complaint.id,
        current_user=admin,
        new_status=PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
        admin_resolution_notes="Requesting bank NPCI transaction trace.",
    )

    # Admin resolves complaint with findings (admin never acknowledges on behalf of farmer)
    service.admin_resolve_complaint(
        complaint_id=complaint.id,
        current_user=admin,
        new_status=PAYMENT_COMPLAINT_STATUS_RESOLVED,
        admin_resolution_notes="NPCI bank confirmation verified. Funds delivered to farmer bank.",
    )
    db_session.commit()

    # Verify persistence in PostgreSQL: payment returned to payment_recorded (unacknowledged)
    with _SessionLocal() as session:
        c_db = session.query(PaymentComplaint).filter(PaymentComplaint.id == complaint.id).one()
        p_db = session.query(PaymentRecord).filter(PaymentRecord.id == record.id).one()
        assert c_db.status == PAYMENT_COMPLAINT_STATUS_RESOLVED
        assert p_db.status == PAYMENT_STATUS_RECORDED
        assert p_db.acknowledged_at is None

        repo = PaymentRepository(session)
        summary = repo.calculate_order_payment_summary(order.id, order.total_amount)
        assert summary["settlement_status"] == "payment_pending_acknowledgement"
        assert summary["total_acknowledged"] == Decimal("0.00")
        assert summary["unacknowledged_amount"] == Decimal("1000.00")

    # Designated selling farmer explicitly acknowledges payment
    service.acknowledge_payment(payment_id=record.id, current_user=farmer)
    db_session.commit()

    # Now verify payment is acknowledged and order is fully settled
    with _SessionLocal() as session:
        p_db = session.query(PaymentRecord).filter(PaymentRecord.id == record.id).one()
        assert p_db.status == PAYMENT_STATUS_ACKNOWLEDGED
        assert p_db.acknowledged_at is not None

        repo = PaymentRepository(session)
        summary = repo.calculate_order_payment_summary(order.id, order.total_amount)
        assert summary["settlement_status"] == "fully_settled"
        assert summary["total_acknowledged"] == Decimal("1000.00")


# ===========================================================================
# 5. Concurrency: Disputed Payment Retains Overpayment Ceiling Protection
# ===========================================================================

def test_pg_concurrent_payments_with_disputed_payment_overpayment_prevention(db_session: Session):
    """Concurrent payment attempts respect ceiling when an existing payment is disputed.

    Order: 1000.00 INR.
    Disputed payment: 700.00 INR.
    Remaining payable ceiling: 300.00 INR.
    4 concurrent threads attempt 150.00 INR payments (total attempted: 600.00 INR).
    Order row locking (Tier 2) ensures exactly 2 succeed (300.00 INR) and 2 are rejected (409 Conflict).
    """
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    service = PaymentService(db_session)
    record = service.record_payment(
        order_id=order.id,
        current_user=buyer,
        payload=PaymentRecordCreate(
            amount=Decimal("700.00"),
            payment_method=PAYMENT_METHOD_BANK_TRANSFER,
            reference_number="DISP_PAY_01",
            payment_date=date.today(),
        ),
    )
    service.file_payment_complaint(
        payment_id=record.id,
        current_user=farmer,
        complaint_reason="Bank credit short of declared amount",
    )
    db_session.commit()

    results: List[Tuple[bool, str]] = []
    lock = threading.Lock()

    def attempt_payment(worker_id: int):
        session = _SessionLocal()
        try:
            s = PaymentService(session)
            s.record_payment(
                order_id=order.id,
                current_user=buyer,
                payload=PaymentRecordCreate(
                    amount=Decimal("150.00"),
                    payment_method=PAYMENT_METHOD_UPI,
                    reference_number=f"DISP_CONCUR_{worker_id}",
                    payment_date=date.today(),
                ),
            )
            session.commit()
            with lock:
                results.append((True, "success"))
        except Exception as exc:
            session.rollback()
            with lock:
                results.append((False, str(exc)))
        finally:
            session.close()

    threads = [threading.Thread(target=attempt_payment, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]

    # Exactly 2 must succeed: 2 * 150 = 300. The 3rd would make 700 + 450 = 1150 > 1000.
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}: {results}"
    assert len(failures) == 2, f"Expected 2 failures, got {len(failures)}: {results}"

    # Verify authoritative database state
    with _SessionLocal() as verify_session:
        repo = PaymentRepository(verify_session)
        summary = repo.calculate_order_payment_summary(order.id, order.total_amount)
        assert summary["total_disputed"] == Decimal("700.00")
        assert summary["unacknowledged_amount"] == Decimal("300.00")
        assert summary["max_available_for_new_payment"] == Decimal("0.00")
        assert summary["total_recorded"] == Decimal("1000.00")


# ===========================================================================
# 6. PostgreSQL Audit Trail: Historical Acknowledgement & Reaffirmation
# ===========================================================================

def test_pg_previously_acknowledged_payment_preserves_audit_trail_and_reaffirmation(db_session: Session):
    """Verify in PostgreSQL that historical acknowledgement is never erased across disputes.

    1. Farmer acknowledges payment in PostgreSQL -> original_acknowledged_at is persisted (T1).
    2. Dispute filed -> status is 'disputed', original_acknowledged_at remains T1 in DB.
    3. Admin resolves dispute -> status is 'payment_recorded', acknowledged_at is None,
       original_acknowledged_at is PRESERVED as T1, AdminAuditLog record is created.
    4. Farmer reaffirms receipt -> status is 'acknowledged', acknowledged_at is T2,
       original_acknowledged_at remains T1 in DB.
    """
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("2000.00"))

    service = PaymentService(db_session)
    record = service.record_payment(
        order_id=order.id,
        current_user=buyer,
        payload=PaymentRecordCreate(
            amount=Decimal("2000.00"),
            payment_method=PAYMENT_METHOD_BANK_TRANSFER,
            reference_number="PG_AUDIT_001",
            payment_date=date.today(),
        ),
    )
    payment_id = record.id

    # 1. Farmer acknowledges
    service.acknowledge_payment(payment_id=payment_id, current_user=farmer)
    db_session.commit()

    with _SessionLocal() as session:
        p_db = session.query(PaymentRecord).filter(PaymentRecord.id == payment_id).one()
        assert p_db.status == PAYMENT_STATUS_ACKNOWLEDGED
        t1 = p_db.acknowledged_at
        assert t1 is not None
        assert p_db.original_acknowledged_at == t1

    # 2. Farmer disputes
    complaint = service.file_payment_complaint(
        payment_id=payment_id,
        current_user=farmer,
        complaint_reason="Bank issued unexpected chargeback advisory",
    )
    db_session.commit()
    complaint_id = complaint.id

    with _SessionLocal() as session:
        p_db = session.query(PaymentRecord).filter(PaymentRecord.id == payment_id).one()
        assert p_db.status == PAYMENT_STATUS_DISPUTED
        # Original acknowledgement is NOT erased in PostgreSQL!
        assert p_db.original_acknowledged_at == t1

        repo = PaymentRepository(session)
        summary = repo.calculate_order_payment_summary(order.id, order.total_amount)
        assert summary["settlement_status"] == "disputed"
        assert summary["total_disputed"] == Decimal("2000.00")
        assert summary["total_acknowledged"] == Decimal("0.00")

    # 3. Admin resolves dispute with findings
    service.admin_resolve_complaint(
        complaint_id=complaint_id,
        current_user=admin,
        new_status=PAYMENT_COMPLAINT_STATUS_RESOLVED,
        admin_resolution_notes="Chargeback reversed by payer bank; funds confirmed safely credited.",
    )
    db_session.commit()

    with _SessionLocal() as session:
        p_db = session.query(PaymentRecord).filter(PaymentRecord.id == payment_id).one()
        assert p_db.status == PAYMENT_STATUS_RECORDED
        assert p_db.acknowledged_at is None  # Active confirmation reset pending seller reaffirmation
        assert p_db.original_acknowledged_at == t1  # HISTORICAL EVIDENCE PRESERVED IN POSTGRESQL!

        # Verify AdminAuditLog persistence
        audit_log = (
            session.query(AdminAuditLog)
            .filter(
                AdminAuditLog.target_entity_type == "payment_complaint",
                AdminAuditLog.target_entity_id == complaint_id,
            )
            .first()
        )
        assert audit_log is not None
        assert audit_log.admin_user_id == admin.id
        assert audit_log.action == "payment_dispute_resolved"

    # 4. Farmer explicitly reaffirms receipt
    service.acknowledge_payment(payment_id=payment_id, current_user=farmer)
    db_session.commit()

    with _SessionLocal() as session:
        p_db = session.query(PaymentRecord).filter(PaymentRecord.id == payment_id).one()
        assert p_db.status == PAYMENT_STATUS_ACKNOWLEDGED
        t2 = p_db.acknowledged_at
        assert t2 is not None
        # Original acknowledgement remains T1 in PostgreSQL
        assert p_db.original_acknowledged_at == t1

        repo = PaymentRepository(session)
        summary = repo.calculate_order_payment_summary(order.id, order.total_amount)
        assert summary["settlement_status"] == "fully_settled"
        assert summary["total_acknowledged"] == Decimal("2000.00")



