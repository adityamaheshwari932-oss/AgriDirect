"""Integration and unit tests for the Connected Transportation Marketplace & Connection Requests.

Tests:
1. Verified transporter discovery (unverified excluded)
2. Connection request lifecycle (Farmer/Buyer -> Transporter)
3. Duplicate connection prevention (409)
4. Unverified user/transporter restrictions (403/400)
5. Deal/Order association and participant permissions
6. Accept, Decline, and Cancel workflows
7. Automatic order assignment coordination on acceptance
8. Notifications generated for participants
"""

from datetime import date, datetime
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.notification import Notification
from app.models.offer import Offer, OfferItem
from app.models.order import Order, OrderItem
from app.models.transporter_connection import TransportConnectionRequest
from app.models.user import BuyerProfile, FarmerProfile, ServiceArea, TransporterProfile, User


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
def client(db_session):
    """Test client with db override."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def users_fixture(db_session: Session):
    """Sets up farmer, buyer, verified transporter, unverified transporter, and unverified farmer."""
    pwd = hash_password("Password123!")

    # 1. Verified Farmer
    farmer = User(
        email="farmer.rajesh@example.com",
        password_hash=pwd,
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(farmer)
    db_session.flush()

    farmer_prof = FarmerProfile(
        user_id=farmer.id,
        full_name="Rajesh Patil",
        farm_name="Patil Organic Farms",
        farm_location_address="Farm Road 12",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db_session.add(farmer_prof)

    # 2. Verified Buyer
    buyer = User(
        email="buyer.amit@example.com",
        password_hash=pwd,
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(buyer)
    db_session.flush()

    buyer_prof = BuyerProfile(
        user_id=buyer.id,
        business_name="Metro Fresh Mart",
        contact_person_name="Amit Shah",
        business_type="retailer",
        delivery_receiving_address="Central Cold Storage, Vashi",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400703",
    )
    db_session.add(buyer_prof)

    # 3. Verified Transporter
    transporter_v = User(
        email="transporter.verified@example.com",
        password_hash=pwd,
        role="transporter",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(transporter_v)
    db_session.flush()

    tp_v = TransporterProfile(
        user_id=transporter_v.id,
        business_name="Sahyadri Express Logistics",
        contact_name="Sanjay Shinde",
        phone_number="9876543212",
        transport_type="refrigerated",
        vehicle_capacity_kg=Decimal("8000.00"),
        vehicle_registration_number="MH-15-TC-1234",
        is_available=True,
        experience_years=8,
        operating_states="Maharashtra, Gujarat",
    )
    db_session.add(tp_v)
    db_session.flush()

    sa1 = ServiceArea(
        transporter_profile_id=tp_v.id,
        state="Maharashtra",
        district="Nashik",
        coverage_type="both",
        is_active=True,
    )
    sa2 = ServiceArea(
        transporter_profile_id=tp_v.id,
        state="Maharashtra",
        district="Mumbai",
        coverage_type="both",
        is_active=True,
    )
    db_session.add_all([sa1, sa2])

    # 4. Unverified Transporter
    transporter_unv = User(
        email="transporter.unv@example.com",
        password_hash=pwd,
        role="transporter",
        verification_status="unverified",
        account_status="active",
    )
    db_session.add(transporter_unv)
    db_session.flush()

    tp_unv = TransporterProfile(
        user_id=transporter_unv.id,
        business_name="Unverified Haulers",
        contact_name="Ramesh",
        phone_number="9876543213",
        transport_type="mini_truck",
        vehicle_capacity_kg=Decimal("2000.00"),
        vehicle_registration_number="MH-12-UV-9999",
        is_available=True,
        experience_years=1,
    )
    db_session.add(tp_unv)

    # 5. Unverified Farmer
    farmer_unv = User(
        email="farmer.unv@example.com",
        password_hash=pwd,
        role="farmer",
        verification_status="unverified",
        account_status="active",
    )
    db_session.add(farmer_unv)

    db_session.commit()

    return {
        "farmer": farmer,
        "buyer": buyer,
        "transporter_v": transporter_v,
        "transporter_unv": transporter_unv,
        "farmer_unv": farmer_unv,
        "tp_v": tp_v,
    }


def get_auth_headers(user: User) -> dict:
    """Generate bearer auth header for a test user."""
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "status": user.account_status}
    )
    return {"Authorization": f"Bearer {token}"}


def test_discover_transporters_returns_only_verified(client, users_fixture):
    """Verify that unverified transporters are strictly excluded from search results."""
    res = client.get("/api/v1/transporters/discover")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["business_name"] == "Sahyadri Express Logistics"
    assert data["items"][0]["verification_status"] == "verified"


def test_farmer_create_connection_request_success(client, users_fixture):
    """Verified farmer creates connection request to verified transporter."""
    farmer = users_fixture["farmer"]
    transporter = users_fixture["transporter_v"]

    payload = {
        "transporter_user_id": str(transporter.id),
        "pickup_state": "Maharashtra",
        "pickup_district": "Nashik",
        "pickup_address": "Farm Gate #4, Dindori",
        "delivery_state": "Maharashtra",
        "delivery_district": "Mumbai",
        "delivery_address": "Vashi APMC Market, Yard 2",
        "cargo_description": "4000 kg Fresh Pomegranate",
        "weight_kg": 4000,
        "required_delivery_date": "2026-12-01",
        "notes": "Need refrigerated container maintained at 6C.",
    }

    res = client.post(
        "/api/v1/transporters/connection-requests",
        json=payload,
        headers=get_auth_headers(farmer),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending"
    assert data["transporter_business_name"] == "Sahyadri Express Logistics"
    assert data["requester_role"] == "farmer"
    assert data["weight_kg"] == "4000.00"
    assert data["required_delivery_date"] == "2026-12-01"


def test_unverified_farmer_cannot_create_connection_request(client, users_fixture):
    """Unverified users are blocked with 403."""
    farmer_unv = users_fixture["farmer_unv"]
    transporter = users_fixture["transporter_v"]

    payload = {
        "transporter_user_id": str(transporter.id),
        "cargo_description": "Grapes 1000 kg",
    }
    res = client.post(
        "/api/v1/transporters/connection-requests",
        json=payload,
        headers=get_auth_headers(farmer_unv),
    )
    assert res.status_code == 403
    assert "verified account" in res.json()["detail"].lower()


def test_cannot_request_unverified_transporter(client, users_fixture):
    """Cannot request transportation from an unverified hauler."""
    farmer = users_fixture["farmer"]
    transporter_unv = users_fixture["transporter_unv"]

    payload = {
        "transporter_user_id": str(transporter_unv.id),
        "cargo_description": "Tomatoes 500 kg",
    }
    res = client.post(
        "/api/v1/transporters/connection-requests",
        json=payload,
        headers=get_auth_headers(farmer),
    )
    assert res.status_code == 400
    assert "unverified provider" in res.json()["detail"].lower()


def test_duplicate_pending_connection_request_rejected(client, users_fixture):
    """Duplicate pending request for the same deal yields 409 Conflict."""
    farmer = users_fixture["farmer"]
    transporter = users_fixture["transporter_v"]

    payload = {
        "transporter_user_id": str(transporter.id),
        "cargo_description": "Grapes 2000 kg",
    }
    res1 = client.post(
        "/api/v1/transporters/connection-requests",
        json=payload,
        headers=get_auth_headers(farmer),
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/transporters/connection-requests",
        json=payload,
        headers=get_auth_headers(farmer),
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_connection_request_associated_with_order(client, db_session, users_fixture):
    """Connection request linked with an order auto-populates and validates participants."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    conv = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    db_session.add(conv)
    db_session.flush()

    offer = Offer(
        offer_number="OFF-TEST-001",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=Decimal("150000.00"),
        status="accepted",
    )
    db_session.add(offer)
    db_session.flush()

    order = Order(
        order_number="ORD-TEST-999",
        source_offer_id=offer.id,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("150000.00"),
        status="confirmed",
        transport_status="none",
        delivery_destination_address="Mumbai Central Cold Storage, Dock 5",
        delivery_arranged_date=date(2026, 12, 5),
    )
    db_session.add(order)
    db_session.commit()

    # Buyer requests transport for this order
    payload = {
        "transporter_user_id": str(transporter.id),
        "order_id": str(order.id),
        "notes": "Urgent morning delivery required",
    }
    res = client.post(
        "/api/v1/transporters/connection-requests",
        json=payload,
        headers=get_auth_headers(buyer),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["order_id"] == str(order.id)
    assert data["order_number"] == "ORD-TEST-999"
    assert data["delivery_address"] == "Mumbai Central Cold Storage, Dock 5"
    assert data["required_delivery_date"] == "2026-12-05"


def test_transporter_accepts_connection_request_assigns_order(client, db_session, users_fixture):
    """When a transporter accepts a request for an order, order is NOT assigned until counterparty approves."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    conv = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    db_session.add(conv)
    db_session.flush()

    offer = Offer(
        offer_number="OFF-TEST-002",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=Decimal("50000.00"),
        status="accepted",
    )
    db_session.add(offer)
    db_session.flush()

    order = Order(
        order_number="ORD-TEST-888",
        source_offer_id=offer.id,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("50000.00"),
        status="confirmed",
        transport_status="none",
    )
    db_session.add(order)
    db_session.commit()

    # 1. Farmer initiates request
    req_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order.id),
            "cargo_description": "Onions 3000 kg",
        },
        headers=get_auth_headers(farmer),
    )
    req_id = req_res.json()["id"]

    # 2. Transporter accepts -> Status becomes transporter_accepted
    accept_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/accept",
        json={"response_notes": "Accepted. Pickup confirmed for 8 AM."},
        headers=get_auth_headers(transporter),
    )
    assert accept_res.status_code == 200
    data = accept_res.json()
    assert data["status"] == "transporter_accepted"
    assert data["response_notes"] == "Accepted. Pickup confirmed for 8 AM."
    assert data["transporter_accepted_at"] is not None

    # Order is NOT assigned yet (bilateral safety guarantee)
    db_session.refresh(order)
    assert order.transporter_id is None
    assert order.transport_status == "none"

    # 3. Deal counterparty (buyer) approves the assignment
    approve_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/approve",
        json={"approval_notes": "Counterparty logistics approval granted."},
        headers=get_auth_headers(buyer),
    )
    assert approve_res.status_code == 200
    appr_data = approve_res.json()
    assert appr_data["status"] == "counterparty_approved"
    assert appr_data["counterparty_approved_by_id"] == str(buyer.id)
    assert appr_data["counterparty_approved_at"] is not None

    # 4. Verify order is now atomically assigned
    db_session.refresh(order)
    assert order.transporter_id == transporter.id
    assert order.transport_status == "assigned"
    assert "Bilaterally approved" in order.delivery_notes

    # 5. Verify notifications sent
    notifs = db_session.query(Notification).filter(Notification.user_id == farmer.id).all()
    assert len(notifs) >= 1
    assert any("approved" in n.title.lower() or "accepted" in n.title.lower() for n in notifs)


def test_initiator_cannot_approve_own_request_and_rejection_workflow(client, db_session, users_fixture):
    """Requester and transporter cannot approve assignment; only deal counterparty can reject or approve."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    conv = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    db_session.add(conv)
    db_session.flush()

    order = Order(
        order_number="ORD-TEST-777",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("80000.00"),
        status="confirmed",
        transport_status="none",
    )
    db_session.add(order)
    db_session.commit()

    # 1. Farmer initiates request
    req_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order.id),
            "cargo_description": "Apples 2000 kg",
        },
        headers=get_auth_headers(farmer),
    )
    req_id = req_res.json()["id"]

    # 2. Transporter accepts
    client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/accept",
        json={"response_notes": "Ready to dispatch."},
        headers=get_auth_headers(transporter),
    )

    # 3. Farmer (initiator) tries to approve -> 403 Forbidden
    f_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/approve",
        headers=get_auth_headers(farmer),
    )
    assert f_res.status_code == 403
    assert "cannot approve on behalf of the deal counterparty" in f_res.json()["detail"].lower()

    # 4. Transporter tries to approve own assignment -> 403 Forbidden
    t_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/approve",
        headers=get_auth_headers(transporter),
    )
    assert t_res.status_code == 403
    assert "transporter cannot approve" in t_res.json()["detail"].lower()

    # 5. Counterparty (buyer) rejects the assignment
    rej_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/reject",
        json={"counterparty_rejection_reason": "Rate too high; preferred local carrier."},
        headers=get_auth_headers(buyer),
    )
    assert rej_res.status_code == 200
    rej_data = rej_res.json()
    assert rej_data["status"] == "counterparty_rejected"
    assert rej_data["counterparty_rejection_reason"] == "Rate too high; preferred local carrier."
    assert rej_data["counterparty_rejected_by_id"] == str(buyer.id)

    # Order remains unassigned
    db_session.refresh(order)
    assert order.transporter_id is None
    assert order.transport_status == "none"


