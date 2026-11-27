"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 10:
Administrative User Moderation & Platform Governance.

Verifies Module 10 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`.

Safety Guarantees:
- Uses ONLY `agridirect_module3_test`.
- Strictly NEVER touches, accesses, or modifies `agridirect_db`.
- Pre-flight database name assertion on every test execution.
- Auto-clean up via TRUNCATE CASCADE with complete isolation.
- Real PostgreSQL row-level locking (SELECT ... FOR UPDATE) and concurrency verification.
"""

import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from tests.pg_test_utils import cleanup_pg_test_tables, ensure_pg_test_schema_at_head

from app.admin.schemas import (
    AdminListingModerateRequest,
    AdminUserStatusUpdateRequest,
)
from app.admin.service import (
    AdminCatalogModerationService,
    AdminUserModerationService,
)
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.admin import AdminAuditLog
from app.models.listing import ProduceCategory, ProduceListing
from app.models.notification import Notification
from app.models.report import UserReport
from app.models.requirement import BuyerRequirement
from app.models.user import BuyerProfile, FarmerProfile, User

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
# Seed Helpers
# ---------------------------------------------------------------------------


def make_headers(user: User) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "status": user.verification_status}
    )
    return {"Authorization": f"Bearer {token}"}


def seed_pg_farmer(db: Session, name_suffix: str = "") -> User:
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
        full_name=f"PG Farmer {name_suffix}".strip(),
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


def seed_pg_buyer(db: Session, name_suffix: str = "") -> User:
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
        contact_person_name=f"PG Buyer {name_suffix}".strip(),
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


def seed_pg_admin(db: Session, email_prefix: str = "pg_admin") -> User:
    u = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:8]}@agridirect.test",
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


def seed_pg_category(db: Session, name: str = "Vegetables") -> ProduceCategory:
    cat = ProduceCategory(name=name, slug=f"{name.lower()}-{uuid.uuid4().hex[:6]}")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def seed_pg_listing(
    db: Session,
    farmer: User,
    category: ProduceCategory,
    product_name: str = "Onions",
    status: str = "active",
    initial_qty: Decimal = Decimal("1000.00"),
    available_qty: Decimal = Decimal("1000.00"),
) -> ProduceListing:
    now_utc = datetime.now(timezone.utc)
    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=category.id,
        product_name=product_name,
        title=f"Fresh {product_name}",
        initial_quantity=initial_qty,
        available_quantity=available_qty,
        unit="kg",
        price_per_unit=Decimal("25.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        status=status,
        harvest_date=date.today(),
        available_from=date.today(),
        expires_at=now_utc + timedelta(days=14),
        created_at=now_utc,
        updated_at=now_utc,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------


class TestPostgresAdminSafety:
    """Verify safety guarantees against PostgreSQL test database."""

    def test_safety_check_connects_only_to_test_db(self, pg_session: Session):
        db_name = pg_session.execute(text("SELECT current_database()")).scalar()
        assert db_name == "agridirect_module3_test"
        assert db_name != "agridirect_db"


class TestPostgresLastAdminConcurrency:
    """Verify deterministic row-level locking and race prevention for last active admin."""

    def test_concurrent_mutual_admin_suspension_race(self, pg_session: Session):
        """Two active admins attempt to suspend each other concurrently.

        With deterministic ascending ID row locking, one transaction evaluates first and
        suspends the other. The second transaction blocks, re-evaluates remaining active admins,
        detects that only 1 active admin remains, and returns HTTP 409 Conflict.
        Zero deadlocks occur and the platform never loses its last active administrator.
        """
        admin1 = seed_pg_admin(pg_session, email_prefix="admin_alpha")
        admin2 = seed_pg_admin(pg_session, email_prefix="admin_beta")

        barrier = threading.Barrier(2)
        results = {}

        def thread_moderate(actor: User, target: User, thread_id: str):
            with _SessionLocal() as db:
                service = AdminUserModerationService(db)
                req = AdminUserStatusUpdateRequest(
                    account_status="suspended",
                    reason="Mutual concurrent administrative suspension race condition test",
                )
                barrier.wait()
                try:
                    resp = service.update_user_status(
                        user_id=target.id,
                        current_admin=actor,
                        payload=req,
                    )
                    results[thread_id] = ("success", resp.new_status)
                except Exception as ex:
                    status_code = getattr(ex, "status_code", None)
                    detail = getattr(ex, "detail", str(ex))
                    results[thread_id] = ("error", status_code, detail)

        t1 = threading.Thread(target=thread_moderate, args=(admin1, admin2, "t1"))
        t2 = threading.Thread(target=thread_moderate, args=(admin2, admin1, "t2"))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Assert no thread hung
        assert not t1.is_alive()
        assert not t2.is_alive()

        statuses = [res[0] for res in results.values()]
        assert "success" in statuses
        assert "error" in statuses

        error_res = next(res for res in results.values() if res[0] == "error")
        assert error_res[1] == 409
        assert "Cannot suspend, restrict, or block the platform's last active administrator" in error_res[2]

        # Verify database state: exactly 1 active admin remains
        with _SessionLocal() as db:
            active_admins = (
                db.query(User)
                .filter(User.role == "admin", User.account_status == "active")
                .count()
            )
            assert active_admins == 1


class TestPostgresCatalogModerationConcurrency:
    """Verify concurrency safety on produce listings and buyer requirements."""

    def test_concurrent_listing_close_and_remove(self, pg_session: Session):
        """Two admins concurrently attempt to moderate the same listing.

        Row-level locking serializes updates; second transaction fails idempotency check.
        """
        admin1 = seed_pg_admin(pg_session, email_prefix="admin_m1")
        admin2 = seed_pg_admin(pg_session, email_prefix="admin_m2")
        farmer = seed_pg_farmer(pg_session)
        cat = seed_pg_category(pg_session)
        listing = seed_pg_listing(pg_session, farmer, cat)

        barrier = threading.Barrier(2)
        results = {}

        def thread_action(actor: User, action: str, thread_id: str):
            with _SessionLocal() as db:
                service = AdminCatalogModerationService(db)
                req = AdminListingModerateRequest(
                    action=action,
                    reason="Concurrent moderation race condition verification test",
                )
                barrier.wait()
                try:
                    resp = service.moderate_listing(
                        listing_id=listing.id,
                        current_admin=actor,
                        payload=req,
                    )
                    results[thread_id] = ("success", resp.action)
                except Exception as ex:
                    import traceback
                    traceback.print_exc()
                    status_code = getattr(ex, "status_code", None)
                    detail = getattr(ex, "detail", str(ex))
                    results[thread_id] = ("error", status_code, detail)

        t1 = threading.Thread(target=thread_action, args=(admin1, "close", "t1"))
        t2 = threading.Thread(target=thread_action, args=(admin2, "close", "t2"))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not t1.is_alive()
        assert not t2.is_alive()

        statuses = [res[0] for res in results.values()]
        assert "success" in statuses
        assert "error" in statuses

        error_res = next(res for res in results.values() if res[0] == "error")
        assert error_res[1] == 400
        assert "Listing is already closed" in error_res[2]


class TestPostgresTransactionAtomicity:
    """Verify atomic persistence of user status, audit log, and in-app notification."""

    def test_atomic_status_update_audit_and_notification(self, pg_session: Session):
        admin = seed_pg_admin(pg_session)
        farmer = seed_pg_farmer(pg_session)

        with _SessionLocal() as db:
            service = AdminUserModerationService(db)
            reason = "Account suspended due to documented breach of contract"
            req = AdminUserStatusUpdateRequest(account_status="suspended", reason=reason)
            resp = service.update_user_status(
                user_id=farmer.id,
                current_admin=admin,
                payload=req,
                ip_address="192.168.1.100",
            )
            assert resp.new_status == "suspended"

        # Assert in a fresh session that all 3 records exist
        with _SessionLocal() as db:
            u = db.query(User).filter(User.id == farmer.id).one()
            assert u.account_status == "suspended"

            audit = db.query(AdminAuditLog).filter(AdminAuditLog.target_entity_id == farmer.id).one()
            assert audit.admin_user_id == admin.id
            assert audit.action == "user_status_suspended"
            assert audit.ip_address == "192.168.1.100"
            assert reason in audit.reason

            notif = db.query(Notification).filter(Notification.user_id == farmer.id).one()
            assert notif.event_type == "account_status_changed"
            assert reason in notif.body
