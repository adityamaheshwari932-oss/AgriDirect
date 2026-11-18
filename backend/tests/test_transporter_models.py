"""Unit tests for TransporterProfile, ServiceArea, and user role constraints."""

from decimal import Decimal
import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.user import ServiceArea, TransporterProfile, User


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


def test_user_transporter_role(db_session):
    """Test user creation with 'transporter' role."""
    user = User(
        email="transporter_test@example.com",
        phone_number="+919876543201",
        password_hash="argon2id$hashed",
        role="transporter",
        verification_status="unverified",
        account_status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.role == "transporter"


def test_invalid_user_role(db_session):
    """Test user creation with invalid role raises ValueError."""
    with pytest.raises(ValueError, match="Invalid role 'invalid_role'"):
        User(
            email="invalid_role@example.com",
            password_hash="argon2id$hashed",
            role="invalid_role",
        )


def test_transporter_profile_creation(db_session):
    """Test TransporterProfile creation and relationship."""
    user = User(
        email="transporter_prof@example.com",
        phone_number="+919876543202",
        password_hash="argon2id$hashed",
        role="transporter",
    )
    db_session.add(user)
    db_session.commit()

    profile = TransporterProfile(
        user_id=user.id,
        business_name="Fast Agri Logistics",
        contact_name="Ramesh Kumar",
        phone_number="+919876543202",
        transport_type="refrigerated",
        vehicle_capacity_kg=Decimal("5000.00"),
        vehicle_registration_number="MH-12-AB-1234",
        is_available=True,
        experience_years=8,
        operating_states="Maharashtra, Gujarat",
        bio="Specialized cold-chain logistics for perishables.",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.id is not None
    assert profile.business_name == "Fast Agri Logistics"
    assert profile.vehicle_capacity_kg == Decimal("5000.00")
    assert profile.user.email == "transporter_prof@example.com"
    assert user.transporter_profile.id == profile.id


def test_transporter_profile_role_enforcement(db_session):
    """Test TransporterProfile cannot be attached to farmer or buyer."""
    farmer = User(
        email="farmer_not_transporter@example.com",
        phone_number="+919876543203",
        password_hash="argon2id$hashed",
        role="farmer",
    )
    db_session.add(farmer)
    db_session.commit()

    with pytest.raises(ValueError, match="TransporterProfile requires role='transporter'"):
        farmer.transporter_profile = TransporterProfile(
            business_name="Invalid Fleet",
            contact_name="Invalid",
            phone_number="+919876543203",
            transport_type="tempo",
            vehicle_capacity_kg=Decimal("1000.00"),
            vehicle_registration_number="MH-01-XY-9999",
        )


def test_transporter_capacity_positive_validation():
    """Test vehicle_capacity_kg must be strictly positive."""
    with pytest.raises(ValueError, match="vehicle_capacity_kg must be strictly positive"):
        TransporterProfile(
            business_name="Zero Cap",
            contact_name="Zero",
            phone_number="+919876543204",
            transport_type="tempo",
            vehicle_capacity_kg=Decimal("-10.00"),
            vehicle_registration_number="MH-01-XY-0000",
        )


def test_service_area_creation_and_cascade(db_session):
    """Test ServiceArea creation, retrieval, and cascade delete."""
    user = User(
        email="transporter_sa@example.com",
        phone_number="+919876543205",
        password_hash="argon2id$hashed",
        role="transporter",
    )
    profile = TransporterProfile(
        business_name="Sahyadri Transport",
        contact_name="Suresh Patil",
        phone_number="+919876543205",
        transport_type="mini_truck",
        vehicle_capacity_kg=Decimal("2500.00"),
        vehicle_registration_number="MH-14-CD-5678",
    )
    user.transporter_profile = profile
    db_session.add(user)
    db_session.commit()

    area1 = ServiceArea(
        transporter_profile_id=profile.id,
        state="Maharashtra",
        district="Pune",
        taluka_subdistrict="Haveli",
        village_town="Hadapsar",
        pincode="411028",
        coverage_type="both",
        is_active=True,
    )
    area2 = ServiceArea(
        transporter_profile_id=profile.id,
        state="Maharashtra",
        district="Nashik",
        coverage_type="pickup_only",
        is_active=True,
    )
    db_session.add_all([area1, area2])
    db_session.commit()

    db_session.refresh(profile)
    assert len(profile.service_areas) == 2

    # Verify coverage_type validator
    with pytest.raises(ValueError, match="Invalid coverage_type"):
        ServiceArea(
            transporter_profile_id=profile.id,
            state="Maharashtra",
            district="Satara",
            coverage_type="invalid_coverage",
        )

    # Deleting user cascades to profile and service areas
    db_session.delete(user)
    db_session.commit()

    assert db_session.query(TransporterProfile).filter(TransporterProfile.id == profile.id).first() is None
    assert db_session.query(ServiceArea).filter(ServiceArea.id == area1.id).first() is None
