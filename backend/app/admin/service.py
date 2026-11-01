"""Service layer for administrative audit log querying.

Enforces:
- Strict administrator-only authorization
- Bounded pagination limits
- Read-only historical access: No mutation or deletion paths exist
"""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.admin.repository import AdminAuditLogRepository
from app.admin.schemas import AdminAuditLogListResponse, AdminAuditLogResponse
from app.models.admin import AdminAuditLog
from app.models.user import User


class AdminAuditLogService:
    """Orchestrates administrative audit log queries and access controls."""

    def __init__(
        self,
        db: Session,
        repository: Optional[AdminAuditLogRepository] = None,
    ) -> None:
        self.db = db
        self.repo = repository or AdminAuditLogRepository(db)

    def list_logs(
        self,
        current_admin: User,
        admin_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminAuditLogListResponse:
        """Retrieve paginated audit trail entries with optional filtering.

        Args:
            current_admin: Authenticated caller (must have role 'admin').
            admin_user_id: Filter by acting administrator ID.
            action: Filter by action string.
            target_entity_type: Filter by target entity category.
            target_entity_id: Filter by specific target entity primary key.
            page: 1-indexed page number.
            page_size: Number of items per page (1 to 100).

        Returns:
            AdminAuditLogListResponse containing matching entries and pagination metadata.
        """
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.repo.list_logs(
            admin_user_id=admin_user_id,
            action=action,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            skip=skip,
            limit=page_size,
        )
        total = self.repo.count_logs(
            admin_user_id=admin_user_id,
            action=action,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
        )

        items_resp = [AdminAuditLogResponse.model_validate(item) for item in items]
        return AdminAuditLogListResponse.create(
            items=items_resp,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_log(
        self,
        log_id: uuid.UUID,
        current_admin: User,
    ) -> AdminAuditLog:
        """Fetch details of a specific audit log entry."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        log_entry = self.repo.get_by_id(log_id)
        if log_entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit log entry '{log_id}' not found",
            )
        return log_entry