def test_transporter_profile_and_detail_read_includes_user_id(client, users_fixture):
    """Verify TransporterProfileRead and TransporterDetailRead contracts include user_id."""
    transporter = users_fixture["transporter_v"]
    tp = users_fixture["tp_v"]

    # 1. Search discovery includes user_id
    disc_res = client.get("/api/v1/transporters/discover")
    assert disc_res.status_code == 200
    disc_items = disc_res.json()["items"]
    assert len(disc_items) >= 1
    assert disc_items[0]["user_id"] == str(transporter.id)

    # 2. Detail by profile ID includes user_id
    det_res = client.get(f"/api/v1/transporters/{tp.id}")
    assert det_res.status_code == 200
    det_data = det_res.json()
    assert det_data["user_id"] == str(transporter.id)

    # 3. Profile /me includes user_id
    me_res = client.get("/api/v1/transporters/me", headers=get_auth_headers(transporter))
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user_id"] == str(transporter.id)


def test_cargo_description_validation_length(client, users_fixture):
    """Verify cargo description accepts up to 500 characters and rejects beyond 500 characters."""
    farmer = users_fixture["farmer"]
    transporter = users_fixture["transporter_v"]

    # 490 characters succeeds
    long_desc = "Produce Item: " + ("A" * 450)
    res_ok = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "cargo_description": long_desc,
        },
        headers=get_auth_headers(farmer),
    )
    assert res_ok.status_code == 201

    # 501 characters fails 422
    too_long_desc = "B" * 501
    res_fail = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "cargo_description": too_long_desc,
        },
        headers=get_auth_headers(farmer),
    )
    assert res_fail.status_code == 422


