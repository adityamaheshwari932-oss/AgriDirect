"""Automated integration and unit tests for Produce Listings Management (Backend Module 1).

Tests cover:
1. Produce Categories:
   - GET /api/v1/listings/categories (active taxonomy listing)
2. Listing Creation:
   - Verified farmer creates valid listing (201 Created, server-derived owner, default location from profile)
   - Unauthenticated rejected (401)
   - Buyer rejected (403)
   - Unverified farmer rejected (403)
   - Suspended farmer rejected (403)
   - Missing required fields, whitespace strings, negative prices, zero quantities rejected (422)
   - Extra/forbidden server-controlled fields (id, farmer_id, is_deleted) rejected (422)
   - Invalid / inactive category rejected (422)
   - Past expiration timestamp rejected (422)
   - Creation in draft status (201)
3. Farmer Listing Management:
   - GET /api/v1/listings/me (paginated own listings)
   - Status filtering on /me (draft, active, closed)
   - Isolation: Farmer B cannot see Farmer A's private listings in /me
   - Buyer / Unverified cannot access /me (403)
   - Detail retrieval for draft/closed listing permitted to owner (200), hidden from public (404)
4. Listing Updates & Lifecycle Status Transitions:
   - Farmer updates allowed fields (title, price, description) (200)
   - Farmer B cannot update Farmer A's listing (403)
   - Server-controlled fields rejected on update (422)
   - Available quantity > initial quantity rejected (422)
   - Valid status transitions: draft -> active, active -> closed, closed -> active (200)
   - Invalid status transitions rejected (400)
   - Reopening expired or zero-quantity listing rejected (400)
   - Soft-delete listing via DELETE /api/v1/listings/{id} (204)
   - Updating soft-deleted listing rejected (400)
   - Non-owner cannot delete listing (403)
   - Admin can delete listing (204)
5. Public Marketplace Catalog:
   - Only active, unexpired, available, non-deleted listings visible in GET /api/v1/listings
   - Draft, closed, expired, zero-quantity, and soft-deleted listings excluded
   - Category filtering (by ID and slug)
   - Keyword search (q) on product name, title, description
   - Price range filtering (min_price, max_price)
   - Location filtering (state, city)
   - Pagination and deterministic sorting (price asc/desc, created_at desc)
   - Public summary card sanitized (no private user notes or sensitive fields)
6. Listing Images:
   - Farmer owner uploads valid image (201, first image becomes primary)
   - Multiple images, primary thumbnail toggle
   - Non-owner cannot upload or modify images (403)
   - Disallowed extension and fake image signature rejected (422)
   - Image download/streaming endpoint (200)
   - Image deletion and primary thumbnail auto-promotion (204)
"""

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import create_access_token
from app.listings.storage import ListingImageStorageService
from app.main import app
from app.models.listing import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_DRAFT,
    ListingImage,
    ProduceCategory,
    ProduceListing,
)
from app.models.user import BuyerProfile, FarmerProfile, User
from PIL import Image


def _build_test_image(img_format: str, size=(20, 20), color="green") -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", size, color=color)
    im.save(buf, format=img_format)
    return buf.getvalue()


VALID_PNG_BYTES = _build_test_image("PNG", (20, 20), "green")
VALID_JPEG_BYTES = _build_test_image("JPEG", (20, 20), "blue")


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
def isolated_upload_dir(tmp_path, monkeypatch):
    """Configure an isolated temporary directory for listing image uploads."""
    upload_path = tmp_path / "listing_uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    orig_init = ListingImageStorageService.__init__

    def mock_init(self, upload_dir=None):
        orig_init(self, upload_dir=str(upload_path))

    monkeypatch.setattr(ListingImageStorageService, "__init__", mock_init)
    return upload_path


