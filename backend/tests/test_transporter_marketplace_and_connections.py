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

import threading
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.notification import Notification
from app.models.offer import Offer
from app.models.order import Order
from app.models.transporter_connection import TransportConnectionRequest
from app.models.user import BuyerProfile, FarmerProfile, ServiceArea, TransporterProfile, User
from app.orders.schemas import OrderCancelRequest
from app.orders.service import OrderService
from app.transporters.repository import TransporterRepository
from app.transporters.schemas import TransportConnectionApprovalResponse
from app.transporters.service import TransporterService


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


# ===========================================================================
# Stage 2 & Stage 3 Remediation Tests:
# Bypass Removal, Row Locking, Concurrency Races, and Transaction Atomicity
# ===========================================================================


def _create_second_verified_transporter(db_session: Session) -> User:
    """Helper creating a second verified transporter user and profile."""
    pwd = hash_password("Password123!")
    t2 = User(
        email=f"transporter2.{uuid.uuid4().hex[:6]}@example.com",
        password_hash=pwd,
        role="transporter",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(t2)
    db_session.flush()
    tp2 = TransporterProfile(
        user_id=t2.id,
        business_name="Deccan Cargo Movers",
        contact_name="Vikram More",
        phone_number="9876500001",
        transport_type="covered_truck",
        vehicle_capacity_kg=Decimal("6000.00"),
        vehicle_registration_number=f"MH-12-{uuid.uuid4().hex[:4].upper()}",
        is_available=True,
        experience_years=5,
        operating_states="Maharashtra",
    )
    db_session.add(tp2)
    db_session.commit()
    return t2


def test_legacy_unilateral_transport_assignment_blocked_for_all_roles(
    client, db_session, users_fixture
):
    """Buyer, farmer, and admin cannot bypass bilateral approval via transport-coordination."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    admin = User(
        email="admin.transport@example.com",
        password_hash=hash_password("Password123!"),
        role="admin",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(admin)
    order = Order(
        order_number="ORD-NO-BYPASS-001",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("25000.00"),
        status="confirmed",
        transport_status="none",
    )
    db_session.add(order)
    db_session.commit()

    for actor in (buyer, farmer, admin):
        res = client.post(
            f"/api/v1/orders/{order.id}/transport-coordination",
            json={"transporter_user_id": str(transporter.id)},
            headers=get_auth_headers(actor),
        )
        assert res.status_code == 400
        assert "bilateral" in res.json()["detail"].lower()

    # Setting active transport statuses before assignment is also rejected
    for status_value in ("assigned", "in_transit", "delivered"):
        res_status = client.post(
            f"/api/v1/orders/{order.id}/transport-coordination",
            json={"transport_status": status_value},
            headers=get_auth_headers(buyer),
        )
        assert res_status.status_code == 400

    # Delivery note coordination without transporter assignment still works cleanly
    res_note = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"delivery_notes": "Buyer loading dock open 6 AM - 2 PM"},
        headers=get_auth_headers(buyer),
    )
    assert res_note.status_code == 200
    assert res_note.json()["transporter_id"] is None
    assert res_note.json()["transport_status"] == "none"

    db_session.refresh(order)
    assert order.transporter_id is None
    assert order.transport_status == "none"


def test_lock_queries_compile_postgresql_for_update_without_outer_join(db_session):
    """Row-locking statements compile to valid PostgreSQL FOR UPDATE without outer joins."""
    from sqlalchemy import select

    stmt_req = (
        select(TransportConnectionRequest)
        .where(TransportConnectionRequest.id == uuid.uuid4())
        .with_for_update(of=TransportConnectionRequest)
    )
    sql_req = str(stmt_req.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql_req
    assert "LEFT OUTER JOIN" not in sql_req

    stmt_order = select(Order).where(Order.id == uuid.uuid4()).with_for_update(of=Order)
    sql_order = str(stmt_order.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql_order
    assert "LEFT OUTER JOIN" not in sql_order


def test_notification_failure_rolls_back_assignment_atomically(
    client, db_session, users_fixture
):
    """If notification persistence fails during approval, request and order changes roll back."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    order = Order(
        order_number="ORD-ATOMIC-001",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("42000.00"),
        status="confirmed",
        transport_status="none",
    )
    db_session.add(order)
    db_session.commit()

    service = TransporterService(TransporterRepository(db_session))
    req_read = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order.id),
            "cargo_description": "Wheat 1500 kg",
        },
        headers=get_auth_headers(farmer),
    ).json()
    req_id = uuid.UUID(req_read["id"])

    client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/accept",
        json={"response_notes": "Accepted"},
        headers=get_auth_headers(transporter),
    )

    before_notif_count = (
        db_session.query(Notification)
        .filter(
            Notification.reference_id == req_id,
            Notification.event_type == "transport_assignment_approved",
        )
        .count()
    )
    assert before_notif_count == 0

    call_count = 0
    orig_add_notif = TransporterRepository.add_notification

    def failing_on_second_notification(self_repo, notification):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Simulated notification write failure")
        return orig_add_notif(self_repo, notification)

    with (
        patch.object(TransporterRepository, "add_notification", failing_on_second_notification),
        pytest.raises(RuntimeError, match="Simulated notification write failure"),
    ):
        service.approve_assignment(
            buyer,
            req_id,
            TransportConnectionApprovalResponse(approval_notes="Should roll back"),
        )

    db_session.expire_all()
    refreshed_req = db_session.get(TransportConnectionRequest, req_id)
    refreshed_order = db_session.get(Order, order.id)
    assert refreshed_req.status == "transporter_accepted"
    assert refreshed_req.counterparty_approved_by_id is None
    assert refreshed_order.transporter_id is None
    assert refreshed_order.transport_status == "none"

    after_notif_count = (
        db_session.query(Notification)
        .filter(
            Notification.reference_id == req_id,
            Notification.event_type == "transport_assignment_approved",
        )
        .count()
    )
    assert after_notif_count == 0


