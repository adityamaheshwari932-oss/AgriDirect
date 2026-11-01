"""Business service layer for Module 6 — Payment Tracking & Dispute Moderation.

Enforces:
- Strict non-custodial record-keeping rules (BR-15, FR-PAY-01 to FR-PAY-10).
- Canonical 5-tier database lock hierarchy (ADR-008, ADR-010).
- Overpayment prevention and financial Decimal calculations.
- Anti-enumeration authorization (404 for unauthorized entities).
- Secure attachment validation and atomic rollback cleanup.
- Administrative dispute facilitation boundaries.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.admin import AdminAuditLog
from app.models.notification import Notification
from app.models.order import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERY_ARRANGED,
    ORDER_STATUS_DISPUTED,
    Order,
)
from app.models.payment import (
    PAYMENT_COMPLAINT_STATUS_DISMISSED,
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    VALID_PAYMENT_COMPLAINT_STATUSES,
    PaymentComplaint,
    PaymentRecord,
)
from app.models.user import User
from app.payments.repository import PaymentRepository
from app.payments.schemas import PaymentRecordCreate
from app.payments.storage import PaymentStorageService


class PaymentService:
    """Service implementing all business workflows and security invariants for payments."""

    def __init__(self, db: Session, storage: Optional[PaymentStorageService] = None) -> None:
        self.db = db
        self.repo = PaymentRepository(db)
        self.storage = storage or PaymentStorageService()

    # -------------------------------------------------------------------------
    # Helper Authorization Guards
    # -------------------------------------------------------------------------

    def _verify_active_and_verified(self, user: User) -> None:
        """Reject unverified or inactive users."""
        if getattr(user, "account_status", "active") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended",
            )
        is_verified = (
            getattr(user, "verification_status", "") == "verified"
            or getattr(user, "is_verified", False) is True
            or getattr(user, "role", "") == "admin"
        )
        if not is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified users may perform payment operations",
            )

    # -------------------------------------------------------------------------
    # 1. Payment Recording (Buyer)
    # -------------------------------------------------------------------------

    def record_payment(
        self,
        order_id: uuid.UUID,
        current_user: User,
        payload: PaymentRecordCreate,
        proof_file: Optional[UploadFile] = None,
    ) -> PaymentRecord:
        """Record an off-platform payment claim made against a confirmed order."""
        self._verify_active_and_verified(current_user)

        # 1. Lock Order (Tier 2 in the canonical 7-tier global lock hierarchy)
        order = (
            self.db.query(Order)
            .filter(Order.id == order_id)
            .with_for_update(of=Order)
            .populate_existing()
            .first()
        )

        # Anti-enumeration: if order does not exist or caller is unrelated
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        if current_user.id != order.buyer_id and current_user.id != order.farmer_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        # Role enforcement: only buyer can record buyer payment
        if current_user.id != order.buyer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the buyer associated with this order may record payments",
            )

        # Order eligibility check
        if order.status in (ORDER_STATUS_CANCELLED, ORDER_STATUS_DISPUTED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record payment for an order in '{order.status}' status",
            )

        # Payment date validations
        today = date.today()
        if payload.payment_date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment date cannot be in the future",
            )
        if payload.payment_date < order.created_at.date():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment date cannot be earlier than the order creation date",
            )

        # Overpayment protection calculation:
        # Disputed payments MUST NOT silently disappear from the overpayment ceiling.
        # Every claim (acknowledged, unacknowledged, disputed) is fully committed
        # against the order total to prevent second payments exploiting active disputes.
        aggregates = self.repo.calculate_order_payment_summary(order.id, order.total_amount)
        current_committed = (
            aggregates["total_acknowledged"]
            + aggregates["unacknowledged_amount"]
            + aggregates["total_disputed"]
        )
        remaining_payable = max(Decimal("0.00"), order.total_amount - current_committed)

        if payload.amount > remaining_payable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Payment amount of INR {payload.amount} exceeds the remaining payable ceiling "
                    f"of INR {remaining_payable} (Order Total: INR {order.total_amount}, "
                    f"Currently Committed: INR {current_committed} "
                    f"[Acknowledged: {aggregates['total_acknowledged']}, "
                    f"Unacknowledged: {aggregates['unacknowledged_amount']}, "
                    f"Disputed: {aggregates['total_disputed']}])"
                ),
            )

        # Handle optional proof upload
        proof_file_uri: Optional[str] = None
        if proof_file is not None and proof_file.filename:
            proof_file_uri, _, _ = self.storage.save_proof(proof_file)

        try:
            record = self.repo.create_payment_record(
                order_id=order.id,
                recorded_by_user_id=current_user.id,
                amount=payload.amount,
                payment_method=payload.payment_method,
                payment_date=payload.payment_date,
                reference_number=payload.reference_number,
                proof_file_uri=proof_file_uri,
            )

            # Emit notification to designated farmer
            self.db.add(
                Notification(
                    user_id=order.farmer_id,
                    event_type="payment_recorded",
                    title="Payment Recorded",
                    body=(
                        f"Buyer recorded a payment of INR {payload.amount} via {payload.payment_method} "
                        f"for Order {order.order_number}. Please verify and acknowledge receipt."
                    ),
                    reference_type="order",
                    reference_id=order.id,
                )
            )

            self.db.commit()
            return record
        except Exception:
            self.db.rollback()
            if proof_file_uri:
                self.storage.delete_file(proof_file_uri)
            raise

    # -------------------------------------------------------------------------
    # 2. Payment Retrieval & Summaries
    # -------------------------------------------------------------------------

    def get_order_payments(
        self,
        order_id: uuid.UUID,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PaymentRecord], int]:
        """Retrieve paginated payment records for an order with anti-enumeration security."""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if current_user.id not in (order.buyer_id, order.farmer_id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        return self.repo.get_payments_for_order(order_id=order.id, limit=limit, offset=offset)

    def get_payment_summary(
        self,
        order_id: uuid.UUID,
        current_user: User,
    ) -> Dict[str, Any]:
        """Retrieve authoritative financial reconciliation summary for an order."""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if current_user.id not in (order.buyer_id, order.farmer_id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        return self.repo.calculate_order_payment_summary(order.id, order.total_amount)

    def get_payment_details(
        self,
        payment_id: uuid.UUID,
        current_user: User,
    ) -> PaymentRecord:
        """Retrieve detailed information about a specific payment record."""
        payment = self.repo.get_payment_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        order = self.db.query(Order).filter(Order.id == payment.order_id).first()
        if not order or (current_user.id not in (order.buyer_id, order.farmer_id) and current_user.role != "admin"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        return payment

    # -------------------------------------------------------------------------
    # 3. Farmer Payment Acknowledgement
    # -------------------------------------------------------------------------

    def acknowledge_payment(
        self,
        payment_id: uuid.UUID,
        current_user: User,
    ) -> PaymentRecord:
        """Acknowledge receipt of a recorded payment (farmer exclusivity)."""
        self._verify_active_and_verified(current_user)

        # Pre-lookup to discover associated order
        payment_peek = self.repo.get_payment_by_id(payment_id)
        if not payment_peek:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        # Canonical lock hierarchy: Order (Tier 2) -> PaymentRecord (Tier 6)
        order = (
            self.db.query(Order)
            .filter(Order.id == payment_peek.order_id)
            .with_for_update(of=Order)
            .populate_existing()
            .first()
        )
        payment = self.repo.get_payment_by_id(payment_id, for_update=True)

        if not order or not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        # Anti-enumeration
        if current_user.id not in (order.buyer_id, order.farmer_id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        # Exclusive farmer authorization
        if current_user.id != order.farmer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the designated farmer of this order may acknowledge receipt of payment",
            )

        # Prevent duplicate or invalid state transitions
        if payment.status == PAYMENT_STATUS_ACKNOWLEDGED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment has already been acknowledged",
            )
        if payment.status == PAYMENT_STATUS_DISPUTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot acknowledge a disputed payment record. Dispute must be resolved first.",
            )
        if payment.status != PAYMENT_STATUS_RECORDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge payment in '{payment.status}' status",
            )

        now_utc = datetime.now(timezone.utc)
        payment = self.repo.update_payment_status(
            payment=payment,
            new_status=PAYMENT_STATUS_ACKNOWLEDGED,
            acknowledged_at=now_utc,
        )

        # Notify buyer of receipt confirmation
        self.db.add(
            Notification(
                user_id=order.buyer_id,
                event_type="payment_acknowledged",
                title="Payment Receipt Confirmed",
                body=(
                    f"Farmer confirmed receipt of INR {payment.amount} for Order {order.order_number}. "
                    "Payment status updated to acknowledged."
                ),
                reference_type="order",
                reference_id=order.id,
            )
        )

        self.db.commit()
        return payment

    # -------------------------------------------------------------------------
    # 4. Payment Dispute & Complaints
    # -------------------------------------------------------------------------

    def file_payment_complaint(
        self,
        payment_id: uuid.UUID,
        current_user: User,
        complaint_reason: str,
        evidence_file: Optional[UploadFile] = None,
    ) -> PaymentComplaint:
        """File a formal dispute against a payment record."""
        self._verify_active_and_verified(current_user)

        # Pre-lookup
        payment_peek = self.repo.get_payment_by_id(payment_id)
        if not payment_peek:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        # Canonical lock hierarchy: Order (Tier 2) -> PaymentRecord (Tier 6)
        order = (
            self.db.query(Order)
            .filter(Order.id == payment_peek.order_id)
            .with_for_update(of=Order)
            .populate_existing()
            .first()
        )
        payment = self.repo.get_payment_by_id(payment_id, for_update=True)

        if not order or not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        # Anti-enumeration
        if current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        # Active duplicate complaint check
        existing_active = self.repo.get_active_complaint_for_payment(payment.id)
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An active complaint is already under review for this payment record",
            )

        evidence_file_uri: Optional[str] = None
        if evidence_file is not None and evidence_file.filename:
            evidence_file_uri, _, _ = self.storage.save_evidence(evidence_file)

        try:
            # Transition payment to disputed atomically
            self.repo.update_payment_status(payment, PAYMENT_STATUS_DISPUTED)

            complaint = self.repo.create_payment_complaint(
                payment_record_id=payment.id,
                complainant_user_id=current_user.id,
                complaint_reason=complaint_reason,
                evidence_file_uri=evidence_file_uri,
            )

            # Notify counterparty of dispute
            counterparty_id = order.buyer_id if current_user.id == order.farmer_id else order.farmer_id
            self.db.add(
                Notification(
                    user_id=counterparty_id,
                    event_type="payment_disputed",
                    title="Payment Record Disputed",
                    body=(
                        f"A dispute has been raised regarding payment of INR {payment.amount} "
                        f"on Order {order.order_number}. The payment has been marked as disputed."
                    ),
                    reference_type="order",
                    reference_id=order.id,
                )
            )

            self.db.commit()
            return complaint
        except Exception:
            self.db.rollback()
            if evidence_file_uri:
                self.storage.delete_file(evidence_file_uri)
            raise

    # -------------------------------------------------------------------------
    # 5. Administrative Dispute Moderation
    # -------------------------------------------------------------------------

    def admin_list_complaints(
        self,
        current_user: User,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PaymentComplaint], int]:
        """List complaints for the administrative moderation queue."""
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
        return self.repo.list_complaints(status_filter=status_filter, limit=limit, offset=offset)

    def admin_get_complaint_detail(
        self,
        complaint_id: uuid.UUID,
        current_user: User,
    ) -> Dict[str, Any]:
        """Retrieve comprehensive dispute details for admin mediation."""
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

        complaint = self.repo.get_complaint_by_id(complaint_id)
        if not complaint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment complaint not found")

        payment = self.repo.get_payment_by_id(complaint.payment_record_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        order = self.db.query(Order).filter(Order.id == payment.order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        return {
            "complaint": complaint,
            "payment": payment,
            "order_id": order.id,
            "order_number": order.order_number,
            "buyer_id": order.buyer_id,
            "farmer_id": order.farmer_id,
        }

    def admin_resolve_complaint(
        self,
        complaint_id: uuid.UUID,
        current_user: User,
        new_status: str,
        admin_resolution_notes: Optional[str] = None,
    ) -> PaymentComplaint:
        """Apply administrative dispute facilitation outcome."""
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

        # Canonical lock hierarchy: Order (Tier 2) -> PaymentRecord (Tier 6) -> PaymentComplaint (Tier 7)
        complaint_peek = self.repo.get_complaint_by_id(complaint_id)
        if not complaint_peek:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment complaint not found")

        payment = self.repo.get_payment_by_id(complaint_peek.payment_record_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        order = (
            self.db.query(Order)
            .filter(Order.id == payment.order_id)
            .with_for_update(of=Order)
            .populate_existing()
            .first()
        )
        payment_locked = self.repo.get_payment_by_id(payment.id, for_update=True)
        complaint = self.repo.get_complaint_by_id(complaint_id, for_update=True)

        if not complaint or not payment_locked or not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute entities not found")

        # State transition validation
        if complaint.status in (PAYMENT_COMPLAINT_STATUS_RESOLVED, PAYMENT_COMPLAINT_STATUS_DISMISSED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Complaint is already in terminal '{complaint.status}' status and cannot be modified",
            )

        if new_status not in VALID_PAYMENT_COMPLAINT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{new_status}'. Allowed: {', '.join(VALID_PAYMENT_COMPLAINT_STATUSES)}",
            )

        if new_status in (PAYMENT_COMPLAINT_STATUS_RESOLVED, PAYMENT_COMPLAINT_STATUS_DISMISSED):
            if not admin_resolution_notes or len(admin_resolution_notes.strip()) < 5:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Administrative resolution notes of at least 5 characters are required for terminal status",
                )

        # Administrative facilitation outcome:
        # Administrators review evidence and record findings.
        # Administrators NEVER acknowledge payments on behalf of participants.
        # If a complaint is resolved or dismissed:
        # - Complaint transitions to 'resolved' or 'dismissed'.
        # - Payment transitions from 'disputed' to 'payment_recorded' (unacknowledged for current settlement).
        # - payment.acknowledged_at is reset to None (requires explicit farmer reaffirmation).
        # - payment.original_acknowledged_at is PRESERVED as an immutable audit record of initial receipt.
        # - Original payment amount, method, reference, date, and proof are 100% preserved.
        # - Only the designated farmer can subsequently perform payment receipt acknowledgement.
        if new_status in (PAYMENT_COMPLAINT_STATUS_RESOLVED, PAYMENT_COMPLAINT_STATUS_DISMISSED):
            payment_locked.status = PAYMENT_STATUS_RECORDED
            payment_locked.acknowledged_at = None
            # payment_locked.original_acknowledged_at is intentionally preserved!

        updated_complaint = self.repo.update_complaint_status(
            complaint=complaint,
            new_status=new_status,
            admin_resolution_notes=admin_resolution_notes,
            resolved_by_admin_id=current_user.id,
        )

        # Permanent administrative audit trail
        self.db.add(
            AdminAuditLog(
                admin_user_id=current_user.id,
                action=f"payment_dispute_{new_status}",
                target_entity_type="payment_complaint",
                target_entity_id=complaint.id,
                reason=admin_resolution_notes,
            )
        )

        # Notify participants of administrative action
        for participant_id in (order.buyer_id, order.farmer_id):
            self.db.add(
                Notification(
                    user_id=participant_id,
                    event_type="payment_dispute_moderated",
                    title="Payment Dispute Status Update",
                    body=f"Dispute on Order {order.order_number} has been updated to '{new_status}' by administrator.",
                    reference_type="order",
                    reference_id=order.id,
                )
            )

        self.db.commit()
        return updated_complaint

    # -------------------------------------------------------------------------
    # 6. Attachment Download Path Resolution
    # -------------------------------------------------------------------------

    def get_payment_proof_download_path(self, payment_id: uuid.UUID, current_user: User) -> Tuple[Path, str]:
        """Verify participant authorization and resolve filesystem path for payment proof."""
        payment = self.repo.get_payment_by_id(payment_id)
        if not payment or not payment.proof_file_uri:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment proof not found")

        order = self.db.query(Order).filter(Order.id == payment.order_id).first()
        if not order or (current_user.id not in (order.buyer_id, order.farmer_id) and current_user.role != "admin"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment proof not found")

        resolved_path = self.storage.get_file_path(payment.proof_file_uri)
        return resolved_path, f"payment_proof_{payment.id}{resolved_path.suffix}"

    def get_complaint_evidence_download_path(self, complaint_id: uuid.UUID, current_user: User) -> Tuple[Path, str]:
        """Verify participant authorization and resolve filesystem path for dispute evidence."""
        complaint = self.repo.get_complaint_by_id(complaint_id)
        if not complaint or not complaint.evidence_file_uri:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute evidence not found")

        payment = self.repo.get_payment_by_id(complaint.payment_record_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute evidence not found")

        order = self.db.query(Order).filter(Order.id == payment.order_id).first()
        if not order or (current_user.id not in (order.buyer_id, order.farmer_id) and current_user.role != "admin"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute evidence not found")

        resolved_path = self.storage.get_file_path(complaint.evidence_file_uri)
        return resolved_path, f"dispute_evidence_{complaint.id}{resolved_path.suffix}"

