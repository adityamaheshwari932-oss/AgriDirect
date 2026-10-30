"""Automated tests for Requirement Fulfillment Approval Workflow (ADR-003).

Covers:
1. Farmer offer acceptance creates pending fulfillment approval records (BR-07, FR-REQ-06).
2. Subsequent buyer full approval deducts remaining quantity and transitions status.
3. Subsequent buyer partial approval deducts custom quantity while commercial order remains intact.
4. Subsequent buyer approval explicit closure vs remaining open when remaining reaches 0.000.
5. Subsequent buyer rejection preserves requirement open demand (FR-REQ-08).
6. Immediate buyer offer acceptance (apply=True, apply=False, partial quantity).
7. Multi-item offer acceptance atomicity and rollback guarantees.
8. Anti-enumeration security checks (404 Not Found for non-owners).
9. Idempotency guards and duplicate review prevention (409 Conflict).
10. Strict no-clamping validation when approved quantity exceeds remaining demand (409 Conflict).
11. Order cancellation handling (voiding pending approvals with audit trail).
12. Database CHECK constraint invariants and composite foreign key enforcement.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.listing import (
    STATUS_ACTIVE,
    ProduceCategory,
    ProduceListing,
)
from app.models.offer import (
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_PENDING,
    Offer,
    OfferItem,
)
from app.models.order import (
    CHANGE_TYPE_ORDER_FULFILLMENT,
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_STATUS_PENDING,
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
from app.models.requirement_approval import (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_NOT_APPLIED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_VOIDED,
    RequirementFulfillmentApproval,
)
from app.models.user import BuyerProfile, FarmerProfile, User
from app.requirements.approval_service import FulfillmentApprovalService


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
    """Create a produce category."""
    cat = ProduceCategory(name="Vegetables", slug="vegetables", is_active=True)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture
def verified_farmer(db_session: Session) -> User:
    """Create an active, verified farmer."""
    user = User(
        email="farmer.approval@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543201",
    )
    FarmerProfile(
        user=user,
        full_name="Ramesh Kumar",
        farm_name="Green Valley Farms",
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
    """Create an active, verified buyer."""
    user = User(
        email="buyer.approval@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543202",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Ramesh Kumar",
        business_name="FreshMart Retails Ltd",
        business_type="retailer",
        delivery_receiving_address="Warehouse 4B, APMC Market",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_buyer(db_session: Session) -> User:
    """Create a second active, verified buyer."""
    user = User(
        email="other.buyer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543203",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Suresh Sharma",
        business_name="Sahyadri Supermarkets",
        business_type="retailer",
        delivery_receiving_address="Shop 12, MG Road",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
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
# 1. Farmer Acceptance & Pending Approval Creation Tests
# ===========================================================================

def test_farmer_acceptance_creates_pending_approval_and_preserves_requirement(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """When farmer accepts an offer sent by a buyer against a requirement:
    - Order is created atomically
    - Requirement remaining_quantity is NOT altered (BR-07, FR-REQ-06)
    - RequirementFulfillmentApproval record created in 'pending' status
    """
    # Buyer sends offer
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
    order_id = uuid.UUID(accept_resp.json()["order_id"])

    # Requirement remains untouched
    db_session.expire_all()
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE

    # Approval record is created in pending status
    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.order_id == order_id
    ).first()
    assert approval is not None
    assert approval.requirement_id == buyer_requirement.id
    assert approval.status == APPROVAL_STATUS_PENDING
    assert approval.proposed_quantity == Decimal("30.000")
    assert approval.approved_quantity is None
    assert approval.reviewed_by_user_id is None
    assert approval.reviewed_at is None
    assert approval.rejection_reason is None


# ===========================================================================
# 2. Subsequent Buyer Approval Tests
# ===========================================================================

def test_buyer_subsequent_full_approval_defaults_to_proposed_quantity(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Buyer approves pending fulfillment without specifying approved_quantity.
    It defaults to proposed_quantity, decrements requirement remaining demand,
    and transitions status to partially_fulfilled.
    """
    # Create offer and accept as farmer
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
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()
    assert approval.status == APPROVAL_STATUS_PENDING

    # Buyer approves
    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == APPROVAL_STATUS_APPROVED
    assert Decimal(str(data["approved_quantity"])) == Decimal("30.000")
    assert Decimal(str(data["requirement_remaining_quantity"])) == Decimal("70.000")
    assert data["requirement_status"] == REQUIREMENT_STATUS_PARTIALLY_FULFILLED

    db_session.expire_all()
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.remaining_quantity == Decimal("70.000")
    assert req.status == REQUIREMENT_STATUS_PARTIALLY_FULFILLED