def test_concurrent_same_request_double_approval_race(tmp_path):
    """Concurrent approvals on the same request allow exactly one winner without double notifications."""
    db_file = tmp_path / "same_req_race.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as seed:
        pwd = hash_password("Password123!")
        farmer = User(email="f1@ex.com", password_hash=pwd, role="farmer", verification_status="verified", account_status="active")
        buyer = User(email="b1@ex.com", password_hash=pwd, role="buyer", verification_status="verified", account_status="active")
        t1 = User(email="t1@ex.com", password_hash=pwd, role="transporter", verification_status="verified", account_status="active")
        seed.add_all([farmer, buyer, t1])
        seed.flush()
        seed.add(
            TransporterProfile(
                user_id=t1.id,
                business_name="Race Transit",
                contact_name="Raj",
                phone_number="9999900001",
                transport_type="mini_truck",
                vehicle_capacity_kg=Decimal("3000.00"),
                vehicle_registration_number="MH-01-AB-1111",
            )
        )
        order = Order(order_number="ORD-RACE-1", farmer_id=farmer.id, buyer_id=buyer.id, total_amount=Decimal("10000.00"), status="confirmed", transport_status="none")
        seed.add(order)
        seed.flush()
        req = TransportConnectionRequest(
            requester_id=farmer.id,
            transporter_id=t1.id,
            order_id=order.id,
            status="transporter_accepted",
        )
        seed.add(req)
        seed.commit()
        buyer_id, req_id, order_id, t1_id = buyer.id, req.id, order.id, t1.id

    barrier = threading.Barrier(2)
    results = []

    def worker():
        with SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = TransporterService(TransporterRepository(sess))
                barrier.wait()
                svc.approve_assignment(user_obj, req_id)
                results.append(("ok", 200))
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                status_code = getattr(exc, "status_code", 500)
                results.append(("err", status_code))

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(1 for kind, _ in results if kind == "ok") == 1
    assert sum(1 for kind, code in results if kind == "err" and code == 400) == 1

    with SessionLocal() as check:
        final_order = check.get(Order, order_id)
        final_req = check.get(TransportConnectionRequest, req_id)
        notif_count = check.query(Notification).filter(Notification.reference_id == req_id).count()
        assert final_order.transporter_id == t1_id
        assert final_order.transport_status == "assigned"
        assert final_req.status == "counterparty_approved"
        assert notif_count == 3

    engine.dispose()


