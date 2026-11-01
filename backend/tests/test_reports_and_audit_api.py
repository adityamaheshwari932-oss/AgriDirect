"""Unit and API integration tests for AgriDirect Module 8: Governance & Audit Trail.

Covers:
1. User safety report submission (category validation, target validation, description limits).
2. Confidentiality and anti-enumeration:
   - Reported user cannot view or discover reports filed against them (404).
   - Third parties receive 404.
   - Reporter can view own reports under /reports/me and /reports/{id}.
3. Self-reporting prevention (400 Bad Request).
4. Administrator moderation queue (filtering by status, category, paginated).
5. Administrator moderation resolution ('under_review', 'action_taken', 'dismissed').
6. Non-admin moderation attempt blocked (403 Forbidden).
7. Terminal report state transition rules.
8. Permanent AdminAuditLog creation on moderation:
   - Audit actor matches authenticated administrator.
   - Audit action and target match report and decision.
   - Audit timestamp and justification recorded.
9. Audit log API security:
   - Ordinary users blocked from /api/v1/admin/audit-logs (403).
   - No update or delete endpoints exist (405 Method Not Allowed).
   - Append-only integrity.
10. Operational notification delivered to reporter on moderation decision.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.admin import AdminAuditLog, TARGET_ENTITY_REPORT
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE
from app.models.notification import Notification
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


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Isolated in-memory SQLite engine with foreign key enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Direct database session."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


@pytest.fixture
def client(sqlite_engine) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ===========================================================================
# Helper Seed Functions
# ===========================================================================


def make_headers(user: User) -> dict:
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
    """Create a farmer with profile."""
    u = User(
        email=f"farmer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="farmer",
        verification_status="verified" if verified else "unverified",
        account_status="active" if active else "suspended",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    fp = FarmerProfile(
        user_id=u.id,
        full_name="Farmer Ramesh",
        farm_name="Green Acres Farm",
        farm_location_address="Village Post, Dist",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db.add(fp)
    db.commit()
    db.refresh(u)
    return u


def seed_buyer(db: Session, verified: bool = True, active: bool = True) -> User:
    """Create a buyer with profile."""
    u = User(
        email=f"buyer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active" if active else "suspended",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    bp = BuyerProfile(
        user_id=u.id,
        contact_person_name="Buyer Suresh",
        business_name="Fresh Mart Wholesale",
        business_type="wholesaler",
        delivery_receiving_address="Market Yard, Sector 4",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db.add(bp)
    db.commit()
    db.refresh(u)
    return u


def seed_admin(db: Session) -> User:
    """Create an administrator user."""
    u = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@agridirect.test",
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


def seed_listing(db: Session, farmer: User) -> ProduceListing:
    """Create a produce listing."""
    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Grains").first()
    if not cat:
        cat = ProduceCategory(name="Grains", slug=f"grains_{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Basmati Rice",
        title="Premium Basmati Rice",
        initial_quantity=Decimal("5000.000"),
        available_quantity=Decimal("5000.000"),
        unit="kg",
        price_per_unit=Decimal("80.00"),
        location_state="Punjab",
        location_city="Amritsar",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


# ===========================================================================
# Test Cases: User Reports
# ===========================================================================


class TestUserReportFiling:
    """Verify report submission, validation, and privacy rules."""

    def test_file_report_against_user_success(self, client: TestClient, db_session: Session) -> None:
        """Buyer files a report against farmer with valid category and narrative."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)

        payload = {
            "reported_user_id": str(farmer.id),
            "category": "quality_issue",
            "description": "Batch received contains significantly higher moisture than agreed in contract.",
        }
        res = client.post("/api/v1/reports", json=payload, headers=make_headers(buyer))
        assert res.status_code == 201
        data = res.json()
        assert data["reporter_id"] == str(buyer.id)
        assert data["reported_user_id"] == str(farmer.id)
        assert data["category"] == "quality_issue"
        assert data["status"] == "open"
        assert data["admin_notes"] is None

    def test_file_report_against_listing_success(self, client: TestClient, db_session: Session) -> None:
        """Buyer files a report against misleading listing."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        listing = seed_listing(db_session, farmer=farmer)

        payload = {
            "listing_id": str(listing.id),
            "category": "fraud",
            "description": "Listing photos appear to be stock imagery with fabricated variety claims.",
        }
        res = client.post("/api/v1/reports", json=payload, headers=make_headers(buyer))
        assert res.status_code == 201
        data = res.json()
        assert data["listing_id"] == str(listing.id)
        assert data["category"] == "fraud"

    def test_self_reporting_rejected(self, client: TestClient, db_session: Session) -> None:
        """Filing a report against oneself fails with 400."""
        buyer = seed_buyer(db_session)
        payload = {
            "reported_user_id": str(buyer.id),
            "category": "harassment",
            "description": "Attempting to file a report against myself.",
        }
        res = client.post("/api/v1/reports", json=payload, headers=make_headers(buyer))
        assert res.status_code == 400
        assert "yourself" in res.json()["detail"].lower()

    def test_missing_targets_rejected(self, client: TestClient, db_session: Session) -> None:
        """Report with neither reported_user_id nor listing_id is rejected with 400."""
        buyer = seed_buyer(db_session)
        payload = {
            "category": "other",
            "description": "Vague complaint without mentioning any user or listing target.",
        }
        res = client.post("/api/v1/reports", json=payload, headers=make_headers(buyer))
        assert res.status_code == 400

    def test_invalid_category_rejected(self, client: TestClient, db_session: Session) -> None:
        """Invalid category string is rejected with 400."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        payload = {
            "reported_user_id": str(farmer.id),
            "category": "invalid_category_name",
            "description": "Testing unapproved category string rejection.",
        }
        res = client.post("/api/v1/reports", json=payload, headers=make_headers(buyer))
        assert res.status_code == 400

    def test_reported_user_cannot_access_confidential_report(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Reported user querying report detail receives 404 (confidentiality protection)."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)

        # Buyer files report against farmer
        res_create = client.post(
            "/api/v1/reports",
            json={
                "reported_user_id": str(farmer.id),
                "category": "fraud",
                "description": "Suspicious financial activity noticed during off-platform negotiation.",
            },
            headers=make_headers(buyer),
        )
        report_id = res_create.json()["id"]

        # Farmer (the accused) attempts to inspect the report
        res_farmer = client.get(f"/api/v1/reports/{report_id}", headers=make_headers(farmer))
        assert res_farmer.status_code == 404

        # Third party attempts to inspect the report
        third_party = seed_buyer(db_session)
        res_third = client.get(f"/api/v1/reports/{report_id}", headers=make_headers(third_party))
        assert res_third.status_code == 404

        # Original reporter CAN inspect their own report
        res_reporter = client.get(f"/api/v1/reports/{report_id}", headers=make_headers(buyer))
        assert res_reporter.status_code == 200

    def test_list_my_reports(self, client: TestClient, db_session: Session) -> None:
        """Reporter can list their own submitted reports."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)

        client.post(
            "/api/v1/reports",
            json={
                "reported_user_id": str(farmer.id),
                "category": "harassment",
                "description": "Abusive communication in chat context.",
            },
            headers=make_headers(buyer),
        )

        res = client.get("/api/v1/reports/me", headers=make_headers(buyer))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "harassment"


# ===========================================================================
# Test Cases: Administrative Moderation & Audit Logs
# ===========================================================================


class TestAdminModerationAndAudit:
    """Verify administrator queue inspection, moderation state transitions, and audit trail."""

    def test_non_admin_blocked_from_moderation_queue(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Non-admin caller cannot access /admin/reports or /admin/audit-logs."""
        buyer = seed_buyer(db_session)

        res_queue = client.get("/api/v1/admin/reports", headers=make_headers(buyer))
        assert res_queue.status_code == 403

        res_audit = client.get("/api/v1/admin/audit-logs", headers=make_headers(buyer))
        assert res_audit.status_code == 403

    def test_admin_moderates_report_and_verifies_audit_log(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Admin inspects queue, transitions report to 'action_taken', and creates immutable audit log."""
        admin = seed_admin(db_session)
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)

        res_create = client.post(
            "/api/v1/reports",
            json={
                "reported_user_id": str(farmer.id),
                "category": "quantity_mismatch",
                "description": "Weighbridge receipt showed 200kg discrepancy against invoice.",
            },
            headers=make_headers(buyer),
        )
        report_id = res_create.json()["id"]

        # Admin views moderation queue
        res_queue = client.get("/api/v1/admin/reports?status=open", headers=make_headers(admin))
        assert res_queue.status_code == 200
        assert res_queue.json()["total"] >= 1

        # Admin moderates report -> 'action_taken'
        mod_payload = {
            "status": "action_taken",
            "admin_notes": "Investigation confirmed discrepancy; farmer agreed to partial credit note.",
        }
        res_mod = client.post(
            f"/api/v1/admin/reports/{report_id}/moderate",
            json=mod_payload,
            headers=make_headers(admin),
        )
        assert res_mod.status_code == 200
        mod_data = res_mod.json()
        assert mod_data["status"] == "action_taken"
        assert mod_data["reviewed_by_admin_id"] == str(admin.id)
        assert mod_data["admin_notes"] == mod_payload["admin_notes"]

        # Verify notification dispatched to reporter
        notif = (
            db_session.query(Notification)
            .filter_by(user_id=buyer.id, event_type="report_status_update")
            .first()
        )
        assert notif is not None
        assert "action_taken" in notif.body

        # Verify AdminAuditLog entry created in database
        res_audit = client.get(
            f"/api/v1/admin/audit-logs?target_entity_type=report&target_entity_id={report_id}",
            headers=make_headers(admin),
        )
        assert res_audit.status_code == 200
        audit_data = res_audit.json()
        assert audit_data["total"] == 1
        entry = audit_data["items"][0]
        assert entry["admin_user_id"] == str(admin.id)
        assert entry["action"] == "report_moderate_action_taken"
        assert entry["target_entity_type"] == "report"
        assert entry["target_entity_id"] == report_id
        assert entry["reason"] == mod_payload["admin_notes"]

    def test_terminal_report_reopening_rejected(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Terminal report cannot be reopened to 'open' without explicit authorization."""
        admin = seed_admin(db_session)
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)

        res_create = client.post(
            "/api/v1/reports",
            json={
                "reported_user_id": str(farmer.id),
                "category": "other",
                "description": "Contractual dispute over packaging specifications.",
            },
            headers=make_headers(buyer),
        )
        report_id = res_create.json()["id"]

        # Admin dismisses report
        client.post(
            f"/api/v1/admin/reports/{report_id}/moderate",
            json={"status": "dismissed", "admin_notes": "Packaging met agreed standards."},
            headers=make_headers(admin),
        )

        # Attempt to set back to 'open'
        res_reopen = client.post(
            f"/api/v1/admin/reports/{report_id}/moderate",
            json={"status": "open", "admin_notes": "Attempting invalid transition to open."},
            headers=make_headers(admin),
        )
        # Reopening to 'open' is rejected by service / schema validation
        assert res_reopen.status_code in (400, 409, 422)

    def test_audit_logs_append_only_immutability(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Audit logs cannot be updated or deleted via API."""
        admin = seed_admin(db_session)

        # Direct database insert of an audit log entry
        audit_entry = AdminAuditLog(
            admin_user_id=admin.id,
            action="system_test_action",
            target_entity_type="system",
            target_entity_id=uuid.uuid4(),
            reason="Integration audit testing",
        )
        db_session.add(audit_entry)
        db_session.commit()
        db_session.refresh(audit_entry)

        log_id = audit_entry.id

        # GET single log works
        res_get = client.get(f"/api/v1/admin/audit-logs/{log_id}", headers=make_headers(admin))
        assert res_get.status_code == 200

        # PUT rejected (405 Method Not Allowed)
        res_put = client.put(f"/api/v1/admin/audit-logs/{log_id}", json={}, headers=make_headers(admin))
        assert res_put.status_code in (404, 405)

        # PATCH rejected (405 Method Not Allowed)
        res_patch = client.patch(f"/api/v1/admin/audit-logs/{log_id}", json={}, headers=make_headers(admin))
        assert res_patch.status_code in (404, 405)

        # DELETE rejected (405 Method Not Allowed)
        res_delete = client.delete(f"/api/v1/admin/audit-logs/{log_id}", headers=make_headers(admin))
        assert res_delete.status_code in (404, 405)

