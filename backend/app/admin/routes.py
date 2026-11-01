"""FastAPI route handlers for administrative audit trail inspection.

Implements Module 8 / Part B endpoints under /api/v1/admin:
- ``GET /api/v1/admin/audit-logs``: Filterable, paginated audit trail listing
- ``GET /api/v1/admin/audit-logs/{id}``: Detailed inspection of an audit record
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.admin.schemas import AdminAuditLogListResponse, AdminAuditLogResponse
from app.admin.service import AdminAuditLogService
from app.db.session import get_db
from app.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit-logs"])


@router.get(
    "",
    response_model=AdminAuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List administrative audit logs",
    description=(
        "Returns a paginated, chronologically ordered (newest-first) audit log of privileged administrative actions. "
        "Supports filtering by acting administrator, action string, target entity type, and target entity ID. "
        "Strictly restricted to users with administrator role."
    ),
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
    "/{id}",
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

