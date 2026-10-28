"""Automated unit and integration tests for BuyerRequirement ORM model.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``buyer_requirements``
- Column definitions, data types, precision, scale, nullabilities, and defaults
- Primary key generation via ``UUIDPrimaryKeyMixin``
- ``TimestampMixin`` usage (created_at and updated_at present)
- Foreign key definitions and on-delete rules:
  - ``buyer_requirements.buyer_id -> users.id`` (ON DELETE RESTRICT)
  - ``buyer_requirements.category_id -> produce_categories.id`` (ON DELETE SET NULL)
- Table-level indexes across buyer requirements:
  - ``idx_requirements_buyer`` on (buyer_id)
  - ``idx_requirements_category_status`` on (category_id, status, is_deleted)
  - ``idx_requirements_deadline`` on (required_by_date)
- Check constraints on ``buyer_requirements``:
  - ``chk_requirements_required_quantity`` (required_quantity > 0)
  - ``chk_requirements_remaining_quantity`` (remaining_quantity >= 0 AND remaining_quantity <= required_quantity)
  - ``chk_requirements_target_price`` (target_price_per_unit IS NULL OR target_price_per_unit > 0)
  - ``chk_requirements_price_condition`` (exact, range, negotiable)
  - ``chk_requirements_status`` (draft, active, partially_fulfilled, closed, expired)
- Database execution:
  - Valid requirement creation with full fields and decimal precision
  - Minimal requirement creation with defaults (status='active', price_condition='negotiable', is_deleted=False)
  - Extensible produce unit values (no DB-level check constraint)
  - Soft-delete field persistence (is_deleted, deleted_at)
  - All valid lifecycle statuses and price conditions
  - Bidirectional ORM navigation (User.requirements, ProduceCategory.requirements, BuyerRequirement.buyer, BuyerRequirement.category)
  - Database enforcement of check constraints (IntegrityError on violations)
  - Database enforcement of NOT NULL constraints on mandatory fields
  - Deletion restriction on buyer (ON DELETE RESTRICT)
  - SET NULL on category deletion (ON DELETE SET NULL)
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
    UNIT_BAG,
    UNIT_KG,
    UNIT_METRIC_TON,
    UNIT_QUINTAL,
    ProduceCategory,
)
from app.models.requirement import (
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
    PRICE_CONDITION_RANGE,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_DRAFT,
    REQUIREMENT_STATUS_EXPIRED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    VALID_PRICE_CONDITIONS,
    VALID_REQUIREMENT_STATUSES,
    BuyerRequirement,
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
def sample_buyer(db_session: Session) -> User:
    """Create and persist a verified commercial buyer user."""
    buyer = User(
        email="procurement_buyer@agridirect.test",
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
def sample_category(db_session: Session) -> ProduceCategory:
    """Create and persist a produce category."""
    category = ProduceCategory(
        name="Pulses & Legumes",
        slug="pulses-legumes",
        is_active=True,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestBuyerRequirementMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_table_registered_in_metadata(self) -> None:
        """buyer_requirements must be registered in Base.metadata."""
        assert "buyer_requirements" in Base.metadata.tables

    def test_buyer_requirements_columns_and_nullability(self) -> None:
        """buyer_requirements must have all 20 specified columns with exact nullabilities."""
        table = Base.metadata.tables["buyer_requirements"]

        expected_columns = {
            # col_name: nullable
            "id": False,
            "buyer_id": False,
            "category_id": True,
            "product_name": False,
            "title": False,
            "description": True,
            "required_quantity": False,
            "remaining_quantity": False,
            "unit": False,
            "target_price_per_unit": True,
            "price_condition": False,
            "quality_grade": True,
            "destination_state": False,
            "destination_city": False,
            "required_by_date": False,
            "status": False,
            "is_deleted": False,
            "deleted_at": True,
            "created_at": False,
            "updated_at": False,
        }

        assert len(table.columns) == 20, (
            f"Expected exactly 20 columns on buyer_requirements, got {len(table.columns)}: "
            f"{[c.name for c in table.columns]}"
        )

        for col_name, nullable in expected_columns.items():
            assert col_name in table.c, f"Column '{col_name}' missing from buyer_requirements"
            assert table.c[col_name].nullable == nullable, (
                f"Column '{col_name}' nullable expected {nullable}, got {table.c[col_name].nullable}"
            )

    def test_primary_key_and_mixins(self) -> None:
        """buyer_requirements must use UUID primary key and TimestampMixin."""
        table = Base.metadata.tables["buyer_requirements"]

        # Primary key: id is UUID
        assert "id" in table.primary_key.columns
        pk_col = table.c.id
        assert isinstance(pk_col.type, PG_UUID)
        assert pk_col.type.as_uuid is True

        # TimestampMixin columns present
        assert "created_at" in table.c
        assert "updated_at" in table.c

    def test_foreign_keys_and_on_delete_rules(self) -> None:
        """Foreign keys must point to correct tables with required on-delete actions."""
        table = Base.metadata.tables["buyer_requirements"]
        fks = {fk.parent.name: fk for fk in table.foreign_keys}

        assert "buyer_id" in fks, "Missing FK on buyer_id"
        assert fks["buyer_id"].column.table.name == "users"
        assert fks["buyer_id"].ondelete == "RESTRICT"

        assert "category_id" in fks, "Missing FK on category_id"
        assert fks["category_id"].column.table.name == "produce_categories"
        assert fks["category_id"].ondelete == "SET NULL"

    def test_numeric_precision_and_scale(self) -> None:
        """Quantities must be NUMERIC(12, 3) and price must be NUMERIC(12, 2)."""
        table = Base.metadata.tables["buyer_requirements"]
        assert table.c.required_quantity.type.precision == 12
        assert table.c.required_quantity.type.scale == 3
        assert table.c.remaining_quantity.type.precision == 12
        assert table.c.remaining_quantity.type.scale == 3
        assert table.c.target_price_per_unit.type.precision == 12
        assert table.c.target_price_per_unit.type.scale == 2

    def test_buyer_requirements_check_constraints(self) -> None:
        """buyer_requirements must define all five required check constraints."""
        table = Base.metadata.tables["buyer_requirements"]
        check_names = {c.name for c in table.constraints if hasattr(c, "sqltext")}
        expected_checks = {
            "chk_requirements_required_quantity",
            "chk_requirements_remaining_quantity",
            "chk_requirements_target_price",
            "chk_requirements_price_condition",
            "chk_requirements_status",
        }
        assert expected_checks.issubset(check_names), (
            f"Missing check constraints. Expected: {expected_checks}, got: {check_names}"
        )

    def test_buyer_requirements_indexes(self) -> None:
        """buyer_requirements must define all three required named indexes."""
        table = Base.metadata.tables["buyer_requirements"]
        indexes = {idx.name: [c.name for c in idx.columns] for idx in table.indexes}

        assert "idx_requirements_buyer" in indexes
        assert indexes["idx_requirements_buyer"] == ["buyer_id"]

        assert "idx_requirements_category_status" in indexes
        assert indexes["idx_requirements_category_status"] == ["category_id", "status", "is_deleted"]

        assert "idx_requirements_deadline" in indexes
        assert indexes["idx_requirements_deadline"] == ["required_by_date"]

    def test_canonical_constants(self) -> None:
        """Canonical status, price condition, and unit constants must match specifications."""
        assert REQUIREMENT_STATUS_DRAFT == "draft"
        assert REQUIREMENT_STATUS_ACTIVE == "active"
        assert REQUIREMENT_STATUS_PARTIALLY_FULFILLED == "partially_fulfilled"
        assert REQUIREMENT_STATUS_CLOSED == "closed"
        assert REQUIREMENT_STATUS_EXPIRED == "expired"
        assert set(VALID_REQUIREMENT_STATUSES) == {
            "draft",
            "active",
            "partially_fulfilled",
            "closed",
            "expired",
        }

        assert PRICE_CONDITION_EXACT == "exact"
        assert PRICE_CONDITION_RANGE == "range"
        assert PRICE_CONDITION_NEGOTIABLE == "negotiable"
        assert set(VALID_PRICE_CONDITIONS) == {"exact", "range", "negotiable"}

        # Canonical units reused from listing.py
        assert set(CANONICAL_UNITS) == {"kg", "quintal", "metric_ton", "bag"}


# ===========================================================================
# 2. Database Operations & Persistence Tests
# ===========================================================================


class TestBuyerRequirementPersistence:
    """Verify CRUD and database persistence behaviors."""

    def test_create_requirement_with_all_fields(
        self, db_session: Session, sample_buyer: User, sample_category: ProduceCategory
    ) -> None:
        """Persist requirement with all optional fields explicitly specified."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            category_id=sample_category.id,
            product_name="Kabuli Chickpeas",
            title="Bulk A-grade Kabuli Chickpeas Needed",
            description="Seeking 20 MT export-quality chickpeas for canning plant.",
            required_quantity=Decimal("20000.000"),
            remaining_quantity=Decimal("20000.000"),
            unit=UNIT_KG,
            target_price_per_unit=Decimal("85.50"),
            price_condition=PRICE_CONDITION_EXACT,
            quality_grade="Grade A",
            destination_state="Maharashtra",
            destination_city="Navi Mumbai",
            required_by_date=date.today() + timedelta(days=45),
            status=REQUIREMENT_STATUS_ACTIVE,
            is_deleted=False,
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        assert isinstance(req.id, uuid.UUID)
        assert req.buyer_id == sample_buyer.id
        assert req.category_id == sample_category.id
        assert req.product_name == "Kabuli Chickpeas"
        assert req.title == "Bulk A-grade Kabuli Chickpeas Needed"
        assert req.description == "Seeking 20 MT export-quality chickpeas for canning plant."
        assert req.required_quantity == Decimal("20000.000")
        assert req.remaining_quantity == Decimal("20000.000")
        assert req.unit == "kg"
        assert req.target_price_per_unit == Decimal("85.50")
        assert req.price_condition == "exact"
        assert req.quality_grade == "Grade A"
        assert req.destination_state == "Maharashtra"
        assert req.destination_city == "Navi Mumbai"
        assert req.status == "active"
        assert req.is_deleted is False
        assert req.deleted_at is None
        assert req.created_at is not None
        assert req.updated_at is not None

    def test_create_requirement_with_minimal_fields_and_defaults(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Persist requirement with only mandatory fields, verifying model defaults."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Mustard Seed",
            title="Clean Mustard Seed Wanted",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_QUINTAL,
            destination_state="Rajasthan",
            destination_city="Jaipur",
            required_by_date=date.today() + timedelta(days=20),
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        assert req.category_id is None
        assert req.description is None
        assert req.target_price_per_unit is None
        assert req.quality_grade is None
        assert req.price_condition == PRICE_CONDITION_NEGOTIABLE
        assert req.status == REQUIREMENT_STATUS_ACTIVE
        assert req.is_deleted is False
        assert req.deleted_at is None

    def test_extensible_produce_units(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Units are extensible free text with no DB constraint restricting values."""
        units_to_test = [UNIT_KG, UNIT_QUINTAL, UNIT_METRIC_TON, UNIT_BAG, "box", "crate", "ton"]
        for idx, unit_str in enumerate(units_to_test):
            req = BuyerRequirement(
                buyer_id=sample_buyer.id,
                product_name=f"Crop {idx}",
                title=f"Requirement for unit {unit_str}",
                required_quantity=Decimal("100.000"),
                remaining_quantity=Decimal("100.000"),
                unit=unit_str,
                destination_state="Delhi",
                destination_city="New Delhi",
                required_by_date=date.today() + timedelta(days=15),
            )
            db_session.add(req)
        db_session.commit()

    def test_soft_delete_persistence(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Setting is_deleted and deleted_at updates the requirement record cleanly."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Basmati Rice",
            title="Pusa 1121 Paddy/Rice",
            required_quantity=Decimal("10.000"),
            remaining_quantity=Decimal("10.000"),
            unit=UNIT_METRIC_TON,
            destination_state="Punjab",
            destination_city="Amritsar",
            required_by_date=date.today() + timedelta(days=30),
        )
        db_session.add(req)
        db_session.commit()

        # Perform soft delete
        now_utc = datetime.now(timezone.utc)
        req.is_deleted = True
        req.deleted_at = now_utc
        db_session.commit()
        db_session.refresh(req)

        assert req.is_deleted is True
        assert req.deleted_at is not None

    def test_all_lifecycle_statuses_persisted(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Every status in VALID_REQUIREMENT_STATUSES can be saved in the database."""
        for status_val in VALID_REQUIREMENT_STATUSES:
            req = BuyerRequirement(
                buyer_id=sample_buyer.id,
                product_name=f"Product for {status_val}",
                title=f"Title for {status_val}",
                required_quantity=Decimal("10.000"),
                remaining_quantity=Decimal("10.000"),
                unit=UNIT_KG,
                destination_state="Karnataka",
                destination_city="Bengaluru",
                required_by_date=date.today() + timedelta(days=10),
                status=status_val,
            )
            db_session.add(req)
        db_session.commit()

    def test_all_price_conditions_persisted(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Every condition in VALID_PRICE_CONDITIONS can be saved in the database."""
        for cond in VALID_PRICE_CONDITIONS:
            req = BuyerRequirement(
                buyer_id=sample_buyer.id,
                product_name=f"Product for {cond}",
                title=f"Title for {cond}",
                required_quantity=Decimal("10.000"),
                remaining_quantity=Decimal("10.000"),
                unit=UNIT_KG,
                destination_state="Gujarat",
                destination_city="Surat",
                required_by_date=date.today() + timedelta(days=10),
                price_condition=cond,
            )
            db_session.add(req)
        db_session.commit()


# ===========================================================================
# 3. Database Check Constraint & NOT NULL Enforcement Tests
# ===========================================================================


class TestBuyerRequirementCheckConstraints:
    """Verify that SQLite runtime rejects records violating check constraints."""

    def test_required_quantity_must_be_positive_zero_fails(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """required_quantity == 0 violates chk_requirements_required_quantity."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Zero Quantity Product",
            title="Zero Quantity",
            required_quantity=Decimal("0.000"),
            remaining_quantity=Decimal("0.000"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_required_quantity_must_be_positive_negative_fails(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """required_quantity < 0 violates chk_requirements_required_quantity."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Negative Quantity Product",
            title="Negative Quantity",
            required_quantity=Decimal("-10.000"),
            remaining_quantity=Decimal("-10.000"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_remaining_quantity_cannot_be_negative(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """remaining_quantity < 0 violates chk_requirements_remaining_quantity."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Negative Remaining Product",
            title="Negative Remaining",
            required_quantity=Decimal("100.000"),
            remaining_quantity=Decimal("-0.001"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_remaining_quantity_cannot_exceed_required_quantity(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """remaining_quantity > required_quantity violates chk_requirements_remaining_quantity."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Excess Remaining Product",
            title="Excess Remaining",
            required_quantity=Decimal("100.000"),
            remaining_quantity=Decimal("100.001"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_remaining_quantity_boundary_values_allowed(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """remaining_quantity == 0 and remaining_quantity == required_quantity are both valid."""
        # 1. remaining == 0 (fully fulfilled requirement)
        req_fulfilled = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Fulfilled Crop",
            title="Fulfilled Requirement",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("0.000"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
            status=REQUIREMENT_STATUS_CLOSED,
        )
        # 2. remaining == required (new unfulfilled requirement)
        req_new = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="New Crop",
            title="New Requirement",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add_all([req_fulfilled, req_new])
        db_session.commit()

    def test_target_price_per_unit_must_be_positive_when_specified(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """target_price_per_unit <= 0 violates chk_requirements_target_price."""
        # 1. Zero price fails
        req_zero = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Free Demand Crop",
            title="Zero Price Demand",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            target_price_per_unit=Decimal("0.00"),
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req_zero)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

        # 2. Negative price fails
        req_neg = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Negative Demand Crop",
            title="Negative Price Demand",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            target_price_per_unit=Decimal("-5.00"),
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req_neg)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_target_price_null_is_allowed(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """target_price_per_unit IS NULL satisfies chk_requirements_target_price."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Unpriced Crop",
            title="Open Price Demand",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            target_price_per_unit=None,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
        )
        db_session.add(req)
        db_session.commit()
        assert req.target_price_per_unit is None

    def test_invalid_price_condition_raises_integrity_error(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Price condition outside ('exact', 'range', 'negotiable') violates constraint."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Bad Condition Crop",
            title="Bad Condition Title",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
            price_condition="flexible",  # Invalid
        )
        db_session.add(req)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_invalid_status_raises_integrity_error(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Status outside permitted set violates chk_requirements_status."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Bad Status Crop",
            title="Bad Status Title",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_KG,
            destination_state="Haryana",
            destination_city="Karnal",
            required_by_date=date.today() + timedelta(days=10),
            status="pending_approval",  # Invalid
        )
        db_session.add(req)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_missing_mandatory_fields_raises_integrity_error(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """Omitting required non-nullable fields raises IntegrityError at DB level."""
        # Missing product_name
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO buyer_requirements (id, buyer_id, title, required_quantity, "
                    "remaining_quantity, unit, destination_state, destination_city, required_by_date) "
                    "VALUES (:id, :bid, 'Test Title', 10, 10, 'kg', 'State', 'City', '2026-11-01')"
                ),
                {"id": str(uuid.uuid4()), "bid": str(sample_buyer.id)},
            )
            db_session.commit()
        db_session.rollback()


# ===========================================================================
# 4. Bidirectional Relationships & FK Deletion Behavior Tests
# ===========================================================================


class TestBuyerRequirementRelationshipsAndDeletions:
    """Verify relationships and foreign-key cascade/restrict behavior."""

    def test_buyer_requirements_bidirectional_relationship(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """User.requirements and BuyerRequirement.buyer correctly navigate bidirectionally."""
        req1 = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Wheat",
            title="Sharbati Wheat Needed",
            required_quantity=Decimal("100.000"),
            remaining_quantity=Decimal("100.000"),
            unit=UNIT_QUINTAL,
            destination_state="Madhya Pradesh",
            destination_city="Indore",
            required_by_date=date.today() + timedelta(days=25),
        )
        req2 = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Barley",
            title="Feed Barley Needed",
            required_quantity=Decimal("200.000"),
            remaining_quantity=Decimal("200.000"),
            unit=UNIT_QUINTAL,
            destination_state="Rajasthan",
            destination_city="Kota",
            required_by_date=date.today() + timedelta(days=35),
        )
        db_session.add_all([req1, req2])
        db_session.commit()

        # Buyer -> requirements
        db_session.refresh(sample_buyer)
        buyer_req_ids = {r.id for r in sample_buyer.requirements}
        assert req1.id in buyer_req_ids
        assert req2.id in buyer_req_ids

        # Requirement -> buyer
        db_session.refresh(req1)
        assert req1.buyer.id == sample_buyer.id
        assert req1.buyer.email == sample_buyer.email

    def test_category_requirements_bidirectional_relationship(
        self, db_session: Session, sample_buyer: User, sample_category: ProduceCategory
    ) -> None:
        """ProduceCategory.requirements and BuyerRequirement.category navigate bidirectionally."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            category_id=sample_category.id,
            product_name="Green Gram (Moong)",
            title="Moong Dal Whole",
            required_quantity=Decimal("30.000"),
            remaining_quantity=Decimal("30.000"),
            unit=UNIT_QUINTAL,
            destination_state="Maharashtra",
            destination_city="Pune",
            required_by_date=date.today() + timedelta(days=15),
        )
        db_session.add(req)
        db_session.commit()

        # Category -> requirements
        db_session.refresh(sample_category)
        assert len(sample_category.requirements) == 1
        assert sample_category.requirements[0].id == req.id

        # Requirement -> category
        db_session.refresh(req)
        assert req.category is not None
        assert req.category.id == sample_category.id
        assert req.category.name == sample_category.name

    def test_buyer_deletion_is_restricted(
        self, db_session: Session, sample_buyer: User
    ) -> None:
        """ON DELETE RESTRICT prevents deleting a User who has posted requirements."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            product_name="Soybean",
            title="Organic Soybean for Crushing",
            required_quantity=Decimal("50.000"),
            remaining_quantity=Decimal("50.000"),
            unit=UNIT_METRIC_TON,
            destination_state="Madhya Pradesh",
            destination_city="Ujjain",
            required_by_date=date.today() + timedelta(days=20),
        )
        db_session.add(req)
        db_session.commit()

        # Attempting to delete the buyer user must raise IntegrityError
        db_session.delete(sample_buyer)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_category_deletion_sets_null_on_requirements(
        self, db_session: Session, sample_buyer: User, sample_category: ProduceCategory
    ) -> None:
        """ON DELETE SET NULL sets requirement.category_id to NULL when the category is deleted."""
        req = BuyerRequirement(
            buyer_id=sample_buyer.id,
            category_id=sample_category.id,
            product_name="Black Gram (Urad)",
            title="Premium Urad Dal",
            required_quantity=Decimal("40.000"),
            remaining_quantity=Decimal("40.000"),
            unit=UNIT_QUINTAL,
            destination_state="Andhra Pradesh",
            destination_city="Guntur",
            required_by_date=date.today() + timedelta(days=30),
        )
        db_session.add(req)
        db_session.commit()

        # Delete category
        db_session.delete(sample_category)
        db_session.commit()

        # Refresh requirement and confirm category_id is set to None
        db_session.refresh(req)
        assert req.category_id is None
        assert req.category is None
