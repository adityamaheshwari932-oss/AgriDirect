"""Automated unit and integration tests for AgriDirect Module 4 (Orders & Inventory Lifecycle).

Covers all batches:
- Batch 1: Order Listing, Details, and Farmer Confirmation
- Batch 2: Atomic Order Cancellation & Authoritative Restitution
- Batch 3: Bilateral Post-Finalization Amendments & Cumulative Accounting
- Batch 4: Delivery Coordination & Mutual Acknowledgement
- Batch 5: Inventory Audit Ledgers (Order & Listing)
"""

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple

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
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_VOIDED,
    RequirementFulfillmentApproval,
)
from app.models.user import BuyerProfile, FarmerProfile, User


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def sqlite_engine():
    """Isolated SQLite in-memory engine."""
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
def client(sqlite_engine) -> TestClient:
    """FastAPI TestClient with overridden get_db."""
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
    cat = ProduceCategory(name="Vegetables", slug="vegetables", is_active=True)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture
def farmer(db_session: Session) -> User:
    user = User(
        email="farmer.ramesh@test.com",
        password_hash="hash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543210",
    )
    FarmerProfile(
        user=user,
        full_name="Ramesh Kumar",
        farm_name="Ramesh Organic Farms",
        farm_location_address="Farm 12, Nashik",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def farmer_token(farmer: User) -> str:
    return create_access_token(data={"sub": str(farmer.id)})


@pytest.fixture
def buyer(db_session: Session) -> User:
    user = User(
        email="buyer.priya@test.com",
        password_hash="hash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919123456789",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Priya Sharma",
        business_name="Fresh Mart Retail",
        business_type="retailer",
        delivery_receiving_address="Shop 5, APMC Market Yard",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def buyer_token(buyer: User) -> str:
    return create_access_token(data={"sub": str(buyer.id)})


@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        email="other@test.com",
        password_hash="hash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919999999999",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Other User",
        business_name="Other Mart",
        business_type="retailer",
        delivery_receiving_address="Address 123",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_token(other_user: User) -> str:
    return create_access_token(data={"sub": str(other_user.id)})


@pytest.fixture
def admin_user(db_session: Session) -> User:
    admin = User(
        email="admin.orders@test.com",
        password_hash="hash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number="+919888888888",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(data={"sub": str(admin_user.id)})



@pytest.fixture
def listing(db_session: Session, farmer: User, category: ProduceCategory) -> ProduceListing:
    l = ProduceListing(
        farmer_id=farmer.id,
        category_id=category.id,
        product_name="Organic Red Onion",
        title="Fresh Red Onions",
        initial_quantity=Decimal("100.000"),
        available_quantity=Decimal("60.000"),  # 40 kg already deducted for order
        unit="kg",
        price_per_unit=Decimal("40.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_PARTIALLY_FULFILLED,
    )
    db_session.add(l)
    db_session.commit()
    db_session.refresh(l)
    return l


@pytest.fixture
def requirement(db_session: Session, buyer: User, category: ProduceCategory) -> BuyerRequirement:
    req = BuyerRequirement(
        buyer_id=buyer.id,
        category_id=category.id,
        product_name="Organic Red Onion",
        title="Procurement of Onions",
        required_quantity=Decimal("100.000"),
        remaining_quantity=Decimal("70.000"),  # 30 kg approved
        unit="kg",
        destination_city="Mumbai",
        destination_state="Maharashtra",
        required_by_date=date.today() + timedelta(days=10),
        status=REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def create_test_order(
    db: Session,
    farmer: User,
    buyer: User,
    listing: ProduceListing,
    requirement: BuyerRequirement = None,
    order_qty: Decimal = Decimal("40.000"),
    unit_price: Decimal = Decimal("40.00"),
    approval_status: str = APPROVAL_STATUS_APPROVED,
    approved_qty: Decimal = Decimal("30.000"),
) -> Tuple[Order, OrderItem, ProduceListing]:
    """Helper to instantiate an order with inventory adjustment and fulfillment approval."""
    # Reusable Conversation
    conv = db.query(Conversation).filter(
        Conversation.farmer_id == farmer.id,
        Conversation.buyer_id == buyer.id,
    ).first()
    if not conv:
        conv = Conversation(
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            initial_context_type="listing",
            initial_context_id=listing.id,
        )
        db.add(conv)
        db.flush()

    # Source offer
    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:6].upper()}",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=order_qty * unit_price,
        status=OFFER_STATUS_ACCEPTED,
    )
    db.add(offer)
    db.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        source_offer_id=offer.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=order_qty * unit_price,
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
        unit_price=unit_price,
        subtotal=order_qty * unit_price,
        status=ORDER_ITEM_STATUS_CONFIRMED,
    )
    db.add(item)
    db.flush()

    # Initial order deduction
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
    return order, item, listing


# ===========================================================================
# Batch 1 Tests: Order Listing, Details & Farmer Confirmation
# ===========================================================================

def test_list_orders_pagination_and_role_filtering(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token, other_token):
    order1, _, _ = create_test_order(db_session, farmer, buyer, listing)
    order2, _, _ = create_test_order(db_session, farmer, buyer, listing)

    # Farmer sees orders
    res_f = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {farmer_token}"})
    assert res_f.status_code == 200
    data_f = res_f.json()
    assert data_f["total"] == 2
    assert len(data_f["items"]) == 2
    assert data_f["page"] == 1
    assert data_f["items"][0]["items_count"] == 1

    # Buyer sees orders
    res_b = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {buyer_token}"})
    assert res_b.status_code == 200
    assert res_b.json()["total"] == 2

    # Unrelated user sees 0 orders
    res_o = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {other_token}"})
    assert res_o.status_code == 200
    assert res_o.json()["total"] == 0


def test_get_order_detail_and_anti_enumeration(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token, other_token):
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    # Farmer views details
    res_f = client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {farmer_token}"})
    assert res_f.status_code == 200
    data = res_f.json()
    assert data["order_number"] == order.order_number
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == listing.product_name
    assert Decimal(str(data["total_amount"])) == order.total_amount

    # Buyer views details
    res_b = client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {buyer_token}"})
    assert res_b.status_code == 200

    # Unrelated user receives 404 anti-enumeration
    res_o = client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res_o.status_code == 404


def test_confirm_order_lifecycle(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token):
    order, _, _ = create_test_order(db_session, farmer, buyer, listing)

    # Buyer cannot confirm farmer's order (403)
    res_b = client.post(f"/api/v1/orders/{order.id}/confirm", headers={"Authorization": f"Bearer {buyer_token}"})
    assert res_b.status_code == 403

    # Farmer confirms order
    res_f = client.post(f"/api/v1/orders/{order.id}/confirm", headers={"Authorization": f"Bearer {farmer_token}"})
    assert res_f.status_code == 200
    assert res_f.json()["status"] == ORDER_STATUS_CONFIRMED

    # Repeated confirmation returns 409 Conflict
    res_repeat = client.post(f"/api/v1/orders/{order.id}/confirm", headers={"Authorization": f"Bearer {farmer_token}"})
    assert res_repeat.status_code == 409


# ===========================================================================
# Batch 2 Tests: Atomic Order Cancellation
# ===========================================================================

def test_cancel_catalog_order_restores_inventory(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token):
    order, _, _ = create_test_order(db_session, farmer, buyer, listing, order_qty=Decimal("40.000"))
    assert listing.available_quantity == Decimal("60.000")

    # Farmer cancels order
    res = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"reason": "Customer requested cancellation"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == ORDER_STATUS_CANCELLED

    db_session.refresh(listing)
    # 60 + 40 = 100 kg restored
    assert listing.available_quantity == Decimal("100.000")
    assert listing.status == STATUS_ACTIVE

    # Verify inventory ledger net impact is exactly zero
    adjs = db_session.query(InventoryAdjustment).filter(InventoryAdjustment.order_id == order.id).all()
    net = sum(a.quantity_delta for a in adjs)
    assert net == Decimal("0.000")


def test_cancel_order_with_approved_requirement(client: TestClient, db_session: Session, farmer, buyer, listing, requirement, buyer_token):
    order, _, _ = create_test_order(
        db_session, farmer, buyer, listing, requirement,
        order_qty=Decimal("40.000"), approved_qty=Decimal("30.000")
    )
    assert requirement.remaining_quantity == Decimal("70.000")

    # Buyer cancels order
    res = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"reason": "Procurement cancelled"},
    )
    assert res.status_code == 200

    db_session.refresh(requirement)
    # 70 + 30 = 100 kg restored
    assert requirement.remaining_quantity == Decimal("100.000")
    assert requirement.status == REQUIREMENT_STATUS_ACTIVE


