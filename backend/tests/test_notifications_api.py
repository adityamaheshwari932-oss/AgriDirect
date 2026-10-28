"""Integration tests for protected notification API endpoints.

Tests cover:
- GET /api/v1/notifications
  - Unauthenticated access rejection (401)
  - Invalid/expired token rejection (401)
  - Inactive account access rejection (403)
  - Authenticated listing with unread-first ordering
  - Pagination parameters and count metadata
  - unread_only filtering
  - Multi-tenant tenant isolation (User A cannot view User B notifications)
- POST /api/v1/notifications/{id}/read
  - Unauthenticated access rejection (401)
  - Marking own notification as read (200 with timestamp)
  - Idempotent repeated read acknowledgement
  - Marking nonexistent notification (404)
  - Attempting to mark another user's notification (403)
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.notification import Notification
from app.models.user import User


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
    """Provide a transactional session for test fixture setup."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(sqlite_engine) -> TestClient:
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
def user_farmer(db_session: Session) -> User:
    """Create a verified active farmer user."""
    user = User(
        email="api_farmer@agridirect.test",
        password_hash="hashed_pw_farmer",
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_buyer(db_session: Session) -> User:
    """Create a verified active buyer user."""
    user = User(
        email="api_buyer@agridirect.test",
        password_hash="hashed_pw_buyer",
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_suspended(db_session: Session) -> User:
    """Create a suspended user for account status checks."""
    user = User(
        email="suspended_user@agridirect.test",
        password_hash="hashed_pw_suspended",
        role="buyer",
        verification_status="verified",
        account_status="suspended",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header_for_user(user: User) -> dict[str, str]:
    """Generate Authorization header with valid Bearer token for user."""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. GET /api/v1/notifications Tests
# ===========================================================================


class TestGetNotificationsEndpoint:
    """Tests for GET /api/v1/notifications."""

    def test_unauthenticated_request_rejected(self, client: TestClient) -> None:
        """GET /api/v1/notifications without token returns 401 Unauthorized."""
        response = client.get("/api/v1/notifications")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_invalid_token_rejected(self, client: TestClient) -> None:
        """Malformed token returns 401 Unauthorized."""
        response = client.get(
            "/api/v1/notifications",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401

    def test_suspended_user_forbidden(
        self, client: TestClient, user_suspended: User
    ) -> None:
        """User with non-active account_status receives 403 Forbidden."""
        headers = auth_header_for_user(user_suspended)
        response = client.get("/api/v1/notifications", headers=headers)
        assert response.status_code == 403
        assert "inactive or suspended" in response.json()["detail"].lower()

    def test_empty_inbox_returns_valid_structure(
        self, client: TestClient, user_farmer: User
    ) -> None:
        """User with no notifications receives empty list with 0 counts."""
        headers = auth_header_for_user(user_farmer)
        response = client.get("/api/v1/notifications", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["unread_count"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 0

    def test_list_notifications_unread_first_and_counts(
        self, client: TestClient, db_session: Session, user_farmer: User
    ) -> None:
        """Returns caller notifications ordered with unread first and accurate count metrics."""
        now = datetime.now(timezone.utc)

        # 1. Read notification
        n_read = Notification(
            user_id=user_farmer.id,
            event_type="order_update",
            title="Old Read Order",
            body="Completed order",
            is_read=True,
            read_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=2),
        )
        # 2. Unread notification (older)
        n_unread_1 = Notification(
            user_id=user_farmer.id,
            event_type="offer_alert",
            title="First Unread Offer",
            body="Offer pending",
            is_read=False,
            created_at=now - timedelta(minutes=45),
        )
        # 3. Unread notification (newer)
        n_unread_2 = Notification(
            user_id=user_farmer.id,
            event_type="offer_alert",
            title="Second Unread Offer",
            body="Newest offer",
            is_read=False,
            created_at=now - timedelta(minutes=10),
        )
        db_session.add_all([n_read, n_unread_1, n_unread_2])
        db_session.commit()

        headers = auth_header_for_user(user_farmer)
        response = client.get("/api/v1/notifications", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert data["unread_count"] == 2
        assert len(data["items"]) == 3

        # Verify unread-first and newest-first within unread
        assert data["items"][0]["title"] == "Second Unread Offer"
        assert data["items"][1]["title"] == "First Unread Offer"
        assert data["items"][2]["title"] == "Old Read Order"
        assert data["items"][2]["is_read"] is True

    def test_filter_unread_only(
        self, client: TestClient, db_session: Session, user_farmer: User
    ) -> None:
        """?unread_only=true returns only unread notifications."""
        n1 = Notification(
            user_id=user_farmer.id,
            event_type="alert",
            title="Read Alert",
            body="Read",
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )
        n2 = Notification(
            user_id=user_farmer.id,
            event_type="alert",
            title="Unread Alert",
            body="Unread",
            is_read=False,
        )
        db_session.add_all([n1, n2])
        db_session.commit()

        headers = auth_header_for_user(user_farmer)
        response = client.get("/api/v1/notifications?unread_only=true", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Unread Alert"

    def test_pagination_parameters(
        self, client: TestClient, db_session: Session, user_farmer: User
    ) -> None:
        """Pagination query parameters limit and page results."""
        for i in range(7):
            db_session.add(
                Notification(
                    user_id=user_farmer.id,
                    event_type="alert",
                    title=f"Notification {i}",
                    body="Body",
                )
            )
        db_session.commit()

        headers = auth_header_for_user(user_farmer)
        response = client.get("/api/v1/notifications?page=2&page_size=3", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 7
        assert data["total_pages"] == 3
        assert data["page"] == 2
        assert data["page_size"] == 3

    def test_user_boundary_isolation(
        self,
        client: TestClient,
        db_session: Session,
        user_farmer: User,
        user_buyer: User,
    ) -> None:
        """Farmer cannot view Buyer's notifications."""
        db_session.add(
            Notification(
                user_id=user_buyer.id,
                event_type="private_event",
                title="Secret Buyer Message",
                body="Confidential",
            )
        )
        db_session.commit()

        # Farmer requests inbox
        headers = auth_header_for_user(user_farmer)
        response = client.get("/api/v1/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# ===========================================================================
# 2. POST /api/v1/notifications/{id}/read Tests
# ===========================================================================


class TestMarkNotificationReadEndpoint:
    """Tests for POST /api/v1/notifications/{id}/read."""

    def test_unauthenticated_mark_read_rejected(self, client: TestClient) -> None:
        """Request without token returns 401 Unauthorized."""
        response = client.post(f"/api/v1/notifications/{uuid.uuid4()}/read")
        assert response.status_code == 401

    def test_mark_own_notification_as_read_success(
        self, client: TestClient, db_session: Session, user_farmer: User
    ) -> None:
        """Owner can mark unread notification as read; response contains read timestamp."""
        notif = Notification(
            user_id=user_farmer.id,
            event_type="test",
            title="Mark Me Read",
            body="Content",
            is_read=False,
        )
        db_session.add(notif)
        db_session.commit()

        headers = auth_header_for_user(user_farmer)
        response = client.post(f"/api/v1/notifications/{notif.id}/read", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(notif.id)
        assert data["is_read"] is True
        assert data["read_at"] is not None

        # Verify in database
        db_session.refresh(notif)
        assert notif.is_read is True
        assert notif.read_at is not None

    def test_mark_as_read_idempotency(
        self, client: TestClient, db_session: Session, user_farmer: User
    ) -> None:
        """Marking an already-read notification again returns 200 OK without errors."""
        notif = Notification(
            user_id=user_farmer.id,
            event_type="test",
            title="Already Read",
            body="Content",
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )
        db_session.add(notif)
        db_session.commit()

        headers = auth_header_for_user(user_farmer)
        response = client.post(f"/api/v1/notifications/{notif.id}/read", headers=headers)
        assert response.status_code == 200
        assert response.json()["is_read"] is True

    def test_cannot_mark_other_users_notification(
        self,
        client: TestClient,
        db_session: Session,
        user_farmer: User,
        user_buyer: User,
    ) -> None:
        """Farmer cannot mark Buyer's notification as read (returns 403 Forbidden)."""
        buyer_notif = Notification(
            user_id=user_buyer.id,
            event_type="private",
            title="Buyer Only",
            body="Private content",
            is_read=False,
        )
        db_session.add(buyer_notif)
        db_session.commit()

        # Farmer attempts to mark buyer's notification
        headers = auth_header_for_user(user_farmer)
        response = client.post(
            f"/api/v1/notifications/{buyer_notif.id}/read",
            headers=headers,
        )
        assert response.status_code == 403
        assert "forbidden" in response.json()["detail"].lower()

        # Verify buyer notification remains unread
        db_session.refresh(buyer_notif)
        assert buyer_notif.is_read is False

    def test_mark_nonexistent_notification_returns_404(
        self, client: TestClient, user_farmer: User
    ) -> None:
        """Marking a random nonexistent UUID returns 404 Not Found."""
        headers = auth_header_for_user(user_farmer)
        response = client.post(
            f"/api/v1/notifications/{uuid.uuid4()}/read",
            headers=headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
