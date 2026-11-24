"""Comprehensive end-to-end and unit test suite for Product / Listing Image Uploads & Management.

Covers all 18 requirements from Section 9 of the Product Image specification:
1. Successful single-image upload.
2. Successful multiple-image upload.
3. Upload by the product owner.
4. Upload attempt by another farmer (403 Forbidden).
5. Upload attempt by a buyer (403 Forbidden).
6. Upload attempt by an unauthenticated user (401 Unauthorized).
7. Unsupported file format (.gif, .txt).
8. Invalid or malformed image (magic byte signature mismatch).
9. File exceeding the configured size limit (413 Payload Too Large).
10. Maximum image-count enforcement (400 Bad Request).
11. Image listing (/api/v1/listings/{id}/images & /api/v1/products/{id}/images).
12. Primary-image selection.
13. Image reordering (/api/v1/listings/{id}/images/reorder).
14. Image deletion.
15. Attempt to delete another product's image (404 Not Found).
16. Product deletion cascades to images.
17. Database failure cleans up orphaned physical files.
18. Product responses expose image metadata (image_url, is_primary, display_order).
"""

import io
import os
import shutil
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

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
    STATUS_EXPIRED,
    ListingImage,
    ProduceListing,
)
from app.models.user import FarmerProfile, User
from PIL import Image


def _build_test_image(img_format: str, size=(20, 20), color="green") -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", size, color=color)
    im.save(buf, format=img_format)
    return buf.getvalue()


VALID_PNG_BYTES = _build_test_image("PNG", (20, 20), "green")
VALID_JPEG_BYTES = _build_test_image("JPEG", (20, 20), "blue")
VALID_WEBP_BYTES = _build_test_image("WEBP", (20, 20), "red")


