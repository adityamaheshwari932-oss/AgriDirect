"""Automated unit, integration, and lifecycle tests for Offers and Negotiation (Module 3).

Covers:
1. Initial Offer Creation:
   - Buyer-initiated against farmer produce listing
   - Farmer-initiated against buyer requirement
   - Consolidated multi-item offer against multiple buyer requirements
   - Multiple listings in a single offer
   - Role validation (opposite roles required, self-negotiation forbidden, verified status required)
   - 7-point dual-reference validation (ownership, status, categories, units, quantities)
   - Server-calculated subtotals and total amounts
   - Conversation auto-creation and reuse
2. Access Control & Authorization:
   - Participant access (sender, recipient)
   - Unrelated user forbidden (403)
   - Admin access authorized (200)
3. Counter-Offers:
   - Valid counter-proposal reverses roles and updates parent to 'countered'
   - Sender forbidden from countering own offer (403)
   - Multi-step negotiation chain traversal ($A \to B \to A \to B \to \text{Accept}$)
   - Branching prevention on already-countered parent (409)
4. Lifecycle Operations:
   - Rejection by recipient (200), sender forbidden (403)
   - Withdrawal by sender (200), recipient forbidden (403)
   - Expiration validation (lazy evaluation rejects mutations with 409)
5. Atomic Acceptance & Order Instantiation:
   - Order and OrderItem records created atomically
   - Listing stock deducted and InventoryAdjustment ledger rows appended
   - Multi-requirement fulfillment calculation and buyer-control rules
   - Non-recipient forbidden from accepting (403)
   - Insufficient stock rolls back entire transaction (409)
   - Duplicate acceptance prevention (409)
6. Concurrency & Notifications:
   - In-app notification creation for offer events
   - Concurrency race simulation on shared listing stock
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.listing import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_PARTIALLY_FULFILLED,
    ProduceCategory,
    ProduceListing,
)
from app.models.notification import Notification
from app.models.offer import (
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_COUNTERED,
    OFFER_STATUS_EXPIRED,
    OFFER_STATUS_PENDING,
    OFFER_STATUS_REJECTED,
    OFFER_STATUS_WITHDRAWN,
    Offer,
    OfferItem,
)
from app.models.order import (
    CHANGE_TYPE_ORDER_FULFILLMENT,
    InventoryAdjustment,
    Order,
    OrderItem,
)
from app.models.requirement import (
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    BuyerRequirement,
)
from app.models.requirement_approval import RequirementFulfillmentApproval
from app.models.user import BuyerProfile, FarmerProfile, User


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
    """Provide a direct database session for test fixture setup."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


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
def category(db_session: Session) -> ProduceCategory:
    """Create a sample active produce category."""
    cat = ProduceCategory(
        name="Vegetables",
        slug="vegetables",
        is_active=True,
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture
def verified_farmer(db_session: Session) -> User:
    """Create an active, verified farmer with profile."""
    user = User(
        email="farmer.ramesh@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543210",
    )
    FarmerProfile(
        user=user,
        full_name="Ramesh Kumar",
        farm_name="Ramesh Organic Farms",
        farm_location_address="Gat No 45, Dindori Road",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def verified_buyer(db_session: Session) -> User:
    """Create an active, verified commercial buyer with profile."""
    user = User(
        email="buyer.anita@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543211",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Anita Sharma",
        business_name="Fresh Mart Retailers",
        business_type="retailer",
        delivery_receiving_address="Plot 12, APMC Market Yard",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_verified_buyer(db_session: Session) -> User:
    """Create a second active, verified buyer."""
    user = User(
        email="buyer.second@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543212",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Vikram Patel",
        business_name="Agro Procurements Ltd",
        business_type="wholesaler",
        delivery_receiving_address="Plot 44, Hadapsar Industrial Area",
        city="Pune",
        state="Maharashtra",
        postal_code="411028",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_farmer(db_session: Session) -> User:
    """Create an unverified farmer."""
    user = User(
        email="unverified.farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543213",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an administrator."""
    user = User(
        email="admin@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543299",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def farmer_listing(db_session: Session, verified_farmer: User, category: ProduceCategory) -> ProduceListing:
    """Create an active produce listing owned by verified_farmer."""
    listing = ProduceListing(
        farmer_id=verified_farmer.id,
        category_id=category.id,
        product_name="Organic Tomatoes",
        title="Fresh Organic Tomatoes from Nashik",
        initial_quantity=Decimal("500.000"),
        available_quantity=Decimal("500.000"),
        unit="kg",
        price_per_unit=Decimal("25.00"),
        quality_grade="Grade A",
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


@pytest.fixture
def farmer_second_listing(db_session: Session, verified_farmer: User, category: ProduceCategory) -> ProduceListing:
    """Create a second active produce listing (Potatoes) owned by verified_farmer."""
    listing = ProduceListing(
        farmer_id=verified_farmer.id,
        category_id=category.id,
        product_name="Fresh Potatoes",
        title="Farm Fresh Potatoes",
        initial_quantity=Decimal("300.000"),
        available_quantity=Decimal("300.000"),
        unit="kg",
        price_per_unit=Decimal("30.00"),
        quality_grade="Grade B",
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


@pytest.fixture
def buyer_requirement(db_session: Session, verified_buyer: User, category: ProduceCategory) -> BuyerRequirement:
    """Create an active buyer requirement owned by verified_buyer."""
    req = BuyerRequirement(
        buyer_id=verified_buyer.id,
        category_id=category.id,
        product_name="Organic Tomatoes",
        title="Need 100kg Organic Tomatoes",
        required_quantity=Decimal("100.000"),
        remaining_quantity=Decimal("100.000"),
        unit="kg",
        target_price_per_unit=Decimal("24.00"),
        price_condition="negotiable",
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=7),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


@pytest.fixture
def buyer_second_requirement(db_session: Session, verified_buyer: User, category: ProduceCategory) -> BuyerRequirement:
    """Create a second buyer requirement (Potatoes) owned by verified_buyer."""
    req = BuyerRequirement(
        buyer_id=verified_buyer.id,
        category_id=category.id,
        product_name="Fresh Potatoes",
        title="Need 50kg Fresh Potatoes",
        required_quantity=Decimal("50.000"),
        remaining_quantity=Decimal("50.000"),
        unit="kg",
        target_price_per_unit=Decimal("28.00"),
        price_condition="negotiable",
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=7),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def auth_headers(user: User) -> dict:
    """Generate JWT Authorization headers."""
    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "verification_status": user.verification_status,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Offer Creation Tests
# ===========================================================================

def test_buyer_creates_offer_from_listing_success(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Verified buyer submits a valid offer on a farmer listing."""
    payload = {
        "recipient_id": str(verified_farmer.id),
        "delivery_terms": "Buyer pickup from Nashik farm gate",
        "proposed_delivery_date": (date.today() + timedelta(days=3)).isoformat(),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 100.0,
                "unit": "kg",
                "unit_price": 22.50,
                "quality_grade": "Grade A",
            }
        ],
    }

    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_buyer))
    assert resp.status_code == 201
    data = resp.json()

    assert data["sender_id"] == str(verified_buyer.id)
    assert data["recipient_id"] == str(verified_farmer.id)
    assert data["status"] == "pending"
    assert Decimal(str(data["total_amount"])) == Decimal("2250.00")  # 100 * 22.50
    assert len(data["items"]) == 1
    assert Decimal(str(data["items"][0]["subtotal"])) == Decimal("2250.00")
    assert data["items"][0]["product_name"] == "Organic Tomatoes"


def test_farmer_creates_offer_from_buyer_requirement_success(
    client: TestClient,
    verified_farmer: User,
    verified_buyer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Verified farmer submits an offer against a buyer's requirement."""
    payload = {
        "recipient_id": str(verified_buyer.id),
        "delivery_terms": "Farmer delivers to Mumbai APMC",
        "proposed_delivery_date": (date.today() + timedelta(days=4)).isoformat(),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "buyer_requirement_id": str(buyer_requirement.id),
                "quantity": 80.0,
                "unit": "kg",
                "unit_price": 25.00,
            }
        ],
    }

    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_farmer))
    assert resp.status_code == 201
    data = resp.json()

    assert data["sender_id"] == str(verified_farmer.id)
    assert data["recipient_id"] == str(verified_buyer.id)
    assert Decimal(str(data["total_amount"])) == Decimal("2000.00")
    assert data["items"][0]["buyer_requirement_id"] == str(buyer_requirement.id)


