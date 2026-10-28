"""Automated unit and integration tests for produce catalog, listings, and images ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``produce_categories``
  - ``produce_listings``
  - ``listing_images``
- Column definitions, data types, precision, scale, nullabilities, and defaults
- Primary key generation via ``UUIDPrimaryKeyMixin``
- ``TimestampMixin`` usage (present on ``produce_listings``, absent on ``produce_categories`` and ``listing_images``)
- Foreign key definitions and on-delete rules:
  - ``produce_categories.parent_id -> produce_categories.id`` (ON DELETE SET NULL)
  - ``produce_listings.farmer_id -> users.id`` (ON DELETE RESTRICT)
  - ``produce_listings.category_id -> produce_categories.id`` (ON DELETE SET NULL)
  - ``listing_images.listing_id -> produce_listings.id`` (ON DELETE CASCADE)
- Table-level indexes across all three models
- Check constraints on ``produce_listings``:
  - ``chk_listings_initial_quantity`` (initial_quantity > 0)
  - ``chk_listings_available_quantity`` (0 <= available_quantity <= initial_quantity)
  - ``chk_listings_price`` (price_per_unit > 0)
  - ``chk_listings_status`` (draft, active, partially_fulfilled, closed, expired)
- Database execution:
  - Category creation and self-referencing hierarchy navigation (parent <-> subcategories)
  - Valid listing creation with decimal quantities and prices
  - Extensible produce unit values (no DB-level check constraint)
  - Soft-delete field persistence (is_deleted, deleted_at)
  - Listing images attachment and ordering
  - Bidirectional ORM navigation (User.listings, ProduceCategory.listings, ProduceListing.images)
  - Database enforcement of check constraints (IntegrityError on violations)
  - Database enforcement of NOT NULL constraints on mandatory fields
  - Deletion restriction on farmer (ON DELETE RESTRICT)
  - SET NULL on category deletion
  - CASCADE on listing deletion (deletes attached images)
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
from app.models.listing import (
    CANONICAL_UNITS,
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_DRAFT,
    STATUS_EXPIRED,
    STATUS_PARTIALLY_FULFILLED,
    UNIT_BAG,
    UNIT_KG,
    UNIT_METRIC_TON,
    UNIT_QUINTAL,
    VALID_LISTING_STATUSES,
    ListingImage,
    ProduceCategory,
    ProduceListing,
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
        email="listing_farmer@agridirect.test",
        password_hash="hashed_secret_farmer",
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)
    return farmer


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestProduceListingMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """All three Phase 4 tables must be registered in Base.metadata."""
        assert "produce_categories" in Base.metadata.tables
        assert "produce_listings" in Base.metadata.tables
        assert "listing_images" in Base.metadata.tables

    def test_produce_categories_columns_and_nullability(self) -> None:
        """produce_categories must have all expected columns and nullabilities."""
        table = Base.metadata.tables["produce_categories"]
        expected_cols = {
            "id": False,
            "parent_id": True,
            "name": False,
            "slug": False,
            "is_active": False,
            "created_at": False,
        }
        for col_name, nullable in expected_cols.items():
            assert col_name in table.c, f"Column '{col_name}' missing from produce_categories"
            assert table.c[col_name].nullable is nullable, (
                f"Column '{col_name}' in produce_categories nullable expected {nullable}, got {table.c[col_name].nullable}"
            )

        # Absence of updated_at on produce_categories
        assert "updated_at" not in table.c
        assert not hasattr(ProduceCategory, "updated_at")

    def test_produce_listings_columns_and_nullability(self) -> None:
        """produce_listings must have all expected columns and nullabilities."""
        table = Base.metadata.tables["produce_listings"]
        expected_cols = {
            "id": False,
            "farmer_id": False,
            "category_id": True,
            "product_name": False,
            "title": False,
            "description": True,
            "initial_quantity": False,
            "available_quantity": False,
            "unit": False,
            "price_per_unit": False,
            "quality_grade": True,
            "location_state": False,
            "location_city": False,
            "harvest_date": True,
            "available_from": False,
            "expires_at": False,
            "status": False,
            "is_deleted": False,
            "deleted_at": True,
            "created_at": False,
            "updated_at": False,
        }
        for col_name, nullable in expected_cols.items():
            assert col_name in table.c, f"Column '{col_name}' missing from produce_listings"
            assert table.c[col_name].nullable is nullable, (
                f"Column '{col_name}' in produce_listings nullable expected {nullable}, got {table.c[col_name].nullable}"
            )

    def test_listing_images_columns_and_nullability(self) -> None:
        """listing_images must have all expected columns and nullabilities."""
        table = Base.metadata.tables["listing_images"]
        expected_cols = {
            "id": False,
            "listing_id": False,
            "image_uri": False,
            "is_primary": False,
            "display_order": False,
            "created_at": False,
        }
        for col_name, nullable in expected_cols.items():
            assert col_name in table.c, f"Column '{col_name}' missing from listing_images"
            assert table.c[col_name].nullable is nullable, (
                f"Column '{col_name}' in listing_images nullable expected {nullable}, got {table.c[col_name].nullable}"
            )

        # Absence of updated_at on listing_images
        assert "updated_at" not in table.c
        assert not hasattr(ListingImage, "updated_at")

    def test_primary_keys_use_uuid(self) -> None:
        """All three tables must use surrogate UUID primary keys."""
        for tbl_name in ["produce_categories", "produce_listings", "listing_images"]:
            table = Base.metadata.tables[tbl_name]
            pk_cols = [c.name for c in table.primary_key.columns]
            assert pk_cols == ["id"], f"{tbl_name} primary key must be ['id']"
            assert isinstance(table.c.id.type, PG_UUID), f"{tbl_name}.id must be UUID"

    def test_foreign_keys_and_ondelete_rules(self) -> None:
        """Verify foreign key references and cascade rules match schema design."""
        # 1. produce_categories.parent_id -> produce_categories.id (ON DELETE SET NULL)
        cat_table = Base.metadata.tables["produce_categories"]
        cat_fks = {fk.parent.name: fk for fk in cat_table.foreign_keys}
        assert "parent_id" in cat_fks
        assert cat_fks["parent_id"].column.table.name == "produce_categories"
        assert cat_fks["parent_id"].column.name == "id"
        assert cat_fks["parent_id"].ondelete.upper() == "SET NULL"

        # 2. produce_listings.farmer_id -> users.id (ON DELETE RESTRICT)
        #    produce_listings.category_id -> produce_categories.id (ON DELETE SET NULL)
        list_table = Base.metadata.tables["produce_listings"]
        list_fks = {fk.parent.name: fk for fk in list_table.foreign_keys}
        assert "farmer_id" in list_fks
        assert list_fks["farmer_id"].column.table.name == "users"
        assert list_fks["farmer_id"].column.name == "id"
        assert list_fks["farmer_id"].ondelete.upper() == "RESTRICT"

        assert "category_id" in list_fks
        assert list_fks["category_id"].column.table.name == "produce_categories"
        assert list_fks["category_id"].column.name == "id"
        assert list_fks["category_id"].ondelete.upper() == "SET NULL"

        # 3. listing_images.listing_id -> produce_listings.id (ON DELETE CASCADE)
        img_table = Base.metadata.tables["listing_images"]
        img_fks = {fk.parent.name: fk for fk in img_table.foreign_keys}
        assert "listing_id" in img_fks
        assert img_fks["listing_id"].column.table.name == "produce_listings"
        assert img_fks["listing_id"].column.name == "id"
        assert img_fks["listing_id"].ondelete.upper() == "CASCADE"

    def test_numeric_precision_and_scale(self) -> None:
        """Quantities must be NUMERIC(12, 3) and price must be NUMERIC(12, 2)."""
        table = Base.metadata.tables["produce_listings"]
        assert table.c.initial_quantity.type.precision == 12
        assert table.c.initial_quantity.type.scale == 3
        assert table.c.available_quantity.type.precision == 12
        assert table.c.available_quantity.type.scale == 3
        assert table.c.price_per_unit.type.precision == 12
        assert table.c.price_per_unit.type.scale == 2

    def test_produce_listings_check_constraints(self) -> None:
        """produce_listings must define all required check constraints."""
        table = Base.metadata.tables["produce_listings"]
        check_names = {c.name for c in table.constraints if hasattr(c, "sqltext")}
        expected_checks = {
            "chk_listings_initial_quantity",
            "chk_listings_available_quantity",
            "chk_listings_price",
            "chk_listings_status",
        }
        assert expected_checks.issubset(check_names), (
            f"Missing check constraints. Expected: {expected_checks}, got: {check_names}"
        )

    def test_indexes_defined_on_all_models(self) -> None:
        """All documented indexes must be registered across the three models."""
        # 1. produce_categories indexes
        cat_table = Base.metadata.tables["produce_categories"]
        cat_indexes = {idx.name: [c.name for c in idx.columns] for idx in cat_table.indexes}
        assert "idx_categories_slug" in cat_indexes
        assert cat_indexes["idx_categories_slug"] == ["slug"]
        assert "idx_categories_parent" in cat_indexes
        assert cat_indexes["idx_categories_parent"] == ["parent_id"]

        # 2. produce_listings indexes
        list_table = Base.metadata.tables["produce_listings"]
        list_index_names = {idx.name for idx in list_table.indexes}
        expected_list_indexes = {
            "idx_listings_farmer_id",
            "idx_listings_category_status",
            "idx_listings_product_name",
            "idx_listings_location",
            "idx_listings_price",
            "idx_listings_created",
        }
        assert expected_list_indexes.issubset(list_index_names), (
            f"Missing indexes on produce_listings. Expected: {expected_list_indexes}, got: {list_index_names}"
        )

        # 3. listing_images index
        img_table = Base.metadata.tables["listing_images"]
        img_indexes = {idx.name: [c.name for c in idx.columns] for idx in img_table.indexes}
        assert "idx_listing_images_listing" in img_indexes
        assert img_indexes["idx_listing_images_listing"] == ["listing_id"]

    def test_canonical_constants(self) -> None:
        """Canonical status and unit constants must match project specifications."""
        assert STATUS_DRAFT == "draft"
        assert STATUS_ACTIVE == "active"
        assert STATUS_PARTIALLY_FULFILLED == "partially_fulfilled"
        assert STATUS_CLOSED == "closed"
        assert STATUS_EXPIRED == "expired"
        assert set(VALID_LISTING_STATUSES) == {
            "draft",
            "active",
            "partially_fulfilled",
            "closed",
            "expired",
        }

        assert UNIT_KG == "kg"
        assert UNIT_QUINTAL == "quintal"
        assert UNIT_METRIC_TON == "metric_ton"
        assert UNIT_BAG == "bag"
        assert set(CANONICAL_UNITS) == {"kg", "quintal", "metric_ton", "bag"}


# ===========================================================================
# 2. Database Integration & Operations Tests
# ===========================================================================


class TestListingDatabaseOperations:
    """Integration tests executing against an isolated test database with FK enforcement."""

    def test_create_category_hierarchy(self, db_session: Session) -> None:
        """Create a hierarchical category tree and traverse bidirectional relationships."""
        root = ProduceCategory(
            name="Cereals and Grains",
            slug="cereals-and-grains",
        )
        db_session.add(root)
        db_session.commit()
        db_session.refresh(root)

        child = ProduceCategory(
            parent_id=root.id,
            name="Wheat",
            slug="wheat",
        )
        db_session.add(child)
        db_session.commit()
        db_session.refresh(child)
        db_session.refresh(root)

        assert child.parent_id == root.id
        assert child.parent is root
        assert len(root.subcategories) == 1
        assert root.subcategories[0] is child

    def test_create_valid_listing(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """Create and persist a complete produce listing with decimal values."""
        category = ProduceCategory(name="Pulses", slug="pulses")
        db_session.add(category)
        db_session.commit()

        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            category_id=category.id,
            product_name="Organic Chickpeas (Kabuli Chana)",
            title="Fresh Premium Organic Kabuli Chana 2026",
            description="Grade A machine-cleaned organic chickpeas. Free from pesticides.",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            unit=UNIT_QUINTAL,
            price_per_unit=Decimal("7500.00"),
            quality_grade="Grade A",
            location_state="Madhya Pradesh",
            location_city="Indore",
            harvest_date=date(2026, 3, 15),
            available_from=date(2026, 4, 1),
            expires_at=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            status=STATUS_ACTIVE,
        )
        db_session.add(listing)
        db_session.commit()
        db_session.refresh(listing)

        assert listing.id is not None
        assert isinstance(listing.id, uuid.UUID)
        assert listing.created_at is not None
        assert listing.updated_at is not None
        assert listing.initial_quantity == Decimal("50.000")
        assert listing.available_quantity == Decimal("50.000")
        assert listing.price_per_unit == Decimal("7500.00")
        assert listing.unit == "quintal"
        assert listing.is_deleted is False
        assert listing.deleted_at is None
        assert listing.status == STATUS_ACTIVE
        assert listing.farmer is sample_farmer
        assert listing.category is category

    def test_create_listing_with_images(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """Attach gallery images to a produce listing and verify ordering."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Sharbati Wheat",
            title="Fresh Sharbati Wheat",
            initial_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            unit=UNIT_QUINTAL,
            price_per_unit=Decimal("3200.00"),
            location_state="Madhya Pradesh",
            location_city="Sehore",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=60),
        )
        db_session.add(listing)
        db_session.commit()

        img1 = ListingImage(
            listing_id=listing.id,
            image_uri="storage/listings/wheat_thumbnail.jpg",
            is_primary=True,
            display_order=0,
        )
        img2 = ListingImage(
            listing_id=listing.id,
            image_uri="storage/listings/wheat_field.jpg",
            is_primary=False,
            display_order=1,
        )
        db_session.add_all([img1, img2])
        db_session.commit()

        db_session.refresh(listing)
        assert len(listing.images) == 2
        assert listing.images[0].is_primary is True
        assert listing.images[0].display_order == 0
        assert listing.images[1].is_primary is False
        assert listing.images[1].display_order == 1
        assert img1.listing is listing

    def test_extensible_unit_accepted(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """Flexible unit column accepts custom agricultural units without constraint error."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Kashmir Apples",
            title="Crisp Royal Delicious Apples",
            initial_quantity=Decimal("500.000"),
            available_quantity=Decimal("500.000"),
            unit="wooden_crate",  # Custom extensible unit
            price_per_unit=Decimal("1200.00"),
            location_state="Jammu and Kashmir",
            location_city="Shopian",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(listing)
        db_session.commit()
        db_session.refresh(listing)

        assert listing.unit == "wooden_crate"

    def test_soft_delete_preserves_row(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """Setting is_deleted=True and deleted_at retains the listing for audit trails."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Soybean",
            title="Yellow Soybean",
            initial_quantity=Decimal("20.000"),
            available_quantity=Decimal("20.000"),
            unit=UNIT_QUINTAL,
            price_per_unit=Decimal("4500.00"),
            location_state="Maharashtra",
            location_city="Latur",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=45),
        )
        db_session.add(listing)
        db_session.commit()

        # Mark soft deleted
        now = datetime.now(timezone.utc)
        listing.is_deleted = True
        listing.deleted_at = now
        listing.status = STATUS_CLOSED
        db_session.commit()
        db_session.refresh(listing)

        assert listing.is_deleted is True
        assert listing.deleted_at is not None
        assert listing.status == STATUS_CLOSED

    def test_bidirectional_user_listings_navigation(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """User.listings navigation correctly retrieves all listings by the farmer."""
        l1 = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Crop A",
            title="Crop A Title",
            initial_quantity=Decimal("10.000"),
            available_quantity=Decimal("10.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("50.00"),
            location_state="Punjab",
            location_city="Ludhiana",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        l2 = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Crop B",
            title="Crop B Title",
            initial_quantity=Decimal("20.000"),
            available_quantity=Decimal("20.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("75.00"),
            location_state="Punjab",
            location_city="Ludhiana",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add_all([l1, l2])
        db_session.commit()

        db_session.refresh(sample_farmer)
        assert len(sample_farmer.listings) == 2
        assert l1 in sample_farmer.listings
        assert l2 in sample_farmer.listings

    # -----------------------------------------------------------------------
    # Database Constraint Enforcement Tests
    # -----------------------------------------------------------------------

    def test_initial_quantity_must_be_positive(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """initial_quantity <= 0 violates chk_listings_initial_quantity."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Zero Quantity Crop",
            title="Zero Quantity Title",
            initial_quantity=Decimal("0.000"),
            available_quantity=Decimal("0.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("100.00"),
            location_state="Gujarat",
            location_city="Rajkot",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(listing)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_available_quantity_cannot_be_negative(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """available_quantity < 0 violates chk_listings_available_quantity."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Negative Quantity Crop",
            title="Negative Quantity Title",
            initial_quantity=Decimal("100.000"),
            available_quantity=Decimal("-5.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("100.00"),
            location_state="Gujarat",
            location_city="Rajkot",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(listing)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_available_quantity_cannot_exceed_initial(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """available_quantity > initial_quantity violates chk_listings_available_quantity."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Excess Quantity Crop",
            title="Excess Quantity Title",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("60.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("100.00"),
            location_state="Gujarat",
            location_city="Rajkot",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(listing)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_price_per_unit_must_be_positive(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """price_per_unit <= 0 violates chk_listings_price."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Free Crop",
            title="Free Crop Title",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("0.00"),
            location_state="Gujarat",
            location_city="Rajkot",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(listing)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_status_raises_integrity_error(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """Status outside permitted set violates chk_listings_status."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Bad Status Crop",
            title="Bad Status Title",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            price_per_unit=Decimal("100.00"),
            location_state="Gujarat",
            location_city="Rajkot",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            status="pending_approval",  # Invalid status string
        )
        db_session.add(listing)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_missing_mandatory_fields_raises_integrity_error(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """Missing required NOT NULL columns raises an IntegrityError."""
        # Missing product_name via raw SQL
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO produce_listings (id, farmer_id, title, initial_quantity, "
                    "available_quantity, unit, price_per_unit, location_state, location_city, "
                    "available_from, expires_at, created_at, updated_at) "
                    "VALUES (:id, :farmer_id, 'Title', 10.0, 10.0, 'kg', 50.0, 'State', 'City', "
                    "date('now'), datetime('now', '+30 days'), datetime('now'), datetime('now'))"
                ),
                {"id": uuid.uuid4().hex, "farmer_id": sample_farmer.id.hex},
            )
            db_session.commit()
        db_session.rollback()

    # -----------------------------------------------------------------------
    # Foreign Key Cascade & Restriction Tests
    # -----------------------------------------------------------------------

    def test_farmer_deletion_restricted_when_listings_exist(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """ON DELETE RESTRICT blocks deleting a farmer who has produce listings."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Wheat",
            title="Golden Wheat",
            initial_quantity=Decimal("10.000"),
            available_quantity=Decimal("10.000"),
            unit=UNIT_QUINTAL,
            price_per_unit=Decimal("2500.00"),
            location_state="Haryana",
            location_city="Karnal",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(listing)
        db_session.commit()

        # Deleting the farmer must fail with IntegrityError due to RESTRICT rule
        with pytest.raises(IntegrityError):
            db_session.delete(sample_farmer)
            db_session.commit()
        db_session.rollback()

    def test_category_deletion_sets_null_on_listings(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """ON DELETE SET NULL sets listing.category_id to NULL when category is removed."""
        category = ProduceCategory(name="Spices", slug="spices")
        db_session.add(category)
        db_session.commit()

        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            category_id=category.id,
            product_name="Cumin (Jeera)",
            title="Unpolished Whole Cumin",
            initial_quantity=Decimal("5.000"),
            available_quantity=Decimal("5.000"),
            unit=UNIT_QUINTAL,
            price_per_unit=Decimal("22000.00"),
            location_state="Rajasthan",
            location_city="Jodhpur",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=60),
        )
        db_session.add(listing)
        db_session.commit()

        # Delete category
        db_session.delete(category)
        db_session.commit()

        db_session.refresh(listing)
        assert listing.category_id is None
        assert listing.category is None

    def test_parent_category_deletion_sets_null_on_subcategories(
        self, db_session: Session
    ) -> None:
        """ON DELETE SET NULL sets subcategory.parent_id to NULL when parent is removed."""
        parent = ProduceCategory(name="Fruits", slug="fruits")
        db_session.add(parent)
        db_session.commit()

        child = ProduceCategory(parent_id=parent.id, name="Citrus", slug="citrus")
        db_session.add(child)
        db_session.commit()

        # Delete parent category
        db_session.delete(parent)
        db_session.commit()

        db_session.refresh(child)
        assert child.parent_id is None
        assert child.parent is None

    def test_listing_deletion_cascades_to_images(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """ON DELETE CASCADE deletes all attached images when the parent listing is deleted."""
        listing = ProduceListing(
            farmer_id=sample_farmer.id,
            product_name="Mango",
            title="Alphonso Mango",
            initial_quantity=Decimal("20.000"),
            available_quantity=Decimal("20.000"),
            unit="box",
            price_per_unit=Decimal("1500.00"),
            location_state="Maharashtra",
            location_city="Ratnagiri",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=20),
        )
        db_session.add(listing)
        db_session.commit()

        img = ListingImage(
            listing_id=listing.id,
            image_uri="storage/listings/alphonso.jpg",
            is_primary=True,
        )
        db_session.add(img)
        db_session.commit()
        img_id = img.id

        # Delete listing
        db_session.delete(listing)
        db_session.commit()

        # Image must be gone
        deleted_img = db_session.get(ListingImage, img_id)
        assert deleted_img is None
