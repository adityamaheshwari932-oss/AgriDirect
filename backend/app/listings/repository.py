"""Database repository layer for produce catalog, listings, and images.

Implements synchronous SQLAlchemy queries, filtering, sorting, pagination, and persistence.
Adheres to ADR-002: Synchronous Session via Psycopg 3, parameterised queries, no raw SQL.
"""

import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.listing import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    ListingImage,
    ProduceCategory,
    ProduceListing,
)
from app.models.user import User


class ListingRepository:
    """Manages database operations for produce categories, listings, and images."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Produce Categories
    # -----------------------------------------------------------------------

    def get_category_by_id(self, category_id: uuid.UUID) -> Optional[ProduceCategory]:
        """Retrieve a produce category by UUID."""
        return self.db.query(ProduceCategory).filter(ProduceCategory.id == category_id).first()

    def get_category_by_slug(self, slug: str) -> Optional[ProduceCategory]:
        """Retrieve a produce category by unique slug."""
        return self.db.query(ProduceCategory).filter(ProduceCategory.slug == slug).first()

    def list_categories(self, active_only: bool = True) -> List[ProduceCategory]:
        """List produce categories, ordered by name."""
        query = self.db.query(ProduceCategory)
        if active_only:
            query = query.filter(ProduceCategory.is_active.is_(True))
        return query.order_by(ProduceCategory.name.asc()).all()

    # -----------------------------------------------------------------------
    # Produce Listings
    # -----------------------------------------------------------------------

    def create_listing(self, listing_data: Dict[str, Any]) -> ProduceListing:
        """Create and persist a new produce listing."""
        listing = ProduceListing(**listing_data)
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_listing_by_id(
        self,
        listing_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[ProduceListing]:
        """Retrieve a listing by UUID with attached category, images, and farmer."""
        query = (
            self.db.query(ProduceListing)
            .options(
                joinedload(ProduceListing.category),
                selectinload(ProduceListing.images),
                joinedload(ProduceListing.farmer).joinedload(User.farmer_profile),
            )
            .filter(ProduceListing.id == listing_id)
        )
        if not include_deleted:
            query = query.filter(ProduceListing.is_deleted.is_(False))
        return query.first()

    def list_farmer_listings(
        self,
        farmer_id: uuid.UUID,
        status_filter: Optional[str] = None,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ProduceListing], int]:
        """Retrieve paginated listings belonging to a specific farmer.

        Args:
            farmer_id: UUID of the farmer owner.
            status_filter: Optional status filter.
            include_deleted: Whether to include soft-deleted listings.
            page: 1-indexed page number.
            page_size: Number of items per page.

        Returns:
            Tuple of (list_of_listings, total_count).
        """
        query = self.db.query(ProduceListing).filter(ProduceListing.farmer_id == farmer_id)

        if not include_deleted:
            query = query.filter(ProduceListing.is_deleted.is_(False))

        if status_filter:
            query = query.filter(ProduceListing.status == status_filter)

        total_count = query.count()

        offset = (page - 1) * page_size
        listings = (
            query.options(
                joinedload(ProduceListing.category),
                selectinload(ProduceListing.images),
                joinedload(ProduceListing.farmer).joinedload(User.farmer_profile),
            )
            .order_by(ProduceListing.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return listings, total_count

    def search_public_listings(
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
    ) -> Tuple[List[ProduceListing], int]:
        """Search and filter publicly visible active produce listings.

        Enforces mandatory public visibility constraints:
        - is_deleted == False
        - status == 'active'
        - available_quantity > 0
        - expires_at > now()
        - farmer account_status == 'active'
        - farmer verification_status == 'verified'
        """
        now = datetime.now(timezone.utc)
        query = (
            self.db.query(ProduceListing)
            .join(ProduceListing.farmer)
            .filter(
                ProduceListing.is_deleted.is_(False),
                ProduceListing.status == STATUS_ACTIVE,
                ProduceListing.available_quantity > 0,
                ProduceListing.expires_at > now,
                User.account_status == "active",
                User.verification_status == "verified",
            )
        )

        # Filters
        if category_id:
            query = query.filter(ProduceListing.category_id == category_id)

        if category_slug:
            query = query.join(ProduceListing.category).filter(ProduceCategory.slug == category_slug)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.filter(
                (ProduceListing.product_name.ilike(pattern))
                | (ProduceListing.title.ilike(pattern))
                | (ProduceListing.description.ilike(pattern))
            )

        if product_name:
            query = query.filter(ProduceListing.product_name.ilike(f"%{product_name.strip()}%"))

        if location_state:
            query = query.filter(ProduceListing.location_state.ilike(f"%{location_state.strip()}%"))

        if location_city:
            query = query.filter(ProduceListing.location_city.ilike(f"%{location_city.strip()}%"))

        if min_price is not None:
            query = query.filter(ProduceListing.price_per_unit >= min_price)

        if max_price is not None:
            query = query.filter(ProduceListing.price_per_unit <= max_price)

        if unit:
            query = query.filter(ProduceListing.unit == unit.strip())

        if quality_grade:
            query = query.filter(ProduceListing.quality_grade.ilike(f"%{quality_grade.strip()}%"))

        if farmer_id:
            query = query.filter(ProduceListing.farmer_id == farmer_id)

        total_count = query.count()

        # Deterministic sorting
        sort_col = getattr(ProduceListing, sort_by, ProduceListing.created_at)
        if sort_order.lower() == "asc":
            order_expression = sort_col.asc()
        else:
            order_expression = sort_col.desc()

        offset = (page - 1) * page_size
        listings = (
            query.options(
                joinedload(ProduceListing.category),
                selectinload(ProduceListing.images),
                joinedload(ProduceListing.farmer).joinedload(User.farmer_profile),
            )
            .order_by(order_expression, ProduceListing.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return listings, total_count

    def update_listing(self, listing: ProduceListing, data: Dict[str, Any]) -> ProduceListing:
        """Update fields on a produce listing."""
        for key, value in data.items():
            setattr(listing, key, value)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def soft_delete_listing(self, listing: ProduceListing) -> ProduceListing:
        """Mark a listing as soft deleted and set status to closed."""
        listing.is_deleted = True
        listing.deleted_at = datetime.now(timezone.utc)
        listing.status = STATUS_CLOSED
        self.db.commit()
        self.db.refresh(listing)
        return listing

    # -----------------------------------------------------------------------
    # Listing Images
    # -----------------------------------------------------------------------

    def count_listing_images(self, listing_id: uuid.UUID) -> int:
        """Count active images attached to a listing."""
        return self.db.query(ListingImage).filter(ListingImage.listing_id == listing_id).count()

    def add_listing_image(
        self,
        listing_id: uuid.UUID,
        image_uri: str,
        is_primary: bool = False,
        display_order: int = 0,
    ) -> ListingImage:
        """Attach an image to a produce listing."""
        if is_primary:
            # Unset any existing primary image for this listing
            self.db.query(ListingImage).filter(
                ListingImage.listing_id == listing_id,
                ListingImage.is_primary.is_(True),
            ).update({"is_primary": False})

        image = ListingImage(
            listing_id=listing_id,
            image_uri=image_uri,
            is_primary=is_primary,
            display_order=display_order,
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def get_listing_image(
        self,
        image_id: uuid.UUID,
        listing_id: Optional[uuid.UUID] = None,
    ) -> Optional[ListingImage]:
        """Retrieve an image by UUID, optionally ensuring it belongs to a listing."""
        query = self.db.query(ListingImage).filter(ListingImage.id == image_id)
        if listing_id:
            query = query.filter(ListingImage.listing_id == listing_id)
        return query.first()

    def delete_listing_image(self, image: ListingImage) -> None:
        """Delete a listing image row and reassign primary within a single transaction.

        If the deleted image was primary, promotes another remaining image if one exists.
        """
        listing_id = image.listing_id
        was_primary = image.is_primary

        self.db.delete(image)
        if was_primary:
            remaining = (
                self.db.query(ListingImage)
                .filter(
                    ListingImage.listing_id == listing_id,
                    ListingImage.id != image.id,
                )
                .order_by(ListingImage.display_order.asc(), ListingImage.created_at.asc())
                .first()
            )
            if remaining:
                remaining.is_primary = True

        self.db.commit()

    def set_primary_image(
        self,
        listing_id: uuid.UUID,
        image_id: uuid.UUID,
    ) -> Optional[ListingImage]:
        """Set a specific image as the primary image for a listing."""
        image = self.get_listing_image(image_id=image_id, listing_id=listing_id)
        if not image:
            return None

        # Reset all other images for this listing
        self.db.query(ListingImage).filter(
            ListingImage.listing_id == listing_id,
            ListingImage.id != image_id,
        ).update({"is_primary": False})

        image.is_primary = True
        self.db.commit()
        self.db.refresh(image)
        return image

    def list_listing_images(self, listing_id: uuid.UUID) -> List[ListingImage]:
        """List all images attached to a listing ordered by display_order, then created_at."""
        return (
            self.db.query(ListingImage)
            .filter(ListingImage.listing_id == listing_id)
            .order_by(ListingImage.display_order.asc(), ListingImage.created_at.asc())
            .all()
        )

    def reorder_listing_images(
        self,
        listing_id: uuid.UUID,
        image_ids: List[uuid.UUID],
    ) -> List[ListingImage]:
        """Update display_order for images matching listing_id according to the given order."""
        for order_index, img_id in enumerate(image_ids):
            self.db.query(ListingImage).filter(
                ListingImage.listing_id == listing_id,
                ListingImage.id == img_id,
            ).update({"display_order": order_index})
        self.db.commit()
        return self.list_listing_images(listing_id)

    def add_listing_images(
        self,
        listing_id: uuid.UUID,
        image_entries: List[dict],
    ) -> List[ListingImage]:
        """Batch attach multiple images to a produce listing atomically."""
        created_images = []
        for entry in image_entries:
            if entry.get("is_primary"):
                self.db.query(ListingImage).filter(
                    ListingImage.listing_id == listing_id,
                    ListingImage.is_primary.is_(True),
                ).update({"is_primary": False})
            img = ListingImage(
                listing_id=listing_id,
                image_uri=entry["image_uri"],
                is_primary=entry.get("is_primary", False),
                display_order=entry.get("display_order", 0),
            )
            self.db.add(img)
            created_images.append(img)
        self.db.commit()
        for img in created_images:
            self.db.refresh(img)
        return created_images

