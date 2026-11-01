"""FastAPI route handlers for user reporting and platform safety moderation.

Implements Module 8 / Part A endpoints under /api/v1:
- User endpoints:
  - ``POST /api/v1/reports``: File a safety, fraud, or transaction violation report
  - ``GET /api/v1/reports/me``: List reports filed by the authenticated user
  - ``GET /api/v1/reports/{id}``: View an individual report (reporter or admin only)
- Administrator moderation endpoints:
  - ``GET /api/v1/admin/reports``: Filterable, paginated moderation queue
  - ``GET /api/v1/admin/reports/{id}``: Detailed inspection of a report
  - ``POST /api/v1/admin/reports/{id}/moderate``: Update moderation status with audit trail
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.reports.schemas import (
    ReportCreate,
    ReportListResponse,
    ReportModerateRequest,
    ReportResponse,
)
from app.reports.service import ReportService

router = APIRouter(tags=["reports"])


# ---------------------------------------------------------------------------
# User Report Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a safety or violation report",
    description=(
        "Submits a complaint regarding conduct, produce quality, fraud, or marketplace violations. "
        "The report is initially in 'open' status awaiting administrative moderation."
    ),
)
def create_report(
    report_in: ReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Submit a safety report against a user or produce listing."""
    service = ReportService(db)
    report = service.create_report(current_user=current_user, report_in=report_in)
    return ReportResponse.model_validate(report)


@router.get(
    "/reports/me",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reports filed by caller",
    description="Returns a paginated list of reports submitted by the authenticated user, newest first.",
)
def list_my_reports(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """List reports filed by the authenticated caller."""
    service = ReportService(db)
    return service.list_my_reports(current_user=current_user, page=page, page_size=page_size)


@router.get(
    "/reports/{id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve report details",
    description=(
        "Fetches report details. Accessible only to the original reporter and platform administrators. "
        "Reported users and third parties receive 404 to protect reporter confidentiality."
    ),
)
def get_report(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Retrieve details of a report accessible to caller."""
    service = ReportService(db)
    report = service.get_report(report_id=id, current_user=current_user)
    return ReportResponse.model_validate(report)


# ---------------------------------------------------------------------------
# Administrator Moderation Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/admin/reports",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reports for administrative moderation",
    description=(
        "Returns a paginated moderation queue of user reports. "
        "Supports filtering by status ('open', 'under_review', 'action_taken', 'dismissed') "
        "and category."
    ),
)
def admin_list_reports(
    status_filter: Annotated[Optional[str], Query(alias="status", description="Filter by report status")] = None,
    category_filter: Annotated[Optional[str], Query(alias="category", description="Filter by category")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Moderation queue listing for administrators."""
    service = ReportService(db)
    return service.admin_list_reports(
        status_filter=status_filter,
        category_filter=category_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/admin/reports/{id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get report detail for administrative review",
    description="Allows administrators to inspect complete report narrative, targets, and notes.",
)
def admin_get_report_detail(
    id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Inspect full report detail as an administrator."""
    service = ReportService(db)
    report = service.get_report(report_id=id, current_user=admin_user)
    return ReportResponse.model_validate(report)


@router.post(
    "/admin/reports/{id}/moderate",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Moderate user report and record resolution",
    description=(
        "Updates report status to 'under_review', 'action_taken', or 'dismissed'. "
        "Records administrative findings, inserts an immutable AdminAuditLog entry, "
        "and notifies the reporting user."
    ),
)
def admin_moderate_report(
    id: uuid.UUID,
    payload: ReportModerateRequest,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Execute administrative moderation on a report."""
    ip_address = request.client.host if request.client else None
    service = ReportService(db)
    updated = service.admin_moderate_report(
        report_id=id,
        current_admin=admin_user,
        moderate_in=payload,
        ip_address=ip_address,
    )
    return ReportResponse.model_validate(updated)

