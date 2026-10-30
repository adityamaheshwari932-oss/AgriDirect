"""FastAPI route handlers for commercial buyer procurement requirements.

Implements Module 2 (Buyer Requirements Management) under /api/v1:
- ``POST /api/v1/requirements``: Create requirement (verified buyer only)
- ``GET /api/v1/requirements/me``: View own requirements (verified buyer only)
- ``GET /api/v1/requirements``: Search and filter marketplace requirements (public)
- ``GET /api/v1/requirements/{id}`: Retrieve requirement details (public active / owner full)
- ``PATCH /api/v1/requirements/{id}`: Update requirement fields (owner only)
- ``PATCH /api/v1/requirements/{id}/status``: Transition requirement status (owner only)
- ``DELETE /api/v1/requirements/{id}`: Soft-delete requirement (owner or admin)
"""

import uuid
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import (
    get_current_active_user,
    get_current_user,
    http_bearer,
    require_verified_buyer,
)
from app.models.user import User
from app.requirements.approval_service import FulfillmentApprovalService
from app.requirements.schemas import (
    ApproveFulfillmentRequest,
    BuyerRequirementDetailResponse,
    BuyerRequirementListResponse,
    BuyerRequirementPublicListResponse,
    FulfillmentApprovalListResponse,
    FulfillmentApprovalResponse,
    RejectFulfillmentRequest,
    RequirementCreate,
    RequirementStatusUpdate,
    RequirementUpdate,
)
from app.requirements.service import RequirementService

