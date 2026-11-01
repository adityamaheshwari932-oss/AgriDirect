"""SQLAlchemy repository for payment records, status updates, and dispute complaints.

Adheres strictly to synchronous SQLAlchemy 2.x conventions and row-level locking.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.payment import (
    PAYMENT_COMPLAINT_STATUS_DISMISSED,
    PAYMENT_COMPLAINT_STATUS_OPEN,
    PAYMENT_COMPLAINT_STATUS_RESOLVED,
    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
    PAYMENT_STATUS_ACKNOWLEDGED,
    PAYMENT_STATUS_DISPUTED,
    PAYMENT_STATUS_RECORDED,
    PaymentComplaint,
    PaymentRecord,
)


class PaymentRepository:
    """Synchronous database repository for Module 6 payment entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -------------------------------------------------------------------------
    # PaymentRecord Queries & Persistence
    # -------------------------------------------------------------------------

    def get_payment_by_id(
        self,
        payment_id: uuid.UUID,
        for_update: bool = False,
    ) -> Optional[PaymentRecord]:
        """Retrieve a PaymentRecord by ID with optional Tier 6 row-level lock.

        In the extended global lock hierarchy:
        Tier 1 (Offer) -> Tier 2 (Order) -> Tier 3 (Listing) -> Tier 4 (Requirement) ->
        Tier 5 (Approval) -> Tier 6 (PaymentRecord) -> Tier 7 (PaymentComplaint).
        """
        query = self.db.query(PaymentRecord).filter(PaymentRecord.id == payment_id)
        if for_update:
            query = query.with_for_update(of=PaymentRecord).populate_existing()
        return query.first()

    def get_payments_for_order(
        self,
        order_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PaymentRecord], int]:
        """Retrieve paginated payment records for an order, ordered newest first."""
        base_query = self.db.query(PaymentRecord).filter(PaymentRecord.order_id == order_id)
        total = base_query.count()
        records = (
            base_query.order_by(PaymentRecord.created_at.desc(), PaymentRecord.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return records, total

    def get_all_payments_for_order(self, order_id: uuid.UUID) -> List[PaymentRecord]:
        """Retrieve all payment records for an order (for balance aggregations)."""
        return (
            self.db.query(PaymentRecord)
            .filter(PaymentRecord.order_id == order_id)
            .order_by(PaymentRecord.created_at.asc())
            .all()
        )

    def create_payment_record(
        self,
        order_id: uuid.UUID,
        recorded_by_user_id: uuid.UUID,
        amount: Decimal,
        payment_method: str,
        payment_date: date,
        reference_number: Optional[str] = None,
        proof_file_uri: Optional[str] = None,
    ) -> PaymentRecord:
        """Create and persist a new PaymentRecord in 'payment_recorded' status."""
        record = PaymentRecord(
            order_id=order_id,
            recorded_by_user_id=recorded_by_user_id,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            proof_file_uri=proof_file_uri,
            status=PAYMENT_STATUS_RECORDED,
            payment_date=payment_date,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def update_payment_status(
        self,
        payment: PaymentRecord,
        new_status: str,
        acknowledged_at: Optional[datetime] = None,
        clear_acknowledged_at: bool = False,
    ) -> PaymentRecord:
        """Update payment status and acknowledgement timestamp.

        Preserves original_acknowledged_at as an immutable historical record.
        """
        payment.status = new_status
        if clear_acknowledged_at:
            payment.acknowledged_at = None
        elif acknowledged_at is not None:
            payment.acknowledged_at = acknowledged_at
            if payment.original_acknowledged_at is None:
                payment.original_acknowledged_at = acknowledged_at
        self.db.add(payment)
        self.db.flush()
        return payment

    def calculate_order_payment_summary(
        self,
        order_id: uuid.UUID,
        order_total: Decimal,
    ) -> Dict[str, Any]:
        """Compute authoritative financial reconciliation aggregates for an order.

        Distinguishes:
        - total_recorded: Sum of all recorded payments (retains full platform visibility).
        - total_acknowledged: Sum of payments currently confirmed by farmer (status = 'acknowledged').
        - total_disputed: Sum of payments currently locked in dispute (status = 'disputed').
        - unacknowledged_amount: Sum of payments awaiting acknowledgement (status = 'payment_recorded').
        - remaining_acknowledged_balance: max(0.00, order_total - total_acknowledged).
        - remaining_payable_amount / max_available_for_new_payment: max(0.00, order_total - committed_total).
        - settlement_status:
            * 'fully_settled': total_acknowledged >= order_total
            * 'partially_settled': 0.00 < total_acknowledged < order_total
            * 'payment_pending_acknowledgement': total_acknowledged == 0 and unacknowledged_amount > 0
            * 'disputed': total_acknowledged == 0 and unacknowledged_amount == 0 and total_disputed > 0
            * 'unpaid': total_recorded == 0 (strictly zero payment claims recorded)
        """
        payments = self.get_all_payments_for_order(order_id)

        total_recorded = Decimal("0.00")
        total_acknowledged = Decimal("0.00")
        total_disputed = Decimal("0.00")
        unacknowledged_amount = Decimal("0.00")

        for p in payments:
            total_recorded += p.amount
            if p.status == PAYMENT_STATUS_ACKNOWLEDGED:
                total_acknowledged += p.amount
            elif p.status == PAYMENT_STATUS_DISPUTED:
                total_disputed += p.amount
            elif p.status == PAYMENT_STATUS_RECORDED:
                unacknowledged_amount += p.amount

        remaining_balance = max(Decimal("0.00"), order_total - total_acknowledged)
        committed_total = total_acknowledged + unacknowledged_amount + total_disputed
        remaining_payable = max(Decimal("0.00"), order_total - committed_total)

        if total_acknowledged >= order_total:
            settlement_status = "fully_settled"
        elif total_acknowledged > Decimal("0.00"):
            settlement_status = "partially_settled"
        elif unacknowledged_amount > Decimal("0.00"):
            settlement_status = "payment_pending_acknowledgement"
        elif total_disputed > Decimal("0.00"):
            settlement_status = "disputed"
        else:
            settlement_status = "unpaid"

        return {
            "order_id": order_id,
            "order_total": order_total,
            "total_recorded": total_recorded,
            "total_acknowledged": total_acknowledged,
            "total_disputed": total_disputed,
            "unacknowledged_amount": unacknowledged_amount,
            "remaining_acknowledged_balance": remaining_balance,
            "remaining_payable_amount": remaining_payable,
            "max_available_for_new_payment": remaining_payable,
            "settlement_status": settlement_status,
            "records_count": len(payments),
        }

    # -------------------------------------------------------------------------
    # PaymentComplaint Queries & Persistence
    # -------------------------------------------------------------------------

    def get_complaint_by_id(
        self,
        complaint_id: uuid.UUID,
        for_update: bool = False,
    ) -> Optional[PaymentComplaint]:
        """Retrieve a PaymentComplaint by ID with optional Tier 7 row-level lock.

        In the extended global lock hierarchy:
        Tier 1 (Offer) -> Tier 2 (Order) -> Tier 3 (Listing) -> Tier 4 (Requirement) ->
        Tier 5 (Approval) -> Tier 6 (PaymentRecord) -> Tier 7 (PaymentComplaint).
        """
        query = self.db.query(PaymentComplaint).filter(PaymentComplaint.id == complaint_id)
        if for_update:
            query = query.with_for_update(of=PaymentComplaint).populate_existing()
        return query.first()

    def get_active_complaint_for_payment(
        self,
        payment_id: uuid.UUID,
    ) -> Optional[PaymentComplaint]:
        """Retrieve any open or under-review dispute for a payment record."""
        return (
            self.db.query(PaymentComplaint)
            .filter(
                PaymentComplaint.payment_record_id == payment_id,
                PaymentComplaint.status.in_([
                    PAYMENT_COMPLAINT_STATUS_OPEN,
                    PAYMENT_COMPLAINT_STATUS_UNDER_REVIEW,
                ]),
            )
            .first()
        )

    def create_payment_complaint(
        self,
        payment_record_id: uuid.UUID,
        complainant_user_id: uuid.UUID,
        complaint_reason: str,
        evidence_file_uri: Optional[str] = None,
    ) -> PaymentComplaint:
        """Create and persist a new PaymentComplaint in 'open' status."""
        complaint = PaymentComplaint(
            payment_record_id=payment_record_id,
            complainant_user_id=complainant_user_id,
            complaint_reason=complaint_reason,
            evidence_file_uri=evidence_file_uri,
            status=PAYMENT_COMPLAINT_STATUS_OPEN,
        )
        self.db.add(complaint)
        self.db.flush()
        return complaint

    def update_complaint_status(
        self,
        complaint: PaymentComplaint,
        new_status: str,
        admin_resolution_notes: Optional[str] = None,
        resolved_by_admin_id: Optional[uuid.UUID] = None,
    ) -> PaymentComplaint:
        """Update dispute complaint status and administrative notes."""
        complaint.status = new_status
        if admin_resolution_notes is not None:
            complaint.admin_resolution_notes = admin_resolution_notes
        if resolved_by_admin_id is not None:
            complaint.resolved_by_admin_id = resolved_by_admin_id
        self.db.add(complaint)
        self.db.flush()
        return complaint

    def list_complaints(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PaymentComplaint], int]:
        """Retrieve paginated complaints for administrative review queues."""
        query = self.db.query(PaymentComplaint)
        if status_filter:
            query = query.filter(PaymentComplaint.status == status_filter)
        total = query.count()
        complaints = (
            query.order_by(PaymentComplaint.created_at.desc(), PaymentComplaint.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return complaints, total

