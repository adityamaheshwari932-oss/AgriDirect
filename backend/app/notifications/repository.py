"""Repository layer for notification persistence and query operations.

Provides scoped database access to the ``notifications`` table:
- Scoped listing with unread-first and newest-first ordering
- Efficient count queries using PostgreSQL aggregate functions
- Single notification retrieval strictly scoped to the authenticated user
- Read status mutation
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.notifications.schemas import NotificationCreate


class NotificationRepository:
    """Encapsulates all database interactions for the Notification model."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with an active SQLAlchemy session.

        Args:
            db: The current database session.
        """
        self.db = db

    def create(self, notification_in: NotificationCreate) -> Notification:
        """Insert a new notification record.

        Args:
            notification_in: Validated notification creation schema.

        Returns:
            The created Notification model instance (not yet committed).
        """
        notification = Notification(
            user_id=notification_in.user_id,
            event_type=notification_in.event_type,
            title=notification_in.title,
            body=notification_in.body,
            reference_type=notification_in.reference_type,
            reference_id=notification_in.reference_id,
            is_read=False,
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_by_id_and_user(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Notification]:
        """Fetch a single notification by ID strictly scoped to a specific user.

        Args:
            notification_id: Primary key of the notification.
            user_id: Owner user ID.

        Returns:
            The Notification instance if found and owned by user, else None.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def get_by_id(self, notification_id: uuid.UUID) -> Optional[Notification]:
        """Fetch a single notification by ID without user scoping (e.g. for permission checks).

        Args:
            notification_id: Primary key of the notification.

        Returns:
            The Notification instance if found, else None.
        """
        stmt = select(Notification).where(Notification.id == notification_id)
        return self.db.scalars(stmt).first()

    def list_for_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False,
    ) -> List[Notification]:
        """Retrieve paginated notifications for a user.

        Ordering:
            1. Unread notifications first (is_read ASC)
            2. Newest first within each read-status group (created_at DESC)

        Args:
            user_id: Target user ID.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.
            unread_only: If True, filters only unread notifications.

        Returns:
            List of matching Notification instances.
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        # Unread first, then newest first
        stmt = (
            stmt.order_by(
                Notification.is_read.asc(),
                Notification.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def count_for_user(self, user_id: uuid.UUID, unread_only: bool = False) -> int:
        """Count total notifications belonging to a user using an aggregate COUNT.

        Args:
            user_id: Target user ID.
            unread_only: If True, counts only unread notifications.

        Returns:
            Total matching records count.
        """
        stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        return self.db.scalar(stmt) or 0

    def count_unread_for_user(self, user_id: uuid.UUID) -> int:
        """Count only unread notifications for a user.

        Args:
            user_id: Target user ID.

        Returns:
            Unread notification count.
        """
        return self.count_for_user(user_id=user_id, unread_only=True)

    def mark_as_read(
        self, notification: Notification, read_time: Optional[datetime] = None
    ) -> Notification:
        """Update a notification to read status with timestamp.

        Args:
            notification: The Notification instance to update.
            read_time: Timestamp to record (defaults to current UTC time).

        Returns:
            The mutated Notification instance (not yet committed).
        """
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = read_time or datetime.now(timezone.utc)
        elif notification.read_at is None:
            notification.read_at = read_time or datetime.now(timezone.utc)
        self.db.flush()
        return notification

    def mark_all_as_read(
        self, user_id: uuid.UUID, read_time: Optional[datetime] = None
    ) -> int:
        """Mark all unread notifications for a user as read.

        Args:
            user_id: Target user ID.
            read_time: Timestamp to set (defaults to current UTC time).

        Returns:
            Number of notifications marked as read.
        """
        now = read_time or datetime.now(timezone.utc)
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        unread_items = list(self.db.scalars(stmt).all())
        for notif in unread_items:
            notif.is_read = True
            notif.read_at = now
        self.db.flush()
        return len(unread_items)