router = APIRouter(prefix="/requirements", tags=["buyer-requirements"])


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
# Buyer Requirement Management (Creation & Own Requirements)
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BuyerRequirementDetailResponse,
    summary="Create a buyer procurement requirement",
    description=(
        "Creates a new procurement demand requirement. Restricted to authenticated, active, verified buyers. "
        "Server strictly derives owner buyer ID from authentication token."
    ),
    status_code=status.HTTP_201_CREATED,
)
def create_requirement(
    payload: RequirementCreate,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> BuyerRequirementDetailResponse:
    """Create a new procurement requirement."""
    service = RequirementService(db)
    return service.create_requirement(user=current_user, payload=payload)


@router.get(
    "/me",
    response_model=BuyerRequirementListResponse,
    summary="List own procurement requirements",
    description="Returns paginated requirements created by the authenticated verified commercial buyer.",
    status_code=status.HTTP_200_OK,
)
def list_my_requirements(
    status_filter: Annotated[
        Optional[str],
        Query(alias="status", description="Filter by requirement status (draft, active, closed, etc.)"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> BuyerRequirementListResponse:
    """List authenticated buyer's own requirements."""
    service = RequirementService(db)
    return service.list_buyer_requirements(
        user=current_user,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Requirement Fulfillment Approvals (ADR-003)
# ---------------------------------------------------------------------------

@router.get(
    "/fulfillment-approvals",
    response_model=FulfillmentApprovalListResponse,
    summary="List fulfillment approvals for authenticated buyer",
    description="Returns paginated fulfillment approval requests for requirements owned by the authenticated verified buyer.",
    status_code=status.HTTP_200_OK,
)
def list_fulfillment_approvals(
    status_filter: Annotated[
        Optional[str],
        Query(alias="status", description="Filter by approval status (pending, approved, rejected, not_applied, voided)"),
    ] = None,
    requirement_id: Annotated[
        Optional[uuid.UUID],
        Query(description="Filter by specific requirement UUID"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> FulfillmentApprovalListResponse:
    """List fulfillment approvals for the current buyer's requirements."""
    service = FulfillmentApprovalService(db)
    return service.list_approvals(
        current_user=current_user,
        status_filter=status_filter,
        requirement_id=requirement_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/fulfillment-approvals/{id}",
    response_model=FulfillmentApprovalResponse,
    summary="Get fulfillment approval details",
    description="Retrieve details of a specific fulfillment approval request. Enforces buyer ownership with anti-enumeration security.",
    status_code=status.HTTP_200_OK,
)
def get_fulfillment_approval(
    id: uuid.UUID,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> FulfillmentApprovalResponse:
    """Retrieve details of a single fulfillment approval."""
    service = FulfillmentApprovalService(db)
    return service.get_approval(current_user=current_user, approval_id=id)


@router.post(
    "/fulfillment-approvals/{id}/approve",
    response_model=FulfillmentApprovalResponse,
    summary="Approve requirement fulfillment",
    description="Approve full or partial fulfillment of a buyer requirement. Atomically decrements remaining demand without altering commercial order quantity.",
    status_code=status.HTTP_200_OK,
)
def approve_fulfillment(
    id: uuid.UUID,
    payload: ApproveFulfillmentRequest,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> FulfillmentApprovalResponse:
    """Approve a pending requirement fulfillment request."""
    service = FulfillmentApprovalService(db)
    return service.approve_fulfillment(current_user=current_user, approval_id=id, payload=payload)


@router.post(
    "/fulfillment-approvals/{id}/reject",
    response_model=FulfillmentApprovalResponse,
    summary="Reject requirement fulfillment",
    description="Reject applying an order toward requirement fulfillment. Preserves open requirement demand per FR-REQ-08.",
    status_code=status.HTTP_200_OK,
)
def reject_fulfillment(
    id: uuid.UUID,
    payload: RejectFulfillmentRequest,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> FulfillmentApprovalResponse:
    """Reject a pending requirement fulfillment request."""
    service = FulfillmentApprovalService(db)
    return service.reject_fulfillment(current_user=current_user, approval_id=id, payload=payload)



# ---------------------------------------------------------------------------
# Marketplace Demand Catalog (Public Browsing & Search)
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=BuyerRequirementPublicListResponse,
    summary="Browse and search marketplace buyer requirements",
    description=(
        "Publicly browsable demand catalog. Automatically restricts results to active or partially "
        "fulfilled, unexpired requirements with remaining quantity > 0 from verified buyers. Returns sanitized cards."
    ),
    status_code=status.HTTP_200_OK,
)
def search_marketplace(
    category_id: Annotated[Optional[uuid.UUID], Query(description="Filter by category UUID")] = None,
    category_slug: Annotated[Optional[str], Query(description="Filter by category slug")] = None,
    q: Annotated[Optional[str], Query(description="Search produce name, title, or description")] = None,
    product_name: Annotated[Optional[str], Query(description="Filter by produce name")] = None,
    destination_state: Annotated[Optional[str], Query(description="Filter by delivery destination state")] = None,
    destination_city: Annotated[Optional[str], Query(description="Filter by delivery destination city")] = None,
    state: Annotated[Optional[str], Query(description="Filter by delivery destination state (alias)")] = None,
    city: Annotated[Optional[str], Query(description="Filter by delivery destination city (alias)")] = None,
    min_price: Annotated[Optional[Decimal], Query(ge=0, description="Minimum target price per unit")] = None,
    max_price: Annotated[Optional[Decimal], Query(ge=0, description="Maximum target price per unit")] = None,
    min_quantity: Annotated[Optional[Decimal], Query(ge=0, description="Minimum available demand quantity")] = None,
    max_quantity: Annotated[Optional[Decimal], Query(ge=0, description="Maximum available demand quantity")] = None,
    unit: Annotated[Optional[str], Query(description="Filter by measurement unit (kg, quintal, etc.)")] = None,
    quality_grade: Annotated[Optional[str], Query(description="Filter by quality grade")] = None,
    price_condition: Annotated[Optional[str], Query(description="Filter by price condition ('exact', 'range', 'negotiable')")] = None,
    buyer_id: Annotated[Optional[uuid.UUID], Query(description="Filter by specific buyer UUID")] = None,
    sort_by: Annotated[
        str,
        Query(description="Sort field: created_at, required_by_date, required_quantity, target_price_per_unit, product_name"),
    ] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc, desc")] = "desc",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    db: Session = Depends(get_db),
) -> BuyerRequirementPublicListResponse:
    """Browse public marketplace buyer requirements catalog."""
    service = RequirementService(db)
    return service.search_marketplace(
        category_id=category_id,
        category_slug=category_slug,
        search_query=q,
        product_name=product_name,
        destination_state=destination_state or state,
        destination_city=destination_city or city,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        unit=unit,
        quality_grade=quality_grade,
        price_condition=price_condition,
        buyer_id=buyer_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Individual Requirement Details & Management
# ---------------------------------------------------------------------------

@router.get(
    "/{id}",
    response_model=BuyerRequirementDetailResponse,
    summary="Retrieve requirement details",
    description=(
        "Retrieves detailed information for a buyer requirement. Active requirements are publicly viewable. "
        "Draft, closed, or expired requirements are viewable only by their buyer owner or administrators."
    ),
    status_code=status.HTTP_200_OK,
)
def get_requirement_detail(
    id: uuid.UUID,
    optional_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> BuyerRequirementDetailResponse:
    """Retrieve requirement details."""
    service = RequirementService(db)
    return service.get_requirement_detail(requirement_id=id, current_user=optional_user)


@router.patch(
    "/{id}",
    response_model=BuyerRequirementDetailResponse,
    summary="Update requirement details",
    description=(
        "Updates permitted attributes of a buyer requirement. Strictly restricted to the buyer owner. "
        "Server-controlled fields (id, buyer_id, timestamps, soft-delete) cannot be modified."
    ),
    status_code=status.HTTP_200_OK,
)
def update_requirement(
    id: uuid.UUID,
    payload: RequirementUpdate,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> BuyerRequirementDetailResponse:
    """Update permitted fields on a requirement."""
    service = RequirementService(db)
    return service.update_requirement(requirement_id=id, user=current_user, payload=payload)


@router.patch(
    "/{id}/status",
    response_model=BuyerRequirementDetailResponse,
    summary="Transition requirement status",
    description=(
        "Transitions requirement lifecycle status using documented transitions (draft -> active, "
        "active -> closed, closed -> active). Restricted to the buyer owner."
    ),
    status_code=status.HTTP_200_OK,
)
def update_requirement_status(
    id: uuid.UUID,
    payload: RequirementStatusUpdate,
    current_user: User = Depends(require_verified_buyer),
    db: Session = Depends(get_db),
) -> BuyerRequirementDetailResponse:
    """Transition requirement status."""
    service = RequirementService(db)
    return service.update_requirement_status(requirement_id=id, user=current_user, payload=payload)


@router.delete(
    "/{id}",
    summary="Soft-delete buyer requirement",
    description=(
        "Soft-deletes a buyer requirement. Requirement is marked as deleted and status set to closed. "
        "Restricted to the buyer owner or platform administrator."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_requirement(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete a buyer requirement."""
    service = RequirementService(db)
    service.soft_delete_requirement(requirement_id=id, user=current_user)

