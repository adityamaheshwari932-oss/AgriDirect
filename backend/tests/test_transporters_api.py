"""Integration and unit tests for AgriDirect Transporter Module.

Tests:
1. Transporter Registration & Authentication
2. Profile Inspection & Update
3. Service Area CRUD, Deduplication & Ownership Enforcement
4. Transporter Discovery & Geo/Capacity Filtering
5. Order Transport Coordination Workflow
"""

import uuid
from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.offer import Offer
from app.models.order import Order
from app.models.user import ServiceArea, TransporterProfile, User


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
    """TestClient wired to isolated in-memory SQLite database."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_headers(user: User) -> dict:
    """Generate authorization Bearer headers for a user."""
    token = create_access_token({"sub": str(user.id), "role": user.role, "status": user.verification_status})
    return {"Authorization": f"Bearer {token}"}


def test_register_transporter_success(client):
    """Test successful transporter registration."""
    payload = {
        "email": "trans_reg@example.com",
        "password": "Password123!",
        "phone_number": "+919111122222",
        "business_name": "Bharat Kisan Logistics",
        "contact_name": "Deepak Sharma",
        "transport_type": "mini_truck",
        "vehicle_capacity_kg": 3000.0,
        "vehicle_registration_number": "DL-01-AB-1234",
        "experience_years": 5,
        "operating_states": "Delhi, Haryana, Punjab",
        "bio": "Experienced rural agriculture transport service.",
        "initial_service_areas": [
            {
                "state": "Punjab",
                "district": "Ludhiana",
                "coverage_type": "both",
                "is_active": True,
            }
        ],
    }

    resp = client.post("/api/v1/auth/register/transporter", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "trans_reg@example.com"
    assert data["role"] == "transporter"
    assert data["verification_status"] == "unverified"
    assert data["account_status"] == "active"
    assert data["transporter_profile"] is not None
    assert data["transporter_profile"]["business_name"] == "Bharat Kisan Logistics"
    assert float(data["transporter_profile"]["vehicle_capacity_kg"]) == 3000.0


def test_register_transporter_duplicate_conflict(client):
    """Test duplicate registration returns 409 Conflict."""
    payload = {
        "email": "trans_dup@example.com",
        "password": "Password123!",
        "phone_number": "+919222233333",
        "business_name": "Dup Trans",
        "contact_name": "Dup Contact",
        "transport_type": "tempo",
        "vehicle_capacity_kg": 1500.0,
        "vehicle_registration_number": "MH-12-QQ-1111",
    }
    resp1 = client.post("/api/v1/auth/register/transporter", json=payload)
    assert resp1.status_code == 201

    # Conflict on email
    resp2 = client.post("/api/v1/auth/register/transporter", json=payload)
    assert resp2.status_code == 409
    assert "email address already exists" in resp2.json()["detail"]


def test_transporter_login(client):
    """Test login with transporter credentials."""
    payload = {
        "email": "trans_login@example.com",
        "password": "Password123!",
        "phone_number": "+919333344444",
        "business_name": "Login Trans",
        "contact_name": "Login Contact",
        "transport_type": "open_body",
        "vehicle_capacity_kg": 5000.0,
        "vehicle_registration_number": "MH-14-ZZ-2222",
    }
    client.post("/api/v1/auth/register/transporter", json=payload)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "trans_login@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["user"]["role"] == "transporter"


def test_transporter_profile_me_and_forbidden_for_farmer(client, db_session):
    """Test /api/v1/transporters/me endpoints."""
    # Create transporter
    user = User(
        email="trans_me@example.com",
        phone_number="+919444455555",
        password_hash=hash_password("Pass1234"),
        role="transporter",
        verification_status="verified",
    )
    profile = TransporterProfile(
        business_name="Me Transport",
        contact_name="Me Owner",
        phone_number="+919444455555",
        transport_type="refrigerated",
        vehicle_capacity_kg=Decimal("4000.00"),
        vehicle_registration_number="KA-01-EE-3333",
    )
    user.transporter_profile = profile
    db_session.add(user)

    # Create farmer
    farmer = User(
        email="farmer_test@example.com",
        password_hash=hash_password("Pass1234"),
        role="farmer",
    )
    db_session.add(farmer)
    db_session.commit()

    # Transporter gets profile
    resp = client.get("/api/v1/transporters/me", headers=make_headers(user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["business_name"] == "Me Transport"
    assert data["transport_type"] == "refrigerated"

    # Farmer gets 403 Forbidden
    resp_farmer = client.get("/api/v1/transporters/me", headers=make_headers(farmer))
    assert resp_farmer.status_code == 403
    assert "Operation permitted only for users with role='transporter'" in resp_farmer.json()["detail"]

    # Transporter updates profile
    patch_resp = client.patch(
        "/api/v1/transporters/me",
        json={"business_name": "Updated Me Logistics", "is_available": False},
        headers=make_headers(user),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["business_name"] == "Updated Me Logistics"
    assert patch_resp.json()["is_available"] is False


def test_service_areas_crud_and_deduplication(client, db_session):
    """Test ServiceArea add, list, update, duplicate check, and delete."""
    user = User(
        email="trans_sa_test@example.com",
        phone_number="+919555566666",
        password_hash=hash_password("Pass1234"),
        role="transporter",
    )
    profile = TransporterProfile(
        business_name="Area Transport",
        contact_name="Area Owner",
        phone_number="+919555566666",
        transport_type="mini_truck",
        vehicle_capacity_kg=Decimal("2000.00"),
        vehicle_registration_number="MH-20-AA-4444",
    )
    user.transporter_profile = profile
    db_session.add(user)
    db_session.commit()

    headers = make_headers(user)

    # 1. Add service area
    add_payload = {
        "state": "Maharashtra",
        "district": "Nashik",
        "taluka_subdistrict": "Niphad",
        "pincode": "422303",
        "coverage_type": "both",
        "is_active": True,
    }
    resp = client.post("/api/v1/transporters/service-areas", json=add_payload, headers=headers)
    assert resp.status_code == 201
    area_data = resp.json()
    assert area_data["state"] == "Maharashtra"
    assert area_data["district"] == "Nashik"
    area_id = area_data["id"]

    # 2. Add duplicate service area -> 409 Conflict
    resp_dup = client.post("/api/v1/transporters/service-areas", json=add_payload, headers=headers)
    assert resp_dup.status_code == 409
    assert "already exists" in resp_dup.json()["detail"]

    # 3. List service areas
    list_resp = client.get("/api/v1/transporters/service-areas", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 4. Update service area
    update_resp = client.patch(
        f"/api/v1/transporters/service-areas/{area_id}",
        json={"pincode": "422304", "coverage_type": "pickup_only"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["pincode"] == "422304"
    assert update_resp.json()["coverage_type"] == "pickup_only"

    # 5. Delete service area
    del_resp = client.delete(f"/api/v1/transporters/service-areas/{area_id}", headers=headers)
    assert del_resp.status_code == 200

    # 6. Verify list is now empty
    list_resp2 = client.get("/api/v1/transporters/service-areas", headers=headers)
    assert len(list_resp2.json()) == 0


def test_transporter_discovery(client, db_session):
    """Test marketplace discovery with filters."""
    # Transporter 1: Pune, mini_truck, 2000kg
    u1 = User(
        email="t1@example.com",
        password_hash=hash_password("P1"),
        role="transporter",
        account_status="active",
        verification_status="verified",
    )
    p1 = TransporterProfile(
        business_name="Pune Express",
        contact_name="P1",
        phone_number="+919666611111",
        transport_type="mini_truck",
        vehicle_capacity_kg=Decimal("2000.00"),
        vehicle_registration_number="MH-12-P1",
        is_available=True,
        experience_years=5,
    )
    u1.transporter_profile = p1
    db_session.add(u1)
    db_session.commit()

    sa1 = ServiceArea(transporter_profile_id=p1.id, state="Maharashtra", district="Pune", coverage_type="both", is_active=True)
    db_session.add(sa1)

    # Transporter 2: Nashik to Mumbai, refrigerated, 8000kg
    u2 = User(
        email="t2@example.com",
        password_hash=hash_password("P2"),
        role="transporter",
        account_status="active",
        verification_status="verified",
    )
    p2 = TransporterProfile(
        business_name="ColdChain Transit",
        contact_name="P2",
        phone_number="+919666622222",
        transport_type="refrigerated",
        vehicle_capacity_kg=Decimal("8000.00"),
        vehicle_registration_number="MH-15-P2",
        is_available=True,
        experience_years=10,
    )
    u2.transporter_profile = p2
    db_session.add(u2)
    db_session.commit()

    sa2_pickup = ServiceArea(transporter_profile_id=p2.id, state="Maharashtra", district="Nashik", coverage_type="pickup_only", is_active=True)
    sa2_deliv = ServiceArea(transporter_profile_id=p2.id, state="Maharashtra", district="Mumbai", coverage_type="delivery_only", is_active=True)
    db_session.add_all([sa2_pickup, sa2_deliv])
    db_session.commit()

    # Search: pickup Pune -> matches only t1
    resp = client.get("/api/v1/transporters/discover?pickup_state=Maharashtra&pickup_district=Pune")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["business_name"] == "Pune Express"

    # Search: pickup Nashik -> matches t2
    resp2 = client.get("/api/v1/transporters/discover?pickup_state=Maharashtra&pickup_district=Nashik")
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 1
    assert resp2.json()["items"][0]["business_name"] == "ColdChain Transit"

    # Search: min capacity 5000kg -> matches t2 only
    resp3 = client.get("/api/v1/transporters/discover?min_capacity_kg=5000")
    assert resp3.status_code == 200
    assert resp3.json()["total"] == 1
    assert resp3.json()["items"][0]["business_name"] == "ColdChain Transit"

    # Search: transport_type refrigerated
    resp4 = client.get("/api/v1/transporters/discover?transport_type=refrigerated")
    assert resp4.status_code == 200
    assert resp4.json()["total"] == 1
    assert resp4.json()["items"][0]["business_name"] == "ColdChain Transit"

    # Public profile inspection
    resp_pub = client.get(f"/api/v1/transporters/{p2.id}")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["business_name"] == "ColdChain Transit"
    assert len(resp_pub.json()["service_areas"]) == 2


def test_order_transport_coordination(client, db_session):
    """Test order transport coordination by farmer/buyer and status updates by transporter."""
    # Farmer
    farmer = User(
        email="f_ord@example.com",
        password_hash=hash_password("Pass1"),
        role="farmer",
        verification_status="verified",
    )
    db_session.add(farmer)
    # Buyer
    buyer = User(
        email="b_ord@example.com",
        password_hash=hash_password("Pass2"),
        role="buyer",
        verification_status="verified",
    )
    db_session.add(buyer)
    # Transporter
    transporter = User(
        email="t_ord@example.com",
        password_hash=hash_password("Pass3"),
        role="transporter",
        verification_status="verified",
    )
    t_prof = TransporterProfile(
        business_name="Fast Transit",
        contact_name="Transit Driver",
        phone_number="+919777788888",
        transport_type="mini_truck",
        vehicle_capacity_kg=Decimal("3000.00"),
        vehicle_registration_number="MH-12-TT-9999",
    )
    transporter.transporter_profile = t_prof
    db_session.add(transporter)
    db_session.commit()

    # Conversation
    conv = Conversation(
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        initial_context_type="general",
    )
    db_session.add(conv)
    db_session.commit()

    # Offer
    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        status="accepted",
        total_amount=Decimal("15000.00"),
    )
    db_session.add(offer)
    db_session.commit()

    # Order
    order = Order(
        order_number="ORD-2026-TEST-99",
        source_offer_id=offer.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=Decimal("15000.00"),
        status="confirmed",
        delivery_status="not_arranged",
    )
    db_session.add(order)
    db_session.commit()

    # 1. Legacy direct transporter assignment via transport-coordination is disabled
    resp_bypass = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={
            "transporter_user_id": str(transporter.id),
            "transport_status": "assigned",
            "delivery_notes": "Attempted bypass assignment",
        },
        headers=make_headers(buyer),
    )
    assert resp_bypass.status_code == 400
    assert "bilateral" in resp_bypass.json()["detail"].lower()
    db_session.refresh(order)
    assert order.transporter_id is None
    assert order.transport_status == "none"

    # 2. Cannot mark in_transit before bilateral transporter assignment
    resp_early_transit = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transport_status": "in_transit"},
        headers=make_headers(buyer),
    )
    assert resp_early_transit.status_code == 400

    # 3. Assign transporter properly through bilateral workflow (request -> accept -> approve)
    req_resp = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(transporter.id),
            "order_id": str(order.id),
            "cargo_description": "Pickup at farm warehouse Gate 2",
        },
        headers=make_headers(buyer),
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["id"]

    accept_resp = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/accept",
        json={"response_notes": "Confirmed pickup schedule"},
        headers=make_headers(transporter),
    )
    assert accept_resp.status_code == 200

    approve_resp = client.post(
        f"/api/v1/transporters/connection-requests/{req_id}/approve",
        json={"approval_notes": "Approved by farmer"},
        headers=make_headers(farmer),
    )
    assert approve_resp.status_code == 200
    db_session.refresh(order)
    assert order.transporter_id == transporter.id
    assert order.transport_status == "assigned"

    # 4. Transporter updates status to in_transit via transport-coordination
    resp_transit = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transport_status": "in_transit", "delivery_notes": "Departed from farm"},
        headers=make_headers(transporter),
    )
    assert resp_transit.status_code == 200
    assert resp_transit.json()["transport_status"] == "in_transit"
    assert resp_transit.json()["transporter_business_name"] == "Fast Transit"

    # 5. Transporter marks delivered
    resp_deliv = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transport_status": "delivered", "delivery_notes": "Delivered to buyer dock"},
        headers=make_headers(transporter),
    )
    assert resp_deliv.status_code == 200
    assert resp_deliv.json()["transport_status"] == "delivered"

    # 6. Unauthorized third party receives 403
    random_user = User(email="rando@example.com", password_hash=hash_password("PassX"), role="farmer")
    db_session.add(random_user)
    db_session.commit()

    resp_unauth = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"delivery_notes": "Hacked"},
        headers=make_headers(random_user),
    )
    assert resp_unauth.status_code == 403
