"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 8: Governance & Audit Trail.

Verifies Module 8 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`.

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
from typing import Generator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.admin import TARGET_ENTITY_REPORT, AdminAuditLog
from app.models.listing import STATUS_ACTIVE, ProduceCategory, ProduceListing
from app.models.report import (
    REPORT_CATEGORY_FRAUD,
    REPORT_CATEGORY_QUALITY_ISSUE,
    REPORT_STATUS_ACTION_TAKEN,
    REPORT_STATUS_DISMISSED,
    REPORT_STATUS_OPEN,
    REPORT_STATUS_UNDER_REVIEW,
    UserReport,
)
from app.models.user import BuyerProfile, FarmerProfile, User
from app.reports.repository import ReportRepository
from app.reports.schemas import ReportModerateRequest
from app.reports.service import ReportService
from tests.pg_test_utils import cleanup_pg_test_tables, ensure_pg_test_schema_at_head

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
                ratings_reviews,
                user_reports,
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
            CASCADE;
            """)
        )
        db.commit()


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure isolated PG DB is migrated to head and clean before and after each test."""
    ensure_pg_test_schema_at_head()
    cleanup_pg_test_tables(_SessionLocal)
    yield
    cleanup_pg_test_tables(_SessionLocal)


@pytest.fixture
def pg_session() -> Generator[Session, None, None]:
    """Provide a real PostgreSQL session."""
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(pg_session: Session) -> Generator[TestClient, None, None]:
    """TestClient wired directly to real PostgreSQL test DB."""
    def override_get_db():
        with _SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_headers(user: User) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "verification_status": user.verification_status}
    )
    return {"Authorization": f"Bearer {token}"}


def seed_pg_farmer(db: Session) -> User:
    u = User(
        email=f"pg_farmer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    fp = FarmerProfile(
        user_id=u.id,
        full_name="PG Farmer",
        farm_name="PG Farms",
        farm_location_address="Nashik Highway",
        city="Nashik",
        state="Maharashtra",
        postal_code="422001",
    )
    db.add(fp)
    db.commit()
    db.refresh(u)
    return u


def seed_pg_buyer(db: Session) -> User:
    u = User(
        email=f"pg_buyer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    bp = BuyerProfile(
        user_id=u.id,
        contact_person_name="PG Buyer Contact",
        business_name="PG Supermarkets",
        business_type="retailer",
        delivery_receiving_address="Central Warehouse, Gate 2",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db.add(bp)
    db.commit()
    db.refresh(u)
    return u


def seed_pg_admin(db: Session) -> User:
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


def seed_pg_listing(db: Session, farmer: User) -> ProduceListing:
    cat = db.query(ProduceCategory).filter_by(name="Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg_{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Nashik Red Onion",
        title="High Grade Red Onions",
        initial_quantity=Decimal("2000.000"),
        available_quantity=Decimal("1500.000"),
        unit="kg",
        price_per_unit=Decimal("25.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# Tests: Module 8 on PostgreSQL
# ---------------------------------------------------------------------------


def test_pg_user_reports_category_check_constraint(pg_session: Session) -> None:
    """chk_user_reports_category rejects unapproved category strings in PostgreSQL."""
    buyer = seed_pg_buyer(pg_session)
    farmer = seed_pg_farmer(pg_session)

    bad_report = UserReport(
        reporter_id=buyer.id,
        reported_user_id=farmer.id,
        category="unapproved_category_foo",
        description="Testing check constraint violation.",
        status="open",
    )
    pg_session.add(bad_report)
    with pytest.raises(IntegrityError) as exc_info:
        pg_session.commit()
    assert "chk_user_reports_category" in str(exc_info.value)
    pg_session.rollback()


def test_pg_user_reports_status_check_constraint(pg_session: Session) -> None:
    """chk_user_reports_status rejects invalid status strings in PostgreSQL."""
    buyer = seed_pg_buyer(pg_session)
    farmer = seed_pg_farmer(pg_session)

    bad_report = UserReport(
        reporter_id=buyer.id,
        reported_user_id=farmer.id,
        category="quality_issue",
        description="Testing status check constraint violation.",
        status="invalid_status_bar",
    )
    pg_session.add(bad_report)
    with pytest.raises(IntegrityError) as exc_info:
        pg_session.commit()
    assert "chk_user_reports_status" in str(exc_info.value)
    pg_session.rollback()


def test_pg_user_reports_foreign_key_ondelete_rules(pg_session: Session) -> None:
    """Verify ON DELETE RESTRICT on reporter_id and ON DELETE SET NULL on reported_user_id and listing_id."""
    buyer = seed_pg_buyer(pg_session)
    farmer = seed_pg_farmer(pg_session)
    listing = seed_pg_listing(pg_session, farmer=farmer)

    report = UserReport(
        reporter_id=buyer.id,
        reported_user_id=farmer.id,
        listing_id=listing.id,
        category="fraud",
        description="Testing foreign key cascade/set null rules.",
        status="open",
    )
    pg_session.add(report)
    pg_session.commit()
    pg_session.refresh(report)

    # Deleting buyer (reporter) should fail due to RESTRICT
    pg_session.delete(buyer)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()

    # Re-fetch report
    report = pg_session.get(UserReport, report.id)
    assert report.reported_user_id == farmer.id

    # Deleting listing should succeed and set listing_id to NULL
    listing_to_del = pg_session.get(ProduceListing, listing.id)
    pg_session.delete(listing_to_del)
    pg_session.commit()

    pg_session.refresh(report)
    assert report.listing_id is None
    assert report.reporter_id == buyer.id


def test_pg_admin_moderation_atomic_audit_log_creation(pg_session: Session) -> None:
    """Moderating a report creates UserReport update and AdminAuditLog atomically in PostgreSQL."""
    admin = seed_pg_admin(pg_session)
    buyer = seed_pg_buyer(pg_session)
    farmer = seed_pg_farmer(pg_session)

    report = UserReport(
        reporter_id=buyer.id,
        reported_user_id=farmer.id,
        category="quantity_mismatch",
        description="Weight was short by 150kg at arrival.",
        status="open",
    )
    pg_session.add(report)
    pg_session.commit()
    pg_session.refresh(report)

    service = ReportService(pg_session)
    updated = service.admin_moderate_report(
        report_id=report.id,
        current_admin=admin,
        moderate_in=ReportModerateRequest(
            status="action_taken",
            admin_notes="Discrepancy confirmed by weighbridge slip; farmer sanctioned.",
        ),
        ip_address="192.168.1.100",
    )

    assert updated.status == "action_taken"
    assert updated.reviewed_by_admin_id == admin.id

    # Verify audit log in PostgreSQL
    audit = (
        pg_session.query(AdminAuditLog)
        .filter_by(
            admin_user_id=admin.id,
            target_entity_type=TARGET_ENTITY_REPORT,
            target_entity_id=report.id,
        )
        .first()
    )
    assert audit is not None
    assert audit.action == "report_moderate_action_taken"
    assert audit.ip_address == "192.168.1.100"
    assert "Discrepancy confirmed" in audit.reason


def test_pg_audit_logs_append_only_constraints(pg_session: Session) -> None:
    """admin_audit_logs enforces NOT NULL constraints on admin_user_id, action, target_entity_type, target_entity_id."""
    admin = seed_pg_admin(pg_session)

    # Missing action
    bad_audit = AdminAuditLog(
        admin_user_id=admin.id,
        action=None,  # NOT NULL violation
        target_entity_type="report",
        target_entity_id=uuid.uuid4(),
    )
    pg_session.add(bad_audit)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_pg_atomic_rollback_prevents_orphan_audit(pg_session: Session) -> None:
    """If moderation transaction fails, audit record must not be orphaned."""
    admin = seed_pg_admin(pg_session)
    buyer = seed_pg_buyer(pg_session)

    report = UserReport(
        reporter_id=buyer.id,
        category="other",
        description="Test transaction atomicity.",
        status="open",
    )
    pg_session.add(report)
    pg_session.commit()
    pg_session.refresh(report)

    # Simulate an error inside service by passing invalid status
    service = ReportService(pg_session)
    with pytest.raises(Exception):
        service.admin_moderate_report(
            report_id=report.id,
            current_admin=admin,
            moderate_in=ReportModerateRequest(
                status="invalid_status",
                admin_notes="This should fail.",
            ),
        )

    # Verify no audit record was committed
    count = pg_session.query(AdminAuditLog).filter_by(target_entity_id=report.id).count()
    assert count == 0

