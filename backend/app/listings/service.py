"""Service layer for produce listings and catalog management.

Enforces business rules:
- Farmer ownership and verification checks.
- Quantity bounds (0 <= available <= initial).
- Status transition state machine.
- Public marketplace visibility rules.
- Local secure image processing and cleanup.
"""

import logging
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.listings.models import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_DRAFT,
    STATUS_EXPIRED,
    STATUS_PARTIALLY_FULFILLED,
    VALID_LISTING_STATUSES,
)
from app.listings.repository import ListingRepository
from app.listings.schemas import (
    CategoryResponse,
    FarmerListingListResponse,
    FarmerSummary,
    ListingCreate,
    ListingImageResponse,
    ListingStatusUpdate,
    ListingUpdate,
    ProduceListingDetailResponse,
    ProduceListingPublicListResponse,
    ProduceListingPublicSummary,
)
from app.listings.storage import ListingImageStorageService
from app.models.listing import ListingImage, ProduceListing
from app.models.user import User

MAX_IMAGES_PER_LISTING = 10

# Permitted lifecycle state transitions (from_status -> allowed_target_statuses)
PERMITTED_STATUS_TRANSITIONS: Dict[str, set[str]] = {
    STATUS_DRAFT: {STATUS_ACTIVE, STATUS_CLOSED},
    STATUS_ACTIVE: {STATUS_DRAFT, STATUS_CLOSED},
    STATUS_PARTIALLY_FULFILLED: {STATUS_CLOSED},
    STATUS_CLOSED: {STATUS_ACTIVE},  # Reopening active if quantity and expiration permit
    STATUS_EXPIRED: {STATUS_CLOSED},
}


