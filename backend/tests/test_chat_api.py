"""Unit and API integration tests for AgriDirect Module 5 (Messaging and Communication System).

Covers all 12 functional requirements:
- M5-01: Conversation Creation
- M5-02: Conversation Management
- M5-03: Text Messaging
- M5-04: Message History
- M5-05: Image Attachments
- M5-06: Document Attachments
- M5-07: Contact Information Sharing
- M5-08: Message Status Tracking
- M5-09: Message Permissions & Anti-Enumeration
- M5-10: Order-Linked Conversations
- M5-11: Attachment Validation & Security
- M5-12: Restrictions & Lifecycle Management
"""

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import (
    ATTACHMENT_TYPE_DOCUMENT,
    ATTACHMENT_TYPE_IMAGE,
    CONTACT_REQUEST_STATUS_APPROVED,
    CONTACT_REQUEST_STATUS_PENDING,
    CONTACT_REQUEST_STATUS_REJECTED,
    CONTEXT_TYPE_LISTING,
    CONTEXT_TYPE_ORDER,
    CONTEXT_TYPE_REQUIREMENT,
    MESSAGE_STATUS_DELIVERED,
    MESSAGE_STATUS_READ,
    MESSAGE_STATUS_SENT,
    ContactShareRequest,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)
from app.models.listing import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    ProduceCategory,
    ProduceListing,
)
from app.models.offer import (
    OFFER_STATUS_ACCEPTED,
    Offer,
    OfferItem,
)
from app.models.order import (
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    Order,
    OrderItem,
)
from app.models.requirement import (
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    BuyerRequirement,
)
from app.models.user import BuyerProfile, FarmerProfile, User


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
def client(sqlite_engine) -> TestClient:
    """FastAPI TestClient with overridden get_db."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
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
        full_name="Rajesh Patil",
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
        business_name="FreshMart Foods Pvt Ltd",
        business_type="retailer",
        contact_person_name="Anita Sharma",
        delivery_receiving_address="Shop 4, APMC Market, Navi Mumbai",
        city="Navi Mumbai",
        state="Maharashtra",
        postal_code="400703",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_listing(db: Session, farmer: User, status: str = STATUS_ACTIVE) -> ProduceListing:
    """Create an active produce listing."""
    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg-{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    now_utc = datetime.now(timezone.utc)
    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Nashik Red Onions",
        title="Fresh Red Onions",
        initial_quantity=Decimal("500.000"),
        available_quantity=Decimal("500.000"),
        unit="kg",
        price_per_unit=Decimal("35.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=now_utc + timedelta(days=14),
        status=status,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def seed_requirement(db: Session, buyer: User, status: str = REQUIREMENT_STATUS_ACTIVE) -> BuyerRequirement:
    """Create a buyer requirement."""
    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg-{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    req = BuyerRequirement(
        buyer_id=buyer.id,
        category_id=cat.id,
        product_name="Potatoes",
        title="Fresh Potatoes Required",
        required_quantity=Decimal("300.000"),
        remaining_quantity=Decimal("300.000"),
        unit="kg",
        price_condition="negotiable",
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=10),
        status=status,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def seed_order(db: Session, farmer: User, buyer: User, status: str = ORDER_STATUS_CONFIRMED) -> Order:
    """Create an order with an offer and an item."""
    conv = db.query(Conversation).filter(
        Conversation.farmer_id == farmer.id,
        Conversation.buyer_id == buyer.id,
    ).first()
    if not conv:
        conv = Conversation(
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            initial_context_type="general",
        )
        db.add(conv)
        db.flush()

    offer = Offer(
        offer_number=f"OFF-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=Decimal("1500.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db.add(offer)
    db.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        source_offer_id=offer.id,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("1500.00"),
        status=status,
        delivery_status=DELIVERY_STATUS_NOT_ARRANGED,
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        product_name="Nashik Red Onions",
        quantity=Decimal("50.000"),
        unit="kg",
        unit_price=Decimal("30.00"),
        subtotal=Decimal("1500.00"),
        status="confirmed",
    )
    db.add(item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# M5-01: Conversation Creation Tests
# ===========================================================================

class TestConversationCreation:
    """Verify conversation creation, context validation, role eligibility, and deduplication."""

    def test_buyer_creates_conversation_with_listing_context(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"listing_id": str(listing.id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["farmer_id"] == str(farmer.id)
        assert data["buyer_id"] == str(buyer.id)
        assert data["initial_context_type"] == CONTEXT_TYPE_LISTING
        assert data["initial_context_id"] == str(listing.id)

    def test_verified_farmer_creates_conversation_with_requirement_context(self, client, db_session):
        farmer = seed_farmer(db_session, verified=True)
        buyer = seed_buyer(db_session)
        req = seed_requirement(db_session, buyer)

        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"requirement_id": str(req.id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["farmer_id"] == str(farmer.id)
        assert data["buyer_id"] == str(buyer.id)
        assert data["initial_context_type"] == CONTEXT_TYPE_REQUIREMENT

    def test_unverified_farmer_cannot_respond_to_requirement(self, client, db_session):
        farmer = seed_farmer(db_session, verified=False)
        buyer = seed_buyer(db_session)
        req = seed_requirement(db_session, buyer)

        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"requirement_id": str(req.id)},
        )
        assert resp.status_code == 403
        assert "verified farmers" in resp.json()["detail"].lower()

    def test_self_conversation_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        listing = seed_listing(db_session, farmer)

        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"listing_id": str(listing.id), "target_user_id": str(farmer.id)},
        )
        assert resp.status_code == 400
        assert "themselves" in resp.json()["detail"].lower()

    def test_buyer_without_context_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)

        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"target_user_id": str(farmer.id)},
        )
        assert resp.status_code == 400
        assert "marketplace context" in resp.json()["detail"].lower()

    def test_nonexistent_listing_returns_404(self, client, db_session):
        buyer = seed_buyer(db_session)
        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"listing_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_nonexistent_requirement_returns_404(self, client, db_session):
        farmer = seed_farmer(db_session, verified=True)
        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"requirement_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_nonexistent_order_returns_404(self, client, db_session):
        farmer = seed_farmer(db_session)
        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"order_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_unrelated_user_cannot_access_order_context(self, client, db_session):
        f1 = seed_farmer(db_session)
        b1 = seed_buyer(db_session)
        order = seed_order(db_session, f1, b1)

        unrelated = seed_buyer(db_session)
        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(unrelated),
            json={"order_id": str(order.id)},
        )
        # Anti-enumeration check
        assert resp.status_code == 404

    def test_idempotent_conversation_creation_returns_existing(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        resp1 = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"listing_id": str(listing.id)},
        )
        assert resp1.status_code == 201
        conv_id = resp1.json()["id"]

        # Call again: should return 200 with the exact same thread
        resp2 = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"listing_id": str(listing.id)},
        )
        assert resp2.status_code == 200
        assert resp2.json()["id"] == conv_id


# ===========================================================================
# M5-02: Conversation Management Tests
# ===========================================================================

class TestConversationManagement:
    """Verify conversation listing, pagination, unread counts, and privacy disclosure."""

    def test_list_conversations_only_returns_own_threads(self, client, db_session):
        f1 = seed_farmer(db_session)
        b1 = seed_buyer(db_session)
        f2 = seed_farmer(db_session)
        b2 = seed_buyer(db_session)

        l1 = seed_listing(db_session, f1)
        l2 = seed_listing(db_session, f2)

        client.post("/api/v1/conversations", headers=make_headers(b1), json={"listing_id": str(l1.id)})
        client.post("/api/v1/conversations", headers=make_headers(b2), json={"listing_id": str(l2.id)})

        # b1 should only see thread with f1
        resp = client.get("/api/v1/conversations", headers=make_headers(b1))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["farmer_id"] == str(f1.id)

    def test_conversation_details_participant_and_anti_enumeration(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        other_user = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        create_resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"listing_id": str(listing.id)},
        )
        conv_id = create_resp.json()["id"]

        # Authorized participant view
        resp_auth = client.get(f"/api/v1/conversations/{conv_id}", headers=make_headers(farmer))
        assert resp_auth.status_code == 200
        assert resp_auth.json()["id"] == conv_id

        # Unauthorized view returns 404 (anti-enumeration)
        resp_unauth = client.get(f"/api/v1/conversations/{conv_id}", headers=make_headers(other_user))
        assert resp_unauth.status_code == 404

    def test_contact_details_hidden_before_consent(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        create_resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"listing_id": str(listing.id)},
        )
        conv_id = create_resp.json()["id"]

        detail_resp = client.get(f"/api/v1/conversations/{conv_id}", headers=make_headers(buyer))
        assert detail_resp.status_code == 200
        other_part = detail_resp.json()["other_participant"]
        assert other_part["name"] == "Rajesh Patil"
        # Privacy check: email and phone MUST be None before consent
        assert other_part["email"] is None
        assert other_part["phone_number"] is None


# ===========================================================================
# M5-03 & M5-04: Text Messaging & Message History Tests
# ===========================================================================

class TestTextMessagingAndHistory:
    """Verify message creation, validation, unicode text, ordering, and pagination."""

    def test_send_valid_text_message(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        msg_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Hello, is the onion stock ready for immediate dispatch?"},
        )
        assert msg_resp.status_code == 201
        data = msg_resp.json()
        assert data["content"] == "Hello, is the onion stock ready for immediate dispatch?"
        assert data["sender_id"] == str(buyer.id)
        assert data["delivery_status"] == MESSAGE_STATUS_SENT
        assert data["is_read"] is False

    def test_send_empty_and_whitespace_message_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        # Empty string
        resp1 = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": ""},
        )
        assert resp1.status_code == 422

        # Whitespace only
        resp2 = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "   \n\t   "},
        )
        assert resp2.status_code == 422

    def test_send_excessive_length_message_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        long_text = "A" * 5001
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": long_text},
        )
        assert resp.status_code == 422

    def test_send_multilingual_unicode_messages(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        # Hindi, Marathi, Telugu, Tamil, and Emojis
        multilingual_samples = [
            "नमस्कार! कांद्याचा भाव काय आहे? 🧅🌾",  # Marathi
            "नमस्ते, हमें 200 किलो अच्छी गुणवत्ता वाले प्याज चाहिए।",  # Hindi
            "నమస్కారం, సరుకు ఎప్పుడు పంపుతారు?",  # Telugu
            "வணக்கம், தரமான வெங்காயம் கிடைக்குமா?",  # Tamil
        ]

        for text_sample in multilingual_samples:
            resp = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=make_headers(buyer),
                json={"content": text_sample},
            )
            assert resp.status_code == 201
            assert resp.json()["content"] == text_sample

    def test_message_history_ordering_and_pagination(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        for i in range(5):
            client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=make_headers(buyer),
                json={"content": f"Message {i+1}"},
            )

        resp = client.get(f"/api/v1/conversations/{conv_id}/messages?limit=3&order=asc", headers=make_headers(farmer))
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3
        assert items[0]["content"] == "Message 1"
        assert items[1]["content"] == "Message 2"
        assert items[2]["content"] == "Message 3"

        # Cursor pagination: get messages after item 3
        after_id = items[2]["id"]
        resp_after = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=3&after_id={after_id}&order=asc",
            headers=make_headers(farmer),
        )
        assert resp_after.status_code == 200
        items_after = resp_after.json()
        assert len(items_after) == 2
        assert items_after[0]["content"] == "Message 4"
        assert items_after[1]["content"] == "Message 5"


# ===========================================================================
# M5-05, M5-06, M5-11: Attachments & Security Tests
# ===========================================================================

class TestAttachmentsAndSecurity:
    """Verify image/document validation, signatures, executable rejection, and secure download."""

    def test_upload_valid_image_jpeg(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Here is the sample photo"},
        )
        msg_id = m_resp.json()["id"]

        # Valid JPEG magic bytes: \xff\xd8\xff
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
        files = {"file": ("sample.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}

        att_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(buyer),
            files=files,
        )
        assert att_resp.status_code == 201
        data = att_resp.json()
        assert data["file_name"] == "sample.jpg"
        assert data["file_mime_type"] == "image/jpeg"
        assert data["attachment_type"] == ATTACHMENT_TYPE_IMAGE

    def test_upload_valid_document_pdf(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(farmer),
            json={"content": "Here is the crop certificate"},
        )
        msg_id = m_resp.json()["id"]

        # Valid PDF magic bytes: %PDF-
        pdf_bytes = b"%PDF-1.4\n" + b"Sample PDF body content" * 20
        files = {"file": ("certificate.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

        att_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(farmer),
            files=files,
        )
        assert att_resp.status_code == 201
        data = att_resp.json()
        assert data["file_name"] == "certificate.pdf"
        assert data["file_mime_type"] == "application/pdf"
        assert data["attachment_type"] == ATTACHMENT_TYPE_DOCUMENT

    def test_upload_disallowed_extension_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Check this file"},
        )
        msg_id = m_resp.json()["id"]

        bad_bytes = b"echo hello"
        files = {"file": ("malicious.sh", io.BytesIO(bad_bytes), "text/plain")}

        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(buyer),
            files=files,
        )
        assert resp.status_code == 422
        assert "unsupported file extension" in resp.json()["detail"].lower()

    def test_upload_executable_magic_bytes_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Disguised exe"},
        )
        msg_id = m_resp.json()["id"]

        # DOS MZ header masquerading as a JPEG
        fake_jpeg = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 50
        files = {"file": ("payload.jpg", io.BytesIO(fake_jpeg), "image/jpeg")}

        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(buyer),
            files=files,
        )
        assert resp.status_code == 422
        assert "executable" in resp.json()["detail"].lower()

    def test_upload_fake_signature_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Corrupt file"},
        )
        msg_id = m_resp.json()["id"]

        corrupt_png = b"Not a real PNG header content here"
        files = {"file": ("photo.png", io.BytesIO(corrupt_png), "image/png")}

        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(buyer),
            files=files,
        )
        assert resp.status_code == 422
        assert "invalid file signature" in resp.json()["detail"].lower()

    def test_upload_empty_file_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Empty"},
        )
        msg_id = m_resp.json()["id"]

        files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(buyer),
            files=files,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_download_attachment_authorized_and_anti_enumeration(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        other_user = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Photo"},
        )
        msg_id = m_resp.json()["id"]

        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x01" * 80
        files = {"file": ("sample.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
        att_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
            headers=make_headers(buyer),
            files=files,
        )
        att_id = att_resp.json()["id"]

        # Authorized download by recipient (farmer)
        dl_resp = client.get(f"/api/v1/attachments/{att_id}", headers=make_headers(farmer))
        assert dl_resp.status_code == 200
        assert dl_resp.content == jpeg_bytes

        # Unauthorized download by third party returns 404 (anti-enumeration)
        dl_unauth = client.get(f"/api/v1/attachments/{att_id}", headers=make_headers(other_user))
        assert dl_unauth.status_code == 404

    def test_send_message_with_attachment_convenience_endpoint(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        pdf_bytes = b"%PDF-1.4\n" + b"Test PDF" * 10
        files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"content": "Attached document"}

        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/with-attachment",
            headers=make_headers(buyer),
            data=data,
            files=files,
        )
        assert resp.status_code == 201
        res = resp.json()
        assert res["content"] == "Attached document"
        assert len(res["attachments"]) == 1
        assert res["attachments"][0]["file_name"] == "doc.pdf"

    def test_storage_rejects_sibling_directory_prefix_match(self, tmp_path):
        """Regression test: ChatStorageService must reject paths in a sibling directory
        whose name shares the allowed directory's prefix (string-prefix vulnerability)."""
        from app.chat.storage import ChatStorageService
        from fastapi import HTTPException

        allowed_dir = tmp_path / "chat"
        allowed_dir.mkdir()
        sibling_dir = tmp_path / "chat_sibling"
        sibling_dir.mkdir()
        target_file = sibling_dir / "secret.txt"
        target_file.write_text("confidential")

        storage = ChatStorageService(upload_dir=str(allowed_dir))

        # Attempt to access file in sibling directory via relative path traversal
        with pytest.raises(HTTPException) as exc_info:
            storage.get_file_path("../chat_sibling/secret.txt")

        assert exc_info.value.status_code == 400
        assert "invalid file path detected" in exc_info.value.detail.lower()


