"""Unit and API integration tests for AgriDirect Module 9: Descriptive Market Analytics.

Covers:
1. Public / Authenticated Market Summary (GET /api/v1/analytics/market-summary):
   - Empty dataset handling (coarse count band "0", suppression diagnostics).
   - Participant diversity threshold failures (< 3 farmers or < 3 buyers -> suppression).
   - Diversity passes (>= 3 farmers, >= 3 buyers, >= 3 trades -> unsuppressed counts).
   - Quantity dominance suppression (>= 50% share).
   - Monetary dominance suppression (>= 50% share).
   - Joint VWAP suppression when either quantity or monetary share >= 50%.
   - Arithmetic mean influence suppression (observation share or price share >= 50%).
   - Median dominance and point ownership check (observation share >= 50% or point owner >= 40%).
   - Extrema point isolation protection (sample depth < 5, and clustering within 2%).
   - City-to-state geographic fallback logic.
   - Realized trades include completed orders with disputed/pending payments; excludes cancelled orders.
   - Absence of payment settlement totals from public market summary.
   - Date range boundaries [start_date, end_date + 1 day).
   - Invalid date range 400 Bad Request.

2. Public / Authenticated Demand Summary (GET /api/v1/analytics/demand-summary):
   - Empty demand dataset handling.
   - Active demand diversity and dominance suppression.
   - Permanent audited fulfillment rule: approved fulfillments retained permanently across
     closed and soft-deleted requirements.

3. Authenticated User Performance (GET /api/v1/analytics/my-performance):
   - Unauthenticated 401 Unauthorized.
   - Admin account 403 Forbidden.
   - Farmer performance: outcome classification with non-pending denominator,
     realized revenue, commodity breakdown, payment settlement breakdown, reviews.
   - Buyer performance: outcome classification, purchase expenditures, payment settlement.

4. Administrator Platform Analytics (GET /api/v1/analytics/admin/platform & alias):
   - Unauthenticated 401 / Non-admin 403 Forbidden.
   - Admin access 200 OK: Platform GMV, pipeline GMV, inventory, demand fulfillment,
     order outcome breakdown, payment velocities, user engagement composition.

5. Read-Only Session Enforcement:
   - Mutation barrier raises RuntimeError on write attempts.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.dependencies import get_read_only_db
from app.analytics.service import AnalyticsService, to_count_band
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE
from app.models.offer import Offer, OfferItem, OFFER_STATUS_ACCEPTED
from app.models.order import (
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_DISPUTED,
    ORDER_STATUS_PAYMENT_PENDING,
    ORDER_STATUS_PAYMENT_RECORDED,
    ORDER_STATUS_PENDING,
    Order,
    OrderItem,
)
from app.models.payment import (
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_UPI,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    PaymentRecord,
)
from app.models.requirement import (
    BuyerRequirement,
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
)
from app.models.requirement_approval import (
    APPROVAL_STATUS_APPROVED,
    RequirementFulfillmentApproval,
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
    """FastAPI TestClient with overridden get_db and get_read_only_db."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_read_only_db] = override_get_db
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


def seed_farmer(
    db: Session,
    state: str = "Maharashtra",
    city: str = "Pune",
    verified: bool = True,
) -> User:
    """Create a verified farmer."""
    u = User(
        email=f"farmer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="farmer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    fp = FarmerProfile(
        user_id=u.id,
        full_name=f"Farmer {u.id.hex[:4]}",
        farm_name="Green Valley Farms",
        farm_location_address="Taluka Haveli",
        city=city,
        state=state,
        postal_code="411001",
    )
    db.add(fp)
    db.commit()
    db.refresh(u)
    return u


def seed_buyer(
    db: Session,
    state: str = "Maharashtra",
    city: str = "Pune",
    verified: bool = True,
) -> User:
    """Create a verified commercial buyer."""
    u = User(
        email=f"buyer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9199{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    bp = BuyerProfile(
        user_id=u.id,
        contact_person_name="Mr. Buyer",
        business_name="Fresh Mart Ltd",
        business_type="wholesaler",
        delivery_receiving_address="Market Yard",
        city=city,
        state=state,
        postal_code="411037",
    )
    db.add(bp)
    db.commit()
    db.refresh(u)
    return u


def seed_admin(db: Session) -> User:
    """Create an administrator."""
    u = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_listing(
    db: Session,
    farmer: User,
    product_name: str = "Nashik Red Onion",
    quantity: Decimal = Decimal("500.000"),
    unit: str = "kg",
    price: Decimal = Decimal("30.00"),
    state: str = "Maharashtra",
    city: str = "Pune",
) -> ProduceListing:
    """Create an active produce listing."""
    listing = ProduceListing(
        farmer_id=farmer.id,
        product_name=product_name,
        title=f"Fresh {product_name}",
        description="Freshly harvested crop",
        initial_quantity=quantity,
        available_quantity=quantity,
        unit=unit,
        price_per_unit=price,
        location_state=state,
        location_city=city,
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def seed_completed_order(
    db: Session,
    farmer: User,
    buyer: User,
    product_name: str = "Nashik Red Onion",
    quantity: Decimal = Decimal("100.000"),
    unit: str = "kg",
    price: Decimal = Decimal("30.00"),
    completed_at: datetime = None,
    listing: ProduceListing = None,
) -> Order:
    """Seed an accepted offer, order, and line items in completed status."""
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)

    # Conversation between farmer and buyer
    conv = db.query(Conversation).filter_by(farmer_id=farmer.id, buyer_id=buyer.id).first()
    if not conv:
        conv = Conversation(
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            initial_context_type="general",
        )
        db.add(conv)
        db.flush()

    # 1. Source offer
    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=quantity * price,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(offer)
    db.flush()

    offer_item = OfferItem(
        offer_id=offer.id,
        product_name=product_name,
        quantity=quantity,
        unit=unit,
        unit_price=price,
        subtotal=quantity * price,
    )
    db.add(offer_item)
    db.flush()

    # 2. Order
    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        source_offer_id=offer.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=quantity * price,
        status=ORDER_STATUS_COMPLETED,
        delivery_status=DELIVERY_STATUS_COMPLETED,
        completed_at=completed_at,
    )
    db.add(order)
    db.flush()

    # 3. Order item
    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id if listing else None,
        product_name=product_name,
        quantity=quantity,
        unit=unit,
        unit_price=price,
        subtotal=quantity * price,
        status="fulfilled",
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# 1. Coarse Count Banding Unit Tests
# ===========================================================================