def test_cancel_order_with_closed_requirement_does_not_reopen(client: TestClient, db_session: Session, farmer, buyer, listing, requirement, buyer_token):
    requirement.status = REQUIREMENT_STATUS_CLOSED
    db_session.commit()

    order, _, _ = create_test_order(
        db_session, farmer, buyer, listing, requirement,
        order_qty=Decimal("40.000"), approved_qty=Decimal("30.000")
    )

    # Cancel order
    res = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"reason": "Cancelled"},
    )
    assert res.status_code == 200

    db_session.refresh(requirement)
    # Closed requirements are NEVER reopened and demand is NEVER restored
    assert requirement.status == REQUIREMENT_STATUS_CLOSED
    assert requirement.remaining_quantity == Decimal("70.000")


def test_cancel_order_voids_pending_approval(client: TestClient, db_session: Session, farmer, buyer, listing, requirement, farmer_token):
    order, item, _ = create_test_order(
        db_session, farmer, buyer, listing, requirement,
        approval_status=APPROVAL_STATUS_PENDING
    )

    res = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"reason": "Out of stock"},
    )
    assert res.status_code == 200

    appr = db_session.query(RequirementFulfillmentApproval).filter(RequirementFulfillmentApproval.order_item_id == item.id).first()
    assert appr.status == APPROVAL_STATUS_VOIDED
    assert appr.voided_by_user_id == farmer.id