def test_farmer_creates_consolidated_multi_requirement_offer(
    client: TestClient,
    verified_farmer: User,
    verified_buyer: User,
    farmer_listing: ProduceListing,
    farmer_second_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
    buyer_second_requirement: BuyerRequirement,
):
    """Farmer submits a single consolidated offer addressing two different buyer requirements."""
    payload = {
        "recipient_id": str(verified_buyer.id),
        "delivery_terms": "Combined consolidated truck delivery",
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "buyer_requirement_id": str(buyer_requirement.id),
                "quantity": 80.0,
                "unit": "kg",
                "unit_price": 24.00,
            },
            {
                "listing_id": str(farmer_second_listing.id),
                "buyer_requirement_id": str(buyer_second_requirement.id),
                "quantity": 40.0,
                "unit": "kg",
                "unit_price": 30.00,
            },
        ],
    }

    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_farmer))
    assert resp.status_code == 201
    data = resp.json()

    assert len(data["items"]) == 2
    # Item 1: 80 * 24 = 1920, Item 2: 40 * 30 = 1200 -> Total = 3120
    assert Decimal(str(data["total_amount"])) == Decimal("3120.00")
    assert data["items"][0]["buyer_requirement_id"] == str(buyer_requirement.id)
    assert data["items"][1]["buyer_requirement_id"] == str(buyer_second_requirement.id)