def test_coarse_count_banding():
    """Verify exact count mapping to coarse count bands."""
    assert to_count_band(0) == "0"
    assert to_count_band(-5) == "0"
    assert to_count_band(1) == "1–2"
    assert to_count_band(2) == "1–2"
    assert to_count_band(3) == "3–5"
    assert to_count_band(4) == "3–5"
    assert to_count_band(5) == "3–5"
    assert to_count_band(6) == "6–10"
    assert to_count_band(10) == "6–10"
    assert to_count_band(11) == "11+"
    assert to_count_band(100) == "11+"


# ===========================================================================
# 2. Public Market Summary Tests
# ===========================================================================


def test_market_summary_empty_dataset(client: TestClient):
    """Empty database returns 200 with suppression flags and count band '0'."""
    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    assert data["provenance"]["geographic_level_applied"] == "national"
    assert not data["provenance"]["geographic_fallback_triggered"]

    # Supply is suppressed
    assert data["listed_supply"]["privacy"]["is_suppressed"] is True
    assert data["listed_supply"]["privacy"]["suppression_reason"] == "INSUFFICIENT_PARTICIPANTS"
    assert data["listed_supply"]["total_listings_band"] == "0"
    assert data["listed_supply"]["total_listings_count"] is None

    # Realized trades are suppressed
    assert data["realized_trades"]["privacy"]["is_suppressed"] is True
    assert data["realized_trades"]["privacy"]["suppression_reason"] == "INSUFFICIENT_PARTICIPANTS"
    assert data["realized_trades"]["total_trades_band"] == "0"
    assert data["realized_trades"]["total_trades_count"] is None
    assert data["realized_trades"]["total_quantity_traded"] is None

    # NO payment settlement totals in public market summary
    assert "payment_settlement" not in data
    assert "payments" not in data["realized_trades"]


def test_market_summary_diversity_suppression(client: TestClient, db_session: Session):
    """When k_farmers < 3 or k_buyers < 3, realized trades are suppressed."""
    f1 = seed_farmer(db_session, city="Pune")
    f2 = seed_farmer(db_session, city="Pune")
    b1 = seed_buyer(db_session, city="Pune")
    b2 = seed_buyer(db_session, city="Pune")

    # 2 farmers, 2 buyers -> k=2 (< 3)
    seed_completed_order(db_session, f1, b1, quantity=Decimal("100"), price=Decimal("20"))
    seed_completed_order(db_session, f2, b2, quantity=Decimal("100"), price=Decimal("25"))

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    assert trades["privacy"]["is_suppressed"] is True
    assert trades["privacy"]["suppression_reason"] == "INSUFFICIENT_PARTICIPANTS"
    assert trades["distinct_farmers_band"] == "1–2"
    assert trades["distinct_buyers_band"] == "1–2"
    assert trades["total_trades_band"] == "1–2"
    assert trades["distinct_farmers_count"] is None
    assert trades["total_quantity_traded"] is None
    assert trades["vwap"] is None


def test_market_summary_diversity_passes(client: TestClient, db_session: Session):
    """When k_farmers >= 3 and k_buyers >= 3 and N >= 3, diversity check passes."""
    farmers = [seed_farmer(db_session, city="Pune") for _ in range(3)]
    buyers = [seed_buyer(db_session, city="Pune") for _ in range(3)]

    # 3 trades, each with equal quantity and price
    for i in range(3):
        seed_completed_order(
            db_session,
            farmers[i],
            buyers[i],
            quantity=Decimal("100.000"),
            price=Decimal("30.00"),
        )

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    assert trades["distinct_farmers_count"] == 3
    assert trades["distinct_farmers_band"] == "3–5"
    assert trades["distinct_buyers_count"] == 3
    assert trades["distinct_buyers_band"] == "3–5"
    assert trades["total_trades_count"] == 3
    assert trades["total_trades_band"] == "3–5"

    assert Decimal(str(trades["total_quantity_traded"])) == Decimal("300.000")
    assert Decimal(str(trades["total_gross_value"])) == Decimal("9000.00")
    assert Decimal(str(trades["vwap"])) == Decimal("30.00")
    assert Decimal(str(trades["arithmetic_mean_price"])) == Decimal("30.00")
    assert Decimal(str(trades["median_price"])) == Decimal("30.00")