def test_cancel_order_repeated_conflict(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token):
    order, _, _ = create_test_order(db_session, farmer, buyer, listing)

    client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"reason": "Cancelled"},
    )

    # Second cancellation must fail with 409 Conflict
    res2 = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"reason": "Cancelled again"},
    )
    assert res2.status_code == 409


# ===========================================================================
# Batch 3 Tests: Order Amendments & Cumulative Accounting
# ===========================================================================

def test_propose_and_accept_quantity_decrease(client: TestClient, db_session: Session, farmer, buyer, listing, requirement, farmer_token, buyer_token):
    order, item, _ = create_test_order(
        db_session, farmer, buyer, listing, requirement,
        order_qty=Decimal("40.000"), approved_qty=Decimal("30.000")
    )
    assert listing.available_quantity == Decimal("60.000")
    assert requirement.remaining_quantity == Decimal("70.000")

    # Farmer proposes quantity reduction from 40 to 25 kg
    res_prop = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "amendment_type": "quantity",
            "order_item_id": str(item.id),
            "new_quantity": "25.000",
            "justification": "Partial harvest yield reduction",
        },
    )
    assert res_prop.status_code == 201
    aid = res_prop.json()["id"]

    # Proposer cannot self-accept (409)
    res_self = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid}/accept",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_self.status_code == 409

    # Buyer accepts amendment
    res_acc = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid}/accept",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_acc.status_code == 200
    assert res_acc.json()["status"] == AMENDMENT_STATUS_EFFECTIVE

    db_session.refresh(listing)
    db_session.refresh(requirement)
    db_session.refresh(order)
    db_session.refresh(item)

    # 15 kg restored to listing (60 + 15 = 75 kg)
    assert listing.available_quantity == Decimal("75.000")
    # Demand consumed was 30 kg; new order is 25 kg -> demand to restore = 30 - 25 = 5 kg
    # Requirement remaining quantity becomes 70 + 5 = 75 kg
    assert requirement.remaining_quantity == Decimal("75.000")
    assert item.quantity == Decimal("25.000")
    assert order.total_amount == Decimal("25.000") * Decimal("40.00")