def test_buyer_subsequent_partial_approval_preserves_order_item_quantity(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Buyer approves partial quantity (20.0 kg out of 30.0 kg proposed).
    - Requirement is deducted by 20.0 kg (now 80.0 kg).
    - Commercial order item quantity remains intact at 30.0 kg.
    """
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
    offer_id = r1.json()["id"]
    acc = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    order_id = uuid.UUID(acc.json()["order_id"])

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()

    # Buyer approves only 20 kg
    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={"approved_quantity": 20.0},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == APPROVAL_STATUS_APPROVED
    assert Decimal(str(data["approved_quantity"])) == Decimal("20.000")
    assert Decimal(str(data["proposed_quantity"])) == Decimal("30.000")
    assert Decimal(str(data["requirement_remaining_quantity"])) == Decimal("80.000")

    db_session.expire_all()
    # Check requirement
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.remaining_quantity == Decimal("80.000")

    # Check commercial order item remains 30.000 kg
    order_item = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).first()
    assert order_item.quantity == Decimal("30.000")


def test_buyer_subsequent_approval_explicit_closure(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Buyer explicitly passes close_requirement=True on approval.
    Requirement status transitions to 'closed'.
    """
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
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()

    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={"close_requirement": True},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 200
    assert resp.json()["requirement_status"] == REQUIREMENT_STATUS_CLOSED

    db_session.expire_all()
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.status == REQUIREMENT_STATUS_CLOSED


def test_zero_remaining_quantity_without_auto_closure(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    category: ProduceCategory,
):
    """Strict Buyer Authority: When approved quantity brings remaining to 0.000,
    the system does NOT automatically close the requirement unless explicitly instructed.
    """
    # Create requirement with exactly 50kg
    small_req = BuyerRequirement(
        buyer_id=verified_buyer.id,
        category_id=category.id,
        product_name="Organic Tomatoes",
        title="Exact 50kg needed",
        required_quantity=Decimal("50.000"),
        remaining_quantity=Decimal("50.000"),
        unit="kg",
        target_price_per_unit=Decimal("24.00"),
        price_condition="negotiable",
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=7),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db_session.add(small_req)
    db_session.commit()
    db_session.refresh(small_req)

    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(small_req.id),
                    "quantity": 50.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == small_req.id
    ).first()

    # Buyer approves full 50kg without close_requirement=True
    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={"close_requirement": False},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["requirement_remaining_quantity"])) == Decimal("0.000")
    # Must NOT be closed!
    assert data["requirement_status"] == REQUIREMENT_STATUS_PARTIALLY_FULFILLED

    db_session.expire_all()
    req = db_session.get(BuyerRequirement, small_req.id)
    assert req.remaining_quantity == Decimal("0.000")
    assert req.status == REQUIREMENT_STATUS_PARTIALLY_FULFILLED


# ===========================================================================
# 3. Subsequent Buyer Rejection Tests
# ===========================================================================

def test_buyer_subsequent_rejection_preserves_demand(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Buyer rejects fulfillment deduction:
    - Requirement remaining_quantity is completely untouched (FR-REQ-08).
    - Requirement status remains active.
    - Approval status transitions to 'rejected' with rejection_reason recorded.
    """
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
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()

    # Buyer rejects
    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/reject",
        json={"reason": "Delivery terms did not match our procurement warehouse schedule"},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == APPROVAL_STATUS_REJECTED
    assert data["approved_quantity"] is None
    assert data["rejection_reason"] == "Delivery terms did not match our procurement warehouse schedule"
    assert Decimal(str(data["requirement_remaining_quantity"])) == Decimal("100.000")
    assert data["requirement_status"] == REQUIREMENT_STATUS_ACTIVE

    db_session.expire_all()
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE


# ===========================================================================
# 4. Immediate Buyer Acceptance Tests
# ===========================================================================

def test_buyer_immediate_offer_acceptance_applied(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Farmer sends offer to buyer; buyer accepts immediately with apply_to_requirement=True.
    Approval record is created directly in 'approved' status.
    """
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
                    "unit_price": 24.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_id = r1.json()["id"]

    # Buyer accepts with payload
    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept",
        json={
            "apply_to_requirement": True,
            "approved_quantity": 25.0,
            "close_requirement": False,
        },
        headers=auth_headers(verified_buyer),
    )
    assert accept_resp.status_code == 200
    order_id = uuid.UUID(accept_resp.json()["order_id"])

    db_session.expire_all()
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.remaining_quantity == Decimal("75.000")
    assert req.status == REQUIREMENT_STATUS_PARTIALLY_FULFILLED

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.order_id == order_id
    ).first()
    assert approval.status == APPROVAL_STATUS_APPROVED
    assert approval.approved_quantity == Decimal("25.000")
    assert approval.reviewed_by_user_id == verified_buyer.id


