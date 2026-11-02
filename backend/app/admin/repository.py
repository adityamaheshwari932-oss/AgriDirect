"""Repository layer for administrative operations, user directory, and catalog moderation.

Provides query methods with parameterised filters, deterministic sorting,
efficient eager loading, and row-level locking for concurrency safety.
"""

import uuid
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.admin import AdminAuditLog
from app.models.listing import ProduceCategory, ProduceListing
from app.models.order import ORDER_STATUS_COMPLETED, Order
from app.models.report import UserReport
from app.models.requirement import BuyerRequirement
from app.models.user import BuyerProfile, FarmerProfile, User
from app.models.verification import VerificationDocument, VerificationSubmission


class AdminAuditLogRepository:
    """Encapsulates read queries for AdminAuditLog records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, log_id: uuid.UUID) -> Optional[AdminAuditLog]:
        """Fetch a single audit log entry by primary key."""
        stmt = select(AdminAuditLog).where(AdminAuditLog.id == log_id)
        return self.db.scalars(stmt).first()

    def list_logs(
        self,
        admin_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[AdminAuditLog]:
        """Retrieve paginated audit logs ordered newest first."""
        stmt = select(AdminAuditLog)

        if admin_user_id is not None:
            stmt = stmt.where(AdminAuditLog.admin_user_id == admin_user_id)
        if action is not None:
            stmt = stmt.where(AdminAuditLog.action == action)
        if target_entity_type is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_type == target_entity_type)
        if target_entity_id is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_id == target_entity_id)

        stmt = stmt.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_logs(
        self,
        admin_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Count total audit logs matching the given filters."""
        stmt = select(func.count(AdminAuditLog.id))

        if admin_user_id is not None:
            stmt = stmt.where(AdminAuditLog.admin_user_id == admin_user_id)
        if action is not None:
            stmt = stmt.where(AdminAuditLog.action == action)
        if target_entity_type is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_type == target_entity_type)
        if target_entity_id is not None:
            stmt = stmt.where(AdminAuditLog.target_entity_id == target_entity_id)

        return self.db.scalar(stmt) or 0


