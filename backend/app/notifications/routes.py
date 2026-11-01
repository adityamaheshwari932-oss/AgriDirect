"""FastAPI route handlers for notification endpoints.

Implements Module 7 / Group 11 endpoints under /api/v1/notifications:
- ``GET /api/v1/notifications``: Scoped user inbox with unread-first ordering and counts
- ``GET /api/v1/notifications/unread-count``: Fast aggregate count of unread notifications
- ``POST /api/v1/notifications/read-all``: Bulk mark all caller's notifications as read
- ``GET /api/v1/notifications/{id}``: Retrieve single notification details with ownership check
- ``POST /api/v1/notifications/{id}/read``: Marks notification as read with ownership check
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.notifications.schemas import (
    NotificationListResponse,
    NotificationMarkAllReadResponse,
    NotificationMarkReadResponse,
    NotificationRead,
    NotificationUnreadCountResponse,
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


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    summary="Get unread notification count",
    description="Returns the total number of unread notifications for the authenticated user.",
    status_code=status.HTTP_200_OK,
)
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationUnreadCountResponse:
    """Retrieve count of unread notifications for caller."""
    service = NotificationService(db)
    count = service.get_unread_count(user_id=current_user.id)
    return NotificationUnreadCountResponse(unread_count=count)


@router.post(
    "/read-all",
    response_model=NotificationMarkAllReadResponse,
    summary="Mark all notifications as read",
    description="Bulk updates all unread notifications belonging to the authenticated user to read status.",
    status_code=status.HTTP_200_OK,
)
def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationMarkAllReadResponse:
    """Mark all caller's notifications as read."""
    service = NotificationService(db)
    marked = service.mark_all_as_read(user_id=current_user.id)
    return NotificationMarkAllReadResponse(
        marked_count=marked,
        message="All notifications marked as read successfully",
    )


@router.get(
    "/{id}",
    response_model=NotificationRead,
    summary="Retrieve an individual notification",
    description="Fetches details of a specific notification owned by the authenticated user.",
    status_code=status.HTTP_200_OK,
)
def get_notification(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    """Retrieve a single notification owned by caller."""
    service = NotificationService(db)
    notification = service.get_notification(notification_id=id, user_id=current_user.id)
    return NotificationRead.model_validate(notification)


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
