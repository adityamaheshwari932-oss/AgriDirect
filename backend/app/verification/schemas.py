"""Pydantic v2 schemas for verification submissions, documents, and admin reviews.

Enforces strict input validation, protects against privilege escalation,
and excludes internal storage paths from API responses.
"""

import math
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

VALID_FARMER_DOCUMENT_TYPES = (
    "kisan_credit_card",
    "land_ownership",
    "government_id",
    "organic_certification",
    "other",
)

VALID_BUYER_DOCUMENT_TYPES = (
    "gstin_certificate",
    "trade_license",
    "fssai_license",
    "incorporation_certificate",
    "pan_card",
    "other",
)


class VerificationDocumentRead(BaseModel):
    """Public read model for verification documents.

    Excludes internal filesystem paths or storage URIs.
    """

    id: uuid.UUID
    submission_id: uuid.UUID
    document_type: str
    document_number: Optional[str] = None
    file_mime_type: str
    file_size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationSubmissionCreate(BaseModel):
    """Payload for submitting a new verification application."""

    model_config = ConfigDict(extra="forbid")

    submission_notes: Optional[str] = Field(
        None, max_length=2000, description="Contextual notes or information from applicant"
    )
    role: Optional[str] = Field(
        None, description="Optional applicant role; must match authenticated user's role if provided"
    )


class VerificationDocumentCreate(BaseModel):
    """Metadata payload when attaching a document to a verification submission."""

    model_config = ConfigDict(extra="forbid")

    document_type: str = Field(..., min_length=1, max_length=64, description="Canonical document type")
    document_number: Optional[str] = Field(None, max_length=64, description="Registration or document number")


class VerificationRejectRequest(BaseModel):
    """Payload for administrative rejection."""

    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Reason explaining why the verification submission was rejected",
    )


class VerificationApproveRequest(BaseModel):
    """Optional payload for administrative approval."""

    model_config = ConfigDict(extra="forbid")

    approval_notes: Optional[str] = Field(
        None, max_length=1000, description="Optional administrative notes on approval"
    )


class VerificationSubmissionRead(BaseModel):
    """Public read model for verification submission lifecycle and attached documents."""

    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    submission_notes: Optional[str] = None
    reviewed_by_admin_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    documents: List[VerificationDocumentRead] = Field(default_factory=list)

    # Contextual metadata from relationship
    user_email: Optional[str] = None
    user_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_user_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        user = getattr(data, "user", None)
        if user is not None:
            try:
                setattr(data, "user_email", getattr(user, "email", None))
                setattr(data, "user_role", getattr(user, "role", None))
            except Exception:
                pass
        return data


class VerificationListResponse(BaseModel):
    """Paginated response model for verification queues."""

    items: List[VerificationSubmissionRead]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: List[VerificationSubmissionRead],
        total: int,
        page: int,
        page_size: int,
    ) -> "VerificationListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
