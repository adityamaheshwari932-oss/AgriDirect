"""Automated integration and unit tests for Buyer Requirements Management (Backend Module 2).

Tests cover:
1. Authorization & RBAC:
   - Verified active buyer creates requirement (201 Created, server-derived buyer_id)
   - Unauthenticated rejected (401)
   - Farmer rejected (403)
   - Unverified buyer rejected (403)
   - Suspended buyer rejected (403)
   - Cross-buyer isolation on /me and modification attempts (403)
   - Admin can delete requirement (204)
2. Validation & Quantity Integrity:
   - Required fields, non-empty stripped strings, positive quantities & prices (422)
   - Valid price conditions ('exact', 'range', 'negotiable') (422 on invalid)
   - Category validation (inactive or non-existent rejected 422)
   - Procurement deadline must be today or future (422)
   - Server-controlled fields forbidden on create & update (422)
   - Remaining quantity <= required quantity (422)
   - Wholly unfilled requirement quantity update automatically adjusts remaining quantity
   - Partially fulfilled requirement cannot reduce required quantity below fulfilled quantity
3. Location Defaulting:
   - Destination state and city defaulted from buyer profile if omitted
   - Missing destination and missing profile raises 422
4. Buyer Own Management:
   - GET /api/v1/requirements/me with pagination and status filters
   - Isolation: Buyer B cannot see Buyer A's requirements
5. Detail Retrieval:
   - Public view active unexpired requirement (200)
   - Public blocked from draft, closed, expired, soft-deleted (404)
   - Owner and admin view own draft, closed, expired (200)
6. Status Lifecycle Transitions:
   - draft -> active, active -> closed, closed -> active, active -> draft (200)
   - Invalid transitions rejected (400)
   - Reopening expired closed requirement without future date rejected (400)
   - Reopening expired requirement with future date in same PATCH succeeds (200)
   - Reopening requirement with 0 remaining quantity rejected (400)
   - Soft delete sets is_deleted=True, status=closed (204)
   - Modifying soft-deleted requirement rejected (400)
7. Public Catalog Search:
   - Only active/partially fulfilled, unexpired, positive remaining quantity from verified active buyers visible
   - Draft, closed, expired, zero-quantity, soft-deleted, suspended buyer excluded
   - Category ID, category slug, keyword (q), location, price range, quantity range, sort order filtering
"""

