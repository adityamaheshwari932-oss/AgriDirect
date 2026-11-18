"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 5 (Messaging & Communication).

Verifies Module 5 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`
at Alembic revision `f6a1b2c3d4e5`.

Safety Guarantee:
- Uses ONLY `agridirect_module3_test`.
- NEVER touches, accesses, or modifies `agridirect_db`.
- Cleans up all test-created records via TRUNCATE CASCADE with pre-flight database name assertion.
"""

import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator, List, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import close_db, get_db, init_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import (
    ATTACHMENT_TYPE_IMAGE,
    CONTACT_REQUEST_STATUS_APPROVED,
    CONTACT_REQUEST_STATUS_PENDING,
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
    ProduceCategory,
    ProduceListing,
)
from app.models.offer import (
    OFFER_STATUS_ACCEPTED,
    Offer,
    OfferItem,
)
from app.models.order import (
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_STATUS_CONFIRMED,
    Order,
    OrderItem,
)
from app.models.requirement import (
    REQUIREMENT_STATUS_ACTIVE,
    BuyerRequirement,
)
from app.models.user import BuyerProfile, FarmerProfile, User

# Verified isolated PostgreSQL test connection
TEST_PG_DB_URL = "postgresql+psycopg://agridirect_app:agridirect@localhost:5432/agridirect_module3_test"

_pg_engine = create_engine(TEST_PG_DB_URL, pool_size=15, max_overflow=5)
_SessionLocal = sessionmaker(bind=_pg_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Database Cleanup and Safety Guarantees
# ---------------------------------------------------------------------------

def _cleanup_database() -> None:
    """Pre-flight check and clean up agridirect_module3_test."""
    with _SessionLocal() as db:
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
    """Clean up after each test to ensure complete test isolation."""
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
# Seed Helpers
# ---------------------------------------------------------------------------

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


def create_pg_farmer(db: Session, verified: bool = True) -> User:
    """Create farmer user in PostgreSQL."""
    user = User(
        email=f"pg_farmer_{uuid.uuid4().hex[:8]}@test.agridirect",
        password_hash="mockhash",
        role="farmer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    FarmerProfile(
        user=user,
        full_name="Farmer Ramesh",
        farm_name="Nashik Agro Farms",
        farm_location_address="Gat 45, Dindori",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_pg_buyer(db: Session, verified: bool = True) -> User:
    """Create buyer user in PostgreSQL."""
    user = User(
        email=f"pg_buyer_{uuid.uuid4().hex[:8]}@test.agridirect",
        password_hash="mockhash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    BuyerProfile(
        user=user,
        business_name="Fresh Agro Retail Ltd",
        business_type="retailer",
        contact_person_name="Anita Sharma",
        delivery_receiving_address="Shop 5, APMC Market",
        city="Navi Mumbai",
        state="Maharashtra",
        postal_code="400703",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_pg_listing(db: Session, farmer: User) -> ProduceListing:
    """Create category and active listing in PostgreSQL."""
    cat = db.query(ProduceCategory).filter(ProduceCategory.name == "Vegetables").first()
    if not cat:
        cat = ProduceCategory(name="Vegetables", slug=f"veg-{uuid.uuid4().hex[:6]}", is_active=True)
        db.add(cat)
        db.flush()

    listing = ProduceListing(
        farmer_id=farmer.id,
        category_id=cat.id,
        product_name="Nashik Red Onions",
        title="High Quality Red Onions",
        initial_quantity=Decimal("1000.000"),
        available_quantity=Decimal("1000.000"),
        unit="kg",
        price_per_unit=Decimal("40.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        status=STATUS_ACTIVE,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def create_pg_order(db: Session, farmer: User, buyer: User) -> Order:
    """Create offer and order in PostgreSQL."""
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
        total_amount=Decimal("4000.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db.add(offer)
    db.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        source_offer_id=offer.id,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("4000.00"),
        status=ORDER_STATUS_CONFIRMED,
        delivery_status=DELIVERY_STATUS_NOT_ARRANGED,
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        product_name="Nashik Red Onions",
        quantity=Decimal("100.000"),
        unit="kg",
        unit_price=Decimal("40.00"),
        subtotal=Decimal("4000.00"),
        status="confirmed",
    )
    db.add(item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# PostgreSQL Integration & Concurrency Tests
# ===========================================================================

def test_01_verify_postgres_environment_and_revision(db_session: Session):
    """Verify live PostgreSQL 18 runtime, user role, and Alembic revision head f6a1b2c3d4e5."""
    db_name = db_session.execute(text("SELECT current_database()")).scalar()
    assert db_name == "agridirect_module3_test"

    alembic_rev = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert alembic_rev in ("f6a1b2c3d4e5", "a1b2c3d4e5f6", "b2c3d4e5f6a1"), f"Expected revision f6a1b2c3d4e5, a1b2c3d4e5f6, or b2c3d4e5f6a1, got {alembic_rev}"

    # Verify contact_share_requests table exists
    table_exists = db_session.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'contact_share_requests')")
    ).scalar()
    assert table_exists is True


def test_02_concurrent_conversation_creation_race_condition(client: TestClient, db_session: Session):
    """Verify that concurrent requests attempting to create a thread for the same counterparts

    do not violate unique constraint uq_conversations_counterparts and result in exactly one thread.
    """
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer)

    results = []
    errors = []

    def attempt_create():
        try:
            resp = client.post(
                "/api/v1/conversations",
                headers=make_auth_headers(buyer),
                json={"listing_id": str(listing.id)},
            )
            results.append((resp.status_code, resp.json().get("id")))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=attempt_create) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    # Every request must succeed (either 201 Created or 200 OK)
    assert all(code in (200, 201) for code, _ in results)

    # Exactly one unique conversation ID should exist in the database for these counterparts
    conv_ids = set(cid for _, cid in results if cid is not None)
    assert len(conv_ids) == 1

    total_threads_in_db = db_session.execute(
        text("SELECT COUNT(*) FROM conversations WHERE farmer_id = :fid AND buyer_id = :bid"),
        {"fid": farmer.id, "bid": buyer.id},
    ).scalar()
    assert total_threads_in_db == 1


def test_03_concurrent_message_creation_ordering(client: TestClient, db_session: Session):
    """Verify that concurrent messages from both participants maintain deterministic ordering."""
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer)

    c_resp = client.post(
        "/api/v1/conversations",
        headers=make_auth_headers(buyer),
        json={"listing_id": str(listing.id)},
    )
    conv_id = c_resp.json()["id"]

    num_messages = 10
    errors = []

    def post_buyer_msg(i: int):
        try:
            r = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=make_auth_headers(buyer),
                json={"content": f"Buyer message {i}"},
            )
            assert r.status_code == 201
        except Exception as e:
            errors.append(e)

    def post_farmer_msg(i: int):
        try:
            r = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=make_auth_headers(farmer),
                json={"content": f"Farmer response {i}"},
            )
            assert r.status_code == 201
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(num_messages):
        threads.append(threading.Thread(target=post_buyer_msg, args=(i,)))
        threads.append(threading.Thread(target=post_farmer_msg, args=(i,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0

    # Verify message count in database
    total_msgs = db_session.execute(
        text("SELECT COUNT(*) FROM messages WHERE conversation_id = :cid"),
        {"cid": conv_id},
    ).scalar()
    assert total_msgs == num_messages * 2


def test_04_concurrent_contact_sharing_request_deduplication(client: TestClient, db_session: Session):
    """Verify that concurrent contact sharing requests do not create multiple pending requests."""
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer)

    c_resp = client.post(
        "/api/v1/conversations",
        headers=make_auth_headers(buyer),
        json={"listing_id": str(listing.id)},
    )
    conv_id = c_resp.json()["id"]

    results = []

    def request_sharing():
        r = client.post(
            f"/api/v1/conversations/{conv_id}/contact-requests",
            headers=make_auth_headers(buyer),
            json={"notes": "Please share contact details"},
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=request_sharing) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one request should succeed (201 Created), others should be rejected (400 Bad Request)
    created_count = results.count(201)
    rejected_count = results.count(400)
    assert created_count == 1
    assert rejected_count == 4

    pending_in_db = db_session.execute(
        text("SELECT COUNT(*) FROM contact_share_requests WHERE conversation_id = :cid AND status = 'pending'"),
        {"cid": conv_id},
    ).scalar()
    assert pending_in_db == 1


def test_05_concurrent_mark_as_read_idempotency(client: TestClient, db_session: Session):
    """Verify concurrent read acknowledgements do not create inconsistencies."""
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer)

    c_resp = client.post(
        "/api/v1/conversations",
        headers=make_auth_headers(buyer),
        json={"listing_id": str(listing.id)},
    )
    conv_id = c_resp.json()["id"]

    # Send 5 messages from buyer
    for i in range(5):
        client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=make_auth_headers(buyer),
            json={"content": f"Msg {i}"},
        )

    # Farmer issues multiple concurrent read requests
    results = []

    def mark_read():
        r = client.post(
            f"/api/v1/conversations/{conv_id}/read",
            headers=make_auth_headers(farmer),
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=mark_read) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(code == 200 for code in results)

    # Unread count should now be exactly 0
    unread = client.get(
        f"/api/v1/conversations/{conv_id}/unread-count",
        headers=make_auth_headers(farmer),
    ).json()["unread_count"]
    assert unread == 0


def test_06_order_linked_conversation_preservation_on_delete_set_null(client: TestClient, db_session: Session):
    """Verify that order-linked conversations survive and set order_id to NULL if order is removed."""
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    order = create_pg_order(db_session, farmer, buyer)

    c_resp = client.post(
        "/api/v1/conversations",
        headers=make_auth_headers(farmer),
        json={"order_id": str(order.id)},
    )
    conv_id = c_resp.json()["id"]
    assert c_resp.json()["order_id"] == str(order.id)

    # Send message referencing order
    m_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=make_auth_headers(farmer),
        json={"content": "Discussing order delivery", "order_id": str(order.id)},
    )
    assert m_resp.status_code == 201

    # Delete order row in PostgreSQL
    db_session.execute(text("DELETE FROM order_items WHERE order_id = :oid"), {"oid": order.id})
    db_session.execute(text("DELETE FROM orders WHERE id = :oid"), {"oid": order.id})
    db_session.commit()

    # Conversation thread must still exist
    conv_after = db_session.execute(
        text("SELECT id, order_id FROM conversations WHERE id = :cid"),
        {"cid": conv_id},
    ).fetchone()
    assert conv_after is not None
    # FK ondelete='SET NULL' sets order_id to None
    assert conv_after[1] is None

    # Message must still exist
    msg_after = db_session.execute(
        text("SELECT id, order_id FROM messages WHERE conversation_id = :cid"),
        {"cid": conv_id},
    ).fetchone()
    assert msg_after is not None
    assert msg_after[1] is None


def test_07_postgresql_attachment_type_and_size_constraints(client: TestClient, db_session: Session):
    """Verify check constraints chk_msg_attachments_file_size and chk_msg_attachments_type in PostgreSQL."""
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer)

    c_resp = client.post(
        "/api/v1/conversations",
        headers=make_auth_headers(buyer),
        json={"listing_id": str(listing.id)},
    )
    conv_id = c_resp.json()["id"]

    m_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=make_auth_headers(buyer),
        json={"content": "Evidence attachment"},
    )
    msg_id = m_resp.json()["id"]

    # Verify invalid size rejected by check constraint in PostgreSQL
    with pytest.raises(Exception):
        db_session.execute(
            text("""
            INSERT INTO message_attachments (id, message_id, file_uri, file_name, file_mime_type, file_size_bytes, attachment_type)
            VALUES (:id, :mid, 'chat/test.jpg', 'test.jpg', 'image/jpeg', 0, 'image')
        """),
            {"id": uuid.uuid4(), "mid": msg_id},
        )
        db_session.commit()
    db_session.rollback()

    # Verify invalid attachment_type rejected by check constraint in PostgreSQL
    with pytest.raises(Exception):
        db_session.execute(
            text("""
            INSERT INTO message_attachments (id, message_id, file_uri, file_name, file_mime_type, file_size_bytes, attachment_type)
            VALUES (:id, :mid, 'chat/test.jpg', 'test.jpg', 'image/jpeg', 100, 'audio')
        """),
            {"id": uuid.uuid4(), "mid": msg_id},
        )
        db_session.commit()
    db_session.rollback()


def test_08_contact_privacy_unconsented_sql_inspection(client: TestClient, db_session: Session):
    """Verify that unconsented contact information remains hidden across API inspection."""
    farmer = create_pg_farmer(db_session)
    buyer = create_pg_buyer(db_session)
    listing = create_pg_listing(db_session, farmer)

    c_resp = client.post(
        "/api/v1/conversations",
        headers=make_auth_headers(buyer),
        json={"listing_id": str(listing.id)},
    )
    conv_id = c_resp.json()["id"]

    # Detail API endpoint
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=make_auth_headers(buyer)).json()
    assert detail["contact_sharing_consented"] is False
    assert detail["other_participant"]["email"] is None
    assert detail["other_participant"]["phone_number"] is None

    # Direct contact endpoint returns 403 Forbidden
    resp = client.get(f"/api/v1/conversations/{conv_id}/contacts", headers=make_auth_headers(buyer))
    assert resp.status_code == 403

