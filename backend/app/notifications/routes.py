"""FastAPI route handlers for notification endpoints.

Implements Module 7 / Group 11 endpoints under /api/v1/notifications:
- ``GET /api/v1/notifications``: Scoped user inbox with unread-first ordering and counts
- ``POST /api/v1/notifications/{id}/read``: Marks notification as read with ownership check
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.notifications.schemas import (
    NotificationListResponse,
    NotificationMarkReadResponse,
)
from app.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List authenticated user notifications",
    description=(
        "Returns a paginated list of notifications for the authenticated user. "
        "Unread notifications appear first, followed by newest-first ordering within status groups."
    ),
    status_code=status.HTTP_200_OK,
)
def list_notifications(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    unread_only: Annotated[bool, Query(description="Filter unread notifications only")] = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    """Retrieve caller's notification inbox."""
    service = NotificationService(db)
    return service.list_user_notifications(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )


@router.post(
    "/{id}/read",
    response_model=NotificationMarkReadResponse,
    summary="Mark notification as read",
    description=(
        "Marks a specific notification as read and sets the read timestamp. "
        "Users can only mark their own notifications."
    ),
    status_code=status.HTTP_200_OK,
)
def mark_notification_as_read(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationMarkReadResponse:
    """Mark a notification owned by caller as read."""
    service = NotificationService(db)
    updated = service.mark_as_read(notification_id=id, user_id=current_user.id)
    return NotificationMarkReadResponse(
        id=updated.id,
        is_read=updated.is_read,
        read_at=updated.read_at,
    )