def test_buyer_immediate_offer_acceptance_not_applied(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Buyer accepts offer with apply_to_requirement=False.
    Approval record is created directly in 'not_applied' status.
    Requirement remains untouched at 100.000.
    """
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
                    "unit_price": 24.0,
                }
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_id = r1.json()["id"]

    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept",
        json={
            "apply_to_requirement": False,
        },
        headers=auth_headers(verified_buyer),
    )
    assert accept_resp.status_code == 200
    order_id = uuid.UUID(accept_resp.json()["order_id"])

    db_session.expire_all()
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.order_id == order_id
    ).first()
    assert approval.status == APPROVAL_STATUS_NOT_APPLIED
    assert approval.approved_quantity is None
    assert approval.reviewed_by_user_id == verified_buyer.id


def test_buyer_immediate_offer_acceptance_granular_item_decisions(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    farmer_second_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
    buyer_second_requirement: BuyerRequirement,
):
    """Multi-item offer where buyer applies Item 1 to requirement, but marks Item 2 as not_applied."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 30.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                },
                {
                    "listing_id": str(farmer_second_listing.id),
                    "buyer_requirement_id": str(buyer_second_requirement.id),
                    "quantity": 20.0,
                    "unit": "kg",
                    "unit_price": 30.0,
                },
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    assert r1.status_code == 201
    offer_data = r1.json()
    offer_id = offer_data["id"]
    item_1_id = offer_data["items"][0]["id"]
    item_2_id = offer_data["items"][1]["id"]

    # Buyer accepts with granular decisions
    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept",
        json={
            "item_fulfillments": [
                {
                    "offer_item_id": item_1_id,
                    "apply_to_requirement": True,
                    "approved_quantity": 30.0,
                },
                {
                    "offer_item_id": item_2_id,
                    "apply_to_requirement": False,
                },
            ]
        },
        headers=auth_headers(verified_buyer),
    )
    assert accept_resp.status_code == 200
    order_id = uuid.UUID(accept_resp.json()["order_id"])

    db_session.expire_all()
    # Req 1 reduced
    req1 = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert req1.remaining_quantity == Decimal("70.000")

    # Req 2 unchanged
    req2 = db_session.get(BuyerRequirement, buyer_second_requirement.id)
    assert req2.remaining_quantity == Decimal("50.000")

    approvals = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.order_id == order_id
    ).all()
    assert len(approvals) == 2
    app_map = {a.requirement_id: a for a in approvals}
    assert app_map[buyer_requirement.id].status == APPROVAL_STATUS_APPROVED
    assert app_map[buyer_requirement.id].approved_quantity == Decimal("30.000")
    assert app_map[buyer_second_requirement.id].status == APPROVAL_STATUS_NOT_APPLIED
    assert app_map[buyer_second_requirement.id].approved_quantity is None


# ===========================================================================
# 5. Multi-Item Atomicity & Rollback Guarantee
# ===========================================================================