def test_successive_amendments_and_subsequent_cancellation(client: TestClient, db_session: Session, farmer, buyer, listing, requirement, farmer_token, buyer_token):
    """
    Scenario:
    - Approved: 30 kg, Order: 40 kg. Req remaining: 70 kg.
    - Amendment 1: 40 -> 25 kg. Restores 5 kg demand. (Req: 75 kg)
    - Amendment 2: 25 -> 15 kg. Restores 10 kg demand. (Req: 85 kg)
    - Order Cancelled: Restores remaining 15 kg demand (Req: 100 kg).
    - Guarantees total restoration = 30 kg, never double-counted!
    """
    order, item, _ = create_test_order(
        db_session, farmer, buyer, listing, requirement,
        order_qty=Decimal("40.000"), approved_qty=Decimal("30.000")
    )

    # Amendment 1: 40 -> 25
    r1 = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "amendment_type": "quantity",
            "order_item_id": str(item.id),
            "new_quantity": "25.000",
            "justification": "Step 1",
        },
    )
    aid1 = r1.json()["id"]
    client.post(f"/api/v1/orders/{order.id}/amendments/{aid1}/accept", headers={"Authorization": f"Bearer {buyer_token}"})

    db_session.refresh(requirement)
    assert requirement.remaining_quantity == Decimal("75.000")

    # Amendment 2: 25 -> 15
    r2 = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "amendment_type": "quantity",
            "order_item_id": str(item.id),
            "new_quantity": "15.000",
            "justification": "Step 2",
        },
    )
    aid2 = r2.json()["id"]
    client.post(f"/api/v1/orders/{order.id}/amendments/{aid2}/accept", headers={"Authorization": f"Bearer {buyer_token}"})

    db_session.refresh(requirement)
    assert requirement.remaining_quantity == Decimal("85.000")

    # Cancellation afterwards
    r_cancel = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"reason": "Cancellation"},
    )
    assert r_cancel.status_code == 200

    db_session.refresh(requirement)
    # Remaining requirement quantity must equal required quantity (100 kg), never overfilled!
    assert requirement.remaining_quantity == Decimal("100.000")

    # Inventory ledger must balance to 0
    adjs = db_session.query(InventoryAdjustment).filter(InventoryAdjustment.order_id == order.id).all()
    assert sum(a.quantity_delta for a in adjs) == Decimal("0.000")


def test_amendment_rejection(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token):
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    res_prop = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "amendment_type": "price",
            "order_item_id": str(item.id),
            "new_price": "30.00",
            "justification": "Market price drop",
        },
    )
    aid = res_prop.json()["id"]

    # Proposer cannot self-reject (409)
    res_self = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid}/reject",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_self.status_code == 409

    # Farmer rejects amendment
    res_rej = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid}/reject",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == AMENDMENT_STATUS_REJECTED


# ===========================================================================
# Batch 4 Tests: Delivery Coordination & Revised Acknowledgement Policy
# ===========================================================================