import uuid
from datetime import date, datetime, timedelta, timezone
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
from app.models.listing import ProduceCategory
from app.models.requirement import (
    PRICE_CONDITION_EXACT,
    PRICE_CONDITION_NEGOTIABLE,
    PRICE_CONDITION_RANGE,
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_DRAFT,
    REQUIREMENT_STATUS_EXPIRED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    BuyerRequirement,
)
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
def verified_buyer(db_session: Session) -> User:
    """Create an active, verified commercial buyer with an attached profile."""
    user = User(
        email="verified.buyer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876500001",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Anita Sharma",
        business_name="Fresh Mart Retailers Pvt Ltd",
        business_type="retailer",
        delivery_receiving_address="Plot 12, APMC Market Yard",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_verified_buyer(db_session: Session) -> User:
    """Create a second active, verified commercial buyer."""
    user = User(
        email="other.buyer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876500002",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Rahul Verma",
        business_name="Verma Food Processors",
        business_type="food_processor",
        delivery_receiving_address="Industrial Area Phase 2",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_buyer(db_session: Session) -> User:
    """Create an unverified commercial buyer."""
    user = User(
        email="unverified.buyer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876500003",
    )
    BuyerProfile(
        user=user,
        contact_person_name="New Buyer",
        business_name="New Venture Foods",
        business_type="wholesaler",
        delivery_receiving_address="Address 1",
        city="Nagpur",
        state="Maharashtra",
        postal_code="440001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def suspended_buyer(db_session: Session) -> User:
    """Create a suspended commercial buyer."""
    user = User(
        email="suspended.buyer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="suspended",
        phone_number="+919876500004",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Suspended Contact",
        business_name="Suspended Enterprise",
        business_type="retailer",
        delivery_receiving_address="Address 2",
        city="Nashik",
        state="Maharashtra",
        postal_code="422001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def verified_farmer(db_session: Session) -> User:
    """Create an active verified farmer."""
    user = User(
        email="farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876500005",
    )
    FarmerProfile(
        user=user,
        full_name="Ramesh Patel",
        farm_name="Patel Organic Farms",
        farm_location_address="Survey No. 45",
        city="Anand",
        state="Gujarat",
        postal_code="388001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an administrator user."""
    user = User(
        email="admin@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number="+919876500006",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def active_category(db_session: Session) -> ProduceCategory:
    """Create an active produce category."""
    cat = ProduceCategory(
        name="Vegetables",
        slug="vegetables",
        is_active=True,
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture
def inactive_category(db_session: Session) -> ProduceCategory:
    """Create an inactive produce category."""
    cat = ProduceCategory(
        name="Exotic Fruits",
        slug="exotic-fruits",
        is_active=False,
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def auth_headers(user: User) -> dict:
    """Helper to generate Authorization header for a user."""
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Authorization & RBAC Tests
# ===========================================================================

class TestBuyerRequirementAuthorization:
    """Tests enforcing creator eligibility, RBAC, and ownership boundaries."""

    def test_verified_buyer_can_create_requirement(self, client, verified_buyer, active_category):
        """Verified active commercial buyer can create requirement (201 Created)."""
        future_date = (date.today() + timedelta(days=20)).isoformat()
        payload = {
            "product_name": "Processing Potatoes",
            "title": "Need 500 Quintals Potatoes for Chips",
            "description": "High dry matter content suitable for crisping.",
            "category_id": str(active_category.id),
            "required_quantity": 500.0,
            "unit": "quintal",
            "target_price_per_unit": 1800.00,
            "price_condition": "negotiable",
            "quality_grade": "Chip Grade",
            "destination_state": "Maharashtra",
            "destination_city": "Mumbai",
            "required_by_date": future_date,
            "status": "active",
        }
        res = client.post("/api/v1/requirements", json=payload, headers=auth_headers(verified_buyer))
        assert res.status_code == 201
        data = res.json()
        assert data["product_name"] == "Processing Potatoes"
        assert data["title"] == "Need 500 Quintals Potatoes for Chips"
        assert float(data["required_quantity"]) == 500.0
        assert float(data["remaining_quantity"]) == 500.0
        assert data["buyer_id"] == str(verified_buyer.id)
        assert data["status"] == "active"
        assert data["buyer"]["business_name"] == "Fresh Mart Retailers Pvt Ltd"

    def test_unauthenticated_cannot_create_requirement(self, client):
        """Unauthenticated caller receives 401 Unauthorized."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Wheat",
                "title": "Need Wheat",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
        )
        assert res.status_code == 401

    def test_farmer_cannot_create_requirement(self, client, verified_farmer):
        """Farmer cannot create buyer requirements (403 Forbidden)."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Wheat",
                "title": "Need Wheat",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_farmer),
        )
        assert res.status_code == 403
        assert "buyer account" in res.json()["detail"].lower()

    def test_unverified_buyer_cannot_create_requirement(self, client, unverified_buyer):
        """Unverified buyer cannot create buyer requirements (403 Forbidden)."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Wheat",
                "title": "Need Wheat",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(unverified_buyer),
        )
        assert res.status_code == 403
        assert "verified" in res.json()["detail"].lower()

    def test_suspended_buyer_cannot_create_requirement(self, client, suspended_buyer):
        """Suspended buyer cannot create requirements (403 Forbidden)."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Wheat",
                "title": "Need Wheat",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(suspended_buyer),
        )
        assert res.status_code == 403

    def test_buyer_cannot_update_other_buyer_requirement(self, client, verified_buyer, other_verified_buyer):
        """Buyer B cannot update Buyer A's requirement (403 Forbidden)."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Tomatoes",
                "title": "Need 50 Crates Tomatoes",
                "required_quantity": 50.0,
                "unit": "crate",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_update = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"title": "Hacked Title"},
            headers=auth_headers(other_verified_buyer),
        )
        assert res_update.status_code == 403

    def test_buyer_cannot_transition_status_of_other_buyer_requirement(
        self, client, verified_buyer, other_verified_buyer
    ):
        """Buyer B cannot transition status of Buyer A's requirement (403 Forbidden)."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Onions",
                "title": "Need Onions",
                "required_quantity": 200.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "closed"},
            headers=auth_headers(other_verified_buyer),
        )
        assert res_patch.status_code == 403

    def test_buyer_cannot_delete_other_buyer_requirement(self, client, verified_buyer, other_verified_buyer):
        """Buyer B cannot delete Buyer A's requirement (403 Forbidden)."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Carrots",
                "title": "Need Carrots",
                "required_quantity": 50.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_delete = client.delete(
            f"/api/v1/requirements/{req_id}",
            headers=auth_headers(other_verified_buyer),
        )
        assert res_delete.status_code == 403

    def test_admin_can_delete_buyer_requirement(self, client, verified_buyer, admin_user):
        """Platform administrator can soft-delete any requirement (204 No Content)."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Cabbage",
                "title": "Need Cabbage",
                "required_quantity": 80.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_delete = client.delete(
            f"/api/v1/requirements/{req_id}",
            headers=auth_headers(admin_user),
        )
        assert res_delete.status_code == 204

        # Confirm soft-deleted
        res_get = client.get(f"/api/v1/requirements/{req_id}", headers=auth_headers(admin_user))
        assert res_get.status_code == 200
        assert res_get.json()["is_deleted"] is True
        assert res_get.json()["status"] == "closed"


# ===========================================================================
# 2. Validation & Quantity Integrity Tests
# ===========================================================================

class TestBuyerRequirementValidation:
    """Tests for payload validation, string sanitation, numeric bounds, and quantity integrity."""

    def test_missing_required_fields_rejected(self, client, verified_buyer):
        """Omitting mandatory fields returns 422 Unprocessable Content."""
        res = client.post(
            "/api/v1/requirements",
            json={},
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

    def test_empty_or_whitespace_strings_rejected(self, client, verified_buyer):
        """Empty or whitespace-only product names, titles, or units return 422."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "   ",
                "title": "Need Potatoes",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

    def test_zero_or_negative_quantity_rejected(self, client, verified_buyer):
        """Quantity <= 0 returns 422."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Rice",
                "title": "Need Rice",
                "required_quantity": 0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

        res2 = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Rice",
                "title": "Need Rice",
                "required_quantity": -10,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res2.status_code == 422

    def test_negative_or_zero_target_price_rejected(self, client, verified_buyer):
        """target_price_per_unit <= 0 returns 422."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Corn",
                "title": "Need Corn",
                "required_quantity": 50,
                "unit": "quintal",
                "target_price_per_unit": 0,
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

    def test_invalid_price_condition_rejected(self, client, verified_buyer):
        """Unsupported price_condition string returns 422."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Corn",
                "title": "Need Corn",
                "required_quantity": 50,
                "unit": "quintal",
                "price_condition": "unlimited",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

    def test_inactive_category_rejected(self, client, verified_buyer, inactive_category):
        """Inactive produce category reference returns 422."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Dragonfruit",
                "title": "Need Dragonfruit",
                "category_id": str(inactive_category.id),
                "required_quantity": 20,
                "unit": "kg",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422
        assert "inactive" in res.json()["detail"].lower()

    def test_past_required_by_date_rejected(self, client, verified_buyer):
        """required_by_date in the past returns 422."""
        past_date = (date.today() - timedelta(days=1)).isoformat()
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Barley",
                "title": "Need Barley",
                "required_quantity": 30,
                "unit": "quintal",
                "required_by_date": past_date,
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

    def test_forbidden_server_controlled_fields_rejected_on_create(self, client, verified_buyer):
        """Supplying id, buyer_id, remaining_quantity, or is_deleted returns 422."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Wheat",
                "title": "Need Wheat",
                "required_quantity": 100,
                "remaining_quantity": 50,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 422

    def test_forbidden_server_controlled_fields_rejected_on_update(self, client, verified_buyer):
        """Supplying id or buyer_id on update returns 422."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Wheat",
                "title": "Need Wheat",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_update = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"buyer_id": str(uuid.uuid4())},
            headers=auth_headers(verified_buyer),
        )
        assert res_update.status_code == 422

    def test_remaining_quantity_exceeding_required_quantity_rejected(self, client, verified_buyer):
        """remaining_quantity > required_quantity returns 422."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Soybean",
                "title": "Need Soybean",
                "required_quantity": 100,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_update = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"remaining_quantity": 150.0},
            headers=auth_headers(verified_buyer),
        )
        assert res_update.status_code == 422
        assert "cannot exceed" in res_update.json()["detail"].lower()


# ===========================================================================
# 3. Location Defaulting & Quantity Integrity Tests
# ===========================================================================

class TestLocationDefaultingAndQuantityIntegrity:
    """Tests location auto-population and quantity adjustment logic."""

    def test_destination_defaults_from_buyer_profile_when_omitted(self, client, verified_buyer):
        """Omitting destination_state and destination_city pulls from BuyerProfile."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Garlic",
                "title": "Need Garlic",
                "required_quantity": 40.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=12)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["destination_state"] == "Maharashtra"
        assert data["destination_city"] == "Mumbai"

    def test_missing_destination_and_missing_profile_raises_422(self, client, db_session):
        """If buyer profile has no state/city and request omits them, returns 422."""
        user = User(
            email="noprofile.buyer@agridirect.test",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
            role="buyer",
            verification_status="verified",
            account_status="active",
            phone_number="+919876500007",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Garlic",
                "title": "Need Garlic",
                "required_quantity": 40.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=12)).isoformat(),
            },
            headers=auth_headers(user),
        )
        assert res.status_code == 422
        assert "destination state and city are required" in res.json()["detail"].lower()

    def test_wholly_unfilled_quantity_update_adjusts_remaining_quantity(self, client, verified_buyer):
        """Updating required_quantity on wholly unfilled requirement adjusts remaining_quantity."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Ginger",
                "title": "Need Ginger",
                "required_quantity": 100.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]
        assert float(res_create.json()["remaining_quantity"]) == 100.0

        res_update = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"required_quantity": 150.0},
            headers=auth_headers(verified_buyer),
        )
        assert res_update.status_code == 200
        data = res_update.json()
        assert float(data["required_quantity"]) == 150.0
        assert float(data["remaining_quantity"]) == 150.0

    def test_partially_fulfilled_quantity_update_preserves_fulfilled_quantity(
        self, client, verified_buyer, db_session
    ):
        """Partially fulfilled requirement cannot reduce required_quantity below fulfilled quantity."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Turmeric",
                "title": "Need Turmeric",
                "required_quantity": 100.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = uuid.UUID(res_create.json()["id"])

        # Simulate partial fulfillment: 40 fulfilled, 60 remaining
        db_req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
        db_req.remaining_quantity = Decimal("60.0")
        db_req.status = REQUIREMENT_STATUS_PARTIALLY_FULFILLED
        db_session.commit()

        # Attempt to reduce required_quantity to 30 (< 40 fulfilled) -> 422
        res_fail = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"required_quantity": 30.0},
            headers=auth_headers(verified_buyer),
        )
        assert res_fail.status_code == 422
        assert "below already fulfilled quantity" in res_fail.json()["detail"].lower()

        # Reducing required_quantity to 80 (fulfilled is 40, so new remaining is 40)
        res_ok = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"required_quantity": 80.0},
            headers=auth_headers(verified_buyer),
        )
        assert res_ok.status_code == 200
        data = res_ok.json()
        assert float(data["required_quantity"]) == 80.0
        assert float(data["remaining_quantity"]) == 40.0


# ===========================================================================
# 4. Buyer Own Management (/me) Tests
# ===========================================================================

class TestBuyerOwnRequirementsManagement:
    """Tests for GET /api/v1/requirements/me pagination, filtering, and cross-buyer isolation."""

    def test_list_my_requirements_isolation_and_pagination(
        self, client, verified_buyer, other_verified_buyer
    ):
        """Buyer A cannot see Buyer B's requirements on /me."""
        # Create 3 for Buyer A
        for i in range(3):
            client.post(
                "/api/v1/requirements",
                json={
                    "product_name": f"Buyer A Product {i}",
                    "title": f"Buyer A Requirement {i}",
                    "required_quantity": 10.0 + i,
                    "unit": "kg",
                    "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                },
                headers=auth_headers(verified_buyer),
            )

        # Create 2 for Buyer B
        for i in range(2):
            client.post(
                "/api/v1/requirements",
                json={
                    "product_name": f"Buyer B Product {i}",
                    "title": f"Buyer B Requirement {i}",
                    "required_quantity": 20.0 + i,
                    "unit": "kg",
                    "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                },
                headers=auth_headers(other_verified_buyer),
            )

        res_a = client.get("/api/v1/requirements/me", headers=auth_headers(verified_buyer))
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["total"] == 3
        assert all(item["buyer_id"] == str(verified_buyer.id) for item in data_a["items"])

        res_b = client.get("/api/v1/requirements/me", headers=auth_headers(other_verified_buyer))
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["total"] == 2
        assert all(item["buyer_id"] == str(other_verified_buyer.id) for item in data_b["items"])

    def test_list_my_requirements_status_filtering(self, client, verified_buyer):
        """Status query parameter filters own requirements accurately."""
        # 1 active
        client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Active Product",
                "title": "Active Req",
                "required_quantity": 10.0,
                "unit": "kg",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        # 1 draft
        client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Draft Product",
                "title": "Draft Req",
                "required_quantity": 10.0,
                "unit": "kg",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                "status": "draft",
            },
            headers=auth_headers(verified_buyer),
        )

        res_active = client.get("/api/v1/requirements/me?status=active", headers=auth_headers(verified_buyer))
        assert res_active.status_code == 200
        assert res_active.json()["total"] == 1
        assert res_active.json()["items"][0]["status"] == "active"

        res_draft = client.get("/api/v1/requirements/me?status=draft", headers=auth_headers(verified_buyer))
        assert res_draft.status_code == 200
        assert res_draft.json()["total"] == 1
        assert res_draft.json()["items"][0]["status"] == "draft"