class AdminUserRepository:
    """Manages database querying, filtering, and row locking for user accounts."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _build_user_query(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        account_status: Optional[str] = None,
        verification_status: Optional[str] = None,
        registered_from: Optional[date] = None,
        registered_to: Optional[date] = None,
    ):
        query = (
            self.db.query(User)
            .outerjoin(User.farmer_profile)
            .outerjoin(User.buyer_profile)
        )

        if role:
            query = query.filter(User.role == role.strip().lower())
        if account_status:
            query = query.filter(User.account_status == account_status.strip().lower())
        if verification_status:
            query = query.filter(User.verification_status == verification_status.strip().lower())

        if registered_from:
            dt_from = datetime.combine(registered_from, time.min).replace(tzinfo=timezone.utc)
            query = query.filter(User.created_at >= dt_from)
        if registered_to:
            dt_to = datetime.combine(registered_to, time.max).replace(tzinfo=timezone.utc)
            query = query.filter(User.created_at <= dt_to)

        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.email.ilike(pat),
                    User.phone_number.ilike(pat),
                    FarmerProfile.full_name.ilike(pat),
                    FarmerProfile.farm_name.ilike(pat),
                    BuyerProfile.contact_person_name.ilike(pat),
                    BuyerProfile.business_name.ilike(pat),
                )
            )

        return query

    def list_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        account_status: Optional[str] = None,
        verification_status: Optional[str] = None,
        registered_from: Optional[date] = None,
        registered_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[User]:
        query = self._build_user_query(
            search=search,
            role=role,
            account_status=account_status,
            verification_status=verification_status,
            registered_from=registered_from,
            registered_to=registered_to,
        )

        # Sorting column
        sort_col = User.created_at
        if sort_by == "email":
            sort_col = User.email
        elif sort_by == "role":
            sort_col = User.role
        elif sort_by == "account_status":
            sort_col = User.account_status

        order_expr = sort_col.asc() if sort_order == "asc" else sort_col.desc()
        # Tie-breaker deterministic sorting
        query = query.order_by(order_expr, User.id.asc())

        return (
            query.options(
                joinedload(User.farmer_profile),
                joinedload(User.buyer_profile),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        account_status: Optional[str] = None,
        verification_status: Optional[str] = None,
        registered_from: Optional[date] = None,
        registered_to: Optional[date] = None,
    ) -> int:
        query = self._build_user_query(
            search=search,
            role=role,
            account_status=account_status,
            verification_status=verification_status,
            registered_from=registered_from,
            registered_to=registered_to,
        )
        return query.with_entities(func.count(User.id)).scalar() or 0

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return (
            self.db.query(User)
            .options(
                joinedload(User.farmer_profile),
                joinedload(User.buyer_profile),
            )
            .filter(User.id == user_id)
            .first()
        )

    def get_user_by_id_for_update(self, user_id: uuid.UUID) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .with_for_update()
            .first()
        )

    def lock_and_count_active_admins(self, target_user_id: uuid.UUID) -> int:
        """Lock all active administrators in ascending ID order to prevent concurrency deadlocks,

        and return the count of other active administrators.
        """
        active_admins = (
            self.db.query(User)
            .filter(User.role == "admin", User.account_status == "active")
            .order_by(User.id.asc())
            .with_for_update()
            .all()
        )
        return sum(1 for a in active_admins if a.id != target_user_id)

    def get_user_activity_counts(self, user: User) -> Dict[str, int]:
        """Aggregate activity counts across listings, requirements, orders, and reports."""
        listings_count = (
            self.db.query(func.count(ProduceListing.id))
            .filter(ProduceListing.farmer_id == user.id)
            .scalar()
            or 0
        )
        requirements_count = (
            self.db.query(func.count(BuyerRequirement.id))
            .filter(BuyerRequirement.buyer_id == user.id)
            .scalar()
            or 0
        )
        completed_orders_count = (
            self.db.query(func.count(Order.id))
            .filter(
                or_(Order.buyer_id == user.id, Order.farmer_id == user.id),
                Order.status == ORDER_STATUS_COMPLETED,
            )
            .scalar()
            or 0
        )
        reports_filed_count = (
            self.db.query(func.count(UserReport.id))
            .filter(UserReport.reporter_id == user.id)
            .scalar()
            or 0
        )
        reports_received_count = (
            self.db.query(func.count(UserReport.id))
            .filter(UserReport.reported_user_id == user.id)
            .scalar()
            or 0
        )

        return {
            "listings_count": listings_count,
            "requirements_count": requirements_count,
            "completed_orders_count": completed_orders_count,
            "reports_filed_count": reports_filed_count,
            "reports_received_count": reports_received_count,
        }

    def get_latest_verification(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Fetch the most recent verification submission and document count."""
        sub = (
            self.db.query(VerificationSubmission)
            .filter(VerificationSubmission.user_id == user_id)
            .order_by(VerificationSubmission.created_at.desc())
            .first()
        )
        if not sub:
            return None

        doc_count = (
            self.db.query(func.count(VerificationDocument.id))
            .filter(VerificationDocument.submission_id == sub.id)
            .scalar()
            or 0
        )

        return {
            "latest_submission_id": sub.id,
            "status": sub.status,
            "submitted_at": sub.created_at,
            "reviewed_at": sub.reviewed_at,
            "rejection_reason": sub.rejection_reason,
            "documents_count": doc_count,
        }

    def get_recent_audit_logs(self, user_id: uuid.UUID, limit: int = 5) -> List[AdminAuditLog]:
        """Fetch latest administrative actions targeting this user."""
        return (
            self.db.query(AdminAuditLog)
            .filter(
                AdminAuditLog.target_entity_type == "user",
                AdminAuditLog.target_entity_id == user_id,
            )
            .order_by(AdminAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )


class AdminCatalogRepository:
    """Manages database querying, filtering, and row locking for listings and requirements."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Produce Listings
    # -----------------------------------------------------------------------

    def _build_listing_query(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        farmer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
    ):
        query = (
            self.db.query(ProduceListing)
            .join(ProduceListing.farmer)
            .outerjoin(User.farmer_profile)
            .outerjoin(ProduceListing.category)
        )

        if status:
            query = query.filter(ProduceListing.status == status.strip().lower())
        if category_id:
            query = query.filter(ProduceListing.category_id == category_id)
        if farmer_id:
            query = query.filter(ProduceListing.farmer_id == farmer_id)
        if is_deleted is not None:
            query = query.filter(ProduceListing.is_deleted == is_deleted)

        if has_reports is True:
            reported_listing_ids = (
                select(UserReport.listing_id)
                .where(UserReport.listing_id.isnot(None))
                .distinct()
            )
            query = query.filter(ProduceListing.id.in_(reported_listing_ids))
        elif has_reports is False:
            reported_listing_ids = (
                select(UserReport.listing_id)
                .where(UserReport.listing_id.isnot(None))
                .distinct()
            )
            query = query.filter(ProduceListing.id.notin_(reported_listing_ids))

        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    ProduceListing.product_name.ilike(pat),
                    ProduceListing.title.ilike(pat),
                    User.email.ilike(pat),
                    FarmerProfile.full_name.ilike(pat),
                    FarmerProfile.farm_name.ilike(pat),
                )
            )

        return query

    def list_listings(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        farmer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Tuple[ProduceListing, int]]:
        query = self._build_listing_query(
            search=search,
            status=status,
            category_id=category_id,
            farmer_id=farmer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
        )

        sort_col = ProduceListing.created_at
        if sort_by == "product_name":
            sort_col = ProduceListing.product_name
        elif sort_by == "price":
            sort_col = ProduceListing.price_per_unit
        elif sort_by == "status":
            sort_col = ProduceListing.status

        order_expr = sort_col.asc() if sort_order == "asc" else sort_col.desc()
        query = query.order_by(order_expr, ProduceListing.id.asc())

        listings = (
            query.options(
                joinedload(ProduceListing.farmer).joinedload(User.farmer_profile),
                joinedload(ProduceListing.category),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Batch report counts for retrieved listings
        if not listings:
            return []

        listing_ids = [l.id for l in listings]
        report_counts = dict(
            self.db.query(UserReport.listing_id, func.count(UserReport.id))
            .filter(UserReport.listing_id.in_(listing_ids))
            .group_by(UserReport.listing_id)
            .all()
        )

        return [(l, report_counts.get(l.id, 0)) for l in listings]

    def count_listings(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        farmer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
    ) -> int:
        query = self._build_listing_query(
            search=search,
            status=status,
            category_id=category_id,
            farmer_id=farmer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
        )
        return query.with_entities(func.count(ProduceListing.id)).scalar() or 0

    def get_listing_by_id(self, listing_id: uuid.UUID) -> Optional[ProduceListing]:
        return (
            self.db.query(ProduceListing)
            .options(
                joinedload(ProduceListing.farmer).joinedload(User.farmer_profile),
                joinedload(ProduceListing.category),
            )
            .filter(ProduceListing.id == listing_id)
            .first()
        )

    def get_listing_by_id_for_update(self, listing_id: uuid.UUID) -> Optional[ProduceListing]:
        return (
            self.db.query(ProduceListing)
            .filter(ProduceListing.id == listing_id)
            .with_for_update()
            .first()
        )

    def get_listing_reports_count(self, listing_id: uuid.UUID) -> int:
        return (
            self.db.query(func.count(UserReport.id))
            .filter(UserReport.listing_id == listing_id)
            .scalar()
            or 0
        )

    def close_user_active_catalog(self, user_id: uuid.UUID, now_utc: datetime) -> int:
        """Close active listings and requirements when user is suspended."""
        closed_listings = (
            self.db.query(ProduceListing)
            .filter(
                ProduceListing.farmer_id == user_id,
                ProduceListing.status.in_(["active", "partially_fulfilled"]),
            )
            .update(
                {"status": "closed", "updated_at": now_utc},
                synchronize_session="fetch",
            )
        )
        closed_reqs = (
            self.db.query(BuyerRequirement)
            .filter(
                BuyerRequirement.buyer_id == user_id,
                BuyerRequirement.status.in_(["active", "partially_fulfilled"]),
            )
            .update(
                {"status": "closed", "updated_at": now_utc},
                synchronize_session="fetch",
            )
        )
        return closed_listings + closed_reqs

    def soft_remove_user_active_catalog(self, user_id: uuid.UUID, now_utc: datetime) -> int:
        """Soft-remove active listings and requirements when user is blocked."""
        removed_listings = (
            self.db.query(ProduceListing)
            .filter(
                ProduceListing.farmer_id == user_id,
                ProduceListing.is_deleted.is_(False),
            )
            .update(
                {
                    "status": "closed",
                    "is_deleted": True,
                    "deleted_at": now_utc,
                    "updated_at": now_utc,
                },
                synchronize_session="fetch",
            )
        )
        removed_reqs = (
            self.db.query(BuyerRequirement)
            .filter(
                BuyerRequirement.buyer_id == user_id,
                BuyerRequirement.is_deleted.is_(False),
            )
            .update(
                {
                    "status": "closed",
                    "is_deleted": True,
                    "deleted_at": now_utc,
                    "updated_at": now_utc,
                },
                synchronize_session="fetch",
            )
        )
        return removed_listings + removed_reqs

    # -----------------------------------------------------------------------
    # Buyer Requirements
    # -----------------------------------------------------------------------

    def _build_requirement_query(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        buyer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
    ):
        query = (
            self.db.query(BuyerRequirement)
            .join(BuyerRequirement.buyer)
            .outerjoin(User.buyer_profile)
            .outerjoin(BuyerRequirement.category)
        )

        if status:
            query = query.filter(BuyerRequirement.status == status.strip().lower())
        if category_id:
            query = query.filter(BuyerRequirement.category_id == category_id)
        if buyer_id:
            query = query.filter(BuyerRequirement.buyer_id == buyer_id)
        if is_deleted is not None:
            query = query.filter(BuyerRequirement.is_deleted == is_deleted)

        if has_reports is True:
            reported_buyer_ids = (
                select(UserReport.reported_user_id)
                .where(UserReport.reported_user_id.isnot(None))
                .distinct()
            )
            query = query.filter(BuyerRequirement.buyer_id.in_(reported_buyer_ids))
        elif has_reports is False:
            reported_buyer_ids = (
                select(UserReport.reported_user_id)
                .where(UserReport.reported_user_id.isnot(None))
                .distinct()
            )
            query = query.filter(BuyerRequirement.buyer_id.notin_(reported_buyer_ids))

        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    BuyerRequirement.product_name.ilike(pat),
                    BuyerRequirement.title.ilike(pat),
                    User.email.ilike(pat),
                    BuyerProfile.contact_person_name.ilike(pat),
                    BuyerProfile.business_name.ilike(pat),
                )
            )

        return query

    def list_requirements(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        buyer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Tuple[BuyerRequirement, int]]:
        query = self._build_requirement_query(
            search=search,
            status=status,
            category_id=category_id,
            buyer_id=buyer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
        )

        sort_col = BuyerRequirement.created_at
        if sort_by == "product_name":
            sort_col = BuyerRequirement.product_name
        elif sort_by == "required_by_date":
            sort_col = BuyerRequirement.required_by_date
        elif sort_by == "status":
            sort_col = BuyerRequirement.status

        order_expr = sort_col.asc() if sort_order == "asc" else sort_col.desc()
        query = query.order_by(order_expr, BuyerRequirement.id.asc())

        reqs = (
            query.options(
                joinedload(BuyerRequirement.buyer).joinedload(User.buyer_profile),
                joinedload(BuyerRequirement.category),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        if not reqs:
            return []

        # Count reports on buyer
        buyer_ids = [r.buyer_id for r in reqs]
        report_counts = dict(
            self.db.query(UserReport.reported_user_id, func.count(UserReport.id))
            .filter(UserReport.reported_user_id.in_(buyer_ids))
            .group_by(UserReport.reported_user_id)
            .all()
        )

        return [(r, report_counts.get(r.buyer_id, 0)) for r in reqs]

    def count_requirements(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        buyer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
    ) -> int:
        query = self._build_requirement_query(
            search=search,
            status=status,
            category_id=category_id,
            buyer_id=buyer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
        )
        return query.with_entities(func.count(BuyerRequirement.id)).scalar() or 0

    def get_requirement_by_id(self, req_id: uuid.UUID) -> Optional[BuyerRequirement]:
        return (
            self.db.query(BuyerRequirement)
            .options(
                joinedload(BuyerRequirement.buyer).joinedload(User.buyer_profile),
                joinedload(BuyerRequirement.category),
            )
            .filter(BuyerRequirement.id == req_id)
            .first()
        )

    def get_requirement_by_id_for_update(self, req_id: uuid.UUID) -> Optional[BuyerRequirement]:
        return (
            self.db.query(BuyerRequirement)
            .filter(BuyerRequirement.id == req_id)
            .with_for_update()
            .first()
        )

    def get_requirement_reports_count(self, buyer_id: uuid.UUID) -> int:
        return (
            self.db.query(func.count(UserReport.id))
            .filter(UserReport.reported_user_id == buyer_id)
            .scalar()
            or 0
        )