def test_delivery_scenario_a_farmer_marks_buyer_acknowledges(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token, other_token, admin_token):
    """Scenario A: Farmer marks delivery completed; Buyer acknowledges receipt."""
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    # 1. Arrange delivery
    tomorrow = date.today() + timedelta(days=1)
    res_arr = client.post(
        f"/api/v1/orders/{order.id}/delivery/arrange",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "delivery_method": "seller_dispatch",
            "delivery_destination_address": "Shop 5, Wholesale Market, Mumbai",
            "delivery_arranged_date": tomorrow.isoformat(),
            "delivery_notes": "Handle with care",
        },
    )
    assert res_arr.status_code == 200
    assert res_arr.json()["delivery_status"] == DELIVERY_STATUS_ARRANGED

    # 2. Farmer marks delivery completed
    res_mark = client.post(
        f"/api/v1/orders/{order.id}/delivery/mark-completed",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_mark.status_code == 200
    data_mark = res_mark.json()
    assert data_mark["delivery_status"] == DELIVERY_STATUS_COMPLETION_MARKED
    assert data_mark["delivery_acknowledgements_pending"] == ["buyer"]

    # 3. Farmer attempts self-acknowledgement (403 Forbidden)
    res_self_ack = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_self_ack.status_code == 403
    assert "party who marked delivery completion" in res_self_ack.json()["detail"]

    # 4. Unrelated user attempts acknowledgement (404 Not Found)
    res_other = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res_other.status_code == 404

    # 5. Admin attempts to acknowledge on behalf of buyer (403 Forbidden)
    res_admin = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 403

    # 6. Buyer acknowledges receipt, completing order
    res_ack = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"notes": "All 40 kg onions verified in good shape"},
    )
    assert res_ack.status_code == 200
    data_done = res_ack.json()
    assert data_done["status"] == ORDER_STATUS_COMPLETED
    assert data_done["delivery_status"] == DELIVERY_STATUS_COMPLETED
    assert data_done["completed_at"] is not None
    assert data_done["items"][0]["status"] == ORDER_ITEM_STATUS_FULFILLED
    assert data_done["delivery_acknowledgements_pending"] == []
    assert len(data_done["delivery_acknowledgements"]) == 1
    assert data_done["delivery_acknowledgements"][0]["user_id"] == str(buyer.id)
    assert data_done["delivery_acknowledgements"][0]["notes"] == "All 40 kg onions verified in good shape"

    # 7. Buyer attempts duplicate acknowledgement (409 Conflict)
    res_dup = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_dup.status_code == 409


def test_delivery_scenario_b_buyer_marks_farmer_acknowledges(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token):
    """Scenario B: Buyer marks delivery completed (e.g. self-pickup); Farmer acknowledges receipt."""
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    # 1. Arrange delivery (buyer pickup)
    tomorrow = date.today() + timedelta(days=1)
    res_arr = client.post(
        f"/api/v1/orders/{order.id}/delivery/arrange",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "delivery_method": "buyer_pickup",
            "delivery_destination_address": "Farm Gate, Nashik",
            "delivery_arranged_date": tomorrow.isoformat(),
        },
    )
    assert res_arr.status_code == 200

    # 2. Buyer marks completion
    res_mark = client.post(
        f"/api/v1/orders/{order.id}/delivery/mark-completed",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_mark.status_code == 200
    data_mark = res_mark.json()
    assert data_mark["delivery_status"] == DELIVERY_STATUS_COMPLETION_MARKED
    assert data_mark["delivery_acknowledgements_pending"] == ["farmer"]

    # 3. Buyer attempts self-acknowledgement (403 Forbidden)
    res_self = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_self.status_code == 403

    # 4. Farmer acknowledges, completing transaction
    res_ack = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"notes": "Buyer picked up produce at farm gate"},
    )
    assert res_ack.status_code == 200
    data_done = res_ack.json()
    assert data_done["status"] == ORDER_STATUS_COMPLETED
    assert data_done["delivery_status"] == DELIVERY_STATUS_COMPLETED
    assert data_done["delivery_acknowledgements_pending"] == []
    assert len(data_done["delivery_acknowledgements"]) == 1
    assert data_done["delivery_acknowledgements"][0]["user_id"] == str(farmer.id)


