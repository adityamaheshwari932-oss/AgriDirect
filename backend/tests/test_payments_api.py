"""Unit and API integration tests for AgriDirect Module 6: Payment Tracking & Dispute Moderation.

Covers:
1. Payment Recording (JSON and multipart form-data with proof file).
2. Authorization and anti-enumeration guards.
3. Overpayment ceiling enforcement and balance calculations.
4. Farmer receipt acknowledgement workflow.
5. Payment dispute complaint filing and atomic transition to disputed.
6. Admin dispute moderation queue, detail inspection, and resolutions.
7. Proof and evidence file security (magic bytes, executable rejection, path traversal).
8. Order reconciliation summary and settlement statuses.
"""

import io
import os
import shutil
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
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
from app.models.chat import Conversation
from app.models.listing import ProduceCategory, ProduceListing, STATUS_ACTIVE
from app.models.offer import Offer, OfferItem, OFFER_STATUS_ACCEPTED
from app.models.order import (
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DISPUTED,
    Order,
    OrderItem,
)
from app.models.payment import (
    PAYMENT_COMPLAINT_STATUS_DISMISSED,
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    PaymentComplaint,
    PaymentRecord,
)
from app.models.user import BuyerProfile, FarmerProfile, User
from app.payments.routes import get_payment_storage
from app.payments.storage import PaymentStorageService


# ===========================================================================
# Magic Byte Payloads for Security Testing
# ===========================================================================

JPEG_MAGIC = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 50
PNG_MAGIC = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00" + b"\x00" * 50
PDF_MAGIC = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

EXE_MAGIC = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
ELF_MAGIC = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
JAVA_CLASS = b"\xca\xfe\xba\xbe\x00\x00\x00\x34"
SHEBANG_SCRIPT = b"#!/bin/bash\necho Malicious\n"
PLAIN_TEXT = b"Hello, this is just plain text masquerading as an image."


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
def temp_storage():
    """Temporary storage directory for payment files."""
    tmpdir = tempfile.mkdtemp(prefix="agridirect_pay_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def client(sqlite_engine, temp_storage) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db and temporary storage."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    test_storage = PaymentStorageService(base_dir=temp_storage)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_payment_storage] = lambda: test_storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ===========================================================================