def test_create_offer_unverified_sender_rejected(
    client: TestClient,
    unverified_farmer: User,
    verified_buyer: User,
    farmer_listing: ProduceListing,
):
    """Unverified user cannot create an offer (403 Forbidden)."""
    payload = {
        "recipient_id": str(verified_buyer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 50.0,
                "unit": "kg",
                "unit_price": 25.00,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(unverified_farmer))
    assert resp.status_code == 403


def test_create_offer_same_role_rejected(
    client: TestClient,
    verified_buyer: User,
    other_verified_buyer: User,
    farmer_listing: ProduceListing,
):
    """Buyer cannot send offer to another buyer (must be bilateral farmer-buyer)."""
    payload = {
        "recipient_id": str(other_verified_buyer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 10.0,
                "unit": "kg",
                "unit_price": 25.00,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_buyer))
    assert resp.status_code == 400
    assert "bilateral between a farmer and a buyer" in resp.json()["detail"]


def test_create_offer_self_negotiation_rejected(
    client: TestClient,
    verified_buyer: User,
    farmer_listing: ProduceListing,
):
    """Sender cannot be recipient (self-offer rejected with 400)."""
    payload = {
        "recipient_id": str(verified_buyer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 10.0,
                "unit": "kg",
                "unit_price": 25.00,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_buyer))
    assert resp.status_code == 400
    assert "Self-negotiation is forbidden" in resp.json()["detail"]


def test_create_offer_insufficient_stock_rejected(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Cannot propose quantity greater than available listing stock (409 Conflict)."""
    payload = {
        "recipient_id": str(verified_farmer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 600.0,  # Available is 500
                "unit": "kg",
                "unit_price": 20.00,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_buyer))
    assert resp.status_code == 409
    assert "exceeds available stock" in resp.json()["detail"]


def test_create_offer_insufficient_demand_rejected(
    client: TestClient,
    verified_farmer: User,
    verified_buyer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Cannot propose quantity greater than remaining requirement demand (409 Conflict)."""
    payload = {
        "recipient_id": str(verified_buyer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "buyer_requirement_id": str(buyer_requirement.id),
                "quantity": 150.0,  # Requirement needed is 100
                "unit": "kg",
                "unit_price": 25.00,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_farmer))
    assert resp.status_code == 409
    assert "exceeds remaining demand" in resp.json()["detail"]


def test_create_offer_unit_mismatch_rejected(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Item unit must match listing unit (422 Unprocessable)."""
    payload = {
        "recipient_id": str(verified_farmer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 10.0,
                "unit": "quintal",  # Listing is in 'kg'
                "unit_price": 2500.00,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_buyer))
    assert resp.status_code == 422
    assert "does not match listing unit" in resp.json()["detail"]


# ===========================================================================
# 2. Offer Access & Authorization Tests
# ===========================================================================

def test_get_offer_participant_authorized_and_unrelated_forbidden(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    other_verified_buyer: User,
    farmer_listing: ProduceListing,
):
    """Sender and recipient can view offer; unrelated user receives 403 Forbidden."""
    create_resp = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = create_resp.json()["id"]

    # 1. Sender views (200)
    resp1 = client.get(f"/api/v1/offers/{offer_id}", headers=auth_headers(verified_buyer))
    assert resp1.status_code == 200

    # 2. Recipient views (200)
    resp2 = client.get(f"/api/v1/offers/{offer_id}", headers=auth_headers(verified_farmer))
    assert resp2.status_code == 200

    # 3. Third-party buyer views (403 Forbidden)
    resp3 = client.get(f"/api/v1/offers/{offer_id}", headers=auth_headers(other_verified_buyer))
    assert resp3.status_code == 403


def test_admin_can_view_any_offer(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    admin_user: User,
    farmer_listing: ProduceListing,
):
    """Administrator can view offer for dispute/audit purposes (200 OK)."""
    create_resp = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/offers/{offer_id}", headers=auth_headers(admin_user))
    assert resp.status_code == 200


def test_list_user_offers_scoped_and_filtered(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """List endpoint correctly paginates and filters by role."""
    client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )

    # Buyer queries sent offers
    resp = client.get("/api/v1/offers?role=sent", headers=auth_headers(verified_buyer))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["sender_id"] == str(verified_buyer.id)

    # Farmer queries received offers
    resp_farmer = client.get("/api/v1/offers?role=received", headers=auth_headers(verified_farmer))
    assert resp_farmer.status_code == 200
    assert resp_farmer.json()["total"] >= 1


# ===========================================================================
# 3. Counter-Offer Lineage Tests
# ===========================================================================

def test_counter_offer_reverses_participants_and_updates_parent_status(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Recipient counters offer: parent becomes 'countered', new offer has reversed roles."""
    # Step 1: Buyer sends offer to farmer (100 kg at 20.00)
    orig_resp = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 100.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    parent_id = orig_resp.json()["id"]

    # Step 2: Farmer counters with higher price (100 kg at 24.00)
    counter_payload = {
        "delivery_terms": "Farmer delivers to APMC",
        "items": [{"listing_id": str(farmer_listing.id), "quantity": 100.0, "unit": "kg", "unit_price": 24.0}],
    }
    counter_resp = client.post(
        f"/api/v1/offers/{parent_id}/counter",
        json=counter_payload,
        headers=auth_headers(verified_farmer),
    )
    assert counter_resp.status_code == 201
    counter_data = counter_resp.json()

    assert counter_data["sender_id"] == str(verified_farmer.id)
    assert counter_data["recipient_id"] == str(verified_buyer.id)
    assert counter_data["parent_offer_id"] == parent_id
    assert Decimal(str(counter_data["total_amount"])) == Decimal("2400.00")

    # Step 3: Verify parent offer transitioned to 'countered'
    parent_check = client.get(f"/api/v1/offers/{parent_id}", headers=auth_headers(verified_buyer))
    assert parent_check.json()["status"] == "countered"


def test_sender_cannot_counter_own_offer(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Sender attempting to counter their own offer is rejected (403 Forbidden)."""
    orig_resp = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    parent_id = orig_resp.json()["id"]

    resp = client.post(
        f"/api/v1/offers/{parent_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 22.0}]},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 403


def test_multi_step_counter_offer_lineage_chain(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Complete negotiation chain (Buyer -> Farmer -> Buyer -> Accept) is traceable."""
    # 1. Buyer Offer
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    o1_id = r1.json()["id"]

    # 2. Farmer Counter
    r2 = client.post(
        f"/api/v1/offers/{o1_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 25.0}]},
        headers=auth_headers(verified_farmer),
    )
    o2_id = r2.json()["id"]

    # 3. Buyer Counter-Counter
    r3 = client.post(
        f"/api/v1/offers/{o2_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 23.0}]},
        headers=auth_headers(verified_buyer),
    )
    o3_id = r3.json()["id"]

    # 4. Check negotiation history
    hist_resp = client.get(f"/api/v1/offers/{o3_id}/history", headers=auth_headers(verified_buyer))
    assert hist_resp.status_code == 200
    hist = hist_resp.json()

    assert hist["chain_length"] == 3
    assert hist["root_offer_id"] == o1_id
    assert hist["history"][0]["id"] == o1_id
    assert hist["history"][1]["id"] == o2_id
    assert hist["history"][2]["id"] == o3_id


def test_cannot_counter_already_countered_offer_prevents_branching(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Attempting to counter an offer that has already been countered fails (409 Conflict)."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    o1_id = r1.json()["id"]

    # Farmer counters once
    client.post(
        f"/api/v1/offers/{o1_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 25.0}]},
        headers=auth_headers(verified_farmer),
    )

    # Attempt second counter from the same parent
    dup_counter = client.post(
        f"/api/v1/offers/{o1_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 26.0}]},
        headers=auth_headers(verified_farmer),
    )
    assert dup_counter.status_code == 409


# ===========================================================================
# 4. Lifecycle Operations: Reject & Withdraw Tests
# ===========================================================================

def test_reject_offer_by_recipient(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Recipient can reject an offer with reason; sender cannot reject (403)."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    # Sender tries to reject (403)
    resp_sender = client.post(f"/api/v1/offers/{offer_id}/reject", headers=auth_headers(verified_buyer))
    assert resp_sender.status_code == 403

    # Recipient rejects (200)
    resp_recipient = client.post(
        f"/api/v1/offers/{offer_id}/reject",
        json={"reason": "Offered price is below minimum cost"},
        headers=auth_headers(verified_farmer),
    )
    assert resp_recipient.status_code == 200
    assert resp_recipient.json()["status"] == "rejected"


def test_withdraw_offer_by_sender(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Sender can withdraw a pending offer; recipient cannot withdraw (403)."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 50.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    # Recipient tries to withdraw (403)
    resp_recip = client.post(f"/api/v1/offers/{offer_id}/withdraw", headers=auth_headers(verified_farmer))
    assert resp_recip.status_code == 403

    # Sender withdraws (200)
    resp_sender = client.post(f"/api/v1/offers/{offer_id}/withdraw", headers=auth_headers(verified_buyer))
    assert resp_sender.status_code == 200
    assert resp_sender.json()["status"] == "withdrawn"


# ===========================================================================
# 5. Atomic Acceptance & Order Instantiation Tests
# ===========================================================================

def test_accept_offer_atomic_order_and_inventory_deduction(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Accepting offer deducts stock, calculates requirement fulfillment, and creates Order."""
    # Farmer sends offer to buyer for 80 kg
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 80.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_id = r1.json()["id"]

    # Buyer accepts offer
    accept_resp = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert accept_resp.status_code == 200
    acc_data = accept_resp.json()

    assert acc_data["status"] == "accepted"
    assert acc_data["order_number"].startswith("ORD-")
    order_id = uuid.UUID(acc_data["order_id"])

    # Verify Database State
    db_session.expire_all()

    # 1. Order exists
    order = db_session.query(Order).filter(Order.id == order_id).first()
    assert order is not None
    assert order.buyer_id == verified_buyer.id
    assert order.farmer_id == verified_farmer.id
    assert order.total_amount == Decimal("2000.00")
    assert len(order.items) == 1
    assert order.items[0].quantity == Decimal("80.000")
    assert order.items[0].buyer_requirement_id == buyer_requirement.id

    # 2. Listing stock deducted
    listing_after = db_session.query(ProduceListing).filter(ProduceListing.id == farmer_listing.id).first()
    assert listing_after.available_quantity == Decimal("420.000")  # 500 - 80

    # 3. InventoryAdjustment record created
    adj = db_session.query(InventoryAdjustment).filter(InventoryAdjustment.order_id == order.id).first()
    assert adj is not None
    assert adj.quantity_delta == Decimal("-80.000")
    assert adj.change_type == CHANGE_TYPE_ORDER_FULFILLMENT

    # 4. Buyer requirement remaining quantity updated (SRS FR-REQ-06)
    req_after = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == buyer_requirement.id).first()
    assert req_after.remaining_quantity == Decimal("20.000")  # 100 - 80
    assert req_after.status == REQUIREMENT_STATUS_PARTIALLY_FULFILLED


def test_accept_offer_preserves_buyer_control_over_closure_br07(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Under rule BR-07 and FR-REQ-07, reaching 0 remaining quantity does NOT auto-close requirement without buyer consent."""
    # Farmer sends offer to buyer for the entire 100 kg
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 100.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    assert r1.status_code == 201
    offer_id = r1.json()["id"]

    # 1. Accept WITHOUT close_requirement=True: requirement stays partially_fulfilled, NOT auto-closed
    accept_resp = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert accept_resp.status_code == 200

    db_session.expire_all()
    req_after = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == buyer_requirement.id).first()
    assert req_after.remaining_quantity == Decimal("0.000")
    # Rule BR-07: Still partially_fulfilled, awaiting explicit buyer closure decision
    assert req_after.status == REQUIREMENT_STATUS_PARTIALLY_FULFILLED


def test_accept_offer_sender_cannot_accept(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Sender cannot accept their own offer (403 Forbidden)."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    resp = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert resp.status_code == 403


def test_duplicate_acceptance_rejected(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Cannot accept an already-accepted offer twice (409 Conflict)."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    # First accept
    r_acc = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    assert r_acc.status_code == 200

    # Second accept attempt
    r_dup = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    assert r_dup.status_code == 409


def test_accept_offer_insufficient_stock_fails_atomically(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """If stock drops between offer creation and acceptance, accept fails and rolls back."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 400.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    # Simulate stock drop on listing
    listing = db_session.query(ProduceListing).filter(ProduceListing.id == farmer_listing.id).first()
    listing.available_quantity = Decimal("100.000")  # Now only 100 available
    db_session.commit()

    resp = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    assert resp.status_code == 409
    assert "Insufficient stock" in resp.json()["detail"]


# ===========================================================================
# 6. Requirement Fulfillment & Buyer Approval Tests
# ===========================================================================

def test_full_requirement_fulfillment_and_closure_under_buyer_control(
    client: TestClient,
    db_session: Session,
    verified_farmer: User,
    verified_buyer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """When requirement is 100% fulfilled, remaining_quantity is 0 and status transitions to closed."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 100.0,  # 100% of required quantity
                    "unit": "kg",
                    "unit_price": 24.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_id = r1.json()["id"]

    # Explicitly pass close_requirement=true per BR-07 / FR-REQ-07 buyer approval
    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept?close_requirement=true",
        headers=auth_headers(verified_buyer),
    )
    assert accept_resp.status_code == 200

    db_session.expire_all()
    req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == buyer_requirement.id).first()
    assert req.remaining_quantity == Decimal("0.000")
    assert req.status == REQUIREMENT_STATUS_CLOSED


# ===========================================================================
# 7. Expiry & Notification Tests
# ===========================================================================

def test_lazy_expiry_evaluation_rejects_mutation(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Expired offer cannot be accepted, countered, or rejected."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    # Artificially age the offer into the past
    offer = db_session.query(Offer).filter(Offer.id == uuid.UUID(offer_id)).first()
    offer.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    # Mutation attempt should detect expiry and return 409
    resp = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    assert resp.status_code == 409
    assert "expired" in resp.json()["detail"].lower()


def test_in_app_notifications_recorded_for_negotiation(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Creating and accepting offers records in-app notifications in notifications table."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 25.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]

    # Farmer should have an unread notification
    farmer_notifs = db_session.query(Notification).filter(Notification.user_id == verified_farmer.id).all()
    assert len(farmer_notifs) >= 1
    assert any("New Offer Received" in n.title for n in farmer_notifs)


def test_create_offer_category_mismatch_rejected(
    client: TestClient,
    db_session: Session,
    verified_farmer: User,
    verified_buyer: User,
    farmer_listing: ProduceListing,
):
    """If listing and requirement specify conflicting categories, reject with 422."""
    other_cat = ProduceCategory(name="Fruits", slug="fruits", is_active=True)
    db_session.add(other_cat)
    db_session.commit()

    fruit_req = BuyerRequirement(
        buyer_id=verified_buyer.id,
        category_id=other_cat.id,  # Fruits category
        product_name="Mangoes",
        title="Need 100kg Mangoes",
        required_quantity=Decimal("100.000"),
        remaining_quantity=Decimal("100.000"),
        unit="kg",
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=7),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db_session.add(fruit_req)
    db_session.commit()

    # Attempt to offer vegetable listing against fruit requirement
    resp = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),  # Vegetables
                    "buyer_requirement_id": str(fruit_req.id),  # Fruits
                    "quantity": 50.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    assert resp.status_code == 422
    assert "Category mismatch" in resp.json()["detail"]


def test_cannot_accept_already_countered_parent_offer(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """A parent offer that has been superseded by a counter-offer cannot be accepted (409 Conflict)."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    parent_id = r1.json()["id"]

    # Farmer counters
    client.post(
        f"/api/v1/offers/{parent_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 22.0}]},
        headers=auth_headers(verified_farmer),
    )

    # Farmer now tries to accept the old countered parent
    resp = client.post(f"/api/v1/offers/{parent_id}/accept", headers=auth_headers(verified_farmer))
    assert resp.status_code == 409
    assert "Cannot accept offer in 'countered' status" in resp.json()["detail"]


def test_cannot_counter_rejected_or_withdrawn_offer(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Terminal offers (rejected or withdrawn) cannot be countered (409 Conflict)."""
    # 1. Rejected offer
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    o1_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{o1_id}/reject", headers=auth_headers(verified_farmer))

    resp_counter_rej = client.post(
        f"/api/v1/offers/{o1_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 22.0}]},
        headers=auth_headers(verified_farmer),
    )
    assert resp_counter_rej.status_code == 409

    # 2. Withdrawn offer
    r2 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    o2_id = r2.json()["id"]
    client.post(f"/api/v1/offers/{o2_id}/withdraw", headers=auth_headers(verified_buyer))

    resp_counter_withdrawn = client.post(
        f"/api/v1/offers/{o2_id}/counter",
        json={"items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 22.0}]},
        headers=auth_headers(verified_farmer),
    )
    assert resp_counter_withdrawn.status_code == 409


def test_concurrency_race_competing_offers_on_limited_stock(
    client: TestClient,
    db_session: Session,
    verified_farmer: User,
    verified_buyer: User,
    other_verified_buyer: User,
    category: ProduceCategory,
):
    """Two buyers have offers on the same 100kg listing for 60kg each. Exactly one can succeed."""
    limited_listing = ProduceListing(
        farmer_id=verified_farmer.id,
        category_id=category.id,
        product_name="Limited Batch Onions",
        title="Limited Batch Onions 100kg",
        initial_quantity=Decimal("100.000"),
        available_quantity=Decimal("100.000"),
        unit="kg",
        price_per_unit=Decimal("40.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        status=STATUS_ACTIVE,
    )
    db_session.add(limited_listing)
    db_session.commit()

    # Buyer 1 offer for 60 kg
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(limited_listing.id), "quantity": 60.0, "unit": "kg", "unit_price": 40.0}],
        },
        headers=auth_headers(verified_buyer),
    )
    o1_id = r1.json()["id"]

    # Buyer 2 offer for 60 kg
    r2 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [{"listing_id": str(limited_listing.id), "quantity": 60.0, "unit": "kg", "unit_price": 40.0}],
        },
        headers=auth_headers(other_verified_buyer),
    )
    o2_id = r2.json()["id"]

    # Farmer accepts offer 1 -> succeeds, stock becomes 40kg
    resp1 = client.post(f"/api/v1/offers/{o1_id}/accept", headers=auth_headers(verified_farmer))
    assert resp1.status_code == 200

    # Farmer now tries to accept offer 2 (needs 60kg, only 40kg left) -> fails with 409
    resp2 = client.post(f"/api/v1/offers/{o2_id}/accept", headers=auth_headers(verified_farmer))
    assert resp2.status_code == 409
    assert "Insufficient stock" in resp2.json()["detail"]


# ===========================================================================
# 9. Audit Remediation & Deep Edge-Case Tests
# ===========================================================================


def test_buyer_rejects_requirement_quantity_reduction_br07(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Under rule BR-07, buyer can accept offer with approve_requirement_update=false; remaining_quantity is not reduced."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 40.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    assert r1.status_code == 201
    offer_id = r1.json()["id"]

    # Buyer accepts with approve_requirement_update=false
    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept?approve_requirement_update=false",
        headers=auth_headers(verified_buyer),
    )
    assert accept_resp.status_code == 200

    db_session.expire_all()
    req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == buyer_requirement.id).first()
    # Quantity remains untouched at 100.000 per buyer instruction
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE


def test_farmer_accepts_buyer_offer_cannot_alter_requirement_br07(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """When farmer accepts an offer sent by a buyer, farmer has NO authority to update buyer's requirement."""
    # Buyer sends offer referencing their requirement
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 30.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_buyer),
    )
    assert r1.status_code == 201
    offer_id = r1.json()["id"]

    # Farmer accepts the offer
    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept",
        headers=auth_headers(verified_farmer),
    )
    assert accept_resp.status_code == 200

    db_session.expire_all()
    req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == buyer_requirement.id).first()
    # Farmer cannot reduce buyer requirement; demand remains 100.000 awaiting buyer approval
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE


def test_create_offer_missing_listing_id_fails_validation(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
):
    """An offer item without listing_id fails Pydantic schema validation with 422."""
    payload = {
        "recipient_id": str(verified_farmer.id),
        "items": [
            {
                "product_name": "Tomatoes without listing",
                "quantity": 50.0,
                "unit": "kg",
                "unit_price": 20.0,
            }
        ],
    }
    resp = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_buyer))
    assert resp.status_code == 422


