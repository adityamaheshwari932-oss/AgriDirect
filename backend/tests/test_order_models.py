"""Automated unit and integration tests for Orders and Inventory (Group 8) ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``orders``
  - ``order_items``
  - ``order_amendments``
  - ``inventory_adjustments``
- Column definitions, data types, precision, scale, nullabilities, and defaults
- Primary key generation via ``UUIDPrimaryKeyMixin``
- ``TimestampMixin`` usage (present on orders and order_amendments)
- Foreign key definitions and on-delete rules:
  - ``orders.source_offer_id -> offers.id`` (ON DELETE RESTRICT)
  - ``orders.buyer_id -> users.id`` (ON DELETE RESTRICT)
  - ``orders.farmer_id -> users.id`` (ON DELETE RESTRICT)
  - ``order_items.order_id -> orders.id`` (ON DELETE CASCADE)
  - ``order_items.listing_id -> produce_listings.id`` (ON DELETE SET NULL)
  - ``order_amendments.order_id -> orders.id`` (ON DELETE RESTRICT)
  - ``order_amendments.proposed_by_user_id -> users.id`` (ON DELETE RESTRICT)
  - ``inventory_adjustments.listing_id -> produce_listings.id`` (ON DELETE RESTRICT)
  - ``inventory_adjustments.order_id -> orders.id`` (ON DELETE SET NULL)
  - ``inventory_adjustments.amendment_id -> order_amendments.id`` (ON DELETE SET NULL)
  - ``inventory_adjustments.recorded_by_user_id -> users.id`` (ON DELETE RESTRICT)
- Constraints:
  - ``chk_orders_counterparts`` (buyer_id <> farmer_id)
  - ``chk_orders_total_amount`` (total_amount > 0)
  - ``chk_orders_status``
  - ``chk_orders_delivery_status``
  - ``chk_order_items_quantity`` (quantity > 0)
  - ``chk_order_items_unit_price`` (unit_price > 0)
  - ``chk_order_items_subtotal`` (subtotal > 0)
  - ``chk_order_items_status``
  - ``chk_amendments_type``
  - ``chk_amendments_status``
  - ``chk_inv_adjustments_change_type``
  - ``uq_orders_order_number`` (UNIQUE)
  - ``uq_orders_source_offer`` (UNIQUE)
- Indexes on all four tables
- Database execution:
  - Order creation from accepted offer
  - Snapshot line items preservation
  - Post-finalization amendments creation
  - Append-only inventory adjustment audit ledger
  - Prevention of self-dealing
  - Prevention of duplicate order creation from same offer
  - Cascade and restrict foreign-key behavior
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.chat import Conversation
from app.models.listing import ProduceListing
from app.models.offer import (
    OFFER_STATUS_ACCEPTED,
    Offer,
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
    CHANGE_TYPE_MANUAL_RESTOCK,
    CHANGE_TYPE_MANUAL_SHRINKAGE,
    CHANGE_TYPE_ORDER_CANCELLATION_RELEASE,
    CHANGE_TYPE_ORDER_FULFILLMENT,
    DELIVERY_STATUS_ARRANGED,
    DELIVERY_STATUS_COMPLETED,
    DELIVERY_STATUS_COMPLETION_MARKED,
    DELIVERY_STATUS_NOT_ARRANGED,
    ORDER_ITEM_STATUS_CANCELLED,
    ORDER_ITEM_STATUS_CONFIRMED,
    ORDER_ITEM_STATUS_DISPUTED,
    ORDER_ITEM_STATUS_FULFILLED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_DISPUTED,
    ORDER_STATUS_PAYMENT_PENDING,
    ORDER_STATUS_PAYMENT_RECORDED,
    ORDER_STATUS_PENDING,
    VALID_AMENDMENT_STATUSES,
    VALID_AMENDMENT_TYPES,
    VALID_CHANGE_TYPES,
    VALID_DELIVERY_STATUSES,
    VALID_ORDER_ITEM_STATUSES,
    VALID_ORDER_STATUSES,
    InventoryAdjustment,
    Order,
    OrderAmendment,
    OrderItem,
)
from app.models.user import User


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database engine with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

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
    """Provide a transactional database session for each test."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_farmer(db_session: Session) -> User:
    """Create and persist a verified farmer user."""
    farmer = User(
        email="order_farmer@agridirect.test",
        password_hash="hashed_secret_farmer",
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)
    return farmer


