"""Service layer for user complaints, safety reporting, and administrative moderation.

Enforces:
- Active account verification for filing reports
- Validation of targets (reported user, produce listing)
- Anti-enumeration & confidentiality: Reported users and third parties cannot access filed reports
- Valid moderation lifecycle: 'open' -> 'under_review' -> 'action_taken' / 'dismissed'
- Non-terminal reopening restrictions
- Atomic administrative audit logging via AdminAuditLog
- Reporter operational notifications on moderation decisions
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin import AdminAuditLog, TARGET_ENTITY_REPORT
from app.models.listing import ProduceListing
from app.models.report import (
    REPORT_STATUS_ACTION_TAKEN,
    REPORT_STATUS_DISMISSED,
    REPORT_STATUS_OPEN,
    REPORT_STATUS_UNDER_REVIEW,
    VALID_REPORT_CATEGORIES,
    VALID_REPORT_STATUSES,
    UserReport,
)
from app.models.user import User
from app.notifications.service import NotificationService
from app.reports.repository import ReportRepository
from app.reports.schemas import (
    ReportCreate,
    ReportListResponse,
    ReportModerateRequest,
    ReportResponse,
)


class ReportService:
    """Orchestrates report lifecycle, validation, administrative moderation, and audit logging."""

    def __init__(
        self,
        db: Session,
        repository: Optional[ReportRepository] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.db = db
        self.repo = repository or ReportRepository(db)
        self.notification_service = notification_service or NotificationService(db)

    def create_report(
        self,
        current_user: User,
        report_in: ReportCreate,
    ) -> UserReport:
        """Submit a safety, fraud, or transaction violation report.

        Args:
            current_user: Authenticated caller filing the report.
            report_in: Validated report creation payload.

        Returns:
            The created and committed UserReport instance.

        Raises:
            HTTPException 403: If caller account is inactive.
            HTTPException 400: If self-reporting or missing targets.
            HTTPException 404: If target user or listing does not exist.
        """
        if current_user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive or suspended users cannot submit reports",
            )

        if report_in.category not in VALID_REPORT_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category '{report_in.category}'. Allowed categories: {list(VALID_REPORT_CATEGORIES)}",
            )

        if not report_in.reported_user_id and not report_in.listing_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report must specify at least one target: reported_user_id or listing_id",
            )

        # Validate reported user target
        if report_in.reported_user_id is not None:
            if report_in.reported_user_id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot submit a report against yourself",
                )
            target_user = self.db.query(User).filter(User.id == report_in.reported_user_id).first()
            if target_user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reported user '{report_in.reported_user_id}' does not exist",
                )

        # Validate listing target
        if report_in.listing_id is not None:
            listing = self.db.query(ProduceListing).filter(ProduceListing.id == report_in.listing_id).first()
            if listing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reported listing '{report_in.listing_id}' does not exist",
                )

        report = self.repo.create(
            reporter_id=current_user.id,
            report_in=report_in,
        )
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report(
        self,
        report_id: uuid.UUID,
        current_user: User,
    ) -> UserReport:
        """Fetch report details enforcing privacy and anti-enumeration.

        Rules:
        - Administrators may view any report.
        - The reporting user may view their own submitted report.
        - Reported users receive 404 (confidentiality protection).
        - Unrelated third parties receive 404.
        """
        report = self.repo.get_by_id(report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found",
            )

        if current_user.role != "admin" and current_user.id != report.reporter_id:
            # 404 returned to prevent enumeration or disclosure to reported user / third parties
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found",
            )

        return report

    def list_my_reports(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> ReportListResponse:
        """Retrieve paginated reports filed by the authenticated caller."""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.repo.list_for_reporter(
            reporter_id=current_user.id,
            skip=skip,
            limit=page_size,
        )
        total = self.repo.count_for_reporter(reporter_id=current_user.id)

        items_resp = [ReportResponse.model_validate(item) for item in items]
        return ReportListResponse.create(
            items=items_resp,
            total=total,
            page=page,
            page_size=page_size,
        )

    def admin_list_reports(
        self,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ReportListResponse:
        """Retrieve paginated reports for administrator moderation queue."""
        if status_filter and status_filter not in VALID_REPORT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter '{status_filter}'",
            )
        if category_filter and category_filter not in VALID_REPORT_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category filter '{category_filter}'",
            )

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.repo.list_for_admin(
            status_filter=status_filter,
            category_filter=category_filter,
            skip=skip,
            limit=page_size,
        )
        total = self.repo.count_for_admin(
            status_filter=status_filter,
            category_filter=category_filter,
        )

        items_resp = [ReportResponse.model_validate(item) for item in items]
        return ReportListResponse.create(
            items=items_resp,
            total=total,
            page=page,
            page_size=page_size,
        )

    def admin_moderate_report(
        self,
        report_id: uuid.UUID,
        current_admin: User,
        moderate_in: ReportModerateRequest,
        ip_address: Optional[str] = None,
    ) -> UserReport:
        """Perform administrative review, status transition, and audit logging.

        Atomically:
        1. Validates status transition
        2. Updates report status, admin_notes, reviewed_by_admin_id, updated_at
        3. Inserts an immutable AdminAuditLog entry
        4. Notifies the reporting user of the moderation outcome
        """
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        if moderate_in.status not in (REPORT_STATUS_UNDER_REVIEW, REPORT_STATUS_ACTION_TAKEN, REPORT_STATUS_DISMISSED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid target moderation status '{moderate_in.status}'. "
                    "Must be 'under_review', 'action_taken', or 'dismissed'."
                ),
            )

        report = self.repo.get_by_id(report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found",
            )

        # State transition validation: Terminal reports cannot be set back to open
        if report.status in (REPORT_STATUS_ACTION_TAKEN, REPORT_STATUS_DISMISSED) and moderate_in.status == REPORT_STATUS_OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Report is in terminal status '{report.status}' and cannot be reopened to 'open'",
            )

        # Update report entity
        now_utc = datetime.now(timezone.utc)
        report.status = moderate_in.status
        report.admin_notes = moderate_in.admin_notes.strip()
        report.reviewed_by_admin_id = current_admin.id
        report.updated_at = now_utc

        # Permanent audit log insertion
        audit = AdminAuditLog(
            admin_user_id=current_admin.id,
            action=f"report_moderate_{moderate_in.status}",
            target_entity_type=TARGET_ENTITY_REPORT,
            target_entity_id=report.id,
            reason=moderate_in.admin_notes.strip(),
            ip_address=ip_address,
        )
        self.db.add(audit)

        # Notify reporter
        self.notification_service.create_notification(
            user_id=report.reporter_id,
            event_type="report_status_update",
            title="User Report Status Update",
            body=(
                f"Your report regarding '{report.category}' has been reviewed by an administrator. "
                f"Status: {moderate_in.status}."
            ),
        )

        self.db.commit()
        self.db.refresh(report)
        return report