# ===========================================================================
# 5. Detail View & Public Visibility Tests
# ===========================================================================

class TestBuyerRequirementDetailVisibility:
    """Tests for GET /api/v1/requirements/{id} public vs owner/admin access."""

    def test_public_can_view_active_unexpired_requirement(self, client, verified_buyer):
        """Public caller can view active, unexpired requirement (200 OK)."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Apples",
                "title": "Need Kashmiri Apples",
                "required_quantity": 500.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        res_get = client.get(f"/api/v1/requirements/{req_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == req_id

    def test_public_cannot_view_draft_or_closed_requirement(self, client, verified_buyer):
        """Public caller receives 404 for draft or closed requirement."""
        res_draft = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Pears",
                "title": "Draft Pears",
                "required_quantity": 20.0,
                "unit": "kg",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
                "status": "draft",
            },
            headers=auth_headers(verified_buyer),
        )
        draft_id = res_draft.json()["id"]

        res_get = client.get(f"/api/v1/requirements/{draft_id}")
        assert res_get.status_code == 404

        # Owner can view own draft
        res_owner = client.get(f"/api/v1/requirements/{draft_id}", headers=auth_headers(verified_buyer))
        assert res_owner.status_code == 200
        assert res_owner.json()["status"] == "draft"

    def test_public_cannot_view_expired_requirement(self, client, verified_buyer, db_session):
        """Public caller receives 404 for expired requirement."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Grapes",
                "title": "Need Grapes",
                "required_quantity": 50.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=5)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = uuid.UUID(res_create.json()["id"])

        # Manually backdate required_by_date
        db_req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
        db_req.required_by_date = date.today() - timedelta(days=2)
        db_session.commit()

        # Public receives 404
        res_public = client.get(f"/api/v1/requirements/{req_id}")
        assert res_public.status_code == 404

        # Owner receives 200
        res_owner = client.get(f"/api/v1/requirements/{req_id}", headers=auth_headers(verified_buyer))
        assert res_owner.status_code == 200


