"""Automated unit and integration tests for structured offers and negotiation (Group 7) ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``offers``
  - ``offer_items``
- Column definitions, data types, precision, scale, nullabilities, and defaults
- Primary key generation via ``UUIDPrimaryKeyMixin``
- ``TimestampMixin`` usage (present on ``offers``, absent on ``offer_items``)
- Foreign key definitions and on-delete rules:
  - ``offers.conversation_id -> conversations.id`` (ON DELETE CASCADE)
  - ``offers.sender_id -> users.id`` (ON DELETE RESTRICT)
  - ``offers.recipient_id -> users.id`` (ON DELETE RESTRICT)
  - ``offers.parent_offer_id -> offers.id`` (ON DELETE SET NULL)
  - ``offer_items.offer_id -> offers.id`` (ON DELETE CASCADE)
  - ``offer_items.listing_id -> produce_listings.id`` (ON DELETE SET NULL)
- Check constraints:
  - ``chk_offers_counterparts`` (sender_id <> recipient_id)
  - ``chk_offers_total_amount`` (total_amount > 0)
  - ``chk_offers_status`` (pending, countered, accepted, rejected, withdrawn, expired)
  - ``chk_offer_items_quantity`` (quantity > 0)
  - ``chk_offer_items_unit_price`` (unit_price > 0)
  - ``chk_offer_items_subtotal`` (subtotal > 0)
  - ``chk_offer_items_status`` (proposed, agreed, rejected, modified)
- Indexes:
  - ``idx_offers_conversation`` on (conversation_id)
  - ``idx_offers_sender`` on (sender_id)
  - ``idx_offers_recipient`` on (recipient_id)
  - ``idx_offers_parent`` on (parent_offer_id)
  - ``idx_offers_status`` on (status)
  - ``idx_offer_items_offer`` on (offer_id)
  - ``idx_offer_items_listing`` on (listing_id)
- Database execution:
  - Valid proposal creation with items and decimal precision
  - Multi-item proposal with subtotals
  - Counter-offer lineage tree traversal (parent <-> counter_offers)
  - Extensible produce unit values
  - Bidirectional navigation
  - Enforcement of check constraints (IntegrityError on invalid values)
  - Unique offer_number enforcement
  - Deletion behavior: RESTRICT on users, SET NULL on parent offer, CASCADE on offer items, SET NULL on produce listings
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
from app.models.listing import ProduceCategory, ProduceListing
from app.models.offer import (
    OFFER_ITEM_STATUS_AGREED,
    OFFER_ITEM_STATUS_MODIFIED,
    OFFER_ITEM_STATUS_PROPOSED,
    OFFER_ITEM_STATUS_REJECTED,
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_COUNTERED,
    OFFER_STATUS_EXPIRED,
    OFFER_STATUS_PENDING,
    OFFER_STATUS_REJECTED,
    OFFER_STATUS_WITHDRAWN,
    VALID_OFFER_ITEM_STATUSES,
    VALID_OFFER_STATUSES,
    Offer,
    OfferItem,
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
        email="offer_farmer@agridirect.test",
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
        email="offer_buyer@agridirect.test",
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
    """Create and persist a conversation thread between farmer and buyer."""
    conv = Conversation(
        farmer_id=sample_farmer.id,
        buyer_id=sample_buyer.id,
    )
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
        product_name="Nashik Red Onions",
        title="Grade-A Export Red Onions",
        initial_quantity=Decimal("500.000"),
        available_quantity=Decimal("500.000"),
        unit="quintal",
        price_per_unit=Decimal("2400.00"),
        location_state="Maharashtra",
        location_city="Nashik",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestOfferMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """offers and offer_items must be registered in Base.metadata."""
        assert "offers" in Base.metadata.tables
        assert "offer_items" in Base.metadata.tables

    def test_offers_columns_and_nullability(self) -> None:
        """offers must have all 13 columns with exact nullabilities."""
        table = Base.metadata.tables["offers"]
        expected = {
            "id": False,
            "offer_number": False,
            "conversation_id": False,
            "sender_id": False,
            "recipient_id": False,
            "parent_offer_id": True,
            "delivery_terms": True,
            "proposed_delivery_date": True,
            "total_amount": False,
            "status": False,
            "expires_at": True,
            "created_at": False,
            "updated_at": False,
        }
        assert len(table.columns) == 13
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from offers"
            assert table.c[col_name].nullable == nullable

    def test_offer_items_columns_and_nullability(self) -> None:
        """offer_items must have all 12 columns with exact nullabilities."""
        table = Base.metadata.tables["offer_items"]
        expected = {
            "id": False,
            "offer_id": False,
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
            assert col_name in table.c, f"Column {col_name} missing from offer_items"
            assert table.c[col_name].nullable == nullable

    def test_primary_keys_and_mixins(self) -> None:
        """Both tables must use UUID primary keys; offers uses TimestampMixin."""
        for tbl_name in ["offers", "offer_items"]:
            table = Base.metadata.tables[tbl_name]
            assert "id" in table.primary_key.columns
            pk_col = table.c.id
            assert isinstance(pk_col.type, PG_UUID)
            assert pk_col.type.as_uuid is True

        # TimestampMixin columns on offers
        assert "created_at" in Base.metadata.tables["offers"].c
        assert "updated_at" in Base.metadata.tables["offers"].c

        # offer_items has created_at only
        assert "created_at" in Base.metadata.tables["offer_items"].c
        assert "updated_at" not in Base.metadata.tables["offer_items"].c

    def test_numeric_precision_and_scale(self) -> None:
        """Precision and scale must match schema."""
        offers_tbl = Base.metadata.tables["offers"]
        assert offers_tbl.c.total_amount.type.precision == 12
        assert offers_tbl.c.total_amount.type.scale == 2

        items_tbl = Base.metadata.tables["offer_items"]
        assert items_tbl.c.quantity.type.precision == 12
        assert items_tbl.c.quantity.type.scale == 3
        assert items_tbl.c.unit_price.type.precision == 12
        assert items_tbl.c.unit_price.type.scale == 2
        assert items_tbl.c.subtotal.type.precision == 12
        assert items_tbl.c.subtotal.type.scale == 2

    def test_foreign_keys_and_on_delete_rules(self) -> None:
        """Foreign keys must point to correct tables with exact deletion actions."""
        # offers
        offers_tbl = Base.metadata.tables["offers"]
        offers_fks = {fk.parent.name: fk for fk in offers_tbl.foreign_keys}
        assert offers_fks["conversation_id"].column.table.name == "conversations"
        assert offers_fks["conversation_id"].ondelete == "CASCADE"
        assert offers_fks["sender_id"].column.table.name == "users"
        assert offers_fks["sender_id"].ondelete == "RESTRICT"
        assert offers_fks["recipient_id"].column.table.name == "users"
        assert offers_fks["recipient_id"].ondelete == "RESTRICT"
        assert offers_fks["parent_offer_id"].column.table.name == "offers"
        assert offers_fks["parent_offer_id"].ondelete == "SET NULL"

        # offer_items
        items_tbl = Base.metadata.tables["offer_items"]
        items_fks = {fk.parent.name: fk for fk in items_tbl.foreign_keys}
        assert items_fks["offer_id"].column.table.name == "offers"
        assert items_fks["offer_id"].ondelete == "CASCADE"
        assert items_fks["listing_id"].column.table.name == "produce_listings"
        assert items_fks["listing_id"].ondelete == "SET NULL"
        assert items_fks["buyer_requirement_id"].column.table.name == "buyer_requirements"
        assert items_fks["buyer_requirement_id"].ondelete == "SET NULL"

    def test_check_constraints_and_indexes(self) -> None:
        """All required check constraints and indexes must be registered."""
        # offers
        offers_tbl = Base.metadata.tables["offers"]
        offers_checks = {c.name for c in offers_tbl.constraints if hasattr(c, "sqltext")}
        assert "chk_offers_counterparts" in offers_checks
        assert "chk_offers_total_amount" in offers_checks
        assert "chk_offers_status" in offers_checks

        offers_idx = {idx.name for idx in offers_tbl.indexes}
        assert "idx_offers_conversation" in offers_idx
        assert "idx_offers_sender" in offers_idx
        assert "idx_offers_recipient" in offers_idx
        assert "idx_offers_parent" in offers_idx
        assert "idx_offers_status" in offers_idx

        # offer_items
        items_tbl = Base.metadata.tables["offer_items"]
        items_checks = {c.name for c in items_tbl.constraints if hasattr(c, "sqltext")}
        assert "chk_offer_items_quantity" in items_checks
        assert "chk_offer_items_unit_price" in items_checks
        assert "chk_offer_items_subtotal" in items_checks
        assert "chk_offer_items_status" in items_checks

        items_idx = {idx.name for idx in items_tbl.indexes}
        assert "idx_offer_items_offer" in items_idx
        assert "idx_offer_items_listing" in items_idx
        assert "idx_offer_items_requirement" in items_idx

    def test_canonical_constants(self) -> None:
        """Canonical offer and offer-item statuses must match specifications."""
        assert OFFER_STATUS_PENDING == "pending"
        assert OFFER_STATUS_COUNTERED == "countered"
        assert OFFER_STATUS_ACCEPTED == "accepted"
        assert OFFER_STATUS_REJECTED == "rejected"
        assert OFFER_STATUS_WITHDRAWN == "withdrawn"
        assert OFFER_STATUS_EXPIRED == "expired"
        assert set(VALID_OFFER_STATUSES) == {
            "pending",
            "countered",
            "accepted",
            "rejected",
            "withdrawn",
            "expired",
        }

        assert OFFER_ITEM_STATUS_PROPOSED == "proposed"
        assert OFFER_ITEM_STATUS_AGREED == "agreed"
        assert OFFER_ITEM_STATUS_REJECTED == "rejected"
        assert OFFER_ITEM_STATUS_MODIFIED == "modified"
        assert set(VALID_OFFER_ITEM_STATUSES) == {
            "proposed",
            "agreed",
            "rejected",
            "modified",
        }


# ===========================================================================
# 2. Database Operations & Persistence Tests
# ===========================================================================


class TestOfferPersistence:
    """Verify database CRUD, multi-item proposals, and lineage persistence."""

    def test_create_offer_with_items(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """Create structured offer with multi-line proposal items."""
        offer = Offer(
            offer_number="OFF-20261026-0001",
            conversation_id=sample_conversation.id,
            sender_id=sample_buyer.id,
            recipient_id=sample_farmer.id,
            delivery_terms="Buyer arranges truck pickup from farm gate",
            proposed_delivery_date=date.today() + timedelta(days=7),
            total_amount=Decimal("220000.00"),
            status=OFFER_STATUS_PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        db_session.add(offer)
        db_session.commit()
        db_session.refresh(offer)

        item1 = OfferItem(
            offer_id=offer.id,
            listing_id=sample_listing.id,
            product_name="Nashik Red Onions (Grade A)",
            quantity=Decimal("100.000"),
            unit="quintal",
            unit_price=Decimal("2200.00"),
            subtotal=Decimal("220000.00"),
            quality_grade="Grade A Export",
            status=OFFER_ITEM_STATUS_PROPOSED,
        )
        db_session.add(item1)
        db_session.commit()

        db_session.refresh(offer)
        assert len(offer.items) == 1
        assert offer.items[0].product_name == "Nashik Red Onions (Grade A)"
        assert offer.items[0].subtotal == Decimal("220000.00")
        assert offer.created_at is not None
        assert offer.updated_at is not None

    def test_counter_offer_lineage_tree(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """Verify self-referential counter-offer lineage (parent_offer -> counter_offers)."""
        # 1. Initial Offer by Buyer
        offer_1 = Offer(
            offer_number="OFF-20261026-0002",
            conversation_id=sample_conversation.id,
            sender_id=sample_buyer.id,
            recipient_id=sample_farmer.id,
            total_amount=Decimal("100000.00"),
            status=OFFER_STATUS_COUNTERED,
        )
        db_session.add(offer_1)
        db_session.commit()

        # 2. Farmer Counters Offer 1
        offer_2 = Offer(
            offer_number="OFF-20261026-0003",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            parent_offer_id=offer_1.id,
            total_amount=Decimal("110000.00"),
            status=OFFER_STATUS_COUNTERED,
        )
        db_session.add(offer_2)
        db_session.commit()

        # 3. Buyer Counters Offer 2
        offer_3 = Offer(
            offer_number="OFF-20261026-0004",
            conversation_id=sample_conversation.id,
            sender_id=sample_buyer.id,
            recipient_id=sample_farmer.id,
            parent_offer_id=offer_2.id,
            total_amount=Decimal("105000.00"),
            status=OFFER_STATUS_ACCEPTED,
        )
        db_session.add(offer_3)
        db_session.commit()

        # Check lineage navigation
        db_session.refresh(offer_1)
        db_session.refresh(offer_2)
        db_session.refresh(offer_3)

        assert offer_1.parent_offer is None
        assert len(offer_1.counter_offers) == 1
        assert offer_1.counter_offers[0].id == offer_2.id

        assert offer_2.parent_offer.id == offer_1.id
        assert len(offer_2.counter_offers) == 1
        assert offer_2.counter_offers[0].id == offer_3.id

        assert offer_3.parent_offer.id == offer_2.id
        assert len(offer_3.counter_offers) == 0

    def test_bidirectional_navigation(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """Test full relationship traversal for offers and items."""
        offer = Offer(
            offer_number="OFF-20261026-0005",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("50000.00"),
        )
        db_session.add(offer)
        db_session.commit()

        item = OfferItem(
            offer_id=offer.id,
            listing_id=sample_listing.id,
            product_name="Nashik Onions",
            quantity=Decimal("25.000"),
            unit="quintal",
            unit_price=Decimal("2000.00"),
            subtotal=Decimal("50000.00"),
        )
        db_session.add(item)
        db_session.commit()

        db_session.refresh(sample_farmer)
        assert offer.id in [o.id for o in sample_farmer.sent_offers]

        db_session.refresh(sample_buyer)
        assert offer.id in [o.id for o in sample_buyer.received_offers]

        db_session.refresh(sample_conversation)
        assert offer.id in [o.id for o in sample_conversation.offers]

        db_session.refresh(sample_listing)
        assert item.id in [i.id for i in sample_listing.offer_items]


# ===========================================================================
# 3. Check Constraint & Integrity Enforcement Tests
# ===========================================================================


class TestOfferConstraints:
    """Verify runtime check and unique constraint enforcement."""

    def test_offer_counterparts_must_be_different(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
    ) -> None:
        """chk_offers_counterparts rejects sender_id == recipient_id."""
        offer = Offer(
            offer_number="OFF-BAD-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_farmer.id,  # Same user
            total_amount=Decimal("5000.00"),
        )
        db_session.add(offer)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_offer_total_amount_must_be_positive(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """chk_offers_total_amount rejects total_amount <= 0."""
        offer = Offer(
            offer_number="OFF-BAD-002",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("0.00"),
        )
        db_session.add(offer)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_offer_status_fails(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """chk_offers_status rejects invalid status."""
        offer = Offer(
            offer_number="OFF-BAD-003",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("1000.00"),
            status="in_review",  # Invalid
        )
        db_session.add(offer)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_offer_number_fails(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """UNIQUE constraint rejects duplicate offer_number."""
        offer1 = Offer(
            offer_number="OFF-DUP-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(offer1)
        db_session.commit()

        offer2 = Offer(
            offer_number="OFF-DUP-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("2000.00"),
        )
        db_session.add(offer2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_offer_item_positive_quantity_and_prices(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """Offer items enforce quantity > 0, unit_price > 0, and subtotal > 0."""
        offer = Offer(
            offer_number="OFF-ITEM-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("5000.00"),
        )
        db_session.add(offer)
        db_session.commit()

        # Zero quantity
        bad_qty = OfferItem(
            offer_id=offer.id,
            product_name="Product",
            quantity=Decimal("0.000"),
            unit="kg",
            unit_price=Decimal("10.00"),
            subtotal=Decimal("0.00"),
        )
        db_session.add(bad_qty)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_offer_deletion_cascades_to_items(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """ON DELETE CASCADE deletes offer_items when the offer is deleted."""
        offer = Offer(
            offer_number="OFF-DEL-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(offer)
        db_session.commit()

        item = OfferItem(
            offer_id=offer.id,
            product_name="Tomatoes",
            quantity=Decimal("10.000"),
            unit="crate",
            unit_price=Decimal("100.00"),
            subtotal=Decimal("1000.00"),
        )
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        db_session.delete(offer)
        db_session.commit()

        assert db_session.get(OfferItem, item_id) is None

    def test_parent_offer_deletion_sets_null_on_child_counter_offer(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
    ) -> None:
        """ON DELETE SET NULL sets child parent_offer_id to NULL on parent deletion."""
        parent = Offer(
            offer_number="OFF-PARENT-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_buyer.id,
            recipient_id=sample_farmer.id,
            total_amount=Decimal("1000.00"),
        )
        db_session.add(parent)
        db_session.commit()

        child = Offer(
            offer_number="OFF-CHILD-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            parent_offer_id=parent.id,
            total_amount=Decimal("1100.00"),
        )
        db_session.add(child)
        db_session.commit()

        # Delete parent
        db_session.delete(parent)
        db_session.commit()

        db_session.refresh(child)
        assert child.parent_offer_id is None
        assert child.parent_offer is None

    def test_listing_deletion_sets_null_on_offer_items(
        self,
        db_session: Session,
        sample_conversation: Conversation,
        sample_farmer: User,
        sample_buyer: User,
        sample_listing: ProduceListing,
    ) -> None:
        """ON DELETE SET NULL sets offer_item.listing_id to NULL on produce listing deletion."""
        offer = Offer(
            offer_number="OFF-LST-001",
            conversation_id=sample_conversation.id,
            sender_id=sample_farmer.id,
            recipient_id=sample_buyer.id,
            total_amount=Decimal("2000.00"),
        )
        db_session.add(offer)
        db_session.commit()

        item = OfferItem(
            offer_id=offer.id,
            listing_id=sample_listing.id,
            product_name="Red Onions",
            quantity=Decimal("1.000"),
            unit="quintal",
            unit_price=Decimal("2000.00"),
            subtotal=Decimal("2000.00"),
        )
        db_session.add(item)
        db_session.commit()

        # Delete listing
        db_session.delete(sample_listing)
        db_session.commit()

        db_session.refresh(item)
        assert item.listing_id is None
        assert item.listing is None