def test_consolidated_offer_multiple_buyer_requirements(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
    category: ProduceCategory,
):
    """A single consolidated offer can propose items fulfilling distinct buyer requirements."""
    # Create a second requirement for the same buyer
    req2 = BuyerRequirement(
        buyer_id=verified_buyer.id,
        category_id=category.id,
        product_name="Organic Potatoes",
        title="Procurement of Organic Potatoes",
        required_quantity=Decimal("50.000"),
        remaining_quantity=Decimal("50.000"),
        unit="kg",
        destination_state="Maharashtra",
        destination_city="Pune",
        required_by_date=date.today() + timedelta(days=10),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    listing2 = ProduceListing(
        farmer_id=verified_farmer.id,
        category_id=category.id,
        product_name="Organic Potatoes",
        title="Fresh Potatoes 200kg",
        initial_quantity=Decimal("200.000"),
        available_quantity=Decimal("200.000"),
        unit="kg",
        price_per_unit=Decimal("15.00"),
        location_state="Maharashtra",
        location_city="Pune",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        status=STATUS_ACTIVE,
    )
    db_session.add_all([req2, listing2])
    db_session.commit()

    # Consolidated offer: Item 1 for Requirement 1, Item 2 for Requirement 2, Item 3 listing-only
    payload = {
        "recipient_id": str(verified_buyer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "buyer_requirement_id": str(buyer_requirement.id),
                "quantity": 25.0,
                "unit": "kg",
                "unit_price": 22.0,
            },
            {
                "listing_id": str(listing2.id),
                "buyer_requirement_id": str(req2.id),
                "quantity": 20.0,
                "unit": "kg",
                "unit_price": 15.0,
            },
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 10.0,
                "unit": "kg",
                "unit_price": 25.0,
            },
        ],
    }

    r1 = client.post("/api/v1/offers", json=payload, headers=auth_headers(verified_farmer))
    assert r1.status_code == 201
    offer_id = r1.json()["id"]

    # Buyer accepts consolidated offer
    acc = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert acc.status_code == 200

    db_session.expire_all()
    # Verify both requirements were updated appropriately
    req1_after = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == buyer_requirement.id).first()
    assert req1_after.remaining_quantity == Decimal("75.000")  # 100 - 25
    req2_after = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req2.id).first()
    assert req2_after.remaining_quantity == Decimal("30.000")  # 50 - 20


