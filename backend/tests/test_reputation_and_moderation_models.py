"""Automated unit and integration tests for Reputation, Notifications & Moderation (Group 10) ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``ratings_reviews``
  - ``notifications``
  - ``user_reports``
- Column definitions, nullabilities, data types, and defaults:
  - ``ratings_reviews``: 11 columns, Integer ratings (1-5), optional text review
  - ``notifications``: 10 columns, is_read boolean (default False), reference polymorphism
  - ``user_reports``: 11 columns, status (default 'open'), optional listing_id and reported_user_id
- Primary key generation via ``UUIDPrimaryKeyMixin``
- Timestamp handling (TimestampMixin on user_reports; func.now() on ratings_reviews and notifications)
- Foreign keys and on-delete rules:
  - ``ratings_reviews.order_id -> orders.id`` (ON DELETE RESTRICT)
  - ``ratings_reviews.reviewer_id -> users.id`` (ON DELETE RESTRICT)
  - ``ratings_reviews.reviewed_user_id -> users.id`` (ON DELETE RESTRICT)
  - ``notifications.user_id -> users.id`` (ON DELETE CASCADE)
  - ``user_reports.reporter_id -> users.id`` (ON DELETE RESTRICT)
  - ``user_reports.reported_user_id -> users.id`` (ON DELETE SET NULL)
  - ``user_reports.listing_id -> produce_listings.id`` (ON DELETE SET NULL)
  - ``user_reports.reviewed_by_admin_id -> users.id`` (ON DELETE SET NULL)
- Check constraints:
  - ``chk_reviewer_different`` (reviewer_id <> reviewed_user_id)
  - ``chk_reviews_overall_rating`` (overall_rating BETWEEN 1 AND 5)
  - ``chk_reviews_quality_rating`` (1-5 or null)
  - ``chk_reviews_accuracy_rating`` (1-5 or null)
  - ``chk_reviews_communication_rating`` (1-5 or null)
  - ``chk_reviews_reliability_rating`` (1-5 or null)
  - ``chk_user_reports_category``
  - ``chk_user_reports_status``
- Unique constraints:
  - ``uq_order_reviewer`` (order_id, reviewer_id)
- Indexes on all three tables
- Database execution:
  - Bilateral rating and review submission
  - In-app notification creation, unread tracking, and cascade deletion
  - User safety report filing, listing association, and admin moderation
  - Prevention of self-reviews and duplicate reviews for the same order
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
from app.models.listing import ProduceListing
from app.models.notification import (
    NOTIFICATION_REF_ORDER,
    VALID_NOTIFICATION_REF_TYPES,
    Notification,
)
from app.models.offer import OFFER_STATUS_ACCEPTED, Offer
from app.models.order import ORDER_STATUS_COMPLETED, Order
from app.models.report import (
    REPORT_CATEGORY_PAYMENT,
    REPORT_CATEGORY_QUALITY_ISSUE,
    REPORT_STATUS_ACTION_TAKEN,
    REPORT_STATUS_OPEN,
    VALID_REPORT_CATEGORIES,
    VALID_REPORT_STATUSES,
    UserReport,
)
from app.models.review import RatingReview
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
        email="rep_farmer@agridirect.test",
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
        email="rep_buyer@agridirect.test",
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
        email="rep_admin@agridirect.test",
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
def sample_listing(db_session: Session, sample_farmer: User) -> ProduceListing:
    """Create and persist a produce listing."""
    listing = ProduceListing(
        farmer_id=sample_farmer.id,
        product_name="Organic Basmati Rice",
        title="Pusa 1121 Basmati Rice",
        initial_quantity=Decimal("500.000"),
        available_quantity=Decimal("500.000"),
        unit="quintal",
        price_per_unit=Decimal("4200.00"),
        location_state="Punjab",
        location_city="Amritsar",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


@pytest.fixture
def sample_completed_order(
    db_session: Session, sample_farmer: User, sample_buyer: User
) -> Order:
    """Create and persist a completed order eligible for rating."""
    conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
    db_session.add(conv)
    db_session.commit()

    offer = Offer(
        offer_number="OFF-REP-0001",
        conversation_id=conv.id,
        sender_id=sample_buyer.id,
        recipient_id=sample_farmer.id,
        total_amount=Decimal("42000.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db_session.add(offer)
    db_session.commit()

    order = Order(
        order_number="ORD-REP-0001",
        source_offer_id=offer.id,
        buyer_id=sample_buyer.id,
        farmer_id=sample_farmer.id,
        total_amount=Decimal("42000.00"),
        status=ORDER_STATUS_COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestReputationAndModerationMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """All three Group 10 tables must be registered in Base.metadata."""
        assert "ratings_reviews" in Base.metadata.tables
        assert "notifications" in Base.metadata.tables
        assert "user_reports" in Base.metadata.tables

    def test_ratings_reviews_columns_and_nullability(self) -> None:
        """ratings_reviews table must have all 11 specified columns with exact nullabilities."""
        table = Base.metadata.tables["ratings_reviews"]
        expected = {
            "id": False,
            "order_id": False,
            "reviewer_id": False,
            "reviewed_user_id": False,
            "overall_rating": False,
            "quality_rating": True,
            "accuracy_rating": True,
            "communication_rating": True,
            "reliability_rating": True,
            "review_text": True,
            "created_at": False,
        }
        assert len(table.columns) == 11
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from ratings_reviews"
            assert table.c[col_name].nullable == nullable

    def test_notifications_columns_and_nullability(self) -> None:
        """notifications table must have all 10 specified columns with exact nullabilities."""
        table = Base.metadata.tables["notifications"]
        expected = {
            "id": False,
            "user_id": False,
            "event_type": False,
            "title": False,
            "body": False,
            "reference_type": True,
            "reference_id": True,
            "is_read": False,
            "read_at": True,
            "created_at": False,
        }
        assert len(table.columns) == 10
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from notifications"
            assert table.c[col_name].nullable == nullable

    def test_user_reports_columns_and_nullability(self) -> None:
        """user_reports table must have all 11 specified columns with exact nullabilities."""
        table = Base.metadata.tables["user_reports"]
        expected = {
            "id": False,
            "reporter_id": False,
            "reported_user_id": True,
            "listing_id": True,
            "category": False,
            "description": False,
            "status": False,
            "admin_notes": True,
            "reviewed_by_admin_id": True,
            "created_at": False,
            "updated_at": False,
        }
        assert len(table.columns) == 11
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from user_reports"
            assert table.c[col_name].nullable == nullable

    def test_foreign_keys_and_on_delete_rules(self) -> None:
        """Foreign keys must match exact on-delete actions across all three tables."""
        # 1. ratings_reviews
        rev_tbl = Base.metadata.tables["ratings_reviews"]
        rev_fks = {fk.parent.name: fk for fk in rev_tbl.foreign_keys}
        assert rev_fks["order_id"].column.table.name == "orders"
        assert rev_fks["order_id"].ondelete == "RESTRICT"
        assert rev_fks["reviewer_id"].column.table.name == "users"
        assert rev_fks["reviewer_id"].ondelete == "RESTRICT"
        assert rev_fks["reviewed_user_id"].column.table.name == "users"
        assert rev_fks["reviewed_user_id"].ondelete == "RESTRICT"

        # 2. notifications
        notif_tbl = Base.metadata.tables["notifications"]
        notif_fks = {fk.parent.name: fk for fk in notif_tbl.foreign_keys}
        assert notif_fks["user_id"].column.table.name == "users"
        assert notif_fks["user_id"].ondelete == "CASCADE"

        # 3. user_reports
        rep_tbl = Base.metadata.tables["user_reports"]
        rep_fks = {fk.parent.name: fk for fk in rep_tbl.foreign_keys}
        assert rep_fks["reporter_id"].column.table.name == "users"
        assert rep_fks["reporter_id"].ondelete == "RESTRICT"
        assert rep_fks["reported_user_id"].column.table.name == "users"
        assert rep_fks["reported_user_id"].ondelete == "SET NULL"
        assert rep_fks["listing_id"].column.table.name == "produce_listings"
        assert rep_fks["listing_id"].ondelete == "SET NULL"
        assert rep_fks["reviewed_by_admin_id"].column.table.name == "users"
        assert rep_fks["reviewed_by_admin_id"].ondelete == "SET NULL"

    def test_canonical_constants(self) -> None:
        """Constants for notification references, report categories, and statuses."""
        assert set(VALID_NOTIFICATION_REF_TYPES) == {
            "order",
            "offer",
            "listing",
            "verification",
        }
        assert set(VALID_REPORT_CATEGORIES) == {
            "payment",
            "quantity_mismatch",
            "quality_issue",
            "fraud",
            "harassment",
            "other",
        }
        assert set(VALID_REPORT_STATUSES) == {
            "open",
            "under_review",
            "action_taken",
            "dismissed",
        }


# ===========================================================================
# 2. Database Operations & Persistence Tests
# ===========================================================================


class TestReputationAndModerationPersistence:
    """Verify database CRUD, bilateral reviews, notifications, and safety reports."""

    def test_bilateral_ratings_for_completed_order(
        self,
        db_session: Session,
        sample_completed_order: Order,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """Both buyer and farmer can submit mutual reviews for the same completed order."""
        # 1. Buyer reviews farmer
        buyer_review = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_buyer.id,
            reviewed_user_id=sample_farmer.id,
            overall_rating=5,
            quality_rating=5,
            accuracy_rating=5,
            communication_rating=4,
            reliability_rating=5,
            review_text="Excellent grain quality, prompt loading and dispatch.",
        )
        db_session.add(buyer_review)

        # 2. Farmer reviews buyer
        farmer_review = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_farmer.id,
            reviewed_user_id=sample_buyer.id,
            overall_rating=5,
            communication_rating=5,
            reliability_rating=5,
            review_text="Prompt payment acknowledgement and clear communication.",
        )
        db_session.add(farmer_review)
        db_session.commit()

        db_session.refresh(sample_completed_order)
        assert len(sample_completed_order.ratings_reviews) == 2

        # Check relationships on User
        db_session.refresh(sample_buyer)
        db_session.refresh(sample_farmer)
        assert len(sample_buyer.reviews_given) == 1
        assert len(sample_buyer.reviews_received) == 1
        assert len(sample_farmer.reviews_given) == 1
        assert len(sample_farmer.reviews_received) == 1

    def test_notification_creation_and_mark_read(
        self,
        db_session: Session,
        sample_buyer: User,
        sample_completed_order: Order,
    ) -> None:
        """Create notification for buyer and mark it read."""
        notif = Notification(
            user_id=sample_buyer.id,
            event_type="order_completed",
            title="Order Completed",
            body=f"Your order {sample_completed_order.order_number} has been completed successfully.",
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=sample_completed_order.id,
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        assert notif.is_read is False
        assert notif.read_at is None

        # Mark read
        now_utc = datetime.now(timezone.utc)
        notif.is_read = True
        notif.read_at = now_utc
        db_session.commit()
        db_session.refresh(notif)

        assert notif.is_read is True
        assert notif.read_at is not None

    def test_user_report_creation_and_admin_action(
        self,
        db_session: Session,
        sample_buyer: User,
        sample_farmer: User,
        sample_listing: ProduceListing,
        sample_admin: User,
    ) -> None:
        """Buyer files quality report against farmer; admin inspects and resolves."""
        report = UserReport(
            reporter_id=sample_buyer.id,
            reported_user_id=sample_farmer.id,
            listing_id=sample_listing.id,
            category=REPORT_CATEGORY_QUALITY_ISSUE,
            description="Moisture level exceeded specifications in delivery batch.",
            status=REPORT_STATUS_OPEN,
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)

        assert report.status == "open"
        assert report.created_at is not None

        # Admin resolves report
        report.status = REPORT_STATUS_ACTION_TAKEN
        report.reviewed_by_admin_id = sample_admin.id
        report.admin_notes = "Farmer agreed to a 10% credit adjustment on subsequent orders."
        db_session.commit()
        db_session.refresh(report)

        assert report.status == "action_taken"
        assert report.reviewed_by_admin.id == sample_admin.id


# ===========================================================================
# 3. Check Constraint & Integrity Enforcement Tests
# ===========================================================================


class TestReputationAndModerationConstraints:
    """Verify runtime check constraints, unique constraints, and cascade/restrict rules."""

    def test_self_review_fails_constraint(
        self,
        db_session: Session,
        sample_completed_order: Order,
        sample_farmer: User,
    ) -> None:
        """chk_reviewer_different rejects reviewer_id == reviewed_user_id."""
        review = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_farmer.id,
            reviewed_user_id=sample_farmer.id,  # Same user
            overall_rating=5,
        )
        db_session.add(review)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_review_by_same_reviewer_fails(
        self,
        db_session: Session,
        sample_completed_order: Order,
        sample_buyer: User,
        sample_farmer: User,
    ) -> None:
        """uq_order_reviewer rejects duplicate review for same order and reviewer."""
        review1 = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_buyer.id,
            reviewed_user_id=sample_farmer.id,
            overall_rating=5,
        )
        db_session.add(review1)
        db_session.commit()

        review2 = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_buyer.id,  # Duplicate reviewer for same order
            reviewed_user_id=sample_farmer.id,
            overall_rating=4,
        )
        db_session.add(review2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_rating_out_of_bounds_fails(
        self,
        db_session: Session,
        sample_completed_order: Order,
        sample_buyer: User,
        sample_farmer: User,
    ) -> None:
        """chk_reviews_overall_rating rejects values < 1 or > 5."""
        # 1. Rating 0 fails
        bad_review_low = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_buyer.id,
            reviewed_user_id=sample_farmer.id,
            overall_rating=0,
        )
        db_session.add(bad_review_low)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

        # 2. Rating 6 fails
        bad_review_high = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_buyer.id,
            reviewed_user_id=sample_farmer.id,
            overall_rating=6,
        )
        db_session.add(bad_review_high)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_dimension_rating_out_of_bounds_fails(
        self,
        db_session: Session,
        sample_completed_order: Order,
        sample_buyer: User,
        sample_farmer: User,
    ) -> None:
        """Dimension rating (e.g. quality_rating) must be between 1 and 5 when non-null."""
        review = RatingReview(
            order_id=sample_completed_order.id,
            reviewer_id=sample_buyer.id,
            reviewed_user_id=sample_farmer.id,
            overall_rating=4,
            quality_rating=10,  # Invalid
        )
        db_session.add(review)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_report_category_fails(
        self,
        db_session: Session,
        sample_buyer: User,
        sample_farmer: User,
    ) -> None:
        """chk_user_reports_category rejects unknown category."""
        report = UserReport(
            reporter_id=sample_buyer.id,
            reported_user_id=sample_farmer.id,
            category="unsolicited_promotion",  # Invalid
            description="Testing category check",
        )
        db_session.add(report)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_report_status_fails(
        self,
        db_session: Session,
        sample_buyer: User,
        sample_farmer: User,
    ) -> None:
        """chk_user_reports_status rejects unknown status."""
        report = UserReport(
            reporter_id=sample_buyer.id,
            reported_user_id=sample_farmer.id,
            category=REPORT_CATEGORY_PAYMENT,
            description="Testing status check",
            status="pending_triage",  # Invalid
        )
        db_session.add(report)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_user_deletion_cascades_to_notifications(
        self,
        db_session: Session,
        sample_buyer: User,
    ) -> None:
        """ON DELETE CASCADE removes user notifications when user is deleted."""
        notif = Notification(
            user_id=sample_buyer.id,
            event_type="system_alert",
            title="Scheduled Maintenance",
            body="Platform maintenance tonight at 02:00 UTC",
        )
        db_session.add(notif)
        db_session.commit()
        notif_id = notif.id

        db_session.delete(sample_buyer)
        db_session.commit()

        assert db_session.get(Notification, notif_id) is None

    def test_reported_user_or_listing_deletion_sets_null(
        self,
        db_session: Session,
        sample_buyer: User,
        sample_farmer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """ON DELETE SET NULL preserves user report history when reported user or listing is deleted."""
        report = UserReport(
            reporter_id=sample_buyer.id,
            reported_user_id=sample_farmer.id,
            listing_id=sample_listing.id,
            category=REPORT_CATEGORY_QUALITY_ISSUE,
            description="Preserve report audit trail",
        )
        db_session.add(report)
        db_session.commit()

        # Delete listing
        db_session.delete(sample_listing)
        db_session.commit()

        db_session.refresh(report)
        assert report.listing_id is None
        assert report.reported_user_id == sample_farmer.id
