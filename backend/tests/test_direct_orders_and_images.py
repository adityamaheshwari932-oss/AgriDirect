"""Comprehensive tests for Direct Order Placement, Idempotency, and Order Images (Phases 1 & 2)."""

import io
import os
import shutil
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.listing import ProduceListing, STATUS_ACTIVE, STATUS_CLOSED
from app.models.user import BuyerProfile, FarmerProfile, User
from app.orders.storage import OrderImageStorageService


def _build_test_image(img_format: str = "PNG", size=(20, 20), color="blue") -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", size, color=color)
    im.save(buf, format=img_format)
    return buf.getvalue()


VALID_PNG = _build_test_image("PNG")
VALID_JPEG = _build_test_image("JPEG")


@pytest.fixture
def test_temp_dir():
    temp_dir = tempfile.mkdtemp(prefix="agridirect_test_orders_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sqlite_engine():
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
    TestingSessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session, test_temp_dir):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Point storage service to isolated temporary directory
    isolated_storage = OrderImageStorageService(upload_dir=test_temp_dir)
    with patch("app.orders.service.OrderImageStorageService", return_value=isolated_storage):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def verified_farmer(db_session: Session) -> User:
    farmer = User(
        id=uuid.uuid4(),
        email=f"farmer_{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="test_hash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="9876543210",
    )
    profile = FarmerProfile(
        id=uuid.uuid4(),
        user_id=farmer.id,
        full_name="Verified Farmer Ramesh",
        farm_name="Ramesh Organic Farms",
        farm_location_address="Farm Rd 1",
        city="Nashik",
        state="Maharashtra",
        postal_code="422001",
    )
    db_session.add(farmer)
    db_session.add(profile)
    db_session.commit()
    return farmer


