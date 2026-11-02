"""Pydantic v2 schemas for administrative operations, audit logs, and catalog moderation.

Implements Module 10 (Administrative User Moderation & Platform Governance) of AgriDirect:
- Administrative User Directory & Detailed Inspection
- User Account Status Moderation (active, restricted, suspended, blocked)
- Administrative Produce Listing Moderation Queue & Actions
- Administrative Buyer Requirement Moderation Queue & Actions
- Administrative Audit Trail Serialization
"""

import math
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.schemas import BuyerProfileRead, FarmerProfileRead
from app.models.listing import VALID_LISTING_STATUSES
from app.models.requirement import VALID_REQUIREMENT_STATUSES
from app.models.user import VALID_ACCOUNT_STATUSES, VALID_USER_ROLES, VALID_VERIFICATION_STATUSES

# Permitted catalog moderation actions
CATALOG_ACTION_CLOSE = "close"
CATALOG_ACTION_REMOVE = "remove"
CATALOG_ACTION_RESTORE = "restore"
VALID_CATALOG_MODERATION_ACTIONS = (
    CATALOG_ACTION_CLOSE,
    CATALOG_ACTION_REMOVE,
    CATALOG_ACTION_RESTORE,
)


# ===========================================================================
# 1. Administrative Audit Log Schemas (Module 8 / Part B)
# ===========================================================================


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


# ===========================================================================
# 2. Administrative User Directory & Inspection Schemas
# ===========================================================================


class AdminUserSummaryRead(BaseModel):
    """Safe administrative summary of a platform user without credential exposure."""

    id: uuid.UUID
    email: str
    phone_number: Optional[str] = None
    role: str
    verification_status: str
    account_status: str
    display_name: str
    organization_name: Optional[str] = None
    location_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    """Paginated user directory response."""

    items: List[AdminUserSummaryRead]
    total: int = Field(..., ge=0, description="Total matching users")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Users per page")
    total_pages: int = Field(..., ge=0, description="Total available pages")

    @classmethod
    def create(
        cls,
        items: List[AdminUserSummaryRead],
        total: int,
        page: int,
        page_size: int,
    ) -> "AdminUserListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class AdminUserActivityCounts(BaseModel):
    """Summary metrics of platform activity associated with a user."""

    listings_count: int = Field(0, description="Total produce listings created")
    requirements_count: int = Field(0, description="Total buyer requirements posted")
    completed_orders_count: int = Field(0, description="Total completed orders as buyer or farmer")
    reports_filed_count: int = Field(0, description="Complaints filed by this user")
    reports_received_count: int = Field(0, description="Complaints filed against this user")


class AdminVerificationSummary(BaseModel):
    """Summary of latest identity verification submission."""

    latest_submission_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    documents_count: int = 0