def test_multi_item_offer_acceptance_atomicity_failure_rolls_back_everything(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    farmer_second_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
    buyer_second_requirement: BuyerRequirement,
):
    """ADR-003 Section 3.2: If ANY item fails validation (e.g. approved_quantity > remaining_demand),
    the ENTIRE transaction rolls back. Zero rows are altered, no order created.
    """
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_buyer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 20.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                },
                {
                    "listing_id": str(farmer_second_listing.id),
                    "buyer_requirement_id": str(buyer_second_requirement.id),
                    "quantity": 40.0,
                    "unit": "kg",
                    "unit_price": 30.0,
                },
            ],
        },
        headers=auth_headers(verified_farmer),
    )
    offer_data = r1.json()
    offer_id = offer_data["id"]
    item_1_id = offer_data["items"][0]["id"]
    item_2_id = offer_data["items"][1]["id"]

    # Set buyer_second_requirement remaining to 10 kg
    req2 = db_session.get(BuyerRequirement, buyer_second_requirement.id)
    req2.remaining_quantity = Decimal("10.000")
    db_session.commit()

    # Buyer attempts to approve full quantity (40 kg > 10 kg remaining)
    accept_resp = client.post(
        f"/api/v1/offers/{offer_id}/accept",
        json={
            "item_fulfillments": [
                {
                    "offer_item_id": item_1_id,
                    "apply_to_requirement": True,
                    "approved_quantity": 20.0,
                },
                {
                    "offer_item_id": item_2_id,
                    "apply_to_requirement": True,
                    "approved_quantity": 40.0,
                },
            ]
        },
        headers=auth_headers(verified_buyer),
    )
    # Should fail with 409 Conflict
    assert accept_resp.status_code == 409
    assert "exceeds current remaining demand" in accept_resp.json()["detail"]

    # Verify atomic rollback
    db_session.expire_all()
    # Offer remains pending
    off = db_session.get(Offer, uuid.UUID(offer_id))
    assert off.status == OFFER_STATUS_PENDING

    # No order created
    orders_count = db_session.query(Order).filter(Order.source_offer_id == off.id).count()
    assert orders_count == 0

    # No approvals created
    approvals_count = db_session.query(RequirementFulfillmentApproval).count()
    assert approvals_count == 0

    # Listing inventory untouched
    l1 = db_session.get(ProduceListing, farmer_listing.id)
    assert l1.available_quantity == Decimal("500.000")

    # Both requirements untouched
    r_check1 = db_session.get(BuyerRequirement, buyer_requirement.id)
    assert r_check1.remaining_quantity == Decimal("100.000")
    r_check2 = db_session.get(BuyerRequirement, buyer_second_requirement.id)
    assert r_check2.remaining_quantity == Decimal("10.000")


# ===========================================================================
# 6. Anti-Enumeration & Security Tests
# ===========================================================================

def test_approval_unauthorized_non_owner_anti_enumeration(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    other_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Non-owner attempting to GET, approve, or reject an approval receives 404 Not Found."""
    headers_buyer = auth_headers(verified_buyer)
    headers_other = auth_headers(other_buyer)
    headers_farmer = auth_headers(verified_farmer)

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
        headers=headers_buyer,
    )
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=headers_farmer)

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()
    app_id = approval.id

    # other_buyer tries to GET
    r_get = client.get(
        f"/api/v1/requirements/fulfillment-approvals/{app_id}",
        headers=headers_other,
    )
    assert r_get.status_code == 404

    # other_buyer tries to approve
    r_app = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{app_id}/approve",
        json={},
        headers=headers_other,
    )
    assert r_app.status_code == 404

    # other_buyer tries to reject
    r_rej = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{app_id}/reject",
        json={},
        headers=headers_other,
    )
    assert r_rej.status_code == 404


# ===========================================================================
# 7. Validation & Idempotency Tests
# ===========================================================================

def test_approval_already_reviewed_returns_409_conflict(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Attempting to review an already-reviewed approval returns 409 Conflict."""
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
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()

    # First approval succeeds
    r_first = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={},
        headers=auth_headers(verified_buyer),
    )
    assert r_first.status_code == 200

    # Second review attempt fails with 409
    r_second = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={},
        headers=auth_headers(verified_buyer),
    )
    assert r_second.status_code == 409
    assert "already been reviewed" in r_second.json()["detail"]


