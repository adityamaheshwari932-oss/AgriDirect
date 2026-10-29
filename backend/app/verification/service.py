"""Service layer for verification application workflow, evidence storage, and administrative reviews.

Enforces:
- Role consistency: farmers submit farmer evidence; buyers submit buyer evidence.
- Duplicate prevention: at most one active pending application per user.
- Status integrity: submissions move to pending; only authorized administrators can approve or reject.
- Atomic state transitions: user verification_status and submission status are updated synchronously.
- Security: multi-tenant evidence isolation, audit logging, and domain notifications.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.admin import (
    ACTION_VERIFY_APPROVE,
    ACTION_VERIFY_REJECT,
    TARGET_ENTITY_VERIFICATION_SUBMISSION,
    AdminAuditLog,
)
from app.models.notification import NOTIFICATION_REF_VERIFICATION
from app.models.user import User
from app.models.verification import VerificationDocument, VerificationSubmission
from app.notifications.service import (
    EVENT_VERIFICATION_STATUS_CHANGED,
    NotificationService,
)
from app.verification.repository import VerificationRepository
from app.verification.schemas import (
    VALID_BUYER_DOCUMENT_TYPES,
    VALID_FARMER_DOCUMENT_TYPES,
    VerificationApproveRequest,
    VerificationRejectRequest,
    VerificationSubmissionCreate,
)
from app.verification.storage import DocumentStorageService


class VerificationService:
    """Orchestrates verification application lifecycle, document attachments, and reviews."""

    def __init__(
        self,
        db: Session,
        repository: Optional[VerificationRepository] = None,
        storage: Optional[DocumentStorageService] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.db = db
        self.repository = repository or VerificationRepository(db)
        self.storage = storage or DocumentStorageService()
        self.notification_service = notification_service or NotificationService(db)

    def submit_application(
        self,
        user: User,
        payload: VerificationSubmissionCreate,
    ) -> VerificationSubmission:
        """Submit a new verification application for an unverified or rejected farmer/buyer.

        Args:
            user: Authenticated active user.
            payload: Submission notes and optional role check.

        Returns:
            The newly created pending VerificationSubmission instance.

        Raises:
            HTTPException: 400 if user role is invalid, already verified, or role mismatch.
            HTTPException: 409 if an active pending application already exists.
        """
        if user.role not in ("farmer", "buyer"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only farmers and commercial buyers can submit verification applications",
            )

        if payload.role and payload.role.strip().lower() != user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application role '{payload.role}' does not match your account role '{user.role}'",
            )

        if user.verification_status == "verified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is already verified",
            )

        # Check for existing pending application (prevent duplicate review queue spam)
        active_pending = self.repository.get_pending_submission_by_user(user.id)
        if active_pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active verification submission under review",
            )

        submission = VerificationSubmission(
            user_id=user.id,
            status="pending",
            submission_notes=payload.submission_notes.strip() if payload.submission_notes else None,
        )
        self.repository.create_submission(submission)

        # Update user's verification status synchronously
        user.verification_status = "pending"

        # Dispatch confirmation notification
        self.notification_service.create_notification(
            user_id=user.id,
            event_type=EVENT_VERIFICATION_STATUS_CHANGED,
            title="Verification Application Submitted",
            body="Your verification application has been received and is pending administrative review.",
            reference_type=NOTIFICATION_REF_VERIFICATION,
            reference_id=submission.id,
        )

        self.db.commit()
        self.db.refresh(submission)
        return submission

    def upload_document(
        self,
        user: User,
        upload_file: UploadFile,
        document_type: str,
        document_number: Optional[str] = None,
    ) -> VerificationDocument:
        """Attach a verification evidence document to the user's active pending submission.

        If no submission exists yet and user is not verified, one is automatically created.

        Args:
            user: Authenticated user.
            upload_file: Multipart file stream.
            document_type: Canonical document category key.
            document_number: Optional ID or registration number on the document.

        Returns:
            The created VerificationDocument instance.

        Raises:
            HTTPException: 400 if user is already verified.
            HTTPException: 422 if document_type is invalid for user's role.
        """
        if user.role not in ("farmer", "buyer"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only farmers and commercial buyers can upload verification documents",
            )

        if user.verification_status == "verified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is already verified; document uploads are not permitted",
            )

        # Validate role-appropriate document types
        doc_type_clean = document_type.strip().lower()
        if user.role == "farmer" and doc_type_clean not in VALID_FARMER_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid document_type '{document_type}' for farmer. Allowed types: {', '.join(VALID_FARMER_DOCUMENT_TYPES)}",
            )
        if user.role == "buyer" and doc_type_clean not in VALID_BUYER_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid document_type '{document_type}' for buyer. Allowed types: {', '.join(VALID_BUYER_DOCUMENT_TYPES)}",
            )

        # Retrieve active pending submission or initialize one
        submission = self.repository.get_pending_submission_by_user(user.id)
        if submission is None:
            submission = VerificationSubmission(
                user_id=user.id,
                status="pending",
                submission_notes="Automatically created with document upload",
            )
            self.repository.create_submission(submission)
            user.verification_status = "pending"

        # Stream and validate upload to private storage
        file_uri, mime_type, file_size_bytes = self.storage.save_upload(upload_file)

        try:
            document = VerificationDocument(
                submission_id=submission.id,
                document_type=doc_type_clean,
                document_number=document_number.strip() if document_number else None,
                file_uri=file_uri,
                file_mime_type=mime_type,
                file_size_bytes=file_size_bytes,
            )
            self.repository.add_document(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception:
            self.db.rollback()
            try:
                file_path = self.storage.get_file_path(file_uri)
                if file_path.is_file():
                    file_path.unlink()
            except Exception:
                pass
            raise

    def get_my_current_submission(self, user: User) -> Optional[VerificationSubmission]:
        """Retrieve the applicant's current pending submission or most recent submission."""
        pending = self.repository.get_pending_submission_by_user(user.id)
        if pending is not None:
            return pending
        return self.repository.get_latest_submission_by_user(user.id)

    def get_my_submission_history(self, user: User) -> List[VerificationSubmission]:
        """Retrieve applicant's complete verification history."""
        return self.repository.get_all_submissions_by_user(user.id)

    def get_document_for_download(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> Tuple[Path, str]:
        """Authorize and resolve a verification document for downloading.

        Enforces multi-tenant ownership: only the document owner or an administrator
        is authorized to retrieve the file.

        Args:
            document_id: Primary key of document.
            current_user: Authenticated user.

        Returns:
            Tuple of (Path to file on disk, MIME type).

        Raises:
            HTTPException: 404 if document does not exist.
            HTTPException: 403 if caller is neither admin nor document owner.
        """
        doc = self.repository.get_document_by_id(document_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification document not found",
            )

        # Authorization check: admin or owner
        is_owner = doc.submission.user_id == current_user.id
        is_admin = current_user.role == "admin"

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access this document",
            )

        file_path = self.storage.get_file_path(doc.file_uri)
        return file_path, doc.file_mime_type

    def get_submission_document_for_download(
        self,
        submission_id: uuid.UUID,
        document_id: uuid.UUID,
        current_user: User,
    ) -> Tuple[Path, str]:
        """Authorize and resolve a document asserting it belongs to submission_id.

        Args:
            submission_id: Parent submission ID.
            document_id: Primary key of document.
            current_user: Authenticated user (admin or applicant).

        Returns:
            Tuple of (Path to file on disk, MIME type).

        Raises:
            HTTPException: 404 if document does not exist or does not belong to submission.
            HTTPException: 403 if caller is neither admin nor document owner.
        """
        doc = self.repository.get_document_by_id(document_id)
        if doc is None or doc.submission_id != submission_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification document not found for this submission",
            )

        is_owner = doc.submission.user_id == current_user.id
        is_admin = current_user.role == "admin"

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access this document",
            )

        file_path = self.storage.get_file_path(doc.file_uri)
        return file_path, doc.file_mime_type

    def admin_list_submissions(
        self,
        admin_user: User,
        status_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[VerificationSubmission], int]:
        """Retrieve a paginated queue of verification submissions for administrative review."""
        if admin_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        skip = (page - 1) * page_size

        items = self.repository.list_submissions(
            status=status_filter,
            role=role_filter,
            skip=skip,
            limit=page_size,
        )
        total = self.repository.count_submissions(
            status=status_filter,
            role=role_filter,
        )
        return items, total

    def admin_get_submission(
        self,
        submission_id: uuid.UUID,
        admin_user: User,
    ) -> VerificationSubmission:
        """Retrieve a single verification submission detail for admin review."""
        if admin_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        submission = self.repository.get_by_id(submission_id)
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification submission not found",
            )
        return submission

    def admin_approve_submission(
        self,
        submission_id: uuid.UUID,
        admin_user: User,
        payload: Optional[VerificationApproveRequest] = None,
        client_ip: Optional[str] = None,
    ) -> VerificationSubmission:
        """Approve an active pending verification submission and mark user verified.

        Args:
            submission_id: ID of submission.
            admin_user: Authenticated administrator.
            payload: Optional approval notes.
            client_ip: Remote IP address for audit trail.

        Returns:
            Updated VerificationSubmission instance.

        Raises:
            HTTPException: 403 if caller is not admin.
            HTTPException: 404 if submission is not found.
            HTTPException: 400 if submission is not in 'pending' status.
        """
        if admin_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        submission = self.repository.get_by_id_for_update(submission_id)
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification submission not found",
            )

        if submission.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve submission with status '{submission.status}'. Only 'pending' submissions can be approved.",
            )

        # Transition submission
        submission.status = "approved"
        submission.reviewed_by_admin_id = admin_user.id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.rejection_reason = None

        # Transition applicant user
        applicant = submission.user
        applicant.verification_status = "verified"

        # Record audit log
        audit = AdminAuditLog(
            admin_user_id=admin_user.id,
            action=ACTION_VERIFY_APPROVE,
            target_entity_type=TARGET_ENTITY_VERIFICATION_SUBMISSION,
            target_entity_id=submission.id,
            reason=payload.approval_notes if payload else "Approved by admin",
            ip_address=client_ip,
        )
        self.repository.record_admin_audit(audit)

        # Notify applicant
        self.notification_service.create_notification(
            user_id=applicant.id,
            event_type=EVENT_VERIFICATION_STATUS_CHANGED,
            title="Verification Approved",
            body="Your verification application has been approved. You now have full access to marketplace features.",
            reference_type=NOTIFICATION_REF_VERIFICATION,
            reference_id=submission.id,
        )

        self.db.commit()
        self.db.refresh(submission)
        return submission

    def admin_reject_submission(
        self,
        submission_id: uuid.UUID,
        admin_user: User,
        payload: VerificationRejectRequest,
        client_ip: Optional[str] = None,
    ) -> VerificationSubmission:
        """Reject an active pending verification submission with a mandatory reason.

        Args:
            submission_id: ID of submission.
            admin_user: Authenticated administrator.
            payload: Mandatory rejection reason.
            client_ip: Remote IP address for audit trail.

        Returns:
            Updated VerificationSubmission instance.

        Raises:
            HTTPException: 403 if caller is not admin.
            HTTPException: 404 if submission is not found.
            HTTPException: 400 if submission is not in 'pending' status or reason is blank.
        """
        if admin_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        reason = payload.rejection_reason.strip()
        if not reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason cannot be blank",
            )

        submission = self.repository.get_by_id_for_update(submission_id)
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification submission not found",
            )

        if submission.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject submission with status '{submission.status}'. Only 'pending' submissions can be rejected.",
            )

        # Transition submission
        submission.status = "rejected"
        submission.reviewed_by_admin_id = admin_user.id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.rejection_reason = reason

        # Transition applicant user
        applicant = submission.user
        applicant.verification_status = "rejected"

        # Record audit log
        audit = AdminAuditLog(
            admin_user_id=admin_user.id,
            action=ACTION_VERIFY_REJECT,
            target_entity_type=TARGET_ENTITY_VERIFICATION_SUBMISSION,
            target_entity_id=submission.id,
            reason=reason,
            ip_address=client_ip,
        )
        self.repository.record_admin_audit(audit)

        # Notify applicant
        self.notification_service.create_notification(
            user_id=applicant.id,
            event_type=EVENT_VERIFICATION_STATUS_CHANGED,
            title="Verification Rejected",
            body=f"Your verification application was rejected. Reason: {reason}. You may update your documentation and resubmit.",
            reference_type=NOTIFICATION_REF_VERIFICATION,
            reference_id=submission.id,
        )

        self.db.commit()
        self.db.refresh(submission)
        return submission
