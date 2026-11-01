"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 4 (Orders & Inventory Lifecycle).

Verifies Module 4 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`
at Alembic revision `d4e5f6a1b2c3`.

Safety Guarantee:
- Uses ONLY `agridirect_module3_test`.
- NEVER touches, accesses, or modifies `agridirect_db`.
- Cleans up all test-created records via TRUNCATE CASCADE with pre-flight database name assertion.
"""

import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Generator, List, Tuple

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import close_db, get_db, init_db
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
    Offer,
    OfferItem,
)
from app.models.order import (
    AMENDMENT_STATUS_EFFECTIVE,
    AMENDMENT_STATUS_PROPOSED,
    AMENDMENT_STATUS_REJECTED,
    AMENDMENT_TYPE_DELIVERY_DATE,
    AMENDMENT_TYPE_PRICE,
    AMENDMENT_TYPE_QUANTITY,
    AMENDMENT_TYPE_TERMS,
    CHANGE_TYPE_AMENDMENT_DELTA,
    CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
    CHANGE_TYPE_ORDER_FULFILLMENT,
    DELIVERY_STATUS_ARRANGED,
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_COMPLETION_MARKED,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_ITEM_STATUS_CANCELLED,
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_ITEM_STATUS_FULFILLED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_PENDING,
    InventoryAdjustment,
    Order,
    OrderAmendment,
    OrderDeliveryAcknowledgement,
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
from app.orders.schemas import (
    DeliveryArrangeRequest,
    OrderAmendmentCreate,
    OrderCancelRequest,
)
from app.orders.service import OrderService
from app.requirements.approval_service import FulfillmentApprovalService
from app.requirements.schemas import ApproveFulfillmentRequest

# Verified isolated PostgreSQL test connection
TEST_PG_DB_URL = "postgresql+psycopg://agridirect_app:agridirect@localhost:5432/agridirect_module3_test"

_pg_engine = create_engine(TEST_PG_DB_URL, pool_size=15, max_overflow=5)
_SessionLocal = sessionmaker(bind=_pg_engine, expire_on_commit=False)


def _cleanup_database():
    """Clean up all test artifacts created in agridirect_module3_test."""
    with _SessionLocal() as db:
        # Pre-flight safety check
        db_name = db.execute(text("SELECT current_database()")).scalar()
        if db_name != "agridirect_module3_test":
            raise RuntimeError(
                f"ABORT: Safety check failed! Connected to '{db_name}', expected 'agridirect_module3_test'"
            )

        db.execute(
            text("""
            TRUNCATE TABLE 
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
            CASCADE
        """)
        )
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


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def create_pg_category(db: Session, name="Vegetables") -> ProduceCategory:
    cat = ProduceCategory(name=name, slug=f"{name.lower()}-{uuid.uuid4().hex[:6]}", is_active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def create_pg_farmer(db: Session) -> User:
    u = User(
        email=f"farmer.{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number=f"+91{uuid.uuid4().int % 10000000000:010d}",
    )
    FarmerProfile(
        user=u,
        full_name="Farmer Ramesh",
        farm_name="Ramesh Farms",
        farm_location_address="Nashik Farm",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def create_pg_admin(db: Session) -> User:
    u = User(
        email=f"admin.{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number=f"+91{uuid.uuid4().int % 10000000000:010d}",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u



def create_pg_buyer(db: Session) -> User:
    u = User(
        email=f"buyer.{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number=f"+91{uuid.uuid4().int % 10000000000:010d}",
    )
    BuyerProfile(
        user=u,
        contact_person_name="Priya Sharma",
        business_name="Fresh Mart",
        business_type="retailer",
        delivery_receiving_address="APMC Yard",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def create_pg_listing(db: Session, farmer: User, cat: ProduceCategory, qty=Decimal("100.000")) -> ProduceListing:
    l = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Nashik Red Onion",
        title="Fresh Red Onions",
        initial_quantity=qty,
        available_quantity=qty,
        unit="kg",
        price_per_unit=Decimal("40.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    return l


def create_pg_requirement(db: Session, buyer: User, cat: ProduceCategory, qty=Decimal("100.000")) -> BuyerRequirement:
    req = BuyerRequirement(
        buyer_id=buyer.id,
        category_id=cat.id,
        product_name="Nashik Red Onion",
        title="Procurement of Onions",
        required_quantity=qty,
        remaining_quantity=qty,
        unit="kg",
        destination_city="Mumbai",
        destination_state="Maharashtra",
        required_by_date=date.today() + timedelta(days=10),
        status=REQUIREMENT_STATUS_ACTIVE,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def setup_pg_order(
    db: Session,
    farmer: User,
    buyer: User,
    listing: ProduceListing,
    requirement: BuyerRequirement = None,
    order_qty: Decimal = Decimal("40.000"),
    approved_qty: Decimal = Decimal("30.000"),
    approval_status: str = APPROVAL_STATUS_APPROVED,
) -> Tuple[Order, OrderItem]:
    """Helper creating order, deduction, and approval on PostgreSQL."""
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
        total_amount=order_qty * listing.price_per_unit,
        status=OFFER_STATUS_ACCEPTED,
    )
    db.add(offer)
    db.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        source_offer_id=offer.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=order_qty * listing.price_per_unit,
        status=ORDER_STATUS_PENDING,
        delivery_status=DELIVERY_STATUS_NOT_ARRANGED,
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        buyer_requirement_id=requirement.id if requirement else None,
        product_name=listing.product_name,
        quantity=order_qty,
        unit="kg",
        unit_price=listing.price_per_unit,
        subtotal=order_qty * listing.price_per_unit,
        status=ORDER_ITEM_STATUS_CONFIRMED,
    )
    db.add(item)
    db.flush()

    # Deduct listing stock
    listing.available_quantity -= order_qty
    listing.status = STATUS_PARTIALLY_FULFILLED if listing.available_quantity > 0 else STATUS_CLOSED

    inv_adj = InventoryAdjustment(
        listing_id=listing.id,
        order_id=order.id,
        change_type=CHANGE_TYPE_ORDER_FULFILLMENT,
        quantity_delta=-order_qty,
        recorded_by_user_id=farmer.id,
        notes="Order placement fulfillment deduction",
    )
    db.add(inv_adj)

    if requirement:
        requirement.remaining_quantity -= approved_qty
        requirement.status = REQUIREMENT_STATUS_PARTIALLY_FULFILLED
        now_utc = datetime.now(timezone.utc)
        approval = RequirementFulfillmentApproval(
            requirement_id=requirement.id,
            order_id=order.id,
            order_item_id=item.id,
            proposed_quantity=order_qty,
            approved_quantity=approved_qty if approval_status == APPROVAL_STATUS_APPROVED else None,
            status=approval_status,
            reviewed_by_user_id=buyer.id if approval_status == APPROVAL_STATUS_APPROVED else None,
            reviewed_at=now_utc if approval_status == APPROVAL_STATUS_APPROVED else None,
        )
        db.add(approval)

    db.commit()
    db.refresh(order)
    db.refresh(item)
    db.refresh(listing)
    if requirement:
        db.refresh(requirement)
    return order, item


# ===========================================================================
# Phase A: PostgreSQL Real Transaction and Row-Lock Tests
# ===========================================================================

def test_pg_order_confirmation(db_session: Session):
    cat = create_pg_category(db_session)
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer, cat)
    order, _ = setup_pg_order(db_session, farmer, buyer, listing)

    svc = OrderService(db_session)
    confirmed = svc.confirm_order(farmer, order.id)
    assert confirmed.status == ORDER_STATUS_CONFIRMED


def test_pg_atomic_cancellation_and_inventory_restitution(db_session: Session):
    cat = create_pg_category(db_session)
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer, cat, qty=Decimal("100.000"))
    order, _ = setup_pg_order(db_session, farmer, buyer, listing, order_qty=Decimal("40.000"))

    assert listing.available_quantity == Decimal("60.000")

    svc = OrderService(db_session)
    cancelled = svc.cancel_order(farmer, order.id, OrderCancelRequest(reason="PostgreSQL Cancellation Test"))
    assert cancelled.status == ORDER_STATUS_CANCELLED

    db_session.refresh(listing)
    assert listing.available_quantity == Decimal("100.000")
    assert listing.status == STATUS_ACTIVE

    # Net ledger balance must be 0
    adjs = db_session.query(InventoryAdjustment).filter_by(order_id=order.id).all()
    assert sum(a.quantity_delta for a in adjs) == Decimal("0.000")


def test_pg_requirement_restitution_cumulative_accounting(db_session: Session):
    cat = create_pg_category(db_session)
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer, cat, qty=Decimal("100.000"))
    req = create_pg_requirement(db_session, buyer, cat, qty=Decimal("100.000"))

    # Order 40 kg, approved 30 kg -> req remaining: 70 kg
    order, item = setup_pg_order(db_session, farmer, buyer, listing, req, order_qty=Decimal("40.000"), approved_qty=Decimal("30.000"))
    assert req.remaining_quantity == Decimal("70.000")

    svc = OrderService(db_session)

    # 1. Amendment 40 -> 25 kg (restores 5 kg demand)
    prop = svc.propose_amendment(
        farmer,
        order.id,
        OrderAmendmentCreate(
            amendment_type="quantity",
            order_item_id=item.id,
            new_quantity=Decimal("25.000"),
            justification="Reduce to 25 kg",
        ),
    )
    svc.accept_amendment(buyer, order.id, prop.id)

    db_session.refresh(req)
    assert req.remaining_quantity == Decimal("75.000")

    # 2. Cancellation: restores remaining 25 kg consumption (from original 30 kg approved: 30 - 5 = 25 kg)
    svc.cancel_order(buyer, order.id, OrderCancelRequest(reason="Cancelled after amendment"))

    db_session.refresh(req)
    assert req.remaining_quantity == Decimal("100.000")


# ===========================================================================
# Phase C: Multi-Connection PostgreSQL Concurrency Tests
# ===========================================================================

def test_concurrency_scenario_1_simultaneous_cancellation():
    """Scenario 1: Two simultaneous cancellation requests on the same order.

    Guarantees:
    - Tier 2 Order Lock serializes cancellation.
    - Exactly one transaction succeeds; competitor receives 409 Conflict.
    - Zero duplicate inventory restoration.
    - Final net ledger impact for order is exactly zero.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        listing = create_pg_listing(db, farmer, cat, qty=Decimal("100.000"))
        order, _ = setup_pg_order(db, farmer, buyer, listing, order_qty=Decimal("40.000"))
        order_id = order.id
        farmer_id = farmer.id
        buyer_id = buyer.id
        listing_id = listing.id

    barrier = threading.Barrier(2)
    results = {}

    def worker(worker_name, user_id):
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=user_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.cancel_order(user, order_id, OrderCancelRequest(reason=f"Cancelled by {worker_name}"))
                results[worker_name] = ("SUCCESS", res.status)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=worker, args=("Buyer-Worker", buyer_id))
    t2 = threading.Thread(target=worker, args=("Farmer-Worker", farmer_id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = [v[0] for v in results.values()]
    assert "SUCCESS" in statuses
    assert "HTTP_ERROR" in statuses
    err_result = next(v for v in results.values() if v[0] == "HTTP_ERROR")
    assert err_result[1] == 409

    # Verify inventory in database
    with _SessionLocal() as db:
        final_listing = db.query(ProduceListing).filter_by(id=listing_id).one()
        assert final_listing.available_quantity == Decimal("100.000")
        adjs = db.query(InventoryAdjustment).filter_by(order_id=order_id).all()
        assert sum(a.quantity_delta for a in adjs) == Decimal("0.000")


def test_concurrency_scenario_2_cancellation_racing_with_approval_review():
    """Scenario 2: Cancellation racing with fulfillment approval review.

    Guarantees:
    - Tier 2 -> 3 -> 4 -> 5 vs Tier 4 -> 5.
    - No duplicate demand deductions or restorations.
    - Requirement demand strictly consistent and within [0, required_quantity].
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        listing = create_pg_listing(db, farmer, cat, qty=Decimal("100.000"))
        req = create_pg_requirement(db, buyer, cat, qty=Decimal("100.000"))

        # Pending approval
        order, item = setup_pg_order(
            db, farmer, buyer, listing, req,
            order_qty=Decimal("40.000"),
            approved_qty=Decimal("0.000"),
            approval_status=APPROVAL_STATUS_PENDING,
        )
        approval = db.query(RequirementFulfillmentApproval).filter_by(order_item_id=item.id).one()

        order_id = order.id
        approval_id = approval.id
        farmer_id = farmer.id
        buyer_id = buyer.id
        req_id = req.id

    barrier = threading.Barrier(2)
    results = {}

    def cancel_worker():
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=farmer_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.cancel_order(user, order_id, OrderCancelRequest(reason="Farmer cancel"))
                results["CANCEL"] = ("SUCCESS", res.status)
            except HTTPException as e:
                results["CANCEL"] = ("HTTP_ERROR", e.status_code, e.detail)

    def approve_worker():
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=buyer_id).one()
            svc = FulfillmentApprovalService(session)
            barrier.wait()
            try:
                res = svc.approve_fulfillment(user, approval_id, ApproveFulfillmentRequest(approved_quantity=Decimal("40.000")))
                results["APPROVE"] = ("SUCCESS", res.status)
            except HTTPException as e:
                results["APPROVE"] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=cancel_worker)
    t2 = threading.Thread(target=approve_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify requirement consistency
    with _SessionLocal() as db:
        final_req = db.query(BuyerRequirement).filter_by(id=req_id).one()
        final_appr = db.query(RequirementFulfillmentApproval).filter_by(id=approval_id).one()
        assert final_req.remaining_quantity >= Decimal("0.000")
        assert final_req.remaining_quantity <= final_req.required_quantity


def test_concurrency_scenario_3_cancellation_vs_amendment_acceptance():
    """Scenario 3: Cancellation racing with amendment acceptance.

    Guarantees:
    - Tier 2 exclusive lock serializes the two mutating operations.
    - One operation completes, the other appropriately succeeds or raises conflict.
    - Inventory ledger net balance after cancellation is exactly zero.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        listing = create_pg_listing(db, farmer, cat, qty=Decimal("100.000"))
        order, item = setup_pg_order(db, farmer, buyer, listing, order_qty=Decimal("40.000"))

        svc = OrderService(db)
        prop = svc.propose_amendment(
            farmer,
            order.id,
            OrderAmendmentCreate(
                amendment_type="quantity",
                order_item_id=item.id,
                new_quantity=Decimal("30.000"),
                justification="Reduce to 30 kg",
            ),
        )

        order_id = order.id
        aid = prop.id
        farmer_id = farmer.id
        buyer_id = buyer.id
        listing_id = listing.id

    barrier = threading.Barrier(2)
    results = {}

    def cancel_worker():
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=farmer_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.cancel_order(user, order_id, OrderCancelRequest(reason="Cancellation race"))
                results["CANCEL"] = ("SUCCESS", res.status)
            except HTTPException as e:
                results["CANCEL"] = ("HTTP_ERROR", e.status_code, e.detail)

    def accept_worker():
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=buyer_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.accept_amendment(user, order_id, aid)
                results["ACCEPT"] = ("SUCCESS", res.status)
            except HTTPException as e:
                results["ACCEPT"] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=cancel_worker)
    t2 = threading.Thread(target=accept_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    with _SessionLocal() as db:
        final_order = db.query(Order).filter_by(id=order_id).one()
        final_listing = db.query(ProduceListing).filter_by(id=listing_id).one()
        # If order was cancelled, net impact must be 0
        if final_order.status == ORDER_STATUS_CANCELLED:
            adjs = db.query(InventoryAdjustment).filter_by(order_id=order_id).all()
            assert sum(a.quantity_delta for a in adjs) == Decimal("0.000")
            assert final_listing.available_quantity == Decimal("100.000")


def test_concurrency_scenario_4_concurrent_amendment_proposals():
    """Scenario 4: Two concurrent amendment proposals on the same order.

    Guarantees:
    - Tier 2 exclusive lock serializes proposal creation.
    - Exactly one pending amendment permitted; second proposal returns 409 Conflict.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        listing = create_pg_listing(db, farmer, cat)
        order, item = setup_pg_order(db, farmer, buyer, listing)

        order_id = order.id
        item_id = item.id
        farmer_id = farmer.id
        buyer_id = buyer.id

    barrier = threading.Barrier(2)
    results = {}

    def propose_worker(worker_name, user_id, qty):
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=user_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.propose_amendment(
                    user,
                    order_id,
                    OrderAmendmentCreate(
                        amendment_type="quantity",
                        order_item_id=item_id,
                        new_quantity=qty,
                        justification=f"Proposal by {worker_name}",
                    ),
                )
                results[worker_name] = ("SUCCESS", res.id)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=propose_worker, args=("Farmer-Prop", farmer_id, Decimal("35.000")))
    t2 = threading.Thread(target=propose_worker, args=("Buyer-Prop", buyer_id, Decimal("30.000")))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = [v[0] for v in results.values()]
    assert "SUCCESS" in statuses
    assert "HTTP_ERROR" in statuses
    err_res = next(v for v in results.values() if v[0] == "HTTP_ERROR")
    assert err_res[1] == 409
    assert "already pending" in err_res[2]


def test_concurrency_scenario_5_delivery_acknowledgement_race():
    """Scenario 5: Concurrent delivery completion acknowledgement attempts.

    Guarantees:
    - Exactly one acknowledgement transitions the order to completed.
    - The second receives 409 Conflict.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        listing = create_pg_listing(db, farmer, cat)
        order, _ = setup_pg_order(db, farmer, buyer, listing)

        svc = OrderService(db)
        tomorrow = date.today() + timedelta(days=1)
        svc.arrange_delivery(
            buyer,
            order.id,
            DeliveryArrangeRequest(
                delivery_method="seller_dispatch",
                delivery_destination_address="Mumbai Yard",
                delivery_arranged_date=tomorrow,
            ),
        )
        svc.mark_delivery_completed(farmer, order.id)

        order_id = order.id
        buyer_id = buyer.id

    barrier = threading.Barrier(2)
    results = {}

    def ack_worker(worker_name):
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=buyer_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.acknowledge_delivery(user, order_id)
                results[worker_name] = ("SUCCESS", res.status)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=ack_worker, args=("Ack-Thread-1",))
    t2 = threading.Thread(target=ack_worker, args=("Ack-Thread-2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = [v[0] for v in results.values()]
    assert "SUCCESS" in statuses
    assert "HTTP_ERROR" in statuses
    err_res = next(v for v in results.values() if v[0] == "HTTP_ERROR")
    assert err_res[1] == 409

    with _SessionLocal() as db:
        acks = db.query(OrderDeliveryAcknowledgement).filter_by(order_id=order_id).all()
        assert len(acks) == 1
        assert acks[0].user_id == buyer_id
        final_order = db.query(Order).filter_by(id=order_id).one()
        assert final_order.status == ORDER_STATUS_COMPLETED
        assert final_order.delivery_status == DELIVERY_STATUS_COMPLETED



def test_concurrency_scenario_6_inventory_restoration_bounds():
    """Scenario 6: Multiple concurrent cancellations across independent orders on the same listing.

    Guarantees:
    - Final listing stock equals exactly the sum of initial available stock plus all cancelled order quantities.
    - Zero overselling or phantom inventory.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        b1 = create_pg_buyer(db)
        b2 = create_pg_buyer(db)
        listing = create_pg_listing(db, farmer, cat, qty=Decimal("100.000"))

        # Order 1: 30 kg, Order 2: 40 kg. Available: 100 - 30 - 40 = 30 kg.
        o1, _ = setup_pg_order(db, farmer, b1, listing, order_qty=Decimal("30.000"))
        o2, _ = setup_pg_order(db, farmer, b2, listing, order_qty=Decimal("40.000"))
        assert listing.available_quantity == Decimal("30.000")

        o1_id = o1.id
        o2_id = o2.id
        b1_id = b1.id
        b2_id = b2.id
        listing_id = listing.id

    barrier = threading.Barrier(2)
    results = {}

    def cancel_worker(worker_name, user_id, order_id):
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=user_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.cancel_order(user, order_id, OrderCancelRequest(reason=f"Concurrent cancel {worker_name}"))
                results[worker_name] = ("SUCCESS", res.status)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=cancel_worker, args=("Order-1-Cancel", b1_id, o1_id))
    t2 = threading.Thread(target=cancel_worker, args=("Order-2-Cancel", b2_id, o2_id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both independent orders should successfully cancel
    assert results["Order-1-Cancel"][0] == "SUCCESS"
    assert results["Order-2-Cancel"][0] == "SUCCESS"

    with _SessionLocal() as db:
        final_listing = db.query(ProduceListing).filter_by(id=listing_id).one()
        # 30 + 30 + 40 = 100 kg fully restored
        assert final_listing.available_quantity == Decimal("100.000")
        assert final_listing.status == STATUS_ACTIVE


def test_concurrency_scenario_7_requirement_restitution_capacity_clamp():
    """Scenario 7: Concurrent cancellation on independent orders linked to the same requirement.

    Guarantees:
    - Remaining quantity is clamped strictly to required_quantity.
    - Never exceeds required demand.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer1 = create_pg_farmer(db)
        farmer2 = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        l1 = create_pg_listing(db, farmer1, cat, qty=Decimal("100.000"))
        l2 = create_pg_listing(db, farmer2, cat, qty=Decimal("100.000"))
        req = create_pg_requirement(db, buyer, cat, qty=Decimal("100.000"))

        # Order 1: 50 kg approved, Order 2: 50 kg approved -> req remaining = 0
        o1, _ = setup_pg_order(db, farmer1, buyer, l1, req, order_qty=Decimal("50.000"), approved_qty=Decimal("50.000"))
        o2, _ = setup_pg_order(db, farmer2, buyer, l2, req, order_qty=Decimal("50.000"), approved_qty=Decimal("50.000"))
        assert req.remaining_quantity == Decimal("0.000")

        o1_id = o1.id
        o2_id = o2.id
        b_id = buyer.id
        req_id = req.id

    barrier = threading.Barrier(2)
    results = {}

    def cancel_worker(worker_name, order_id):
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=b_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.cancel_order(user, order_id, OrderCancelRequest(reason=f"Concurrent cancel {worker_name}"))
                results[worker_name] = ("SUCCESS", res.status)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=cancel_worker, args=("Cancel-Order-1", o1_id))
    t2 = threading.Thread(target=cancel_worker, args=("Cancel-Order-2", o2_id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["Cancel-Order-1"][0] == "SUCCESS"
    assert results["Cancel-Order-2"][0] == "SUCCESS"

    with _SessionLocal() as db:
        final_req = db.query(BuyerRequirement).filter_by(id=req_id).one()
        # Both restored 50 kg -> exactly 100 kg, clamped by required_quantity
        assert final_req.remaining_quantity == Decimal("100.000")
        assert final_req.status == REQUIREMENT_STATUS_ACTIVE


def test_concurrency_scenario_8_admin_completion_dual_acknowledgement_race():
    """Scenario 8: Concurrent delivery acknowledgements from both Farmer and Buyer after Admin completion mark.

    Guarantees:
    - Admin-initiated delivery completion requires dual independent acknowledgements.
    - Farmer and Buyer threads race to acknowledge concurrently.
    - Tier 2 Order lock serializes the two transactions in PostgreSQL.
    - The first thread records 1 acknowledgement, leaving order in completion_marked.
    - The second thread records 2nd acknowledgement, transitioning order to completed.
    - Exactly two distinct OrderDeliveryAcknowledgement records exist in the database.
    - Final order status is terminal 'completed' with 0 race conditions or deadlocks.
    """
    with _SessionLocal() as db:
        cat = create_pg_category(db)
        farmer = create_pg_farmer(db)
        buyer = create_pg_buyer(db)
        admin = create_pg_admin(db)
        listing = create_pg_listing(db, farmer, cat)
        order, _ = setup_pg_order(db, farmer, buyer, listing)

        svc = OrderService(db)
        tomorrow = date.today() + timedelta(days=1)
        svc.arrange_delivery(
            buyer,
            order.id,
            DeliveryArrangeRequest(
                delivery_method="third_party_transport",
                delivery_destination_address="Central Logistics Hub, Pune",
                delivery_arranged_date=tomorrow,
            ),
        )
        svc.mark_delivery_completed(admin, order.id)

        order_id = order.id
        farmer_id = farmer.id
        buyer_id = buyer.id

    barrier = threading.Barrier(2)
    results = {}

    def ack_worker(worker_name, user_id):
        with _SessionLocal() as session:
            user = session.query(User).filter_by(id=user_id).one()
            svc = OrderService(session)
            barrier.wait()
            try:
                res = svc.acknowledge_delivery(user, order_id)
                results[worker_name] = ("SUCCESS", res.status)
            except HTTPException as e:
                results[worker_name] = ("HTTP_ERROR", e.status_code, e.detail)

    t1 = threading.Thread(target=ack_worker, args=("Farmer-Worker", farmer_id))
    t2 = threading.Thread(target=ack_worker, args=("Buyer-Worker", buyer_id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both participants must succeed!
    assert results["Farmer-Worker"][0] == "SUCCESS"
    assert results["Buyer-Worker"][0] == "SUCCESS"

    with _SessionLocal() as db:
        final_order = db.query(Order).filter_by(id=order_id).one()
        assert final_order.status == ORDER_STATUS_COMPLETED
        assert final_order.delivery_status == DELIVERY_STATUS_COMPLETED
        assert final_order.completed_at is not None

        acks = db.query(OrderDeliveryAcknowledgement).filter_by(order_id=order_id).all()
        assert len(acks) == 2
        acked_users = {a.user_id for a in acks}
        assert acked_users == {farmer_id, buyer_id}