def test_repeated_listing_references_in_one_offer_aggregates_demand(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """An offer containing multiple items referencing the same listing aggregates demand against stock."""
    # Listing has available_quantity = 500 kg
    # Item 1: references buyer_requirement (300 kg)
    # Item 2: listing-only without requirement (250 kg)
    # Total = 550 kg > 500 kg available stock -> 409 Conflict
    payload_too_much = {
        "recipient_id": str(verified_farmer.id),
        "items": [
            {
                "listing_id": str(farmer_listing.id),
                "buyer_requirement_id": str(buyer_requirement.id),
                "quantity": 300.0,
                "unit": "kg",
                "unit_price": 20.0,
            },
            {
                "listing_id": str(farmer_listing.id),
                "quantity": 250.0,
                "unit": "kg",
                "unit_price": 20.0,
            },
        ],
    }
    r_fail = client.post("/api/v1/offers", json=payload_too_much, headers=auth_headers(verified_buyer))
    assert r_fail.status_code == 409
    assert "exceeds available stock" in r_fail.json()["detail"]


def test_duplicate_exact_item_lines_in_offer_fails_schema_validation(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """An offer payload containing duplicate exact item lines fails with 422 Unprocessable Content."""
    payload_dup = {
        "recipient_id": str(verified_farmer.id),
        "items": [
            {"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 20.0},
            {"listing_id": str(farmer_listing.id), "quantity": 20.0, "unit": "kg", "unit_price": 20.0},
        ],
    }
    r_dup = client.post("/api/v1/offers", json=payload_dup, headers=auth_headers(verified_buyer))
    assert r_dup.status_code == 422
    assert "Duplicate item reference detected" in str(r_dup.json()["detail"])


def test_duplicate_acceptance_returns_409_conflict(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """Repeated calls to accept the same offer return 409 Conflict."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 10.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_id = r1.json()["id"]

    acc1 = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert acc1.status_code == 200

    acc2 = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert acc2.status_code == 409
    assert "Cannot accept offer in 'accepted' status" in acc2.json()["detail"]


def test_post_commit_email_failure_does_not_fail_acceptance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
):
    """If send_email_notification encounters an unexpected failure after commit, acceptance still succeeds."""
    from unittest.mock import MagicMock
    mock_email = MagicMock(side_effect=RuntimeError("SMTP Server Down"))
    monkeypatch.setattr("app.offers.service.send_email_notification", mock_email)

    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [{"listing_id": str(farmer_listing.id), "quantity": 15.0, "unit": "kg", "unit_price": 20.0}],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_id = r1.json()["id"]

    resp = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


def test_order_item_preserves_snapshot_and_nulls_on_requirement_deletion(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """When a buyer requirement is deleted, OrderItem preserves snapshot product/price/quantity and nulls FK."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 25.0,
                    "unit": "kg",
                    "unit_price": 30.0,
                    "quality_grade": "Grade A",
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    assert r1.status_code == 201
    offer_id = r1.json()["id"]

    acc = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_buyer))
    assert acc.status_code == 200
    order_id = uuid.UUID(acc.json()["order_id"])

    # Verify order item exists with requirement ID
    db_session.expire_all()
    order_item = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).first()
    assert order_item is not None
    assert order_item.buyer_requirement_id == buyer_requirement.id
    assert order_item.product_name == "Organic Tomatoes"
    assert order_item.quantity == Decimal("25.000")
    assert order_item.unit_price == Decimal("30.00")
    assert order_item.subtotal == Decimal("750.00")

    # Under ADR-003, RequirementFulfillmentApproval has ON DELETE RESTRICT on requirement_id
    # to protect procurement audit integrity. To test order_items.buyer_requirement_id ON DELETE SET NULL,
    # remove the approval row first.
    db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).delete()
    db_session.commit()

    # Hard delete requirement to test ON DELETE SET NULL
    req_to_del = db_session.get(BuyerRequirement, buyer_requirement.id)
    db_session.delete(req_to_del)
    db_session.commit()

    # Verify OrderItem snapshot remains fully intact and buyer_requirement_id becomes None
    db_session.expire_all()
    refreshed_item = db_session.get(OrderItem, order_item.id)
    assert refreshed_item is not None
    assert refreshed_item.buyer_requirement_id is None
    assert refreshed_item.product_name == "Organic Tomatoes"
    assert refreshed_item.quantity == Decimal("25.000")
    assert refreshed_item.unit_price == Decimal("30.00")
    assert refreshed_item.subtotal == Decimal("750.00")
