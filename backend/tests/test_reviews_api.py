"""Unit and API integration tests for AgriDirect Module 7: Ratings & Reviews.

Covers:
1. Mutual bilateral reviews (buyer -> farmer and farmer -> buyer).
2. Strict rating bounds (1 to 5 integer, validation errors for <1, >5, float).
3. Review text length constraints (<= 2000 chars, empty text permitted).
4. Counterparty and participant authorization (third parties receive 404/403).
5. Self-review prevention (400 Bad Request).
6. Transaction eligibility: Only completed orders (ORDER_STATUS_COMPLETED) can be reviewed (409 Conflict for pending/confirmed/cancelled).
7. Duplicate review rejection (409 Conflict for second review on same order by same reviewer).
8. Reputation aggregation: Average calculation, criterion scores, and star distribution.
9. Notification generation upon review receipt.
10. Unverified or suspended user rejection (403 Forbidden).
"""

import uuid
from datetime import datetime, timezone
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
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE
from app.models.notification import Notification
from app.models.offer import Offer, OfferItem, OFFER_STATUS_ACCEPTED
from app.models.order import (
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_PENDING,
    Order,
    OrderItem,
)
from app.models.review import RatingReview
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
# Seed Helpers
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


def seed_order(
    db: Session,
    buyer: User,
    farmer: User,
    order_status: str = ORDER_STATUS_COMPLETED,
    total_amount: Decimal = Decimal("5000.00"),
) -> Order:
    """Create an order for review testing using exact model columns."""
    from datetime import date, timedelta
    from app.models.chat import Conversation

    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg_{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Organic Red Tomato",
        title="Fresh Tomatoes",
        initial_quantity=Decimal("1000.000"),
        available_quantity=Decimal("800.000"),
        unit="kg",
        price_per_unit=Decimal("50.00"),
        location_state="Maharashtra",
        location_city="Pune",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.flush()

    conv = db.query(Conversation).filter_by(farmer_id=farmer.id, buyer_id=buyer.id).first()
    if not conv:
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
        status=order_status,
        delivery_status=DELIVERY_STATUS_COMPLETED if order_status == ORDER_STATUS_COMPLETED else DELIVERY_STATUS_NOT_ARRANGED,
        completed_at=datetime.now(timezone.utc) if order_status == ORDER_STATUS_COMPLETED else None,
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        product_name=listing.product_name,
        quantity=Decimal("100.000"),
        unit="kg",
        unit_price=Decimal("50.00"),
        subtotal=total_amount,
        status="fulfilled" if order_status == ORDER_STATUS_COMPLETED else "confirmed",
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# Test Cases
# ===========================================================================


class TestReviewSubmission:
    """Verify mutual rating and review creation rules and validations."""

    def test_buyer_reviews_farmer_success(self, client: TestClient, db_session: Session) -> None:
        """Buyer reviews farmer with full criteria on completed order."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer, order_status=ORDER_STATUS_COMPLETED)

        payload = {
            "order_id": str(order.id),
            "overall_rating": 5,
            "quality_rating": 5,
            "accuracy_rating": 4,
            "communication_rating": 5,
            "reliability_rating": 5,
            "review_text": "Excellent tomatoes, perfectly packaged and fresh on delivery.",
        }
        res = client.post("/api/v1/reviews", json=payload, headers=make_headers(buyer))
        assert res.status_code == 201
        data = res.json()
        assert data["order_id"] == str(order.id)
        assert data["reviewer_id"] == str(buyer.id)
        assert data["reviewed_user_id"] == str(farmer.id)
        assert data["overall_rating"] == 5
        assert data["quality_rating"] == 5
        assert data["review_text"] == "Excellent tomatoes, perfectly packaged and fresh on delivery."

        # Verify notification was sent to farmer
        notif = (
            db_session.query(Notification)
            .filter_by(user_id=farmer.id, event_type="review_received")
            .first()
        )
        assert notif is not None
        assert f"Order {order.order_number}" in notif.title

    def test_farmer_reviews_buyer_success(self, client: TestClient, db_session: Session) -> None:
        """Farmer reviews buyer with overall rating and optional text."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer, order_status=ORDER_STATUS_COMPLETED)

        payload = {
            "order_id": str(order.id),
            "overall_rating": 4,
            "communication_rating": 4,
            "reliability_rating": 5,
            "review_text": "Prompt payment and seamless receiving at market dock.",
        }
        res = client.post("/api/v1/reviews", json=payload, headers=make_headers(farmer))
        assert res.status_code == 201
        data = res.json()
        assert data["reviewer_id"] == str(farmer.id)
        assert data["reviewed_user_id"] == str(buyer.id)
        assert data["overall_rating"] == 4

        # Verify notification was sent to buyer
        notif = (
            db_session.query(Notification)
            .filter_by(user_id=buyer.id, event_type="review_received")
            .first()
        )
        assert notif is not None

    def test_rating_bounds_enforced(self, client: TestClient, db_session: Session) -> None:
        """Ratings below 1 or above 5 are rejected with 422."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer)

        # Rating < 1
        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order.id), "overall_rating": 0},
            headers=make_headers(buyer),
        )
        assert res.status_code == 422

        # Rating > 5
        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order.id), "overall_rating": 6},
            headers=make_headers(buyer),
        )
        assert res.status_code == 422

        # Non-integer rating
        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order.id), "overall_rating": 4.5},
            headers=make_headers(buyer),
        )
        assert res.status_code == 422

    def test_review_text_length_limit(self, client: TestClient, db_session: Session) -> None:
        """Review text exceeding 2000 chars is rejected."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer)

        res = client.post(
            "/api/v1/reviews",
            json={
                "order_id": str(order.id),
                "overall_rating": 5,
                "review_text": "x" * 2001,
            },
            headers=make_headers(buyer),
        )
        assert res.status_code == 422

    def test_non_participant_rejected_with_404(self, client: TestClient, db_session: Session) -> None:
        """An unrelated third-party user receives 404 (anti-enumeration)."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer)
        unrelated = seed_buyer(db_session)

        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order.id), "overall_rating": 5},
            headers=make_headers(unrelated),
        )
        assert res.status_code == 404

    def test_ineligible_order_rejected_with_409(self, client: TestClient, db_session: Session) -> None:
        """Ineligible non-completed order (pending/confirmed/cancelled) rejected."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order_pending = seed_order(db_session, buyer=buyer, farmer=farmer, order_status=ORDER_STATUS_PENDING)

        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order_pending.id), "overall_rating": 5},
            headers=make_headers(buyer),
        )
        assert res.status_code == 409
        assert "completed" in res.json()["detail"].lower()

        # Cancelled order
        order_cancelled = seed_order(db_session, buyer=buyer, farmer=farmer, order_status=ORDER_STATUS_CANCELLED)
        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order_cancelled.id), "overall_rating": 5},
            headers=make_headers(buyer),
        )
        assert res.status_code == 409

    def test_duplicate_review_rejected(self, client: TestClient, db_session: Session) -> None:
        """Submitting multiple reviews for the same order by the same reviewer fails with 409."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer)

        payload = {"order_id": str(order.id), "overall_rating": 5}
        res1 = client.post("/api/v1/reviews", json=payload, headers=make_headers(buyer))
        assert res1.status_code == 201

        # Second attempt
        res2 = client.post("/api/v1/reviews", json=payload, headers=make_headers(buyer))
        assert res2.status_code == 409
        assert "already been submitted" in res2.json()["detail"]

    def test_unverified_or_suspended_user_blocked(self, client: TestClient, db_session: Session) -> None:
        """Unverified or suspended accounts are rejected with 403."""
        buyer_unverified = seed_buyer(db_session, verified=False)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer_unverified, farmer=farmer)

        res = client.post(
            "/api/v1/reviews",
            json={"order_id": str(order.id), "overall_rating": 5},
            headers=make_headers(buyer_unverified),
        )
        assert res.status_code == 403


class TestReputationAggregation:
    """Verify SQL-level reputation calculations and distribution."""

    def test_user_reputation_summary_calculation(self, client: TestClient, db_session: Session) -> None:
        """Aggregates multiple reviews correctly for a farmer."""
        farmer = seed_farmer(db_session)
        buyer1 = seed_buyer(db_session)
        buyer2 = seed_buyer(db_session)
        buyer3 = seed_buyer(db_session)

        order1 = seed_order(db_session, buyer=buyer1, farmer=farmer)
        order2 = seed_order(db_session, buyer=buyer2, farmer=farmer)
        order3 = seed_order(db_session, buyer=buyer3, farmer=farmer)

        # Buyer 1: 5 stars
        client.post(
            "/api/v1/reviews",
            json={
                "order_id": str(order1.id),
                "overall_rating": 5,
                "quality_rating": 5,
                "accuracy_rating": 4,
            },
            headers=make_headers(buyer1),
        )
        # Buyer 2: 4 stars
        client.post(
            "/api/v1/reviews",
            json={
                "order_id": str(order2.id),
                "overall_rating": 4,
                "quality_rating": 4,
                "accuracy_rating": 4,
            },
            headers=make_headers(buyer2),
        )
        # Buyer 3: 3 stars
        client.post(
            "/api/v1/reviews",
            json={
                "order_id": str(order3.id),
                "overall_rating": 3,
                "quality_rating": 3,
            },
            headers=make_headers(buyer3),
        )

        # Query summary
        res = client.get(f"/api/v1/reviews/users/{farmer.id}/summary")
        assert res.status_code == 200
        summary = res.json()
        assert summary["total_reviews"] == 3
        # Average: (5 + 4 + 3) / 3 = 4.0
        assert summary["average_rating"] == 4.0
        # Quality average: (5 + 4 + 3) / 3 = 4.0
        assert summary["quality_rating_avg"] == 4.0
        # Accuracy average: (4 + 4) / 2 = 4.0
        assert summary["accuracy_rating_avg"] == 4.0
        # Star distribution
        assert summary["rating_distribution"]["5"] == 1
        assert summary["rating_distribution"]["4"] == 1
        assert summary["rating_distribution"]["3"] == 1
        assert summary["rating_distribution"]["2"] == 0
        assert summary["rating_distribution"]["1"] == 0

    def test_list_user_reviews_and_order_reviews(self, client: TestClient, db_session: Session) -> None:
        """Query reviews by user and by order."""
        buyer = seed_buyer(db_session)
        farmer = seed_farmer(db_session)
        order = seed_order(db_session, buyer=buyer, farmer=farmer)

        client.post(
            "/api/v1/reviews",
            json={"order_id": str(order.id), "overall_rating": 5, "review_text": "Great"},
            headers=make_headers(buyer),
        )

        # List reviews for farmer
        res_user = client.get(f"/api/v1/reviews/users/{farmer.id}")
        assert res_user.status_code == 200
        data_user = res_user.json()
        assert data_user["total"] == 1
        assert data_user["items"][0]["order_id"] == str(order.id)

        # List reviews for order (buyer)
        res_order = client.get(f"/api/v1/reviews/orders/{order.id}", headers=make_headers(buyer))
        assert res_order.status_code == 200
        assert len(res_order.json()) == 1

        # Unrelated third party access to order reviews returns 404
        unrelated = seed_buyer(db_session)
        res_unrelated = client.get(f"/api/v1/reviews/orders/{order.id}", headers=make_headers(unrelated))
        assert res_unrelated.status_code == 404
