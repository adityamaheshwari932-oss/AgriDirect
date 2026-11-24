"""FastAPI route handlers for produce catalog, listings, and image endpoints.

Implements Module 2 (Catalog, Listings, and Media Assets) under /api/v1:
- ``POST /api/v1/listings``: Create listing (verified farmer only)
- ``GET /api/v1/listings/me``: View own listings (verified farmer only)
- ``GET /api/v1/listings/categories``: Browse produce taxonomy categories (public)
- ``GET /api/v1/listings``: Search and filter marketplace listings (public)
- ``GET /api/v1/listings/{id}``: Retrieve listing details (public active / owner full)
- ``PATCH /api/v1/listings/{id}``: Update listing fields (owner only)
- ``PATCH /api/v1/listings/{id}/status``: Transition listing status (owner only)
- ``DELETE /api/v1/listings/{id}``: Soft-delete listing (owner or admin)
- ``POST /api/v1/listings/{id}/images``: Upload listing image (owner only)
- ``DELETE /api/v1/listings/{id}/images/{image_id}``: Delete listing image (owner only)
- ``PATCH /api/v1/listings/{id}/images/{image_id}/primary``: Set primary image (owner only)
- ``GET /api/v1/listings/{id}/images/{image_id}``: Download / view image file (public)
"""

import uuid
from decimal import Decimal
from typing import Annotated, List, Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import (
    get_current_active_user,
    get_current_user,
    http_bearer,
    require_verified_farmer,
)
from app.listings.schemas import (
    CategoryResponse,
    FarmerListingListResponse,
    ListingCreate,
    ListingImageResponse,
    ListingImagesReorderRequest,
    ListingStatusUpdate,
    ListingUpdate,
    ProduceListingDetailResponse,
    ProduceListingPublicListResponse,
)
from app.listings.service import ListingService
from app.models.user import User