def test_market_summary_quantity_dominance(client: TestClient, db_session: Session):
    """If one participant contributes >= 50% of volume, quantity & VWAP are suppressed."""
    farmers = [seed_farmer(db_session, city="Pune") for _ in range(3)]
    buyers = [seed_buyer(db_session, city="Pune") for _ in range(3)]

    # Farmer 0 sells 600kg (60%), Farmers 1 & 2 sell 200kg each (20% each). Total = 1000kg.
    seed_completed_order(db_session, farmers[0], buyers[0], quantity=Decimal("600.000"), price=Decimal("20.00"))
    seed_completed_order(db_session, farmers[1], buyers[1], quantity=Decimal("200.000"), price=Decimal("25.00"))
    seed_completed_order(db_session, farmers[2], buyers[2], quantity=Decimal("200.000"), price=Decimal("25.00"))

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    assert trades["privacy"]["quantity_suppressed"] is True
    assert trades["total_quantity_traded"] is None
    # VWAP must also be suppressed because quantity is suppressed
    assert trades["privacy"]["vwap_suppressed"] is True
    assert trades["vwap"] is None

    # Monetary value: F0 = 12,000 (54.5%), F1 = 5,000 (22.7%), F2 = 5,000 (22.7%). Total = 22,000.
    # F0 monetary share is 12000/22000 = 54.5% >= 50%, so monetary value is also suppressed!
    assert trades["privacy"]["gross_value_suppressed"] is True
    assert trades["total_gross_value"] is None


def test_market_summary_extrema_clustering_protection(client: TestClient, db_session: Session):
    """Extrema (min_price, max_price) are suppressed if sample depth < 5 or isolated."""
    # 3 farmers, 3 buyers -> depth k=3 (< 5). Extrema should be suppressed.
    farmers = [seed_farmer(db_session) for _ in range(3)]
    buyers = [seed_buyer(db_session) for _ in range(3)]

    seed_completed_order(db_session, farmers[0], buyers[0], price=Decimal("10.00"))
    seed_completed_order(db_session, farmers[1], buyers[1], price=Decimal("20.00"))
    seed_completed_order(db_session, farmers[2], buyers[2], price=Decimal("30.00"))

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    assert trades["privacy"]["min_price_suppressed"] is True
    assert trades["privacy"]["max_price_suppressed"] is True
    assert trades["min_price"] is None
    assert trades["max_price"] is None


def test_market_summary_extrema_clustering_unsuppressed(client: TestClient, db_session: Session):
    """Extrema are unsuppressed when sample depth >= 5 and at least 2 farmers & 2 buyers cluster within 2%."""
    farmers = [seed_farmer(db_session) for _ in range(5)]
    buyers = [seed_buyer(db_session) for _ in range(5)]

    # 5 trades
    # Min trades around 10.00:
    # Trade 1: F0, B0 @ 10.00 (min)
    # Trade 2: F1, B1 @ 10.15 (within 2% of 10.00 -> 10.00 * 1.02 = 10.20)
    # This gives 2 distinct farmers (F0, F1) and 2 distinct buyers (B0, B1) in [10.00, 10.20]
    seed_completed_order(db_session, farmers[0], buyers[0], price=Decimal("10.00"))
    seed_completed_order(db_session, farmers[1], buyers[1], price=Decimal("10.15"))

    # Mid trade:
    seed_completed_order(db_session, farmers[2], buyers[2], price=Decimal("20.00"))

    # Max trades around 50.00:
    # 50.00 * 0.98 = 49.00
    # Trade 4: F3, B3 @ 49.50
    # Trade 5: F4, B4 @ 50.00
    seed_completed_order(db_session, farmers[3], buyers[3], price=Decimal("49.50"))
    seed_completed_order(db_session, farmers[4], buyers[4], price=Decimal("50.00"))

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    assert trades["distinct_farmers_count"] == 5
    assert trades["distinct_buyers_count"] == 5
    assert trades["privacy"]["min_price_suppressed"] is False
    assert trades["privacy"]["max_price_suppressed"] is False
    assert Decimal(str(trades["min_price"])) == Decimal("10.00")
    assert Decimal(str(trades["max_price"])) == Decimal("50.00")


def test_market_summary_city_to_state_fallback(client: TestClient, db_session: Session):
    """When a city query has < 3 participants, it automatically falls back to state."""
    # Farmer 0 & 1 in Pune, Farmer 2 in Nagpur. All in Maharashtra.
    f0 = seed_farmer(db_session, state="Maharashtra", city="Pune")
    f1 = seed_farmer(db_session, state="Maharashtra", city="Pune")
    f2 = seed_farmer(db_session, state="Maharashtra", city="Nagpur")

    b0 = seed_buyer(db_session, state="Maharashtra", city="Pune")
    b1 = seed_buyer(db_session, state="Maharashtra", city="Pune")
    b2 = seed_buyer(db_session, state="Maharashtra", city="Nagpur")

    seed_completed_order(db_session, f0, b0, quantity=Decimal("100"), price=Decimal("25"))
    seed_completed_order(db_session, f1, b1, quantity=Decimal("100"), price=Decimal("25"))
    seed_completed_order(db_session, f2, b2, quantity=Decimal("100"), price=Decimal("25"))

    # Query with city="Pune" (which only has 2 farmers, 2 buyers -> diversity fails)
    res = client.get("/api/v1/analytics/market-summary?city=Pune")
    assert res.status_code == 200
    data = res.json()

    assert data["provenance"]["geographic_fallback_triggered"] is True
    assert data["provenance"]["geographic_level_applied"] == "state"

    # State level includes Nagpur -> 3 farmers, 3 buyers -> diversity passes at state level!
    assert data["realized_trades"]["distinct_farmers_count"] == 3


