"""Pydantic v2 schemas for administrative audit logs.

Implements Module 8 (Governance & Audit Trail / Part B — Administrative Audit Logs):
- ``AdminAuditLogResponse``: Read-only serialization of an audit log entry
- ``AdminAuditLogListResponse``: Paginated collection of audit log entries
"""

import math
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AdminAuditLogResponse(BaseModel):
    """Immutable public view of an administrative audit record."""

    id: uuid.UUID
    admin_user_id: uuid.UUID
    action: str
    target_entity_type: str
    target_entity_id: uuid.UUID
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminAuditLogListResponse(BaseModel):
    """Paginated collection of administrative audit logs."""

    items: List[AdminAuditLogResponse]
    total: int = Field(..., ge=0, description="Total matching audit log entries")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages available")

    @classmethod
    def create(
        cls,
        items: List[AdminAuditLogResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "AdminAuditLogListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

