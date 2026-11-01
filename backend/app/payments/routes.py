"""FastAPI route handlers for off-platform payment tracking and dispute moderation.

Implements Module 6 endpoints:
- Order payments recording: POST /api/v1/orders/{order_id}/payments
- Order payments listing: GET /api/v1/orders/{order_id}/payments
- Order payments summary: GET /api/v1/orders/{order_id}/payments/summary
- Payment record details: GET /api/v1/payments/{payment_id}
- Farmer receipt acknowledgement: POST /api/v1/payments/{payment_id}/acknowledge
- Payment dispute complaints: POST /api/v1/payments/{payment_id}/complaints
- Proof file download: GET /api/v1/payments/{payment_id}/proof
- Dispute evidence download: GET /api/v1/payment-complaints/{complaint_id}/evidence
- Admin complaints queue: GET /api/v1/admin/payment-complaints
- Admin complaint detail: GET /api/v1/admin/payment-complaints/{complaint_id}
- Admin complaint resolve: POST /api/v1/admin/payment-complaints/{complaint_id}/resolve
"""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.payments.schemas import (
    AdminComplaintResolveRequest,
    PaymentComplaintCreate,
    PaymentComplaintDetailResponse,
    PaymentComplaintListResponse,
    PaymentComplaintResponse,
    PaymentRecordCreate,
    PaymentRecordListResponse,
    PaymentRecordResponse,
    PaymentSummaryResponse,
)
from app.payments.service import PaymentService
from app.payments.storage import PaymentStorageService

router = APIRouter(tags=["payments"])


def get_payment_storage() -> PaymentStorageService:
    """Dependency provider for PaymentStorageService."""
    return PaymentStorageService()


# ===========================================================================
# 1. Order-Scoped Payment Endpoints
# ===========================================================================


@router.post(
    "/orders/{order_id}/payments",
    response_model=PaymentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an off-platform payment against an order",
    description="A verified buyer records an off-platform payment (UPI, Bank Transfer, Cash, etc.) with optional proof.",
)
async def record_order_payment(
    order_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    storage: PaymentStorageService = Depends(get_payment_storage),
) -> PaymentRecordResponse:
    """Record payment supporting both JSON and multipart form-data requests."""
    content_type = request.headers.get("content-type", "").lower()
    proof_file: Optional[UploadFile] = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            payload = PaymentRecordCreate(**body)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )
    else:
        # Form data / multipart
        form = await request.form()
        raw_amount = form.get("amount")
        raw_method = form.get("payment_method")
        raw_date = form.get("payment_date")
        raw_ref = form.get("reference_number")
        uploaded = form.get("proof_file")

        if not raw_amount or not raw_method or not raw_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Fields 'amount', 'payment_method', and 'payment_date' are required",
            )

        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, ValueError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid numeric value for 'amount'",
            )

        try:
            payment_date = date.fromisoformat(str(raw_date))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid ISO format for 'payment_date' (expected YYYY-MM-DD)",
            )

        if uploaded is not None and getattr(uploaded, "filename", None):
            proof_file = uploaded

        try:
            payload = PaymentRecordCreate(
                amount=amount,
                payment_method=str(raw_method),
                payment_date=payment_date,
                reference_number=str(raw_ref) if raw_ref else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )

    service = PaymentService(db, storage=storage)
    record = service.record_payment(
        order_id=order_id,
        current_user=current_user,
        payload=payload,
        proof_file=proof_file,
    )
    return PaymentRecordResponse.from_orm_model(record)