router = APIRouter(prefix="/listings", tags=["produce-listings"])


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user if Bearer token is provided, or return None."""
    if not credentials:
        return None
    try:
        return get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Produce Categories
# ---------------------------------------------------------------------------

@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="List produce taxonomy categories",
    description="Returns active produce categories for search filtering and listing categorization.",
    status_code=status.HTTP_200_OK,
)
def list_categories(db: Session = Depends(get_db)) -> List[CategoryResponse]:
    """Retrieve all active taxonomy categories."""
    service = ListingService(db)
    return service.list_active_categories()


# ---------------------------------------------------------------------------
# Farmer Listing Management (Own Listings)
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ProduceListingDetailResponse,
    summary="Create a produce listing",
    description=(
        "Creates a new produce listing. Restricted to authenticated, active, verified farmers. "
        "Server strictly derives owner ID from authentication token."
    ),
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    payload: ListingCreate,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> ProduceListingDetailResponse:
    """Create a new produce listing."""
    service = ListingService(db)
    return service.create_listing(user=current_user, payload=payload)


@router.get(
    "/me",
    response_model=FarmerListingListResponse,
    summary="List own produce listings",
    description="Returns paginated produce listings created by the authenticated verified farmer.",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/mine",
    response_model=FarmerListingListResponse,
    include_in_schema=False,
)
def list_my_listings(
    status_filter: Annotated[
        Optional[str],
        Query(alias="status", description="Filter by listing status (draft, active, closed, etc.)"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> FarmerListingListResponse:
    """List authenticated farmer's own listings."""
    service = ListingService(db)
    return service.list_farmer_listings(
        user=current_user,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Marketplace Catalog (Public Browsing & Search)
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ProduceListingPublicListResponse,
    summary="Browse and search marketplace catalog",
    description=(
        "Publicly browsable marketplace catalog. Automatically restricts results to active, "
        "non-deleted, unexpired listings with available quantity > 0. Returns sanitized public cards."
    ),
    status_code=status.HTTP_200_OK,
)
def search_marketplace(
    category_id: Annotated[Optional[uuid.UUID], Query(description="Filter by category UUID")] = None,
    category_slug: Annotated[Optional[str], Query(description="Filter by category slug")] = None,
    q: Annotated[Optional[str], Query(description="Search produce name, title, or description")] = None,
    product_name: Annotated[Optional[str], Query(description="Filter by produce name")] = None,
    state: Annotated[Optional[str], Query(alias="location_state", description="Filter by sourcing state")] = None,
    city: Annotated[Optional[str], Query(alias="location_city", description="Filter by sourcing city")] = None,
    min_price: Annotated[Optional[Decimal], Query(ge=0, description="Minimum price per unit")] = None,
    max_price: Annotated[Optional[Decimal], Query(ge=0, description="Maximum price per unit")] = None,
    unit: Annotated[Optional[str], Query(description="Filter by measurement unit (kg, quintal, bag, etc.)")] = None,
    quality_grade: Annotated[Optional[str], Query(description="Filter by quality grade (Grade A, Organic, etc.)")] = None,
    farmer_id: Annotated[Optional[uuid.UUID], Query(description="Filter by specific farmer UUID")] = None,
    sort_by: Annotated[
        str,
        Query(description="Sort field: created_at, price_per_unit, available_quantity, product_name"),
    ] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc, desc")] = "desc",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    db: Session = Depends(get_db),
) -> ProduceListingPublicListResponse:
    """Browse public marketplace catalog."""
    service = ListingService(db)
    return service.search_marketplace(
        category_id=category_id,
        category_slug=category_slug,
        search_query=q,
        product_name=product_name,
        location_state=state,
        location_city=city,
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


# ---------------------------------------------------------------------------
# Individual Listing Details & Management
# ---------------------------------------------------------------------------

@router.get(
    "/{id}",
    response_model=ProduceListingDetailResponse,
    summary="Retrieve listing details",
    description=(
        "Retrieves detailed information for a produce listing. Active listings are publicly viewable. "
        "Draft, closed, or expired listings are viewable only by their farmer owner or administrators."
    ),
    status_code=status.HTTP_200_OK,
)
def get_listing_detail(
    id: uuid.UUID,
    optional_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ProduceListingDetailResponse:
    """Retrieve produce listing details."""
    service = ListingService(db)
    return service.get_listing_detail(listing_id=id, current_user=optional_user)


@router.patch(
    "/{id}",
    response_model=ProduceListingDetailResponse,
    summary="Update listing details",
    description=(
        "Updates permitted attributes of a produce listing. Strictly restricted to the farmer owner. "
        "Server-controlled fields (id, farmer_id, timestamps) cannot be modified."
    ),
    status_code=status.HTTP_200_OK,
)
def update_listing(
    id: uuid.UUID,
    payload: ListingUpdate,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> ProduceListingDetailResponse:
    """Update permitted fields on a produce listing."""
    service = ListingService(db)
    return service.update_listing(listing_id=id, user=current_user, payload=payload)


@router.patch(
    "/{id}/status",
    response_model=ProduceListingDetailResponse,
    summary="Transition listing status",
    description=(
        "Transitions listing lifecycle status using documented transitions (draft -> active, "
        "active -> closed, closed -> active). Restricted to the farmer owner."
    ),
    status_code=status.HTTP_200_OK,
)
def update_listing_status(
    id: uuid.UUID,
    payload: ListingStatusUpdate,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> ProduceListingDetailResponse:
    """Transition listing status."""
    service = ListingService(db)
    return service.update_listing_status(listing_id=id, user=current_user, payload=payload)


@router.delete(
    "/{id}",
    summary="Soft-delete produce listing",
    description=(
        "Soft-deletes a produce listing. Listing is marked as deleted and status set to closed. "
        "Restricted to the farmer owner or platform administrator."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_listing(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete a produce listing."""
    service = ListingService(db)
    service.soft_delete_listing(listing_id=id, user=current_user)


# ---------------------------------------------------------------------------
# Listing Images
# ---------------------------------------------------------------------------

@router.get(
    "/{id}/images",
    response_model=List[ListingImageResponse],
    summary="List all listing images",
    description="Returns all images attached to a produce listing ordered by display order.",
    status_code=status.HTTP_200_OK,
)
def list_listing_images(
    id: uuid.UUID,
    optional_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> List[ListingImageResponse]:
    """Retrieve all images attached to a produce listing."""
    service = ListingService(db)
    return service.list_listing_images(listing_id=id, current_user=optional_user)


@router.post(
    "/{id}/images",
    response_model=Union[ListingImageResponse, List[ListingImageResponse]],
    summary="Upload listing image(s)",
    description=(
        "Uploads and attaches one or more photographic assets to a produce listing. "
        "Restricted to the farmer owner. Validates image mime types (JPEG, PNG, WebP), "
        "binary magic bytes, and size (<= 5 MB)."
    ),
    status_code=status.HTTP_201_CREATED,
)
def upload_listing_image(
    id: uuid.UUID,
    file: Optional[UploadFile] = File(None, description="Single photographic image file (JPEG, PNG, WebP)"),
    files: Optional[List[UploadFile]] = File(None, description="Multiple photographic image files"),
    is_primary: bool = Form(False, description="Whether this image is primary thumbnail"),
    display_order: int = Form(0, description="Display sort order"),
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> Union[ListingImageResponse, List[ListingImageResponse]]:
    """Upload and attach photo(s) to a produce listing."""
    service = ListingService(db)

    upload_files: List[UploadFile] = []
    if files:
        upload_files.extend(files)
    if file:
        upload_files.append(file)

    if not upload_files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one image file ('file' or 'files') must be provided",
        )

    # Single-file upload via 'file' parameter returns single response
    if len(upload_files) == 1 and file is not None and not files:
        return service.upload_listing_image(
            listing_id=id,
            user=current_user,
            upload_file=file,
            is_primary=is_primary,
            display_order=display_order,
        )

    return service.upload_listing_images(
        listing_id=id,
        user=current_user,
        upload_files=upload_files,
    )


@router.delete(
    "/{id}/images/{image_id}",
    summary="Delete listing image",
    description="Deletes an attached image and removes it from storage. Restricted to the farmer owner.",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_listing_image(
    id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> None:
    """Delete an image attached to a produce listing."""
    service = ListingService(db)
    service.delete_listing_image(listing_id=id, image_id=image_id, user=current_user)


@router.patch(
    "/{id}/images/{image_id}/primary",
    response_model=ListingImageResponse,
    summary="Set primary listing image",
    description="Designates an attached image as the primary catalog thumbnail. Restricted to farmer owner.",
    status_code=status.HTTP_200_OK,
)
def set_primary_listing_image(
    id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> ListingImageResponse:
    """Designate primary catalog image thumbnail."""
    service = ListingService(db)
    return service.set_primary_image(listing_id=id, image_id=image_id, user=current_user)


@router.patch(
    "/{id}/images/reorder",
    response_model=List[ListingImageResponse],
    summary="Reorder listing images",
    description="Updates presentation display order of images attached to a produce listing. Restricted to farmer owner.",
    status_code=status.HTTP_200_OK,
)
def reorder_listing_images(
    id: uuid.UUID,
    payload: ListingImagesReorderRequest,
    current_user: User = Depends(require_verified_farmer),
    db: Session = Depends(get_db),
) -> List[ListingImageResponse]:
    """Reorder gallery images."""
    service = ListingService(db)
    return service.reorder_listing_images(
        listing_id=id,
        user=current_user,
        image_ids=payload.image_ids,
    )


@router.get(
    "/{id}/images/{image_id}",
    summary="Download or view listing image file",
    description=(
        "Streams the raw image file for catalog rendering. Publicly accessible for active, "
        "unexpired listings with positive availability. Draft or closed listing images require "
        "farmer ownership or administrative authorization."
    ),
    status_code=status.HTTP_200_OK,
)
def download_listing_image(
    id: uuid.UUID,
    image_id: uuid.UUID,
    optional_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream raw image file."""
    service = ListingService(db)
    file_path = service.get_image_file_path(
        listing_id=id, image_id=image_id, current_user=optional_user
    )
    return FileResponse(path=file_path)


# ---------------------------------------------------------------------------
# Product Alias Router (/api/v1/products/...)
# Supports product-level media endpoints for compatibility with both
# /api/v1/listings/{id}/images and /api/v1/products/{id}/images conventions.
# ---------------------------------------------------------------------------

products_router = APIRouter(prefix="/products", tags=["products"])

products_router.add_api_route(
    "/{id}/images",
    list_listing_images,
    methods=["GET"],
    response_model=List[ListingImageResponse],
    summary="List images attached to a product (alias)",
)
products_router.add_api_route(
    "/{id}/images",
    upload_listing_image,
    methods=["POST"],
    response_model=Union[ListingImageResponse, List[ListingImageResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Upload image(s) for a product (alias)",
)
products_router.add_api_route(
    "/{id}/images/{image_id}",
    delete_listing_image,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product image (alias)",
)
products_router.add_api_route(
    "/{id}/images/{image_id}/primary",
    set_primary_listing_image,
    methods=["PATCH"],
    response_model=ListingImageResponse,
    summary="Set primary product image (alias)",
)
products_router.add_api_route(
    "/{id}/images/reorder",
    reorder_listing_images,
    methods=["PATCH"],
    response_model=List[ListingImageResponse],
    summary="Reorder product images (alias)",
)
products_router.add_api_route(
    "/{id}/images/{image_id}",
    download_listing_image,
    methods=["GET"],
    summary="Download or view product image file (alias)",
)


