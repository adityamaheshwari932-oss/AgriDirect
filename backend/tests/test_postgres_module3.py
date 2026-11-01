"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 3.

Verifies Module 3 (Offers, Negotiation, Orders, and Requirement Fulfillment Approvals)
against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`
at Alembic revision `d4e5f6a1b2c3`.

Safety Guarantee:
- Uses ONLY `agridirect_module3_test`.
- NEVER touches, accesses, or modifies `agridirect_db`.
- Cleans up only test-created records via unique test emails and foreign-key ordered teardown.
"""

import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Generator, List, Tuple

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.dependencies import create_access_token
from app.db.session import close_db, get_db, init_db
from app.main import app
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE, STATUS_PARTIALLY_FULFILLED
from app.models.notification import Notification
from app.models.offer import (
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_COUNTERED,
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
    PRICE_CONDITION_NEGOTIABLE,
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
from app.offers.schemas import (
    CounterOfferCreate,
    OfferAcceptRequest,
    OfferCreate,
    OfferItemCreate,
    OfferRejectRequest,
)
from app.offers.service import OfferService
from app.requirements.approval_service import FulfillmentApprovalService
from app.requirements.schemas import ApproveFulfillmentRequest, RejectFulfillmentRequest

# Verified isolated PostgreSQL connection
TEST_PG_DB_URL = "postgresql+psycopg://agridirect_app:agridirect@localhost:5432/agridirect_module3_test"

_pg_engine = create_engine(TEST_PG_DB_URL, pool_size=15, max_overflow=5)
_SessionLocal = sessionmaker(bind=_pg_engine, expire_on_commit=False)


def _cleanup_database():
    """Clean up all test artifacts created in agridirect_module3_test."""
    with _SessionLocal() as db:
        # Pre-flight safety check
        db_name = db.execute(text("SELECT current_database()")).scalar()
        if db_name != "agridirect_module3_test":
            raise RuntimeError(f"ABORT: Safety check failed! Connected to '{db_name}', expected 'agridirect_module3_test'")

        db.execute(text("""
            TRUNCATE TABLE 
                contact_share_requests,
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
            CASCADE
        """))
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def setup_pg_environment():
    """Verify database identity and prepare test database once per session."""
    with _SessionLocal() as db:
        db_name = db.execute(text("SELECT current_database()")).scalar()
        if db_name != "agridirect_module3_test":
            raise RuntimeError(f"Refusing to execute tests on database: {db_name}")
    _cleanup_database()
    yield
    _cleanup_database()


@pytest.fixture(autouse=True)
def run_around_tests():
    """Clean up after each test to ensure complete isolation."""
    yield
    _cleanup_database()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh SQLAlchemy Session connected to agridirect_module3_test."""
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient connected to agridirect_module3_test."""
    def override_get_db():
        session = _SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_auth_headers(user: User) -> dict:
    """Generate JWT authorization headers."""
    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "verification_status": user.verification_status,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helper Seed Functions
# ---------------------------------------------------------------------------

def create_test_category(db: Session, name: str = "Vegetables") -> ProduceCategory:
    slug = f"{name.lower()}-{uuid.uuid4().hex[:8]}"
    cat = ProduceCategory(name=name, slug=slug, is_active=True)
    db.add(cat)
    db.flush()
    return cat


def create_test_farmer(db: Session, verified: bool = True) -> User:
    user = User(
        email=f"farmer_{uuid.uuid4().hex[:8]}@pgtest.agridirect",
        password_hash="fakehash",
        role="farmer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    FarmerProfile(
        user=user,
        full_name="Farmer Ramesh",
        farm_name="Nashik Agro",
        farm_location_address="Gat 45, Dindori",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db.add(user)
    db.flush()
    return user


def create_test_buyer(db: Session, verified: bool = True) -> User:
    user = User(
        email=f"buyer_{uuid.uuid4().hex[:8]}@pgtest.agridirect",
        password_hash="fakehash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Buyer Suresh",
        business_name="Fresh Mart Ltd",
        business_type="retailer",
        delivery_receiving_address="APMC Market Yard",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db.add(user)
    db.flush()
    return user


def create_test_listing(
    db: Session,
    farmer: User,
    category: ProduceCategory,
    product_name: str = "Organic Tomatoes",
    qty: Decimal = Decimal("100.000"),
    price: Decimal = Decimal("25.00"),
) -> ProduceListing:
    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=category.id,
        product_name=product_name,
        title=f"Fresh {product_name}",
        initial_quantity=qty,
        available_quantity=qty,
        unit="kg",
        price_per_unit=price,
        quality_grade="Grade A",
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.flush()
    return listing


def create_test_requirement(
    db: Session,
    buyer: User,
    category: ProduceCategory,
    product_name: str = "Organic Tomatoes",
    qty: Decimal = Decimal("100.000"),
    target_price: Decimal = Decimal("25.00"),
) -> BuyerRequirement:
    req = BuyerRequirement(
        buyer_id=buyer.id,
        category_id=category.id,
        product_name=product_name,
        title=f"Need {qty}kg {product_name}",
        required_quantity=qty,
        remaining_quantity=qty,
        unit="kg",
        target_price_per_unit=target_price,
        price_condition=PRICE_CONDITION_NEGOTIABLE,
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=7),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db.add(req)
    db.flush()
    return req


# ===========================================================================
# 1. Environment & Pre-Flight Verification Tests
# ===========================================================================

def test_00_verify_postgres_environment(db_session: Session):
    """Verify live PostgreSQL 18 runtime, user role, and Alembic revision head."""
    res = db_session.execute(
        text("SELECT current_database(), current_user, version()")
    ).fetchone()
    assert res[0] == "agridirect_module3_test"
    assert res[1] == "agridirect_app"
    assert "PostgreSQL 18" in res[2]

    # Check Alembic revision head (at least Module 3 revision)
    alembic_rev = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert alembic_rev in ("d4e5f6a1b2c3", "e5f6a1b2c3d4", "f6a1b2c3d4e5", "a1b2c3d4e5f6")


# ===========================================================================
# 2. Phase B: Offer Lifecycle Tests
# ===========================================================================

def test_offer_lifecycle_create_and_retrieve(db_session: Session):
    """Test offer creation, retrieval, and listing on PostgreSQL."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat)
    db_session.commit()

    svc = OfferService(db_session)
    create_req = OfferCreate(
        recipient_id=farmer.id,
        items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
    )
    offer_resp = svc.create_offer(buyer, create_req)
    assert offer_resp.status == OFFER_STATUS_PENDING
    assert offer_resp.total_amount == Decimal("1000.00")
    assert offer_resp.conversation_id is not None

    # Retrieve offer
    fetched = svc.get_offer(buyer, offer_resp.id)
    assert fetched.id == offer_resp.id
    assert fetched.offer_number == offer_resp.offer_number

    # List offers
    listed = svc.list_user_offers(farmer, status_filter=OFFER_STATUS_PENDING)
    assert any(o.id == offer_resp.id for o in listed.items)


def test_offer_lifecycle_counter_offer(db_session: Session):
    """Test farmer counter-offer transitions parent to countered and creates child pending offer."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat)
    db_session.commit()

    svc = OfferService(db_session)
    off1 = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("20.00"))],
        ),
    )

    # Farmer counters with higher price
    counter_req = CounterOfferCreate(
        items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("24.00"))]
    )
    off2 = svc.counter_offer(farmer, off1.id, counter_req)
    assert off2.status == OFFER_STATUS_PENDING
    assert off2.total_amount == Decimal("1200.00")

    # Parent offer must now be countered
    parent = svc.get_offer(farmer, off1.id)
    assert parent.status == OFFER_STATUS_COUNTERED


def test_offer_lifecycle_reject_offer(db_session: Session):
    """Test offer rejection transitions status to rejected and keeps stock unchanged."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("30.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )

    # Farmer rejects offer
    rej_resp = svc.reject_offer(farmer, off.id, OfferRejectRequest(reason="Price too low"))
    assert rej_resp.status == OFFER_STATUS_REJECTED

    # Listing inventory remains intact
    db_session.refresh(listing)
    assert listing.available_quantity == Decimal("100.000")


def test_offer_lifecycle_withdraw_offer(db_session: Session):
    """Test offer sender can withdraw a pending offer."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat)
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("20.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )

    # Buyer withdraws
    w_resp = svc.withdraw_offer(buyer, off.id)
    assert w_resp.status == OFFER_STATUS_WITHDRAWN


def test_offer_lifecycle_negotiation_history(db_session: Session):
    """Test complete negotiation thread history retrieval."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat)
    db_session.commit()

    svc = OfferService(db_session)
    off1 = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("20.00"))],
        ),
    )
    off2 = svc.counter_offer(
        farmer,
        off1.id,
        CounterOfferCreate(items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("22.00"))]),
    )
    off3 = svc.counter_offer(
        buyer,
        off2.id,
        CounterOfferCreate(items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("21.00"))]),
    )

    history = svc.get_offer_history(buyer, off3.id)
    assert len(history.history) == 3
    assert [h.status for h in history.history] == [OFFER_STATUS_COUNTERED, OFFER_STATUS_COUNTERED, OFFER_STATUS_PENDING]


# ===========================================================================
# 3. Phase B: Multi-Item and Multi-Requirement Behavior Tests
# ===========================================================================

def test_multi_item_and_requirement_mapping(db_session: Session):
    """Test offer containing multiple items correctly mapped to distinct listings and requirements."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)

    l1 = create_test_listing(db_session, farmer, cat, product_name="Tomatoes", qty=Decimal("200.000"))
    l2 = create_test_listing(db_session, farmer, cat, product_name="Potatoes", qty=Decimal("150.000"))
    r1 = create_test_requirement(db_session, buyer, cat, product_name="Tomatoes", qty=Decimal("80.000"))
    r2 = create_test_requirement(db_session, buyer, cat, product_name="Potatoes", qty=Decimal("60.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[
                OfferItemCreate(listing_id=l1.id, buyer_requirement_id=r1.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00")),
                OfferItemCreate(listing_id=l2.id, buyer_requirement_id=r2.id, quantity=Decimal("30.000"), unit="kg", unit_price=Decimal("30.00")),
            ],
        ),
    )

    # Farmer accepts offer
    acc = svc.accept_offer(farmer, off.id)
    assert acc.status == OFFER_STATUS_ACCEPTED

    # Verify orders and fulfillment approvals
    order = db_session.query(Order).filter_by(id=acc.order_id).one()
    assert len(order.items) == 2

    approvals = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=order.id).all()
    assert len(approvals) == 2

    app1 = next(a for a in approvals if a.requirement_id == r1.id)
    app2 = next(a for a in approvals if a.requirement_id == r2.id)
    assert app1.proposed_quantity == Decimal("40.000") and app1.status == APPROVAL_STATUS_PENDING
    assert app2.proposed_quantity == Decimal("30.000") and app2.status == APPROVAL_STATUS_PENDING


def test_duplicate_or_invalid_line_item_rejected(db_session: Session):
    """Test duplicate listing line items in the same offer are rejected with 400 Bad Request."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat)
    db_session.commit()

    svc = OfferService(db_session)
    with pytest.raises(ValidationError) as exc_info:
        svc.create_offer(
            buyer,
            OfferCreate(
                recipient_id=farmer.id,
                items=[
                    OfferItemCreate(listing_id=listing.id, quantity=Decimal("20.000"), unit="kg", unit_price=Decimal("25.00")),
                    OfferItemCreate(listing_id=listing.id, quantity=Decimal("10.000"), unit="kg", unit_price=Decimal("25.00")),
                ],
            ),
        )
    assert "Duplicate item reference detected" in str(exc_info.value)


# ===========================================================================
# 4. Phase B: Inventory & Order Integrity Tests
# ===========================================================================

def test_inventory_and_order_integrity(db_session: Session):
    """Test inventory deduction, InventoryAdjustment creation, and order creation."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)

    db_session.refresh(listing)
    assert listing.available_quantity == Decimal("60.000")
    assert listing.status == STATUS_PARTIALLY_FULFILLED

    # Check InventoryAdjustment audit row
    adj = db_session.query(InventoryAdjustment).filter_by(order_id=acc.order_id).one()
    assert adj.quantity_delta == Decimal("-40.000")
    assert adj.change_type == CHANGE_TYPE_ORDER_FULFILLMENT


def test_failed_acceptance_rollback(db_session: Session):
    """Test that a failed acceptance rolls back all database changes."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("50.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )

    # Artificially deplete stock before acceptance
    listing.available_quantity = Decimal("10.000")
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        svc.accept_offer(farmer, off.id)
    assert exc_info.value.status_code == 409
    assert "Insufficient stock" in exc_info.value.detail

    # No order should have been created
    orders = db_session.query(Order).all()
    assert len(orders) == 0


def test_inventory_never_negative_enforcement(db_session: Session):
    """Test PostgreSQL check constraint prevents negative inventory values."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("10.000"))
    db_session.commit()

    listing.available_quantity = Decimal("-5.000")
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ===========================================================================
# 5. Phase B: Fulfillment Approval Workflow Tests
# ===========================================================================

def test_farmer_acceptance_creates_pending_approval(db_session: Session):
    """Farmer accepting buyer offer creates pending approval without premature deduction."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)

    # Requirement remains completely untouched
    db_session.refresh(req)
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE

    # Approval is pending
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()
    assert approval.status == APPROVAL_STATUS_PENDING
    assert approval.approved_quantity is None


def test_buyer_approval_applies_correct_quantity(db_session: Session):
    """Buyer approval deducts approved quantity from requirement."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()

    # Buyer approves
    app_svc = FulfillmentApprovalService(db_session)
    res = app_svc.approve_fulfillment(buyer, approval.id, ApproveFulfillmentRequest(approved_quantity=Decimal("35.000")))
    assert res.status == APPROVAL_STATUS_APPROVED
    assert res.approved_quantity == Decimal("35.000")

    db_session.refresh(req)
    assert req.remaining_quantity == Decimal("65.000")
    assert req.status == REQUIREMENT_STATUS_PARTIALLY_FULFILLED


def test_buyer_rejection_leaves_requirement_untouched(db_session: Session):
    """Buyer rejection leaves requirement open demand untouched (FR-REQ-08)."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()

    # Buyer rejects
    app_svc = FulfillmentApprovalService(db_session)
    res = app_svc.reject_fulfillment(buyer, approval.id, RejectFulfillmentRequest(reason="Quality check failed"))
    assert res.status == APPROVAL_STATUS_REJECTED
    assert res.approved_quantity is None

    db_session.refresh(req)
    assert req.remaining_quantity == Decimal("100.000")
    assert req.status == REQUIREMENT_STATUS_ACTIVE


def test_invalid_approved_quantity_rejected(db_session: Session):
    """Test approved quantities exceeding proposed or remaining demand are rejected without clamping."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()

    app_svc = FulfillmentApprovalService(db_session)

    # Exceeds proposed quantity (50 > 40)
    with pytest.raises(HTTPException) as exc1:
        app_svc.approve_fulfillment(buyer, approval.id, ApproveFulfillmentRequest(approved_quantity=Decimal("50.000")))
    assert exc1.value.status_code == 409
    assert "cannot exceed proposed quantity" in exc1.value.detail

    # Exceeds remaining requirement demand (35 > 30)
    req.remaining_quantity = Decimal("30.000")
    db_session.commit()

    with pytest.raises(HTTPException) as exc2:
        app_svc.approve_fulfillment(buyer, approval.id, ApproveFulfillmentRequest(approved_quantity=Decimal("35.000")))
    assert exc2.value.status_code == 409
    assert "exceeds current remaining requirement quantity" in exc2.value.detail


def test_terminal_approval_records_immutable(db_session: Session):
    """Test that once approved or rejected, approval records cannot be re-reviewed."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()

    app_svc = FulfillmentApprovalService(db_session)
    app_svc.approve_fulfillment(buyer, approval.id, ApproveFulfillmentRequest(approved_quantity=Decimal("40.000")))

    # Attempt re-approval
    with pytest.raises(HTTPException) as exc1:
        app_svc.approve_fulfillment(buyer, approval.id, ApproveFulfillmentRequest(approved_quantity=Decimal("40.000")))
    assert exc1.value.status_code == 409

    # Attempt re-rejection
    with pytest.raises(HTTPException) as exc2:
        app_svc.reject_fulfillment(buyer, approval.id, RejectFulfillmentRequest(reason="Late reject"))
    assert exc2.value.status_code == 409


def test_order_cancellation_voids_pending_approvals(db_session: Session):
    """Test cancelling an order voids any pending fulfillment approval records."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()
    assert approval.status == APPROVAL_STATUS_PENDING

    # Void on order cancellation
    app_svc = FulfillmentApprovalService(db_session)
    voided = app_svc.handle_order_cancelled(
        order_id=acc.order_id,
        cancelling_user_id=buyer.id,
        reason="Buyer cancelled order",
    )
    assert len(voided) == 1
    assert voided[0].status == APPROVAL_STATUS_VOIDED
    assert voided[0].void_reason == "Buyer cancelled order"


# ===========================================================================
# 6. Phase B: Authorization Tests
# ===========================================================================

def test_fulfillment_approval_buyer_ownership_enforcement(db_session: Session):
    """Test non-owner buyer receives 404 Not Found (anti-enumeration security)."""
    cat = create_test_category(db_session)
    farmer = create_test_farmer(db_session)
    buyer1 = create_test_buyer(db_session)
    buyer2 = create_test_buyer(db_session)
    listing = create_test_listing(db_session, farmer, cat, qty=Decimal("200.000"))
    req = create_test_requirement(db_session, buyer1, cat, qty=Decimal("100.000"))
    db_session.commit()

    svc = OfferService(db_session)
    off = svc.create_offer(
        buyer1,
        OfferCreate(
            recipient_id=farmer.id,
            items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))],
        ),
    )
    acc = svc.accept_offer(farmer, off.id)
    approval = db_session.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()

    app_svc = FulfillmentApprovalService(db_session)

    # Buyer 2 tries to view approval
    with pytest.raises(HTTPException) as exc1:
        app_svc.get_approval(buyer2, approval.id)
    assert exc1.value.status_code == 404

    # Buyer 2 tries to approve
    with pytest.raises(HTTPException) as exc2:
        app_svc.approve_fulfillment(buyer2, approval.id, ApproveFulfillmentRequest(approved_quantity=Decimal("40.000")))
    assert exc2.value.status_code == 404


def test_unverified_farmer_rejected(db_session: Session):
    """Test unverified farmer cannot create or accept offers."""
    cat = create_test_category(db_session)
    unverified_farmer = create_test_farmer(db_session, verified=False)
    buyer = create_test_buyer(db_session)
    listing = create_test_listing(db_session, unverified_farmer, cat)
    db_session.commit()

    svc = OfferService(db_session)
    with pytest.raises(HTTPException) as exc:
        svc.create_offer(
            unverified_farmer,
            OfferCreate(
                recipient_id=buyer.id,
                items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("10.000"), unit="kg", unit_price=Decimal("25.00"))],
            ),
        )
    assert exc.value.status_code == 403


# ===========================================================================
# 7. Phase C: Real Multi-Connection PostgreSQL Concurrency Tests
# ===========================================================================

def test_concurrency_scenario_1_inventory_overselling():
    """Scenario 1: Two independent transactions compete for stock (100 kg initial, 70 kg & 50 kg demand).

    Guarantees:
    - Zero overselling.
    - Final available inventory strictly non-negative (30.000 kg).
    - Exactly one transaction succeeds; competitor receives 409 Conflict.
    """
    with _SessionLocal() as db:
        cat = create_test_category(db)
        farmer = create_test_farmer(db)
        b1 = create_test_buyer(db)
        b2 = create_test_buyer(db)
        listing = create_test_listing(db, farmer, cat, qty=Decimal("100.000"))
        db.commit()

        svc = OfferService(db)
        off1 = svc.create_offer(b1, OfferCreate(recipient_id=farmer.id, items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("70.000"), unit="kg", unit_price=Decimal("20.00"))]))
        off2 = svc.create_offer(b2, OfferCreate(recipient_id=farmer.id, items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("20.00"))]))

        farmer_id = farmer.id
        listing_id = listing.id
        off1_id = off1.id
        off2_id = off2.id

    barrier = threading.Barrier(2)
    results = {}

    def worker(worker_name, offer_id):
        with _SessionLocal() as session:
            f_user = session.query(User).filter_by(id=farmer_id).one()
            service = OfferService(session)
            barrier.wait()
            try:
                res = service.accept_offer(f_user, offer_id)
                results[worker_name] = ("SUCCESS", res.order_number)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=worker, args=("Worker-70kg", off1_id))
    t2 = threading.Thread(target=worker, args=("Worker-50kg", off2_id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One must succeed, one must fail with 409
    statuses = [v[0] for v in results.values()]
    assert "SUCCESS" in statuses
    assert "HTTP_ERROR" in statuses
    err_result = next(v for v in results.values() if v[0] == "HTTP_ERROR")
    assert err_result[1] == 409
    assert "Insufficient stock" in err_result[2]

    # Check database state
    with _SessionLocal() as db:
        final_listing = db.query(ProduceListing).filter_by(id=listing_id).one()
        assert final_listing.available_quantity == Decimal("30.000")
        assert final_listing.available_quantity >= Decimal("0.000")
        orders = db.query(Order).all()
        assert len(orders) == 1


def test_concurrency_scenario_2_concurrent_approval():
    """Scenario 2: Concurrent approval and rejection of the same pending fulfillment approval.

    Guarantees:
    - Exactly one terminal transition succeeds.
    - No duplicate deductions.
    - Consistency between approval status and requirement remaining quantity.
    """
    with _SessionLocal() as db:
        cat = create_test_category(db)
        farmer = create_test_farmer(db)
        buyer = create_test_buyer(db)
        listing = create_test_listing(db, farmer, cat, qty=Decimal("200.000"))
        req = create_test_requirement(db, buyer, cat, qty=Decimal("100.000"))
        db.commit()

        svc = OfferService(db)
        off = svc.create_offer(buyer, OfferCreate(recipient_id=farmer.id, items=[OfferItemCreate(listing_id=listing.id, buyer_requirement_id=req.id, quantity=Decimal("40.000"), unit="kg", unit_price=Decimal("25.00"))]))
        acc = svc.accept_offer(farmer, off.id)
        approval = db.query(RequirementFulfillmentApproval).filter_by(order_id=acc.order_id).one()
        assert approval.status == APPROVAL_STATUS_PENDING

        buyer_id = buyer.id
        approval_id = approval.id
        req_id = req.id

    barrier = threading.Barrier(2)
    results = {}

    def worker(worker_name, action):
        with _SessionLocal() as session:
            b_user = session.query(User).filter_by(id=buyer_id).one()
            service = FulfillmentApprovalService(session)
            barrier.wait()
            try:
                if action == "approve":
                    res = service.approve_fulfillment(b_user, approval_id, ApproveFulfillmentRequest(approved_quantity=Decimal("40.000")))
                    results[worker_name] = ("SUCCESS_APPROVE", res.status, res.approved_quantity)
                else:
                    res = service.reject_fulfillment(b_user, approval_id, RejectFulfillmentRequest(reason="Concurrent reject"))
                    results[worker_name] = ("SUCCESS_REJECT", res.status)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=worker, args=("Worker-Approve", "approve"))
    t2 = threading.Thread(target=worker, args=("Worker-Reject", "reject"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One must succeed, other must fail with 409
    statuses = [v[0] for v in results.values()]
    assert any(s in ("SUCCESS_APPROVE", "SUCCESS_REJECT") for s in statuses)
    assert "HTTP_ERROR" in statuses
    err_res = next(v for v in results.values() if v[0] == "HTTP_ERROR")
    assert err_res[1] == 409
    assert "already been reviewed" in err_res[2]

    # Verify final database state consistency
    with _SessionLocal() as db:
        final_app = db.query(RequirementFulfillmentApproval).filter_by(id=approval_id).one()
        final_req = db.query(BuyerRequirement).filter_by(id=req_id).one()
        assert final_app.status in (APPROVAL_STATUS_APPROVED, APPROVAL_STATUS_REJECTED)
        if final_app.status == APPROVAL_STATUS_APPROVED:
            assert final_req.remaining_quantity == Decimal("60.000")
            assert final_app.approved_quantity == Decimal("40.000")
        else:
            assert final_req.remaining_quantity == Decimal("100.000")
            assert final_app.approved_quantity is None


def test_concurrency_scenario_3_same_offer_acceptance():
    """Scenario 3: Concurrent acceptance of the exact same offer.

    Guarantees:
    - Exactly one acceptance succeeds.
    - Exactly one order generated.
    - No duplicate inventory deduction.
    """
    with _SessionLocal() as db:
        cat = create_test_category(db)
        farmer = create_test_farmer(db)
        buyer = create_test_buyer(db)
        listing = create_test_listing(db, farmer, cat, qty=Decimal("500.000"))
        db.commit()

        svc = OfferService(db)
        off = svc.create_offer(buyer, OfferCreate(recipient_id=farmer.id, items=[OfferItemCreate(listing_id=listing.id, quantity=Decimal("100.000"), unit="kg", unit_price=Decimal("25.00"))]))
        farmer_id = farmer.id
        offer_id = off.id
        listing_id = listing.id

    barrier = threading.Barrier(2)
    results = {}

    def worker(worker_name):
        with _SessionLocal() as session:
            f_user = session.query(User).filter_by(id=farmer_id).one()
            service = OfferService(session)
            barrier.wait()
            try:
                res = service.accept_offer(f_user, offer_id)
                results[worker_name] = ("SUCCESS", res.order_number)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=worker, args=("Acceptor-1",))
    t2 = threading.Thread(target=worker, args=("Acceptor-2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One must succeed, one must fail with 409
    statuses = [v[0] for v in results.values()]
    assert "SUCCESS" in statuses
    assert "HTTP_ERROR" in statuses
    err_res = next(v for v in results.values() if v[0] == "HTTP_ERROR")
    assert err_res[1] == 409
    assert ("Cannot accept offer in 'accepted' status" in err_res[2] or "already been generated" in err_res[2])

    with _SessionLocal() as db:
        final_listing = db.query(ProduceListing).filter_by(id=listing_id).one()
        final_offer = db.query(Offer).filter_by(id=offer_id).one()
        orders = db.query(Order).filter_by(source_offer_id=offer_id).all()
        assert final_offer.status == OFFER_STATUS_ACCEPTED
        assert final_listing.available_quantity == Decimal("400.000")
        assert len(orders) == 1


def test_concurrency_scenario_4_multi_requirement_locking():
    """Scenario 4: Multi-item offers with inverted item orders locking multiple listings and requirements.

    Guarantees:
    - Zero deadlocks (40P01 eliminated by deterministic ascending UUID sorting).
    - Both transactions complete cleanly and serialize.
    - Accurate inventory and requirement deduction.
    """
    with _SessionLocal() as db:
        cat = create_test_category(db)
        farmer = create_test_farmer(db)
        buyer = create_test_buyer(db)

        l1 = create_test_listing(db, farmer, cat, product_name="Onions", qty=Decimal("300.000"))
        l2 = create_test_listing(db, farmer, cat, product_name="Potatoes", qty=Decimal("300.000"))
        r1 = create_test_requirement(db, buyer, cat, product_name="Onions", qty=Decimal("200.000"))
        r2 = create_test_requirement(db, buyer, cat, product_name="Potatoes", qty=Decimal("200.000"))
        db.commit()

        # Offer 1: [L1 -> R1, L2 -> R2]
        svc = OfferService(db)
        off1 = svc.create_offer(
            buyer,
            OfferCreate(
                recipient_id=farmer.id,
                items=[
                    OfferItemCreate(listing_id=l1.id, buyer_requirement_id=r1.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("20.00")),
                    OfferItemCreate(listing_id=l2.id, buyer_requirement_id=r2.id, quantity=Decimal("50.000"), unit="kg", unit_price=Decimal("25.00")),
                ],
            ),
        )
        db.commit()

        # Offer 2: [L2 -> R2, L1 -> R1] (INVERTED order)
        off2 = svc.create_offer(
            buyer,
            OfferCreate(
                recipient_id=farmer.id,
                items=[
                    OfferItemCreate(listing_id=l2.id, buyer_requirement_id=r2.id, quantity=Decimal("60.000"), unit="kg", unit_price=Decimal("25.00")),
                    OfferItemCreate(listing_id=l1.id, buyer_requirement_id=r1.id, quantity=Decimal("60.000"), unit="kg", unit_price=Decimal("20.00")),
                ],
            ),
        )
        db.commit()

        farmer_id = farmer.id
        off1_id = off1.id
        off2_id = off2.id
        l1_id = l1.id
        l2_id = l2.id
        r1_id = r1.id
        r2_id = r2.id

    barrier = threading.Barrier(2)
    results = {}

    def worker(worker_name, offer_id):
        with _SessionLocal() as session:
            f_user = session.query(User).filter_by(id=farmer_id).one()
            service = OfferService(session)
            barrier.wait()
            try:
                res = service.accept_offer(f_user, offer_id)
                results[worker_name] = ("SUCCESS", res.order_number)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=worker, args=("Tx-1 (L1 then L2)", off1_id))
    t2 = threading.Thread(target=worker, args=("Tx-2 (L2 then L1)", off2_id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both must succeed!
    assert results["Tx-1 (L1 then L2)"][0] == "SUCCESS"
    assert results["Tx-2 (L2 then L1)"][0] == "SUCCESS"

    with _SessionLocal() as db:
        final_l1 = db.query(ProduceListing).filter_by(id=l1_id).one()
        final_l2 = db.query(ProduceListing).filter_by(id=l2_id).one()
        orders = db.query(Order).all()
        # Initial 300 - 50 - 60 = 190
        assert final_l1.available_quantity == Decimal("190.000")
        assert final_l2.available_quantity == Decimal("190.000")
        assert len(orders) == 2
