"""Service layer for requirement fulfillment approvals.

Implements ADR-003: Requirement Fulfillment Approval Workflow.
- Monotonic 5-tier global lock hierarchy (Requirement Tier 4 -> Approval Tier 5).
- Bounded retries on transient PostgreSQL errors (40P01, 40001).
- Strict buyer ownership authorization with anti-enumeration 404 responses.
- Partial fulfillment deductions without changing commercial order quantity.
- Explicit requirement closure enforcement (no automatic closure on zero remaining).
- Exhaustive terminal-state immutability and void audit tracking.
"""

import logging
import random
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.notification import NOTIFICATION_REF_ORDER, Notification
from app.models.requirement import (
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    BuyerRequirement,
)
from app.models.requirement_approval import (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_NOT_APPLIED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_VOIDED,
    TERMINAL_APPROVAL_STATUSES,
    RequirementFulfillmentApproval,
)
from app.models.user import User
from app.requirements.repository import RequirementRepository
from app.requirements.schemas import (
    ApproveFulfillmentRequest,
    FulfillmentApprovalListResponse,
    FulfillmentApprovalResponse,
    RejectFulfillmentRequest,
)

logger = logging.getLogger(__name__)

# Maximum retry attempts for transient PostgreSQL concurrency errors
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.05

TRANSIENT_SQLSTATE_CODES = {"40P01", "40001"}


