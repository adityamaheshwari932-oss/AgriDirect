"""API routes for identity verification and administrative review workflows.

Implements Module 1 (Verification Management) of AgriDirect:
- Farmer & Buyer verification application submission
- Evidence document upload and secure file retrieval
- Administrative verification review queue (list, inspect, download evidence)
- Administrative review decisions (approve, reject with mandatory reason)
- Audit trail recording and applicant notification dispatch
"""

import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Body,
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
from app.verification.schemas import (
    VerificationApproveRequest,
    VerificationDocumentRead,
    VerificationListResponse,
    VerificationRejectRequest,
    VerificationSubmissionCreate,
    VerificationSubmissionRead,
)
from app.verification.service import VerificationService

router = APIRouter()


# ---------------------------------------------------------------------------
# Applicant (User) Verification Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/users/me/verification",
    response_model=VerificationSubmissionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["verification"],
    summary="Submit verification application",
    description=(
        "Submits an identity verification application for the authenticated farmer or buyer. "
        "Transitions application to pending review. Rejects duplicate active submissions or "
        "already verified users."
    ),
)
def submit_verification(
    payload: VerificationSubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> VerificationSubmissionRead:
    """Submit a new verification application."""
    service = VerificationService(db)
    return service.submit_application(user=current_user, payload=payload)


@router.get(
    "/users/me/verification",
    response_model=VerificationSubmissionRead,
    status_code=status.HTTP_200_OK,
    tags=["verification"],
    summary="Get current verification status and submission",
    description=(
        "Retrieves the active pending or latest verification submission for the "
        "authenticated user, including review notes and attached documents."
    ),
)
def get_my_verification(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> VerificationSubmissionRead:
    """Retrieve applicant's current active or latest submission."""
    service = VerificationService(db)
    submission = service.get_my_current_submission(user=current_user)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verification submission found for this user",
        )
    return submission


@router.get(
    "/users/me/verification/history",
    response_model=List[VerificationSubmissionRead],
    status_code=status.HTTP_200_OK,
    tags=["verification"],
    summary="Get verification submission history",
    description="Retrieves complete submission history for the authenticated user in reverse chronological order.",
)
def get_my_verification_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[VerificationSubmissionRead]:
    """Retrieve applicant's complete submission history."""
    service = VerificationService(db)
    return service.get_my_submission_history(user=current_user)


@router.post(
    "/users/me/verification/documents",
    response_model=VerificationDocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["verification"],
    summary="Upload verification evidence document",
    description=(
        "Uploads a verification evidence document (.pdf, .jpg, .jpeg, .png, .webp up to 10MB) "
        "and attaches it to the applicant's active pending submission."
    ),
)
def upload_verification_document(
    file: UploadFile = File(..., description="Document file (.pdf, .jpg, .jpeg, .png, .webp) up to 10MB"),
    document_type: str = Form(..., description="Document category code"),
    document_number: Optional[str] = Form(None, description="Optional document registration/ID number"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> VerificationDocumentRead:
    """Stream and store an evidence document attached to pending verification."""
    service = VerificationService(db)
    return service.upload_document(
        user=current_user,
        upload_file=file,
        document_type=document_type,
        document_number=document_number,
    )


@router.get(
    "/users/me/verification/documents/{document_id}/download",
    status_code=status.HTTP_200_OK,
    tags=["verification"],
    summary="Download own verification document",
    description="Downloads an evidence document file previously uploaded by the authenticated user.",
)
def download_my_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download an evidence document owned by the caller."""
    service = VerificationService(db)
    file_path, mime_type = service.get_document_for_download(
        document_id=document_id,
        current_user=current_user,
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
    )


# ---------------------------------------------------------------------------
# Administrator Verification Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/admin/verifications",
    response_model=VerificationListResponse,
    status_code=status.HTTP_200_OK,
    tags=["admin-verification"],
    summary="List verification submissions for review",
    description=(
        "Retrieves a paginated list of verification submissions with optional filtering "
        "by review status ('pending', 'approved', 'rejected') and applicant role ('farmer', 'buyer')."
    ),
)
def admin_list_verifications(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    role: Optional[str] = Query(None, description="Filter by applicant role: farmer, buyer"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VerificationListResponse:
    """List verification submissions for administrative review."""
    service = VerificationService(db)
    items, total = service.admin_list_submissions(
        admin_user=admin_user,
        status_filter=status,
        role_filter=role,
        page=page,
        page_size=page_size,
    )
    return VerificationListResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/admin/verifications/{id}",
    response_model=VerificationSubmissionRead,
    status_code=status.HTTP_200_OK,
    tags=["admin-verification"],
    summary="Get verification submission details for review",
    description="Retrieves a specific verification submission with applicant profile and attached evidence documents.",
)
def admin_get_verification(
    id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VerificationSubmissionRead:
    """Inspect submission details for administrative review."""
    service = VerificationService(db)
    return service.admin_get_submission(submission_id=id, admin_user=admin_user)


@router.get(
    "/admin/verifications/{id}/documents/{document_id}/download",
    status_code=status.HTTP_200_OK,
    tags=["admin-verification"],
    summary="Download verification document evidence as administrator",
    description="Authorized file download of verification evidence document for administrative inspection.",
)
def admin_download_document(
    id: uuid.UUID,
    document_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download an applicant's evidence document for administrative audit."""
    service = VerificationService(db)
    # Ensure parent submission exists and matches
    submission = service.admin_get_submission(submission_id=id, admin_user=admin_user)
    file_path, mime_type = service.get_submission_document_for_download(
        submission_id=id,
        document_id=document_id,
        current_user=admin_user,
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
    )


@router.post(
    "/admin/verifications/{id}/approve",
    response_model=VerificationSubmissionRead,
    status_code=status.HTTP_200_OK,
    tags=["admin-verification"],
    summary="Approve a verification submission",
    description=(
        "Approves an active pending verification submission, atomically updating user verification_status "
        "to 'verified', dispatching notification, and logging an administrative audit entry."
    ),
)
def admin_approve_verification(
    id: uuid.UUID,
    request: Request,
    payload: Optional[VerificationApproveRequest] = Body(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VerificationSubmissionRead:
    """Approve a pending verification submission."""
    client_ip = request.client.host if request.client else None
    service = VerificationService(db)
    return service.admin_approve_submission(
        submission_id=id,
        admin_user=admin_user,
        payload=payload,
        client_ip=client_ip,
    )


@router.post(
    "/admin/verifications/{id}/reject",
    response_model=VerificationSubmissionRead,
    status_code=status.HTTP_200_OK,
    tags=["admin-verification"],
    summary="Reject a verification submission",
    description=(
        "Rejects an active pending verification submission with a mandatory reason, atomically updating "
        "user verification_status to 'rejected', dispatching notification, and logging an administrative audit entry."
    ),
)
def admin_reject_verification(
    id: uuid.UUID,
    request: Request,
    payload: VerificationRejectRequest = Body(...),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VerificationSubmissionRead:
    """Reject a pending verification submission with a reason."""
    client_ip = request.client.host if request.client else None
    service = VerificationService(db)
    return service.admin_reject_submission(
        submission_id=id,
        admin_user=admin_user,
        payload=payload,
        client_ip=client_ip,
    )