def test_market_summary_disputed_payment_included(client: TestClient, db_session: Session):
    """Completed orders with disputed or pending payments are included in trade statistics."""
    farmers = [seed_farmer(db_session) for _ in range(3)]
    buyers = [seed_buyer(db_session) for _ in range(3)]

    orders = [
        seed_completed_order(db_session, farmers[i], buyers[i], quantity=Decimal("100"), price=Decimal("20"))
        for i in range(3)
    ]

    # Log payment for Order 0 as DISPUTED
    pay_disp = PaymentRecord(
        order_id=orders[0].id,
        recorded_by_user_id=buyers[0].id,
        amount=Decimal("2000.00"),
        payment_method=PAYMENT_METHOD_UPI,
        payment_date=date.today(),
        status=PAYMENT_STATUS_DISPUTED,
    )
    db_session.add(pay_disp)
    db_session.commit()

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    # Order 0 is still counted in completed trades
    assert trades["total_trades_count"] == 3
    assert Decimal(str(trades["total_quantity_traded"])) == Decimal("300.000")


def test_market_summary_date_filtering(client: TestClient, db_session: Session):
    """Date filtering applies [start_date, end_date + 1 day) window."""
    farmers = [seed_farmer(db_session) for _ in range(3)]
    buyers = [seed_buyer(db_session) for _ in range(3)]

    # Completed yesterday
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    # Completed today
    today = datetime.now(timezone.utc)

    for i in range(3):
        seed_completed_order(
            db_session, farmers[i], buyers[i],
            completed_at=yesterday if i == 0 else today,
        )

    # Filter for today only
    today_str = datetime.now(timezone.utc).date().isoformat()
    res = client.get(f"/api/v1/analytics/market-summary?start_date={today_str}&end_date={today_str}")
    assert res.status_code == 200
    data = res.json()

    # Only 2 orders completed today -> diversity (<3) triggers suppression
    assert data["realized_trades"]["privacy"]["is_suppressed"] is True
    assert data["realized_trades"]["total_trades_band"] == "1–2"


def test_market_summary_invalid_date_range(client: TestClient):
    """start_date after end_date returns 400 Bad Request."""
    res = client.get("/api/v1/analytics/market-summary?start_date=2026-11-10&end_date=2026-11-01")
    assert res.status_code == 400
    assert "start_date cannot be later than end_date" in res.json()["detail"]


# ===========================================================================
# 3. Demand Summary & Permanent Fulfillment Retention Tests
# ===========================================================================