class FulfillmentApprovalService:
    """Manages fulfillment approvals, buyer verification, atomic deductions, and void lifecycle."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = RequirementRepository(db)

    def _require_verified_buyer(self, user: User) -> None:
        """Validate caller is an active verified commercial buyer."""
        if getattr(user, "is_deleted", False) or user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )
        if user.role != "buyer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only commercial buyers can access requirement fulfillment approvals",
            )
        if user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account verification is required to manage requirement fulfillment approvals",
            )

    def _is_transient_error(self, err: Exception) -> bool:
        """Check if an exception is a recognized transient PostgreSQL concurrency error."""
        if isinstance(err, DBAPIError) and err.orig is not None:
            sqlstate = getattr(err.orig, "pgcode", None) or getattr(err.orig, "sqlstate", None)
            if sqlstate in TRANSIENT_SQLSTATE_CODES:
                return True
        return False

    def _to_response(self, approval: RequirementFulfillmentApproval) -> FulfillmentApprovalResponse:
        """Enrich and map ORM approval model to response schema."""
        req = approval.requirement
        order = approval.order
        order_item = approval.order_item

        return FulfillmentApprovalResponse(
            id=approval.id,
            requirement_id=approval.requirement_id,
            order_id=approval.order_id,
            order_item_id=approval.order_item_id,
            proposed_quantity=approval.proposed_quantity,
            approved_quantity=approval.approved_quantity,
            status=approval.status,
            reviewed_by_user_id=approval.reviewed_by_user_id,
            reviewed_at=approval.reviewed_at,
            rejection_reason=approval.rejection_reason,
            voided_by_user_id=approval.voided_by_user_id,
            voided_at=approval.voided_at,
            void_reason=approval.void_reason,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
            requirement_title=req.title if req else None,
            product_name=req.product_name if req else (order_item.product_name if order_item else None),
            unit=req.unit if req else (order_item.unit if order_item else None),
            requirement_remaining_quantity=req.remaining_quantity if req else None,
            requirement_status=req.status if req else None,
            order_number=order.order_number if order else None,
        )

    # -----------------------------------------------------------------------
    # Buyer Query Endpoints
    # -----------------------------------------------------------------------

    def list_approvals(
        self,
        current_user: User,
        status_filter: Optional[str] = None,
        requirement_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FulfillmentApprovalListResponse:
        """List fulfillment approvals for requirements owned by the authenticated buyer."""
        self._require_verified_buyer(current_user)

        items, total = self.repository.list_approvals_for_buyer(
            buyer_id=current_user.id,
            status_filter=status_filter,
            requirement_id=requirement_id,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        response_items = [self._to_response(item) for item in items]

        return FulfillmentApprovalListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_approval(
        self,
        current_user: User,
        approval_id: uuid.UUID,
    ) -> FulfillmentApprovalResponse:
        """Retrieve a single fulfillment approval record with anti-enumeration security."""
        self._require_verified_buyer(current_user)

        approval = self.repository.get_approval_by_id(approval_id)
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment approval '{approval_id}' not found",
            )

        # Anti-enumeration check: return 404 if caller is not the requirement owner
        if not approval.requirement or approval.requirement.buyer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment approval '{approval_id}' not found",
            )

        return self._to_response(approval)

    # -----------------------------------------------------------------------
    # Decision Endpoints (Approve / Reject)
    # -----------------------------------------------------------------------

    def approve_fulfillment(
        self,
        current_user: User,
        approval_id: uuid.UUID,
        payload: ApproveFulfillmentRequest,
    ) -> FulfillmentApprovalResponse:
        """Approve fulfillment deduction against a buyer requirement.

        Acquires locks strictly following the Global Lock Hierarchy:
        Tier 4: BuyerRequirement -> Tier 5: RequirementFulfillmentApproval.
        """
        self._require_verified_buyer(current_user)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 1. Peek at requirement_id to establish the canonical lock order
                peek = self.repository.get_approval_by_id(approval_id)
                if not peek:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )
                if not peek.requirement or peek.requirement.buyer_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )

                req_id = peek.requirement_id

                # 2. Lock Tier 4: BuyerRequirement FOR UPDATE
                req = self.repository.get_requirement_by_id(req_id, for_update=True)
                if not req or req.buyer_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )

                # 3. Lock Tier 5: RequirementFulfillmentApproval FOR UPDATE
                approval = self.repository.get_approval_by_id(approval_id, for_update=True)
                if not approval or not approval.requirement or approval.requirement.buyer_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )

                # 4. State & Status Validations
                if approval.status != APPROVAL_STATUS_PENDING:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Approval request has already been reviewed with status: '{approval.status}'",
                    )

                if req.status not in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot approve fulfillment for requirement in '{req.status}' status",
                    )

                # 5. Quantity Validations
                effective_qty = (
                    payload.approved_quantity
                    if payload.approved_quantity is not None
                    else approval.proposed_quantity
                )

                if effective_qty <= Decimal("0"):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Approved quantity must be positive",
                    )

                if effective_qty > approval.proposed_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Approved quantity ({effective_qty}) cannot exceed proposed quantity "
                            f"({approval.proposed_quantity})"
                        ),
                    )

                if effective_qty > req.remaining_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Approved quantity ({effective_qty}) exceeds current remaining requirement quantity "
                            f"({req.remaining_quantity}). No quantity clamped."
                        ),
                    )

                # 6. Apply Atomic State Changes
                req.remaining_quantity -= effective_qty
                if payload.close_requirement is True:
                    req.status = REQUIREMENT_STATUS_CLOSED
                elif req.status == REQUIREMENT_STATUS_ACTIVE:
                    req.status = REQUIREMENT_STATUS_PARTIALLY_FULFILLED

                now_utc = datetime.now(timezone.utc)
                approval.status = APPROVAL_STATUS_APPROVED
                approval.approved_quantity = effective_qty
                approval.reviewed_by_user_id = current_user.id
                approval.reviewed_at = now_utc
                approval.updated_at = now_utc

                # 7. Add atomic in-app notification for the farmer
                farmer_id = approval.order.farmer_id if approval.order else None
                if farmer_id:
                    self.db.add(
                        Notification(
                            user_id=farmer_id,
                            event_type="requirement_fulfillment_approved",
                            title="Fulfillment Approved by Buyer",
                            body=(
                                f"Buyer approved {effective_qty} {req.unit} fulfillment for "
                                f"Order {approval.order.order_number if approval.order else ''} "
                                f"against requirement '{req.title}'."
                            ),
                            reference_type=NOTIFICATION_REF_ORDER,
                            reference_id=approval.order_id,
                        )
                    )

                # Atomic commit
                self.db.commit()
                self.db.refresh(approval)
                return self._to_response(approval)

            except HTTPException:
                raise
            except Exception as err:
                self.db.rollback()
                if self._is_transient_error(err) and attempt < MAX_RETRIES:
                    sleep_time = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1)) + random.uniform(0.01, 0.05)
                    logger.warning("Transient concurrency conflict on approval %s, retrying in %.3fs (attempt %d/%d)", approval_id, sleep_time, attempt, MAX_RETRIES)
                    time.sleep(sleep_time)
                    continue
                logger.error("Error approving fulfillment %s: %s", approval_id, err, exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database temporarily busy. Please retry your request.",
                ) from err

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transaction concurrency retries exhausted",
        )

    def reject_fulfillment(
        self,
        current_user: User,
        approval_id: uuid.UUID,
        payload: RejectFulfillmentRequest,
    ) -> FulfillmentApprovalResponse:
        """Reject fulfillment deduction against a buyer requirement.

        Preserves requirement remaining demand per FR-REQ-08.
        Acquires locks strictly following the Global Lock Hierarchy: Tier 4 -> Tier 5.
        """
        self._require_verified_buyer(current_user)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 1. Peek at requirement_id to establish the canonical lock order
                peek = self.repository.get_approval_by_id(approval_id)
                if not peek:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )
                if not peek.requirement or peek.requirement.buyer_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )

                req_id = peek.requirement_id

                # 2. Lock Tier 4: BuyerRequirement FOR UPDATE
                req = self.repository.get_requirement_by_id(req_id, for_update=True)
                if not req or req.buyer_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )

                # 3. Lock Tier 5: RequirementFulfillmentApproval FOR UPDATE
                approval = self.repository.get_approval_by_id(approval_id, for_update=True)
                if not approval or not approval.requirement or approval.requirement.buyer_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Fulfillment approval '{approval_id}' not found",
                    )

                # 4. Status Check
                if approval.status != APPROVAL_STATUS_PENDING:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Approval request has already been reviewed with status: '{approval.status}'",
                    )

                # 5. Apply Rejection (Requirement quantity and status remain completely untouched)
                now_utc = datetime.now(timezone.utc)
                approval.status = APPROVAL_STATUS_REJECTED
                approval.approved_quantity = None
                approval.rejection_reason = payload.reason
                approval.reviewed_by_user_id = current_user.id
                approval.reviewed_at = now_utc
                approval.updated_at = now_utc

                # 6. In-app notification for the farmer
                farmer_id = approval.order.farmer_id if approval.order else None
                if farmer_id:
                    reason_text = f" Reason: {payload.reason}" if payload.reason else ""
                    self.db.add(
                        Notification(
                            user_id=farmer_id,
                            event_type="requirement_fulfillment_rejected",
                            title="Fulfillment Allocation Rejected",
                            body=(
                                f"Buyer rejected applying Order {approval.order.order_number if approval.order else ''} "
                                f"toward requirement '{req.title}'.{reason_text}"
                            ),
                            reference_type=NOTIFICATION_REF_ORDER,
                            reference_id=approval.order_id,
                        )
                    )

                self.db.commit()
                self.db.refresh(approval)
                return self._to_response(approval)

            except HTTPException:
                raise
            except Exception as err:
                self.db.rollback()
                if self._is_transient_error(err) and attempt < MAX_RETRIES:
                    sleep_time = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1)) + random.uniform(0.01, 0.05)
                    logger.warning("Transient concurrency conflict on rejection %s, retrying in %.3fs", approval_id, sleep_time)
                    time.sleep(sleep_time)
                    continue
                logger.error("Error rejecting fulfillment %s: %s", approval_id, err, exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database temporarily busy. Please retry your request.",
                ) from err

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transaction concurrency retries exhausted",
        )

    # -----------------------------------------------------------------------
    # Order Cancellation & Voiding Lifecycle Hook
    # -----------------------------------------------------------------------

    def handle_order_cancelled(
        self,
        order_id: uuid.UUID,
        cancelling_user_id: Optional[uuid.UUID] = None,
        reason: str = "Order cancelled",
    ) -> List[RequirementFulfillmentApproval]:
        """Lifecycle hook when an order is cancelled.

        - If approval is 'pending': transitions to 'voided' with audit metadata.
        - If approval is 'approved': status remains terminal 'approved' and requirement quantity remains unchanged (interim rule).
        - If approval is 'rejected' or 'not_applied': remains unchanged.
        """
        approvals = (
            self.db.query(RequirementFulfillmentApproval)
            .filter(RequirementFulfillmentApproval.order_id == order_id)
            .order_by(RequirementFulfillmentApproval.id.asc())
            .all()
        )

        now_utc = datetime.now(timezone.utc)
        modified: List[RequirementFulfillmentApproval] = []

        for approval in approvals:
            if approval.status == APPROVAL_STATUS_PENDING:
                approval.status = APPROVAL_STATUS_VOIDED
                approval.voided_by_user_id = cancelling_user_id
                approval.voided_at = now_utc
                approval.void_reason = reason
                approval.updated_at = now_utc
                modified.append(approval)

        if modified:
            self.db.flush()

        return modified
