"""Pydantic v2 schemas for user reports and platform safety moderation.

Implements Module 8 (Governance & Audit Trail / Part A — User Reports):
- ``ReportCreate``: User complaint filing payload
- ``ReportResponse``: Serialized representation of a user report
- ``ReportListResponse``: Paginated collection of reports
- ``ReportModerateRequest``: Administrator moderation and resolution action
"""

import math
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import VALID_REPORT_CATEGORIES, VALID_REPORT_STATUSES


class ReportCreate(BaseModel):
    """Payload for submitting a platform safety or compliance report."""

    reported_user_id: Optional[uuid.UUID] = Field(
        None,
        description="User ID of the counterparty being reported, if applicable",
    )
    listing_id: Optional[uuid.UUID] = Field(
        None,
        description="Listing ID involved in the complaint, if applicable",
    )
    category: str = Field(
        ...,
        description=(
            f"Canonical complaint category. Allowed values: {list(VALID_REPORT_CATEGORIES)}"
        ),
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Detailed narrative explaining the complaint, violation, or misconduct",
    )


class ReportResponse(BaseModel):
    """Public serialized view of a user report."""

    id: uuid.UUID
    reporter_id: uuid.UUID
    reported_user_id: Optional[uuid.UUID] = None
    listing_id: Optional[uuid.UUID] = None
    category: str
    description: str
    status: str
    admin_notes: Optional[str] = None
    reviewed_by_admin_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    """Paginated collection of user reports."""

    items: List[ReportResponse]
    total: int = Field(..., ge=0, description="Total matching reports")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages available")

    @classmethod
    def create(
        cls,
        items: List[ReportResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "ReportListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ReportModerateRequest(BaseModel):
    """Payload for administrative investigation and status resolution."""

    status: str = Field(
        ...,
        description="Target status: 'under_review', 'action_taken', 'dismissed'",
    )
    admin_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Administrative findings, investigation notes, or resolution justification",
    )

