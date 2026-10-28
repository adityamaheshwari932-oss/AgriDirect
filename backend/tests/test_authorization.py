"""End-to-end authorization and role-based permissions test suite:
- Token validation boundaries (missing, invalid signature, expired, disallowed algorithm)
- Dynamic database state changes post-token-issuance (revocation, status suspension, deletion)
- Role-based access control and least-privilege matrix (farmer, buyer, admin)
- Verification status gating (unverified, pending, rejected vs verified)
- Multi-tenant resource ownership isolation (notifications inbox and read acknowledgement)
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import (
    create_access_token,
    get_current_active_user,
    get_current_user,
    require_admin,
    require_buyer,
    require_farmer,
    require_verified_buyer,
    require_verified_farmer,
    require_verified_user,
)
from app.main import app
from app.models.notification import Notification
from app.models.user import BuyerProfile, FarmerProfile, User


# ===========================================================================
# Test Routers representing role-gated endpoints across the platform
# ===========================================================================

authz_test_router = APIRouter(prefix="/api/v1/test-authz", tags=["test-authz"])


@authz_test_router.get("/active-only")
def active_only_endpoint(current_user: User = Depends(get_current_active_user)):
    return {"message": "active", "user_id": str(current_user.id)}


@authz_test_router.get("/verified-only")
def verified_only_endpoint(current_user: User = Depends(require_verified_user)):
    return {"message": "verified", "user_id": str(current_user.id)}


@authz_test_router.get("/farmer-only")
def farmer_only_endpoint(current_user: User = Depends(require_farmer)):
    return {"message": "farmer", "user_id": str(current_user.id)}


@authz_test_router.get("/verified-farmer-only")
def verified_farmer_only_endpoint(current_user: User = Depends(require_verified_farmer)):
    return {"message": "verified_farmer", "user_id": str(current_user.id)}


@authz_test_router.get("/buyer-only")
def buyer_only_endpoint(current_user: User = Depends(require_buyer)):
    return {"message": "buyer", "user_id": str(current_user.id)}


@authz_test_router.get("/verified-buyer-only")
def verified_buyer_only_endpoint(current_user: User = Depends(require_verified_buyer)):
    return {"message": "verified_buyer", "user_id": str(current_user.id)}


@authz_test_router.get("/admin-only")
def admin_only_endpoint(current_user: User = Depends(require_admin)):
    return {"message": "admin", "user_id": str(current_user.id)}


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


_router_mounted = False


@pytest.fixture
def client(sqlite_engine) -> TestClient:
    """Provide a TestClient with test routes and overridden get_db dependency."""
    global _router_mounted
    if not _router_mounted:
        app.include_router(authz_test_router)
        _router_mounted = True

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
def db_session(sqlite_engine):
    """Provide a direct database session for test fixture creation."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


# ===========================================================================
# 1. Token Validation Boundaries
# ===========================================================================


class TestTokenValidationBoundaries:
    """Verifies that missing, expired, altered, or forged tokens are rejected."""

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/test-authz/active-only")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_invalid_signature_returns_401(self, client: TestClient) -> None:
        forged_token = jwt.encode(
            {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "completely-wrong-secret-key-32-chars-long",
            algorithm="HS256",
        )
        response = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient) -> None:
        settings = get_settings()
        expired_token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_disallowed_algorithm_none_returns_401(self, client: TestClient) -> None:
        unsecured_token = jwt.encode(
            {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            key="",
            algorithm="none",
        )
        response = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {unsecured_token}"},
        )
        assert response.status_code == 401

    def test_nonexistent_user_token_returns_401(self, client: TestClient) -> None:
        ghost_token = create_access_token({"sub": str(uuid.uuid4())})
        response = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {ghost_token}"},
        )
        assert response.status_code == 401


# ===========================================================================
# 2. Dynamic DB State Changes Post-Issuance (Zero Token Trust)
# ===========================================================================


