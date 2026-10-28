"""Integration tests for Authentication API endpoints:
- POST /api/v1/auth/register/farmer
- POST /api/v1/auth/register/buyer
- POST /api/v1/auth/login
- GET /api/v1/users/me
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
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


# ===========================================================================
# Farmer Registration Tests
# ===========================================================================


class TestFarmerRegistration:
    """Test suite for POST /api/v1/auth/register/farmer."""

    def test_farmer_registration_success_full(self, client: TestClient, sqlite_engine) -> None:
        payload = {
            "email": "farmer1@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "full_name": "Ramesh Patel",
            "phone_number": "+919876543210",
            "farm_name": "Patel Organic Farms",
            "farm_location_address": "Village Khed, Taluka Haveli",
            "city": "Pune",
            "state": "Maharashtra",
            "postal_code": "411001",
            "farm_size_acres": 15.5,
            "farming_practices": "organic",
            "primary_crops": "Tomatoes, Onions",
            "bio": "Generational vegetable farmer.",
        }

        response = client.post("/api/v1/auth/register/farmer", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == "farmer1@example.com"
        assert data["role"] == "farmer"
        assert data["verification_status"] == "unverified"
        assert data["account_status"] == "active"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

        profile = data["farmer_profile"]
        assert profile is not None
        assert profile["full_name"] == "Ramesh Patel"
        assert profile["farm_name"] == "Patel Organic Farms"
        assert profile["city"] == "Pune"
        assert profile["state"] == "Maharashtra"
        assert float(profile["farm_size_acres"]) == 15.5

        # Verify password in DB is hashed with Argon2
        session_factory = sessionmaker(bind=sqlite_engine)
        with session_factory() as db:
            user = db.query(User).filter(User.email == "farmer1@example.com").first()
            assert user is not None
            assert user.password_hash.startswith("$argon2id$")
            assert verify_password("StrongPassword123!", user.password_hash) is True

    def test_farmer_registration_success_minimal(self, client: TestClient) -> None:
        payload = {
            "email": "minimal.farmer@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "full_name": "Kisan Ram",
        }

        response = client.post("/api/v1/auth/register/farmer", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == "minimal.farmer@example.com"
        assert data["role"] == "farmer"
        assert data["farmer_profile"]["full_name"] == "Kisan Ram"
        assert data["farmer_profile"]["farm_name"] == "Kisan Ram's Farm"
        assert data["farmer_profile"]["city"] == "Not Specified"

    def test_farmer_registration_rejects_duplicate_email(self, client: TestClient) -> None:
        payload = {
            "email": "duplicate@example.com",
            "password": "Password123!",
            "full_name": "Farmer One",
        }
        res1 = client.post("/api/v1/auth/register/farmer", json=payload)
        assert res1.status_code == 201

        # Second registration with exact same email
        res2 = client.post("/api/v1/auth/register/farmer", json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"].lower()

    def test_farmer_registration_rejects_duplicate_email_case_insensitive(
        self, client: TestClient
    ) -> None:
        client.post(
            "/api/v1/auth/register/farmer",
            json={"email": "case.farmer@example.com", "password": "Password123!", "full_name": "A"},
        )
        res = client.post(
            "/api/v1/auth/register/farmer",
            json={"email": "CASE.FARMER@EXAMPLE.COM", "password": "Password123!", "full_name": "B"},
        )
        assert res.status_code == 409

    def test_farmer_registration_rejects_duplicate_phone(self, client: TestClient) -> None:
        payload1 = {
            "email": "phone1@example.com",
            "password": "Password123!",
            "full_name": "Farmer A",
            "phone_number": "+919999988888",
        }
        payload2 = {
            "email": "phone2@example.com",
            "password": "Password123!",
            "full_name": "Farmer B",
            "phone_number": "+919999988888",
        }
        res1 = client.post("/api/v1/auth/register/farmer", json=payload1)
        assert res1.status_code == 201

        res2 = client.post("/api/v1/auth/register/farmer", json=payload2)
        assert res2.status_code == 409
        assert "phone number" in res2.json()["detail"].lower()

    def test_farmer_registration_rejects_invalid_email(self, client: TestClient) -> None:
        payload = {
            "email": "not-an-email",
            "password": "Password123!",
            "full_name": "Invalid Email Farmer",
        }
        res = client.post("/api/v1/auth/register/farmer", json=payload)
        assert res.status_code == 422

    def test_farmer_registration_rejects_short_password(self, client: TestClient) -> None:
        payload = {
            "email": "short@example.com",
            "password": "short",
            "full_name": "Short Password Farmer",
        }
        res = client.post("/api/v1/auth/register/farmer", json=payload)
        assert res.status_code == 422

    def test_farmer_registration_rejects_mismatched_password_confirmation(
        self, client: TestClient
    ) -> None:
        payload = {
            "email": "mismatch@example.com",
            "password": "Password123!",
            "password_confirm": "DifferentPassword123!",
            "full_name": "Mismatch Farmer",
        }
        res = client.post("/api/v1/auth/register/farmer", json=payload)
        assert res.status_code == 422
        assert "passwords do not match" in res.text.lower()

    def test_farmer_registration_ignores_client_injected_role_or_status(
        self, client: TestClient
    ) -> None:
        payload = {
            "email": "attacker@example.com",
            "password": "Password123!",
            "full_name": "Attacker",
            "role": "admin",
            "verification_status": "verified",
            "account_status": "blocked",
        }
        res = client.post("/api/v1/auth/register/farmer", json=payload)
        assert res.status_code == 201

        data = res.json()
        assert data["role"] == "farmer"  # Server enforced
        assert data["verification_status"] == "unverified"  # Server enforced
        assert data["account_status"] == "active"  # Server enforced


# ===========================================================================
# Buyer Registration Tests
# ===========================================================================


class TestBuyerRegistration:
    """Test suite for POST /api/v1/auth/register/buyer."""

    def test_buyer_registration_success_full(self, client: TestClient) -> None:
        payload = {
            "email": "procurement@tajhotel.example.com",
            "password": "TajSecurePassword2026!",
            "password_confirm": "TajSecurePassword2026!",
            "contact_person_name": "Priya Sharma",
            "business_name": "Taj Hotels Procurement",
            "business_type": "hotel",
            "business_registration_number": "GSTIN27AABCT3518Q1Z8",
            "phone_number": "+918888877777",
            "delivery_receiving_address": "Dock 4, Gateway Hotel, Colaba",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001",
            "procurement_summary": "Weekly 5 tons of fresh produce.",
        }

        response = client.post("/api/v1/auth/register/buyer", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == "procurement@tajhotel.example.com"
        assert data["role"] == "buyer"
        assert data["verification_status"] == "unverified"
        assert data["account_status"] == "active"
        assert "password" not in data
        assert "password_hash" not in data

        profile = data["buyer_profile"]
        assert profile is not None
        assert profile["contact_person_name"] == "Priya Sharma"
        assert profile["business_name"] == "Taj Hotels Procurement"
        assert profile["business_type"] == "hotel"
        assert profile["city"] == "Mumbai"

    def test_buyer_registration_success_minimal(self, client: TestClient) -> None:
        payload = {
            "email": "restaurant@example.com",
            "password": "StrongPassword123!",
            "full_name": "Chef Anand",
        }

        response = client.post("/api/v1/auth/register/buyer", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["role"] == "buyer"
        assert data["buyer_profile"]["contact_person_name"] == "Chef Anand"
        assert data["buyer_profile"]["business_type"] == "other"

    def test_buyer_registration_rejects_invalid_business_type(self, client: TestClient) -> None:
        payload = {
            "email": "invalid.business@example.com",
            "password": "Password123!",
            "contact_person_name": "John",
            "business_type": "space_agency",
        }
        res = client.post("/api/v1/auth/register/buyer", json=payload)
        assert res.status_code == 422

    def test_buyer_registration_rejects_duplicate_email(self, client: TestClient) -> None:
        payload = {
            "email": "buyer.duplicate@example.com",
            "password": "Password123!",
            "contact_person_name": "Buyer One",
        }
        res1 = client.post("/api/v1/auth/register/buyer", json=payload)
        assert res1.status_code == 201

        res2 = client.post("/api/v1/auth/register/buyer", json=payload)
        assert res2.status_code == 409


# ===========================================================================
# Login Tests
# ===========================================================================


class TestLogin:
    """Test suite for POST /api/v1/auth/login."""

    def test_login_success(self, client: TestClient) -> None:
        # Register user first
        client.post(
            "/api/v1/auth/register/farmer",
            json={
                "email": "login.user@example.com",
                "password": "ValidPassword123!",
                "full_name": "Login Farmer",
            },
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login.user@example.com", "password": "ValidPassword123!"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login.user@example.com"
        assert data["user"]["role"] == "farmer"
        assert "password" not in data
        assert "password_hash" not in data

        # Verify token is decodable
        settings = get_settings()
        payload = jwt.decode(
            data["access_token"], settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == data["user"]["id"]
        assert payload["role"] == "farmer"
        assert payload["status"] == "unverified"

    def test_login_case_insensitive_email(self, client: TestClient) -> None:
        client.post(
            "/api/v1/auth/register/farmer",
            json={"email": "case.login@example.com", "password": "ValidPassword123!", "full_name": "C"},
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "CASE.LOGIN@EXAMPLE.COM", "password": "ValidPassword123!"},
        )
        assert response.status_code == 200

    def test_login_wrong_password_returns_401(self, client: TestClient) -> None:
        client.post(
            "/api/v1/auth/register/farmer",
            json={"email": "wrong.pw@example.com", "password": "CorrectPassword123!", "full_name": "W"},
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong.pw@example.com", "password": "IncorrectPassword456!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_login_nonexistent_email_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "SomePassword123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_login_suspended_account_returns_403(self, client: TestClient, sqlite_engine) -> None:
        client.post(
            "/api/v1/auth/register/farmer",
            json={"email": "suspended@example.com", "password": "ValidPassword123!", "full_name": "S"},
        )

        # Suspend account in DB
        session_factory = sessionmaker(bind=sqlite_engine)
        with session_factory() as db:
            user = db.query(User).filter(User.email == "suspended@example.com").first()
            user.account_status = "suspended"
            db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "suspended@example.com", "password": "ValidPassword123!"},
        )
        assert response.status_code == 403
        assert "suspended or restricted" in response.json()["detail"].lower()

    def test_login_missing_fields_returns_422(self, client: TestClient) -> None:
        res1 = client.post("/api/v1/auth/login", json={})
        assert res1.status_code == 422

        res2 = client.post("/api/v1/auth/login", json={"email": "a@b.com"})
        assert res2.status_code == 422


# ===========================================================================
# Current User (/users/me) Tests
# ===========================================================================


class TestUsersMe:
    """Test suite for GET /api/v1/users/me."""

    def test_get_me_success_farmer(self, client: TestClient) -> None:
        reg_res = client.post(
            "/api/v1/auth/register/farmer",
            json={
                "email": "me.farmer@example.com",
                "password": "Password123!",
                "full_name": "Me Farmer",
                "farm_name": "My Farm",
            },
        )
        token_res = client.post(
            "/api/v1/auth/login",
            json={"email": "me.farmer@example.com", "password": "Password123!"},
        )
        token = token_res.json()["access_token"]

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "me.farmer@example.com"
        assert data["role"] == "farmer"
        assert data["farmer_profile"]["farm_name"] == "My Farm"
        assert "password" not in data
        assert "password_hash" not in data

    def test_get_me_success_buyer(self, client: TestClient) -> None:
        client.post(
            "/api/v1/auth/register/buyer",
            json={
                "email": "me.buyer@example.com",
                "password": "Password123!",
                "contact_person_name": "Me Buyer",
                "business_name": "My Restaurant",
                "business_type": "restaurant",
            },
        )
        token_res = client.post(
            "/api/v1/auth/login",
            json={"email": "me.buyer@example.com", "password": "Password123!"},
        )
        token = token_res.json()["access_token"]

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "buyer"
        assert data["buyer_profile"]["business_name"] == "My Restaurant"

    def test_get_me_missing_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_get_me_invalid_token_returns_401(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.payload"},
        )
        assert response.status_code == 401

    def test_get_me_expired_token_returns_401(self, client: TestClient) -> None:
        settings = get_settings()
        user_id = str(uuid.uuid4())
        expired_token = jwt.encode(
            {
                "sub": user_id,
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_get_me_nonexistent_user_returns_401(self, client: TestClient) -> None:
        fake_token = create_access_token({"sub": str(uuid.uuid4())})
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert response.status_code == 401

    def test_get_me_suspended_user_returns_403(self, client: TestClient, sqlite_engine) -> None:
        client.post(
            "/api/v1/auth/register/farmer",
            json={"email": "me.suspended@example.com", "password": "Password123!", "full_name": "S"},
        )
        token_res = client.post(
            "/api/v1/auth/login",
            json={"email": "me.suspended@example.com", "password": "Password123!"},
        )
        token = token_res.json()["access_token"]

        # Suspend user in DB
        session_factory = sessionmaker(bind=sqlite_engine)
        with session_factory() as db:
            user = db.query(User).filter(User.email == "me.suspended@example.com").first()
            user.account_status = "suspended"
            db.commit()

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "suspended" in response.json()["detail"].lower()
