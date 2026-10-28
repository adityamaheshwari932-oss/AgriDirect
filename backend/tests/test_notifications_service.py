"""Unit tests for NotificationService, NotificationRepository, and domain event handlers.

Tests cover:
- Notification creation with validation
- User existence verification
- Scoped listing for target user
- Unread-first ordering and newest-first secondary ordering
- Aggregate count calculations (total and unread)
- Pagination calculations (page, page_size, total_pages)
- Marking notifications as read (timestamping, idempotency)
- Security: Access control preventing cross-user access
- Domain event triggers for verification, offers, orders, amendments, and payments
- Safe email dispatching with feature flags
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.notification import (
    NOTIFICATION_REF_OFFER,
    NOTIFICATION_REF_ORDER,
    NOTIFICATION_REF_VERIFICATION,
    Notification,
)
from app.models.user import User
from app.notifications.email import send_email_notification
from app.notifications.repository import NotificationRepository
from app.notifications.service import (
    EVENT_AMENDMENT_PROPOSED,
    EVENT_COUNTER_OFFER_RECEIVED,
    EVENT_OFFER_ACCEPTED,
    EVENT_OFFER_RECEIVED,
    EVENT_OFFER_REJECTED,
    EVENT_ORDER_STATUS_CHANGED,
    EVENT_PAYMENT_ACKNOWLEDGED,
    EVENT_PAYMENT_RECORDED,
    EVENT_VERIFICATION_STATUS_CHANGED,
    NotificationService,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite engine with foreign key enforcement."""
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
    """Provide an isolated database session per test."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_user_a(db_session: Session) -> User:
    """Create primary test user."""
    user = User(
        email="user_a@agridirect.test",
        password_hash="hashed_pw_a",
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_user_b(db_session: Session) -> User:
    """Create secondary test user for isolation checks."""
    user = User(
        email="user_b@agridirect.test",
        password_hash="hashed_pw_b",
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ===========================================================================
# 1. Service & Repository Core Operations
# ===========================================================================


class TestNotificationServiceOperations:
    """Tests for core notification CRUD and validations."""

    def test_create_notification_success(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Creating a notification with valid inputs succeeds."""
        service = NotificationService(db_session)
        notif = service.create_notification(
            user_id=sample_user_a.id,
            event_type="test_alert",
            title="Marketplace Update",
            body="New buyer requirements posted in your region.",
            reference_type="requirement",
            reference_id=uuid.uuid4(),
        )

        assert notif.id is not None
        assert notif.user_id == sample_user_a.id
        assert notif.title == "Marketplace Update"
        assert notif.is_read is False
        assert notif.read_at is None
        assert notif.created_at is not None

    def test_create_notification_validations(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Creating notifications with empty strings raises ValueError."""
        service = NotificationService(db_session)

        # Empty title
        with pytest.raises(ValueError, match="title cannot be empty"):
            service.create_notification(
                user_id=sample_user_a.id,
                event_type="test",
                title="",
                body="Body",
            )

        # Empty body
        with pytest.raises(ValueError, match="body cannot be empty"):
            service.create_notification(
                user_id=sample_user_a.id,
                event_type="test",
                title="Title",
                body="   ",
            )

        # Empty event_type
        with pytest.raises(ValueError, match="event_type cannot be empty"):
            service.create_notification(
                user_id=sample_user_a.id,
                event_type="",
                title="Title",
                body="Body",
            )

        # Nonexistent user
        with pytest.raises(ValueError, match="does not exist"):
            service.create_notification(
                user_id=uuid.uuid4(),
                event_type="test",
                title="Title",
                body="Body",
            )

    def test_list_notifications_unread_first_ordering(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Unread notifications must appear before read notifications, with newest first within groups."""
        service = NotificationService(db_session)
        now = datetime.now(timezone.utc)

        # Create read notification (older)
        n1 = Notification(
            user_id=sample_user_a.id,
            event_type="test_1",
            title="Read Notification 1",
            body="First read",
            is_read=True,
            read_at=now - timedelta(minutes=10),
            created_at=now - timedelta(minutes=30),
        )
        # Create unread notification (older)
        n2 = Notification(
            user_id=sample_user_a.id,
            event_type="test_2",
            title="Unread Notification 1",
            body="First unread",
            is_read=False,
            created_at=now - timedelta(minutes=20),
        )
        # Create unread notification (newer)
        n3 = Notification(
            user_id=sample_user_a.id,
            event_type="test_3",
            title="Unread Notification 2",
            body="Second unread",
            is_read=False,
            created_at=now - timedelta(minutes=5),
        )
        db_session.add_all([n1, n2, n3])
        db_session.commit()

        res = service.list_user_notifications(user_id=sample_user_a.id, page=1, page_size=10)

        assert res.total == 3
        assert res.unread_count == 2
        # Check ordering: n3 (unread, newer) -> n2 (unread, older) -> n1 (read)
        assert res.items[0].id == n3.id
        assert res.items[1].id == n2.id
        assert res.items[2].id == n1.id

    def test_list_notifications_pagination(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Pagination metadata (total, total_pages, page, page_size) correctly limits returned items."""
        service = NotificationService(db_session)
        for i in range(5):
            service.create_notification(
                user_id=sample_user_a.id,
                event_type="test",
                title=f"Notification {i}",
                body=f"Body {i}",
            )

        # Page 1 with page_size=2
        page1 = service.list_user_notifications(user_id=sample_user_a.id, page=1, page_size=2)
        assert len(page1.items) == 2
        assert page1.total == 5
        assert page1.total_pages == 3
        assert page1.page == 1

        # Page 3 with page_size=2 (only 1 remaining item)
        page3 = service.list_user_notifications(user_id=sample_user_a.id, page=3, page_size=2)
        assert len(page3.items) == 1
        assert page3.total == 5

    def test_list_notifications_filter_unread_only(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """unread_only flag filters out read notifications."""
        service = NotificationService(db_session)
        n_unread = service.create_notification(
            user_id=sample_user_a.id, event_type="test", title="Unread", body="Unread body"
        )
        n_read = service.create_notification(
            user_id=sample_user_a.id, event_type="test", title="Read", body="Read body"
        )
        service.mark_as_read(n_read.id, sample_user_a.id)

        res = service.list_user_notifications(
            user_id=sample_user_a.id, page=1, page_size=10, unread_only=True
        )
        assert len(res.items) == 1
        assert res.items[0].id == n_unread.id
        assert res.total == 1
        assert res.unread_count == 1

    def test_mark_as_read_success_and_idempotency(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Marking as read sets is_read and read_at; repeated calls succeed idempotently."""
        service = NotificationService(db_session)
        notif = service.create_notification(
            user_id=sample_user_a.id, event_type="test", title="Title", body="Body"
        )
        assert notif.is_read is False

        # First read call
        updated = service.mark_as_read(notif.id, sample_user_a.id)
        assert updated.is_read is True
        assert updated.read_at is not None
        initial_read_at = updated.read_at

        # Second read call (idempotent)
        repeated = service.mark_as_read(notif.id, sample_user_a.id)
        assert repeated.is_read is True
        assert repeated.read_at == initial_read_at


# ===========================================================================
# 2. Authorization & Scoping Isolation
# ===========================================================================


class TestNotificationSecurityAndScoping:
    """Verify strict tenant isolation across different users."""

    def test_user_cannot_access_other_users_notifications(
        self, db_session: Session, sample_user_a: User, sample_user_b: User
    ) -> None:
        """User A's inbox does not show User B's notifications."""
        service = NotificationService(db_session)
        service.create_notification(
            user_id=sample_user_a.id, event_type="a", title="For A", body="A body"
        )
        service.create_notification(
            user_id=sample_user_b.id, event_type="b", title="For B", body="B body"
        )

        inbox_a = service.list_user_notifications(sample_user_a.id)
        assert inbox_a.total == 1
        assert inbox_a.items[0].title == "For A"

        inbox_b = service.list_user_notifications(sample_user_b.id)
        assert inbox_b.total == 1
        assert inbox_b.items[0].title == "For B"

    def test_user_cannot_mark_other_users_notification_as_read(
        self, db_session: Session, sample_user_a: User, sample_user_b: User
    ) -> None:
        """Attempting to mark another user's notification raises 403 Forbidden."""
        service = NotificationService(db_session)
        notif_a = service.create_notification(
            user_id=sample_user_a.id, event_type="a", title="For A", body="A body"
        )

        # User B attempts to mark User A's notification
        with pytest.raises(HTTPException) as exc_info:
            service.mark_as_read(notif_a.id, sample_user_b.id)
        assert exc_info.value.status_code == 403

    def test_mark_nonexistent_notification_raises_404(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Attempting to mark a nonexistent ID raises 404 Not Found."""
        service = NotificationService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            service.mark_as_read(uuid.uuid4(), sample_user_a.id)
        assert exc_info.value.status_code == 404


# ===========================================================================
# 3. Domain Event Handlers
# ===========================================================================


class TestNotificationDomainEvents:
    """Verify notification generators for domain events across the platform."""

    def test_verification_status_event(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Verification approval and rejection events generate contextual notifications."""
        service = NotificationService(db_session)

        # Approved
        n_app = service.notify_verification_status_change(sample_user_a.id, "verified")
        assert n_app.event_type == EVENT_VERIFICATION_STATUS_CHANGED
        assert n_app.reference_type == NOTIFICATION_REF_VERIFICATION
        assert "approved" in n_app.body.lower()

        # Rejected with admin notes
        n_rej = service.notify_verification_status_change(
            sample_user_a.id, "rejected", admin_notes="Tax certificate expired"
        )
        assert n_rej.event_type == EVENT_VERIFICATION_STATUS_CHANGED
        assert "Tax certificate expired" in n_rej.body

    def test_offer_events(
        self, db_session: Session, sample_user_a: User, sample_user_b: User
    ) -> None:
        """Offer lifecycle events generate contextual notifications with offer reference."""
        service = NotificationService(db_session)
        offer_id = uuid.uuid4()
        offer_num = "OFF-20261026-0001"

        # Offer received
        n_recv = service.notify_offer_received(
            recipient_id=sample_user_a.id,
            offer_id=offer_id,
            offer_number=offer_num,
            sender_label="Buyer ABC",
        )
        assert n_recv.event_type == EVENT_OFFER_RECEIVED
        assert n_recv.reference_type == NOTIFICATION_REF_OFFER
        assert n_recv.reference_id == offer_id

        # Offer accepted
        n_acc = service.notify_offer_accepted(
            sender_id=sample_user_b.id,
            offer_id=offer_id,
            offer_number=offer_num,
        )
        assert n_acc.event_type == EVENT_OFFER_ACCEPTED
        assert n_acc.user_id == sample_user_b.id

        # Offer rejected
        n_rej = service.notify_offer_rejected(
            sender_id=sample_user_b.id,
            offer_id=offer_id,
            offer_number=offer_num,
        )
        assert n_rej.event_type == EVENT_OFFER_REJECTED

    def test_order_and_amendment_events(
        self, db_session: Session, sample_user_a: User
    ) -> None:
        """Order status and amendment requests generate notifications."""
        service = NotificationService(db_session)
        order_id = uuid.uuid4()
        amend_id = uuid.uuid4()
        order_num = "ORD-20261026-0001"

        # Order status change
        n_order = service.notify_order_status_change(
            user_id=sample_user_a.id,
            order_id=order_id,
            order_number=order_num,
            new_status="delivery_arranged",
        )
        assert n_order.event_type == EVENT_ORDER_STATUS_CHANGED
        assert n_order.reference_type == NOTIFICATION_REF_ORDER
        assert "delivery_arranged" in n_order.body

        # Amendment proposed
        n_amend = service.notify_amendment_proposed(
            user_id=sample_user_a.id,
            order_id=order_id,
            amendment_id=amend_id,
            order_number=order_num,
            amendment_type="delivery_date",
        )
        assert n_amend.event_type == EVENT_AMENDMENT_PROPOSED
        assert "delivery_date" in n_amend.body

    def test_payment_events(
        self, db_session: Session, sample_user_a: User, sample_user_b: User
    ) -> None:
        """Payment recording and acknowledgement events generate notifications."""
        service = NotificationService(db_session)
        order_id = uuid.uuid4()
        pay_id = uuid.uuid4()
        order_num = "ORD-20261026-0001"

        # Farmer notified of payment recorded
        n_pay = service.notify_payment_recorded(
            farmer_id=sample_user_a.id,
            order_id=order_id,
            payment_id=pay_id,
            order_number=order_num,
            amount_display="INR 50,000.00",
        )
        assert n_pay.event_type == EVENT_PAYMENT_RECORDED
        assert n_pay.user_id == sample_user_a.id
        assert "INR 50,000.00" in n_pay.body

        # Buyer notified of payment acknowledgement
        n_ack = service.notify_payment_acknowledged(
            buyer_id=sample_user_b.id,
            order_id=order_id,
            payment_id=pay_id,
            order_number=order_num,
        )
        assert n_ack.event_type == EVENT_PAYMENT_ACKNOWLEDGED
        assert n_ack.user_id == sample_user_b.id

    def test_email_notification_gated_by_feature_flag(self) -> None:
        """Email dispatcher returns False when feature flag is off without throwing exceptions."""
        result = send_email_notification(
            to_email="test@agridirect.test",
            subject="Test Subject",
            body="Test Body",
        )
        assert result is False  # Feature flag disabled by default
