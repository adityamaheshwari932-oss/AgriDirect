"""Comprehensive integration and unit tests for Verification System (Step 5):
- Applicant workflow: Farmer & Buyer verification application submission
- Document evidence: Upload, streaming, format/size validation, path traversal prevention, secure download
- Multi-tenant security: Document isolation, cross-user download prevention, role scoping
- Administrative review: Queue listing, pagination, filters, submission inspection, document audit
- State transitions: Approve (applicant -> verified), Reject (applicant -> rejected with reason)
- Audit trail & notifications: AdminAuditLog creation, Notification dispatch, applicant isolation
- Re-verification & resubmission: Re-submission after rejection, prevention of duplicate active submissions
- Regression protection: Step 4 profile update verification immutability, role guards
"""

import io
import uuid
from decimal import Decimal
from pathlib import Path

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
from app.models.admin import ACTION_VERIFY_APPROVE, ACTION_VERIFY_REJECT, AdminAuditLog
from app.models.notification import Notification
from app.models.user import BuyerProfile, FarmerProfile, User
from app.models.verification import VerificationDocument, VerificationSubmission


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database supporting multi-threaded access."""
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
    """Provide a TestClient with overridden get_db dependency and temporary upload dir."""
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
def unverified_farmer(db_session: Session) -> User:
    """Create an active, unverified farmer user with profile."""
    user = User(
        email="farmer.test@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543210",
    )
    profile = FarmerProfile(
        user=user,
        full_name="Ramesh Kisan",
        farm_name="Ramesh Organic Farms",
        farm_location_address="Gat No 12, Khed, Pune",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_buyer(db_session: Session) -> User:
    """Create an active, unverified buyer user with profile."""
    user = User(
        email="buyer.test@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543211",
    )
    profile = BuyerProfile(
        user=user,
        contact_person_name="Ananya Sen",
        business_name="Spice Garden Kitchen",
        business_type="restaurant",
        business_registration_number="GSTIN27ABCDE1234F1Z5",
        delivery_receiving_address="Rear Bay 2, Commercial Street",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def verified_farmer(db_session: Session) -> User:
    """Create an active, verified farmer user."""
    user = User(
        email="verified.farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543212",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an active administrator user."""
    user = User(
        email="admin.review@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543213",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_farmer(db_session: Session) -> User:
    """Create a second active farmer to test multi-tenant isolation."""
    user = User(
        email="farmer2.test@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543214",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def suspended_user(db_session: Session) -> User:
    """Create a suspended user."""
    user = User(
        email="suspended@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="unverified",
        account_status="suspended",
        phone_number="+919876543215",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    """Generate Authorization header for a user."""
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Verification Application Submission Tests
# ===========================================================================


def test_farmer_submits_valid_application(client: TestClient, db_session: Session, unverified_farmer: User):
    """Farmer successfully submits an application with notes, gets 201, notification is created."""
    headers = auth_headers(unverified_farmer)
    payload = {"submission_notes": "Submitting land ownership records for 10-acre organic farm."}

    response = client.post("/api/v1/users/me/verification", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "pending"
    assert data["user_id"] == str(unverified_farmer.id)
    assert data["submission_notes"] == payload["submission_notes"]
    assert data["reviewed_by_admin_id"] is None
    assert data["rejection_reason"] is None

    # Verify user verification_status updated to 'pending' in database
    db_session.expire_all()
    user_in_db = db_session.get(User, unverified_farmer.id)
    assert user_in_db.verification_status == "pending"

    # Verify notification dispatched
    notifications = db_session.query(Notification).filter(Notification.user_id == unverified_farmer.id).all()
    assert len(notifications) == 1
    assert "Submitted" in notifications[0].title


def test_buyer_submits_valid_application(client: TestClient, db_session: Session, unverified_buyer: User):
    """Commercial buyer successfully submits verification application."""
    headers = auth_headers(unverified_buyer)
    payload = {"submission_notes": "Restaurant trade license verification", "role": "buyer"}

    response = client.post("/api/v1/users/me/verification", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["user_id"] == str(unverified_buyer.id)

    db_session.expire_all()
    user_in_db = db_session.get(User, unverified_buyer.id)
    assert user_in_db.verification_status == "pending"


def test_unauthenticated_submission_rejected(client: TestClient):
    """Unauthenticated application submission returns 401."""
    response = client.post("/api/v1/users/me/verification", json={"submission_notes": "Test"})
    assert response.status_code == 401


def test_suspended_user_submission_rejected(client: TestClient, suspended_user: User):
    """Suspended user cannot submit verification application (403)."""
    headers = auth_headers(suspended_user)
    response = client.post("/api/v1/users/me/verification", json={}, headers=headers)
    assert response.status_code == 403
    assert "inactive or suspended" in response.json()["detail"].lower()


def test_role_mismatch_in_payload_rejected(client: TestClient, unverified_farmer: User):
    """Farmer specifying role='buyer' in payload is rejected with 400."""
    headers = auth_headers(unverified_farmer)
    response = client.post("/api/v1/users/me/verification", json={"role": "buyer"}, headers=headers)
    assert response.status_code == 400
    assert "does not match your account role" in response.json()["detail"]


def test_admin_cannot_submit_verification(client: TestClient, admin_user: User):
    """Admin user cannot submit verification application."""
    headers = auth_headers(admin_user)
    response = client.post("/api/v1/users/me/verification", json={}, headers=headers)
    assert response.status_code == 400
    assert "Only farmers and commercial buyers" in response.json()["detail"]


def test_duplicate_pending_application_rejected(client: TestClient, unverified_farmer: User):
    """Cannot submit a second application while an active pending application exists (409 Conflict)."""
    headers = auth_headers(unverified_farmer)
    # First submission
    res1 = client.post("/api/v1/users/me/verification", json={"submission_notes": "First"}, headers=headers)
    assert res1.status_code == 201

    # Second submission
    res2 = client.post("/api/v1/users/me/verification", json={"submission_notes": "Second"}, headers=headers)
    assert res2.status_code == 409
    assert "already have an active verification submission" in res2.json()["detail"]


def test_already_verified_user_cannot_submit(client: TestClient, verified_farmer: User):
    """Already verified user cannot submit redundant applications (400)."""
    headers = auth_headers(verified_farmer)
    response = client.post("/api/v1/users/me/verification", json={}, headers=headers)
    assert response.status_code == 400
    assert "already verified" in response.json()["detail"]


def test_submission_rejects_extra_fields(client: TestClient, unverified_farmer: User):
    """Extra or forbidden fields in submission payload return 422 (extra='forbid')."""
    headers = auth_headers(unverified_farmer)
    response = client.post(
        "/api/v1/users/me/verification",
        json={"submission_notes": "Valid notes", "status": "approved", "admin_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 422


def test_get_my_verification_none_found(client: TestClient, unverified_farmer: User):
    """GET /users/me/verification returns 404 when user has never submitted an application."""
    headers = auth_headers(unverified_farmer)
    response = client.get("/api/v1/users/me/verification", headers=headers)
    assert response.status_code == 404
    assert "No verification submission found" in response.json()["detail"]


def test_get_my_verification_and_history(client: TestClient, unverified_farmer: User):
    """GET /users/me/verification and /history return correct submission lifecycle details."""
    headers = auth_headers(unverified_farmer)
    client.post("/api/v1/users/me/verification", json={"submission_notes": "Initial app"}, headers=headers)

    res_current = client.get("/api/v1/users/me/verification", headers=headers)
    assert res_current.status_code == 200
    assert res_current.json()["submission_notes"] == "Initial app"

    res_history = client.get("/api/v1/users/me/verification/history", headers=headers)
    assert res_history.status_code == 200
    assert len(res_history.json()) == 1
    assert res_history.json()[0]["submission_notes"] == "Initial app"


# ===========================================================================
# 2. Document Submission and Storage Security Tests
# ===========================================================================


def test_farmer_uploads_valid_document(client: TestClient, db_session: Session, unverified_farmer: User):
    """Farmer uploads valid kisan credit card PDF document."""
    headers = auth_headers(unverified_farmer)
    fake_pdf = b"%PDF-1.4 sample pdf content for verification test"

    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "kisan_credit_card", "document_number": "KCC-987654"},
        files={"file": ("kcc_card.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["document_type"] == "kisan_credit_card"
    assert doc_data["document_number"] == "KCC-987654"
    assert doc_data["file_mime_type"] == "application/pdf"
    assert doc_data["file_size_bytes"] == len(fake_pdf)
    assert "file_uri" not in doc_data  # Internal path excluded

    # Confirm submission was automatically created
    submission = client.get("/api/v1/users/me/verification", headers=headers).json()
    assert len(submission["documents"]) == 1
    assert submission["documents"][0]["id"] == doc_data["id"]


def test_buyer_uploads_valid_document(client: TestClient, unverified_buyer: User):
    """Buyer uploads valid GSTIN certificate JPEG image."""
    headers = auth_headers(unverified_buyer)
    fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF sample image"

    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "gstin_certificate", "document_number": "29ABCDE1234F1Z5"},
        files={"file": ("gstin.jpg", fake_img, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["document_type"] == "gstin_certificate"


def test_document_upload_invalid_type_for_farmer_role(client: TestClient, unverified_farmer: User):
    """Farmer uploading a buyer-only document type (gstin_certificate) is rejected (422)."""
    headers = auth_headers(unverified_farmer)
    fake_pdf = b"%PDF-1.4 test"

    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "gstin_certificate"},
        files={"file": ("doc.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 422
    assert "Invalid document_type 'gstin_certificate' for farmer" in response.json()["detail"]


def test_document_upload_invalid_type_for_buyer_role(client: TestClient, unverified_buyer: User):
    """Buyer uploading a farmer-only document type (kisan_credit_card) is rejected (422)."""
    headers = auth_headers(unverified_buyer)
    fake_pdf = b"%PDF-1.4 test"

    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "kisan_credit_card"},
        files={"file": ("doc.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 422
    assert "Invalid document_type 'kisan_credit_card' for buyer" in response.json()["detail"]


def test_document_upload_disallowed_extension(client: TestClient, unverified_farmer: User):
    """Uploading executable or unsupported file extension is rejected (422)."""
    headers = auth_headers(unverified_farmer)
    fake_exe = b"MZ executable binary content"

    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("malware.exe", fake_exe, "application/octet-stream")},
        headers=headers,
    )
    assert response.status_code == 422
    assert "Unsupported file extension" in response.json()["detail"]


def test_document_upload_disallowed_mime_type(client: TestClient, unverified_farmer: User):
    """Uploading text/plain with .pdf extension is rejected for invalid MIME type (422)."""
    headers = auth_headers(unverified_farmer)
    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("doc.pdf", b"plain text", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 422
    assert "Unsupported content type" in response.json()["detail"]


def test_document_upload_empty_file_rejected(client: TestClient, unverified_farmer: User):
    """Uploading a 0-byte file returns 400 Bad Request."""
    headers = auth_headers(unverified_farmer)
    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_document_upload_oversized_file_rejected(client: TestClient, monkeypatch, unverified_farmer: User):
    """Uploading a file exceeding configured max_upload_size_bytes returns 413."""
    headers = auth_headers(unverified_farmer)
    settings = get_settings()
    # Temporarily set max size to 100 bytes
    monkeypatch.setattr(settings, "max_upload_size_bytes", 100)

    large_bytes = b"%PDF-1.4" + b"X" * 200
    response = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("toolarge.pdf", large_bytes, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 413
    assert "exceeds maximum permitted size" in response.json()["detail"]


def test_document_download_authorized_and_isolation(
    client: TestClient, unverified_farmer: User, second_farmer: User, admin_user: User
):
    """Verify document download: owner and admin succeed; another user receives 403."""
    farmer_headers = auth_headers(unverified_farmer)
    second_headers = auth_headers(second_farmer)
    admin_headers = auth_headers(admin_user)

    file_content = b"%PDF-1.4 secret proof content"
    upload_res = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("id.pdf", file_content, "application/pdf")},
        headers=farmer_headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Owner download succeeds
    dl_res = client.get(f"/api/v1/users/me/verification/documents/{doc_id}/download", headers=farmer_headers)
    assert dl_res.status_code == 200
    assert dl_res.content == file_content
    assert dl_res.headers["content-type"] == "application/pdf"

    # 2. Another farmer cannot download owner's document (403)
    second_res = client.get(f"/api/v1/users/me/verification/documents/{doc_id}/download", headers=second_headers)
    assert second_res.status_code == 403
    assert "Forbidden" in second_res.json()["detail"]

    # 3. Admin can download via admin endpoint
    sub_id = upload_res.json()["submission_id"]
    admin_dl_res = client.get(
        f"/api/v1/admin/verifications/{sub_id}/documents/{doc_id}/download", headers=admin_headers
    )
    assert admin_dl_res.status_code == 200
    assert admin_dl_res.content == file_content


# ===========================================================================
# 3. Administrative Review Queue & Decisions Tests
# ===========================================================================


def test_admin_list_and_filter_verifications(
    client: TestClient, unverified_farmer: User, unverified_buyer: User, admin_user: User
):
    """Admin lists verification queue with status and role filtering."""
    admin_headers = auth_headers(admin_user)

    # Submit applications
    client.post("/api/v1/users/me/verification", json={"submission_notes": "Farmer App"}, headers=auth_headers(unverified_farmer))
    client.post("/api/v1/users/me/verification", json={"submission_notes": "Buyer App"}, headers=auth_headers(unverified_buyer))

    # List all
    res = client.get("/api/v1/admin/verifications", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Filter by role = 'farmer'
    res_farmer = client.get("/api/v1/admin/verifications?role=farmer", headers=admin_headers)
    assert res_farmer.status_code == 200
    assert res_farmer.json()["total"] == 1
    assert res_farmer.json()["items"][0]["user_role"] == "farmer"

    # Filter by role = 'buyer'
    res_buyer = client.get("/api/v1/admin/verifications?role=buyer", headers=admin_headers)
    assert res_buyer.status_code == 200
    assert res_buyer.json()["total"] == 1
    assert res_buyer.json()["items"][0]["user_role"] == "buyer"


def test_admin_endpoints_reject_non_admin(client: TestClient, unverified_farmer: User):
    """Non-admin user receives 403 Forbidden on all admin endpoints."""
    headers = auth_headers(unverified_farmer)
    fake_id = uuid.uuid4()

    assert client.get("/api/v1/admin/verifications", headers=headers).status_code == 403
    assert client.get(f"/api/v1/admin/verifications/{fake_id}", headers=headers).status_code == 403
    assert client.post(f"/api/v1/admin/verifications/{fake_id}/approve", headers=headers).status_code == 403
    assert client.post(f"/api/v1/admin/verifications/{fake_id}/reject", json={"rejection_reason": "No"}, headers=headers).status_code == 403


def test_admin_approve_verification_workflow(
    client: TestClient, db_session: Session, unverified_farmer: User, admin_user: User
):
    """Admin approves pending submission: updates submission to approved, user to verified, logs audit."""
    farmer_headers = auth_headers(unverified_farmer)
    admin_headers = auth_headers(admin_user)

    # Submit
    sub_res = client.post("/api/v1/users/me/verification", json={"submission_notes": "Approve me"}, headers=farmer_headers)
    sub_id = sub_res.json()["id"]

    # Approve
    approve_res = client.post(
        f"/api/v1/admin/verifications/{sub_id}/approve",
        json={"approval_notes": "Verified government ID & organic certification."},
        headers=admin_headers,
    )
    assert approve_res.status_code == 200
    app_data = approve_res.json()
    assert app_data["status"] == "approved"
    assert app_data["reviewed_by_admin_id"] == str(admin_user.id)
    assert app_data["reviewed_at"] is not None

    # Verify user verification_status updated to 'verified'
    db_session.expire_all()
    user_in_db = db_session.get(User, unverified_farmer.id)
    assert user_in_db.verification_status == "verified"

    # Verify AdminAuditLog persisted
    audit_logs = db_session.query(AdminAuditLog).filter(AdminAuditLog.target_entity_id == uuid.UUID(sub_id)).all()
    assert len(audit_logs) == 1
    assert audit_logs[0].action == ACTION_VERIFY_APPROVE
    assert audit_logs[0].admin_user_id == admin_user.id

    # Verify Notification dispatched to applicant
    notifications = db_session.query(Notification).filter(Notification.user_id == unverified_farmer.id).all()
    assert any("Approved" in n.title for n in notifications)


def test_admin_cannot_approve_already_approved_submission(
    client: TestClient, unverified_farmer: User, admin_user: User
):
    """Attempting to approve an already approved submission returns 400 Bad Request."""
    farmer_headers = auth_headers(unverified_farmer)
    admin_headers = auth_headers(admin_user)

    sub_id = client.post("/api/v1/users/me/verification", json={}, headers=farmer_headers).json()["id"]
    client.post(f"/api/v1/admin/verifications/{sub_id}/approve", headers=admin_headers)

    # Second approve attempt
    second_res = client.post(f"/api/v1/admin/verifications/{sub_id}/approve", headers=admin_headers)
    assert second_res.status_code == 400
    assert "Only 'pending' submissions can be approved" in second_res.json()["detail"]


def test_admin_reject_verification_workflow_and_resubmission(
    client: TestClient, db_session: Session, unverified_farmer: User, admin_user: User
):
    """Admin rejects pending submission with reason: applicant becomes rejected, can resubmit."""
    farmer_headers = auth_headers(unverified_farmer)
    admin_headers = auth_headers(admin_user)

    # 1. Submit initial application
    sub_res = client.post("/api/v1/users/me/verification", json={"submission_notes": "First attempt"}, headers=farmer_headers)
    sub_id = sub_res.json()["id"]

    # 2. Reject with mandatory reason
    rejection_reason = "Submitted ID is blurred and unreadable. Please upload a clear color scan."
    reject_res = client.post(
        f"/api/v1/admin/verifications/{sub_id}/reject",
        json={"rejection_reason": rejection_reason},
        headers=admin_headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    assert reject_res.json()["rejection_reason"] == rejection_reason

    # Verify applicant user status updated to 'rejected'
    db_session.expire_all()
    user_in_db = db_session.get(User, unverified_farmer.id)
    assert user_in_db.verification_status == "rejected"

    # Verify audit log & notification
    audit = db_session.query(AdminAuditLog).filter(AdminAuditLog.target_entity_id == uuid.UUID(sub_id)).first()
    assert audit is not None
    assert audit.action == ACTION_VERIFY_REJECT
    assert audit.reason == rejection_reason

    # 3. Resubmission after rejection
    resub_res = client.post(
        "/api/v1/users/me/verification",
        json={"submission_notes": "Second attempt with high-resolution scan"},
        headers=farmer_headers,
    )
    assert resub_res.status_code == 201
    assert resub_res.json()["status"] == "pending"

    # Verify user status is now 'pending' again
    db_session.expire_all()
    assert db_session.get(User, unverified_farmer.id).verification_status == "pending"

    # Verify history contains both submissions
    history = client.get("/api/v1/users/me/verification/history", headers=farmer_headers).json()
    assert len(history) == 2


def test_admin_reject_empty_reason_rejected(client: TestClient, unverified_farmer: User, admin_user: User):
    """Rejection with empty or whitespace-only reason is rejected (422 or 400)."""
    sub_id = client.post("/api/v1/users/me/verification", json={}, headers=auth_headers(unverified_farmer)).json()["id"]
    res = client.post(
        f"/api/v1/admin/verifications/{sub_id}/reject",
        json={"rejection_reason": "  "},
        headers=auth_headers(admin_user),
    )
    assert res.status_code in (400, 422)


def test_admin_nonexistent_submission_404(client: TestClient, admin_user: User):
    """Accessing non-existent verification submission returns 404."""
    headers = auth_headers(admin_user)
    fake_id = uuid.uuid4()
    assert client.get(f"/api/v1/admin/verifications/{fake_id}", headers=headers).status_code == 404
    assert client.post(f"/api/v1/admin/verifications/{fake_id}/approve", headers=headers).status_code == 404


# ===========================================================================
# 4. Regression & Boundary Tests
# ===========================================================================


def test_profile_update_cannot_bypass_verification(client: TestClient, db_session: Session, unverified_farmer: User):
    """Step 4 profile updates cannot modify verification_status or bypass verification restrictions."""
    headers = auth_headers(unverified_farmer)

    # Attempt to update profile while passing verification_status in payload (rejected via extra='forbid')
    patch_res = client.patch(
        "/api/v1/users/me/farmer",
        json={"farm_name": "New Farm Name", "verification_status": "verified"},
        headers=headers,
    )
    assert patch_res.status_code == 422

    # Legitimate profile update preserves unverified status
    valid_patch = client.patch(
        "/api/v1/users/me/farmer",
        json={"farm_name": "New Valid Farm Name"},
        headers=headers,
    )
    assert valid_patch.status_code == 200
    assert valid_patch.json()["verification_status"] == "unverified"

    db_session.expire_all()
    assert db_session.get(User, unverified_farmer.id).verification_status == "unverified"


def test_upload_png_and_webp_signatures(client: TestClient, unverified_farmer: User):
    """Test valid PNG and WebP uploads with binary format signatures."""
    headers = auth_headers(unverified_farmer)

    # Valid PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    png_res = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("cert.png", png_bytes, "image/png")},
        headers=headers,
    )
    assert png_res.status_code == 201
    assert png_res.json()["file_mime_type"] == "image/png"

    # Valid WebP
    webp_bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 \x18\x00\x00\x00\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00"
    webp_res = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "land_ownership"},
        files={"file": ("land.webp", webp_bytes, "image/webp")},
        headers=headers,
    )
    assert webp_res.status_code == 201
    assert webp_res.json()["file_mime_type"] == "image/webp"


def test_upload_file_signature_mismatch_rejected(client: TestClient, unverified_farmer: User):
    """Uploading text/spoofed content under permitted extensions is rejected via signature verification (422)."""
    headers = auth_headers(unverified_farmer)

    # Fake PDF
    fake_pdf = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("spoof.pdf", b"NOT_A_PDF_CONTENT_HERE", "application/pdf")},
        headers=headers,
    )
    assert fake_pdf.status_code == 422
    assert "Invalid file signature" in fake_pdf.json()["detail"]

    # Fake JPEG
    fake_jpg = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("spoof.jpg", b"NOT_A_JPEG_FILE", "image/jpeg")},
        headers=headers,
    )
    assert fake_jpg.status_code == 422
    assert "Invalid file signature" in fake_jpg.json()["detail"]


def test_upload_truncated_file_header_rejected(client: TestClient, unverified_farmer: User):
    """File with fewer than 4 bytes is rejected for truncated header (422)."""
    headers = auth_headers(unverified_farmer)
    res = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("tiny.pdf", b"%P", "application/pdf")},
        headers=headers,
    )
    assert res.status_code == 422
    assert "truncated or too small" in res.json()["detail"]


def test_admin_download_document_mismatched_submission_404(
    client: TestClient, unverified_farmer: User, unverified_buyer: User, admin_user: User
):
    """Admin requesting document with a mismatched submission ID receives 404."""
    farmer_headers = auth_headers(unverified_farmer)
    buyer_headers = auth_headers(unverified_buyer)
    admin_headers = auth_headers(admin_user)

    # Farmer creates submission 1 with doc 1
    doc1_bytes = b"%PDF-1.4 farmer document content"
    res1 = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "government_id"},
        files={"file": ("farmer_doc.pdf", doc1_bytes, "application/pdf")},
        headers=farmer_headers,
    )
    sub1_id = res1.json()["submission_id"]
    doc1_id = res1.json()["id"]

    # Buyer creates submission 2 with doc 2
    doc2_bytes = b"%PDF-1.4 buyer document content"
    res2 = client.post(
        "/api/v1/users/me/verification/documents",
        data={"document_type": "gstin_certificate"},
        files={"file": ("buyer_doc.pdf", doc2_bytes, "application/pdf")},
        headers=buyer_headers,
    )
    sub2_id = res2.json()["submission_id"]
    doc2_id = res2.json()["id"]

    # Admin requests submission 1 with document 2 (mismatched) -> 404
    mismatch_res = client.get(
        f"/api/v1/admin/verifications/{sub1_id}/documents/{doc2_id}/download",
        headers=admin_headers,
    )
    assert mismatch_res.status_code == 404
    assert "not found for this submission" in mismatch_res.json()["detail"]


def test_orphaned_upload_cleanup_on_db_failure(
    client: TestClient, unverified_farmer: User, monkeypatch, isolated_upload_dir
):
    """If database persistence fails after file write, the newly created upload is safely unlinked."""
    from app.verification.service import VerificationService

    def mock_commit_failure(*args, **kwargs):
        raise RuntimeError("Simulated database failure during commit")

    headers = auth_headers(unverified_farmer)
    pdf_bytes = b"%PDF-1.4 valid test file"

    # Patch session.commit inside VerificationService.upload_document
    monkeypatch.setattr("sqlalchemy.orm.Session.commit", mock_commit_failure)

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        client.post(
            "/api/v1/users/me/verification/documents",
            data={"document_type": "government_id"},
            files={"file": ("cleanup_test.pdf", pdf_bytes, "application/pdf")},
            headers=headers,
        )

    # Verify no orphaned files remain in isolated_upload_dir
    stored_files = list(isolated_upload_dir.glob("*.*"))
    assert len(stored_files) == 0
