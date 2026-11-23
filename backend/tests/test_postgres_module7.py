"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 7: Ratings, Reviews & Notifications.

Verifies Module 7 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`.

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
from app.models.chat import Conversation
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE
from app.models.notification import Notification
from app.models.offer import Offer, OfferItem, OFFER_STATUS_ACCEPTED
from app.models.order import (
    DELIVERY_STATUS_COMPLETED,
    ORDER_STATUS_COMPLETED,
    Order,
    OrderItem,
)
from app.models.review import RatingReview
from app.models.user import BuyerProfile, FarmerProfile, User
from app.notifications.repository import NotificationRepository
from app.reviews.repository import ReviewRepository
from app.reviews.schemas import ReviewCreate
from app.reviews.service import ReviewService

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
    """Ensure database is clean before and after each test."""
    _cleanup_database()
    yield
    _cleanup_database()


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


def seed_pg_completed_order(
    db: Session,
    buyer: User,
    farmer: User,
    total_amount: Decimal = Decimal("10000.00"),
) -> Order:
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
        status=ORDER_STATUS_COMPLETED,
        delivery_status=DELIVERY_STATUS_COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        product_name=listing.product_name,
        quantity=Decimal("400.000"),
        unit="kg",
        unit_price=Decimal("25.00"),
        subtotal=total_amount,
        status="fulfilled",
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# Tests: Module 7 on PostgreSQL
# ---------------------------------------------------------------------------


def test_pg_schema_and_migration_revisions(pg_session: Session) -> None:
    """Verify test database is agridirect_module3_test and alembic version is up to date."""
    db_name = pg_session.execute(text("SELECT current_database()")).scalar()
    assert db_name == "agridirect_module3_test"

    rev = pg_session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert rev in ("a1b2c3d4e5f6", "f6a1b2c3d4e5", "e5f6a1b2c3d4", "fcf5c991d506", "b2c3d4e5f6a1")


def test_pg_self_review_constraint_enforcement(pg_session: Session) -> None:
    """chk_reviewer_different rejects reviewer_id == reviewed_user_id in PostgreSQL."""
    farmer = seed_pg_farmer(pg_session)
    buyer = seed_pg_buyer(pg_session)
    order = seed_pg_completed_order(pg_session, buyer=buyer, farmer=farmer)

    bad_review = RatingReview(
        order_id=order.id,
        reviewer_id=farmer.id,
        reviewed_user_id=farmer.id,  # Same user
        overall_rating=5,
    )
    pg_session.add(bad_review)
    with pytest.raises(IntegrityError) as exc_info:
        pg_session.commit()
    assert "chk_reviewer_different" in str(exc_info.value)
    pg_session.rollback()


def test_pg_rating_bounds_check_constraint(pg_session: Session) -> None:
    """chk_reviews_overall_rating rejects values outside 1-5 in PostgreSQL."""
    farmer = seed_pg_farmer(pg_session)
    buyer = seed_pg_buyer(pg_session)
    order = seed_pg_completed_order(pg_session, buyer=buyer, farmer=farmer)

    bad_review = RatingReview(
        order_id=order.id,
        reviewer_id=buyer.id,
        reviewed_user_id=farmer.id,
        overall_rating=6,  # > 5
    )
    pg_session.add(bad_review)
    with pytest.raises(IntegrityError) as exc_info:
        pg_session.commit()
    assert "chk_reviews_overall_rating" in str(exc_info.value)
    pg_session.rollback()


def test_pg_concurrent_duplicate_review_prevention(pg_session: Session) -> None:
    """Two concurrent threads attempting to review the same order for the same reviewer.

    PostgreSQL unique constraint 'uq_order_reviewer' ensures exactly one transaction succeeds
    and the other fails with a unique constraint violation.
    """
    farmer = seed_pg_farmer(pg_session)
    buyer = seed_pg_buyer(pg_session)
    order = seed_pg_completed_order(pg_session, buyer=buyer, farmer=farmer)

    results: List[str] = []
    barrier = threading.Barrier(2)

    def attempt_review(rating_val: int) -> None:
        with _SessionLocal() as session:
            barrier.wait()
            try:
                review = RatingReview(
                    order_id=order.id,
                    reviewer_id=buyer.id,
                    reviewed_user_id=farmer.id,
                    overall_rating=rating_val,
                )
                session.add(review)
                session.commit()
                results.append("SUCCESS")
            except IntegrityError:
                session.rollback()
                results.append("INTEGRITY_ERROR")

    t1 = threading.Thread(target=attempt_review, args=(5,))
    t2 = threading.Thread(target=attempt_review, args=(4,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert "SUCCESS" in results
    assert "INTEGRITY_ERROR" in results
    assert len(results) == 2

    # Exactly one review recorded in PostgreSQL
    with _SessionLocal() as session:
        count = session.query(RatingReview).filter_by(order_id=order.id, reviewer_id=buyer.id).count()
        assert count == 1


def test_pg_sql_reputation_aggregation(pg_session: Session) -> None:
    """Verifies ReviewRepository SQL-level aggregation on PostgreSQL 18.6."""
    farmer = seed_pg_farmer(pg_session)
    buyer1 = seed_pg_buyer(pg_session)
    buyer2 = seed_pg_buyer(pg_session)

    order1 = seed_pg_completed_order(pg_session, buyer=buyer1, farmer=farmer)
    order2 = seed_pg_completed_order(pg_session, buyer=buyer2, farmer=farmer)

    repo = ReviewRepository(pg_session)
    repo.create(
        ReviewCreate(order_id=order1.id, overall_rating=5, quality_rating=5, accuracy_rating=5),
        reviewer_id=buyer1.id,
        reviewed_user_id=farmer.id,
    )
    repo.create(
        ReviewCreate(order_id=order2.id, overall_rating=3, quality_rating=3, accuracy_rating=3),
        reviewer_id=buyer2.id,
        reviewed_user_id=farmer.id,
    )
    pg_session.commit()

    summary = repo.get_user_reputation_summary(farmer.id)
    assert summary["total_reviews"] == 2
    assert summary["average_rating"] == 4.0
    assert summary["quality_rating_avg"] == 4.0
    assert summary["accuracy_rating_avg"] == 4.0
    assert summary["rating_distribution"]["5"] == 1
    assert summary["rating_distribution"]["3"] == 1
    assert summary["rating_distribution"]["1"] == 0


def test_pg_notifications_and_bulk_read(pg_session: Session) -> None:
    """Test notification persistence and bulk mark-all-read in PostgreSQL."""
    buyer = seed_pg_buyer(pg_session)
    repo = NotificationRepository(pg_session)

    # Insert 3 unread notifications
    for i in range(3):
        n = Notification(
            user_id=buyer.id,
            event_type="test_alert",
            title=f"Alert {i}",
            body=f"Test alert body {i}",
            is_read=False,
        )
        pg_session.add(n)
    pg_session.commit()

    assert repo.count_unread_for_user(buyer.id) == 3

    # Mark all read
    marked = repo.mark_all_as_read(buyer.id)
    pg_session.commit()
    assert marked == 3
    assert repo.count_unread_for_user(buyer.id) == 0

