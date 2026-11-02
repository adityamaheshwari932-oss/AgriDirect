"""FastAPI route handlers for administrative platform governance and moderation.

Endpoints under /api/v1/admin:
- Audit Trail:
  - GET /api/v1/admin/audit-logs
  - GET /api/v1/admin/audit-logs/{id}
- User Directory & Moderation:
  - GET /api/v1/admin/users
  - GET /api/v1/admin/users/{id}
  - PATCH /api/v1/admin/users/{id}/status
- Catalog Moderation:
  - GET /api/v1/admin/listings
  - POST /api/v1/admin/listings/{id}/moderate
  - GET /api/v1/admin/requirements
  - POST /api/v1/admin/requirements/{id}/moderate
"""

import uuid
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.admin.schemas import (
    AdminAuditLogListResponse,
    AdminAuditLogResponse,
    AdminListingListResponse,
    AdminListingModerateRequest,
    AdminListingModerateResponse,
    AdminRequirementListResponse,
    AdminRequirementModerateRequest,
    AdminRequirementModerateResponse,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserStatusUpdateRequest,
    AdminUserStatusUpdateResponse,
)
from app.admin.service import (
    AdminAuditLogService,
    AdminCatalogModerationService,
    AdminUserModerationService,
)
from app.db.session import get_db
from app.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


# ===========================================================================
# 1. Administrative Audit Logs (Module 8)
# ===========================================================================