@pytest.fixture
def test_temp_dir():
    temp_dir = tempfile.mkdtemp(prefix="agridirect_test_products_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sqlite_engine():
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
    TestingSessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session, test_temp_dir):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Point storage service to isolated temporary directory
    with patch("app.listings.service.ListingImageStorageService") as mock_storage_cls:
        real_service = ListingImageStorageService(upload_dir=test_temp_dir)
        mock_storage_cls.return_value = real_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def farmer_user(db_session: Session) -> User:
    u = User(
        email="farmer1@example.com",
        password_hash="test-hash",
        role="farmer",
        account_status="active",
        verification_status="verified",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    prof = FarmerProfile(
        user_id=u.id,
        full_name="Santosh Shinde",
        farm_name="Shinde Orchards",
        farm_location_address="Niphad Road",
        city="Nashik",
        state="Maharashtra",
        postal_code="422303",
    )
    db_session.add(prof)
    db_session.commit()
    return u


@pytest.fixture
def other_farmer_user(db_session: Session) -> User:
    u = User(
        email="farmer2@example.com",
        password_hash="test-hash",
        role="farmer",
        account_status="active",
        verification_status="verified",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def buyer_user(db_session: Session) -> User:
    u = User(
        email="buyer@example.com",
        password_hash="test-hash",
        role="buyer",
        account_status="active",
        verification_status="verified",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def admin_user(db_session: Session) -> User:
    u = User(
        email="admin@example.com",
        password_hash="test-hash",
        role="admin",
        account_status="active",
        verification_status="verified",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def auth_header(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_listing(db_session: Session, farmer_user: User) -> ProduceListing:
    lst = ProduceListing(
        farmer_id=farmer_user.id,
        product_name="Alphonso Mango",
        title="Ratnagiri GI Tag Alphonso Mangoes",
        description="Naturally ripened premium table fruit",
        initial_quantity=Decimal("1000.000"),
        available_quantity=Decimal("1000.000"),
        unit="kg",
        price_per_unit=Decimal("450.00"),
        quality_grade="Grade A",
        location_state="Maharashtra",
        location_city="Ratnagiri",
        available_from=date.today(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=STATUS_ACTIVE,
    )
    db_session.add(lst)
    db_session.commit()
    db_session.refresh(lst)
    return lst


class TestProductImagesComprehensive:
    """Covers all 18 test requirements for product images."""

    # 1. Successful single-image upload
    def test_01_single_image_upload_success(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("mango_1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_primary"] is True
        assert data["display_order"] == 0
        assert "image_url" in data
        assert f"/api/v1/listings/{sample_listing.id}/images/{data['id']}" in data["image_url"]

    # 2. Successful multiple-image upload
    def test_02_multiple_image_upload_success(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        files = [
            ("files", ("mango_1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")),
            ("files", ("mango_2.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")),
            ("files", ("mango_3.png", io.BytesIO(VALID_PNG_BYTES), "image/png")),
        ]
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files=files,
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["is_primary"] is True
        assert data[1]["is_primary"] is False
        assert data[0]["display_order"] == 0
        assert data[1]["display_order"] == 1
        assert data[2]["display_order"] == 2

    # 3. Upload by the product owner
    def test_03_upload_by_owner_allowed(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("fruit.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201

    # 4. Upload attempt by another farmer
    def test_04_upload_by_another_farmer_forbidden(self, client: TestClient, other_farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("fruit.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(other_farmer_user),
        )
        assert resp.status_code == 403

    # 5. Upload attempt by a buyer
    def test_05_upload_by_buyer_forbidden(self, client: TestClient, buyer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("fruit.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(buyer_user),
        )
        assert resp.status_code == 403

    # 6. Upload attempt by an unauthenticated user
    def test_06_upload_unauthenticated_unauthorized(self, client: TestClient, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("fruit.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
        )
        assert resp.status_code == 401

    # 7. Unsupported file format
    def test_07_unsupported_file_format_rejected(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("document.pdf", io.BytesIO(b"%PDF-1.4 sample content"), "application/pdf")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422
        assert "Disallowed image extension" in resp.json()["detail"]

    # 8. Invalid or malformed image
    def test_08_invalid_or_malformed_image_rejected(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        fake_jpeg = b"NOT_A_REAL_JPEG_CONTENT_AT_ALL_HERE"
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("fake.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422
        assert "Invalid file signature" in resp.json()["detail"]

    # 9. File exceeding the configured size limit
    def test_09_file_exceeding_size_limit_rejected(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        oversized = b"\xff\xd8\xff\xe0" + (b"0" * (6 * 1024 * 1024))
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("huge.jpg", io.BytesIO(oversized), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 413
        assert "exceeds maximum permitted size" in resp.json()["detail"]

    # 10. Maximum image-count enforcement
    def test_10_maximum_image_count_enforcement(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        # Max is 10 images
        files = [
            ("files", (f"img_{i}.png", io.BytesIO(VALID_PNG_BYTES), "image/png"))
            for i in range(10)
        ]
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files=files,
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201

        # Attempt to upload 11th image
        overflow_resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("overflow.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        )
        assert overflow_resp.status_code == 400
        assert "maximum allowed images" in overflow_resp.json()["detail"]

    # 11. Image listing (/api/v1/listings/{id}/images & /api/v1/products/{id}/images)
    def test_11_image_listing_both_endpoints(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        # Upload 2 images
        client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("img1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        )
        client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("img2.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
            headers=auth_header(farmer_user),
        )

        # GET /api/v1/listings/{id}/images
        resp1 = client.get(f"/api/v1/listings/{sample_listing.id}/images")
        assert resp1.status_code == 200
        images1 = resp1.json()
        assert len(images1) == 2
        assert images1[0]["is_primary"] is True
        assert "image_url" in images1[0]

        # GET /api/v1/products/{id}/images (alias route)
        resp2 = client.get(f"/api/v1/products/{sample_listing.id}/images")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 2

    # 12. Primary-image selection
    def test_12_primary_image_selection(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        r1 = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("first.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()
        r2 = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("second.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
            headers=auth_header(farmer_user),
        ).json()

        assert r1["is_primary"] is True
        assert r2["is_primary"] is False

        # Designate second image as primary
        patch_resp = client.patch(
            f"/api/v1/listings/{sample_listing.id}/images/{r2['id']}/primary",
            headers=auth_header(farmer_user),
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_primary"] is True

        # Verify first is no longer primary
        list_resp = client.get(f"/api/v1/listings/{sample_listing.id}/images").json()
        img1 = next(i for i in list_resp if i["id"] == r1["id"])
        img2 = next(i for i in list_resp if i["id"] == r2["id"])
        assert img1["is_primary"] is False
        assert img2["is_primary"] is True

    # 13. Image reordering
    def test_13_image_reordering(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        r1 = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("imgA.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()
        r2 = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("imgB.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Reorder [B, A]
        reorder_resp = client.patch(
            f"/api/v1/listings/{sample_listing.id}/images/reorder",
            json={"image_ids": [r2["id"], r1["id"]]},
            headers=auth_header(farmer_user),
        )
        assert reorder_resp.status_code == 200
        reordered = reorder_resp.json()
        assert reordered[0]["id"] == r2["id"]
        assert reordered[0]["display_order"] == 0
        assert reordered[1]["id"] == r1["id"]
        assert reordered[1]["display_order"] == 1

    # 14. Image deletion
    def test_14_image_deletion_success(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("del.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        del_resp = client.delete(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(farmer_user),
        )
        assert del_resp.status_code == 204

        # Listing should now have 0 images
        list_resp = client.get(f"/api/v1/listings/{sample_listing.id}/images").json()
        assert len(list_resp) == 0

    # 15. Attempt to delete another product's image
    def test_15_delete_wrong_product_image_fails(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing, db_session: Session):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("img.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Create second listing
        second_listing = ProduceListing(
            farmer_id=farmer_user.id,
            product_name="Wheat",
            title="Sharbati Wheat",
            initial_quantity=Decimal("500"),
            available_quantity=Decimal("500"),
            unit="quintal",
            price_per_unit=Decimal("2500"),
            location_state="MP",
            location_city="Indore",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            status=STATUS_ACTIVE,
        )
        db_session.add(second_listing)
        db_session.commit()
        db_session.refresh(second_listing)

        # Attempt to delete sample_listing's image via second_listing path
        del_resp = client.delete(
            f"/api/v1/listings/{second_listing.id}/images/{img['id']}",
            headers=auth_header(farmer_user),
        )
        assert del_resp.status_code == 404

    # 16. Product deletion cascades to images
    def test_16_product_deletion_cascades_images(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing, db_session: Session):
        img_data = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("cascade.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Confirm image exists in DB
        db_img = db_session.query(ListingImage).filter(ListingImage.id == uuid.UUID(img_data["id"])).first()
        assert db_img is not None

        # Hard delete listing from DB to verify cascade
        db_session.delete(sample_listing)
        db_session.commit()

        # Image record should be cascaded and deleted
        cascaded_img = db_session.query(ListingImage).filter(ListingImage.id == uuid.UUID(img_data["id"])).first()
        assert cascaded_img is None

    # 17. Database failure cleans up orphaned physical files
    def test_17_db_failure_cleans_up_orphaned_file(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing, test_temp_dir: str):
        with patch.object(ListingImageStorageService, "save_image", wraps=ListingImageStorageService(upload_dir=test_temp_dir).save_image) as spy_save:
            with patch("app.listings.repository.ListingRepository.add_listing_image", side_effect=RuntimeError("Simulated DB Crash")):
                resp = client.post(
                    f"/api/v1/listings/{sample_listing.id}/images",
                    files={"file": ("crash.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
                    headers=auth_header(farmer_user),
                )
                assert resp.status_code == 500

            # Verify that the physical file created before the DB crash was deleted
            stored_files = list(Path(test_temp_dir).glob("*.png"))
            assert len(stored_files) == 0

    # 18. Product responses expose image metadata and accessible URL
    def test_18_product_response_includes_metadata_and_url(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        img_resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("gallery1.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # 18a. Check ProduceListingDetailResponse
        detail_resp = client.get(
            f"/api/v1/listings/{sample_listing.id}",
            headers=auth_header(farmer_user),
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["images"]) == 1
        assert detail["images"][0]["id"] == img_resp["id"]
        assert detail["images"][0]["is_primary"] is True
        assert detail["images"][0]["display_order"] == 0
        assert f"/api/v1/listings/{sample_listing.id}/images/{img_resp['id']}" in detail["images"][0]["image_url"]

        # 18b. Check ProduceListingPublicSummary via /api/v1/listings marketplace search
        market_resp = client.get("/api/v1/listings")
        assert market_resp.status_code == 200
        items = market_resp.json()["items"]
        matching = next(i for i in items if i["id"] == str(sample_listing.id))
        assert matching["primary_image_uri"] == img_resp["image_uri"]
        assert matching["primary_image_url"] == f"/api/v1/listings/{sample_listing.id}/images/{img_resp['id']}"
        assert len(matching["images"]) == 1
        assert matching["images"][0]["id"] == img_resp["id"]


class TestProductImageAuthorizationMatrix:
    """10-point test matrix enforcing authorization, visibility, and bypass protection.

    Validates that:
    1. Unauthenticated callers can access images of active, valid listings.
    2. Unauthenticated callers are rejected (404) for draft listings.
    3. Other farmers are rejected (404) for draft listings.
    4. Buyers are rejected (404) for closed or draft listings.
    5. Listing owners can view their own draft/closed listing images.
    6. Admins can view images across all listing states (active, draft, closed, deleted).
    7. Soft-deleted listing images are blocked from public and owner, accessible only by admin.
    8. Expired listing images are blocked from public, accessible by owner and admin.
    9. Listings by unverified or suspended farmers are blocked from public, accessible by owner and admin.
    10. Direct static file route (/static/products/{filename}) is completely blocked (404).
    """

    def test_auth_01_unauthenticated_access_active_listing_image_allowed(
        self, client: TestClient, farmer_user: User, sample_listing: ProduceListing
    ):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("active.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Unauthenticated GET via /listings/{id}/images/{img_id}
        resp = client.get(f"/api/v1/listings/{sample_listing.id}/images/{img['id']}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/png")
        assert resp.content == VALID_PNG_BYTES

        # Unauthenticated GET via /products/{id}/images/{img_id} (alias)
        resp_alias = client.get(f"/api/v1/products/{sample_listing.id}/images/{img['id']}")
        assert resp_alias.status_code == 200
        assert resp_alias.content == VALID_PNG_BYTES

    def test_auth_02_unauthenticated_access_draft_listing_image_rejected(
        self, client: TestClient, farmer_user: User, db_session: Session
    ):
        draft_listing = ProduceListing(
            farmer_id=farmer_user.id,
            product_name="Draft Onion",
            title="Draft Nashik Red Onion",
            initial_quantity=Decimal("500"),
            available_quantity=Decimal("500"),
            unit="kg",
            price_per_unit=Decimal("20"),
            location_state="Maharashtra",
            location_city="Nashik",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=10),
            status=STATUS_DRAFT,
        )
        db_session.add(draft_listing)
        db_session.commit()
        db_session.refresh(draft_listing)

        img = client.post(
            f"/api/v1/listings/{draft_listing.id}/images",
            files={"file": ("draft.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        resp = client.get(f"/api/v1/listings/{draft_listing.id}/images/{img['id']}")
        assert resp.status_code == 404

    def test_auth_03_other_farmer_access_draft_listing_image_rejected(
        self, client: TestClient, farmer_user: User, other_farmer_user: User, db_session: Session
    ):
        draft_listing = ProduceListing(
            farmer_id=farmer_user.id,
            product_name="Draft Tomato",
            title="Draft Tomatoes",
            initial_quantity=Decimal("200"),
            available_quantity=Decimal("200"),
            unit="kg",
            price_per_unit=Decimal("30"),
            location_state="Maharashtra",
            location_city="Pune",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=10),
            status=STATUS_DRAFT,
        )
        db_session.add(draft_listing)
        db_session.commit()
        db_session.refresh(draft_listing)

        img = client.post(
            f"/api/v1/listings/{draft_listing.id}/images",
            files={"file": ("draft2.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        resp = client.get(
            f"/api/v1/listings/{draft_listing.id}/images/{img['id']}",
            headers=auth_header(other_farmer_user),
        )
        assert resp.status_code == 404

    def test_auth_04_buyer_access_restricted_draft_or_closed_image_rejected(
        self, client: TestClient, farmer_user: User, buyer_user: User, db_session: Session
    ):
        closed_listing = ProduceListing(
            farmer_id=farmer_user.id,
            product_name="Closed Potato",
            title="Closed Batch Potatoes",
            initial_quantity=Decimal("100"),
            available_quantity=Decimal("100"),
            unit="kg",
            price_per_unit=Decimal("15"),
            location_state="Gujarat",
            location_city="Surat",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=10),
            status=STATUS_CLOSED,
        )
        db_session.add(closed_listing)
        db_session.commit()
        db_session.refresh(closed_listing)

        img = client.post(
            f"/api/v1/listings/{closed_listing.id}/images",
            files={"file": ("closed.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        resp = client.get(
            f"/api/v1/listings/{closed_listing.id}/images/{img['id']}",
            headers=auth_header(buyer_user),
        )
        assert resp.status_code == 404

    def test_auth_05_listing_owner_access_own_draft_image_allowed(
        self, client: TestClient, farmer_user: User, db_session: Session
    ):
        draft_listing = ProduceListing(
            farmer_id=farmer_user.id,
            product_name="Draft Ginger",
            title="Draft Ginger Rhizomes",
            initial_quantity=Decimal("50"),
            available_quantity=Decimal("50"),
            unit="kg",
            price_per_unit=Decimal("80"),
            location_state="Kerala",
            location_city="Wayanad",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=10),
            status=STATUS_DRAFT,
        )
        db_session.add(draft_listing)
        db_session.commit()
        db_session.refresh(draft_listing)

        img = client.post(
            f"/api/v1/listings/{draft_listing.id}/images",
            files={"file": ("owner_draft.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        resp = client.get(
            f"/api/v1/listings/{draft_listing.id}/images/{img['id']}",
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 200
        assert resp.content == VALID_PNG_BYTES

    def test_auth_06_admin_access_restricted_listing_images_allowed(
        self, client: TestClient, farmer_user: User, admin_user: User, db_session: Session
    ):
        draft_listing = ProduceListing(
            farmer_id=farmer_user.id,
            product_name="Admin Audit Crop",
            title="Draft Listing for Admin",
            initial_quantity=Decimal("50"),
            available_quantity=Decimal("50"),
            unit="kg",
            price_per_unit=Decimal("50"),
            location_state="Punjab",
            location_city="Amritsar",
            available_from=date.today(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=10),
            status=STATUS_DRAFT,
        )
        db_session.add(draft_listing)
        db_session.commit()
        db_session.refresh(draft_listing)

        img = client.post(
            f"/api/v1/listings/{draft_listing.id}/images",
            files={"file": ("admin_crop.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        resp = client.get(
            f"/api/v1/listings/{draft_listing.id}/images/{img['id']}",
            headers=auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.content == VALID_PNG_BYTES

    def test_auth_07_access_deleted_listing_images(
        self, client: TestClient, farmer_user: User, admin_user: User, sample_listing: ProduceListing, db_session: Session
    ):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("deleted_listing.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Soft delete listing
        sample_listing.is_deleted = True
        db_session.commit()

        # Public access should be 404
        assert client.get(f"/api/v1/listings/{sample_listing.id}/images/{img['id']}").status_code == 404

        # Owner access should be 404 (soft-deleted blocked for non-admins)
        assert client.get(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(farmer_user),
        ).status_code == 404

        # Admin access should succeed (200)
        admin_resp = client.get(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(admin_user),
        )
        assert admin_resp.status_code == 200
        assert admin_resp.content == VALID_PNG_BYTES

    def test_auth_08_access_expired_listing_images(
        self, client: TestClient, farmer_user: User, admin_user: User, sample_listing: ProduceListing, db_session: Session
    ):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("expired.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Expire listing
        sample_listing.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
        db_session.commit()

        # Public access should be 404
        assert client.get(f"/api/v1/listings/{sample_listing.id}/images/{img['id']}").status_code == 404

        # Owner access should succeed (200)
        owner_resp = client.get(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(farmer_user),
        )
        assert owner_resp.status_code == 200
        assert owner_resp.content == VALID_PNG_BYTES

        # Admin access should succeed (200)
        admin_resp = client.get(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(admin_user),
        )
        assert admin_resp.status_code == 200

    def test_auth_09_access_images_unverified_or_inactive_farmer(
        self, client: TestClient, farmer_user: User, admin_user: User, sample_listing: ProduceListing, db_session: Session
    ):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("farmer_unverified.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        # Mark farmer as unverified (pending)
        farmer_user.verification_status = "pending"
        db_session.commit()

        # Public access should be 404
        assert client.get(f"/api/v1/listings/{sample_listing.id}/images/{img['id']}").status_code == 404

        # Owner can still view own images (200)
        owner_resp = client.get(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(farmer_user),
        )
        assert owner_resp.status_code == 200

        # Admin can view images (200)
        admin_resp = client.get(
            f"/api/v1/listings/{sample_listing.id}/images/{img['id']}",
            headers=auth_header(admin_user),
        )
        assert admin_resp.status_code == 200

    def test_auth_10_direct_access_through_old_static_route_blocked(
        self, client: TestClient, farmer_user: User, sample_listing: ProduceListing
    ):
        img = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("probe_static.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        ).json()

        filename = Path(img["image_uri"]).name

        # Directly probe the unmounted static URL
        static_resp = client.get(f"/static/products/{filename}")
        assert static_resp.status_code == 404

        # Verify that accessing via the protected streaming endpoint works
        streaming_resp = client.get(f"/api/v1/listings/{sample_listing.id}/images/{img['id']}")
        assert streaming_resp.status_code == 200


class TestImageContentValidationAndSecurity:
    """Rigorous verification of image content inspection, decoding, and security controls.

    Verifies:
    1. Valid JPEG uploads and decodes successfully.
    2. Valid PNG uploads and decodes successfully.
    3. Valid WebP uploads and decodes successfully.
    4. Corrupted image file is rejected (422).
    5. Fake image with valid extension is rejected (422).
    6. MIME / signature / format mismatch is rejected (422).
    7. Excessive image dimensions are rejected (422).
    8. Decompression-bomb pixel limits are enforced (422).
    9. Oversized files exceeding 5 MB are rejected (413).
    10. Unsupported image formats are rejected (422).
    11. Database failures clean up orphaned physical files.
    """

    def test_val_01_valid_jpeg(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("photo.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201
        assert resp.json()["image_uri"].endswith(".jpg")
        assert "image_url" in resp.json()

    def test_val_02_valid_png(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("photo.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201
        assert resp.json()["image_uri"].endswith(".png")
        assert "image_url" in resp.json()

    def test_val_03_valid_webp(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("photo.webp", io.BytesIO(VALID_WEBP_BYTES), "image/webp")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 201
        assert resp.json()["image_uri"].endswith(".webp")
        assert "image_url" in resp.json()

    def test_val_04_corrupted_image(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        # Starts with valid PNG header, but truncated/corrupt IDAT chunk
        corrupted = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (b"\x00" * 32)
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("corrupt.png", io.BytesIO(corrupted), "image/png")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422
        assert any(term in resp.json()["detail"].lower() for term in ["corrupt", "malformed", "failed", "signature"])

    def test_val_05_fake_image_with_valid_extension(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        fake_text = b"This is plain text disguised as a picture"
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("fake.jpg", io.BytesIO(fake_text), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422

    def test_val_06_mime_signature_mismatch(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        # Genuine JPEG content uploaded under .png with image/png MIME
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("mismatched.png", io.BytesIO(VALID_JPEG_BYTES), "image/png")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422
        assert any(term in resp.json()["detail"].lower() for term in ["signature", "does not match", "invalid"])

    def test_val_07_excessive_dimensions(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        # 9000x100 exceeds MAX_IMAGE_WIDTH (8000)
        huge_dim = _build_test_image("JPEG", size=(9000, 100))
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("huge_width.jpg", io.BytesIO(huge_dim), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422
        assert "exceed maximum permitted dimensions" in resp.json()["detail"]

    def test_val_08_decompression_bomb_protection(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        # 6000x5000 = 30 MP > MAX_IMAGE_PIXELS (25 MP)
        bomb_img = _build_test_image("JPEG", size=(6000, 5000))
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("bomb.jpg", io.BytesIO(bomb_img), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422
        assert any(term in resp.json()["detail"].lower() for term in ["pixel limit", "decompression"])

    def test_val_09_oversized_upload(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        oversized = b"\xff\xd8\xff\xe0" + (b"0" * (6 * 1024 * 1024))
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("huge.jpg", io.BytesIO(oversized), "image/jpeg")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 413

    def test_val_10_unsupported_image_format(self, client: TestClient, farmer_user: User, sample_listing: ProduceListing):
        resp = client.post(
            f"/api/v1/listings/{sample_listing.id}/images",
            files={"file": ("anim.gif", io.BytesIO(b"GIF89a..."), "image/gif")},
            headers=auth_header(farmer_user),
        )
        assert resp.status_code == 422

    def test_val_11_db_failure_cleans_up_physical_file(
        self, client: TestClient, farmer_user: User, sample_listing: ProduceListing, test_temp_dir: str
    ):
        with patch.object(ListingImageStorageService, "save_image", wraps=ListingImageStorageService(upload_dir=test_temp_dir).save_image) as spy_save:
            with patch("app.listings.repository.ListingRepository.add_listing_image", side_effect=RuntimeError("Simulated DB Crash")):
                resp = client.post(
                    f"/api/v1/listings/{sample_listing.id}/images",
                    files={"file": ("cleanup_test.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
                    headers=auth_header(farmer_user),
                )
                assert resp.status_code == 500

            # Verify that the physical file created before the DB crash was safely deleted
            stored_files = list(Path(test_temp_dir).glob("*.png"))
            assert len(stored_files) == 0