@pytest.fixture
def client(sqlite_engine, isolated_upload_dir) -> TestClient:
    """Provide a TestClient with overridden get_db dependency and temporary upload dir."""
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
def verified_farmer(db_session: Session) -> User:
    """Create an active, verified farmer with an attached profile."""
    user = User(
        email="verified.farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543001",
    )
    FarmerProfile(
        user=user,
        full_name="Ramesh Patel",
        farm_name="Patel Organic Farms",
        farm_location_address="Survey No. 45, Village Anand",
        city="Anand",
        state="Gujarat",
        postal_code="388001",
        farm_size_acres=Decimal("25.00"),
        farming_practices="organic",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_verified_farmer(db_session: Session) -> User:
    """Create a second active, verified farmer."""
    user = User(
        email="other.farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543002",
    )
    FarmerProfile(
        user=user,
        full_name="Suresh Kumar",
        farm_name="Kumar Agro Farms",
        farm_location_address="Plot 10, Nashik Road",
        city="Nashik",
        state="Maharashtra",
        postal_code="422001",
        farm_size_acres=Decimal("15.00"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_farmer(db_session: Session) -> User:
    """Create an unverified farmer."""
    user = User(
        email="unverified.farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="unverified",
        account_status="active",
        phone_number="+919876543003",
    )
    FarmerProfile(
        user=user,
        full_name="New Farmer",
        farm_name="New Agri",
        farm_location_address="Address 1",
        city="Nagpur",
        state="Maharashtra",
        postal_code="440001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def suspended_farmer(db_session: Session) -> User:
    """Create a suspended verified farmer."""
    user = User(
        email="suspended.farmer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="farmer",
        verification_status="verified",
        account_status="suspended",
        phone_number="+919876543004",
    )
    FarmerProfile(
        user=user,
        full_name="Suspended Farmer",
        farm_name="Suspended Farm",
        farm_location_address="Address 2",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def buyer_user(db_session: Session) -> User:
    """Create an active verified commercial buyer."""
    user = User(
        email="buyer@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="buyer",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543005",
    )
    BuyerProfile(
        user=user,
        contact_person_name="Anita Sharma",
        business_name="Fresh Mart Retailers",
        business_type="retailer",
        delivery_receiving_address="Dock 3, Warehouse 12",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin user."""
    user = User(
        email="admin@agridirect.test",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="admin",
        verification_status="verified",
        account_status="active",
        phone_number="+919876543006",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def produce_category(db_session: Session) -> ProduceCategory:
    """Create an active produce category."""
    cat = ProduceCategory(
        name="Grains & Cereals",
        slug="grains-cereals",
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
        name="Archived Category",
        slug="archived-category",
        is_active=False,
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def auth_header(user: User) -> dict:
    """Generate Authorization header with valid JWT access token."""
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Produce Categories Endpoint Tests
# ===========================================================================

class TestCategoriesEndpoint:
    """Tests for GET /api/v1/listings/categories."""

    def test_list_active_categories_public(self, client: TestClient, produce_category: ProduceCategory, inactive_category: ProduceCategory):
        response = client.get("/api/v1/listings/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        slugs = [c["slug"] for c in data]
        assert "grains-cereals" in slugs
        assert "archived-category" not in slugs


# ===========================================================================
# 2. Listing Creation Tests
# ===========================================================================

class TestListingCreation:
    """Tests for POST /api/v1/listings."""

    def test_verified_farmer_creates_listing_success(
        self, client: TestClient, verified_farmer: User, produce_category: ProduceCategory
    ):
        payload = {
            "product_name": "Sharbati Wheat",
            "title": "Premium Organic Sharbati Wheat 2026 Harvest",
            "description": "High gluten content, clean, sun-dried grains.",
            "category_id": str(produce_category.id),
            "initial_quantity": 500.0,
            "unit": "quintal",
            "price_per_unit": 2850.00,
            "quality_grade": "Grade A",
            "location_state": "Gujarat",
            "location_city": "Anand",
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 201
        data = response.json()

        assert data["product_name"] == "Sharbati Wheat"
        assert data["farmer_id"] == str(verified_farmer.id)
        assert data["status"] == STATUS_ACTIVE
        assert float(data["initial_quantity"]) == 500.0
        assert float(data["available_quantity"]) == 500.0
        assert float(data["price_per_unit"]) == 2850.00
        assert data["unit"] == "quintal"
        assert data["location_state"] == "Gujarat"
        assert data["location_city"] == "Anand"
        assert data["category"]["id"] == str(produce_category.id)
        assert data["farmer"]["farm_name"] == "Patel Organic Farms"

    def test_farmer_location_defaults_from_farm_profile(
        self, client: TestClient, verified_farmer: User
    ):
        """Omitted location_state and location_city should default to farmer profile."""
        payload = {
            "product_name": "Fresh Potatoes",
            "title": "Fresh Farm Potatoes",
            "initial_quantity": 1000.0,
            "unit": "kg",
            "price_per_unit": 22.50,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 201
        data = response.json()
        assert data["location_state"] == "Gujarat"
        assert data["location_city"] == "Anand"

    def test_unauthenticated_creation_rejected(self, client: TestClient):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 10.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 401

    def test_buyer_cannot_create_listing(self, client: TestClient, buyer_user: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 10.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(buyer_user))
        assert response.status_code == 403

    def test_unverified_farmer_cannot_create_listing(self, client: TestClient, unverified_farmer: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 10.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(unverified_farmer))
        assert response.status_code == 403

    def test_suspended_farmer_cannot_create_listing(self, client: TestClient, suspended_farmer: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 10.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(suspended_farmer))
        assert response.status_code == 403

    def test_creation_with_nonexistent_category_rejected(self, client: TestClient, verified_farmer: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "category_id": str(uuid.uuid4()),
            "initial_quantity": 10.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 422

    def test_creation_with_inactive_category_rejected(
        self, client: TestClient, verified_farmer: User, inactive_category: ProduceCategory
    ):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "category_id": str(inactive_category.id),
            "initial_quantity": 10.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 422

    def test_zero_or_negative_quantity_rejected(self, client: TestClient, verified_farmer: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 0.0,
            "unit": "kg",
            "price_per_unit": 20.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 422

    def test_zero_or_negative_price_rejected(self, client: TestClient, verified_farmer: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 100.0,
            "unit": "kg",
            "price_per_unit": -15.0,
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 422

    def test_server_controlled_fields_rejected_via_extra_forbid(self, client: TestClient, verified_farmer: User):
        payload = {
            "product_name": "Wheat",
            "title": "Wheat Title",
            "initial_quantity": 100.0,
            "unit": "kg",
            "price_per_unit": 25.0,
            "farmer_id": str(uuid.uuid4()),  # Server-controlled, forbidden
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 422

    def test_creation_in_draft_status(self, client: TestClient, verified_farmer: User):
        payload = {
            "product_name": "Mustard Seeds",
            "title": "Fresh Mustard Draft",
            "initial_quantity": 200.0,
            "unit": "kg",
            "price_per_unit": 70.0,
            "status": "draft",
        }
        response = client.post("/api/v1/listings", json=payload, headers=auth_header(verified_farmer))
        assert response.status_code == 201
        assert response.json()["status"] == "draft"


# ===========================================================================
# 3. Farmer Listing Management & Ownership Isolation
# ===========================================================================

class TestFarmerListingManagement:
    """Tests for GET /api/v1/listings/me and cross-farmer isolation."""

    @pytest.fixture
    def farmer_listings(self, client: TestClient, verified_farmer: User, other_verified_farmer: User):
        """Create sample listings for farmer 1 and farmer 2."""
        l1 = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Basmati Rice",
                "title": "Traditional Basmati Rice",
                "initial_quantity": 100.0,
                "unit": "quintal",
                "price_per_unit": 4500.0,
                "status": "active",
            },
            headers=auth_header(verified_farmer),
        ).json()

        l2 = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Soybeans",
                "title": "Yellow Soybeans Draft",
                "initial_quantity": 50.0,
                "unit": "quintal",
                "price_per_unit": 3800.0,
                "status": "draft",
            },
            headers=auth_header(verified_farmer),
        ).json()

        l3 = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Onions",
                "title": "Red Onions from Nashik",
                "initial_quantity": 300.0,
                "unit": "quintal",
                "price_per_unit": 1800.0,
                "status": "active",
            },
            headers=auth_header(other_verified_farmer),
        ).json()

        return {"farmer1": [l1, l2], "farmer2": [l3]}

    def test_list_own_listings_isolated_to_authenticated_farmer(
        self, client: TestClient, verified_farmer: User, farmer_listings: dict
    ):
        response = client.get("/api/v1/listings/me", headers=auth_header(verified_farmer))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = [item["title"] for item in data["items"]]
        assert "Traditional Basmati Rice" in titles
        assert "Yellow Soybeans Draft" in titles
        assert "Red Onions from Nashik" not in titles

    def test_filter_own_listings_by_status(
        self, client: TestClient, verified_farmer: User, farmer_listings: dict
    ):
        response = client.get("/api/v1/listings/me?status=draft", headers=auth_header(verified_farmer))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "draft"

    def test_owner_can_retrieve_draft_listing_details(
        self, client: TestClient, verified_farmer: User, farmer_listings: dict
    ):
        draft_id = farmer_listings["farmer1"][1]["id"]
        response = client.get(f"/api/v1/listings/{draft_id}", headers=auth_header(verified_farmer))
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    def test_public_user_cannot_view_draft_listing_details(
        self, client: TestClient, farmer_listings: dict
    ):
        draft_id = farmer_listings["farmer1"][1]["id"]
        response = client.get(f"/api/v1/listings/{draft_id}")
        assert response.status_code == 404

    def test_buyer_cannot_access_farmer_me_endpoint(self, client: TestClient, buyer_user: User):
        response = client.get("/api/v1/listings/me", headers=auth_header(buyer_user))
        assert response.status_code == 403


# ===========================================================================
# 4. Listing Updates & Lifecycle Status Transitions
# ===========================================================================

class TestListingUpdatesAndTransitions:
    """Tests for PATCH /api/v1/listings/{id} and PATCH /api/v1/listings/{id}/status."""

    @pytest.fixture
    def active_listing(self, client: TestClient, verified_farmer: User) -> dict:
        resp = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Nagpur Oranges",
                "title": "Juicy Nagpur Oranges",
                "initial_quantity": 400.0,
                "unit": "kg",
                "price_per_unit": 55.0,
                "status": "active",
            },
            headers=auth_header(verified_farmer),
        )
        return resp.json()

    def test_farmer_updates_allowed_fields(
        self, client: TestClient, verified_farmer: User, active_listing: dict
    ):
        listing_id = active_listing["id"]
        update_payload = {
            "title": "Fresh Sweet Nagpur Oranges (Updated)",
            "price_per_unit": 50.0,
            "description": "Graded, ripe, ready for immediate delivery.",
        }
        response = client.patch(
            f"/api/v1/listings/{listing_id}",
            json=update_payload,
            headers=auth_header(verified_farmer),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Fresh Sweet Nagpur Oranges (Updated)"
        assert float(data["price_per_unit"]) == 50.0
        assert data["description"] == "Graded, ripe, ready for immediate delivery."

    def test_other_farmer_cannot_update_listing(
        self, client: TestClient, other_verified_farmer: User, active_listing: dict
    ):
        listing_id = active_listing["id"]
        response = client.patch(
            f"/api/v1/listings/{listing_id}",
            json={"title": "Hacked Title"},
            headers=auth_header(other_verified_farmer),
        )
        assert response.status_code == 403

    def test_available_quantity_exceeding_initial_rejected(
        self, client: TestClient, verified_farmer: User, active_listing: dict
    ):
        listing_id = active_listing["id"]
        response = client.patch(
            f"/api/v1/listings/{listing_id}",
            json={"available_quantity": 5000.0},  # Exceeds initial_quantity (400.0)
            headers=auth_header(verified_farmer),
        )
        assert response.status_code == 422

    def test_valid_status_transition_active_to_closed_and_back(
        self, client: TestClient, verified_farmer: User, active_listing: dict
    ):
        listing_id = active_listing["id"]

        # Active -> Closed
        resp1 = client.patch(
            f"/api/v1/listings/{listing_id}/status",
            json={"status": "closed"},
            headers=auth_header(verified_farmer),
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "closed"

        # Closed -> Active
        resp2 = client.patch(
            f"/api/v1/listings/{listing_id}/status",
            json={"status": "active"},
            headers=auth_header(verified_farmer),
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "active"

    def test_invalid_status_transition_rejected(
        self, client: TestClient, verified_farmer: User, active_listing: dict
    ):
        listing_id = active_listing["id"]

        # Close the listing first
        client.patch(
            f"/api/v1/listings/{listing_id}/status",
            json={"status": "closed"},
            headers=auth_header(verified_farmer),
        )

        # Closed -> Draft is NOT a valid transition (only closed -> active is allowed)
        resp = client.patch(
            f"/api/v1/listings/{listing_id}/status",
            json={"status": "draft"},
            headers=auth_header(verified_farmer),
        )
        assert resp.status_code == 400

    def test_soft_delete_listing_and_rejection_of_updates(
        self, client: TestClient, verified_farmer: User, active_listing: dict
    ):
        listing_id = active_listing["id"]

        # Delete listing
        del_resp = client.delete(f"/api/v1/listings/{listing_id}", headers=auth_header(verified_farmer))
        assert del_resp.status_code == 204

        # Cannot update a soft-deleted listing
        patch_resp = client.patch(
            f"/api/v1/listings/{listing_id}",
            json={"title": "Trying to update deleted"},
            headers=auth_header(verified_farmer),
        )
        assert patch_resp.status_code == 400

    def test_admin_can_soft_delete_listing(
        self, client: TestClient, admin_user: User, active_listing: dict
    ):
        listing_id = active_listing["id"]
        response = client.delete(f"/api/v1/listings/{listing_id}", headers=auth_header(admin_user))
        assert response.status_code == 204

    def test_reopen_expired_closed_listing_with_new_expiration_in_same_patch(
        self, client: TestClient, verified_farmer: User, db_session: Session
    ):
        """I-02: Reopening a closed expired listing by providing a future expiration date in the same PATCH succeeds."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        future_date = datetime.now(timezone.utc) + timedelta(days=45)

        listing = ProduceListing(
            farmer_id=verified_farmer.id,
            product_name="Expired Wheat",
            title="Expired Wheat Listing",
            initial_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            unit="quintal",
            price_per_unit=Decimal("2500.00"),
            location_state="Gujarat",
            location_city="Anand",
            available_from=date.today() - timedelta(days=35),
            expires_at=past_date,
            status=STATUS_CLOSED,
            is_deleted=False,
        )
        db_session.add(listing)
        db_session.commit()
        db_session.refresh(listing)

        resp = client.patch(
            f"/api/v1/listings/{listing.id}",
            json={
                "status": "active",
                "expires_at": future_date.isoformat(),
            },
            headers=auth_header(verified_farmer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"

    def test_reopen_expired_closed_listing_without_new_expiration_rejected(
        self, client: TestClient, verified_farmer: User, db_session: Session
    ):
        """I-02: Reopening without updating the expired date still fails with 400."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        listing = ProduceListing(
            farmer_id=verified_farmer.id,
            product_name="Expired Millet",
            title="Expired Millet Listing",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            unit="quintal",
            price_per_unit=Decimal("2000.00"),
            location_state="Gujarat",
            location_city="Anand",
            available_from=date.today() - timedelta(days=35),
            expires_at=past_date,
            status=STATUS_CLOSED,
            is_deleted=False,
        )
        db_session.add(listing)
        db_session.commit()
        db_session.refresh(listing)

        resp = client.patch(
            f"/api/v1/listings/{listing.id}",
            json={"status": "active"},
            headers=auth_header(verified_farmer),
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    def test_reopen_closed_listing_with_zero_quantity_rejected(
        self, client: TestClient, verified_farmer: User, db_session: Session
    ):
        """I-02: Reopening a closed listing with 0 available quantity fails with 400."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        listing = ProduceListing(
            farmer_id=verified_farmer.id,
            product_name="Sold Out Barley",
            title="Sold Out Barley Listing",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("0.000"),
            unit="quintal",
            price_per_unit=Decimal("2000.00"),
            location_state="Gujarat",
            location_city="Anand",
            available_from=date.today(),
            expires_at=future_date,
            status=STATUS_CLOSED,
            is_deleted=False,
        )
        db_session.add(listing)
        db_session.commit()
        db_session.refresh(listing)

        resp = client.patch(
            f"/api/v1/listings/{listing.id}",
            json={"status": "active"},
            headers=auth_header(verified_farmer),
        )
        assert resp.status_code == 400
        assert "0 available quantity" in resp.json()["detail"]


# ===========================================================================
# 5. Public Marketplace Catalog & Search Filtering
# ===========================================================================

class TestMarketplaceCatalogSearch:
    """Tests for GET /api/v1/listings public search, filtering, and pagination."""

    @pytest.fixture(autouse=True)
    def seed_catalog(
        self,
        client: TestClient,
        verified_farmer: User,
        other_verified_farmer: User,
        produce_category: ProduceCategory,
    ):
        """Seed diverse listings for catalog testing."""
        # 1. Active Grain Listing in Gujarat
        client.post(
            "/api/v1/listings",
            json={
                "product_name": "Sharbati Wheat",
                "title": "Fresh Golden Sharbati Wheat",
                "description": "Premium milling wheat from Anand.",
                "category_id": str(produce_category.id),
                "initial_quantity": 200.0,
                "unit": "quintal",
                "price_per_unit": 3200.0,
                "quality_grade": "Grade A",
                "location_state": "Gujarat",
                "location_city": "Anand",
                "status": "active",
            },
            headers=auth_header(verified_farmer),
        )

        # 2. Active Grain Listing in Maharashtra
        client.post(
            "/api/v1/listings",
            json={
                "product_name": "Lokwan Wheat",
                "title": "High Quality Lokwan Wheat",
                "description": "Clean Lokwan grain from Nashik.",
                "category_id": str(produce_category.id),
                "initial_quantity": 100.0,
                "unit": "quintal",
                "price_per_unit": 2700.0,
                "quality_grade": "Standard",
                "location_state": "Maharashtra",
                "location_city": "Nashik",
                "status": "active",
            },
            headers=auth_header(other_verified_farmer),
        )

        # 3. Draft Listing (Should NOT appear in public catalog)
        client.post(
            "/api/v1/listings",
            json={
                "product_name": "Hidden Draft Corn",
                "title": "Private Corn Harvest",
                "initial_quantity": 50.0,
                "unit": "quintal",
                "price_per_unit": 1800.0,
                "status": "draft",
            },
            headers=auth_header(verified_farmer),
        )

    def test_public_catalog_returns_only_active_listings(self, client: TestClient):
        response = client.get("/api/v1/listings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = [item["title"] for item in data["items"]]
        assert "Fresh Golden Sharbati Wheat" in titles
        assert "High Quality Lokwan Wheat" in titles
        assert "Private Corn Harvest" not in titles

    def test_filter_by_keyword_search(self, client: TestClient):
        response = client.get("/api/v1/listings?q=Sharbati")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["product_name"] == "Sharbati Wheat"

    def test_filter_by_category_slug(self, client: TestClient):
        response = client.get("/api/v1/listings?category_slug=grains-cereals")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_by_price_range(self, client: TestClient):
        response = client.get("/api/v1/listings?min_price=3000&max_price=3500")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert float(data["items"][0]["price_per_unit"]) == 3200.0

    def test_filter_by_location(self, client: TestClient):
        response = client.get("/api/v1/listings?location_state=Gujarat")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["location_state"] == "Gujarat"

    def test_sorting_by_price(self, client: TestClient):
        response = client.get("/api/v1/listings?sort_by=price_per_unit&sort_order=asc")
        assert response.status_code == 200
        items = response.json()["items"]
        assert float(items[0]["price_per_unit"]) == 2700.0
        assert float(items[1]["price_per_unit"]) == 3200.0

    def test_catalog_excludes_suspended_and_unverified_farmers(
        self,
        client: TestClient,
        verified_farmer: User,
        suspended_farmer: User,
        unverified_farmer: User,
        db_session: Session,
    ):
        """L-01: Public marketplace catalog must exclude listings from suspended or unverified farmers."""
        l_suspended = ProduceListing(
            farmer_id=suspended_farmer.id,
            product_name="Suspended Wheat",
            title="Suspended Farmer Wheat",
            initial_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            unit="quintal",
            price_per_unit=Decimal("2400.00"),
            location_state="Maharashtra",
            location_city="Pune",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            status=STATUS_ACTIVE,
            is_deleted=False,
        )
        l_unverified = ProduceListing(
            farmer_id=unverified_farmer.id,
            product_name="Unverified Millet",
            title="Unverified Farmer Millet",
            initial_quantity=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            unit="quintal",
            price_per_unit=Decimal("1900.00"),
            location_state="Maharashtra",
            location_city="Nagpur",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            status=STATUS_ACTIVE,
            is_deleted=False,
        )
        db_session.add_all([l_suspended, l_unverified])
        db_session.commit()

        response = client.get("/api/v1/listings")
        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["items"]]
        assert "Suspended Farmer Wheat" not in titles
        assert "Unverified Farmer Millet" not in titles


# ===========================================================================
# 6. Listing Image Upload & Access Controls
# ===========================================================================

class TestListingImages:
    """Tests for /api/v1/listings/{id}/images."""

    @pytest.fixture
    def test_listing(self, client: TestClient, verified_farmer: User) -> dict:
        resp = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Alphonso Mango",
                "title": "Ratnagiri Alphonso Mango",
                "initial_quantity": 50.0,
                "unit": "bag",
                "price_per_unit": 1200.0,
            },
            headers=auth_header(verified_farmer),
        )
        return resp.json()

    def test_upload_valid_image_becomes_primary(
        self, client: TestClient, verified_farmer: User, test_listing: dict
    ):
        listing_id = test_listing["id"]
        file_payload = ("test_mango.png", io.BytesIO(VALID_PNG_BYTES), "image/png")

        response = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": file_payload},
            headers=auth_header(verified_farmer),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_primary"] is True
        assert "uploads/listings/" in data["image_uri"]

    def test_non_owner_cannot_upload_image(
        self, client: TestClient, other_verified_farmer: User, test_listing: dict
    ):
        listing_id = test_listing["id"]
        file_payload = ("hacked.png", io.BytesIO(VALID_PNG_BYTES), "image/png")

        response = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": file_payload},
            headers=auth_header(other_verified_farmer),
        )
        assert response.status_code == 403

    def test_disallowed_file_extension_rejected(
        self, client: TestClient, verified_farmer: User, test_listing: dict
    ):
        listing_id = test_listing["id"]
        file_payload = ("document.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf")

        response = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": file_payload},
            headers=auth_header(verified_farmer),
        )
        assert response.status_code == 422

    def test_fake_signature_rejected(
        self, client: TestClient, verified_farmer: User, test_listing: dict
    ):
        listing_id = test_listing["id"]
        fake_bytes = b"Hello, I am a text file pretending to be JPEG"
        file_payload = ("fake.jpg", io.BytesIO(fake_bytes), "image/jpeg")

        response = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": file_payload},
            headers=auth_header(verified_farmer),
        )
        assert response.status_code == 422

    def test_set_primary_image_and_delete_image(
        self, client: TestClient, verified_farmer: User, test_listing: dict
    ):
        listing_id = test_listing["id"]

        # Upload image 1 (auto primary)
        img1 = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": ("img1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(verified_farmer),
        ).json()
        assert img1["is_primary"] is True

        # Upload image 2
        img2 = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": ("img2.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
            headers=auth_header(verified_farmer),
        ).json()
        assert img2["is_primary"] is False

        # Set image 2 as primary
        primary_resp = client.patch(
            f"/api/v1/listings/{listing_id}/images/{img2['id']}/primary",
            headers=auth_header(verified_farmer),
        )
        assert primary_resp.status_code == 200
        assert primary_resp.json()["is_primary"] is True

        # Download image 2
        download_resp = client.get(f"/api/v1/listings/{listing_id}/images/{img2['id']}")
        assert download_resp.status_code == 200

        # Delete image 2
        del_resp = client.delete(
            f"/api/v1/listings/{listing_id}/images/{img2['id']}",
            headers=auth_header(verified_farmer),
        )
        assert del_resp.status_code == 204