@pytest.fixture
def verified_buyer(db_session: Session) -> User:
    buyer = User(
        id=uuid.uuid4(),
        email=f"buyer_{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="test_hash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="9123456780",
    )
    profile = BuyerProfile(
        id=uuid.uuid4(),
        user_id=buyer.id,
        business_name="Fresh Mart Retailers",
        contact_person_name="Anil Kumar",
        business_type="retailer",
        delivery_receiving_address="Market Yard 4",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db_session.add(buyer)
    db_session.add(profile)
    db_session.commit()
    return buyer


@pytest.fixture
def other_buyer(db_session: Session) -> User:
    buyer = User(
        id=uuid.uuid4(),
        email=f"other_buyer_{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="test_hash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="9123456789",
    )
    profile = BuyerProfile(
        id=uuid.uuid4(),
        user_id=buyer.id,
        business_name="Other Buyer Wholesale",
        contact_person_name="Sunil Sharma",
        business_type="wholesaler",
        delivery_receiving_address="Wholesale Market 12",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db_session.add(buyer)
    db_session.add(profile)
    db_session.commit()
    return buyer


@pytest.fixture
def active_listing(db_session: Session, verified_farmer: User) -> ProduceListing:
    listing = ProduceListing(
        id=uuid.uuid4(),
        farmer_id=verified_farmer.id,
        title="Premium Alphonso Mangoes Grade A",
        product_name="Alphonso Mango",
        quality_grade="Grade A",
        initial_quantity=Decimal("500.00"),
        available_quantity=Decimal("500.00"),
        unit="kg",
        price_per_unit=Decimal("150.00"),
        status=STATUS_ACTIVE,
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        location_city="Ratnagiri",
        location_state="Maharashtra",
    )
    db_session.add(listing)
    db_session.commit()
    return listing


def test_direct_order_creation_success(
    client: TestClient,
    verified_buyer: User,
    active_listing: ProduceListing,
    db_session: Session,
):
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    payload = {
        "listing_id": str(active_listing.id),
        "quantity": 100.0,
        "delivery_destination_address": "Dock 3, Pune",
        "delivery_notes": "Handle with care",
        "idempotency_key": "idem-key-001",
    }
    resp = client.post(
        "/api/v1/orders",
        json=payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["order_number"].startswith("ORD-")
    assert Decimal(str(data["total_amount"])) == Decimal("15000.00")
    assert data["status"] == "pending"
    assert data["buyer_id"] == str(verified_buyer.id)
    assert len(data["items"]) == 1
    assert Decimal(str(data["items"][0]["quantity"])) == Decimal("100.00")

    # Verify listing quantity decremented from 500 to 400
    db_session.refresh(active_listing)
    assert active_listing.available_quantity == Decimal("400.00")


def test_direct_order_idempotency_prevents_duplicate_orders(
    client: TestClient,
    verified_buyer: User,
    active_listing: ProduceListing,
    db_session: Session,
):
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    payload = {
        "listing_id": str(active_listing.id),
        "quantity": 50.0,
        "idempotency_key": "unique-idempotency-token-12345",
    }

    # First request
    resp1 = client.post(
        "/api/v1/orders",
        json=payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp1.status_code == 201
    order1_id = resp1.json()["id"]

    # Repeated request with same idempotency_key
    resp2 = client.post(
        "/api/v1/orders",
        json=payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp2.status_code in (200, 201)
    assert resp2.json()["id"] == order1_id

    # Stock must only have decremented ONCE (500 - 50 = 450, NOT 400)
    db_session.refresh(active_listing)
    assert active_listing.available_quantity == Decimal("450.00")


def test_direct_order_insufficient_quantity(
    client: TestClient,
    verified_buyer: User,
    active_listing: ProduceListing,
):
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    payload = {
        "listing_id": str(active_listing.id),
        "quantity": 600.0,  # exceeds 500.00 available
    }
    resp = client.post(
        "/api/v1/orders",
        json=payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 400
    assert "exceeds available stock" in resp.json()["detail"]


def test_direct_order_farmer_cannot_buy_own_listing(
    client: TestClient,
    verified_farmer: User,
    active_listing: ProduceListing,
):
    farmer_token = create_access_token(data={"sub": str(verified_farmer.id)})
    payload = {
        "listing_id": str(active_listing.id),
        "quantity": 10.0,
    }
    resp = client.post(
        "/api/v1/orders",
        json=payload,
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert resp.status_code == 403 or resp.status_code == 400


def test_order_images_upload_and_streaming(
    client: TestClient,
    verified_buyer: User,
    verified_farmer: User,
    other_buyer: User,
    active_listing: ProduceListing,
):
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    farmer_token = create_access_token(data={"sub": str(verified_farmer.id)})
    other_token = create_access_token(data={"sub": str(other_buyer.id)})

    # Create order first
    order_resp = client.post(
        "/api/v1/orders",
        json={"listing_id": str(active_listing.id), "quantity": 25.0},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # Upload single JPEG image as buyer
    upload_resp = client.post(
        f"/api/v1/orders/{order_id}/images",
        files={"file": ("receipt_spec.jpg", VALID_JPEG, "image/jpeg")},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    img_list = upload_resp.json()
    assert len(img_list) == 1
    image_id = img_list[0]["id"]
    assert img_list[0]["mime_type"] == "image/jpeg"

    # Stream as buyer (participant): 200 OK
    stream_resp_buyer = client.get(
        f"/api/v1/orders/{order_id}/images/{image_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert stream_resp_buyer.status_code == 200
    assert stream_resp_buyer.content == VALID_JPEG

    # Stream as farmer (counterparty): 200 OK
    stream_resp_farmer = client.get(
        f"/api/v1/orders/{order_id}/images/{image_id}",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert stream_resp_farmer.status_code == 200

    # Stream as unrelated third-party buyer: 403 Forbidden
    stream_resp_other = client.get(
        f"/api/v1/orders/{order_id}/images/{image_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert stream_resp_other.status_code == 403


def test_order_images_validation_rejects_non_image(
    client: TestClient,
    verified_buyer: User,
    active_listing: ProduceListing,
):
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    order_resp = client.post(
        "/api/v1/orders",
        json={"listing_id": str(active_listing.id), "quantity": 10.0},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = order_resp.json()["id"]

    # Upload text file disguised as image
    fake_img = b"Not a real image file content"
    resp = client.post(
        f"/api/v1/orders/{order_id}/images",
        files={"file": ("malicious.jpg", fake_img, "image/jpeg")},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 422


def test_order_images_batch_rollback_cleanup_on_failure(
    client: TestClient,
    verified_buyer: User,
    active_listing: ProduceListing,
    test_temp_dir: str,
    db_session: Session,
):
    """If one image in a multi-image batch fails, any saved files in that batch must be deleted."""
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    order_resp = client.post(
        "/api/v1/orders",
        json={"listing_id": str(active_listing.id), "quantity": 10.0},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = order_resp.json()["id"]

    # Multi-file batch where 1st is valid PNG, 2nd is invalid text content
    files = [
        ("files", ("valid.png", VALID_PNG, "image/png")),
        ("files", ("corrupt.png", b"corrupted payload", "image/png")),
    ]

    resp = client.post(
        f"/api/v1/orders/{order_id}/images",
        files=files,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 422

    # Verify no orphaned files remain in test_temp_dir
    files_on_disk = list(Path(test_temp_dir).glob("*"))
    assert len(files_on_disk) == 0, f"Orphaned files remained after failed batch: {files_on_disk}"


def test_order_images_batch_failure_preserves_prior_successful_uploads(
    client: TestClient,
    verified_buyer: User,
    active_listing: ProduceListing,
    test_temp_dir: str,
):
    """Failed batch must never delete files belonging to earlier successful uploads."""
    buyer_token = create_access_token(data={"sub": str(verified_buyer.id)})
    order_resp = client.post(
        "/api/v1/orders",
        json={"listing_id": str(active_listing.id), "quantity": 10.0},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = order_resp.json()["id"]

    # Initial successful upload
    resp1 = client.post(
        f"/api/v1/orders/{order_id}/images",
        files={"file": ("first_valid.png", VALID_PNG, "image/png")},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp1.status_code == 201
    assert len(list(Path(test_temp_dir).glob("*"))) == 1

    # Second batch with 1 valid and 1 corrupt
    files = [
        ("files", ("second_valid.png", VALID_PNG, "image/png")),
        ("files", ("corrupt.png", b"bad image content", "image/png")),
    ]
    resp2 = client.post(
        f"/api/v1/orders/{order_id}/images",
        files=files,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp2.status_code == 422

    # The original file from batch 1 must still exist on disk
    files_on_disk = list(Path(test_temp_dir).glob("*"))
    assert len(files_on_disk) == 1, "Prior successful image was improperly deleted"


def test_idempotency_collision_recovery_on_integrity_error(
    db_session: Session,
    verified_buyer: User,
    active_listing: ProduceListing,
):
    """Simulate a concurrent unique constraint collision on idempotency_key."""
    from app.orders.service import OrderService
    from app.orders.schemas import OrderCreateRequest
    from sqlalchemy.exc import IntegrityError

    service = OrderService(db_session)
    idem_key = f"concurrent-test-{uuid.uuid4()}"
    payload = OrderCreateRequest(
        listing_id=active_listing.id,
        quantity=Decimal("15.00"),
        idempotency_key=idem_key,
    )

    # First creation succeeds normally
    order1 = service.create_direct_order(verified_buyer, payload)
    assert order1.id is not None

    # Now mock db.flush to simulate a race condition where IntegrityError is raised
    # during concurrent execution of the second request
    with patch.object(db_session, "flush", side_effect=IntegrityError("duplicate key", params=None, orig=Exception("uq_idx"))):
        # Must catch IntegrityError, rollback, and return the already committed order
        order2 = service.create_direct_order(verified_buyer, payload)
        assert order2.id == order1.id


def test_unrelated_integrity_error_is_reraised(
    db_session: Session,
    verified_buyer: User,
    active_listing: ProduceListing,
):
    """An IntegrityError NOT caused by an existing idempotency key must be re-raised."""
    from app.orders.service import OrderService
    from app.orders.schemas import OrderCreateRequest
    from sqlalchemy.exc import IntegrityError

    service = OrderService(db_session)
    payload = OrderCreateRequest(
        listing_id=active_listing.id,
        quantity=Decimal("5.00"),
        idempotency_key=f"unrelated-{uuid.uuid4()}",
    )

    with patch.object(db_session, "flush", side_effect=IntegrityError("foreign key failure", params=None, orig=Exception("fk"))):
        with pytest.raises(IntegrityError):
            service.create_direct_order(verified_buyer, payload)