# Helper Seed Functions
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
    FarmerProfile(
        user=u,
        full_name="Ramesh Patil",
        farm_name="Patil Agro Farms",
        farm_location_address="Gat 12, Nashik",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_buyer(db: Session, verified: bool = True, active: bool = True) -> User:
    """Create a commercial buyer with profile."""
    u = User(
        email=f"buyer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active" if active else "suspended",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    BuyerProfile(
        user=u,
        business_name="Green Harvest Foods",
        business_type="restaurant",
        contact_person_name="Priya Sharma",
        delivery_receiving_address="Shop 4, Market Yard",
        city="Pune",
        state="Maharashtra",
        postal_code="411037",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_admin(db: Session) -> User:
    """Create an administrator user."""
    u = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9196{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_order(
    db: Session,
    farmer: User,
    buyer: User,
    total_amount: Decimal = Decimal("5000.00"),
    status: str = ORDER_STATUS_CONFIRMED,
) -> Order:
    """Seed category, listing, conversation, offer, order, and order item."""
    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg_{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Organic Red Onion",
        title="Fresh Red Onions",
        initial_quantity=Decimal("1000.000"),
        available_quantity=Decimal("800.000"),
        unit="kg",
        price_per_unit=Decimal("25.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.flush()

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
        status=status,
        delivery_status=DELIVERY_STATUS_NOT_ARRANGED,
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        product_name=listing.product_name,
        quantity=Decimal("40.000"),
        unit="kg",
        unit_price=Decimal("25.00"),
        subtotal=total_amount,
        status="confirmed",
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# 1. Payment Recording Tests
# ===========================================================================

def test_record_payment_json_success(client: TestClient, db_session: Session):
    """Verified buyer records valid payment via JSON."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    payload = {
        "amount": "400.00",
        "payment_method": "bank_transfer",
        "reference_number": "UTR1234567890",
        "payment_date": date.today().isoformat(),
        "notes": "Advance payment of 40%",
    }

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json=payload,
        headers=make_headers(buyer),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_id"] == str(order.id)
    assert Decimal(data["amount"]) == Decimal("400.00")
    assert data["payment_method"] == "bank_transfer"
    assert data["reference_number"] == "UTR1234567890"
    assert data["status"] == PAYMENT_STATUS_RECORDED
    assert data["acknowledged_at"] is None
    assert data["acknowledged_by"] is None


def test_record_payment_multipart_with_proof_success(client: TestClient, db_session: Session):
    """Verified buyer records valid payment via multipart with JPEG proof."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("2000.00"))

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        data={
            "amount": "1000.00",
            "payment_method": "upi",
            "reference_number": "UPI9876543210",
            "payment_date": date.today().isoformat(),
            "notes": "UPI receipt attached",
        },
        files={"proof_file": ("receipt.jpg", io.BytesIO(JPEG_MAGIC), "image/jpeg")},
        headers=make_headers(buyer),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert Decimal(data["amount"]) == Decimal("1000.00")
    assert data["proof_file_path"] is not None
    assert "receipt" not in data["proof_file_path"]  # Server UUID named, not client name


def test_record_payment_unverified_buyer_rejected(client: TestClient, db_session: Session):
    """Unverified buyer cannot record payment."""
    farmer = seed_farmer(db_session)
    unverified_buyer = seed_buyer(db_session, verified=False)
    order = seed_order(db_session, farmer, unverified_buyer)

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(unverified_buyer),
    )
    assert resp.status_code == 403
    assert "verified" in resp.json()["detail"].lower()


def test_record_payment_inactive_buyer_rejected(client: TestClient, db_session: Session):
    """Suspended buyer cannot record payment."""
    farmer = seed_farmer(db_session)
    suspended_buyer = seed_buyer(db_session, active=False)
    order = seed_order(db_session, farmer, suspended_buyer)

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(suspended_buyer),
    )
    assert resp.status_code == 403


def test_record_payment_farmer_rejected(client: TestClient, db_session: Session):
    """Farmer cannot record payment against order."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(farmer),
    )
    assert resp.status_code == 403
    assert "buyer" in resp.json()["detail"].lower()


def test_record_payment_unrelated_buyer_anti_enumeration(client: TestClient, db_session: Session):
    """Unrelated buyer receives 404 anti-enumeration."""
    farmer = seed_farmer(db_session)
    buyer1 = seed_buyer(db_session)
    buyer2 = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer1)

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer2),
    )
    assert resp.status_code == 404


def test_record_payment_future_date_rejected(client: TestClient, db_session: Session):
    """Future payment date is rejected."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    future_date = (date.today() + timedelta(days=2)).isoformat()
    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "bank_transfer",
            "payment_date": future_date,
        },
        headers=make_headers(buyer),
    )
    assert resp.status_code == 400
    assert "future" in resp.json()["detail"].lower()


def test_record_payment_prior_to_order_date_rejected(client: TestClient, db_session: Session):
    """Payment date prior to order creation date is rejected."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    past_date = (order.created_at.date() - timedelta(days=5)).isoformat()
    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "bank_transfer",
            "payment_date": past_date,
        },
        headers=make_headers(buyer),
    )
    assert resp.status_code == 400
    assert "earlier" in resp.json()["detail"].lower()


def test_record_payment_cancelled_order_rejected(client: TestClient, db_session: Session):
    """Cannot record payment for cancelled order."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, status=ORDER_STATUS_CANCELLED)

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert resp.status_code == 400
    assert "cancelled" in resp.json()["detail"].lower()


# ===========================================================================
# 2. Overpayment Prevention & Balance Checks
# ===========================================================================

def test_overpayment_single_payment_rejected(client: TestClient, db_session: Session):
    """Payment amount exceeding order total is rejected with 409 Conflict."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "1000.01",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert resp.status_code == 409
    assert "exceeds" in resp.json()["detail"].lower()


def test_overpayment_cumulative_payments_rejected(client: TestClient, db_session: Session):
    """Cumulative unacknowledged + acknowledged payments cannot exceed order total."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    # First payment: 600.00
    resp1 = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "600.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert resp1.status_code == 201

    # Second payment: 400.01 (exceeds remaining 400.00)
    resp2 = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "400.01",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert resp2.status_code == 409
    assert "exceeds" in resp2.json()["detail"].lower()

    # Second payment: exactly 400.00 (accepted)
    resp3 = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "400.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert resp3.status_code == 201


# ===========================================================================
# 3. Farmer Receipt Acknowledgement
# ===========================================================================

def test_acknowledge_payment_farmer_success(client: TestClient, db_session: Session):
    """Farmer successfully acknowledges payment receipt."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    # Buyer records payment
    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    # Farmer acknowledges
    ack_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(farmer),
    )
    assert ack_resp.status_code == 200
    data = ack_resp.json()
    assert data["status"] == PAYMENT_STATUS_ACKNOWLEDGED
    assert data["acknowledged_at"] is not None
    assert data["acknowledged_by"] == str(farmer.id)


def test_acknowledge_payment_buyer_rejected(client: TestClient, db_session: Session):
    """Buyer cannot acknowledge their own payment."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    ack_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(buyer),
    )
    assert ack_resp.status_code == 403
    assert "farmer" in ack_resp.json()["detail"].lower()


def test_acknowledge_payment_admin_rejected(client: TestClient, db_session: Session):
    """Administrator cannot directly acknowledge receipt of payment."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    ack_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(admin),
    )
    assert ack_resp.status_code == 403
    assert "farmer" in ack_resp.json()["detail"].lower()


def test_acknowledge_payment_unrelated_user_anti_enumeration(client: TestClient, db_session: Session):
    """Unrelated user receives 404 anti-enumeration."""
    farmer1 = seed_farmer(db_session)
    farmer2 = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer1, buyer)

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    ack_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(farmer2),
    )
    assert ack_resp.status_code == 404


def test_acknowledge_payment_duplicate_rejected(client: TestClient, db_session: Session):
    """Cannot re-acknowledge an already acknowledged payment."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    # First ack
    client.post(f"/api/v1/payments/{payment_id}/acknowledge", headers=make_headers(farmer))

    # Duplicate ack
    ack_resp2 = client.post(f"/api/v1/payments/{payment_id}/acknowledge", headers=make_headers(farmer))
    assert ack_resp2.status_code == 400
    assert "already" in ack_resp2.json()["detail"].lower()


# ===========================================================================
# 4. Dispute Complaint Filing
# ===========================================================================

def test_file_dispute_complaint_farmer_success(client: TestClient, db_session: Session):
    """Farmer files complaint that buyer reported payment never arrived."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "1000.00",
            "payment_method": "bank_transfer",
            "reference_number": "UTR9999",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    # Farmer files complaint
    comp_resp = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={
            "reason": "Payment not received in bank account after 5 working days",
        },
        headers=make_headers(farmer),
    )
    assert comp_resp.status_code == 201
    comp_data = comp_resp.json()
    assert comp_data["payment_id"] == payment_id
    assert comp_data["complainant_id"] == str(farmer.id)
    assert comp_data["status"] == PAYMENT_COMPLAINT_STATUS_OPEN

    # Verify payment record status transitioned to disputed
    pay_check = client.get(f"/api/v1/payments/{payment_id}", headers=make_headers(farmer))
    assert pay_check.json()["status"] == PAYMENT_STATUS_DISPUTED


def test_file_dispute_complaint_with_evidence_file(client: TestClient, db_session: Session):
    """Buyer files complaint with PDF bank statement evidence."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    comp_resp = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        data={"reason": "Farmer disputes receipt; here is bank debit confirmation"},
        files={"evidence_file": ("statement.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
        headers=make_headers(buyer),
    )
    assert comp_resp.status_code == 201
    assert comp_resp.json()["evidence_file_path"] is not None


def test_file_dispute_duplicate_active_complaint_rejected(client: TestClient, db_session: Session):
    """Cannot file another complaint while an active complaint exists on same payment."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    # First complaint
    client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={"reason": "First complaint"},
        headers=make_headers(farmer),
    )

    # Second complaint on same payment
    resp2 = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={"reason": "Second complaint"},
        headers=make_headers(buyer),
    )
    assert resp2.status_code == 400
    assert "already" in resp2.json()["detail"].lower()


# ===========================================================================
# 5. Administrative Dispute Moderation
# ===========================================================================

def test_admin_complaints_queue_and_review(client: TestClient, db_session: Session):
    """Admin inspects complaints queue and transitions complaint to under_review."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer)

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "upi",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    comp_resp = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={"reason": "Amount debited but farmer has not acknowledged"},
        headers=make_headers(buyer),
    )
    complaint_id = comp_resp.json()["id"]

    # 1. Admin lists queue
    list_resp = client.get("/api/v1/admin/payment-complaints", headers=make_headers(admin))
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 2. Non-admin forbidden
    forb_resp = client.get("/api/v1/admin/payment-complaints", headers=make_headers(buyer))
    assert forb_resp.status_code == 403

    # 3. Admin gets detail
    detail_resp = client.get(f"/api/v1/admin/payment-complaints/{complaint_id}", headers=make_headers(admin))
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["complaint"]["id"] == complaint_id
    assert detail["payment"]["id"] == payment_id
    assert detail["order"]["id"] == str(order.id)

    # 4. Admin moves to under_review
    review_resp = client.post(
        f"/api/v1/admin/payment-complaints/{complaint_id}/resolve",
        json={
            "resolution_action": "under_review",
            "resolution_notes": "Contacting bank for transaction reconciliation.",
        },
        headers=make_headers(admin),
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW


def test_admin_resolve_complaint_confirm_payment(client: TestClient, db_session: Session):
    """Admin resolves complaint with confirm_payment, transitioning payment to acknowledged."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "1000.00",
            "payment_method": "bank_transfer",
            "reference_number": "UTR555",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    comp_resp = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={"reason": "Farmer unresponsive to acknowledgement request"},
        headers=make_headers(buyer),
    )
    complaint_id = comp_resp.json()["id"]

    # Admin resolves dispute with findings notes
    resolve_resp = client.post(
        f"/api/v1/admin/payment-complaints/{complaint_id}/resolve",
        json={
            "status": "resolved",
            "resolution_notes": "Bank statement independently verified; funds received in farmer account.",
        },
        headers=make_headers(admin),
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == PAYMENT_COMPLAINT_STATUS_RESOLVED

    # Payment record transitions back to payment_recorded (unacknowledged)
    pay_check = client.get(f"/api/v1/payments/{payment_id}", headers=make_headers(admin))
    assert pay_check.json()["status"] == PAYMENT_STATUS_RECORDED
    assert pay_check.json()["acknowledged_at"] is None

    # Summary shows pending acknowledgement, NOT fully settled
    sum_resp = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer))
    assert sum_resp.json()["settlement_status"] == "payment_pending_acknowledgement"
    assert Decimal(sum_resp.json()["total_acknowledged"]) == Decimal("0.00")
    assert Decimal(sum_resp.json()["unacknowledged_amount"]) == Decimal("1000.00")

    # Farmer explicitly acknowledges payment receipt
    ack_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(farmer),
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == PAYMENT_STATUS_ACKNOWLEDGED
    assert ack_resp.json()["acknowledged_at"] is not None

    # Now summary is fully settled
    sum_resp2 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer))
    assert sum_resp2.json()["settlement_status"] == "fully_settled"
    assert Decimal(sum_resp2.json()["total_acknowledged"]) == Decimal("1000.00")


def test_admin_dismiss_complaint_restores_unacknowledged_without_false_settlement(client: TestClient, db_session: Session):
    """Admin dismisses complaint, returning payment to unacknowledged state without false settlement."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "1000.00",
            "payment_method": "other",
            "reference_number": "CHQ001",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    comp_resp = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={"reason": "Cheque bounced"},
        headers=make_headers(farmer),
    )
    complaint_id = comp_resp.json()["id"]

    # Admin dismisses complaint
    resolve_resp = client.post(
        f"/api/v1/admin/payment-complaints/{complaint_id}/resolve",
        json={
            "status": "dismissed",
            "resolution_notes": "Cheque clearance advice received and verified directly from issuing bank.",
        },
        headers=make_headers(admin),
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == PAYMENT_COMPLAINT_STATUS_DISMISSED

    # Payment record transitions back to payment_recorded (unacknowledged)
    pay_check = client.get(f"/api/v1/payments/{payment_id}", headers=make_headers(admin))
    assert pay_check.json()["status"] == PAYMENT_STATUS_RECORDED
    assert pay_check.json()["acknowledged_at"] is None

    # Summary shows payment_pending_acknowledgement, NOT false settlement
    sum_resp = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(farmer))
    assert sum_resp.json()["settlement_status"] == "payment_pending_acknowledgement"
    assert Decimal(sum_resp.json()["total_acknowledged"]) == Decimal("0.00")
    assert Decimal(sum_resp.json()["unacknowledged_amount"]) == Decimal("1000.00")
    assert Decimal(sum_resp.json()["total_disputed"]) == Decimal("0.00")


def test_disputed_payment_retains_overpayment_ceiling_protection(client: TestClient, db_session: Session):
    """Disputed payment amount remains committed against the order total, blocking overpayment."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    # Buyer records 800.00
    pay1_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "800.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert pay1_resp.status_code == 201
    pay1_id = pay1_resp.json()["id"]

    # Farmer disputes Payment 1
    comp_resp = client.post(
        f"/api/v1/payments/{pay1_id}/complaints",
        json={"reason": "Amount credited was incomplete"},
        headers=make_headers(farmer),
    )
    assert comp_resp.status_code == 201

    # Check order payment summary
    sum_resp = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer))
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert Decimal(sum_data["total_disputed"]) == Decimal("800.00")
    assert Decimal(sum_data["max_available_for_new_payment"]) == Decimal("200.00")
    assert Decimal(sum_data["remaining_payable_amount"]) == Decimal("200.00")

    # Exploitative second payment of 800.00 must be rejected with 409 Conflict
    pay2_fail = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "800.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert pay2_fail.status_code == 409
    assert "exceeds" in pay2_fail.json()["detail"].lower()

    # Legitimate payment of remaining 200.00 is accepted
    pay2_ok = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "200.00",
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert pay2_ok.status_code == 201


def test_previously_acknowledged_payment_dispute_and_reaffirmation_lifecycle(
    client: TestClient, db_session: Session
):
    """Verify complete audit trail and settlement semantics when an acknowledged payment is disputed.

    Lifecycle:
    1. Buyer records payment -> status payment_recorded, original_acknowledged_at is None.
    2. Farmer acknowledges -> status acknowledged, original_acknowledged_at = T1, acknowledged_at = T1.
    3. Complaint filed -> status disputed, original_acknowledged_at remains T1 (never erased!).
       Settlement status distinguishes disputed amounts and preserves overpayment ceiling.
    4. Admin resolves/dismisses -> status payment_recorded, acknowledged_at is None (seller reaffirmation required,
       admin NEVER manufactures acknowledgement), original_acknowledged_at remains T1 (historical evidence intact!).
    5. Farmer reaffirms receipt -> status acknowledged, acknowledged_at = T2, original_acknowledged_at remains T1.
    """
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    # Step 1: Buyer records payment
    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "1000.00",
            "payment_method": "bank_transfer",
            "reference_number": "AUDIT_UTR_001",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert pay_resp.status_code == 201
    pay_data1 = pay_resp.json()
    payment_id = pay_data1["id"]
    assert pay_data1["status"] == PAYMENT_STATUS_RECORDED
    assert pay_data1["acknowledged_at"] is None
    assert pay_data1["original_acknowledged_at"] is None
    assert pay_data1["has_historical_acknowledgement"] is False

    sum1 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert sum1["settlement_status"] == "payment_pending_acknowledgement"
    assert Decimal(sum1["unacknowledged_amount"]) == Decimal("1000.00")
    assert Decimal(sum1["total_acknowledged"]) == Decimal("0.00")
    assert Decimal(sum1["total_disputed"]) == Decimal("0.00")

    # Step 2: Farmer acknowledges receipt
    ack1_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(farmer),
    )
    assert ack1_resp.status_code == 200
    ack1_data = ack1_resp.json()
    assert ack1_data["status"] == PAYMENT_STATUS_ACKNOWLEDGED
    t1 = ack1_data["acknowledged_at"]
    assert t1 is not None
    assert ack1_data["original_acknowledged_at"] == t1
    assert ack1_data["has_historical_acknowledgement"] is True

    sum2 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert sum2["settlement_status"] == "fully_settled"
    assert Decimal(sum2["total_acknowledged"]) == Decimal("1000.00")
    assert Decimal(sum2["remaining_acknowledged_balance"]) == Decimal("0.00")
    assert Decimal(sum2["max_available_for_new_payment"]) == Decimal("0.00")

    # Step 3: Either participant files a dispute complaint on the acknowledged payment
    comp_resp = client.post(
        f"/api/v1/payments/{payment_id}/complaints",
        json={"reason": "Payer bank issued recall memo claiming duplicate debit"},
        headers=make_headers(farmer),
    )
    assert comp_resp.status_code == 201
    complaint_id = comp_resp.json()["id"]

    # Historical acknowledgement must NOT be erased upon dispute filing
    pay_check1 = client.get(f"/api/v1/payments/{payment_id}", headers=make_headers(farmer)).json()
    assert pay_check1["status"] == PAYMENT_STATUS_DISPUTED
    assert pay_check1["original_acknowledged_at"].replace("Z", "") == t1.replace("Z", "")
    assert pay_check1["has_historical_acknowledgement"] is True

    # Summary reflects disputed status and maintains overpayment ceiling
    sum3 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert sum3["settlement_status"] == "disputed"
    assert Decimal(sum3["total_disputed"]) == Decimal("1000.00")
    assert Decimal(sum3["total_acknowledged"]) == Decimal("0.00")
    assert Decimal(sum3["remaining_acknowledged_balance"]) == Decimal("1000.00")
    assert Decimal(sum3["max_available_for_new_payment"]) == Decimal("0.00")

    # Second payment attempt is blocked by ceiling during dispute
    pay_block = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={
            "amount": "500.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        headers=make_headers(buyer),
    )
    assert pay_block.status_code == 409

    # Step 4: Administrator investigates and dismisses complaint
    # Admin records findings notes; admin NEVER acknowledges on behalf of farmer
    resolve_resp = client.post(
        f"/api/v1/admin/payment-complaints/{complaint_id}/resolve",
        json={
            "status": "dismissed",
            "resolution_notes": "Issuing bank verified recall memo was cancelled; funds settled cleanly.",
        },
        headers=make_headers(admin),
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == PAYMENT_COMPLAINT_STATUS_DISMISSED

    # Payment transitions back to payment_recorded (unacknowledged for active settlement)
    # Admin findings do NOT manufacture acknowledgement.
    # CRITICAL AUDIT RULE: original_acknowledged_at MUST REMAIN T1!
    pay_check2 = client.get(f"/api/v1/payments/{payment_id}", headers=make_headers(farmer)).json()
    assert pay_check2["status"] == PAYMENT_STATUS_RECORDED
    assert pay_check2["acknowledged_at"] is None  # Active confirmation is reset pending farmer reaffirmation
    assert pay_check2["original_acknowledged_at"].replace("Z", "") == t1.replace("Z", "")  # HISTORICAL EVIDENCE PRESERVED!
    assert pay_check2["has_historical_acknowledgement"] is True

    # Settlement summary shows pending acknowledgement, NOT fully settled
    sum4 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert sum4["settlement_status"] == "payment_pending_acknowledgement"
    assert Decimal(sum4["total_acknowledged"]) == Decimal("0.00")
    assert Decimal(sum4["unacknowledged_amount"]) == Decimal("1000.00")
    assert Decimal(sum4["total_disputed"]) == Decimal("0.00")

    # Step 5: Selling farmer explicitly reaffirms receipt
    ack2_resp = client.post(
        f"/api/v1/payments/{payment_id}/acknowledge",
        headers=make_headers(farmer),
    )
    assert ack2_resp.status_code == 200
    ack2_data = ack2_resp.json()
    assert ack2_data["status"] == PAYMENT_STATUS_ACKNOWLEDGED
    t2 = ack2_data["acknowledged_at"]
    assert t2 is not None
    # Original acknowledgement remains T1, reaffirmed at T2
    assert ack2_data["original_acknowledged_at"].replace("Z", "") == t1.replace("Z", "")
    assert ack2_data["has_historical_acknowledgement"] is True

    # Final summary: fully settled
    sum5 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert sum5["settlement_status"] == "fully_settled"
    assert Decimal(sum5["total_acknowledged"]) == Decimal("1000.00")
    assert Decimal(sum5["remaining_acknowledged_balance"]) == Decimal("0.00")


# ===========================================================================
# 6. Order Reconciliation Summary
# ===========================================================================

def test_order_payment_summary_lifecycle(client: TestClient, db_session: Session):
    """Verify summary progression: unpaid -> pending ack -> partial -> fully settled."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer, total_amount=Decimal("1000.00"))

    # Initial summary: unpaid
    s0 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert s0["settlement_status"] == "unpaid"
    assert Decimal(s0["remaining_acknowledged_balance"]) == Decimal("1000.00")

    # Buyer records 400.00: pending acknowledgement
    p1_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={"amount": "400.00", "payment_method": "cash", "payment_date": date.today().isoformat()},
        headers=make_headers(buyer),
    )
    p1_id = p1_resp.json()["id"]
    s1 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert s1["settlement_status"] == "payment_pending_acknowledgement"
    assert Decimal(s1["unacknowledged_amount"]) == Decimal("400.00")
    assert Decimal(s1["total_acknowledged"]) == Decimal("0.00")

    # Farmer acknowledges 400.00: partially settled
    client.post(f"/api/v1/payments/{p1_id}/acknowledge", headers=make_headers(farmer))
    s2 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert s2["settlement_status"] == "partially_settled"
    assert Decimal(s2["total_acknowledged"]) == Decimal("400.00")
    assert Decimal(s2["remaining_acknowledged_balance"]) == Decimal("600.00")

    # Buyer records remaining 600.00
    p2_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        json={"amount": "600.00", "payment_method": "bank_transfer", "payment_date": date.today().isoformat()},
        headers=make_headers(buyer),
    )
    p2_id = p2_resp.json()["id"]

    # Farmer acknowledges 600.00: fully settled
    client.post(f"/api/v1/payments/{p2_id}/acknowledge", headers=make_headers(farmer))
    s3 = client.get(f"/api/v1/orders/{order.id}/payments/summary", headers=make_headers(buyer)).json()
    assert s3["settlement_status"] == "fully_settled"
    assert Decimal(s3["total_acknowledged"]) == Decimal("1000.00")
    assert Decimal(s3["remaining_acknowledged_balance"]) == Decimal("0.00")