def test_competing_transporters_concurrent_approval_prevents_overwrite(tmp_path):
    """Concurrent approvals for two competing transporters on one order assign only one (loser gets 409)."""
    db_file = tmp_path / "competing_race.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as seed:
        pwd = hash_password("Password123!")
        farmer = User(email="f2@ex.com", password_hash=pwd, role="farmer", verification_status="verified", account_status="active")
        buyer = User(email="b2@ex.com", password_hash=pwd, role="buyer", verification_status="verified", account_status="active")
        t1 = User(email="t1c@ex.com", password_hash=pwd, role="transporter", verification_status="verified", account_status="active")
        t2 = User(email="t2c@ex.com", password_hash=pwd, role="transporter", verification_status="verified", account_status="active")
        seed.add_all([farmer, buyer, t1, t2])
        seed.flush()
        seed.add_all([
            TransporterProfile(user_id=t1.id, business_name="Carrier One", contact_name="A", phone_number="9999900011", transport_type="mini_truck", vehicle_capacity_kg=Decimal("3000.00"), vehicle_registration_number="MH-01-C1-0001"),
            TransporterProfile(user_id=t2.id, business_name="Carrier Two", contact_name="B", phone_number="9999900012", transport_type="covered_truck", vehicle_capacity_kg=Decimal("5000.00"), vehicle_registration_number="MH-01-C2-0002"),
        ])
        order = Order(order_number="ORD-COMPETE-1", farmer_id=farmer.id, buyer_id=buyer.id, total_amount=Decimal("20000.00"), status="confirmed", transport_status="none")
        seed.add(order)
        seed.flush()
        req1 = TransportConnectionRequest(requester_id=farmer.id, transporter_id=t1.id, order_id=order.id, status="transporter_accepted")
        req2 = TransportConnectionRequest(requester_id=farmer.id, transporter_id=t2.id, order_id=order.id, status="transporter_accepted")
        seed.add_all([req1, req2])
        seed.commit()
        buyer_id, req1_id, req2_id, order_id, t1_id, t2_id = buyer.id, req1.id, req2.id, order.id, t1.id, t2.id

    barrier = threading.Barrier(2)
    results = []

    def worker(target_req_id: uuid.UUID):
        with SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = TransporterService(TransporterRepository(sess))
                barrier.wait()
                svc.approve_assignment(user_obj, target_req_id)
                results.append(("ok", target_req_id, 200))
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                results.append(("err", target_req_id, getattr(exc, "status_code", 500)))

    threads = [threading.Thread(target=worker, args=(req1_id,)), threading.Thread(target=worker, args=(req2_id,))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [r for r in results if r[0] == "ok"]
    losers = [r for r in results if r[0] == "err"]
    assert len(winners) == 1
    assert len(losers) == 1
    assert losers[0][2] == 409

    with SessionLocal() as check:
        final_order = check.get(Order, order_id)
        final_req1 = check.get(TransportConnectionRequest, req1_id)
        final_req2 = check.get(TransportConnectionRequest, req2_id)
        if winners[0][1] == req1_id:
            assert final_order.transporter_id == t1_id
            assert final_req1.status == "counterparty_approved"
            assert final_req2.status == "transporter_accepted"
        else:
            assert final_order.transporter_id == t2_id
            assert final_req2.status == "counterparty_approved"
            assert final_req1.status == "transporter_accepted"

    engine.dispose()


def test_approve_vs_cancel_and_reject_races(client, db_session, users_fixture):
    """Cancel or reject invalidates subsequent approval, and approval invalidates subsequent cancel/reject."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]
    transporter2 = _create_second_verified_transporter(db_session)

    order = Order(
        order_number="ORD-STATE-RACE-001",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("32000.00"),
        status="confirmed",
        transport_status="none",
    )
    db_session.add(order)
    db_session.commit()

    # Case A: Cancel happens before approve
    req_a_id = client.post(
        "/api/v1/transporters/connection-requests",
        json={"transporter_user_id": str(transporter.id), "order_id": str(order.id), "cargo_description": "Rice 1000 kg"},
        headers=get_auth_headers(farmer),
    ).json()["id"]
    client.post(f"/api/v1/transporters/connection-requests/{req_a_id}/accept", json={}, headers=get_auth_headers(transporter))
    assert client.post(f"/api/v1/transporters/connection-requests/{req_a_id}/cancel", headers=get_auth_headers(farmer)).status_code == 200
    assert client.post(f"/api/v1/transporters/connection-requests/{req_a_id}/approve", json={}, headers=get_auth_headers(buyer)).status_code == 400

    db_session.refresh(order)
    assert order.transporter_id is None

    # Case B: Approve happens before cancel or reject
    req_b_id = client.post(
        "/api/v1/transporters/connection-requests",
        json={"transporter_user_id": str(transporter2.id), "order_id": str(order.id), "cargo_description": "Rice 1000 kg"},
        headers=get_auth_headers(farmer),
    ).json()["id"]
    client.post(f"/api/v1/transporters/connection-requests/{req_b_id}/accept", json={}, headers=get_auth_headers(transporter2))
    assert client.post(f"/api/v1/transporters/connection-requests/{req_b_id}/approve", json={}, headers=get_auth_headers(buyer)).status_code == 200
    assert client.post(f"/api/v1/transporters/connection-requests/{req_b_id}/cancel", headers=get_auth_headers(farmer)).status_code == 400
    assert client.post(f"/api/v1/transporters/connection-requests/{req_b_id}/reject", json={}, headers=get_auth_headers(buyer)).status_code == 400

    db_session.refresh(order)
    assert order.transporter_id == transporter2.id


def test_cross_entity_order_offer_exploit_and_authorization(client, db_session, users_fixture):
    """Enforce order/offer pairing integrity and exclusive order-counterparty authorization."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    pwd = hash_password("Password123!")
    buyer2 = User(
        email="buyer2.attacker@example.com",
        password_hash=pwd,
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(buyer2)
    db_session.flush()
    db_session.add(
        BuyerProfile(
            user_id=buyer2.id,
            business_name="Other Buyer Co",
            contact_person_name="Rohan",
            business_type="wholesaler",
            delivery_receiving_address="Yard 9, Pune",
            city="Pune",
            state="Maharashtra",
            postal_code="411001",
        )
    )

    conv_real = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    conv_other = Conversation(farmer_id=farmer.id, buyer_id=buyer2.id)
    db_session.add_all([conv_real, conv_other])
    db_session.flush()

    offer_real = Offer(
        offer_number="OFF-SEC-REAL",
        conversation_id=conv_real.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=Decimal("25000.00"),
        status="accepted",
    )
    offer_other = Offer(
        offer_number="OFF-SEC-OTHER",
        conversation_id=conv_other.id,
        sender_id=farmer.id,
        recipient_id=buyer2.id,
        total_amount=Decimal("18000.00"),
        status="accepted",
    )
    db_session.add_all([offer_real, offer_other])
    db_session.flush()

    order_from_offer = Order(
        order_number="ORD-SEC-OFFER",
        source_offer_id=offer_real.id,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("25000.00"),
        status="confirmed",
        transport_status="none",
    )
    order_direct = Order(
        order_number="ORD-SEC-DIRECT",
        source_offer_id=None,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("22000.00"),
        status="confirmed",
        transport_status="none",
    )
    db_session.add_all([order_from_offer, order_direct])
    db_session.commit()

    # 1. Mismatched order_id + offer_id rejected at creation (both offer-linked and direct order)
    mismatch_res1 = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order_from_offer.id),
            "offer_id": str(offer_other.id),
        },
        headers=get_auth_headers(farmer),
    )
    assert mismatch_res1.status_code == 400

    mismatch_res2 = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order_direct.id),
            "offer_id": str(offer_other.id),
        },
        headers=get_auth_headers(farmer),
    )
    assert mismatch_res2.status_code == 400

    # 2. Valid matching order_id + offer_id works; unrelated offer party cannot inspect/act
    valid_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order_from_offer.id),
            "offer_id": str(offer_real.id),
        },
        headers=get_auth_headers(farmer),
    )
    assert valid_res.status_code == 201
    valid_req_id = valid_res.json()["id"]

    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{valid_req_id}/accept",
            json={},
            headers=get_auth_headers(transporter),
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{valid_req_id}/approve",
            json={},
            headers=get_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{valid_req_id}/reject",
            json={},
            headers=get_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/transporters/connection-requests/{valid_req_id}",
            headers=get_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{valid_req_id}/approve",
            json={},
            headers=get_auth_headers(buyer),
        ).status_code
        == 200
    )
    db_session.refresh(order_from_offer)
    assert order_from_offer.transporter_id == transporter.id

    # 3. Corrupted pre-existing DB row linking order_direct + offer_other blocks buyer2 (403)
    # and rejects even the real order counterparty with 400 integrity error.
    corrupt_req = TransportConnectionRequest(
        requester_id=farmer.id,
        transporter_id=transporter.id,
        order_id=order_direct.id,
        offer_id=offer_other.id,
        status="transporter_accepted",
    )
    db_session.add(corrupt_req)
    db_session.commit()

    assert (
        client.get(
            f"/api/v1/transporters/connection-requests/{corrupt_req.id}",
            headers=get_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{corrupt_req.id}/approve",
            json={},
            headers=get_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{corrupt_req.id}/reject",
            json={},
            headers=get_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{corrupt_req.id}/approve",
            json={},
            headers=get_auth_headers(buyer),
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{corrupt_req.id}/reject",
            json={},
            headers=get_auth_headers(buyer),
        ).status_code
        == 400
    )
    get_order_party = client.get(
        f"/api/v1/transporters/connection-requests/{corrupt_req.id}",
        headers=get_auth_headers(buyer),
    )
    assert get_order_party.status_code == 200
    assert get_order_party.json()["can_current_user_approve"] is False
    assert get_order_party.json()["can_current_user_reject"] is False

    db_session.refresh(order_direct)
    assert order_direct.transporter_id is None