def test_approved_quantity_exceeds_remaining_demand_returns_409_no_clamping(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """If approved quantity exceeds current remaining demand, 409 Conflict is returned.
    Approval remains in pending status without clamping.
    """
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 50.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    # Manually drop remaining demand to 20kg
    req = db_session.get(BuyerRequirement, buyer_requirement.id)
    req.remaining_quantity = Decimal("20.000")
    db_session.commit()

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()
    app_id = approval.id

    # Attempt to approve 30kg (exceeds 20kg remaining)
    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{app_id}/approve",
        json={"approved_quantity": 30.0},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 409
    assert "exceeds current remaining requirement quantity" in resp.json()["detail"]
    assert "No quantity clamped" in resp.json()["detail"]

    db_session.expire_all()
    refreshed_app = db_session.get(RequirementFulfillmentApproval, app_id)
    assert refreshed_app.status == APPROVAL_STATUS_PENDING


def test_approved_quantity_exceeds_proposed_quantity_returns_409(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Attempting to approve a quantity greater than proposed quantity returns 409."""
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
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.requirement_id == buyer_requirement.id
    ).first()

    # Attempt to approve 40kg (proposed is 30kg)
    resp = client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={"approved_quantity": 40.0},
        headers=auth_headers(verified_buyer),
    )
    assert resp.status_code == 409
    assert "cannot exceed proposed quantity" in resp.json()["detail"]


# ===========================================================================
# 8. Query & List Approvals Tests
# ===========================================================================

def test_list_and_get_approvals_endpoints(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Test GET /api/v1/requirements/fulfillment-approvals and detail endpoint."""
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 25.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    # List approvals
    list_resp = client.get(
        "/api/v1/requirements/fulfillment-approvals",
        headers=auth_headers(verified_buyer),
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert list_data["items"][0]["status"] == APPROVAL_STATUS_PENDING

    approval_id = list_data["items"][0]["id"]

    # Detail
    detail_resp = client.get(
        f"/api/v1/requirements/fulfillment-approvals/{approval_id}",
        headers=auth_headers(verified_buyer),
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == approval_id
    assert detail_data["product_name"] == "Organic Tomatoes"


# ===========================================================================
# 9. Order Cancellation & Voiding Tests
# ===========================================================================

def test_order_cancellation_voids_pending_approvals_with_audit(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """When an order with pending fulfillment approvals is cancelled,
    the pending approvals are transitioned to 'voided' with reason and audit timestamp.
    """
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
    offer_id = r1.json()["id"]
    acc = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    order_id = uuid.UUID(acc.json()["order_id"])

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.order_id == order_id
    ).first()
    assert approval.status == APPROVAL_STATUS_PENDING

    # Call cancellation handler on service
    service = FulfillmentApprovalService(db_session)
    voided = service.handle_order_cancelled(
        order_id=order_id,
        cancelling_user_id=verified_buyer.id,
        reason="Buyer cancelled order before fulfillment delivery",
    )
    assert len(voided) == 1

    db_session.expire_all()
    refreshed_app = db_session.get(RequirementFulfillmentApproval, approval.id)
    assert refreshed_app.status == APPROVAL_STATUS_VOIDED
    assert refreshed_app.voided_by_user_id == verified_buyer.id
    assert refreshed_app.voided_at is not None
    assert refreshed_app.void_reason == "Buyer cancelled order before fulfillment delivery"


def test_order_cancellation_leaves_approved_records_unchanged(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """Already 'approved' approvals are terminal and are not voided by order cancellation."""
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
    offer_id = r1.json()["id"]
    acc = client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))
    order_id = uuid.UUID(acc.json()["order_id"])

    approval = db_session.query(RequirementFulfillmentApproval).filter(
        RequirementFulfillmentApproval.order_id == order_id
    ).first()

    # Buyer approves
    client.post(
        f"/api/v1/requirements/fulfillment-approvals/{approval.id}/approve",
        json={},
        headers=auth_headers(verified_buyer),
    )
    db_session.expire_all()

    # Now simulate order cancellation
    service = FulfillmentApprovalService(db_session)
    voided = service.handle_order_cancelled(
        order_id=order_id,
        cancelling_user_id=None,
        reason="System cancellation",
    )
    # No pending approvals were voided
    assert len(voided) == 0

    db_session.expire_all()
    refreshed_app = db_session.get(RequirementFulfillmentApproval, approval.id)
    assert refreshed_app.status == APPROVAL_STATUS_APPROVED


# ===========================================================================
# 10. Database Constraints & Invariants Tests
# ===========================================================================

def test_database_check_constraint_invariants_rejected_on_invalid_insert(
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    buyer_requirement: BuyerRequirement,
):
    """Verify that SQLite/PostgreSQL enforces chk_approval_complete_invariants:
    1. pending cannot have approved_quantity
    2. approved cannot have null approved_quantity
    """
    conv = Conversation(
        buyer_id=verified_buyer.id,
        farmer_id=verified_farmer.id,
    )
    db_session.add(conv)
    db_session.flush()

    offer = Offer(
        offer_number="OFF-CHK-001",
        conversation_id=conv.id,
        sender_id=verified_farmer.id,
        recipient_id=verified_buyer.id,
        total_amount=Decimal("100.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db_session.add(offer)
    db_session.flush()

    order = Order(
        order_number="ORD-TEST-CHK",
        source_offer_id=offer.id,
        buyer_id=verified_buyer.id,
        farmer_id=verified_farmer.id,
        total_amount=Decimal("100.00"),
        status=ORDER_STATUS_PENDING,
    )
    db_session.add(order)
    db_session.flush()

    order_item = OrderItem(
        order_id=order.id,
        buyer_requirement_id=buyer_requirement.id,
        product_name="Tomatoes",
        quantity=Decimal("30.000"),
        unit="kg",
        unit_price=Decimal("25.00"),
        subtotal=Decimal("750.00"),
        status=ORDER_ITEM_STATUS_CONFIRMED,
    )
    db_session.add(order_item)
    db_session.flush()

    # Case 1: pending with approved_quantity set -> FAIL
    bad_pending = RequirementFulfillmentApproval(
        requirement_id=buyer_requirement.id,
        order_id=order.id,
        order_item_id=order_item.id,
        proposed_quantity=Decimal("30.000"),
        approved_quantity=Decimal("30.000"),  # Invalid for pending!
        status=APPROVAL_STATUS_PENDING,
    )
    db_session.add(bad_pending)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Case 2: approved with null approved_quantity -> FAIL
    conv2 = Conversation(
        buyer_id=verified_buyer.id,
        farmer_id=verified_farmer.id,
    )
    db_session.add(conv2)
    db_session.flush()

    offer2 = Offer(
        offer_number="OFF-CHK-002",
        conversation_id=conv2.id,
        sender_id=verified_farmer.id,
        recipient_id=verified_buyer.id,
        total_amount=Decimal("100.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db_session.add(offer2)
    db_session.flush()

    order2 = Order(
        order_number="ORD-TEST-CHK2",
        source_offer_id=offer2.id,
        buyer_id=verified_buyer.id,
        farmer_id=verified_farmer.id,
        total_amount=Decimal("100.00"),
        status=ORDER_STATUS_PENDING,
    )
    db_session.add(order2)
    db_session.flush()

    order_item2 = OrderItem(
        order_id=order2.id,
        buyer_requirement_id=buyer_requirement.id,
        product_name="Tomatoes",
        quantity=Decimal("30.000"),
        unit="kg",
        unit_price=Decimal("25.00"),
        subtotal=Decimal("750.00"),
        status=ORDER_ITEM_STATUS_CONFIRMED,
    )
    db_session.add(order_item2)
    db_session.flush()

    bad_approved = RequirementFulfillmentApproval(
        requirement_id=buyer_requirement.id,
        order_id=order2.id,
        order_item_id=order_item2.id,
        proposed_quantity=Decimal("30.000"),
        approved_quantity=None,  # Invalid for approved!
        status=APPROVAL_STATUS_APPROVED,
        reviewed_by_user_id=verified_buyer.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(bad_approved)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_hard_delete_requirement_blocked_by_approval_fk_restrict(
    client: TestClient,
    db_session: Session,
    verified_buyer: User,
    verified_farmer: User,
    farmer_listing: ProduceListing,
    buyer_requirement: BuyerRequirement,
):
    """ADR-003 Section 5.3: Attempting to hard-delete a requirement while an approval record
    references it fails with foreign key violation (ON DELETE RESTRICT).
    """
    r1 = client.post(
        "/api/v1/offers",
        json={
            "recipient_id": str(verified_farmer.id),
            "items": [
                {
                    "listing_id": str(farmer_listing.id),
                    "buyer_requirement_id": str(buyer_requirement.id),
                    "quantity": 25.0,
                    "unit": "kg",
                    "unit_price": 25.0,
                }
            ],
        },
        headers=auth_headers(verified_buyer),
    )
    offer_id = r1.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/accept", headers=auth_headers(verified_farmer))

    req_to_del = db_session.get(BuyerRequirement, buyer_requirement.id)
    db_session.delete(req_to_del)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
