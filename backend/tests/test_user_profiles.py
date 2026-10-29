"""Integration and unit tests for User Profiles (Step 4):
- GET /api/v1/users/me (profile retrieval, role isolation, sensitive data exclusion)
- PATCH /api/v1/users/me (unified role-aware profile update)
- PATCH /api/v1/users/me/farmer (dedicated farmer profile update)
- PATCH /api/v1/users/me/buyer (dedicated buyer profile update)
- Security: Cross-role protection, unknown/forbidden field rejection, privilege escalation prevention
- Phone number uniqueness and conflict handling
- Partial update semantics (unrelated fields preserved)
- Graceful missing profile initialization
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.user import BuyerProfile, FarmerProfile, User


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database supporting multi-threaded access."""
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
    """Provide a direct database session for test fixture creation."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


@pytest.fixture
def client(sqlite_engine) -> TestClient:
    """Provide a TestClient with overridden get_db dependency."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def farmer_user(db_session: Session) -> User:
    """Create an active farmer with an attached profile."""
    user = User(
        email="farmer.profile@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876500001",
    )
    profile = FarmerProfile(
        user=user,
        full_name="Kisan Ramesh",
        farm_name="Ramesh Farms",
        farm_location_address="Gat No 12, Khed",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
        farm_size_acres=Decimal("12.50"),
        farming_practices="natural",
        primary_crops="Tomatoes, Chillies",
        bio="Experienced vegetable cultivator.",
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def buyer_user(db_session: Session) -> User:
    """Create an active buyer with an attached profile."""
    user = User(
        email="buyer.profile@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876500002",
    )
    profile = BuyerProfile(
        user=user,
        contact_person_name="Ananya Sen",
        business_name="Spice Garden Kitchen",
        business_type="restaurant",
        business_registration_number="GSTIN27ABCDE1234F1Z5",
        delivery_receiving_address="Rear Bay 2, Commercial Street",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        procurement_summary="Needs 500kg vegetables weekly.",
        bio="Multi-cuisine organic restaurant.",
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


# ===========================================================================
# 1. Profile Retrieval Tests
# ===========================================================================


class TestProfileRetrieval:
    """Tests for GET /api/v1/users/me."""

    def test_farmer_retrieves_own_profile(self, client: TestClient, farmer_user: User) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(farmer_user.id)
        assert data["email"] == "farmer.profile@agridirect.test"
        assert data["role"] == "farmer"
        assert data["account_status"] == "active"
        assert data["verification_status"] == "unverified"
        assert data["phone_number"] == "+919876500001"

        # Farmer profile present; buyer profile is None
        assert data["farmer_profile"] is not None
        assert data["farmer_profile"]["full_name"] == "Kisan Ramesh"
        assert data["farmer_profile"]["farm_name"] == "Ramesh Farms"
        assert float(data["farmer_profile"]["farm_size_acres"]) == 12.50
        assert data["buyer_profile"] is None

        # Ensure no sensitive credentials exposed
        assert "password" not in data
        assert "password_hash" not in data

    def test_buyer_retrieves_own_profile(self, client: TestClient, buyer_user: User) -> None:
        token = create_access_token({"sub": str(buyer_user.id)})
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(buyer_user.id)
        assert data["role"] == "buyer"
        assert data["farmer_profile"] is None

        assert data["buyer_profile"] is not None
        assert data["buyer_profile"]["contact_person_name"] == "Ananya Sen"
        assert data["buyer_profile"]["business_name"] == "Spice Garden Kitchen"
        assert data["buyer_profile"]["business_type"] == "restaurant"

    def test_unauthenticated_retrieval_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_suspended_user_retrieval_returns_403(
        self, client: TestClient, db_session: Session, farmer_user: User
    ) -> None:
        farmer_user.account_status = "suspended"
        db_session.commit()

        token = create_access_token({"sub": str(farmer_user.id)})
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# ===========================================================================
# 2. Profile Update Tests — PATCH /api/v1/users/me
# ===========================================================================


class TestProfileUpdateGeneral:
    """Tests for role-aware partial updates via PATCH /api/v1/users/me."""

    def test_farmer_partial_update_success(self, client: TestClient, farmer_user: User) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        payload = {
            "farm_name": "Ramesh Organic Sanctuary",
            "farm_size_acres": 18.0,
            "farming_practices": "certified_organic",
            "city": "Haveli",
        }

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["farmer_profile"]["farm_name"] == "Ramesh Organic Sanctuary"
        assert float(data["farmer_profile"]["farm_size_acres"]) == 18.0
        assert data["farmer_profile"]["farming_practices"] == "certified_organic"
        assert data["farmer_profile"]["city"] == "Haveli"

        # Unmodified fields remain unchanged
        assert data["farmer_profile"]["full_name"] == "Kisan Ramesh"
        assert data["farmer_profile"]["state"] == "Maharashtra"
        assert data["phone_number"] == "+919876500001"

    def test_buyer_partial_update_success(self, client: TestClient, buyer_user: User) -> None:
        token = create_access_token({"sub": str(buyer_user.id)})
        payload = {
            "business_name": "Spice Garden Grand Bistro",
            "business_type": "hotel",
            "procurement_summary": "Expanded needs: 1000kg fresh produce weekly.",
        }

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["buyer_profile"]["business_name"] == "Spice Garden Grand Bistro"
        assert data["buyer_profile"]["business_type"] == "hotel"
        assert data["buyer_profile"]["procurement_summary"] == "Expanded needs: 1000kg fresh produce weekly."

        # Unmodified fields remain unchanged
        assert data["buyer_profile"]["contact_person_name"] == "Ananya Sen"
        assert data["buyer_profile"]["city"] == "Bengaluru"

    def test_update_phone_number_success(self, client: TestClient, farmer_user: User) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        payload = {"phone_number": "+919999911111"}

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["phone_number"] == "+919999911111"

    def test_update_phone_number_to_own_phone_succeeds(
        self, client: TestClient, farmer_user: User
    ) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        payload = {"phone_number": "+919876500001", "city": "Pune North"}

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["phone_number"] == "+919876500001"
        assert response.json()["farmer_profile"]["city"] == "Pune North"

    def test_update_phone_number_conflict_returns_409(
        self, client: TestClient, farmer_user: User, buyer_user: User
    ) -> None:
        # Farmer attempts to adopt buyer's phone number
        token = create_access_token({"sub": str(farmer_user.id)})
        payload = {"phone_number": buyer_user.phone_number}

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_farmer_cannot_update_buyer_fields(
        self, client: TestClient, farmer_user: User
    ) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        payload = {
            "business_type": "restaurant",
            "business_name": "Ramesh Cafe",
        }

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "farmers cannot update buyer-specific" in response.json()["detail"].lower()

    def test_buyer_cannot_update_farmer_fields(
        self, client: TestClient, buyer_user: User
    ) -> None:
        token = create_access_token({"sub": str(buyer_user.id)})
        payload = {
            "farm_size_acres": 25.0,
            "farming_practices": "organic",
        }

        response = client.patch(
            "/api/v1/users/me",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "buyers cannot update farmer-specific" in response.json()["detail"].lower()

    def test_forbidden_server_fields_rejected_via_extra_forbid(
        self, client: TestClient, farmer_user: User
    ) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})

        # Attempts to inject privilege / identity escalation
        for forbidden_key in ["role", "verification_status", "account_status", "email", "id"]:
            response = client.patch(
                "/api/v1/users/me",
                json={forbidden_key: "attacker_value"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 422


# ===========================================================================
# 3. Dedicated Role Endpoints — /me/farmer and /me/buyer
# ===========================================================================


class TestDedicatedRoleProfileEndpoints:
    """Tests for PATCH /api/v1/users/me/farmer and PATCH /api/v1/users/me/buyer."""

    def test_patch_me_farmer_success(self, client: TestClient, farmer_user: User) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        payload = {
            "full_name": "Ramesh Kisan Patel",
            "farm_name": "Patel Krishi Kendra",
            "farm_location_address": "Near Old Canal, Haveli",
            "primary_crops": "Pomegranates, Grapes",
        }

        response = client.patch(
            "/api/v1/users/me/farmer",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["farmer_profile"]["full_name"] == "Ramesh Kisan Patel"
        assert data["farmer_profile"]["farm_name"] == "Patel Krishi Kendra"
        assert data["farmer_profile"]["primary_crops"] == "Pomegranates, Grapes"

    def test_buyer_calling_patch_me_farmer_rejected_with_403(
        self, client: TestClient, buyer_user: User
    ) -> None:
        token = create_access_token({"sub": str(buyer_user.id)})
        response = client.patch(
            "/api/v1/users/me/farmer",
            json={"farm_name": "Unauthorized Farm"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "farmer account" in response.json()["detail"].lower()

    def test_patch_me_buyer_success(self, client: TestClient, buyer_user: User) -> None:
        token = create_access_token({"sub": str(buyer_user.id)})
        payload = {
            "contact_person_name": "Ananya Sen Gupta",
            "business_name": "Spice Garden Fine Dining",
            "delivery_receiving_address": "Dock 3, Central Kitchen",
        }

        response = client.patch(
            "/api/v1/users/me/buyer",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["buyer_profile"]["contact_person_name"] == "Ananya Sen Gupta"
        assert data["buyer_profile"]["business_name"] == "Spice Garden Fine Dining"
        assert data["buyer_profile"]["delivery_receiving_address"] == "Dock 3, Central Kitchen"

    def test_farmer_calling_patch_me_buyer_rejected_with_403(
        self, client: TestClient, farmer_user: User
    ) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        response = client.patch(
            "/api/v1/users/me/buyer",
            json={"business_name": "Unauthorized Restaurant"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "buyer account" in response.json()["detail"].lower()

    def test_invalid_business_type_rejected_with_422(
        self, client: TestClient, buyer_user: User
    ) -> None:
        token = create_access_token({"sub": str(buyer_user.id)})
        response = client.patch(
            "/api/v1/users/me/buyer",
            json={"business_type": "invalid_commercial_type"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_negative_farm_size_rejected_with_422(
        self, client: TestClient, farmer_user: User
    ) -> None:
        token = create_access_token({"sub": str(farmer_user.id)})
        response = client.patch(
            "/api/v1/users/me/farmer",
            json={"farm_size_acres": -5.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


# ===========================================================================
# 4. Missing Profile Row Resilience
# ===========================================================================


class TestMissingProfileResilience:
    """Verifies that if a profile record is missing, updating gracefully initializes it."""

    def test_farmer_with_missing_profile_row_initializes_on_update(
        self, client: TestClient, db_session: Session
    ) -> None:
        # Create farmer without profile row
        user = User(
            email="orphan.farmer@agridirect.test",
            password_hash="hash",
            role="farmer",
            verification_status="unverified",
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token({"sub": str(user.id)})
        payload = {
            "full_name": "Suresh Yadav",
            "farm_name": "Yadav Krishi Farm",
            "city": "Nashik",
            "state": "Maharashtra",
        }

        response = client.patch(
            "/api/v1/users/me/farmer",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["farmer_profile"] is not None
        assert data["farmer_profile"]["full_name"] == "Suresh Yadav"
        assert data["farmer_profile"]["farm_name"] == "Yadav Krishi Farm"
        assert data["farmer_profile"]["city"] == "Nashik"

    def test_buyer_with_missing_profile_row_initializes_on_update(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = User(
            email="orphan.buyer@agridirect.test",
            password_hash="hash",
            role="buyer",
            verification_status="unverified",
            account_status="active",
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token({"sub": str(user.id)})
        payload = {
            "contact_person_name": "Kavita Rao",
            "business_name": "Rao Wholesalers",
            "business_type": "wholesaler",
            "city": "Hyderabad",
            "state": "Telangana",
        }

        response = client.patch(
            "/api/v1/users/me/buyer",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["buyer_profile"] is not None
        assert data["buyer_profile"]["contact_person_name"] == "Kavita Rao"
        assert data["buyer_profile"]["business_name"] == "Rao Wholesalers"
        assert data["buyer_profile"]["business_type"] == "wholesaler"

    def test_farmer_address_whitespace_only_rejected(
        self, client: TestClient, farmer_user: User
    ) -> None:
        """Supplying whitespace-only farm_location_address returns 422."""
        token = create_access_token({"sub": str(farmer_user.id)})
        response = client.patch(
            "/api/v1/users/me/farmer",
            json={"farm_location_address": "   \t  \n "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert "empty or whitespace only" in response.text

    def test_buyer_address_whitespace_only_rejected(
        self, client: TestClient, buyer_user: User
    ) -> None:
        """Supplying whitespace-only delivery_receiving_address returns 422."""
        token = create_access_token({"sub": str(buyer_user.id)})
        response = client.patch(
            "/api/v1/users/me/buyer",
            json={"delivery_receiving_address": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert "empty or whitespace only" in response.text

    def test_unified_profile_address_whitespace_rejected_and_omitted_preserved(
        self, client: TestClient, farmer_user: User
    ) -> None:
        """PATCH /users/me rejects whitespace address but preserves omitted address."""
        token = create_access_token({"sub": str(farmer_user.id)})
        # Whitespace rejected
        res_ws = client.patch(
            "/api/v1/users/me",
            json={"farm_location_address": "  "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_ws.status_code == 422

        # Valid address update succeeds
        res_valid = client.patch(
            "/api/v1/users/me",
            json={"farm_location_address": "Survey 45, Post Khed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_valid.status_code == 200
        assert res_valid.json()["farmer_profile"]["farm_location_address"] == "Survey 45, Post Khed"

        # Omitted address preserves previous value
        res_omitted = client.patch(
            "/api/v1/users/me",
            json={"farm_name": "Updated Farm Name Only"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_omitted.status_code == 200
        assert res_omitted.json()["farmer_profile"]["farm_name"] == "Updated Farm Name Only"
        assert res_omitted.json()["farmer_profile"]["farm_location_address"] == "Survey 45, Post Khed"