# ===========================================================================
# 7. File Security & Anti-Traversal Tests
# ===========================================================================

@pytest.mark.parametrize(
    "bad_content,filename",
    [
        (EXE_MAGIC, "malicious.exe"),
        (ELF_MAGIC, "malicious.elf"),
        (JAVA_CLASS, "malicious.class"),
        (SHEBANG_SCRIPT, "malicious.sh"),
        (PLAIN_TEXT, "fake_image.jpg"),
    ],
)
def test_payment_proof_rejects_malicious_files(client: TestClient, db_session: Session, bad_content, filename):
    """Malicious or non-magic executable files are rejected with 400 Bad Request."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    order = seed_order(db_session, farmer, buyer)

    resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        data={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        files={"proof_file": (filename, io.BytesIO(bad_content), "application/octet-stream")},
        headers=make_headers(buyer),
    )
    assert resp.status_code == 400
    detail_str = resp.json()["detail"].lower()
    assert any(term in detail_str for term in ("unsupported", "invalid", "magic bytes", "rejected", "executable"))


def test_payment_proof_download_and_anti_enumeration(client: TestClient, db_session: Session):
    """Participants can download proof; unrelated users receive 404."""
    farmer = seed_farmer(db_session)
    buyer = seed_buyer(db_session)
    unrelated_buyer = seed_buyer(db_session)
    admin = seed_admin(db_session)
    order = seed_order(db_session, farmer, buyer)

    # Buyer records with proof
    pay_resp = client.post(
        f"/api/v1/orders/{order.id}/payments",
        data={
            "amount": "100.00",
            "payment_method": "cash",
            "payment_date": date.today().isoformat(),
        },
        files={"proof_file": ("proof.png", io.BytesIO(PNG_MAGIC), "image/png")},
        headers=make_headers(buyer),
    )
    payment_id = pay_resp.json()["id"]

    # 1. Buyer downloads (200)
    dl_buyer = client.get(f"/api/v1/payments/{payment_id}/proof", headers=make_headers(buyer))
    assert dl_buyer.status_code == 200

    # 2. Farmer downloads (200)
    dl_farmer = client.get(f"/api/v1/payments/{payment_id}/proof", headers=make_headers(farmer))
    assert dl_farmer.status_code == 200

    # 3. Admin downloads (200)
    dl_admin = client.get(f"/api/v1/payments/{payment_id}/proof", headers=make_headers(admin))
    assert dl_admin.status_code == 200

    # 4. Unrelated user downloads (404 anti-enumeration)
    dl_unrel = client.get(f"/api/v1/payments/{payment_id}/proof", headers=make_headers(unrelated_buyer))
    assert dl_unrel.status_code == 404


def test_storage_path_containment_and_traversal_guards(temp_storage: Path):
    """Verify PaymentStorageService strictly rejects path traversal and prefix exploits."""
    storage = PaymentStorageService(base_dir=temp_storage)

    # Sibling directory exploit test:
    # If base is /tmp/storage, /tmp/storage_sibling must be rejected even though str starts with base
    sibling_dir = temp_storage.parent / f"{temp_storage.name}_sibling"
    sibling_dir.mkdir(exist_ok=True)
    fake_file = sibling_dir / "secret.txt"
    fake_file.write_text("leak")

    with pytest.raises(Exception):
        storage.resolve_and_verify_path(str(fake_file))

    # Dot-dot traversal test
    with pytest.raises(Exception):
        storage.resolve_and_verify_path(f"../../../../etc/passwd")

    shutil.rmtree(sibling_dir, ignore_errors=True)