def test_offer_only_bilateral_workflow_and_outsider_blocks(client, db_session, users_fixture):
    """Offer-only connection requests support bilateral accept/reject/approve & block outsiders."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]
    transporter2 = _create_second_verified_transporter(db_session)

    outsider = User(
        email="outsider.buyer@example.com",
        password_hash=hash_password("Password123!"),
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(outsider)
    conv = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    db_session.add(conv)
    db_session.flush()

    offer = Offer(
        offer_number="OFF-ONLY-001",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=Decimal("30000.00"),
        status="accepted",
    )
    db_session.add(offer)
    db_session.commit()

    # Outsider cannot initiate for someone else's offer
    assert (
        client.post(
            "/api/v1/transporters/connection-requests",
            json={"transporter_user_id": str(transporter.id), "offer_id": str(offer.id)},
            headers=get_auth_headers(outsider),
        ).status_code
        == 403
    )

    # Reject path on offer-only request
    req1_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={"transporter_user_id": str(transporter.id), "offer_id": str(offer.id)},
        headers=get_auth_headers(farmer),
    )
    assert req1_res.status_code == 201
    req1_id = req1_res.json()["id"]
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{req1_id}/accept",
            json={},
            headers=get_auth_headers(transporter),
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/transporters/connection-requests/{req1_id}",
            headers=get_auth_headers(outsider),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{req1_id}/approve",
            json={},
            headers=get_auth_headers(outsider),
        ).status_code
        == 403
    )
    rej_res = client.post(
        f"/api/v1/transporters/connection-requests/{req1_id}/reject",
        json={"counterparty_rejection_reason": "Need larger truck"},
        headers=get_auth_headers(buyer),
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "counterparty_rejected"

    # Approve path on offer-only request
    req2_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={"transporter_user_id": str(transporter2.id), "offer_id": str(offer.id)},
        headers=get_auth_headers(farmer),
    )
    assert req2_res.status_code == 201
    req2_id = req2_res.json()["id"]
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{req2_id}/accept",
            json={},
            headers=get_auth_headers(transporter2),
        ).status_code
        == 200
    )
    appr_res = client.post(
        f"/api/v1/transporters/connection-requests/{req2_id}/approve",
        json={"approval_notes": "Confirmed"},
        headers=get_auth_headers(buyer),
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "counterparty_approved"


def test_cancelled_order_blocks_bilateral_approval_and_coordination(
    client, db_session, users_fixture
):
    """Cancelled orders block bilateral approval (400) and coordination changes (409)."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    order_unassigned = Order(
        order_number="ORD-CANCEL-BILAT",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("26000.00"),
        status="confirmed",
        transport_status="none",
    )
    order_assigned = Order(
        order_number="ORD-CANCEL-COORD",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("28000.00"),
        status="confirmed",
        transporter_id=transporter.id,
        transport_status="assigned",
    )
    db_session.add_all([order_unassigned, order_assigned])
    db_session.commit()

    # Create and accept request while order_unassigned is still confirmed
    req_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order_unassigned.id),
        },
        headers=get_auth_headers(farmer),
    )
    req_id = req_res.json()["id"]
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{req_id}/accept",
            json={},
            headers=get_auth_headers(transporter),
        ).status_code
        == 200
    )

    # Cancel both orders
    order_unassigned.status = "cancelled"
    order_assigned.status = "cancelled"
    db_session.commit()

    # 1. Bilateral approval must fail with 400 and never assign transporter
    appr_res = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/approve",
        json={},
        headers=get_auth_headers(buyer),
    )
    assert appr_res.status_code == 400
    assert "cancelled" in appr_res.json()["detail"].lower()

    db_session.refresh(order_unassigned)
    assert order_unassigned.transporter_id is None
    assert order_unassigned.transport_status == "none"

    # 2. All transport coordination transitions on cancelled order must fail with 409
    for target_status in ("in_transit", "delivered", "assigned", "none"):
        coord_res = client.post(
            f"/api/v1/orders/{order_assigned.id}/transport-coordination",
            json={"transport_status": target_status},
            headers=get_auth_headers(farmer),
        )
        assert coord_res.status_code == 409
        assert "cancelled" in coord_res.json()["detail"].lower()

    # Historical transport fields remain intact
    db_session.refresh(order_assigned)
    assert order_assigned.transporter_id == transporter.id
    assert order_assigned.transport_status == "assigned"


