"""Automated unit and integration tests for Phase 2, Group 1 ORM models.

Tests cover:
- Model registration in ``Base.metadata``
- Expected columns, nullabilities, and PostgreSQL types
- Foreign keys, on-delete cascade rules, and unique constraints
- Check constraints and composite indexes
- Valid and invalid role / status / business_type values
- Profile relationships and duplicate-profile prevention
- Role/profile consistency enforcement at application layer
- Timestamp defaults and ORM update semantics
- Sensitive credential protection in string representations (__repr__)
- Unidirectional cascade preservation (deleting profile preserves user)

Testing Strategy:
- Metadata and schema definitions are inspected directly from ``Base.metadata``.
- Object lifecycle, validators, and relationships are exercised using an
  isolated in-memory SQLite session with full cascade and foreign key support.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import (
    VALID_ACCOUNT_STATUSES,
    VALID_BUYER_TYPES,
    VALID_USER_ROLES,
    VALID_VERIFICATION_STATUSES,
    BuyerProfile,
    FarmerProfile,
    User,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database engine with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
    )

    # Enable SQLite foreign key constraint enforcement
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
    """Provide a transactional SQLAlchemy session bound to the in-memory engine."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session: Session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


# ===========================================================================
# 1. Metadata and Registration Tests
# ===========================================================================


def test_models_registered_in_base_metadata():
    """Verify all Group 1 models are registered in Base.metadata for Alembic discovery."""
    tables = Base.metadata.tables.keys()
    assert "users" in tables, "users table missing from Base.metadata"
    assert "farmer_profiles" in tables, "farmer_profiles table missing from Base.metadata"
    assert "buyer_profiles" in tables, "buyer_profiles table missing from Base.metadata"