@router.get(
    "/audit-logs",
    response_model=AdminAuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List administrative audit logs",
    description="Returns a paginated, chronologically ordered audit log of privileged actions.",
)
def list_admin_audit_logs(
    admin_user_id: Annotated[Optional[uuid.UUID], Query(description="Filter by administrator ID")] = None,
    action: Annotated[Optional[str], Query(description="Filter by action string")] = None,
    target_entity_type: Annotated[Optional[str], Query(description="Filter by target entity type")] = None,
    target_entity_id: Annotated[Optional[uuid.UUID], Query(description="Filter by target entity ID")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminAuditLogListResponse:
    """Retrieve audit trail records."""
    service = AdminAuditLogService(db)
    return service.list_logs(
        current_admin=admin_user,
        admin_user_id=admin_user_id,
        action=action,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/audit-logs/{id}",
    response_model=AdminAuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual audit log entry",
    description="Inspect details of a specific administrative audit record by its primary key.",
)
def get_admin_audit_log(
    id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminAuditLogResponse:
    """Inspect single audit record."""
    service = AdminAuditLogService(db)
    log_entry = service.get_log(log_id=id, current_admin=admin_user)
    return AdminAuditLogResponse.model_validate(log_entry)


# ===========================================================================
# 2. Administrative User Directory & Inspection (Module 10 / Scope A)
# ===========================================================================


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    status_code=status.HTTP_200_OK,
    summary="Administrative user directory",
    description="Filterable, paginated directory of platform users with credential exclusion.",
)
def list_admin_users(
    search: Annotated[Optional[str], Query(description="Search email, phone, name, business")] = None,
    role: Annotated[Optional[str], Query(description="Filter role: farmer, buyer, admin")] = None,
    account_status: Annotated[Optional[str], Query(description="Filter status: active, restricted, suspended, blocked")] = None,
    verification_status: Annotated[Optional[str], Query(description="Filter verification: unverified, pending, verified, rejected")] = None,
    registered_from: Annotated[Optional[date], Query(description="Registration start date")] = None,
    registered_to: Annotated[Optional[date], Query(description="Registration end date")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    sort_by: Annotated[str, Query(description="Sort field: created_at, email, role, account_status")] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc or desc")] = "desc",
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    """List users in admin directory."""
    service = AdminUserModerationService(db)
    return service.list_users(
        current_admin=admin_user,
        search=search,
        role=role,
        account_status_filter=account_status,
        verification_status_filter=verification_status,
        registered_from=registered_from,
        registered_to=registered_to,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/users/{id}",
    response_model=AdminUserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Administrative user inspection",
    description="Comprehensive profile, verification, activity, and audit inspection of a user.",
)
def get_admin_user_detail(
    id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserDetailResponse:
    """Inspect full user details."""
    service = AdminUserModerationService(db)
    return service.get_user_detail(user_id=id, current_admin=admin_user)


# ===========================================================================
# 3. User Account Status Moderation (Module 10 / Scope B)
# ===========================================================================


@router.patch(
    "/users/{id}/status",
    response_model=AdminUserStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Moderate user account status",
    description="Transition account status (active, restricted, suspended, blocked) with mandatory audit logging.",
)
def update_user_account_status(
    id: uuid.UUID,
    payload: AdminUserStatusUpdateRequest,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserStatusUpdateResponse:
    """Moderate user account status."""
    client_ip = request.client.host if request.client else None
    service = AdminUserModerationService(db)
    return service.update_user_status(
        user_id=id,
        current_admin=admin_user,
        payload=payload,
        ip_address=client_ip,
    )


# ===========================================================================
# 4. Produce Listing Moderation (Module 10 / Scope C)
# ===========================================================================


@router.get(
    "/listings",
    response_model=AdminListingListResponse,
    status_code=status.HTTP_200_OK,
    summary="Produce listing moderation queue",
    description="Paginated, filterable moderation queue of produce listings with report counts.",
)
def list_admin_listings(
    search: Annotated[Optional[str], Query(description="Search product name, title, farmer")] = None,
    status: Annotated[Optional[str], Query(description="Filter status: active, closed, expired, draft")] = None,
    category_id: Annotated[Optional[uuid.UUID], Query(description="Filter category ID")] = None,
    farmer_id: Annotated[Optional[uuid.UUID], Query(description="Filter farmer ID")] = None,
    is_deleted: Annotated[Optional[bool], Query(description="Filter soft-deleted listings")] = None,
    has_reports: Annotated[Optional[bool], Query(description="Filter listings with complaints")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    sort_by: Annotated[str, Query(description="Sort field: created_at, product_name, price, status")] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc or desc")] = "desc",
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminListingListResponse:
    """List listings for moderation."""
    service = AdminCatalogModerationService(db)
    return service.list_listings(
        current_admin=admin_user,
        search=search,
        status_filter=status,
        category_id=category_id,
        farmer_id=farmer_id,
        is_deleted=is_deleted,
        has_reports=has_reports,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/listings/{id}/moderate",
    response_model=AdminListingModerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Moderate produce listing",
    description="Close, soft-remove, or restore a produce listing with mandatory rationale and audit logging.",
)
def moderate_listing(
    id: uuid.UUID,
    payload: AdminListingModerateRequest,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminListingModerateResponse:
    """Apply moderation action to listing."""
    client_ip = request.client.host if request.client else None
    service = AdminCatalogModerationService(db)
    return service.moderate_listing(
        listing_id=id,
        current_admin=admin_user,
        payload=payload,
        ip_address=client_ip,
    )


# ===========================================================================
# 5. Buyer Requirement Moderation (Module 10 / Scope D)
# ===========================================================================


@router.get(
    "/requirements",
    response_model=AdminRequirementListResponse,
    status_code=status.HTTP_200_OK,
    summary="Buyer requirement moderation queue",
    description="Paginated, filterable moderation queue of buyer requirements.",
)
def list_admin_requirements(
    search: Annotated[Optional[str], Query(description="Search product name, title, buyer")] = None,
    status: Annotated[Optional[str], Query(description="Filter status: active, closed, expired, draft")] = None,
    category_id: Annotated[Optional[uuid.UUID], Query(description="Filter category ID")] = None,
    buyer_id: Annotated[Optional[uuid.UUID], Query(description="Filter buyer ID")] = None,
    is_deleted: Annotated[Optional[bool], Query(description="Filter soft-deleted requirements")] = None,
    has_reports: Annotated[Optional[bool], Query(description="Filter requirements with complaints")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    sort_by: Annotated[str, Query(description="Sort field: created_at, product_name, required_by_date, status")] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc or desc")] = "desc",
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminRequirementListResponse:
    """List buyer requirements for moderation."""
    service = AdminCatalogModerationService(db)
    return service.list_requirements(
        current_admin=admin_user,
        search=search,
        status_filter=status,
        category_id=category_id,
        buyer_id=buyer_id,
        is_deleted=is_deleted,
        has_reports=has_reports,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/requirements/{id}/moderate",
    response_model=AdminRequirementModerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Moderate buyer requirement",
    description="Close, soft-remove, or restore a buyer requirement with mandatory rationale and audit logging.",
)
def moderate_requirement(
    id: uuid.UUID,
    payload: AdminRequirementModerateRequest,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminRequirementModerateResponse:
    """Apply moderation action to buyer requirement."""
    client_ip = request.client.host if request.client else None
    service = AdminCatalogModerationService(db)
    return service.moderate_requirement(
        req_id=id,
        current_admin=admin_user,
        payload=payload,
        ip_address=client_ip,
    )
