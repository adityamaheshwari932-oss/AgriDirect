"""Repository layer for administrative audit log queries.

Provides read-only access to the ``admin_audit_logs`` table:
- Filtered retrieval by acting administrator, action type, and target entity
- Efficient COUNT aggregate queries
- Lookup by unique audit log identifier
- Strictly append-only: Does not expose mutation or deletion methods
"""

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.admin import AdminAuditLog


class AdminAuditLogRepository:
    """Encapsulates read queries for AdminAuditLog records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, log_id: uuid.UUID) -> Optional[AdminAuditLog]:
        """Fetch a single audit log entry by primary key."""
        stmt = select(AdminAuditLog).where(AdminAuditLog.id == log_id)
        return self.db.scalars(stmt).first()

    def list_logs(
        self,
        admin_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[AdminAuditLog]:
        """Retrieve paginated audit logs ordered newest first."""
        stmt = select(AdminAuditLog)

        if admin_user_id is not None:
            stmt = stmt.where(AdminAuditLog.admin_user_id == admin_user_id)
        if action is not None:
            stmt = stmt.where(AdminAuditLog.action == action)
        if target_entity_type is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_type == target_entity_type)
        if target_entity_id is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_id == target_entity_id)

        stmt = stmt.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_logs(
        self,
        admin_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Count total audit logs matching the given filters."""
        stmt = select(func.count(AdminAuditLog.id))

        if admin_user_id is not None:
            stmt = stmt.where(AdminAuditLog.admin_user_id == admin_user_id)
        if action is not None:
            stmt = stmt.where(AdminAuditLog.action == action)
        if target_entity_type is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_type == target_entity_type)
        if target_entity_id is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_id == target_entity_id)

        return self.db.scalar(stmt) or 0