# ===========================================================================
# M5-07: Contact Information Sharing Consent Tests
# ===========================================================================

class TestContactSharingConsent:
    """Verify mutual consent workflow for disclosing phone numbers and emails."""

    def test_contact_sharing_request_and_approval_flow(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        # Initially, contacts endpoint returns 403 Forbidden
        c_check1 = client.get(f"/api/v1/conversations/{conv_id}/contacts", headers=make_headers(buyer))
        assert c_check1.status_code == 403

        # Buyer initiates request
        req_resp = client.post(
            f"/api/v1/conversations/{conv_id}/contact-requests",
            headers=make_headers(buyer),
            json={"notes": "Please share phone for dispatch coordination"},
        )
        assert req_resp.status_code == 201
        req_id = req_resp.json()["id"]
        assert req_resp.json()["status"] == CONTACT_REQUEST_STATUS_PENDING

        # Duplicate pending request rejected
        dup_resp = client.post(
            f"/api/v1/conversations/{conv_id}/contact-requests",
            headers=make_headers(buyer),
            json={"notes": "Duplicate"},
        )
        assert dup_resp.status_code == 400

        # Requester cannot self-approve
        self_app = client.post(f"/api/v1/contact-requests/{req_id}/approve", headers=make_headers(buyer))
        assert self_app.status_code == 403

        # Recipient (farmer) approves
        app_resp = client.post(f"/api/v1/contact-requests/{req_id}/approve", headers=make_headers(farmer))
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == CONTACT_REQUEST_STATUS_APPROVED

        # Now both can view counterparty contact details
        contacts_buyer = client.get(f"/api/v1/conversations/{conv_id}/contacts", headers=make_headers(buyer))
        assert contacts_buyer.status_code == 200
        b_data = contacts_buyer.json()
        assert b_data["email"] == farmer.email
        assert b_data["phone_number"] == farmer.phone_number

        contacts_farmer = client.get(f"/api/v1/conversations/{conv_id}/contacts", headers=make_headers(farmer))
        assert contacts_farmer.status_code == 200
        f_data = contacts_farmer.json()
        assert f_data["email"] == buyer.email
        assert f_data["phone_number"] == buyer.phone_number

    def test_contact_sharing_rejection_keeps_contacts_hidden(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        req_resp = client.post(
            f"/api/v1/conversations/{conv_id}/contact-requests",
            headers=make_headers(buyer),
            json={"notes": "Can we talk?"},
        )
        req_id = req_resp.json()["id"]

        # Recipient rejects
        rej_resp = client.post(f"/api/v1/contact-requests/{req_id}/reject", headers=make_headers(farmer))
        assert rej_resp.status_code == 200
        assert rej_resp.json()["status"] == CONTACT_REQUEST_STATUS_REJECTED

        # Contacts remain hidden
        c_check = client.get(f"/api/v1/conversations/{conv_id}/contacts", headers=make_headers(buyer))
        assert c_check.status_code == 403

    def test_contact_sharing_third_party_and_suspended_access_rejected(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        third_party = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        req_resp = client.post(
            f"/api/v1/conversations/{conv_id}/contact-requests",
            headers=make_headers(buyer),
            json={"notes": "Coordination"},
        )
        assert req_resp.status_code == 201
        req_id = req_resp.json()["id"]

        # 1. Third party cannot approve request (403)
        tp_app = client.post(f"/api/v1/contact-requests/{req_id}/approve", headers=make_headers(third_party))
        assert tp_app.status_code == 403

        # 2. Third party cannot list contact requests for this conversation (404 anti-enumeration)
        tp_list = client.get(f"/api/v1/conversations/{conv_id}/contact-requests", headers=make_headers(third_party))
        assert tp_list.status_code == 404

        # 3. Third party cannot get contacts for this conversation (404 anti-enumeration)
        tp_contacts = client.get(f"/api/v1/conversations/{conv_id}/contacts", headers=make_headers(third_party))
        assert tp_contacts.status_code == 404

        # 4. Suspended user cannot initiate contact request (403)
        suspended_user = seed_buyer(db_session, active=False)
        susp_req = client.post(
            f"/api/v1/conversations/{conv_id}/contact-requests",
            headers=make_headers(suspended_user),
            json={"notes": "Suspended"},
        )
        assert susp_req.status_code == 403


# ===========================================================================
# M5-08: Message Status Tracking Tests
# ===========================================================================

class TestMessageStatusTracking:
    """Verify Sent, Delivered, and Read status transitions and unread counts."""

    def test_message_lifecycle_sent_delivered_read(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        # Buyer sends message
        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Check quality"},
        )
        msg_id = m_resp.json()["id"]
        assert m_resp.json()["delivery_status"] == MESSAGE_STATUS_SENT

        # Farmer checks unread count: should be 1
        unread_resp = client.get(f"/api/v1/conversations/{conv_id}/unread-count", headers=make_headers(farmer))
        assert unread_resp.json()["unread_count"] == 1

        # Farmer fetches messages: triggers transition to DELIVERED
        history_resp = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=make_headers(farmer))
        assert history_resp.status_code == 200
        msgs = history_resp.json()
        assert msgs[0]["delivery_status"] == MESSAGE_STATUS_DELIVERED

        # Farmer explicitly marks conversation as READ
        read_resp = client.post(f"/api/v1/conversations/{conv_id}/read", headers=make_headers(farmer))
        assert read_resp.status_code == 200
        assert read_resp.json()["marked_read_count"] == 1

        # Unread count now 0 for farmer
        unread_now = client.get(f"/api/v1/conversations/{conv_id}/unread-count", headers=make_headers(farmer))
        assert unread_now.json()["unread_count"] == 0

        # Message status is now READ
        history_after = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=make_headers(farmer))
        assert history_after.json()[0]["delivery_status"] == MESSAGE_STATUS_READ
        assert history_after.json()[0]["is_read"] is True

    def test_sender_cannot_mark_own_message_read(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Buyer message"},
        )

        # Buyer attempts to call read on their own message: marked_read_count should be 0
        read_resp = client.post(f"/api/v1/conversations/{conv_id}/read", headers=make_headers(buyer))
        assert read_resp.status_code == 200
        assert read_resp.json()["marked_read_count"] == 0


# ===========================================================================
# M5-10: Order-Linked Conversations Tests
# ===========================================================================

class TestOrderLinkedConversations:
    """Verify order context integration, lifecycle preservation, and isolation from order mutations."""

    def test_order_linked_conversation_and_messaging(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        order = seed_order(db_session, farmer, buyer)

        # Create order-linked conversation
        c_resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"order_id": str(order.id)},
        )
        assert c_resp.status_code in (200, 201)
        conv_id = c_resp.json()["id"]
        assert c_resp.json()["order_id"] == str(order.id)

        # Send message linked to order
        m_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(farmer),
            json={"content": "Delivery vehicle scheduled for tomorrow morning.", "order_id": str(order.id)},
        )
        assert m_resp.status_code == 201
        assert m_resp.json()["order_id"] == str(order.id)

    def test_messaging_preserved_after_order_completion_and_cancellation(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        order = seed_order(db_session, farmer, buyer, status=ORDER_STATUS_CONFIRMED)

        c_resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"order_id": str(order.id)},
        )
        conv_id = c_resp.json()["id"]

        # Cancel the order
        order.status = ORDER_STATUS_CANCELLED
        db_session.commit()

        # Communication thread is NOT deleted or locked
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Understood the cancellation, thank you."},
        )
        assert resp.status_code == 201

        # History remains accessible
        hist = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=make_headers(farmer))
        assert hist.status_code == 200
        assert len(hist.json()) >= 1

    def test_messaging_does_not_mutate_order_status(self, client, db_session):
        farmer = seed_farmer(db_session)
        buyer = seed_buyer(db_session)
        order = seed_order(db_session, farmer, buyer, status=ORDER_STATUS_CONFIRMED)

        c_resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(buyer),
            json={"order_id": str(order.id)},
        )
        conv_id = c_resp.json()["id"]

        client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Can we cancel this order?"},
        )

        db_session.refresh(order)
        # Order status must remain confirmed
        assert order.status == ORDER_STATUS_CONFIRMED


# ===========================================================================
# M5-12: Restrictions & Lifecycle Management Tests
# ===========================================================================

class TestRestrictionsAndLifecycle:
    """Verify account restrictions, anti-enumeration, and access guards."""

    def test_suspended_account_cannot_initiate_conversation(self, client, db_session):
        farmer = seed_farmer(db_session, active=False)
        buyer = seed_buyer(db_session)
        req = seed_requirement(db_session, buyer)

        resp = client.post(
            "/api/v1/conversations",
            headers=make_headers(farmer),
            json={"requirement_id": str(req.id)},
        )
        assert resp.status_code == 403
        assert "inactive or suspended" in resp.json()["detail"].lower()

    def test_suspended_account_cannot_send_messages(self, client, db_session):
        farmer = seed_farmer(db_session, active=True)
        buyer = seed_buyer(db_session, active=True)
        listing = seed_listing(db_session, farmer)

        c_resp = client.post("/api/v1/conversations", headers=make_headers(buyer), json={"listing_id": str(listing.id)})
        conv_id = c_resp.json()["id"]

        # Suspend buyer account
        buyer.account_status = "suspended"
        db_session.commit()

        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_headers(buyer),
            json={"content": "Should be blocked"},
        )
        assert resp.status_code == 403