class TestDynamicDatabaseStateChanges:
    """Verifies that changes in database state immediately revoke access despite valid JWT."""

    def test_suspended_account_blocked_immediately(
        self, client: TestClient, db_session: Session
    ) -> None:
        # Create active user and issue valid token
        user = User(
            email="to_suspend@example.com",
            password_hash="hash",
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": str(user.id)})

        # Request succeeds while active
        res1 = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 200

        # Suspend user in DB
        user.account_status = "suspended"
        db_session.commit()

        # Subsequent request with same valid token must be rejected with 403
        res2 = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 403
        assert "inactive or suspended" in res2.json()["detail"].lower()

    def test_revoked_verification_blocked_immediately(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = User(
            email="to_reject@example.com",
            password_hash="hash",
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": str(user.id), "status": "verified"})

        # Initial request to verified endpoint succeeds
        res1 = client.get(
            "/api/v1/test-authz/verified-only",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 200

        # Revoke verification in DB to rejected
        user.verification_status = "rejected"
        db_session.commit()

        # Same token is rejected because authorization resolves live DB state
        res2 = client.get(
            "/api/v1/test-authz/verified-only",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 403
        assert "verified account" in res2.json()["detail"].lower()

    def test_deleted_user_blocked_immediately(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = User(
            email="to_delete@example.com",
            password_hash="hash",
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": str(user.id)})

        # Delete user from DB
        db_session.delete(user)
        db_session.commit()

        # Token referencing deleted user returns 401
        res = client.get(
            "/api/v1/test-authz/active-only",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401


# ===========================================================================
# 3. Role Permissions & Least Privilege
# ===========================================================================


class TestRolePermissionsAndLeastPrivilege:
    """Verifies that roles cannot access operations outside their boundary."""

    def test_farmer_cannot_access_buyer_or_admin_endpoints(
        self, client: TestClient, db_session: Session
    ) -> None:
        farmer = User(
            email="active_farmer@example.com",
            password_hash="hash",
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(farmer)
        db_session.commit()
        token = create_access_token({"sub": str(farmer.id)})
        headers = {"Authorization": f"Bearer {token}"}

        # Farmer succeeds on farmer endpoints
        assert client.get("/api/v1/test-authz/farmer-only", headers=headers).status_code == 200
        assert client.get("/api/v1/test-authz/verified-farmer-only", headers=headers).status_code == 200

        # Farmer is rejected on buyer and admin endpoints
        res_buyer = client.get("/api/v1/test-authz/buyer-only", headers=headers)
        assert res_buyer.status_code == 403
        assert "buyer account" in res_buyer.json()["detail"].lower()

        res_v_buyer = client.get("/api/v1/test-authz/verified-buyer-only", headers=headers)
        assert res_v_buyer.status_code == 403

        res_admin = client.get("/api/v1/test-authz/admin-only", headers=headers)
        assert res_admin.status_code == 403
        assert "administrator" in res_admin.json()["detail"].lower()

    def test_buyer_cannot_access_farmer_or_admin_endpoints(
        self, client: TestClient, db_session: Session
    ) -> None:
        buyer = User(
            email="active_buyer@example.com",
            password_hash="hash",
            role="buyer",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(buyer)
        db_session.commit()
        token = create_access_token({"sub": str(buyer.id)})
        headers = {"Authorization": f"Bearer {token}"}

        # Buyer succeeds on buyer endpoints
        assert client.get("/api/v1/test-authz/buyer-only", headers=headers).status_code == 200
        assert client.get("/api/v1/test-authz/verified-buyer-only", headers=headers).status_code == 200

        # Buyer is rejected on farmer and admin endpoints
        res_farmer = client.get("/api/v1/test-authz/farmer-only", headers=headers)
        assert res_farmer.status_code == 403

        res_v_farmer = client.get("/api/v1/test-authz/verified-farmer-only", headers=headers)
        assert res_v_farmer.status_code == 403

        res_admin = client.get("/api/v1/test-authz/admin-only", headers=headers)
        assert res_admin.status_code == 403

    def test_admin_access_allowed_on_admin_endpoint(
        self, client: TestClient, db_session: Session
    ) -> None:
        admin = User(
            email="admin_user@example.com",
            password_hash="hash",
            role="admin",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(admin)
        db_session.commit()
        token = create_access_token({"sub": str(admin.id)})
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/api/v1/test-authz/admin-only", headers=headers)
        assert res.status_code == 200
        assert res.json()["message"] == "admin"


# ===========================================================================
# 4. Verification Gating
# ===========================================================================


class TestVerificationGating:
    """Verifies that only users with status='verified' can access verified routes."""

    @pytest.mark.parametrize("status_val", ["unverified", "pending", "rejected"])
    def test_unverified_farmer_denied_verified_routes(
        self, client: TestClient, db_session: Session, status_val: str
    ) -> None:
        user = User(
            email=f"farmer_{status_val}@example.com",
            password_hash="hash",
            role="farmer",
            verification_status=status_val,
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        # Can access general active and general farmer endpoints
        assert client.get("/api/v1/test-authz/active-only", headers=headers).status_code == 200
        assert client.get("/api/v1/test-authz/farmer-only", headers=headers).status_code == 200

        # Denied on verified endpoints
        res_v = client.get("/api/v1/test-authz/verified-only", headers=headers)
        assert res_v.status_code == 403

        res_vf = client.get("/api/v1/test-authz/verified-farmer-only", headers=headers)
        assert res_vf.status_code == 403

    @pytest.mark.parametrize("status_val", ["unverified", "pending", "rejected"])
    def test_unverified_buyer_denied_verified_routes(
        self, client: TestClient, db_session: Session, status_val: str
    ) -> None:
        user = User(
            email=f"buyer_{status_val}@example.com",
            password_hash="hash",
            role="buyer",
            verification_status=status_val,
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        # Can access general active and general buyer endpoints
        assert client.get("/api/v1/test-authz/active-only", headers=headers).status_code == 200
        assert client.get("/api/v1/test-authz/buyer-only", headers=headers).status_code == 200

        # Denied on verified endpoints
        res_v = client.get("/api/v1/test-authz/verified-only", headers=headers)
        assert res_v.status_code == 403

        res_vb = client.get("/api/v1/test-authz/verified-buyer-only", headers=headers)
        assert res_vb.status_code == 403


# ===========================================================================
# 5. Multi-Tenant Resource Ownership (Notifications)
# ===========================================================================


class TestResourceOwnershipIsolation:
    """Verifies that users can only access their own private resources."""

    def test_notification_inbox_and_marking_isolated_per_user(
        self, client: TestClient, db_session: Session
    ) -> None:
        user_a = User(
            email="user_a@example.com",
            password_hash="hash",
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        user_b = User(
            email="user_b@example.com",
            password_hash="hash",
            role="buyer",
            verification_status="verified",
            account_status="active",
        )
        db_session.add_all([user_a, user_b])
        db_session.commit()

        # Create notifications for both
        notif_a = Notification(
            user_id=user_a.id,
            event_type="test_event",
            title="Notification for User A",
            body="Private content for A",
        )
        notif_b = Notification(
            user_id=user_b.id,
            event_type="test_event",
            title="Notification for User B",
            body="Private content for B",
        )
        db_session.add_all([notif_a, notif_b])
        db_session.commit()

        token_a = create_access_token({"sub": str(user_a.id)})
        token_b = create_access_token({"sub": str(user_b.id)})

        # User A's inbox lists only notif_a
        res_a = client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_a.status_code == 200
        items_a = res_a.json()["items"]
        assert len(items_a) == 1
        assert items_a[0]["id"] == str(notif_a.id)

        # User A cannot mark User B's notification as read (returns 403 Forbidden)
        hack_res = client.post(
            f"/api/v1/notifications/{notif_b.id}/read",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert hack_res.status_code == 403

        # User B can mark their own notification as read (returns 200)
        valid_res = client.post(
            f"/api/v1/notifications/{notif_b.id}/read",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert valid_res.status_code == 200
        assert valid_res.json()["is_read"] is True

        # Nonexistent notification returns 404
        nonexistent_id = uuid.uuid4()
        res_404 = client.post(
            f"/api/v1/notifications/{nonexistent_id}/read",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_404.status_code == 404