def _ensure_tz_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware for portable comparisons (SQLite and PostgreSQL)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ListingService:
    """Orchestrates produce catalog, listing management, and image operations."""

    def __init__(
        self,
        db: Session,
        storage: Optional[ListingImageStorageService] = None,
    ) -> None:
        self.repository = ListingRepository(db)
        self.storage = storage or ListingImageStorageService()

    # -----------------------------------------------------------------------
    # Categories
    # -----------------------------------------------------------------------

    def list_active_categories(self) -> List[CategoryResponse]:
        """Retrieve active produce categories."""
        categories = self.repository.list_categories(active_only=True)
        return [CategoryResponse.model_validate(c) for c in categories]

    # -----------------------------------------------------------------------
    # Farmer Listing Management
    # -----------------------------------------------------------------------

    def create_listing(self, user: User, payload: ListingCreate) -> ProduceListingDetailResponse:
        """Create a produce listing for the authenticated, verified farmer.

        Args:
            user: Authenticated active, verified farmer.
            payload: Validated listing creation schema.

        Returns:
            Detailed listing response.

        Raises:
            HTTPException: 403 if user is not a verified farmer.
            HTTPException: 422 if category is invalid or inactive.
        """
        self._require_verified_farmer(user)

        # Validate category if provided
        if payload.category_id:
            category = self.repository.get_category_by_id(payload.category_id)
            if not category or not category.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Category with ID '{payload.category_id}' does not exist or is inactive",
                )

        # Resolve location defaults from farmer profile if omitted
        state = payload.location_state
        city = payload.location_city
        profile = getattr(user, "farmer_profile", None)

        if not state:
            state = getattr(profile, "state", None) if profile else None
        if not city:
            city = getattr(profile, "city", None) if profile else None

        if not state or not city:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Location state and city are required. Please provide them or update your farm profile.",
            )

        # Resolve available_from and expires_at
        available_from = payload.available_from or date.today()

        now = datetime.now(timezone.utc)
        if payload.expires_at:
            aware_expires = _ensure_tz_aware(payload.expires_at)
            if aware_expires <= now:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Listing expiration timestamp must be in the future",
                )
            expires_at = aware_expires
        else:
            # Default expiration: 30 days after available_from
            expires_date = available_from + timedelta(days=30)
            expires_at = datetime(
                expires_date.year,
                expires_date.month,
                expires_date.day,
                23,
                59,
                59,
                tzinfo=timezone.utc,
            )

        # Initial available quantity matches initial quantity on creation
        listing_data = {
            "farmer_id": user.id,
            "category_id": payload.category_id,
            "product_name": payload.product_name,
            "title": payload.title,
            "description": payload.description,
            "initial_quantity": payload.initial_quantity,
            "available_quantity": payload.initial_quantity,
            "unit": payload.unit,
            "price_per_unit": payload.price_per_unit,
            "quality_grade": payload.quality_grade,
            "location_state": state,
            "location_city": city,
            "harvest_date": payload.harvest_date,
            "available_from": available_from,
            "expires_at": expires_at,
            "status": payload.status or STATUS_ACTIVE,
            "is_deleted": False,
        }

        listing = self.repository.create_listing(listing_data)
        # Fetch fresh with relationships loaded
        loaded = self.repository.get_listing_by_id(listing.id) or listing
        return self._to_detail_response(loaded)

    def list_farmer_listings(
        self,
        user: User,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FarmerListingListResponse:
        """List listings owned by the authenticated farmer."""
        self._require_verified_farmer(user)

        if status_filter and status_filter not in VALID_LISTING_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid status filter '{status_filter}'. Must be one of: {', '.join(VALID_LISTING_STATUSES)}",
            )

        listings, total = self.repository.list_farmer_listings(
            farmer_id=user.id,
            status_filter=status_filter,
            include_deleted=False,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = [self._to_detail_response(lst) for lst in listings]

        return FarmerListingListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_listing_detail(
        self,
        listing_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> ProduceListingDetailResponse:
        """Retrieve full details of a listing.

        If caller is owner (or admin), returns full detail regardless of status.
        If caller is public/buyer, returns detail only if listing is active and not deleted.
        """
        listing = self.repository.get_listing_by_id(listing_id, include_deleted=False)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produce listing '{listing_id}' not found",
            )

        is_owner = current_user is not None and (
            listing.farmer_id == current_user.id or current_user.role == "admin"
        )

        if not is_owner and listing.status != STATUS_ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produce listing '{listing_id}' is not currently available",
            )

        return self._to_detail_response(listing)

    def update_listing(
        self,
        listing_id: uuid.UUID,
        user: User,
        payload: ListingUpdate,
    ) -> ProduceListingDetailResponse:
        """Update permitted fields on a produce listing owned by caller."""
        listing = self._get_owned_listing(listing_id, user)

        data = payload.model_dump(exclude_unset=True)
        if not data:
            return self._to_detail_response(listing)

        # Validate category if updating
        if "category_id" in data and data["category_id"] is not None:
            category = self.repository.get_category_by_id(data["category_id"])
            if not category or not category.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Category with ID '{data['category_id']}' does not exist or is inactive",
                )

        # Validate status transition if requested
        if "status" in data and data["status"] is not None:
            new_status = data["status"]
            effective_expires = data.get("expires_at", listing.expires_at)
            self._validate_status_transition(
                listing, new_status, effective_expires_at=effective_expires
            )

        # Validate quantity consistency
        new_initial = data.get("initial_quantity", listing.initial_quantity)
        new_avail = data.get("available_quantity", listing.available_quantity)

        if new_avail is not None and new_initial is not None:
            if new_avail > new_initial:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Available quantity ({new_avail}) cannot exceed initial quantity ({new_initial})",
                )

        # Validate expiration timestamp
        if "expires_at" in data and data["expires_at"] is not None:
            now = datetime.now(timezone.utc)
            if _ensure_tz_aware(data["expires_at"]) <= now:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Listing expiration timestamp must be in the future",
                )

        updated = self.repository.update_listing(listing, data)
        loaded = self.repository.get_listing_by_id(updated.id) or updated
        return self._to_detail_response(loaded)

    def update_listing_status(
        self,
        listing_id: uuid.UUID,
        user: User,
        payload: ListingStatusUpdate,
    ) -> ProduceListingDetailResponse:
        """Transition listing availability/status using documented transitions."""
        listing = self._get_owned_listing(listing_id, user)
        self._validate_status_transition(listing, payload.status)

        updated = self.repository.update_listing(listing, {"status": payload.status})
        loaded = self.repository.get_listing_by_id(updated.id) or updated
        return self._to_detail_response(loaded)

    def soft_delete_listing(self, listing_id: uuid.UUID, user: User) -> None:
        """Soft-delete a produce listing owned by caller (or by admin)."""
        listing = self.repository.get_listing_by_id(listing_id, include_deleted=True)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produce listing '{listing_id}' not found",
            )

        if listing.farmer_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this listing",
            )

        if listing.is_deleted:
            return

        self.repository.soft_delete_listing(listing)

    # -----------------------------------------------------------------------
    # Marketplace Catalog (Public)
    # -----------------------------------------------------------------------

    def search_marketplace(
        self,
        category_id: Optional[uuid.UUID] = None,
        category_slug: Optional[str] = None,
        search_query: Optional[str] = None,
        product_name: Optional[str] = None,
        location_state: Optional[str] = None,
        location_city: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        unit: Optional[str] = None,
        quality_grade: Optional[str] = None,
        farmer_id: Optional[uuid.UUID] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> ProduceListingPublicListResponse:
        """Search and filter public marketplace catalog listings."""
        valid_sort_fields = {"created_at", "price_per_unit", "available_quantity", "product_name"}
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"

        if sort_order.lower() not in ("asc", "desc"):
            sort_order = "desc"

        listings, total = self.repository.search_public_listings(
            category_id=category_id,
            category_slug=category_slug,
            search_query=search_query,
            product_name=product_name,
            location_state=location_state,
            location_city=location_city,
            min_price=min_price,
            max_price=max_price,
            unit=unit,
            quality_grade=quality_grade,
            farmer_id=farmer_id,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = [self._to_public_summary(lst) for lst in listings]

        return ProduceListingPublicListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # -----------------------------------------------------------------------
    # Listing Images
    # -----------------------------------------------------------------------

    def upload_listing_image(
        self,
        listing_id: uuid.UUID,
        user: User,
        upload_file: UploadFile,
        is_primary: bool = False,
        display_order: int = 0,
    ) -> ListingImageResponse:
        """Upload and attach a photographic asset to a listing owned by caller."""
        listing = self._get_owned_listing(listing_id, user)

        current_count = self.repository.count_listing_images(listing_id)
        settings = get_settings()
        max_images = getattr(settings, "max_product_images_per_listing", MAX_IMAGES_PER_LISTING)
        if current_count >= max_images:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Listing already has maximum allowed images ({max_images})",
            )

        # If this is the first image attached, automatically make it primary
        if current_count == 0:
            is_primary = True

        image_uri, _mime_type, _size = self.storage.save_image(upload_file)

        try:
            image = self.repository.add_listing_image(
                listing_id=listing_id,
                image_uri=image_uri,
                is_primary=is_primary,
                display_order=display_order,
            )
        except Exception:
            self.repository.db.rollback()
            try:
                self.storage.delete_image_file(image_uri)
            except Exception as cleanup_err:
                logger.error("Failed to delete orphaned image file %s: %s", image_uri, cleanup_err)
            raise

        return ListingImageResponse.model_validate(image)

    def upload_listing_images(
        self,
        listing_id: uuid.UUID,
        user: User,
        upload_files: List[UploadFile],
    ) -> List[ListingImageResponse]:
        """Batch upload multiple images for a produce listing owned by caller."""
        listing = self._get_owned_listing(listing_id, user)
        settings = get_settings()
        max_images = getattr(settings, "max_product_images_per_listing", MAX_IMAGES_PER_LISTING)

        current_count = self.repository.count_listing_images(listing_id)
        if current_count + len(upload_files) > max_images:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploading {len(upload_files)} image(s) exceeds maximum allowed images ({max_images}). Current count: {current_count}",
            )

        saved_entries = []
        saved_uris = []
        try:
            for idx, file in enumerate(upload_files):
                image_uri, _mime, _size = self.storage.save_image(file)
                saved_uris.append(image_uri)
                # First image is primary if listing currently has no images
                is_prim = (current_count == 0 and idx == 0)
                saved_entries.append({
                    "image_uri": image_uri,
                    "is_primary": is_prim,
                    "display_order": current_count + idx,
                })

            images = self.repository.add_listing_images(
                listing_id=listing_id,
                image_entries=saved_entries,
            )
            return [ListingImageResponse.model_validate(img) for img in images]
        except Exception:
            self.repository.db.rollback()
            # Clean up all saved physical files on any error
            for uri in saved_uris:
                try:
                    self.storage.delete_image_file(uri)
                except Exception as cleanup_err:
                    logger.error("Failed to delete orphaned image file %s: %s", uri, cleanup_err)
            raise

    def list_listing_images(
        self,
        listing_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> List[ListingImageResponse]:
        """List all images attached to a produce listing."""
        listing = self.repository.get_listing_by_id(listing_id, include_deleted=True)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing '{listing_id}' not found",
            )

        is_owner = current_user is not None and (listing.farmer_id == current_user.id)
        is_admin = current_user is not None and (current_user.role == "admin")

        if not (is_owner or is_admin):
            now = datetime.now(timezone.utc)
            expires_at = _ensure_tz_aware(listing.expires_at)
            farmer = listing.farmer
            farmer_active_and_verified = (
                farmer is not None
                and farmer.account_status == "active"
                and farmer.verification_status == "verified"
            )
            if (
                listing.is_deleted
                or listing.status != STATUS_ACTIVE
                or listing.available_quantity <= 0
                or expires_at <= now
                or not farmer_active_and_verified
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Listing '{listing_id}' not found",
                )

        images = self.repository.list_listing_images(listing_id)
        return [ListingImageResponse.model_validate(img) for img in images]

    def reorder_listing_images(
        self,
        listing_id: uuid.UUID,
        user: User,
        image_ids: List[uuid.UUID],
    ) -> List[ListingImageResponse]:
        """Update display order for images attached to a listing."""
        self._get_owned_listing(listing_id, user)
        existing = {img.id: img for img in self.repository.list_listing_images(listing_id)}
        for img_id in image_ids:
            if img_id not in existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Image '{img_id}' does not belong to listing '{listing_id}'",
                )

        reordered = self.repository.reorder_listing_images(listing_id=listing_id, image_ids=image_ids)
        return [ListingImageResponse.model_validate(img) for img in reordered]

    def delete_listing_image(
        self,
        listing_id: uuid.UUID,
        image_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete an image attached to a listing owned by caller."""
        self._get_owned_listing(listing_id, user)

        image = self.repository.get_listing_image(image_id=image_id, listing_id=listing_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image '{image_id}' not found on listing '{listing_id}'",
            )

        image_uri = image.image_uri

        # 1. Execute database deletion & primary reassignment within single transaction
        try:
            self.repository.delete_listing_image(image)
        except Exception:
            self.repository.db.rollback()
            raise

        # 2. Only after successful commit, unlink physical storage file
        try:
            self.storage.delete_image_file(image_uri)
        except Exception as exc:
            logger.error("Failed to delete physical file %s after DB deletion: %s", image_uri, exc)

    def set_primary_image(
        self,
        listing_id: uuid.UUID,
        image_id: uuid.UUID,
        user: User,
    ) -> ListingImageResponse:
        """Mark an image as primary thumbnail for a listing owned by caller."""
        self._get_owned_listing(listing_id, user)

        updated = self.repository.set_primary_image(listing_id=listing_id, image_id=image_id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image '{image_id}' not found on listing '{listing_id}'",
            )
        return ListingImageResponse.model_validate(updated)

    def get_image_file_path(
        self,
        listing_id: uuid.UUID,
        image_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> Path:
        """Resolve filesystem path for downloading/viewing a listing image.

        Enforces visibility rules:
        - Image must belong to the specified listing.
        - Public / non-owner callers can access only if parent listing is active,
          unexpired, available_quantity > 0, not deleted, and farmer is active & verified.
        - Listing owner or admin can view images for non-public listings (e.g. draft, closed).
        - Soft-deleted listings are blocked from non-admins.
        - Unauthorized requests return non-disclosing 404 Not Found.
        """
        image = self.repository.get_listing_image(image_id=image_id, listing_id=listing_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image '{image_id}' not found",
            )

        listing = self.repository.get_listing_by_id(listing_id, include_deleted=True)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image '{image_id}' not found",
            )

        is_owner = current_user is not None and (listing.farmer_id == current_user.id)
        is_admin = current_user is not None and (current_user.role == "admin")

        if not (is_owner or is_admin):
            now = datetime.now(timezone.utc)
            expires_at = _ensure_tz_aware(listing.expires_at)
            farmer = listing.farmer
            farmer_active_and_verified = (
                farmer is not None
                and farmer.account_status == "active"
                and farmer.verification_status == "verified"
            )
            if (
                listing.is_deleted
                or listing.status != STATUS_ACTIVE
                or listing.available_quantity <= 0
                or expires_at <= now
                or not farmer_active_and_verified
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Image '{image_id}' not found",
                )
        else:
            if listing.is_deleted and not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Image '{image_id}' not found",
                )

        return self.storage.resolve_path(image.image_uri)

    # -----------------------------------------------------------------------
    # Helper & Validation Methods
    # -----------------------------------------------------------------------

    def _require_verified_farmer(self, user: User) -> None:
        """Enforce that caller is an active, verified farmer."""
        if user.role != "farmer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a farmer account",
            )
        if user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a verified farmer account",
            )
        if user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended",
            )

    def _get_owned_listing(self, listing_id: uuid.UUID, user: User) -> ProduceListing:
        """Retrieve listing ensuring caller is the farmer owner and it is not deleted."""
        self._require_verified_farmer(user)

        listing = self.repository.get_listing_by_id(listing_id, include_deleted=True)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produce listing '{listing_id}' not found",
            )

        if listing.farmer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access or modify this listing",
            )

        if listing.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a deleted listing",
            )

        return listing

    def _validate_status_transition(
        self,
        listing: ProduceListing,
        new_status: str,
        effective_expires_at: Optional[datetime] = None,
    ) -> None:
        """Validate that a requested status transition is legally permitted."""
        current_status = listing.status
        if current_status == new_status:
            return

        allowed = PERMITTED_STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from '{current_status}' to '{new_status}'. "
                    f"Permitted target statuses: {', '.join(sorted(allowed)) if allowed else 'none'}"
                ),
            )

        # When reopening to active from closed, ensure quantity > 0 and expiration in future
        if new_status == STATUS_ACTIVE:
            now = datetime.now(timezone.utc)
            if listing.available_quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot activate listing with 0 available quantity",
                )
            target_expires = effective_expires_at if effective_expires_at is not None else listing.expires_at
            if _ensure_tz_aware(target_expires) <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot activate listing that has already expired; please update expiration date first",
                )

    def _to_detail_response(self, listing: ProduceListing) -> ProduceListingDetailResponse:
        """Map ORM ProduceListing model to ProduceListingDetailResponse."""
        category_resp = None
        if listing.category:
            category_resp = CategoryResponse.model_validate(listing.category)

        farmer_summary = None
        farmer_user = listing.farmer
        if farmer_user:
            profile = getattr(farmer_user, "farmer_profile", None)
            farmer_summary = FarmerSummary(
                id=farmer_user.id,
                full_name=getattr(profile, "full_name", "Farmer"),
                farm_name=getattr(profile, "farm_name", "Farm"),
                city=getattr(profile, "city", listing.location_city),
                state=getattr(profile, "state", listing.location_state),
            )

        images = [ListingImageResponse.model_validate(img) for img in (listing.images or [])]

        return ProduceListingDetailResponse(
            id=listing.id,
            farmer_id=listing.farmer_id,
            category_id=listing.category_id,
            category=category_resp,
            product_name=listing.product_name,
            title=listing.title,
            description=listing.description,
            initial_quantity=listing.initial_quantity,
            available_quantity=listing.available_quantity,
            unit=listing.unit,
            price_per_unit=listing.price_per_unit,
            quality_grade=listing.quality_grade,
            location_state=listing.location_state,
            location_city=listing.location_city,
            harvest_date=listing.harvest_date,
            available_from=listing.available_from,
            expires_at=listing.expires_at,
            status=listing.status,
            is_deleted=listing.is_deleted,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
            images=images,
            farmer=farmer_summary,
        )

    def _to_public_summary(self, listing: ProduceListing) -> ProduceListingPublicSummary:
        """Map ORM ProduceListing model to ProduceListingPublicSummary."""
        primary_uri = None
        primary_url = None
        images = []
        if listing.images:
            images = [ListingImageResponse.model_validate(img) for img in listing.images]
            for img in listing.images:
                if img.is_primary:
                    primary_uri = img.image_uri
                    primary_url = f"/api/v1/listings/{listing.id}/images/{img.id}"
                    break
            if not primary_uri and listing.images:
                primary_uri = listing.images[0].image_uri
                primary_url = f"/api/v1/listings/{listing.id}/images/{listing.images[0].id}"

        farmer_summary = None
        farmer_user = listing.farmer
        if farmer_user:
            profile = getattr(farmer_user, "farmer_profile", None)
            farmer_summary = FarmerSummary(
                id=farmer_user.id,
                full_name=getattr(profile, "full_name", "Farmer"),
                farm_name=getattr(profile, "farm_name", "Farm"),
                city=getattr(profile, "city", listing.location_city),
                state=getattr(profile, "state", listing.location_state),
            )

        return ProduceListingPublicSummary(
            id=listing.id,
            category_id=listing.category_id,
            category_name=listing.category.name if listing.category else None,
            product_name=listing.product_name,
            title=listing.title,
            description=listing.description,
            available_quantity=listing.available_quantity,
            unit=listing.unit,
            price_per_unit=listing.price_per_unit,
            quality_grade=listing.quality_grade,
            location_state=listing.location_state,
            location_city=listing.location_city,
            harvest_date=listing.harvest_date,
            available_from=listing.available_from,
            expires_at=listing.expires_at,
            status=listing.status,
            created_at=listing.created_at,
            primary_image_uri=primary_uri,
            primary_image_url=primary_url,
            images=images,
            farmer=farmer_summary,
        )