def test_active_order_transport_coordination_transitions_succeed(
    client, db_session, users_fixture
):
    """Active assigned order can still transition assigned -> in_transit -> delivered cleanly."""
    farmer = users_fixture["farmer"]
    buyer = users_fixture["buyer"]
    transporter = users_fixture["transporter_v"]

    order = Order(
        order_number="ORD-ACTIVE-TRANS",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("19000.00"),
        status="confirmed",
        transporter_id=transporter.id,
        transport_status="assigned",
    )
    db_session.add(order)
    db_session.commit()

    r1 = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transport_status": "in_transit"},
        headers=get_auth_headers(farmer),
    )
    assert r1.status_code == 200
    assert r1.json()["transport_status"] == "in_transit"

    r2 = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transport_status": "delivered"},
        headers=get_auth_headers(buyer),
    )
    assert r2.status_code == 200
    assert r2.json()["transport_status"] == "delivered"


def test_concurrent_cancel_order_vs_approve_assignment_race(tmp_path):
    """Concurrent cancel_order vs approve_assignment never produces cancelled+unclaimed race."""
    db_file = tmp_path / "cancel_approve_race.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as seed:
        pwd = hash_password("Password123!")
        farmer = User(
            email="fcancel@ex.com",
            password_hash=pwd,
            role="farmer",
            verification_status="verified",
            account_status="active",
        )
        buyer = User(
            email="bcancel@ex.com",
            password_hash=pwd,
            role="buyer",
            verification_status="verified",
            account_status="active",
        )
        t1 = User(
            email="tcancel@ex.com",
            password_hash=pwd,
            role="transporter",
            verification_status="verified",
            account_status="active",
        )
        seed.add_all([farmer, buyer, t1])
        seed.flush()
        seed.add(
            FarmerProfile(
                user_id=farmer.id,
                full_name="Farmer Race",
                farm_name="Race Farm",
                farm_location_address="Plot 1",
                city="Nashik",
                state="Maharashtra",
                postal_code="422003",
            )
        )
        seed.add(
            BuyerProfile(
                user_id=buyer.id,
                business_name="Buyer Race",
                contact_person_name="Buyer Contact",
                business_type="retailer",
                delivery_receiving_address="Dock 1",
                city="Mumbai",
                state="Maharashtra",
                postal_code="400001",
            )
        )
        seed.add(
            TransporterProfile(
                user_id=t1.id,
                business_name="Race Logistics",
                contact_name="Raj",
                phone_number="9999900099",
                transport_type="mini_truck",
                vehicle_capacity_kg=Decimal("3000.00"),
                vehicle_registration_number="MH-01-RC-0099",
            )
        )
        order = Order(
            order_number="ORD-CANCEL-RACE-1",
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            total_amount=Decimal("15000.00"),
            status="confirmed",
            transport_status="none",
        )
        seed.add(order)
        seed.flush()
        req = TransportConnectionRequest(
            requester_id=farmer.id,
            transporter_id=t1.id,
            order_id=order.id,
            status="transporter_accepted",
        )
        seed.add(req)
        seed.commit()
        buyer_id, req_id, order_id, t1_id = buyer.id, req.id, order.id, t1.id

    barrier = threading.Barrier(2)
    results = {}

    def cancel_worker():
        with SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = OrderService(sess)
                barrier.wait()
                svc.cancel_order(
                    user_obj, order_id, OrderCancelRequest(reason="Buyer cancelled deal")
                )
                results["cancel"] = ("ok", 200)
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                results["cancel"] = ("err", getattr(exc, "status_code", 500))

    def approve_worker():
        with SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = TransporterService(TransporterRepository(sess))
                barrier.wait()
                svc.approve_assignment(user_obj, req_id)
                results["approve"] = ("ok", 200)
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                results["approve"] = ("err", getattr(exc, "status_code", 500))

    t_cancel = threading.Thread(target=cancel_worker)
    t_approve = threading.Thread(target=approve_worker)
    t_cancel.start()
    t_approve.start()
    t_cancel.join()
    t_approve.join()

    with SessionLocal() as check:
        final_order = check.get(Order, order_id)
        final_req = check.get(TransportConnectionRequest, req_id)
        assert final_order.status == "cancelled"

        if results["approve"][0] == "err":
            # Cancel won the lock first -> approval cleanly rejected and order unassigned
            assert results["approve"][1] in (400, 409)
            assert final_order.transporter_id is None
            assert final_order.transport_status == "none"
            assert final_req.status == "transporter_accepted"
        else:
            # Approve committed atomically before cancel started; both transitions stay consistent
            assert results["approve"] == ("ok", 200)
            assert results["cancel"] == ("ok", 200)
            assert final_order.transporter_id == t1_id
            assert final_req.status == "counterparty_approved"

    engine.dispose()