@pytest.fixture
def sample_buyer(db_session: Session) -> User:
    """Create and persist a verified buyer user."""
    buyer = User(
        email="order_buyer@agridirect.test",
        password_hash="hashed_secret_buyer",
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(buyer)
    db_session.commit()
    db_session.refresh(buyer)
    return buyer


@pytest.fixture
def sample_conversation(
    db_session: Session, sample_farmer: User, sample_buyer: User
) -> Conversation:
    """Create and persist a conversation thread."""
    conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    return conv


@pytest.fixture
def sample_listing(
    db_session: Session, sample_farmer: User
) -> ProduceListing:
    """Create and persist a produce listing."""
    listing = ProduceListing(
        farmer_id=sample_farmer.id,
        product_name="Sharbati Wheat",
        title="Premium Sharbati Wheat",
        initial_quantity=Decimal("1000.000"),
        available_quantity=Decimal("1000.000"),
        unit="quintal",
        price_per_unit=Decimal("3500.00"),
        location_state="Madhya Pradesh",
        location_city="Sehore",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=60),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


@pytest.fixture
def sample_offer(
    db_session: Session,
    sample_conversation: Conversation,
    sample_farmer: User,
    sample_buyer: User,
) -> Offer:
    """Create and persist an accepted offer."""
    offer = Offer(
        offer_number="OFF-ORD-0001",
        conversation_id=sample_conversation.id,
        sender_id=sample_buyer.id,
        recipient_id=sample_farmer.id,
        total_amount=Decimal("350000.00"),
        status=OFFER_STATUS_ACCEPTED,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    return offer


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestOrderMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """All four Group 8 tables must be registered in Base.metadata."""
        assert "orders" in Base.metadata.tables
        assert "order_items" in Base.metadata.tables
        assert "order_amendments" in Base.metadata.tables
        assert "inventory_adjustments" in Base.metadata.tables

    def test_orders_columns_and_nullability(self) -> None:
        """orders table must have all 22 specified columns with exact nullabilities."""
        table = Base.metadata.tables["orders"]
        expected = {
            "id": False,
            "order_number": False,
            "source_offer_id": False,
            "buyer_id": False,
            "farmer_id": False,
            "total_amount": False,
            "status": False,
            "delivery_method": True,
            "delivery_destination_address": True,
            "delivery_arranged_date": True,
            "delivery_status": False,
            "delivery_completion_marked_by_user_id": True,
            "delivery_completion_marked_at": True,
            "delivery_acknowledged_by_user_id": True,
            "delivery_acknowledged_at": True,
            "delivery_notes": True,
            "cancellation_reason": True,
            "cancelled_by_user_id": True,
            "cancelled_at": True,
            "completed_at": True,
            "created_at": False,
            "updated_at": False,
        }
        assert len(table.columns) == 22
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from orders"
            assert table.c[col_name].nullable == nullable

    def test_order_items_columns_and_nullability(self) -> None:
        """order_items table must have all 12 columns with exact nullabilities."""
        table = Base.metadata.tables["order_items"]
        expected = {
            "id": False,
            "order_id": False,
            "listing_id": True,
            "buyer_requirement_id": True,
            "product_name": False,
            "quantity": False,
            "unit": False,
            "unit_price": False,
            "subtotal": False,
            "quality_grade": True,
            "status": False,
            "created_at": False,
        }
        assert len(table.columns) == 12
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from order_items"
            assert table.c[col_name].nullable == nullable

    def test_order_amendments_columns_and_nullability(self) -> None:
        """order_amendments table must have all 13 columns with exact nullabilities."""
        table = Base.metadata.tables["order_amendments"]
        expected = {
            "id": False,
            "order_id": False,
            "proposed_by_user_id": False,
            "amendment_type": False,
            "old_value": False,
            "new_value": False,
            "justification": True,
            "buyer_confirmed": False,
            "farmer_confirmed": False,
            "status": False,
            "effective_at": True,
            "created_at": False,
            "updated_at": False,
        }
        assert len(table.columns) == 13
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from order_amendments"
            assert table.c[col_name].nullable == nullable

    def test_inventory_adjustments_columns_and_nullability(self) -> None:
        """inventory_adjustments table must have all 9 columns with exact nullabilities."""
        table = Base.metadata.tables["inventory_adjustments"]
        expected = {
            "id": False,
            "listing_id": False,
            "order_id": True,
            "amendment_id": True,
            "change_type": False,
            "quantity_delta": False,
            "recorded_by_user_id": False,
            "notes": True,
            "created_at": False,
        }
        assert len(table.columns) == 9
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from inventory_adjustments"
            assert table.c[col_name].nullable == nullable

    def test_foreign_keys_and_on_delete_rules(self) -> None:
        """Foreign keys across all four models must match specified ondelete actions."""
        # 1. orders
        orders_tbl = Base.metadata.tables["orders"]
        orders_fks = {fk.parent.name: fk for fk in orders_tbl.foreign_keys}
        assert orders_fks["source_offer_id"].column.table.name == "offers"
        assert orders_fks["source_offer_id"].ondelete == "RESTRICT"
        assert orders_fks["buyer_id"].column.table.name == "users"
        assert orders_fks["buyer_id"].ondelete == "RESTRICT"
        assert orders_fks["farmer_id"].column.table.name == "users"
        assert orders_fks["farmer_id"].ondelete == "RESTRICT"
        assert orders_fks["delivery_completion_marked_by_user_id"].ondelete == "SET NULL"
        assert orders_fks["delivery_acknowledged_by_user_id"].ondelete == "SET NULL"
        assert orders_fks["cancelled_by_user_id"].ondelete == "SET NULL"

        # 2. order_items
        items_tbl = Base.metadata.tables["order_items"]
        items_fks = {fk.parent.name: fk for fk in items_tbl.foreign_keys}
        assert items_fks["order_id"].column.table.name == "orders"
        assert items_fks["order_id"].ondelete == "CASCADE"
        assert items_fks["listing_id"].column.table.name == "produce_listings"
        assert items_fks["listing_id"].ondelete == "SET NULL"
        assert items_fks["buyer_requirement_id"].column.table.name == "buyer_requirements"
        assert items_fks["buyer_requirement_id"].ondelete == "SET NULL"

        # 3. order_amendments
        amend_tbl = Base.metadata.tables["order_amendments"]
        amend_fks = {fk.parent.name: fk for fk in amend_tbl.foreign_keys}
        assert amend_fks["order_id"].column.table.name == "orders"
        assert amend_fks["order_id"].ondelete == "RESTRICT"
        assert amend_fks["proposed_by_user_id"].column.table.name == "users"
        assert amend_fks["proposed_by_user_id"].ondelete == "RESTRICT"

        # 4. inventory_adjustments
        inv_tbl = Base.metadata.tables["inventory_adjustments"]
        inv_fks = {fk.parent.name: fk for fk in inv_tbl.foreign_keys}
        assert inv_fks["listing_id"].column.table.name == "produce_listings"
        assert inv_fks["listing_id"].ondelete == "RESTRICT"
        assert inv_fks["order_id"].column.table.name == "orders"
        assert inv_fks["order_id"].ondelete == "SET NULL"
        assert inv_fks["amendment_id"].column.table.name == "order_amendments"
        assert inv_fks["amendment_id"].ondelete == "SET NULL"
        assert inv_fks["recorded_by_user_id"].column.table.name == "users"
        assert inv_fks["recorded_by_user_id"].ondelete == "RESTRICT"

    def test_canonical_constants(self) -> None:
        """All order, delivery, amendment, and inventory status constants must match specifications."""
        assert len(VALID_ORDER_STATUSES) == 8
        assert set(VALID_ORDER_STATUSES) == {
            "pending",
            "confirmed",
            "payment_pending",
            "payment_recorded",
            "delivery_arranged",
            "completed",
            "cancelled",
            "disputed",
        }
        assert set(VALID_DELIVERY_STATUSES) == {
            "not_arranged",
            "arranged",
            "completion_marked",
            "completed",
        }
        assert set(VALID_ORDER_ITEM_STATUSES) == {
            "confirmed",
            "fulfilled",
            "cancelled",
            "disputed",
        }
        assert set(VALID_AMENDMENT_TYPES) == {
            "quantity",
            "price",
            "delivery_date",
            "terms",
        }
        assert set(VALID_AMENDMENT_STATUSES) == {
            "proposed",
            "effective",
            "rejected",
        }
        assert set(VALID_CHANGE_TYPES) == {
            "order_fulfillment",
            "order_cancellation_release",
            "amendment_delta",
            "manual_restock",
            "manual_shrinkage",
        }


# ===========================================================================
# 2. Database Operations & Persistence Tests
# ===========================================================================


class TestOrderPersistence:
    """Verify database CRUD, snapshot preservation, amendments, and inventory ledgers."""

    def test_create_order_with_items_and_delivery_fields(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """Create order with integrated delivery fields and immutable snapshot line items."""
        order = Order(
            order_number="ORD-20261026-0001",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("350000.00"),
            status=ORDER_STATUS_CONFIRMED,
            delivery_method="farmer_arranged",
            delivery_destination_address="Warehouse 4B, APMC Yard, Mumbai",
            delivery_arranged_date=date.today() + timedelta(days=5),
            delivery_status=DELIVERY_STATUS_ARRANGED,
            delivery_notes="Truck number MH-12-AB-1234",
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        item = OrderItem(
            order_id=order.id,
            listing_id=sample_listing.id,
            product_name="Sharbati Wheat (Snapshot)",
            quantity=Decimal("100.000"),
            unit="quintal",
            unit_price=Decimal("3500.00"),
            subtotal=Decimal("350000.00"),
            quality_grade="Grade A",
            status=ORDER_ITEM_STATUS_CONFIRMED,
        )
        db_session.add(item)
        db_session.commit()

        db_session.refresh(order)
        assert len(order.items) == 1
        assert order.items[0].product_name == "Sharbati Wheat (Snapshot)"
        assert order.delivery_status == "arranged"
        assert order.created_at is not None
        assert order.updated_at is not None

    def test_create_order_amendment(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """Create an order amendment proposing a delivery date change."""
        order = Order(
            order_number="ORD-20261026-0002",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("10000.00"),
        )
        db_session.add(order)
        db_session.commit()

        amendment = OrderAmendment(
            order_id=order.id,
            proposed_by_user_id=sample_buyer.id,
            amendment_type=AMENDMENT_TYPE_DELIVERY_DATE,
            old_value='{"delivery_date": "2026-11-01"}',
            new_value='{"delivery_date": "2026-11-05"}',
            justification="Transport delay due to festival",
            buyer_confirmed=True,
            farmer_confirmed=False,
            status=AMENDMENT_STATUS_PROPOSED,
        )
        db_session.add(amendment)
        db_session.commit()
        db_session.refresh(amendment)

        assert amendment.status == "proposed"
        assert amendment.buyer_confirmed is True
        assert amendment.farmer_confirmed is False

    def test_inventory_adjustment_audit_record(
        self,
        db_session: Session,
        sample_farmer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """Create an append-only inventory adjustment entry."""
        adjustment = InventoryAdjustment(
            listing_id=sample_listing.id,
            change_type=CHANGE_TYPE_ORDER_FULFILLMENT,
            quantity_delta=Decimal("-50.000"),
            recorded_by_user_id=sample_farmer.id,
            notes="Farmer approved order deduction",
        )
        db_session.add(adjustment)
        db_session.commit()
        db_session.refresh(adjustment)

        assert adjustment.quantity_delta == Decimal("-50.000")
        assert adjustment.change_type == "order_fulfillment"
        assert adjustment.listing_id == sample_listing.id


# ===========================================================================
# 3. Check Constraint & Integrity Enforcement Tests
# ===========================================================================


class TestOrderConstraints:
    """Verify runtime check and unique constraint enforcement."""

    def test_self_dealing_order_fails(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
    ) -> None:
        """chk_orders_counterparts rejects buyer_id == farmer_id."""
        order = Order(
            order_number="ORD-SELF-001",
            source_offer_id=sample_offer.id,
            buyer_id=sample_farmer.id,
            farmer_id=sample_farmer.id,  # Same user
            total_amount=Decimal("1000.00"),
        )
        db_session.add(order)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_source_offer_id_fails(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """UNIQUE constraint on source_offer_id prevents duplicate order creation."""
        order1 = Order(
            order_number="ORD-DUP-001",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(order1)
        db_session.commit()

        order2 = Order(
            order_number="ORD-DUP-002",
            source_offer_id=sample_offer.id,  # Duplicate source offer
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(order2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_order_total_amount_must_be_positive(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """chk_orders_total_amount rejects total_amount <= 0."""
        order = Order(
            order_number="ORD-BAD-AMT",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("0.00"),
        )
        db_session.add(order)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_order_status_fails(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """chk_orders_status rejects invalid status."""
        order = Order(
            order_number="ORD-BAD-STATUS",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("100.00"),
            status="awaiting_shipment",  # Invalid
        )
        db_session.add(order)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_order_deletion_cascades_to_order_items(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """ON DELETE CASCADE removes order_items when an order is deleted."""
        order = Order(
            order_number="ORD-DEL-001",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(order)
        db_session.commit()

        item = OrderItem(
            order_id=order.id,
            product_name="Produce",
            quantity=Decimal("10.000"),
            unit="kg",
            unit_price=Decimal("100.00"),
            subtotal=Decimal("1000.00"),
        )
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        db_session.delete(order)
        db_session.commit()

        assert db_session.get(OrderItem, item_id) is None

    def test_produce_listing_deletion_sets_null_on_order_items(
        self,
        db_session: Session,
        sample_offer: Offer,
        sample_farmer: User,
        sample_buyer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """ON DELETE SET NULL preserves order_items snapshot when produce_listing is removed."""
        order = Order(
            order_number="ORD-LST-001",
            source_offer_id=sample_offer.id,
            buyer_id=sample_buyer.id,
            farmer_id=sample_farmer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(order)
        db_session.commit()

        item = OrderItem(
            order_id=order.id,
            listing_id=sample_listing.id,
            product_name="Produce",
            quantity=Decimal("10.000"),
            unit="kg",
            unit_price=Decimal("100.00"),
            subtotal=Decimal("1000.00"),
        )
        db_session.add(item)
        db_session.commit()

        # Delete listing
        db_session.delete(sample_listing)
        db_session.commit()

        db_session.refresh(item)
        assert item.listing_id is None
        assert item.product_name == "Produce"  # Snapshot preserved