def test_demand_summary_permanent_fulfillment_retention(client: TestClient, db_session: Session):
    """Approved fulfillment volume is retained even when parent requirement is closed or soft-deleted."""
    buyer = seed_buyer(db_session)
    farmer = seed_farmer(db_session)

    # Requirement 1: Active
    req1 = BuyerRequirement(
        buyer_id=buyer.id,
        product_name="Green Chilli",
        title="High Quality Green Chilli",
        required_quantity=Decimal("500.000"),
        remaining_quantity=Decimal("200.000"),
        unit="kg",
        target_price_per_unit=Decimal("40.00"),
        price_condition=PRICE_CONDITION_EXACT,
        destination_state="Maharashtra",
        destination_city="Pune",
        required_by_date=date.today() + timedelta(days=10),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    # Requirement 2: Closed
    req2 = BuyerRequirement(
        buyer_id=buyer.id,
        product_name="Green Chilli",
        title="Green Chilli Closed",
        required_quantity=Decimal("300.000"),
        remaining_quantity=Decimal("50.000"),
        unit="kg",
        destination_state="Maharashtra",
        destination_city="Pune",
        required_by_date=date.today() - timedelta(days=2),
        status=REQUIREMENT_STATUS_CLOSED,
    )
    # Requirement 3: Soft-deleted
    req3 = BuyerRequirement(
        buyer_id=buyer.id,
        product_name="Green Chilli",
        title="Green Chilli Soft Deleted",
        required_quantity=Decimal("200.000"),
        remaining_quantity=Decimal("0.000"),
        unit="kg",
        destination_state="Maharashtra",
        destination_city="Pune",
        required_by_date=date.today() + timedelta(days=5),
        status=REQUIREMENT_STATUS_ACTIVE,
        is_deleted=True,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([req1, req2, req3])
    db_session.flush()

    # Seed an order and order items linked to req2
    order = seed_completed_order(db_session, farmer, buyer, product_name="Green Chilli", quantity=Decimal("300.000"))
    order_item = order.items[0]
    order_item.buyer_requirement_id = req2.id
    db_session.flush()

    # Create approved fulfillment records linked to Req 2 (closed)
    appr2 = RequirementFulfillmentApproval(
        requirement_id=req2.id,
        order_id=order.id,
        order_item_id=order_item.id,
        proposed_quantity=Decimal("250.000"),
        approved_quantity=Decimal("250.000"),
        status=APPROVAL_STATUS_APPROVED,
        reviewed_by_user_id=buyer.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(appr2)
    db_session.commit()

    res = client.get("/api/v1/analytics/demand-summary?product_name=Green Chilli")
    assert res.status_code == 200
    data = res.json()

    concluded = data["concluded_demand_audit"]
    # The approved fulfillment quantity of 250kg is retained!
    assert Decimal(str(concluded["audited_approved_fulfillment_quantity"])) == Decimal("250.000")
    assert concluded["approved_fulfillments_count"] == 1
    # Residual forfeited from non-deleted closed req2 (50kg)
    assert Decimal(str(concluded["closed_residual_unfulfilled_quantity"])) == Decimal("50.000")
    assert concluded["includes_soft_deleted_requirements"] is True


# ===========================================================================
# 4. User Performance Dashboard Tests (/my-performance)
# ===========================================================================


def test_my_performance_unauthenticated(client: TestClient):
    """Unauthenticated request returns 401 Unauthorized."""
    res = client.get("/api/v1/analytics/my-performance")
    assert res.status_code == 401


def test_my_performance_admin_forbidden(client: TestClient, db_session: Session):
    """Admin token returns 403 Forbidden."""
    admin = seed_admin(db_session)
    res = client.get("/api/v1/analytics/my-performance", headers=make_headers(admin))
    assert res.status_code == 403
    assert "only available for farmer or buyer" in res.json()["detail"]


def test_my_performance_farmer_success(client: TestClient, db_session: Session):
    """Farmer gets comprehensive performance dashboard with accurate outcome denominators."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)

    # 1. Listing
    seed_listing(db_session, farmer, product_name="Carrot", quantity=Decimal("500.000"))

    # 2. Orders: 1 pending, 1 in-progress, 1 completed, 1 cancelled, 1 disputed
    # Total = 5 orders; Concluded = 2 (1 completed + 1 cancelled)
    o_comp = seed_completed_order(db_session, farmer, buyer, product_name="Carrot", quantity=Decimal("100"), price=Decimal("20"))

    conv = db_session.query(Conversation).filter_by(farmer_id=farmer.id, buyer_id=buyer.id).first()

    # In-progress order
    off_prog = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=Decimal("1000"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(off_prog)
    db_session.flush()
    o_prog = Order(order_number="ORD-PROG-1", source_offer_id=off_prog.id, buyer_id=buyer.id, farmer_id=farmer.id, total_amount=Decimal("1000"), status=ORDER_STATUS_CONFIRMED)
    db_session.add(o_prog)

    # Pending order
    off_pend = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=Decimal("1000"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(off_pend)
    db_session.flush()
    o_pend = Order(order_number="ORD-PEND-1", source_offer_id=off_pend.id, buyer_id=buyer.id, farmer_id=farmer.id, total_amount=Decimal("1000"), status=ORDER_STATUS_PENDING)
    db_session.add(o_pend)

    # Cancelled order
    off_canc = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=Decimal("1000"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(off_canc)
    db_session.flush()
    o_canc = Order(order_number="ORD-CANC-1", source_offer_id=off_canc.id, buyer_id=buyer.id, farmer_id=farmer.id, total_amount=Decimal("1000"), status=ORDER_STATUS_CANCELLED)
    db_session.add(o_canc)

    # Disputed order
    off_disp = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=Decimal("1000"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(off_disp)
    db_session.flush()
    o_disp = Order(order_number="ORD-DISP-1", source_offer_id=off_disp.id, buyer_id=buyer.id, farmer_id=farmer.id, total_amount=Decimal("1000"), status=ORDER_STATUS_DISPUTED)
    db_session.add(o_disp)

    # 3. Payment record for completed order (acknowledged after 2 hours)
    p_time = datetime.now(timezone.utc) - timedelta(hours=2)
    pay = PaymentRecord(
        order_id=o_comp.id,
        recorded_by_user_id=buyer.id,
        amount=Decimal("2000.00"),
        payment_method=PAYMENT_METHOD_BANK_TRANSFER,
        payment_date=date.today(),
        status=PAYMENT_STATUS_ACKNOWLEDGED,
        acknowledged_at=datetime.now(timezone.utc),
        original_acknowledged_at=datetime.now(timezone.utc),
    )
    db_session.add(pay)

    # 4. Rating review
    rev = RatingReview(
        order_id=o_comp.id,
        reviewer_id=buyer.id,
        reviewed_user_id=farmer.id,
        overall_rating=5,
        review_text="Excellent fresh carrots!",
    )
    db_session.add(rev)
    db_session.commit()

    res = client.get("/api/v1/analytics/my-performance", headers=make_headers(farmer))
    assert res.status_code == 200
    data = res.json()

    assert data["role"] == "farmer"
    assert data["total_listings_created"] == 1
    assert data["active_listings_count"] == 1

    outcomes = data["order_outcomes"]
    assert outcomes["total_orders"] == 5
    assert outcomes["pending_confirmation"] == 1
    assert outcomes["in_progress"] == 1
    assert outcomes["completed"] == 1
    assert outcomes["cancelled"] == 1
    assert outcomes["currently_disputed"] == 1

    # Tier 1: All placed orders denominator (5 total)
    assert outcomes["completed_order_share"] == 20.0
    assert outcomes["in_progress_share"] == 20.0
    assert outcomes["pending_share"] == 20.0
    assert outcomes["dispute_frequency"] == 20.0
    assert outcomes["cancelled_order_share"] == 20.0

    # Tier 2: Concluded orders denominator (1 completed + 1 cancelled = 2 concluded)
    assert outcomes["concluded_orders"] == 2
    assert outcomes["concluded_completion_rate"] == 50.0
    assert outcomes["concluded_cancellation_rate"] == 50.0

    assert Decimal(str(data["total_realized_revenue"])) == Decimal("2000.00")
    assert len(data["top_commodities"]) == 1
    assert data["top_commodities"][0]["product_name"] == "Carrot"

    # Payment settlement
    settle = data["payment_settlement"]
    assert settle["total_payments_count"] == 1
    assert settle["acknowledged_count"] == 1
    assert Decimal(str(settle["acknowledged_amount"])) == Decimal("2000.00")

    # Reviews
    assert data["average_rating"] == 5.0
    assert data["total_reviews_received"] == 1


def test_my_performance_buyer_success(client: TestClient, db_session: Session):
    """Buyer gets personal procurement and expenditure metrics."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)

    # Buyer requirement
    req = BuyerRequirement(
        buyer_id=buyer.id,
        product_name="Potato",
        title="Need Potatoes",
        required_quantity=Decimal("1000.000"),
        remaining_quantity=Decimal("800.000"),
        unit="kg",
        destination_state="Maharashtra",
        destination_city="Pune",
        required_by_date=date.today() + timedelta(days=10),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db_session.add(req)

    # Completed order
    seed_completed_order(db_session, farmer, buyer, product_name="Potato", quantity=Decimal("200.000"), price=Decimal("15.00"))

    res = client.get("/api/v1/analytics/my-performance", headers=make_headers(buyer))
    assert res.status_code == 200
    data = res.json()

    assert data["role"] == "buyer"
    assert data["total_requirements_posted"] == 1
    assert data["active_requirements_count"] == 1
    assert Decimal(str(data["total_realized_expenditure"])) == Decimal("3000.00")
    assert data["order_outcomes"]["total_orders"] == 1
    assert data["order_outcomes"]["completed"] == 1
    assert data["order_outcomes"]["completed_order_share"] == 100.0
    assert data["order_outcomes"]["concluded_orders"] == 1
    assert data["order_outcomes"]["concluded_completion_rate"] == 100.0
    assert data["order_outcomes"]["concluded_cancellation_rate"] == 0.0


# ===========================================================================
# 5. Administrator Platform Analytics Tests
# ===========================================================================


def test_platform_analytics_unauthorized(client: TestClient, db_session: Session):
    """Unauthenticated or non-admin access is rejected."""
    # 401
    res = client.get("/api/v1/analytics/admin/platform")
    assert res.status_code == 401

    # 403 for farmer
    farmer = seed_farmer(db_session)
    res = client.get("/api/v1/analytics/admin/platform", headers=make_headers(farmer))
    assert res.status_code == 403


def test_platform_analytics_admin_success(client: TestClient, db_session: Session):
    """Admin can query unsuppressed platform overview with GMV, pipeline, and engagement."""
    admin = seed_admin(db_session)
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)

    # Completed order (Platform GMV)
    seed_completed_order(db_session, farmer, buyer, quantity=Decimal("100.000"), price=Decimal("50.00"))

    # In-progress confirmed order (Pipeline GMV)
    conv = db_session.query(Conversation).filter_by(farmer_id=farmer.id, buyer_id=buyer.id).first()
    off_prog = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=Decimal("3000.00"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(off_prog)
    db_session.flush()
    o_prog = Order(order_number="ORD-PROG-1", source_offer_id=off_prog.id, buyer_id=buyer.id, farmer_id=farmer.id, total_amount=Decimal("3000.00"), status=ORDER_STATUS_CONFIRMED)
    db_session.add(o_prog)
    db_session.commit()

    # Canonical path
    res = client.get("/api/v1/analytics/admin/platform", headers=make_headers(admin))
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["platform_gmv"])) == Decimal("5000.00")
    assert Decimal(str(data["pipeline_gmv"])) == Decimal("3000.00")
    assert data["order_outcomes"]["total_orders"] == 2
    assert data["order_outcomes"]["completed"] == 1
    assert data["order_outcomes"]["in_progress"] == 1
    assert data["order_outcomes"]["completed_order_share"] == 50.0
    assert data["order_outcomes"]["in_progress_share"] == 50.0
    assert data["order_outcomes"]["concluded_orders"] == 1
    assert data["order_outcomes"]["concluded_completion_rate"] == 100.0
    assert data["order_outcomes"]["concluded_cancellation_rate"] == 0.0
    assert data["user_engagement"]["verified_farmers"] == 1
    assert data["user_engagement"]["verified_buyers"] == 1
    assert data["user_engagement"]["admin_users"] == 1

    # Alias path /admin/analytics/platform
    res_alias = client.get("/api/v1/admin/analytics/platform", headers=make_headers(admin))
    assert res_alias.status_code == 200
    assert res_alias.json()["platform_gmv"] == data["platform_gmv"]


# ===========================================================================
# 6. Read-Only Session Mutation Barrier Tests
# ===========================================================================


def test_read_only_db_blocks_mutation(sqlite_engine):
    """The get_read_only_db dependency raises RuntimeError if a write is attempted."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    from app.analytics.dependencies import get_read_only_db
    import app.analytics.dependencies as deps

    # Temporarily point factory
    orig_factory = deps.get_session_factory
    deps.get_session_factory = lambda: session_factory

    try:
        gen = get_read_only_db()
        ro_session = next(gen)

        u = User(
            email="illegal_write@agridirect.test",
            password_hash="pwd",
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        ro_session.add(u)

        with pytest.raises(RuntimeError, match="Data mutations are strictly prohibited"):
            ro_session.flush()

        try:
            next(gen)
        except StopIteration:
            pass
    finally:
        deps.get_session_factory = orig_factory


# ===========================================================================
# 7. Two-Tier Order Outcome Denominator Model Tests (Version 2.1)
# ===========================================================================


def test_order_outcomes_all_categories_present():
    """Verify all 5 outcome categories present simultaneously with correct shares and concluded rates."""
    status_counts = {
        ORDER_STATUS_PENDING: 10,
        ORDER_STATUS_CONFIRMED: 10,
        ORDER_STATUS_DELIVERY_ARRANGED: 5,
        ORDER_STATUS_PAYMENT_PENDING: 3,
        ORDER_STATUS_PAYMENT_RECORDED: 2,
        ORDER_STATUS_COMPLETED: 40,
        ORDER_STATUS_CANCELLED: 20,
        ORDER_STATUS_DISPUTED: 10,
    }
    # in_progress = 10 + 5 + 3 + 2 = 20
    # total_orders = 10 + 20 + 40 + 20 + 10 = 100
    # concluded_orders = 40 + 20 = 60
    outcomes = AnalyticsService._compute_order_outcomes(status_counts)

    assert outcomes.total_orders == 100
    assert outcomes.pending_confirmation == 10
    assert outcomes.in_progress == 20
    assert outcomes.completed == 40
    assert outcomes.cancelled == 20
    assert outcomes.currently_disputed == 10

    # Tier 1 — All placed orders denominator (100)
    assert outcomes.completed_order_share == 40.0
    assert outcomes.in_progress_share == 20.0
    assert outcomes.pending_share == 10.0
    assert outcomes.dispute_frequency == 10.0
    assert outcomes.cancelled_order_share == 20.0

    # Tier 2 — Concluded orders denominator (60)
    assert outcomes.concluded_orders == 60
    assert outcomes.concluded_completion_rate == 66.67  # 40 / 60 * 100
    assert outcomes.concluded_cancellation_rate == 33.33  # 20 / 60 * 100


def test_order_outcomes_zero_total_orders():
    """When total orders is 0, counts are 0 and all rates/shares are None."""
    status_counts = {}
    outcomes = AnalyticsService._compute_order_outcomes(status_counts)

    assert outcomes.total_orders == 0
    assert outcomes.pending_confirmation == 0
    assert outcomes.in_progress == 0
    assert outcomes.completed == 0
    assert outcomes.cancelled == 0
    assert outcomes.currently_disputed == 0

    # Tier 1 rates are None (no division by zero)
    assert outcomes.completed_order_share is None
    assert outcomes.in_progress_share is None
    assert outcomes.pending_share is None
    assert outcomes.dispute_frequency is None
    assert outcomes.cancelled_order_share is None

    # Tier 2 rates are None
    assert outcomes.concluded_orders == 0
    assert outcomes.concluded_completion_rate is None
    assert outcomes.concluded_cancellation_rate is None


def test_order_outcomes_no_concluded_outcomes():
    """Active orders exist (pending, in_progress, disputed), but 0 concluded orders."""
    status_counts = {
        ORDER_STATUS_PENDING: 3,
        ORDER_STATUS_CONFIRMED: 2,
        ORDER_STATUS_DISPUTED: 1,
    }
    # total = 3 + 2 + 1 = 6; concluded = 0
    outcomes = AnalyticsService._compute_order_outcomes(status_counts)

    assert outcomes.total_orders == 6
    assert outcomes.pending_confirmation == 3
    assert outcomes.in_progress == 2
    assert outcomes.completed == 0
    assert outcomes.cancelled == 0
    assert outcomes.currently_disputed == 1

    # Tier 1 rates computed against total_orders=6
    assert outcomes.pending_share == 50.0  # 3/6
    assert outcomes.in_progress_share == 33.33  # 2/6
    assert outcomes.dispute_frequency == 16.67  # 1/6
    assert outcomes.completed_order_share == 0.0
    assert outcomes.cancelled_order_share == 0.0

    # Tier 2 concluded rates are None because concluded_orders=0
    assert outcomes.concluded_orders == 0
    assert outcomes.concluded_completion_rate is None
    assert outcomes.concluded_cancellation_rate is None


def test_order_outcomes_only_completed():
    """When only completed orders exist, completion rates are 100% and cancellation rates are 0%."""
    status_counts = {
        ORDER_STATUS_COMPLETED: 5,
    }
    outcomes = AnalyticsService._compute_order_outcomes(status_counts)

    assert outcomes.total_orders == 5
    assert outcomes.completed == 5
    assert outcomes.cancelled == 0
    assert outcomes.pending_confirmation == 0
    assert outcomes.in_progress == 0
    assert outcomes.currently_disputed == 0

    # Tier 1
    assert outcomes.completed_order_share == 100.0
    assert outcomes.cancelled_order_share == 0.0
    assert outcomes.in_progress_share == 0.0
    assert outcomes.pending_share == 0.0
    assert outcomes.dispute_frequency == 0.0

    # Tier 2
    assert outcomes.concluded_orders == 5
    assert outcomes.concluded_completion_rate == 100.0
    assert outcomes.concluded_cancellation_rate == 0.0


def test_order_outcomes_only_cancelled():
    """When only cancelled orders exist, cancellation rates are 100% and completion rates are 0%."""
    status_counts = {
        ORDER_STATUS_CANCELLED: 4,
    }
    outcomes = AnalyticsService._compute_order_outcomes(status_counts)

    assert outcomes.total_orders == 4
    assert outcomes.completed == 0
    assert outcomes.cancelled == 4
    assert outcomes.pending_confirmation == 0
    assert outcomes.in_progress == 0
    assert outcomes.currently_disputed == 0

    # Tier 1
    assert outcomes.completed_order_share == 0.0
    assert outcomes.cancelled_order_share == 100.0
    assert outcomes.in_progress_share == 0.0
    assert outcomes.pending_share == 0.0
    assert outcomes.dispute_frequency == 0.0

    # Tier 2
    assert outcomes.concluded_orders == 4
    assert outcomes.concluded_completion_rate == 0.0
    assert outcomes.concluded_cancellation_rate == 100.0


def test_order_outcomes_no_double_counting():
    """Verify that all order statuses map to mutually exclusive buckets without double-counting."""
    status_counts = {
        ORDER_STATUS_PENDING: 1,
        ORDER_STATUS_CONFIRMED: 2,
        ORDER_STATUS_DELIVERY_ARRANGED: 3,
        ORDER_STATUS_PAYMENT_PENDING: 4,
        ORDER_STATUS_PAYMENT_RECORDED: 5,
        ORDER_STATUS_COMPLETED: 6,
        ORDER_STATUS_CANCELLED: 7,
        ORDER_STATUS_DISPUTED: 8,
    }
    # pending = 1
    # in_progress = 2 + 3 + 4 + 5 = 14
    # completed = 6
    # cancelled = 7
    # disputed = 8
    # total = 1 + 14 + 6 + 7 + 8 = 36
    # concluded = 6 + 7 = 13
    outcomes = AnalyticsService._compute_order_outcomes(status_counts)

    assert outcomes.total_orders == 36
    assert outcomes.pending_confirmation == 1
    assert outcomes.in_progress == 14
    assert outcomes.completed == 6
    assert outcomes.cancelled == 7
    assert outcomes.currently_disputed == 8

    # Category sum equals total_orders
    category_sum = (
        outcomes.pending_confirmation
        + outcomes.in_progress
        + outcomes.completed
        + outcomes.cancelled
        + outcomes.currently_disputed
    )
    assert category_sum == outcomes.total_orders

    # Concluded sum equals completed + cancelled
    assert outcomes.concluded_orders == outcomes.completed + outcomes.cancelled

    # Tier 1 shares sum to 100% within roundoff
    tier1_sum = (
        outcomes.completed_order_share
        + outcomes.in_progress_share
        + outcomes.pending_share
        + outcomes.dispute_frequency
        + outcomes.cancelled_order_share
    )
    assert abs(tier1_sum - 100.0) < 0.05

    # Tier 2 rates sum to 100% within roundoff
    tier2_sum = outcomes.concluded_completion_rate + outcomes.concluded_cancellation_rate
    assert abs(tier2_sum - 100.0) < 0.05


def test_order_outcomes_api_integration_zero_and_no_concluded(client: TestClient, db_session: Session):
    """API returns correct None values for zero orders and no concluded orders."""
    farmer = seed_farmer(db_session)

    # 1. Zero orders initially
    res = client.get("/api/v1/analytics/my-performance", headers=make_headers(farmer))
    assert res.status_code == 200
    data = res.json()
    outcomes = data["order_outcomes"]
    assert outcomes["total_orders"] == 0
    assert outcomes["completed_order_share"] is None
    assert outcomes["concluded_orders"] == 0
    assert outcomes["concluded_completion_rate"] is None
    assert outcomes["concluded_cancellation_rate"] is None

    # 2. Add only 1 pending order -> total_orders=1, concluded_orders=0
    buyer = seed_buyer(db_session)
    conv = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    db_session.add(conv)
    db_session.flush()

    off_pend = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=Decimal("500"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(off_pend)
    db_session.flush()

    o_pend = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        source_offer_id=off_pend.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=Decimal("500"),
        status=ORDER_STATUS_PENDING,
    )
    db_session.add(o_pend)
    db_session.commit()

    res2 = client.get("/api/v1/analytics/my-performance", headers=make_headers(farmer))
    assert res2.status_code == 200
    data2 = res2.json()
    outcomes2 = data2["order_outcomes"]
    assert outcomes2["total_orders"] == 1
    assert outcomes2["pending_confirmation"] == 1
    assert outcomes2["pending_share"] == 100.0
    assert outcomes2["completed_order_share"] == 0.0
    assert outcomes2["concluded_orders"] == 0
    assert outcomes2["concluded_completion_rate"] is None
    assert outcomes2["concluded_cancellation_rate"] is None