def test_delivery_scenario_c_admin_marks_both_acknowledge_farmer_first(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token, admin_token):
    """Scenario C: Admin marks delivery completed; Requires both farmer and buyer to independently acknowledge (Farmer first)."""
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    # 1. Arrange delivery
    tomorrow = date.today() + timedelta(days=1)
    client.post(
        f"/api/v1/orders/{order.id}/delivery/arrange",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "delivery_method": "third_party",
            "delivery_destination_address": "Cold Storage, Pune",
            "delivery_arranged_date": tomorrow.isoformat(),
        },
    )

    # 2. Admin marks delivery completed
    res_admin_mark = client.post(
        f"/api/v1/orders/{order.id}/delivery/mark-completed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_mark.status_code == 200
    data_mark = res_admin_mark.json()
    assert data_mark["delivery_status"] == DELIVERY_STATUS_COMPLETION_MARKED
    assert set(data_mark["delivery_acknowledgements_pending"]) == {"farmer", "buyer"}

    # 3. Admin attempts self-acknowledgement (403 Forbidden)
    res_admin_self = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_self.status_code == 403

    # 4. Farmer acknowledges receipt (1 of 2)
    res_ack_farmer = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"notes": "Farmer acknowledges dispatch confirmed"},
    )
    assert res_ack_farmer.status_code == 200
    data_p1 = res_ack_farmer.json()
    # Order remains delivery_arranged / completion_marked because buyer has not yet acknowledged!
    assert data_p1["status"] == ORDER_STATUS_DELIVERY_ARRANGED
    assert data_p1["delivery_status"] == DELIVERY_STATUS_COMPLETION_MARKED
    assert data_p1["completed_at"] is None
    assert data_p1["delivery_acknowledgements_pending"] == ["buyer"]
    assert len(data_p1["delivery_acknowledgements"]) == 1

    # 5. Farmer attempts duplicate acknowledgement (409 Conflict)
    res_farmer_dup = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_farmer_dup.status_code == 409

    # 6. Buyer acknowledges receipt (2 of 2) -> Now order completes!
    res_ack_buyer = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"notes": "Buyer acknowledges goods received in Pune"},
    )
    assert res_ack_buyer.status_code == 200
    data_p2 = res_ack_buyer.json()
    assert data_p2["status"] == ORDER_STATUS_COMPLETED
    assert data_p2["delivery_status"] == DELIVERY_STATUS_COMPLETED
    assert data_p2["completed_at"] is not None
    assert data_p2["delivery_acknowledgements_pending"] == []
    assert len(data_p2["delivery_acknowledgements"]) == 2
    ack_user_ids = {a["user_id"] for a in data_p2["delivery_acknowledgements"]}
    assert ack_user_ids == {str(farmer.id), str(buyer.id)}


def test_delivery_scenario_c_admin_marks_both_acknowledge_buyer_first(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token, admin_token):
    """Scenario C reverse order: Admin marks delivery completed; Buyer acknowledges first, then Farmer."""
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    tomorrow = date.today() + timedelta(days=1)
    client.post(
        f"/api/v1/orders/{order.id}/delivery/arrange",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "delivery_method": "third_party",
            "delivery_destination_address": "Retail Store, Thane",
            "delivery_arranged_date": tomorrow.isoformat(),
        },
    )
    client.post(
        f"/api/v1/orders/{order.id}/delivery/mark-completed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 1. Buyer acknowledges first (1 of 2)
    res_b = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["status"] == ORDER_STATUS_DELIVERY_ARRANGED
    assert data_b["delivery_status"] == DELIVERY_STATUS_COMPLETION_MARKED
    assert data_b["delivery_acknowledgements_pending"] == ["farmer"]
    assert len(data_b["delivery_acknowledgements"]) == 1

    # 2. Farmer acknowledges second (2 of 2) -> Order completed
    res_f = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_f.status_code == 200
    data_f = res_f.json()
    assert data_f["status"] == ORDER_STATUS_COMPLETED
    assert data_f["delivery_status"] == DELIVERY_STATUS_COMPLETED
    assert data_f["completed_at"] is not None
    assert data_f["delivery_acknowledgements_pending"] == []
    assert len(data_f["delivery_acknowledgements"]) == 2



# ===========================================================================
# Batch 5 Tests: Inventory Audit Endpoints
# ===========================================================================

def test_inventory_audit_endpoints(client: TestClient, db_session: Session, farmer, buyer, other_user, listing, farmer_token, buyer_token, other_token):
    order, _, _ = create_test_order(db_session, farmer, buyer, listing)

    # Order inventory history
    res_o = client.get(
        f"/api/v1/orders/{order.id}/inventory-adjustments",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_o.status_code == 200
    data_o = res_o.json()
    assert data_o["total"] == 1
    assert data_o["items"][0]["change_type"] == CHANGE_TYPE_ORDER_FULFILLMENT

    # Unrelated user cannot view order ledger (404)
    res_unauth = client.get(
        f"/api/v1/orders/{order.id}/inventory-adjustments",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res_unauth.status_code == 404

    # Listing inventory history: owner farmer sees history
    res_l = client.get(
        f"/api/v1/listings/{listing.id}/inventory-adjustments",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_l.status_code == 200
    assert res_l.json()["total"] == 1

    # Unrelated farmer/buyer receives 403 Forbidden
    res_l_unauth = client.get(
        f"/api/v1/listings/{listing.id}/inventory-adjustments",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res_l_unauth.status_code == 403


# ===========================================================================
# Edge Cases and Invariant Tests
# ===========================================================================

def test_cancel_order_disputed_rejected(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token):
    order, _, _ = create_test_order(db_session, farmer, buyer, listing)
    order.status = "disputed"
    db_session.commit()

    res = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"reason": "Cannot cancel"},
    )
    assert res.status_code == 409


def test_cancel_order_with_fulfilled_line_item_rejected(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token):
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)
    item.status = ORDER_ITEM_STATUS_FULFILLED
    db_session.commit()

    res = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"reason": "Cannot cancel partially fulfilled items"},
    )
    assert res.status_code == 409