def test_users_table_columns_and_types():
    """Verify columns, PostgreSQL types, and nullabilities on the users table."""
    table = Base.metadata.tables["users"]
    col_names = {c.name for c in table.columns}
    expected = {
        "id",
        "email",
        "phone_number",
        "password_hash",
        "role",
        "verification_status",
        "account_status",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(col_names)

    # PostgreSQL UUID on primary key
    assert isinstance(table.columns["id"].type, PG_UUID)
    assert table.columns["id"].primary_key is True

    # Email must be non-nullable and unique
    assert table.columns["email"].nullable is False
    assert table.columns["email"].unique is True

    # Phone number must be nullable per SRS 'phone/email' requirement, but unique
    assert table.columns["phone_number"].nullable is True
    assert table.columns["phone_number"].unique is True

    # Timezone-aware timestamps
    assert table.columns["created_at"].type.timezone is True
    assert table.columns["updated_at"].type.timezone is True


def test_farmer_profiles_table_columns_and_types():
    """Verify columns and types on the farmer_profiles table."""
    table = Base.metadata.tables["farmer_profiles"]
    col_names = {c.name for c in table.columns}
    expected = {
        "id",
        "user_id",
        "full_name",
        "farm_name",
        "farm_location_address",
        "city",
        "state",
        "postal_code",
        "latitude",
        "longitude",
        "farm_size_acres",
        "farming_practices",
        "primary_crops",
        "bio",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(col_names)

    # user_id must be unique (enforcing 1:1) and non-nullable
    assert table.columns["user_id"].nullable is False
    assert table.columns["user_id"].unique is True

    # Foreign key referencing users.id with CASCADE on delete
    fks = list(table.columns["user_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "users.id"
    assert fks[0].ondelete == "CASCADE"


def test_buyer_profiles_table_columns_and_types():
    """Verify columns and types on the buyer_profiles table."""
    table = Base.metadata.tables["buyer_profiles"]
    col_names = {c.name for c in table.columns}
    expected = {
        "id",
        "user_id",
        "contact_person_name",
        "business_name",
        "business_type",
        "business_registration_number",
        "delivery_receiving_address",
        "city",
        "state",
        "postal_code",
        "latitude",
        "longitude",
        "procurement_summary",
        "bio",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(col_names)

    # user_id must be unique (enforcing 1:1) and non-nullable
    assert table.columns["user_id"].nullable is False
    assert table.columns["user_id"].unique is True

    # Foreign key referencing users.id with CASCADE on delete
    fks = list(table.columns["user_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "users.id"
    assert fks[0].ondelete == "CASCADE"


def test_no_redundant_single_column_indexes():
    """Verify that columns with unique constraints do not have redundant ordinary indexes."""
    users_table = Base.metadata.tables["users"]
    # email and phone_number have unique=True; no separate index on just email or phone
    index_columns = [
        tuple(c.name for c in idx.columns)
        for idx in users_table.indexes
        if not idx.unique
    ]
    assert ("email",) not in index_columns, "Redundant ordinary index found on email"
    assert ("phone_number",) not in index_columns, "Redundant ordinary index found on phone_number"


def test_table_check_constraints_and_composite_indexes():
    """Verify defined check constraints and multi-column indexes in Base.metadata."""
    users_table = Base.metadata.tables["users"]
    constraint_names = {c.name for c in users_table.constraints}
    assert "chk_users_role" in constraint_names
    assert "chk_users_verification_status" in constraint_names
    assert "chk_users_account_status" in constraint_names

    user_index_names = {idx.name for idx in users_table.indexes}
    assert "idx_users_role_status" in user_index_names

    farmer_table = Base.metadata.tables["farmer_profiles"]
    farmer_constraints = {c.name for c in farmer_table.constraints}
    assert "chk_farmer_size_positive" in farmer_constraints
    assert "idx_farmer_profiles_location" in {idx.name for idx in farmer_table.indexes}

    buyer_table = Base.metadata.tables["buyer_profiles"]
    buyer_constraints = {c.name for c in buyer_table.constraints}
    assert "chk_buyer_business_type" in buyer_constraints
    assert "idx_buyer_profiles_business_type" in {idx.name for idx in buyer_table.indexes}
    assert "idx_buyer_profiles_location" in {idx.name for idx in buyer_table.indexes}


# ===========================================================================
# 2. Validation and Domain Constraint Tests
# ===========================================================================


@pytest.mark.parametrize("role", VALID_USER_ROLES)
def test_valid_user_roles(role):
    """Verify all valid roles can be instantiated."""
    user = User(
        email=f"{role}@example.com",
        password_hash="hashed_pw_123",
        role=role,
    )
    assert user.role == role


def test_invalid_user_role_raises_value_error():
    """Verify that invalid role raises a ValueError at application level."""
    with pytest.raises(ValueError, match="Invalid role 'superadmin'"):
        User(
            email="invalid@example.com",
            password_hash="hashed_pw_123",
            role="superadmin",
        )


@pytest.mark.parametrize("status", VALID_VERIFICATION_STATUSES)
def test_valid_verification_statuses(status):
    """Verify all valid verification statuses pass validation."""
    user = User(
        email="test@example.com",
        password_hash="hashed_pw_123",
        role="farmer",
        verification_status=status,
    )
    assert user.verification_status == status


def test_invalid_verification_status_raises_value_error():
    """Verify invalid verification_status raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid verification_status 'approved'"):
        User(
            email="test@example.com",
            password_hash="hashed_pw_123",
            role="farmer",
            verification_status="approved",  # Valid is 'verified'
        )


@pytest.mark.parametrize("status", VALID_ACCOUNT_STATUSES)
def test_valid_account_statuses(status):
    """Verify all valid account statuses pass validation."""
    user = User(
        email="test@example.com",
        password_hash="hashed_pw_123",
        role="farmer",
        account_status=status,
    )
    assert user.account_status == status


def test_invalid_account_status_raises_value_error():
    """Verify invalid account_status raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid account_status 'deleted'"):
        User(
            email="test@example.com",
            password_hash="hashed_pw_123",
            role="farmer",
            account_status="deleted",
        )


@pytest.mark.parametrize("b_type", VALID_BUYER_TYPES)
def test_valid_buyer_types(b_type):
    """Verify all defined buyer commercial types pass validation."""
    profile = BuyerProfile(
        contact_person_name="Contact",
        business_name="Biz",
        business_type=b_type,
        delivery_receiving_address="123 Street",
        city="Nagpur",
        state="Maharashtra",
        postal_code="440001",
    )
    assert profile.business_type == b_type


def test_invalid_buyer_type_raises_value_error():
    """Verify invalid business_type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid business_type 'individual'"):
        BuyerProfile(
            contact_person_name="Contact",
            business_name="Biz",
            business_type="individual",
            delivery_receiving_address="123 Street",
            city="Nagpur",
            state="Maharashtra",
            postal_code="440001",
        )


def test_farmer_size_acres_positive():
    """Verify positive farm size is accepted and non-positive raises ValueError."""
    profile = FarmerProfile(
        full_name="Ramesh Kumar",
        farm_name="Ramesh Farms",
        farm_location_address="Village Post",
        city="Nashik",
        state="Maharashtra",
        postal_code="422001",
        farm_size_acres=Decimal("25.50"),
    )
    assert profile.farm_size_acres == Decimal("25.50")

    with pytest.raises(ValueError, match="farm_size_acres must be strictly positive"):
        FarmerProfile(
            full_name="Ramesh Kumar",
            farm_name="Ramesh Farms",
            farm_location_address="Village Post",
            city="Nashik",
            state="Maharashtra",
            postal_code="422001",
            farm_size_acres=Decimal("-5.00"),
        )


# ===========================================================================
# 3. Role/Profile Consistency Application-Level Enforcement Tests
# ===========================================================================


def test_role_profile_consistency_farmer():
    """Verify that a farmer profile can only be attached to a farmer user."""
    farmer = User(
        email="farmer@example.com",
        password_hash="hashed_pw",
        role="farmer",
    )
    f_profile = FarmerProfile(
        full_name="Suresh Patel",
        farm_name="Patel Agro",
        farm_location_address="Farm Rd",
        city="Surat",
        state="Gujarat",
        postal_code="395001",
    )
    # Valid attachment
    farmer.farmer_profile = f_profile
    assert farmer.farmer_profile.farm_name == "Patel Agro"

    # Attaching farmer profile to buyer user must fail
    buyer = User(
        email="buyer@example.com",
        password_hash="hashed_pw",
        role="buyer",
    )
    with pytest.raises(ValueError, match="Cannot attach FarmerProfile to user with role 'buyer'"):
        buyer.farmer_profile = f_profile


def test_role_profile_consistency_buyer():
    """Verify that a buyer profile can only be attached to a buyer user."""
    buyer = User(
        email="buyer@example.com",
        password_hash="hashed_pw",
        role="buyer",
    )
    b_profile = BuyerProfile(
        contact_person_name="Anil Shah",
        business_name="Fresh Mart",
        business_type="retailer",
        delivery_receiving_address="Market Yard",
        city="Pune",
        state="Maharashtra",
        postal_code="411037",
    )
    # Valid attachment
    buyer.buyer_profile = b_profile
    assert buyer.buyer_profile.business_name == "Fresh Mart"

    # Attaching buyer profile to farmer user must fail
    farmer = User(
        email="farmer@example.com",
        password_hash="hashed_pw",
        role="farmer",
    )
    with pytest.raises(ValueError, match="Cannot attach BuyerProfile to user with role 'farmer'"):
        farmer.buyer_profile = b_profile


def test_profile_reverse_assignment_validation():
    """Verify assigning a mismatched user on the profile side raises ValueError."""
    farmer = User(email="farmer@example.com", password_hash="pw", role="farmer")
    buyer = User(email="buyer@example.com", password_hash="pw", role="buyer")

    f_profile = FarmerProfile(
        full_name="Farmer A",
        farm_name="Farm A",
        farm_location_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    # Assigning buyer to FarmerProfile.user must raise ValueError
    with pytest.raises(ValueError, match="FarmerProfile can only be associated with a user having role='farmer'"):
        f_profile.user = buyer

    b_profile = BuyerProfile(
        contact_person_name="Buyer A",
        business_name="Biz A",
        business_type="hotel",
        delivery_receiving_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    # Assigning farmer to BuyerProfile.user must raise ValueError
    with pytest.raises(ValueError, match="BuyerProfile can only be associated with a user having role='buyer'"):
        b_profile.user = farmer


def test_role_profile_consistency_admin():
    """Verify that an admin user cannot be assigned a FarmerProfile or BuyerProfile."""
    admin = User(email="admin@example.com", password_hash="pw", role="admin")
    f_profile = FarmerProfile(
        full_name="Admin Farmer",
        farm_name="Admin Farm",
        farm_location_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    b_profile = BuyerProfile(
        contact_person_name="Admin Buyer",
        business_name="Admin Biz",
        business_type="hotel",
        delivery_receiving_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )

    # User side
    with pytest.raises(ValueError, match="Cannot attach FarmerProfile to user with role 'admin'"):
        admin.farmer_profile = f_profile

    with pytest.raises(ValueError, match="Cannot attach BuyerProfile to user with role 'admin'"):
        admin.buyer_profile = b_profile

    # Profile side
    with pytest.raises(ValueError, match="FarmerProfile can only be associated with a user having role='farmer'"):
        f_profile.user = admin

    with pytest.raises(ValueError, match="BuyerProfile can only be associated with a user having role='buyer'"):
        b_profile.user = admin


def test_role_mutation_prevented_when_profile_attached():
    """Verify that mutating user.role fails when an existing profile is incompatible."""
    farmer = User(email="f_mutate@example.com", password_hash="pw", role="farmer")
    f_profile = FarmerProfile(
        full_name="Farmer M",
        farm_name="Farm M",
        farm_location_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    farmer.farmer_profile = f_profile

    # Farmer cannot switch to buyer or admin while profile is attached
    with pytest.raises(ValueError, match="Cannot change role to 'buyer' while FarmerProfile is attached"):
        farmer.role = "buyer"

    with pytest.raises(ValueError, match="Cannot change role to 'admin' while FarmerProfile is attached"):
        farmer.role = "admin"

    buyer = User(email="b_mutate@example.com", password_hash="pw", role="buyer")
    b_profile = BuyerProfile(
        contact_person_name="Buyer M",
        business_name="Biz M",
        business_type="retailer",
        delivery_receiving_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    buyer.buyer_profile = b_profile

    # Buyer cannot switch to farmer or admin while profile is attached
    with pytest.raises(ValueError, match="Cannot change role to 'farmer' while BuyerProfile is attached"):
        buyer.role = "farmer"

    with pytest.raises(ValueError, match="Cannot change role to 'admin' while BuyerProfile is attached"):
        buyer.role = "admin"


# ===========================================================================
# 4. Session Persistence, Duplicate Prevention, and Cascade Tests
# ===========================================================================


def test_persist_farmer_user_and_profile(db_session: Session):
    """Test persisting User and FarmerProfile into the database."""
    farmer = User(
        email="farmer1@agridirect.com",
        phone_number="+919876543210",
        password_hash="argon2_hashed_secret",
        role="farmer",
    )
    profile = FarmerProfile(
        full_name="Kisan Singh",
        farm_name="Green Acres Farm",
        farm_location_address="Gat No 12",
        city="Nashik",
        state="Maharashtra",
        postal_code="422003",
        farm_size_acres=Decimal("15.75"),
        farming_practices="organic",
    )
    farmer.farmer_profile = profile

    db_session.add(farmer)
    db_session.commit()

    # Query back
    saved_user = db_session.query(User).filter_by(email="farmer1@agridirect.com").one()
    assert saved_user.id is not None
    assert isinstance(saved_user.id, uuid.UUID)
    assert saved_user.farmer_profile is not None
    assert saved_user.farmer_profile.user_id == saved_user.id
    assert saved_user.farmer_profile.farm_name == "Green Acres Farm"
    assert saved_user.farmer_profile.farm_size_acres == Decimal("15.75")


def test_persist_buyer_user_and_profile(db_session: Session):
    """Test persisting User and BuyerProfile into the database."""
    buyer = User(
        email="buyer1@agridirect.com",
        password_hash="argon2_hashed_secret",
        role="buyer",
    )
    profile = BuyerProfile(
        contact_person_name="Pooja Mehta",
        business_name="The Organic Kitchen",
        business_type="restaurant",
        delivery_receiving_address="Plot 5, Industrial Area",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    buyer.buyer_profile = profile

    db_session.add(buyer)
    db_session.commit()

    saved_buyer = db_session.query(User).filter_by(email="buyer1@agridirect.com").one()
    assert saved_buyer.buyer_profile is not None
    assert saved_buyer.buyer_profile.business_name == "The Organic Kitchen"
    assert saved_buyer.buyer_profile.business_type == "restaurant"


def test_duplicate_email_rejected(db_session: Session):
    """Verify unique constraint prevents duplicate emails."""
    u1 = User(email="dup@example.com", password_hash="pw1", role="farmer")
    u2 = User(email="dup@example.com", password_hash="pw2", role="buyer")
    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_phone_number_rejected(db_session: Session):
    """Verify unique constraint prevents duplicate phone numbers."""
    u1 = User(email="p1@example.com", phone_number="+919876543211", password_hash="pw", role="farmer")
    u2 = User(email="p2@example.com", phone_number="+919876543211", password_hash="pw", role="farmer")
    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_farmer_profile_for_same_user_rejected(db_session: Session):
    """Verify database unique constraint prevents multiple FarmerProfiles for the same user_id."""
    farmer = User(email="single_profile@example.com", password_hash="pw", role="farmer")
    db_session.add(farmer)
    db_session.commit()

    p1 = FarmerProfile(
        user_id=farmer.id,
        full_name="A",
        farm_name="Farm 1",
        farm_location_address="Addr 1",
        city="City",
        state="State",
        postal_code="123456",
    )
    p2 = FarmerProfile(
        user_id=farmer.id,
        full_name="B",
        farm_name="Farm 2",
        farm_location_address="Addr 2",
        city="City",
        state="State",
        postal_code="123456",
    )
    db_session.add(p1)
    db_session.commit()

    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_user_cascades_to_profile(db_session: Session):
    """Verify deleting a User removes its associated profile (child cascade)."""
    farmer = User(email="delete_me@example.com", password_hash="pw", role="farmer")
    profile = FarmerProfile(
        full_name="Test",
        farm_name="Farm",
        farm_location_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    farmer.farmer_profile = profile
    db_session.add(farmer)
    db_session.commit()

    profile_id = profile.id
    db_session.delete(farmer)
    db_session.commit()

    # User and Profile should both be deleted
    assert db_session.get(User, farmer.id) is None
    assert db_session.get(FarmerProfile, profile_id) is None


def test_deleting_profile_preserves_user(db_session: Session):
    """Verify removing a profile does NOT delete the parent User account."""
    buyer = User(email="keep_user@example.com", password_hash="pw", role="buyer")
    profile = BuyerProfile(
        contact_person_name="Test",
        business_name="Biz",
        business_type="hotel",
        delivery_receiving_address="Addr",
        city="City",
        state="State",
        postal_code="123456",
    )
    buyer.buyer_profile = profile
    db_session.add(buyer)
    db_session.commit()

    # Delete only the profile
    db_session.delete(profile)
    db_session.commit()

    # User must still exist
    preserved_user = db_session.get(User, buyer.id)
    assert preserved_user is not None
    assert preserved_user.email == "keep_user@example.com"
    assert preserved_user.buyer_profile is None


# ===========================================================================
# 5. Timestamp Defaults and Representations Tests
# ===========================================================================


def test_timestamp_defaults_and_orm_updates(db_session: Session):
    """Test that timestamps are generated on insert and updated_at advances on update."""
    user = User(email="time_test@example.com", password_hash="pw", role="farmer")
    db_session.add(user)
    db_session.commit()

    t_created = user.created_at
    t_updated = user.updated_at
    assert t_created is not None
    assert t_updated is not None

    # Modify and commit
    user.verification_status = "pending"
    db_session.commit()
    db_session.refresh(user)

    assert user.updated_at is not None
    assert user.updated_at >= t_updated


def test_safe_representation_excludes_password_hash():
    """Verify that User.__repr__ does not leak password_hash or credentials."""
    secret_hash = "$argon2id$v=19$m=65536,t=3,p=4$super_secret_hash"
    user = User(
        email="safe_repr@example.com",
        password_hash=secret_hash,
        role="farmer",
    )
    rep = repr(user)
    assert "safe_repr@example.com" in rep
    assert "farmer" in rep
    assert secret_hash not in rep, "Security risk: password_hash leaked in __repr__!"


def test_profile_representations():
    """Verify FarmerProfile and BuyerProfile __repr__ format safely."""
    f_profile = FarmerProfile(
        user_id=uuid.uuid4(),
        full_name="Kisan",
        farm_name="Kisan Farm",
        farm_location_address="Addr",
        city="Nagpur",
        state="Maharashtra",
        postal_code="440001",
    )
    assert "Kisan Farm" in repr(f_profile)
    assert "Nagpur" in repr(f_profile)

    b_profile = BuyerProfile(
        user_id=uuid.uuid4(),
        contact_person_name="Anil",
        business_name="Mega Foods",
        business_type="food_processor",
        delivery_receiving_address="Addr",
        city="Nashik",
        state="Maharashtra",
        postal_code="422001",
    )
    assert "Mega Foods" in repr(b_profile)
    assert "food_processor" in repr(b_profile)