class AdminUserDetailResponse(BaseModel):
    """Comprehensive administrative inspection profile for a platform user."""

    id: uuid.UUID
    email: str
    phone_number: Optional[str] = None
    role: str
    verification_status: str
    account_status: str
    created_at: datetime
    updated_at: datetime
    farmer_profile: Optional[FarmerProfileRead] = None
    buyer_profile: Optional[BuyerProfileRead] = None
    verification_summary: Optional[AdminVerificationSummary] = None
    activity_counts: AdminUserActivityCounts
    recent_audit_logs: List[AdminAuditLogResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 3. User Account Status Moderation Schemas
# ===========================================================================


class AdminUserStatusUpdateRequest(BaseModel):
    """Payload to moderate user account status."""

    account_status: str = Field(
        ...,
        description="Target account status: active, restricted, suspended, or blocked",
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Mandatory administrative explanation for the status modification",
    )

    @field_validator("account_status")
    @classmethod
    def validate_account_status(cls, value: str) -> str:
        clean = value.strip().lower()
        if clean not in VALID_ACCOUNT_STATUSES:
            raise ValueError(
                f"Invalid account_status '{value}'. Must be one of: {', '.join(VALID_ACCOUNT_STATUSES)}"
            )
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("Administrative reason must contain at least 10 non-whitespace characters")
        if len(stripped) > 1000:
            raise ValueError("Administrative reason cannot exceed 1000 characters")
        return stripped


class AdminUserStatusUpdateResponse(BaseModel):
    """Response returned upon successful account status modification."""

    user: AdminUserSummaryRead
    previous_status: str
    new_status: str
    audit_log_id: uuid.UUID
    reason: str
    updated_at: datetime


# ===========================================================================
# 4. Produce Listing Moderation Schemas
# ===========================================================================


class AdminListingSummaryRead(BaseModel):
    """Administrative representation of a produce listing with moderation context."""

    id: uuid.UUID
    farmer_id: uuid.UUID
    farmer_email: str
    farmer_name: str
    product_name: str
    title: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    initial_quantity: Decimal
    available_quantity: Decimal
    unit: str
    price_per_unit: Decimal
    status: str
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    expires_at: datetime
    reports_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminListingListResponse(BaseModel):
    """Paginated produce listing moderation queue."""

    items: List[AdminListingSummaryRead]
    total: int = Field(..., ge=0, description="Total matching listings")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Listings per page")
    total_pages: int = Field(..., ge=0, description="Total available pages")

    @classmethod
    def create(
        cls,
        items: List[AdminListingSummaryRead],
        total: int,
        page: int,
        page_size: int,
    ) -> "AdminListingListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class AdminListingModerateRequest(BaseModel):
    """Payload to moderate a produce listing."""

    action: str = Field(
        ...,
        description="Moderation action: 'close', 'remove' (soft-delete), or 'restore'",
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Mandatory administrative justification for the moderation action",
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        clean = value.strip().lower()
        if clean not in VALID_CATALOG_MODERATION_ACTIONS:
            raise ValueError(
                f"Invalid action '{value}'. Must be one of: {', '.join(VALID_CATALOG_MODERATION_ACTIONS)}"
            )
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("Administrative reason must contain at least 10 non-whitespace characters")
        if len(stripped) > 1000:
            raise ValueError("Administrative reason cannot exceed 1000 characters")
        return stripped


class AdminListingModerateResponse(BaseModel):
    """Response returned upon successful listing moderation."""

    listing: AdminListingSummaryRead
    action: str
    previous_status: str
    new_status: str
    is_deleted: bool
    audit_log_id: uuid.UUID
    reason: str
    updated_at: datetime


# ===========================================================================
# 5. Buyer Requirement Moderation Schemas
# ===========================================================================


class AdminRequirementSummaryRead(BaseModel):
    """Administrative representation of a buyer requirement with moderation context."""

    id: uuid.UUID
    buyer_id: uuid.UUID
    buyer_email: str
    buyer_name: str
    product_name: str
    title: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    required_quantity: Decimal
    remaining_quantity: Decimal
    unit: str
    target_price_per_unit: Optional[Decimal] = None
    price_condition: str
    required_by_date: date
    status: str
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    reports_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminRequirementListResponse(BaseModel):
    """Paginated buyer requirement moderation queue."""

    items: List[AdminRequirementSummaryRead]
    total: int = Field(..., ge=0, description="Total matching requirements")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Requirements per page")
    total_pages: int = Field(..., ge=0, description="Total available pages")

    @classmethod
    def create(
        cls,
        items: List[AdminRequirementSummaryRead],
        total: int,
        page: int,
        page_size: int,
    ) -> "AdminRequirementListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class AdminRequirementModerateRequest(BaseModel):
    """Payload to moderate a buyer requirement."""

    action: str = Field(
        ...,
        description="Moderation action: 'close', 'remove' (soft-delete), or 'restore'",
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Mandatory administrative justification for the moderation action",
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        clean = value.strip().lower()
        if clean not in VALID_CATALOG_MODERATION_ACTIONS:
            raise ValueError(
                f"Invalid action '{value}'. Must be one of: {', '.join(VALID_CATALOG_MODERATION_ACTIONS)}"
            )
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("Administrative reason must contain at least 10 non-whitespace characters")
        if len(stripped) > 1000:
            raise ValueError("Administrative reason cannot exceed 1000 characters")
        return stripped


class AdminRequirementModerateResponse(BaseModel):
    """Response returned upon successful requirement moderation."""

    requirement: AdminRequirementSummaryRead
    action: str
    previous_status: str
    new_status: str
    is_deleted: bool
    audit_log_id: uuid.UUID
    reason: str
    updated_at: datetime