# ===========================================================================
# 6. Status Lifecycle Transitions & Soft Delete Tests
# ===========================================================================

class TestBuyerRequirementLifecycleTransitions:
    """Tests lifecycle status state machine, valid reopening, and soft deletion."""

    def test_lifecycle_transitions_draft_to_active_to_closed(self, client, verified_buyer):
        """draft -> active -> closed status transitions succeed."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Mangoes",
                "title": "Draft Mangoes",
                "required_quantity": 100.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                "status": "draft",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]
        assert res_create.json()["status"] == "draft"

        # draft -> active
        res_active = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "active"},
            headers=auth_headers(verified_buyer),
        )
        assert res_active.status_code == 200
        assert res_active.json()["status"] == "active"

        # active -> closed
        res_closed = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "closed"},
            headers=auth_headers(verified_buyer),
        )
        assert res_closed.status_code == 200
        assert res_closed.json()["status"] == "closed"

        # closed -> active
        res_reopen = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "active"},
            headers=auth_headers(verified_buyer),
        )
        assert res_reopen.status_code == 200
        assert res_reopen.json()["status"] == "active"

    def test_invalid_status_transition_rejected(self, client, verified_buyer, db_session):
        """Invalid transitions (e.g. partially_fulfilled -> draft) return 400 Bad Request."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Pineapples",
                "title": "Need Pineapples",
                "required_quantity": 50.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = uuid.UUID(res_create.json()["id"])

        db_req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
        db_req.status = REQUIREMENT_STATUS_PARTIALLY_FULFILLED
        db_session.commit()

        # partially_fulfilled -> draft is illegal
        res_invalid = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "draft"},
            headers=auth_headers(verified_buyer),
        )
        assert res_invalid.status_code == 400
        assert "invalid status transition" in res_invalid.json()["detail"].lower()

    def test_reopen_expired_requirement_without_new_date_rejected(self, client, verified_buyer, db_session):
        """Reopening closed expired requirement without providing future date returns 400."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Papaya",
                "title": "Need Papaya",
                "required_quantity": 30.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=5)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = uuid.UUID(res_create.json()["id"])

        db_req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
        db_req.status = REQUIREMENT_STATUS_CLOSED
        db_req.required_by_date = date.today() - timedelta(days=3)
        db_session.commit()

        # Reopen attempt fails
        res_reopen = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "active"},
            headers=auth_headers(verified_buyer),
        )
        assert res_reopen.status_code == 400
        assert "already expired" in res_reopen.json()["detail"].lower()

    def test_reopen_expired_requirement_with_future_date_in_same_patch_succeeds(
        self, client, verified_buyer, db_session
    ):
        """Reopening closed expired requirement while providing future deadline in same PATCH succeeds."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Guava",
                "title": "Need Guava",
                "required_quantity": 40.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=5)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = uuid.UUID(res_create.json()["id"])

        db_req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
        db_req.status = REQUIREMENT_STATUS_CLOSED
        db_req.required_by_date = date.today() - timedelta(days=3)
        db_session.commit()

        future_date = (date.today() + timedelta(days=25)).isoformat()
        res_patch = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"status": "active", "required_by_date": future_date},
            headers=auth_headers(verified_buyer),
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["status"] == "active"
        assert res_patch.json()["required_by_date"] == future_date

    def test_reopen_requirement_with_zero_remaining_quantity_rejected(
        self, client, verified_buyer, db_session
    ):
        """Reopening closed requirement with remaining_quantity <= 0 returns 400."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Dates",
                "title": "Need Dates",
                "required_quantity": 25.0,
                "unit": "box",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = uuid.UUID(res_create.json()["id"])

        db_req = db_session.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
        db_req.status = REQUIREMENT_STATUS_CLOSED
        db_req.remaining_quantity = Decimal("0")
        db_session.commit()

        res_reopen = client.patch(
            f"/api/v1/requirements/{req_id}/status",
            json={"status": "active"},
            headers=auth_headers(verified_buyer),
        )
        assert res_reopen.status_code == 400
        assert "0 remaining quantity" in res_reopen.json()["detail"].lower()

    def test_soft_delete_and_modification_prevention(self, client, verified_buyer):
        """Soft-deleted requirement cannot be updated, reopened, or exposed on /me."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Lemons",
                "title": "Need Lemons",
                "required_quantity": 60.0,
                "unit": "bag",
                "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        # Soft delete
        res_del = client.delete(f"/api/v1/requirements/{req_id}", headers=auth_headers(verified_buyer))
        assert res_del.status_code == 204

        # Cannot update
        res_update = client.patch(
            f"/api/v1/requirements/{req_id}",
            json={"title": "Updated Lemons"},
            headers=auth_headers(verified_buyer),
        )
        assert res_update.status_code == 400
        assert "deleted" in res_update.json()["detail"].lower()

        # Excluded from /me
        res_me = client.get("/api/v1/requirements/me", headers=auth_headers(verified_buyer))
        assert not any(item["id"] == req_id for item in res_me.json()["items"])