def test_transporter_declines_connection_request(client, users_fixture):
    """Transporter declines pending request with reason."""
    farmer = users_fixture["farmer"]
    transporter = users_fixture["transporter_v"]

    req_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "cargo_description": "Apples 5000 kg",
        },
        headers=get_auth_headers(farmer),
    )
    req_id = req_res.json()["id"]

    decline_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/decline",
        json={
            "rejection_reason": "No vehicles available in Nashik on this date",
            "response_notes": "Please contact us next week",
        },
        headers=get_auth_headers(transporter),
    )
    assert decline_res.status_code == 200
    data = decline_res.json()
    assert data["status"] == "declined"
    assert data["rejection_reason"] == "No vehicles available in Nashik on this date"


def test_requester_cancels_pending_request(client, users_fixture):
    """Requester cancels their own pending connection request."""
    farmer = users_fixture["farmer"]
    transporter = users_fixture["transporter_v"]

    req_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "cargo_description": "Potatoes 2000 kg",
        },
        headers=get_auth_headers(farmer),
    )
    req_id = req_res.json()["id"]

    cancel_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/cancel",
        headers=get_auth_headers(farmer),
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


def test_transporter_list_incoming_connection_requests(client, users_fixture):
    """Transporter lists incoming connection requests."""
    farmer = users_fixture["farmer"]
    transporter = users_fixture["transporter_v"]

    # Farmer requests transport
    client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "cargo_description": "Cabbage 1500 kg",
        },
        headers=get_auth_headers(farmer),
    )

    # Transporter lists
    res = client.get(
        "/api/v1/transporters/connection-requests",
        headers=get_auth_headers(transporter),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["items"][0]["cargo_description"] == "Cabbage 1500 kg"
    assert data["items"][0]["requester_role"] == "farmer"
