"""Unit and integration tests for Transporter Verification workflow:
- Transporter verification submission
- Transporter document uploads (RC, driving license, permit, insurance, fitness)
- Validation of document types, signatures, and size limits
- Duplicate submission prevention and multi-tenant isolation
- Admin queue filtering by role='transporter'
- Admin approval with atomic status updates, audit logging, and notifications
- Admin rejection with mandatory reason and history preservation
- Resubmission workflow after rejection
- Marketplace restriction enforcement on unverified transporters
"""

import io
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.admin import ACTION_VERIFY_APPROVE, AdminAuditLog
from app.models.chat import Conversation
from app.models.notification import Notification
from app.models.offer import Offer
from app.models.order import Order
from app.models.user import (
    FarmerProfile,
    ServiceArea,
    TransporterProfile,
    User,
)

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database."""
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
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Provide a direct database session for test fixture creation."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


@pytest.fixture
def isolated_upload_dir(tmp_path, monkeypatch):
    """Configure an isolated temporary directory for document uploads."""
    upload_path = tmp_path / "verification_uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(upload_path))
    monkeypatch.setattr(settings, "max_upload_size_bytes", 10 * 1024 * 1024)
    return upload_path


@pytest.fixture
def client(sqlite_engine, isolated_upload_dir) -> TestClient:
    """Provide a TestClient with overridden get_db dependency."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unverified_transporter(db_session: Session) -> User:
    """Create an active, unverified transporter user with profile and service area."""
    user = User(
        email="transporter.test@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="transporter",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543220",
    )
    profile = TransporterProfile(
        user=user,
        business_name="Kisan Fast Logistics",
        contact_name="Vikram Singh",
        phone_number="+919876543220",
        transport_type="refrigerated",
        vehicle_capacity_kg=Decimal("5000.00"),
        vehicle_registration_number="MH-15-TC-1234",
        is_available=True,
        experience_years=6,
        operating_states="Maharashtra, Gujarat",
        bio="Specialized temperature controlled agricultural haulage.",
    )
    area = ServiceArea(
        transporter_profile=profile,
        state="Maharashtra",
        district="Nashik",
        coverage_type="both",
        is_active=True,
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.add(area)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_transporter(db_session: Session) -> User:
    """Create a second transporter for multi-tenant isolation tests."""
    user = User(
        email="transporter2.test@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="transporter",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543221",
    )
    profile = TransporterProfile(
        user=user,
        business_name="Sahyadri Express Transport",
        contact_name="Deepak Patil",
        phone_number="+919876543221",
        transport_type="open_body",
        vehicle_capacity_kg=Decimal("8000.00"),
        vehicle_registration_number="MH-12-AB-9876",
        is_available=True,
        experience_years=4,
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def verified_farmer(db_session: Session) -> User:
    """Create a verified farmer user."""
    user = User(
        email="farmer.owner@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543222",
    )
    profile = FarmerProfile(
        user=user,
        full_name="Balasaheb Patil",
        farm_name="Patil Agro Farms",
        farm_location_address="Gat 44, Dindori",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def verified_buyer(db_session: Session) -> User:
    """Create a verified buyer user."""
    user = User(
        email="buyer.owner@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543224",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an administrator user."""
    user = User(
        email="admin.transporter@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543223",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    """Generate Authorization header for a user."""
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def sample_pdf_content() -> bytes:
    """Generate dummy valid PDF content matching %PDF- magic bytes."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< >>\nstartxref\n99\n%%EOF"


def sample_jpeg_content() -> bytes:
    """Generate dummy valid JPEG content matching \xff\xd8\xff magic bytes."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"


# ===========================================================================
# 1. Transporter Verification Submission Tests
# ===========================================================================


def test_transporter_submits_valid_application(client: TestClient, db_session: Session, unverified_transporter: User):
    """Transporter submits verification application; transitions to pending, creates notification."""
    headers = auth_headers(unverified_transporter)
    payload = {"submission_notes": "Submitting commercial fleet RC and national carriage permits."}

    response = client.post("/api/v1/users/me/verification", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "pending"
    assert data["user_id"] == str(unverified_transporter.id)
    assert data["submission_notes"] == payload["submission_notes"]
    assert data["reviewed_by_admin_id"] is None
    assert data["rejection_reason"] is None

    # Check user verification_status updated in DB
    db_session.expire_all()
    user_in_db = db_session.get(User, unverified_transporter.id)
    assert user_in_db.verification_status == "pending"

    # Notification created
    notifications = db_session.query(Notification).filter(Notification.user_id == unverified_transporter.id).all()
    assert len(notifications) == 1
    assert "Submitted" in notifications[0].title


def test_transporter_duplicate_submission_conflict(client: TestClient, unverified_transporter: User):
    """Submitting a second application while one is already pending returns 409 Conflict."""
    headers = auth_headers(unverified_transporter)
    res1 = client.post("/api/v1/users/me/verification", json={"submission_notes": "First attempt"}, headers=headers)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/users/me/verification", json={"submission_notes": "Second attempt"}, headers=headers)
    assert res2.status_code == 409
    assert "already have an active verification submission" in res2.json()["detail"]


# ===========================================================================
# 2. Transporter Document Upload Tests
# ===========================================================================


def test_transporter_uploads_valid_documents(client: TestClient, unverified_transporter: User):
    """Transporter uploads vehicle_rc, driving_license, and transport_permit successfully."""
    headers = auth_headers(unverified_transporter)

    # 1. Upload Vehicle Registration Certificate (RC)
    pdf_bytes = sample_pdf_content()
    files = {"file": ("vehicle_rc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"document_type": "vehicle_rc", "document_number": "MH15TC1234"}

    res = client.post("/api/v1/users/me/verification/documents", files=files, data=data, headers=headers)
    assert res.status_code == 201
    doc_rc = res.json()
    assert doc_rc["document_type"] == "vehicle_rc"
    assert doc_rc["document_number"] == "MH15TC1234"
    assert doc_rc["file_mime_type"] == "application/pdf"

    # 2. Upload Commercial Transport Permit (JPEG)
    jpeg_bytes = sample_jpeg_content()
    files2 = {"file": ("permit.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    data2 = {"document_type": "transport_permit", "document_number": "NP-2026-9988"}

    res2 = client.post("/api/v1/users/me/verification/documents", files=files2, data=data2, headers=headers)
    assert res2.status_code == 201
    doc_permit = res2.json()
    assert doc_permit["document_type"] == "transport_permit"
    assert doc_permit["document_number"] == "NP-2026-9988"

    # 3. Retrieve current verification and verify both documents attached
    res_status = client.get("/api/v1/users/me/verification", headers=headers)
    assert res_status.status_code == 200
    sub_data = res_status.json()
    assert len(sub_data["documents"]) == 2


def test_transporter_rejects_invalid_document_type(client: TestClient, unverified_transporter: User):
    """Transporter uploading farmer document type like 'kisan_credit_card' is rejected with 422."""
    headers = auth_headers(unverified_transporter)
    pdf_bytes = sample_pdf_content()
    files = {"file": ("kcc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"document_type": "kisan_credit_card"}

    res = client.post("/api/v1/users/me/verification/documents", files=files, data=data, headers=headers)
    assert res.status_code == 422
    assert "Invalid document_type" in res.json()["detail"]
    assert "transporter" in res.json()["detail"]


def test_transporter_rejects_invalid_file_signature(client: TestClient, unverified_transporter: User):
    """Uploading a file claiming to be PDF but having plain text header is rejected with 422."""
    headers = auth_headers(unverified_transporter)
    fake_pdf = b"THIS IS NOT A VALID PDF FILE AT ALL"
    files = {"file": ("rc.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    data = {"document_type": "vehicle_rc"}

    res = client.post("/api/v1/users/me/verification/documents", files=files, data=data, headers=headers)
    assert res.status_code == 422
    assert "Invalid file signature" in res.json()["detail"]


# ===========================================================================
# 3. Security & Multi-Tenant Isolation Tests
# ===========================================================================


def test_transporter_cannot_download_other_transporter_document(
    client: TestClient, unverified_transporter: User, second_transporter: User
):
    """Transporter 2 cannot download an evidence document uploaded by Transporter 1 (403)."""
    headers1 = auth_headers(unverified_transporter)
    files = {"file": ("rc.pdf", io.BytesIO(sample_pdf_content()), "application/pdf")}
    data = {"document_type": "vehicle_rc"}

    res = client.post("/api/v1/users/me/verification/documents", files=files, data=data, headers=headers1)
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # Transporter 2 tries to download Transporter 1's document
    headers2 = auth_headers(second_transporter)
    res_dl = client.get(f"/api/v1/users/me/verification/documents/{doc_id}/download", headers=headers2)
    assert res_dl.status_code == 403
    assert "Forbidden" in res_dl.json()["detail"]


# ===========================================================================
# 4. Admin Queue & Review Workflows
# ===========================================================================


def test_admin_filters_queue_by_transporter_role(
    client: TestClient, unverified_transporter: User, admin_user: User
):
    """Admin can query the verification queue filtered by role='transporter'."""
    # Submit application for transporter
    headers_t = auth_headers(unverified_transporter)
    client.post("/api/v1/users/me/verification", json={"submission_notes": "Fleet review"}, headers=headers_t)

    # Admin lists with role=transporter
    headers_a = auth_headers(admin_user)
    res = client.get("/api/v1/admin/verifications?role=transporter&status=pending", headers=headers_a)
    assert res.status_code == 200
    queue_data = res.json()
    assert queue_data["total"] >= 1
    assert any(item["user_id"] == str(unverified_transporter.id) for item in queue_data["items"])


def test_admin_approves_transporter_verification(
    client: TestClient, db_session: Session, unverified_transporter: User, admin_user: User
):
    """Admin approves pending transporter application; user status becomes 'verified' and audit log recorded."""
    headers_t = auth_headers(unverified_transporter)
    sub_res = client.post("/api/v1/users/me/verification", json={"submission_notes": "Commercial review"}, headers=headers_t)
    sub_id = sub_res.json()["id"]

    headers_a = auth_headers(admin_user)
    approve_res = client.post(
        f"/api/v1/admin/verifications/{sub_id}/approve",
        json={"approval_notes": "Fleet and commercial permits verified against RTO database."},
        headers=headers_a,
    )
    assert approve_res.status_code == 200
    appr_data = approve_res.json()
    assert appr_data["status"] == "approved"
    assert appr_data["reviewed_by_admin_id"] == str(admin_user.id)

    # Check user in DB
    db_session.expire_all()
    user_db = db_session.get(User, unverified_transporter.id)
    assert user_db.verification_status == "verified"

    # Check AdminAuditLog
    audit = db_session.query(AdminAuditLog).filter(AdminAuditLog.target_entity_id == uuid.UUID(sub_id)).first()
    assert audit is not None
    assert audit.action == ACTION_VERIFY_APPROVE
    assert audit.admin_user_id == admin_user.id

    # Check Notification dispatched
    notifs = db_session.query(Notification).filter(Notification.user_id == unverified_transporter.id).all()
    assert any("Approved" in n.title for n in notifs)


def test_admin_rejects_transporter_verification_and_resubmit(
    client: TestClient, db_session: Session, unverified_transporter: User, admin_user: User
):
    """Admin rejects transporter with mandatory reason; transporter resubmits after updating documents."""
    headers_t = auth_headers(unverified_transporter)
    sub_res = client.post("/api/v1/users/me/verification", json={"submission_notes": "First submission"}, headers=headers_t)
    sub_id = sub_res.json()["id"]

    # Reject without reason -> 422
    headers_a = auth_headers(admin_user)
    bad_reject = client.post(f"/api/v1/admin/verifications/{sub_id}/reject", json={"rejection_reason": ""}, headers=headers_a)
    assert bad_reject.status_code == 422

    # Reject with valid reason
    rejection_reason = "Vehicle RC copy is blurry and commercial fitness certificate is expired."
    reject_res = client.post(
        f"/api/v1/admin/verifications/{sub_id}/reject",
        json={"rejection_reason": rejection_reason},
        headers=headers_a,
    )
    assert reject_res.status_code == 200
    rej_data = reject_res.json()
    assert rej_data["status"] == "rejected"
    assert rej_data["rejection_reason"] == rejection_reason

    # User status in DB
    db_session.expire_all()
    user_db = db_session.get(User, unverified_transporter.id)
    assert user_db.verification_status == "rejected"

    # Transporter views own status and sees rejection reason
    my_status = client.get("/api/v1/users/me/verification", headers=headers_t)
    assert my_status.status_code == 200
    assert my_status.json()["rejection_reason"] == rejection_reason

    # Transporter resubmits updated application
    resubmit_res = client.post(
        "/api/v1/users/me/verification",
        json={"submission_notes": "Resubmitting with clear high-resolution RC scan and renewed fitness certificate."},
        headers=headers_t,
    )
    assert resubmit_res.status_code == 201
    assert resubmit_res.json()["status"] == "pending"

    # User status is back to 'pending'
    db_session.expire_all()
    user_db = db_session.get(User, unverified_transporter.id)
    assert user_db.verification_status == "pending"

    # History contains both submissions
    hist_res = client.get("/api/v1/users/me/verification/history", headers=headers_t)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 2


# ===========================================================================
# 5. Marketplace Restrictions Enforcement Tests
# ===========================================================================


def test_unverified_transporter_restricted_from_order_coordination(
    client: TestClient, db_session: Session, unverified_transporter: User, verified_farmer: User, verified_buyer: User
):
    """An unverified transporter cannot coordinate order transport or update transport status."""
    conv = Conversation(farmer_id=verified_farmer.id, buyer_id=verified_buyer.id, initial_context_type="general")
    db_session.add(conv)
    db_session.commit()

    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=verified_farmer.id,
        recipient_id=verified_buyer.id,
        status="accepted",
        total_amount=Decimal("50000.00"),
    )
    db_session.add(offer)
    db_session.commit()

    order = Order(
        order_number="ORD-TEST-001",
        source_offer_id=offer.id,
        farmer_id=verified_farmer.id,
        buyer_id=verified_buyer.id,
        transporter_id=unverified_transporter.id,
        total_amount=Decimal("50000.00"),
        status="confirmed",
        transport_status="assigned",
        delivery_status="not_arranged",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    # Unverified transporter attempts to update transport status to 'in_transit'
    headers_t = auth_headers(unverified_transporter)
    payload = {"transport_status": "in_transit", "delivery_notes": "Loaded at farm gate"}

    res = client.post(f"/api/v1/orders/{order.id}/transport-coordination", json=payload, headers=headers_t)
    assert res.status_code == 403
    assert "requires a verified transportation provider" in res.json()["detail"]


def test_cannot_assign_unverified_transporter_to_order(
    client: TestClient, db_session: Session, unverified_transporter: User, verified_farmer: User, verified_buyer: User
):
    """Buyer or Farmer cannot assign an unverified transporter to an order."""
    conv = Conversation(farmer_id=verified_farmer.id, buyer_id=verified_buyer.id, initial_context_type="general")
    db_session.add(conv)
    db_session.commit()

    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=verified_farmer.id,
        recipient_id=verified_buyer.id,
        status="accepted",
        total_amount=Decimal("30000.00"),
    )
    db_session.add(offer)
    db_session.commit()

    order = Order(
        order_number="ORD-TEST-002",
        source_offer_id=offer.id,
        farmer_id=verified_farmer.id,
        buyer_id=verified_buyer.id,
        total_amount=Decimal("30000.00"),
        status="confirmed",
        transport_status="none",
        delivery_status="not_arranged",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    # Farmer tries to directly assign transporter via legacy endpoint (blocked)
    headers_f = auth_headers(verified_farmer)
    payload = {"transporter_user_id": str(unverified_transporter.id)}

    res = client.post(f"/api/v1/orders/{order.id}/transport-coordination", json=payload, headers=headers_f)
    assert res.status_code == 400
    assert "bilateral" in res.json()["detail"].lower()

    # Farmer tries to initiate connection request to an unverified transporter (also blocked)
    req_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(unverified_transporter.id),
            "order_id": str(order.id),
            "cargo_description": "Onions 2000 kg",
        },
        headers=headers_f,
    )
    assert req_res.status_code == 400
    assert "unverified provider" in req_res.json()["detail"].lower()

    db_session.refresh(order)
    assert order.transporter_id is None


def test_verified_transporter_can_coordinate_order_transport(
    client: TestClient, db_session: Session, unverified_transporter: User, verified_farmer: User, verified_buyer: User
):
    """Once verified, transporter can update order transport coordination status."""
    # Mark transporter verified
    unverified_transporter.verification_status = "verified"
    db_session.commit()

    conv = Conversation(farmer_id=verified_farmer.id, buyer_id=verified_buyer.id, initial_context_type="general")
    db_session.add(conv)
    db_session.commit()

    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=verified_farmer.id,
        recipient_id=verified_buyer.id,
        status="accepted",
        total_amount=Decimal("40000.00"),
    )
    db_session.add(offer)
    db_session.commit()

    order = Order(
        order_number="ORD-TEST-003",
        source_offer_id=offer.id,
        farmer_id=verified_farmer.id,
        buyer_id=verified_buyer.id,
        transporter_id=unverified_transporter.id,
        total_amount=Decimal("40000.00"),
        status="confirmed",
        transport_status="assigned",
        delivery_status="not_arranged",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    # Verified transporter updates transport status
    headers_t = auth_headers(unverified_transporter)
    payload = {"transport_status": "in_transit", "delivery_notes": "Departed Nashik at 09:00"}

    res = client.post(f"/api/v1/orders/{order.id}/transport-coordination", json=payload, headers=headers_t)
    assert res.status_code == 200
    assert res.json()["transport_status"] == "in_transit"
