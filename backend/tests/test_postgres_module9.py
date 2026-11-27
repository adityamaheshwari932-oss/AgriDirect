"""PostgreSQL Integration and Concurrency Test Suite for Backend Module 9: Descriptive Market Analytics.

Verifies Module 9 against the isolated PostgreSQL 18.6 test database: `agridirect_module3_test`.

Safety Guarantees:
- Uses ONLY `agridirect_module3_test`.
- Strictly NEVER touches, accesses, or modifies `agridirect_db`.
- Pre-flight database name assertion on every test execution.
- Auto-clean up via TRUNCATE CASCADE with complete isolation.
- Verifies real SQL aggregations, permanent fulfillment retention, and read-only session barriers.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.analytics.dependencies import get_read_only_db
from app.db.session import get_db, init_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.listing import STATUS_ACTIVE, ProduceCategory, ProduceListing
from app.models.offer import OFFER_STATUS_ACCEPTED, Offer, OfferItem
from app.models.order import (
    DELIVERY_STATUS_COMPLETED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DISPUTED,
    ORDER_STATUS_PENDING,
    Order,
    OrderItem,
)
from app.models.payment import (
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_UPI,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    PaymentRecord,
)
from app.models.requirement import (
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    BuyerRequirement,
)
from app.models.requirement_approval import (
    APPROVAL_STATUS_APPROVED,
    RequirementFulfillmentApproval,
)
from app.models.review import RatingReview
from app.models.user import BuyerProfile, FarmerProfile, User
from tests.pg_test_utils import cleanup_pg_test_tables, ensure_pg_test_schema_at_head

TEST_PG_DB_URL = "postgresql+psycopg://agridirect_app:agridirect@localhost:5432/agridirect_module3_test"

_pg_engine = create_engine(TEST_PG_DB_URL, pool_size=20, max_overflow=10)
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
                ratings_reviews,
                user_reports,
                admin_audit_logs,
                payment_complaints,
                payment_records,
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
            CASCADE;
            """)
        )
        db.commit()


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure isolated PG DB is migrated to head and clean before and after each test."""
    ensure_pg_test_schema_at_head()
    cleanup_pg_test_tables(_SessionLocal)
    yield
    cleanup_pg_test_tables(_SessionLocal)


@pytest.fixture
def pg_session() -> Generator[Session, None, None]:
    """Provide a real PostgreSQL session."""
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(pg_session: Session) -> Generator[TestClient, None, None]:
    """TestClient wired directly to real PostgreSQL test DB."""
    def override_get_db():
        with _SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_read_only_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed Helpers
# ---------------------------------------------------------------------------


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


def seed_farmer(
    db: Session,
    state: str = "Maharashtra",
    city: str = "Nashik",
    verified: bool = True,
) -> User:
    """Create a verified farmer on PostgreSQL."""
    u = User(
        email=f"farmer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="farmer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    fp = FarmerProfile(
        user_id=u.id,
        full_name=f"Farmer {u.id.hex[:4]}",
        farm_name="Nashik Valley Farms",
        farm_location_address="Dindori Road",
        city=city,
        state=state,
        postal_code="422004",
    )
    db.add(fp)
    db.commit()
    db.refresh(u)
    return u


def seed_buyer(
    db: Session,
    state: str = "Maharashtra",
    city: str = "Mumbai",
    verified: bool = True,
) -> User:
    """Create a verified commercial buyer on PostgreSQL."""
    u = User(
        email=f"buyer_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="buyer",
        verification_status="verified" if verified else "unverified",
        account_status="active",
        phone_number=f"+9199{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.flush()
    bp = BuyerProfile(
        user_id=u.id,
        contact_person_name="Mr. Procurement Head",
        business_name="Metro Agro Traders",
        business_type="wholesaler",
        delivery_receiving_address="Vashi APMC Yard",
        city=city,
        state=state,
        postal_code="400703",
    )
    db.add(bp)
    db.commit()
    db.refresh(u)
    return u


def seed_admin(db: Session) -> User:
    """Create an administrator on PostgreSQL."""
    u = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9197{uuid.uuid4().int % 100000000:08d}",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_completed_order(
    db: Session,
    farmer: User,
    buyer: User,
    product_name: str = "Pomegranate Bhagwa",
    quantity: Decimal = Decimal("200.000"),
    unit: str = "kg",
    price: Decimal = Decimal("80.00"),
    completed_at: datetime = None,
) -> Order:
    """Create completed order transaction with conversation and snapshot line items on PostgreSQL."""
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)

    conv = db.query(Conversation).filter_by(farmer_id=farmer.id, buyer_id=buyer.id).first()
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
        sender_id=buyer.id,
        recipient_id=farmer.id,
        status=OFFER_STATUS_ACCEPTED,
        total_amount=quantity * price,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(offer)
    db.flush()

    offer_item = OfferItem(
        offer_id=offer.id,
        product_name=product_name,
        quantity=quantity,
        unit=unit,
        unit_price=price,
        subtotal=quantity * price,
    )
    db.add(offer_item)
    db.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        source_offer_id=offer.id,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        total_amount=quantity * price,
        status=ORDER_STATUS_COMPLETED,
        delivery_status=DELIVERY_STATUS_COMPLETED,
        completed_at=completed_at,
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_name=product_name,
        quantity=quantity,
        unit=unit,
        unit_price=price,
        subtotal=quantity * price,
        status="fulfilled",
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)
    return order


# ===========================================================================
# PostgreSQL Integration Tests
# ===========================================================================


def test_postgres_market_summary_aggregations(client: TestClient, pg_session: Session):
    """Verify market summary calculations execute cleanly on real PostgreSQL 18.6."""
    farmers = [seed_farmer(pg_session) for _ in range(3)]
    buyers = [seed_buyer(pg_session) for _ in range(3)]

    # 3 trades: 200kg @ 80, 200kg @ 90, 200kg @ 100.
    # Total volume = 600kg, total value = 16000 + 18000 + 20000 = 54000.
    # VWAP = 54000 / 600 = 90.00.
    seed_completed_order(pg_session, farmers[0], buyers[0], price=Decimal("80.00"))
    seed_completed_order(pg_session, farmers[1], buyers[1], price=Decimal("90.00"))
    seed_completed_order(pg_session, farmers[2], buyers[2], price=Decimal("100.00"))

    res = client.get("/api/v1/analytics/market-summary")
    assert res.status_code == 200
    data = res.json()

    trades = data["realized_trades"]
    assert trades["distinct_farmers_count"] == 3
    assert trades["distinct_buyers_count"] == 3
    assert trades["total_trades_count"] == 3
    assert Decimal(str(trades["total_quantity_traded"])) == Decimal("600.000")
    assert Decimal(str(trades["total_gross_value"])) == Decimal("54000.00")
    assert Decimal(str(trades["vwap"])) == Decimal("90.00")
    assert Decimal(str(trades["arithmetic_mean_price"])) == Decimal("90.00")
    assert Decimal(str(trades["median_price"])) == Decimal("90.00")


def test_postgres_demand_summary_permanent_fulfillment(client: TestClient, pg_session: Session):
    """Verify permanent fulfillment preservation on PostgreSQL across soft-deleted requirements."""
    farmer = seed_farmer(pg_session)
    buyer = seed_buyer(pg_session)

    req = BuyerRequirement(
        buyer_id=buyer.id,
        product_name="Alphonso Mango",
        title="Grade A Alphonso Mangoes",
        required_quantity=Decimal("1000.000"),
        remaining_quantity=Decimal("400.000"),
        unit="quintal",
        destination_state="Maharashtra",
        destination_city="Mumbai",
        required_by_date=date.today() + timedelta(days=20),
        status=REQUIREMENT_STATUS_ACTIVE,
        is_deleted=True,
        deleted_at=datetime.now(timezone.utc),
    )
    pg_session.add(req)
    pg_session.flush()

    order = seed_completed_order(
        pg_session, farmer, buyer,
        product_name="Alphonso Mango",
        quantity=Decimal("600.000"),
        unit="quintal",
        price=Decimal("5000.00"),
    )
    order_item = order.items[0]
    order_item.buyer_requirement_id = req.id
    pg_session.flush()

    appr = RequirementFulfillmentApproval(
        requirement_id=req.id,
        order_id=order.id,
        order_item_id=order_item.id,
        proposed_quantity=Decimal("600.000"),
        approved_quantity=Decimal("600.000"),
        status=APPROVAL_STATUS_APPROVED,
        reviewed_by_user_id=buyer.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    pg_session.add(appr)
    pg_session.commit()

    res = client.get("/api/v1/analytics/demand-summary?product_name=Alphonso Mango")
    assert res.status_code == 200
    data = res.json()

    concluded = data["concluded_demand_audit"]
    assert Decimal(str(concluded["audited_approved_fulfillment_quantity"])) == Decimal("600.000")
    assert concluded["approved_fulfillments_count"] == 1
    assert concluded["includes_soft_deleted_requirements"] is True


def test_postgres_platform_analytics(client: TestClient, pg_session: Session):
    """Verify platform-wide statistics on PostgreSQL test database."""
    admin = seed_admin(pg_session)
    farmer = seed_farmer(pg_session)
    buyer = seed_buyer(pg_session)

    # Completed order: 50,000 GMV
    seed_completed_order(
        pg_session, farmer, buyer,
        quantity=Decimal("500.000"),
        unit="kg",
        price=Decimal("100.00"),
    )

    res = client.get("/api/v1/analytics/admin/platform", headers=make_headers(admin))
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["platform_gmv"])) == Decimal("50000.00")
    assert data["order_outcomes"]["total_orders"] == 1
    assert data["order_outcomes"]["completed"] == 1
    assert data["order_outcomes"]["completed_order_share"] == 100.0
    assert data["order_outcomes"]["concluded_orders"] == 1
    assert data["order_outcomes"]["concluded_completion_rate"] == 100.0
    assert data["order_outcomes"]["concluded_cancellation_rate"] == 0.0
    assert data["user_engagement"]["verified_farmers"] == 1
    assert data["user_engagement"]["verified_buyers"] == 1
    assert data["user_engagement"]["admin_users"] == 1


def test_postgres_read_only_session_rejection(pg_session: Session):
    """Verify get_read_only_db enforces read-only transaction on PostgreSQL and blocks flush."""
    # Ensure init_db is bound to the test postgres engine
    init_db(engine=_pg_engine)

    gen = get_read_only_db()
    ro_session = next(gen)

    # Attempt to insert user in read-only session
    illegal_user = User(
        email=f"illegal_{uuid.uuid4().hex[:6]}@agridirect.test",
        password_hash="argon2id$mockhash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number=f"+9198{uuid.uuid4().int % 100000000:08d}",
    )
    ro_session.add(illegal_user)

    # Mutation barrier must raise RuntimeError
    with pytest.raises(RuntimeError, match="Data mutations are strictly prohibited"):
        ro_session.flush()

    try:
        next(gen)
    except StopIteration:
        pass

    # Re-verify that NO row was written to users table
    with _SessionLocal() as verify_db:
        found = verify_db.query(User).filter(User.email == illegal_user.email).first()
        assert found is None, "Violation: Illegal row was persisted in read-only session!"