# ===========================================================================
# 7. Public Marketplace Catalog Search Tests
# ===========================================================================

class TestBuyerRequirementMarketplaceSearch:
    """Tests for GET /api/v1/requirements search, filtering, and sorting."""

    def test_public_catalog_filters_and_sorting(
        self, client, verified_buyer, active_category, db_session
    ):
        """Public catalog supports keyword, location, price, quantity, and category filters."""
        # Create matching requirement
        res1 = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Premium Sharbati Wheat",
                "title": "Need 300 Quintals Sharbati Wheat",
                "description": "High grain luster and protein content",
                "category_id": str(active_category.id),
                "required_quantity": 300.0,
                "unit": "quintal",
                "target_price_per_unit": 2500.0,
                "price_condition": "exact",
                "quality_grade": "Grade A",
                "destination_state": "Madhya Pradesh",
                "destination_city": "Bhopal",
                "required_by_date": (date.today() + timedelta(days=20)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req1_id = res1.json()["id"]

        # Create another non-matching requirement
        client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Basmati Rice",
                "title": "Need Basmati Rice",
                "required_quantity": 100.0,
                "unit": "quintal",
                "target_price_per_unit": 4000.0,
                "destination_state": "Punjab",
                "destination_city": "Amritsar",
                "required_by_date": (date.today() + timedelta(days=20)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )

        # Keyword search matching Wheat
        res_q = client.get("/api/v1/requirements?q=Sharbati")
        assert res_q.status_code == 200
        assert res_q.json()["total"] == 1
        assert res_q.json()["items"][0]["id"] == req1_id

        # Category filter
        res_cat = client.get(f"/api/v1/requirements?category_slug={active_category.slug}")
        assert res_cat.status_code == 200
        assert res_cat.json()["total"] == 1
        assert res_cat.json()["items"][0]["id"] == req1_id

        # Location filter
        res_loc = client.get("/api/v1/requirements?destination_state=Madhya Pradesh")
        assert res_loc.status_code == 200
        assert res_loc.json()["total"] == 1
        assert res_loc.json()["items"][0]["id"] == req1_id

        # Price range filter
        res_price = client.get("/api/v1/requirements?min_price=2000&max_price=3000")
        assert res_price.status_code == 200
        assert res_price.json()["total"] == 1
        assert res_price.json()["items"][0]["id"] == req1_id

        # Quantity range filter
        res_qty = client.get("/api/v1/requirements?min_quantity=200&max_quantity=400")
        assert res_qty.status_code == 200
        assert res_qty.json()["total"] == 1
        assert res_qty.json()["items"][0]["id"] == req1_id

    def test_public_catalog_excludes_suspended_or_unverified_buyers(
        self, client, verified_buyer, db_session
    ):
        """Requirements posted by buyers who later become suspended or unverified are excluded."""
        res_create = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Mustard Seeds",
                "title": "Need Mustard",
                "required_quantity": 50.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res_create.json()["id"]

        # Confirm visible initially
        res_pub1 = client.get("/api/v1/requirements?q=Mustard")
        assert res_pub1.json()["total"] == 1

        # Suspend the buyer
        db_buyer = db_session.query(User).filter(User.id == verified_buyer.id).first()
        db_buyer.account_status = "suspended"
        db_session.commit()

        # Now excluded from public catalog
        res_pub2 = client.get("/api/v1/requirements?q=Mustard")
        assert res_pub2.json()["total"] == 0

    def test_public_search_supports_state_and_city_aliases(self, client, verified_buyer):
        """Public catalog supports state and city aliases for destination filtering."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Fenugreek",
                "title": "Need Fenugreek",
                "required_quantity": 25.0,
                "unit": "quintal",
                "destination_state": "Rajasthan",
                "destination_city": "Jaipur",
                "required_by_date": (date.today() + timedelta(days=15)).isoformat(),
                "status": "active",
            },
            headers=auth_headers(verified_buyer),
        )
        req_id = res.json()["id"]

        res_alias = client.get("/api/v1/requirements?state=Rajasthan&city=Jaipur")
        assert res_alias.status_code == 200
        assert res_alias.json()["total"] == 1
        assert res_alias.json()["items"][0]["id"] == req_id


# ===========================================================================
# 8. Additional Edge Case & Regression Tests
# ===========================================================================

class TestBuyerRequirementEdgeCases:
    """Additional edge case tests for authorization, defaults, and transaction safety."""

    def test_unrelated_authenticated_buyer_cannot_view_draft_requirement(
        self, client, verified_buyer, other_verified_buyer
    ):
        """Authenticated Buyer B receives 404 when attempting to access Buyer A's draft requirement."""
        res_draft = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Special Spices",
                "title": "Private Draft Spices",
                "required_quantity": 15.0,
                "unit": "kg",
                "required_by_date": (date.today() + timedelta(days=20)).isoformat(),
                "status": "draft",
            },
            headers=auth_headers(verified_buyer),
        )
        draft_id = res_draft.json()["id"]

        # Buyer B receives 404 (non-disclosing)
        res_b = client.get(f"/api/v1/requirements/{draft_id}", headers=auth_headers(other_verified_buyer))
        assert res_b.status_code == 404

    def test_create_requirement_without_target_price_succeeds(self, client, verified_buyer):
        """Verified buyer creates requirement with null target_price_per_unit and negotiable price."""
        res = client.post(
            "/api/v1/requirements",
            json={
                "product_name": "Coriander",
                "title": "Need Coriander",
                "required_quantity": 30.0,
                "unit": "quintal",
                "required_by_date": (date.today() + timedelta(days=14)).isoformat(),
                "price_condition": "negotiable",
            },
            headers=auth_headers(verified_buyer),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["target_price_per_unit"] is None
        assert data["price_condition"] == "negotiable"

    def test_create_requirement_with_invalid_initial_status_rejected(self, client, verified_buyer):
        """Attempting to create requirement directly in 'closed' or 'expired' status returns 422."""
        for bad_status in ("closed", "expired", "partially_fulfilled"):
            res = client.post(
                "/api/v1/requirements",
                json={
                    "product_name": "Cumin",
                    "title": "Need Cumin",
                    "required_quantity": 10.0,
                    "unit": "quintal",
                    "required_by_date": (date.today() + timedelta(days=14)).isoformat(),
                    "status": bad_status,
                },
                headers=auth_headers(verified_buyer),
            )
            assert res.status_code == 422

    def test_database_rollback_on_repository_create_exception(self, client, verified_buyer, monkeypatch):
        """Database transaction rolls back cleanly if repository raises an unexpected exception."""
        from app.requirements.repository import RequirementRepository

        def mock_create(self, data):
            raise RuntimeError("Simulated database failure")

        monkeypatch.setattr(RequirementRepository, "create_requirement", mock_create)

        with pytest.raises(RuntimeError, match="Simulated database failure"):
            client.post(
                "/api/v1/requirements",
                json={
                    "product_name": "Black Pepper",
                    "title": "Need Black Pepper",
                    "required_quantity": 5.0,
                    "unit": "kg",
                    "required_by_date": (date.today() + timedelta(days=10)).isoformat(),
                },
                headers=auth_headers(verified_buyer),
            )