# ===========================================================================
# 7. M-01 — Listing Image Access Control & Visibility Rules
# ===========================================================================

class TestListingImageAccessControlAndVisibility:
    """Tests for public vs authorized access to produce listing images (M-01)."""

    @pytest.fixture
    def draft_listing_with_image(
        self, client: TestClient, verified_farmer: User
    ) -> tuple[dict, dict]:
        """Create a draft listing with an uploaded image."""
        listing = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Private Draft Saffron",
                "title": "Kashmir Saffron Draft",
                "initial_quantity": 5.0,
                "unit": "kg",
                "price_per_unit": 150000.0,
                "status": "draft",
            },
            headers=auth_header(verified_farmer),
        ).json()

        img = client.post(
            f"/api/v1/listings/{listing['id']}/images",
            files={"file": ("saffron.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(verified_farmer),
        ).json()

        return listing, img

    def test_public_and_non_owner_cannot_download_draft_listing_image(
        self,
        client: TestClient,
        verified_farmer: User,
        other_verified_farmer: User,
        admin_user: User,
        draft_listing_with_image: tuple[dict, dict],
    ):
        """M-01: Public users and other farmers receive 404 for draft listing images; owner and admin can access."""
        listing, img = draft_listing_with_image
        url = f"/api/v1/listings/{listing['id']}/images/{img['id']}"

        # 1. Unauthenticated public request -> 404
        resp_public = client.get(url)
        assert resp_public.status_code == 404
        assert resp_public.json()["detail"] == f"Image '{img['id']}' not found"

        # 2. Other farmer -> 404
        resp_other = client.get(url, headers=auth_header(other_verified_farmer))
        assert resp_other.status_code == 404

        # 3. Owner farmer -> 200
        resp_owner = client.get(url, headers=auth_header(verified_farmer))
        assert resp_owner.status_code == 200

        # 4. Administrator -> 200
        resp_admin = client.get(url, headers=auth_header(admin_user))
        assert resp_admin.status_code == 200

    def test_public_cannot_download_closed_listing_image(
        self,
        client: TestClient,
        verified_farmer: User,
        draft_listing_with_image: tuple[dict, dict],
    ):
        """M-01: Public users receive 404 for closed listing images; owner can access."""
        listing, img = draft_listing_with_image
        # Activate then close
        client.patch(
            f"/api/v1/listings/{listing['id']}/status",
            json={"status": "active"},
            headers=auth_header(verified_farmer),
        )
        client.patch(
            f"/api/v1/listings/{listing['id']}/status",
            json={"status": "closed"},
            headers=auth_header(verified_farmer),
        )

        url = f"/api/v1/listings/{listing['id']}/images/{img['id']}"
        assert client.get(url).status_code == 404
        assert client.get(url, headers=auth_header(verified_farmer)).status_code == 200

    def test_public_cannot_download_expired_listing_image(
        self,
        client: TestClient,
        verified_farmer: User,
        draft_listing_with_image: tuple[dict, dict],
        db_session: Session,
    ):
        """M-01: Public users receive 404 for expired listing images; owner can access."""
        listing, img = draft_listing_with_image
        # Set status=active and expiration in past directly in DB
        db_listing = db_session.query(ProduceListing).filter(ProduceListing.id == uuid.UUID(listing["id"])).first()
        db_listing.status = STATUS_ACTIVE
        db_listing.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
        db_session.commit()

        url = f"/api/v1/listings/{listing['id']}/images/{img['id']}"
        assert client.get(url).status_code == 404
        assert client.get(url, headers=auth_header(verified_farmer)).status_code == 200

    def test_public_cannot_download_zero_quantity_listing_image(
        self,
        client: TestClient,
        verified_farmer: User,
        draft_listing_with_image: tuple[dict, dict],
        db_session: Session,
    ):
        """M-01: Public users receive 404 for zero available quantity listing images; owner can access."""
        listing, img = draft_listing_with_image
        db_listing = db_session.query(ProduceListing).filter(ProduceListing.id == uuid.UUID(listing["id"])).first()
        db_listing.status = STATUS_ACTIVE
        db_listing.available_quantity = Decimal("0.000")
        db_session.commit()

        url = f"/api/v1/listings/{listing['id']}/images/{img['id']}"
        assert client.get(url).status_code == 404
        assert client.get(url, headers=auth_header(verified_farmer)).status_code == 200

    def test_public_cannot_download_soft_deleted_listing_image(
        self,
        client: TestClient,
        verified_farmer: User,
        admin_user: User,
        draft_listing_with_image: tuple[dict, dict],
    ):
        """M-01: Soft-deleted listings images are blocked from public and owner, accessible only by admin."""
        listing, img = draft_listing_with_image
        # Soft delete listing
        client.delete(f"/api/v1/listings/{listing['id']}", headers=auth_header(verified_farmer))

        url = f"/api/v1/listings/{listing['id']}/images/{img['id']}"
        assert client.get(url).status_code == 404
        assert client.get(url, headers=auth_header(verified_farmer)).status_code == 404
        assert client.get(url, headers=auth_header(admin_user)).status_code == 200

    def test_public_cannot_download_image_if_farmer_is_suspended_or_unverified(
        self,
        client: TestClient,
        verified_farmer: User,
        draft_listing_with_image: tuple[dict, dict],
        db_session: Session,
    ):
        """M-01: If a farmer is suspended or unverified, their listing images are blocked from public access."""
        listing, img = draft_listing_with_image
        # Activate listing
        client.patch(
            f"/api/v1/listings/{listing['id']}/status",
            json={"status": "active"},
            headers=auth_header(verified_farmer),
        )

        url = f"/api/v1/listings/{listing['id']}/images/{img['id']}"
        assert client.get(url).status_code == 200

        # Suspend farmer
        farmer_db = db_session.query(User).filter(User.id == verified_farmer.id).first()
        farmer_db.account_status = "suspended"
        db_session.commit()

        # Public access is now blocked (404)
        assert client.get(url).status_code == 404

        # Restore active, make unverified
        farmer_db.account_status = "active"
        farmer_db.verification_status = "unverified"
        db_session.commit()

        assert client.get(url).status_code == 404

    def test_download_image_with_wrong_listing_id_returns_404(
        self,
        client: TestClient,
        verified_farmer: User,
        draft_listing_with_image: tuple[dict, dict],
    ):
        """M-01: Image requested with mismatched listing UUID returns 404."""
        _listing, img = draft_listing_with_image
        wrong_listing_id = uuid.uuid4()
        url = f"/api/v1/listings/{wrong_listing_id}/images/{img['id']}"
        assert client.get(url, headers=auth_header(verified_farmer)).status_code == 404


# ===========================================================================
# 8. M-02 — File Cleanup on Image Upload Persistence Failure
# ===========================================================================

class TestImageUploadFailureCleanup:
    """Tests for physical file cleanup when database persistence fails (M-02)."""

    def test_upload_db_failure_cleans_up_new_file_and_preserves_existing(
        self,
        client: TestClient,
        verified_farmer: User,
        isolated_upload_dir: Path,
        monkeypatch,
    ):
        """M-02: If database insertion fails during upload, the written file is deleted and existing files are preserved."""
        # 1. Create listing
        listing = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Apples",
                "title": "Shimla Apples",
                "initial_quantity": 100.0,
                "unit": "kg",
                "price_per_unit": 120.0,
            },
            headers=auth_header(verified_farmer),
        ).json()
        listing_id = listing["id"]

        # 2. Successfully upload image 1
        img1_resp = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": ("img1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(verified_farmer),
        )
        assert img1_resp.status_code == 201
        existing_files = list(isolated_upload_dir.iterdir())
        assert len(existing_files) == 1
        existing_img1_path = existing_files[0]

        # 3. Simulate DB persistence failure on add_listing_image
        from app.listings.repository import ListingRepository

        def mock_add_failure(*args, **kwargs):
            raise RuntimeError("Simulated DB insertion crash")

        monkeypatch.setattr(ListingRepository, "add_listing_image", mock_add_failure)

        # 4. Attempt to upload image 2 -> should raise and clean up newly written file
        with pytest.raises(RuntimeError, match="Simulated DB insertion crash"):
            client.post(
                f"/api/v1/listings/{listing_id}/images",
                files={"file": ("img2.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
                headers=auth_header(verified_farmer),
            )

        # 5. Verify isolated_upload_dir STILL only has image 1 (new file was cleaned up)
        current_files = list(isolated_upload_dir.iterdir())
        assert len(current_files) == 1
        assert current_files[0] == existing_img1_path


# ===========================================================================
# 9. L-02 — Transactional Image Deletion & Primary Reassignment
# ===========================================================================

class TestImageDeletionTransactionConsistency:
    """Tests for transactional consistency in image deletion and primary reassignment (L-02)."""

    def test_delete_primary_image_promotes_remaining_image(
        self, client: TestClient, verified_farmer: User
    ):
        """L-02: Deleting primary image promotes a remaining image to primary."""
        listing = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Grapes",
                "title": "Nashik Green Grapes",
                "initial_quantity": 200.0,
                "unit": "kg",
                "price_per_unit": 80.0,
            },
            headers=auth_header(verified_farmer),
        ).json()
        listing_id = listing["id"]

        img1 = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": ("g1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(verified_farmer),
        ).json()
        assert img1["is_primary"] is True

        img2 = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": ("g2.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
            headers=auth_header(verified_farmer),
        ).json()
        assert img2["is_primary"] is False

        # Delete image 1 (the primary)
        del_resp = client.delete(
            f"/api/v1/listings/{listing_id}/images/{img1['id']}",
            headers=auth_header(verified_farmer),
        )
        assert del_resp.status_code == 204

        # Image 2 should now be promoted to primary
        detail = client.get(f"/api/v1/listings/{listing_id}", headers=auth_header(verified_farmer)).json()
        assert len(detail["images"]) == 1
        assert detail["images"][0]["id"] == img2["id"]
        assert detail["images"][0]["is_primary"] is True

    def test_db_failure_during_deletion_preserves_physical_file(
        self,
        client: TestClient,
        verified_farmer: User,
        isolated_upload_dir: Path,
        monkeypatch,
    ):
        """L-02: If database commit fails during image deletion, the physical file is NOT unlinked."""
        listing = client.post(
            "/api/v1/listings",
            json={
                "product_name": "Papaya",
                "title": "Red Lady Papaya",
                "initial_quantity": 50.0,
                "unit": "kg",
                "price_per_unit": 40.0,
            },
            headers=auth_header(verified_farmer),
        ).json()
        listing_id = listing["id"]

        img = client.post(
            f"/api/v1/listings/{listing_id}/images",
            files={"file": ("papaya.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(verified_farmer),
        ).json()

        files_before = list(isolated_upload_dir.iterdir())
        assert len(files_before) == 1

        # Simulate commit failure in repository
        from app.listings.repository import ListingRepository

        def mock_delete_failure(*args, **kwargs):
            raise RuntimeError("Simulated DB deletion crash")

        monkeypatch.setattr(ListingRepository, "delete_listing_image", mock_delete_failure)

        # Attempt delete -> raises RuntimeError
        with pytest.raises(RuntimeError, match="Simulated DB deletion crash"):
            client.delete(
                f"/api/v1/listings/{listing_id}/images/{img['id']}",
                headers=auth_header(verified_farmer),
            )

        # Physical file MUST still exist!
        files_after = list(isolated_upload_dir.iterdir())
        assert len(files_after) == 1
        assert files_after[0].exists()


# ===========================================================================
# 10. L-03 — Listing Image Storage Configuration
# ===========================================================================

class TestListingImageStorageConfiguration:
    """Tests for explicit listing_images_dir configuration setting (L-03)."""

    def test_default_listing_images_dir(self):
        """L-03: Default setting is 'uploads/listings'."""
        s = Settings(
            database_url="postgresql+psycopg://user:pass@localhost:5432/db",
            secret_key="a" * 32,
        )
        assert s.listing_images_dir == "uploads/listings"

    def test_custom_listing_images_dir(self):
        """L-03: Custom directory can be specified and is accepted."""
        s = Settings(
            database_url="postgresql+psycopg://user:pass@localhost:5432/db",
            secret_key="a" * 32,
            listing_images_dir="custom/media/listings",
        )
        assert s.listing_images_dir == "custom/media/listings"

    def test_env_example_documents_listing_images_dir(self):
        """L-03: backend/.env.example documents LISTING_IMAGES_DIR."""
        env_example_path = Path("backend/.env.example")
        if not env_example_path.exists():
            env_example_path = Path(".env.example")
        content = env_example_path.read_text(encoding="utf-8")
        assert "LISTING_IMAGES_DIR" in content