def test_amendment_price_and_terms_lifecycle(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token):
    order, item, _ = create_test_order(db_session, farmer, buyer, listing, order_qty=Decimal("10.000"), unit_price=Decimal("50.00"))
    assert order.total_amount == Decimal("500.00")

    # Propose price increase from 50 to 60
    res_p = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "amendment_type": "price",
            "order_item_id": str(item.id),
            "new_price": "60.00",
            "justification": "Fuel surcharge adjustment",
        },
    )
    assert res_p.status_code == 201
    aid_p = res_p.json()["id"]

    # Buyer accepts price amendment
    res_a = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid_p}/accept",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_a.status_code == 200

    db_session.refresh(order)
    db_session.refresh(item)
    assert item.unit_price == Decimal("60.00")
    assert item.subtotal == Decimal("600.00")
    assert order.total_amount == Decimal("600.00")

    # Propose terms amendment
    res_t = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "amendment_type": "terms",
            "new_terms": "Deliver between 9 AM and 11 AM",
            "justification": "Loading dock availability",
        },
    )
    assert res_t.status_code == 201
    aid_t = res_t.json()["id"]

    # Farmer accepts terms
    res_ta = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid_t}/accept",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_ta.status_code == 200
    db_session.refresh(order)
    assert order.delivery_notes == "Deliver between 9 AM and 11 AM"


def test_amendment_quantity_increase_insufficient_stock(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token):
    # Listing initial: 100 kg, available: 60 kg
    order, item, _ = create_test_order(db_session, farmer, buyer, listing, order_qty=Decimal("40.000"))
    assert listing.available_quantity == Decimal("60.000")

    # Propose quantity increase from 40 to 110 kg (needs +70 kg, but available is only 60 kg)
    res_p = client.post(
        f"/api/v1/orders/{order.id}/amendments",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "amendment_type": "quantity",
            "order_item_id": str(item.id),
            "new_quantity": "110.000",
            "justification": "Scale up requirement",
        },
    )
    assert res_p.status_code == 201
    aid = res_p.json()["id"]

    # Farmer tries to accept but stock is insufficient -> 409 Conflict
    res_a = client.post(
        f"/api/v1/orders/{order.id}/amendments/{aid}/accept",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_a.status_code == 409


def test_delivery_invalid_state_transitions(client: TestClient, db_session: Session, farmer, buyer, listing, farmer_token, buyer_token):
    order, item, _ = create_test_order(db_session, farmer, buyer, listing)

    # Cannot mark completed before delivery is arranged (409)
    res_mark = client.post(
        f"/api/v1/orders/{order.id}/delivery/mark-completed",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_mark.status_code == 409

    # Cannot acknowledge before completion is marked (409)
    res_ack = client.post(
        f"/api/v1/orders/{order.id}/delivery/acknowledge",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_ack.status_code == 409