@router.get(
    "/orders/{order_id}/payments",
    response_model=PaymentRecordListResponse,
    summary="List payment records for an order",
    description="Returns paginated payment records for participants of the specified order.",
)
def list_order_payments(
    order_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PaymentRecordListResponse:
    """List payments for order."""
    service = PaymentService(db)
    records, total = service.get_order_payments(
        order_id=order_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )
    return PaymentRecordListResponse(
        items=[PaymentRecordResponse.from_orm_model(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/orders/{order_id}/payments/summary",
    response_model=PaymentSummaryResponse,
    summary="Get payment reconciliation summary for an order",
    description="Returns total recorded, acknowledged, and disputed payment balances for an order.",
)
def get_order_payment_summary(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PaymentSummaryResponse:
    """Get financial settlement summary for an order."""
    service = PaymentService(db)
    summary_data = service.get_payment_summary(order_id=order_id, current_user=current_user)
    return PaymentSummaryResponse(**summary_data)


# ===========================================================================
# 2. Payment Lifecycle & Acknowledgement Endpoints
# ===========================================================================


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentRecordResponse,
    summary="Get payment record details",
    description="Retrieve details of a specific payment record with anti-enumeration protection.",
)
def get_payment_details(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PaymentRecordResponse:
    """Retrieve individual payment details."""
    service = PaymentService(db)
    record = service.get_payment_details(payment_id=payment_id, current_user=current_user)
    return PaymentRecordResponse.from_orm_model(record)


@router.post(
    "/payments/{payment_id}/acknowledge",
    response_model=PaymentRecordResponse,
    summary="Farmer acknowledges receipt of payment",
    description="The seller (farmer) acknowledges that the recorded payment was received off-platform.",
)
def acknowledge_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PaymentRecordResponse:
    """Acknowledge receipt of payment."""
    service = PaymentService(db)
    record = service.acknowledge_payment(payment_id=payment_id, current_user=current_user)
    return PaymentRecordResponse.from_orm_model(record)


@router.post(
    "/payments/{payment_id}/complaints",
    response_model=PaymentComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="File a dispute complaint against a payment record",
    description="Order participants file a formal dispute regarding a payment with optional evidence.",
)
async def file_payment_complaint(
    payment_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    storage: PaymentStorageService = Depends(get_payment_storage),
) -> PaymentComplaintResponse:
    """File a payment dispute complaint supporting JSON and multipart upload."""
    content_type = request.headers.get("content-type", "").lower()
    evidence_file: Optional[UploadFile] = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            payload = PaymentComplaintCreate(**body)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )
    else:
        form = await request.form()
        reason = form.get("complaint_reason") or form.get("reason")
        uploaded = form.get("evidence_file")

        if not reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Field 'complaint_reason' is required",
            )

        if uploaded is not None and getattr(uploaded, "filename", None):
            evidence_file = uploaded

        try:
            payload = PaymentComplaintCreate(complaint_reason=str(reason))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )

    service = PaymentService(db, storage=storage)
    complaint = service.file_payment_complaint(
        payment_id=payment_id,
        current_user=current_user,
        complaint_reason=payload.complaint_reason,
        evidence_file=evidence_file,
    )
    return PaymentComplaintResponse.from_orm_model(complaint)


# ===========================================================================
# 3. Evidence & Proof Secure Download Endpoints
# ===========================================================================


@router.get(
    "/payments/{payment_id}/proof",
    summary="Download payment proof attachment",
    description="Authorized participants and administrators stream payment receipt proof files.",
)
def download_payment_proof(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    storage: PaymentStorageService = Depends(get_payment_storage),
) -> FileResponse:
    """Stream payment proof attachment."""
    service = PaymentService(db, storage=storage)
    file_path, download_name = service.get_payment_proof_download_path(payment_id, current_user)
    return FileResponse(
        path=str(file_path),
        filename=download_name,
    )


@router.get(
    "/payment-complaints/{complaint_id}/evidence",
    summary="Download dispute evidence attachment",
    description="Authorized participants and administrators stream dispute evidence documents.",
)
def download_complaint_evidence(
    complaint_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    storage: PaymentStorageService = Depends(get_payment_storage),
) -> FileResponse:
    """Stream dispute evidence attachment."""
    service = PaymentService(db, storage=storage)
    file_path, download_name = service.get_complaint_evidence_download_path(complaint_id, current_user)
    return FileResponse(
        path=str(file_path),
        filename=download_name,
    )


# ===========================================================================
# 4. Administrative Dispute Moderation Endpoints
# ===========================================================================


@router.get(
    "/admin/payment-complaints",
    response_model=PaymentComplaintListResponse,
    summary="List payment complaints for administrative moderation",
    description="Administrators view and filter the dispute complaint queue.",
)
def admin_list_payment_complaints(
    status_filter: Annotated[Optional[str], Query(alias="status", description="Filter by complaint status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentComplaintListResponse:
    """Admin queue listing."""
    service = PaymentService(db)
    complaints, total = service.admin_list_complaints(
        current_user=admin_user,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return PaymentComplaintListResponse(
        items=[PaymentComplaintResponse.from_orm_model(c) for c in complaints],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/payment-complaints/{complaint_id}",
    response_model=PaymentComplaintDetailResponse,
    summary="Get payment complaint details for administrative review",
    description="Administrators inspect dispute evidence, order details, and counterparty metadata.",
)
def admin_get_payment_complaint_detail(
    complaint_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentComplaintDetailResponse:
    """Admin dispute detail inspection."""
    service = PaymentService(db)
    detail = service.admin_get_complaint_detail(complaint_id=complaint_id, current_user=admin_user)
    return PaymentComplaintDetailResponse(
        complaint=PaymentComplaintResponse.from_orm_model(detail["complaint"]),
        payment=PaymentRecordResponse.from_orm_model(detail["payment"]),
        order_id=detail["order_id"],
        order_number=detail["order_number"],
        buyer_id=detail["buyer_id"],
        farmer_id=detail["farmer_id"],
        order={
            "id": str(detail["order_id"]),
            "order_number": detail["order_number"],
            "buyer_id": str(detail["buyer_id"]),
            "farmer_id": str(detail["farmer_id"]),
        },
    )


@router.post(
    "/admin/payment-complaints/{complaint_id}/resolve",
    response_model=PaymentComplaintResponse,
    summary="Resolve or update payment complaint status",
    description="Administrators mark complaints under review, resolved, or dismissed with facilitation remarks.",
)
def admin_resolve_payment_complaint(
    complaint_id: uuid.UUID,
    payload: AdminComplaintResolveRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentComplaintResponse:
    """Admin dispute resolution."""
    service = PaymentService(db)
    target_status = payload.get_target_status()
    notes = payload.get_notes()
    updated = service.admin_resolve_complaint(
        complaint_id=complaint_id,
        current_user=admin_user,
        new_status=target_status,
        admin_resolution_notes=notes,
    )
    return PaymentComplaintResponse.from_orm_model(updated)

