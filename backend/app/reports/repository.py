"""Repository layer for user complaints and safety moderation.

Provides scoped database access to the ``user_reports`` table:
- Atomic report insertion
- Scoped retrieval by reporter
- Administrative listing with optional status and category filters
- Status and moderation updates
"""

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.report import UserReport
from app.reports.schemas import ReportCreate


class ReportRepository:
    """Encapsulates all database interactions for the UserReport model."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        reporter_id: uuid.UUID,
        report_in: ReportCreate,
    ) -> UserReport:
        """Insert a new user report.

        Args:
            reporter_id: User ID of the submitting reporter.
            report_in: Validated report creation schema.

        Returns:
            The created UserReport instance (flushed, uncommitted).
        """
        report = UserReport(
            reporter_id=reporter_id,
            reported_user_id=report_in.reported_user_id,
            listing_id=report_in.listing_id,
            category=report_in.category,
            description=report_in.description.strip(),
            status="open",
        )
        self.db.add(report)
        self.db.flush()
        return report

    def get_by_id(self, report_id: uuid.UUID) -> Optional[UserReport]:
        """Fetch a single report by primary key."""
        stmt = select(UserReport).where(UserReport.id == report_id)
        return self.db.scalars(stmt).first()

    def list_for_reporter(
        self,
        reporter_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[UserReport]:
        """Retrieve paginated reports filed by a specific user, newest first."""
        stmt = (
            select(UserReport)
            .where(UserReport.reporter_id == reporter_id)
            .order_by(UserReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def count_for_reporter(self, reporter_id: uuid.UUID) -> int:
        """Count total reports filed by a specific user."""
        stmt = select(func.count(UserReport.id)).where(UserReport.reporter_id == reporter_id)
        return self.db.scalar(stmt) or 0

    def list_for_admin(
        self,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[UserReport]:
        """Retrieve paginated reports for administrative moderation queue."""
        stmt = select(UserReport)
        if status_filter:
            stmt = stmt.where(UserReport.status == status_filter)
        if category_filter:
            stmt = stmt.where(UserReport.category == category_filter)

        stmt = stmt.order_by(UserReport.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_for_admin(
        self,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> int:
        """Count total reports matching administrative filters."""
        stmt = select(func.count(UserReport.id))
        if status_filter:
            stmt = stmt.where(UserReport.status == status_filter)
        if category_filter:
            stmt = stmt.where(UserReport.category == category_filter)
        return self.db.scalar(stmt) or 0

