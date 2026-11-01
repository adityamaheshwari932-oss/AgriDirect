"""Pydantic v2 schemas for off-platform payment tracking and dispute moderation.

Adheres to Module 6 specifications and strict Decimal monetary arithmetic.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.payment import (
    PAYMENT_COMPLAINT_STATUS_DISMISSED,
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    VALID_PAYMENT_COMPLAINT_STATUSES,
    VALID_PAYMENT_METHODS,
    VALID_PAYMENT_STATUSES,
)


# ===========================================================================
# Request Schemas
# ===========================================================================


class PaymentRecordCreate(BaseModel):
    """Payload to record an off-platform payment claim against an order."""

    amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        description="Payment amount in INR (strictly positive, up to 2 decimal places).",
    )
    payment_method: str = Field(
        ...,
        description="Method used off-platform: 'upi', 'bank_transfer', 'cash', 'other'.",
    )
    reference_number: Optional[str] = Field(
        None,
        max_length=128,
        description="Optional external transaction reference (e.g. UPI Ref ID, Bank UTR).",
    )
    payment_date: date = Field(
        ...,
        description="Date when the payment was executed off-platform.",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Enforce maximum 2 decimal places without lossy float conversion."""
        if v <= Decimal("0.00"):
            raise ValueError("Amount must be strictly greater than zero")
        # Check decimal exponent (no more than 2 decimal places)
        exponent = v.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        """Validate payment method against canonical enum values."""
        normalized = v.strip().lower()
        if normalized not in VALID_PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method '{v}'. Must be one of: {', '.join(VALID_PAYMENT_METHODS)}"
            )
        return normalized

    @field_validator("reference_number")
    @classmethod
    def clean_reference_number(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from reference number if present."""
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class PaymentComplaintCreate(BaseModel):
    """Payload to file a formal dispute against a payment record."""

    complaint_reason: Optional[str] = Field(
        None,
        description="Detailed factual reason for the payment dispute.",
    )
    reason: Optional[str] = Field(
        None,
        description="Alias for complaint_reason.",
    )

    @model_validator(mode="before")
    @classmethod
    def harmonize_reason(cls, data: Any) -> Any:
        if isinstance(data, dict):
            r = data.get("reason") or data.get("complaint_reason")
            if r:
                data["complaint_reason"] = r
                data["reason"] = r
        return data

    @field_validator("complaint_reason")
    @classmethod
    def validate_complaint_reason(cls, v: Optional[str]) -> str:
        if not v:
            raise ValueError("Complaint reason must contain at least 5 non-whitespace characters")
        cleaned = v.strip()
        if len(cleaned) < 5:
            raise ValueError("Complaint reason must contain at least 5 non-whitespace characters")
        return cleaned


class AdminComplaintResolveRequest(BaseModel):
    """Payload for administrator to update dispute status and resolution notes.

    Administrators record findings and resolve or dismiss complaints.
    Administrators NEVER acknowledge payments; payment receipt acknowledgement
    remains strictly exclusive to the designated selling farmer.
    """

    status: Optional[str] = Field(
        None,
        description="Target status: 'under_review', 'resolved', or 'dismissed'.",
    )
    resolution_action: Optional[str] = Field(
        None,
        description="Action alias: 'under_review', 'resolve', 'confirm_evidence', 'dismiss'.",
    )
    admin_resolution_notes: Optional[str] = Field(
        None,
        max_length=4000,
        description="Administrative findings, mediation remarks, or action summary.",
    )
    resolution_notes: Optional[str] = Field(
        None,
        max_length=4000,
        description="Alias for admin_resolution_notes.",
    )

    def get_target_status(self) -> str:
        """Resolve and validate target complaint status."""
        action = (self.resolution_action or self.status or "").strip().lower()
        if action in ("confirm_payment", "confirm_evidence", "resolve", "resolved"):
            return PAYMENT_COMPLAINT_STATUS_RESOLVED
        elif action in ("dismiss", "dismissed", "reject_payment"):
            return PAYMENT_COMPLAINT_STATUS_DISMISSED
        elif action in ("under_review",):
            return PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW
        elif action in VALID_PAYMENT_COMPLAINT_STATUSES:
            return action
        raise ValueError(
            f"Invalid dispute moderation status '{action}'. Allowed: {', '.join(VALID_PAYMENT_COMPLAINT_STATUSES)}"
        )

    def get_notes(self) -> Optional[str]:
        """Resolve resolution notes from either field."""
        notes = self.admin_resolution_notes or self.resolution_notes
        return notes.strip() if notes else None


# ===========================================================================
# Response Schemas
# ===========================================================================


class PaymentRecordResponse(BaseModel):
    """Public representation of an off-platform payment claim record."""

    id: uuid.UUID
    order_id: uuid.UUID
    recorded_by_user_id: uuid.UUID
    amount: Decimal
    payment_method: str
    reference_number: Optional[str] = None
    has_proof: bool = False
    proof_file_path: Optional[str] = None
    status: str
    payment_date: date
    acknowledged_at: Optional[datetime] = None
    original_acknowledged_at: Optional[datetime] = None
    has_historical_acknowledgement: bool = False
    acknowledged_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, record: object) -> "PaymentRecordResponse":
        """Construct response ensuring sensitive internal filesystem paths are never leaked."""
        proof_uri = getattr(record, "proof_file_uri", None)
        orig_ack = getattr(record, "original_acknowledged_at", None)
        ack_by = None
        if getattr(record, "acknowledged_at", None) is not None:
            order_obj = getattr(record, "order", None)
            if order_obj:
                ack_by = str(order_obj.farmer_id)
        return cls(
            id=getattr(record, "id"),
            order_id=getattr(record, "order_id"),
            recorded_by_user_id=getattr(record, "recorded_by_user_id"),
            amount=getattr(record, "amount"),
            payment_method=getattr(record, "payment_method"),
            reference_number=getattr(record, "reference_number"),
            has_proof=bool(proof_uri),
            proof_file_path=proof_uri,
            status=getattr(record, "status"),
            payment_date=getattr(record, "payment_date"),
            acknowledged_at=getattr(record, "acknowledged_at"),
            original_acknowledged_at=orig_ack,
            has_historical_acknowledgement=bool(orig_ack),
            acknowledged_by=ack_by,
            created_at=getattr(record, "created_at"),
            updated_at=getattr(record, "updated_at"),
        )


class PaymentRecordListResponse(BaseModel):
    """Paginated list of payment records."""

    items: List[PaymentRecordResponse]
    total: int
    limit: int
    offset: int


class PaymentSummaryResponse(BaseModel):
    """Aggregate financial reconciliation summary for an order's payments.

    Distinguishes:
    - total_recorded: Total sum of all recorded claims (acknowledged + unacknowledged + disputed).
    - total_acknowledged: Total funds confirmed received by the seller off-platform.
    - total_disputed: Total funds currently contested under active dispute.
    - unacknowledged_amount: Total funds recorded by buyer awaiting seller acknowledgement.
    - remaining_acknowledged_balance: Unsettled order balance: max(0.00, order_total - total_acknowledged).
    - remaining_payable_amount / max_available_for_new_payment: Allowable headroom for new payment claims.
    - settlement_status: Categorical settlement state:
        * 'fully_settled': total_acknowledged >= order_total
        * 'partially_settled': total_acknowledged > 0 and < order_total
        * 'payment_pending_acknowledgement': total_acknowledged == 0 and unacknowledged_amount > 0
        * 'disputed': total_acknowledged == 0 and unacknowledged_amount == 0 and total_disputed > 0
        * 'unpaid': total_recorded == 0 (strictly zero payment claims recorded)
    """

    order_id: uuid.UUID = Field(..., description="ID of the order being summarized.")
    order_total: Decimal = Field(..., description="Total monetary obligation agreed in the order.")
    total_recorded: Decimal = Field(..., description="Sum of all payment claims recorded against the order.")
    total_acknowledged: Decimal = Field(..., description="Sum of payments confirmed received by the farmer.")
    total_disputed: Decimal = Field(..., description="Sum of contested payments currently under dispute.")
    unacknowledged_amount: Decimal = Field(..., description="Sum of payments awaiting seller acknowledgement.")
    remaining_acknowledged_balance: Decimal = Field(..., description="Remaining unsettled balance.")
    remaining_payable_amount: Decimal = Field(
        Decimal("0.00"),
        description="Allowable remaining headroom before reaching order total.",
    )
    max_available_for_new_payment: Decimal = Field(
        Decimal("0.00"),
        description="Maximum amount accepted for any new payment submission.",
    )
    settlement_status: str = Field(
        ...,
        description="Settlement status: 'unpaid', 'payment_pending_acknowledgement', 'disputed', 'partially_settled', 'fully_settled'.",
    )
    records_count: int = Field(..., description="Count of payment records associated with this order.")


class PaymentComplaintResponse(BaseModel):
    """Public representation of a payment dispute complaint."""

    id: uuid.UUID
    payment_record_id: uuid.UUID
    payment_id: Optional[uuid.UUID] = None
    complainant_user_id: uuid.UUID
    complainant_id: Optional[uuid.UUID] = None
    complaint_reason: str
    reason: Optional[str] = None
    has_evidence: bool = False
    evidence_file_path: Optional[str] = None
    status: str
    admin_resolution_notes: Optional[str] = None
    resolved_by_admin_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, complaint: object) -> "PaymentComplaintResponse":
        """Construct response ensuring sensitive internal paths are never leaked."""
        pid = getattr(complaint, "payment_record_id")
        cid = getattr(complaint, "complainant_user_id")
        reason = getattr(complaint, "complaint_reason")
        ev_uri = getattr(complaint, "evidence_file_uri", None)
        return cls(
            id=getattr(complaint, "id"),
            payment_record_id=pid,
            payment_id=pid,
            complainant_user_id=cid,
            complainant_id=cid,
            complaint_reason=reason,
            reason=reason,
            has_evidence=bool(ev_uri),
            evidence_file_path=ev_uri,
            status=getattr(complaint, "status"),
            admin_resolution_notes=getattr(complaint, "admin_resolution_notes"),
            resolved_by_admin_id=getattr(complaint, "resolved_by_admin_id"),
            created_at=getattr(complaint, "created_at"),
            updated_at=getattr(complaint, "updated_at"),
        )


class PaymentComplaintDetailResponse(BaseModel):
    """Detailed complaint view for administrative moderation."""

    complaint: PaymentComplaintResponse
    payment: PaymentRecordResponse
    order_id: uuid.UUID
    order_number: str
    buyer_id: uuid.UUID
    farmer_id: uuid.UUID
    order: Optional[dict[str, Any]] = None


class PaymentComplaintListResponse(BaseModel):
    """Paginated list of payment complaints for administrative queues."""

    items: List[PaymentComplaintResponse]
    total: int
    limit: int
    offset: int

