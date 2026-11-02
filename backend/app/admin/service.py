"""Service layer for administrative operations, governance, and catalog moderation.

Orchestrates:
- AdminAuditLogService: Read-only access to immutable audit log records.
- AdminUserModerationService: User directory, inspection, status transition rules,
  self-modification guards, last-active-admin protection, and atomic audit logging.
- AdminCatalogModerationService: Produce listing & buyer requirement moderation queues,
  close/remove/restore lifecycles, domain validation, and atomic audit logging.
"""

import math
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.admin.repository import (
    AdminAuditLogRepository,
    AdminCatalogRepository,
    AdminUserRepository,
)
from app.admin.schemas import (
    AdminAuditLogListResponse,
    AdminAuditLogResponse,
    AdminListingListResponse,
    AdminListingModerateRequest,
    AdminListingModerateResponse,
    AdminListingSummaryRead,
    AdminRequirementListResponse,
    AdminRequirementModerateRequest,
    AdminRequirementModerateResponse,
    AdminRequirementSummaryRead,
    AdminUserActivityCounts,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserStatusUpdateRequest,
    AdminUserStatusUpdateResponse,
    AdminUserSummaryRead,
    AdminVerificationSummary,
)
from app.auth.schemas import BuyerProfileRead, FarmerProfileRead
from app.models.admin import AdminAuditLog
from app.models.listing import ProduceListing
from app.models.notification import Notification
from app.models.requirement import BuyerRequirement
from app.models.user import User

# Permitted account status transition graph
PERMITTED_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "active": ["restricted", "suspended", "blocked"],
    "restricted": ["active", "suspended", "blocked"],
    "suspended": ["active", "restricted", "blocked"],
    "blocked": ["active"],  # Reinstatement via appeal/review
}


# ===========================================================================
# 1. Administrative Audit Log Service (Module 8)
# ===========================================================================


class AdminAuditLogService:
    """Orchestrates administrative audit log queries and access controls."""

    def __init__(
        self,
        db: Session,
        repository: Optional[AdminAuditLogRepository] = None,
    ) -> None:
        self.db = db
        self.repo = repository or AdminAuditLogRepository(db)

    def list_logs(
        self,
        current_admin: User,
        admin_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminAuditLogListResponse:
        """Retrieve paginated audit trail entries with optional filtering."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.repo.list_logs(
            admin_user_id=admin_user_id,
            action=action,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            skip=skip,
            limit=page_size,
        )
        total = self.repo.count_logs(
            admin_user_id=admin_user_id,
            action=action,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
        )

        items_resp = [AdminAuditLogResponse.model_validate(item) for item in items]
        return AdminAuditLogListResponse.create(
            items=items_resp,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_log(
        self,
        log_id: uuid.UUID,
        current_admin: User,
    ) -> AdminAuditLog:
        """Fetch details of a specific audit log entry."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        log_entry = self.repo.get_by_id(log_id)
        if log_entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit log entry '{log_id}' not found",
            )
        return log_entry


# ===========================================================================
# 2. Administrative User Moderation Service (Module 10 / Scope A & B)
# ===========================================================================


class AdminUserModerationService:
    """Manages administrative user directory, inspection, and status transitions."""

    def __init__(
        self,
        db: Session,
        user_repo: Optional[AdminUserRepository] = None,
        catalog_repo: Optional[AdminCatalogRepository] = None,
    ) -> None:
        self.db = db
        self.user_repo = user_repo or AdminUserRepository(db)
        self.catalog_repo = catalog_repo or AdminCatalogRepository(db)

    @staticmethod
    def user_to_summary(user: User) -> AdminUserSummaryRead:
        """Derive display and organization names safely from role profiles."""
        display_name = "User"
        organization_name = None
        location_summary = None

        if user.role == "farmer":
            p = user.farmer_profile
            display_name = p.full_name if p and p.full_name else (user.email.split("@")[0])
            organization_name = p.farm_name if p and p.farm_name else None
            if p and p.city and p.state:
                location_summary = f"{p.city}, {p.state}"
        elif user.role == "buyer":
            p = user.buyer_profile
            display_name = p.contact_person_name if p and p.contact_person_name else (user.email.split("@")[0])
            organization_name = p.business_name if p and p.business_name else None
            if p and p.city and p.state:
                location_summary = f"{p.city}, {p.state}"
        elif user.role == "admin":
            display_name = "Administrator"
            organization_name = "AgriDirect Platform"

        return AdminUserSummaryRead(
            id=user.id,
            email=user.email,
            phone_number=user.phone_number,
            role=user.role,
            verification_status=user.verification_status,
            account_status=user.account_status,
            display_name=display_name,
            organization_name=organization_name,
            location_summary=location_summary,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def list_users(
        self,
        current_admin: User,
        search: Optional[str] = None,
        role: Optional[str] = None,
        account_status_filter: Optional[str] = None,
        verification_status_filter: Optional[str] = None,
        registered_from: Optional[date] = None,
        registered_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> AdminUserListResponse:
        """Query and paginate platform users directory."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        if registered_from and registered_to and registered_from > registered_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="registered_from cannot be later than registered_to",
            )

        if sort_by not in ("created_at", "email", "role", "account_status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field '{sort_by}'",
            )
        if sort_order not in ("asc", "desc"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_order '{sort_order}'. Must be 'asc' or 'desc'.",
            )

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        users = self.user_repo.list_users(
            search=search,
            role=role,
            account_status=account_status_filter,
            verification_status=verification_status_filter,
            registered_from=registered_from,
            registered_to=registered_to,
            skip=skip,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total = self.user_repo.count_users(
            search=search,
            role=role,
            account_status=account_status_filter,
            verification_status=verification_status_filter,
            registered_from=registered_from,
            registered_to=registered_to,
        )

        items = [self.user_to_summary(u) for u in users]
        return AdminUserListResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_user_detail(
        self,
        user_id: uuid.UUID,
        current_admin: User,
    ) -> AdminUserDetailResponse:
        """Fetch full inspection view of a user without sensitive credentials."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        user = self.user_repo.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )

        # Activity metrics
        activity_data = self.user_repo.get_user_activity_counts(user)
        activity_counts = AdminUserActivityCounts(**activity_data)

        # Verification summary
        verif_data = self.user_repo.get_latest_verification(user_id)
        verif_summary = AdminVerificationSummary(**verif_data) if verif_data else None

        # Recent audit logs
        recent_logs = self.user_repo.get_recent_audit_logs(user_id, limit=5)
        recent_logs_resp = [AdminAuditLogResponse.model_validate(log) for log in recent_logs]

        # Role profile
        farmer_profile = (
            FarmerProfileRead.model_validate(user.farmer_profile)
            if user.farmer_profile
            else None
        )
        buyer_profile = (
            BuyerProfileRead.model_validate(user.buyer_profile)
            if user.buyer_profile
            else None
        )

        return AdminUserDetailResponse(
            id=user.id,
            email=user.email,
            phone_number=user.phone_number,
            role=user.role,
            verification_status=user.verification_status,
            account_status=user.account_status,
            created_at=user.created_at,
            updated_at=user.updated_at,
            farmer_profile=farmer_profile,
            buyer_profile=buyer_profile,
            verification_summary=verif_summary,
            activity_counts=activity_counts,
            recent_audit_logs=recent_logs_resp,
        )

    def update_user_status(
        self,
        user_id: uuid.UUID,
        current_admin: User,
        payload: AdminUserStatusUpdateRequest,
        ip_address: Optional[str] = None,
    ) -> AdminUserStatusUpdateResponse:
        """Execute validated account status transition with atomic audit logging and notifications."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        # Safeguard 1: Self-modification protection
        if current_admin.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot modify their own account status",
            )

        # Pre-check target user existence
        target_preview = self.user_repo.get_user_by_id(user_id)
        if target_preview is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )

        # Safeguard 4: Last active administrator concurrency protection
        # When deactivating an administrator, lock all active administrators in deterministic
        # ascending ID order FIRST to ensure deadlock-free serialization under concurrent races.
        if target_preview.role == "admin" and payload.account_status != "active":
            other_active_admins = self.user_repo.lock_and_count_active_admins(target_preview.id)
            if other_active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot suspend, restrict, or block the platform's last active administrator",
                )

        # Step 1: Acquire row-level lock on target user
        target_user = self.user_repo.get_user_by_id_for_update(user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )

        # Safeguard 2: Idempotency / No-op guard
        if target_user.account_status == payload.account_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is already in status '{payload.account_status}'",
            )

        # Safeguard 3: Allowed transitions matrix validation
        allowed_next = PERMITTED_STATUS_TRANSITIONS.get(target_user.account_status, [])
        if payload.account_status not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid account status transition from '{target_user.account_status}' "
                    f"to '{payload.account_status}'"
                ),
            )

        now_utc = datetime.now(timezone.utc)
        prev_status = target_user.account_status
        new_status = payload.account_status

        # Step 2: Apply status mutation
        target_user.account_status = new_status
        target_user.updated_at = now_utc

        # Step 3: Apply catalog side-effects
        if new_status == "suspended":
            self.catalog_repo.close_user_active_catalog(target_user.id, now_utc)
        elif new_status == "blocked":
            self.catalog_repo.soft_remove_user_active_catalog(target_user.id, now_utc)

        # Step 4: Record permanent AdminAuditLog
        audit = AdminAuditLog(
            admin_user_id=current_admin.id,
            action=f"user_status_{new_status}",
            target_entity_type="user",
            target_entity_id=target_user.id,
            reason=f"Status changed from '{prev_status}' to '{new_status}'. Reason: {payload.reason.strip()}",
            ip_address=ip_address,
        )
        self.db.add(audit)
        self.db.flush()

        # Step 5: Record in-app notification in same transaction
        notif = Notification(
            user_id=target_user.id,
            event_type="account_status_changed",
            title=f"Account Status Updated: {new_status.title()}",
            body=f"Your account status was changed to '{new_status}'. Reason: {payload.reason.strip()}",
            is_read=False,
        )
        self.db.add(notif)

        # Step 6: Atomic commit
        self.db.commit()
        self.db.refresh(target_user)

        summary = self.user_to_summary(target_user)
        return AdminUserStatusUpdateResponse(
            user=summary,
            previous_status=prev_status,
            new_status=new_status,
            audit_log_id=audit.id,
            reason=payload.reason.strip(),
            updated_at=now_utc,
        )


# ===========================================================================
# 3. Administrative Catalog Moderation Service (Module 10 / Scope C & D)
# ===========================================================================


class AdminCatalogModerationService:
    """Manages produce listing and buyer requirement moderation queues and actions."""

    def __init__(
        self,
        db: Session,
        catalog_repo: Optional[AdminCatalogRepository] = None,
    ) -> None:
        self.db = db
        self.catalog_repo = catalog_repo or AdminCatalogRepository(db)

    # -----------------------------------------------------------------------
    # Listing Moderation
    # -----------------------------------------------------------------------

    @staticmethod
    def listing_to_summary(listing: ProduceListing, reports_count: int) -> AdminListingSummaryRead:
        f = listing.farmer
        farmer_name = "Farmer"
        if f:
            farmer_name = (
                f.farmer_profile.full_name
                if f.farmer_profile and f.farmer_profile.full_name
                else (f.email.split("@")[0])
            )

        cat_name = listing.category.name if listing.category else None

        return AdminListingSummaryRead(
            id=listing.id,
            farmer_id=listing.farmer_id,
            farmer_email=f.email if f else "unknown",
            farmer_name=farmer_name,
            product_name=listing.product_name,
            title=listing.title,
            category_id=listing.category_id,
            category_name=cat_name,
            initial_quantity=listing.initial_quantity,
            available_quantity=listing.available_quantity,
            unit=listing.unit,
            price_per_unit=listing.price_per_unit,
            status=listing.status,
            is_deleted=listing.is_deleted,
            deleted_at=listing.deleted_at,
            expires_at=listing.expires_at,
            reports_count=reports_count,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )

    def list_listings(
        self,
        current_admin: User,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        farmer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> AdminListingListResponse:
        """Query and paginate produce listings for moderation."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        if sort_by not in ("created_at", "product_name", "price", "status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field '{sort_by}'",
            )
        if sort_order not in ("asc", "desc"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_order '{sort_order}'",
            )

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.catalog_repo.list_listings(
            search=search,
            status=status_filter,
            category_id=category_id,
            farmer_id=farmer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
            skip=skip,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total = self.catalog_repo.count_listings(
            search=search,
            status=status_filter,
            category_id=category_id,
            farmer_id=farmer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
        )

        summaries = [self.listing_to_summary(l, cnt) for l, cnt in items]
        return AdminListingListResponse.create(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    def moderate_listing(
        self,
        listing_id: uuid.UUID,
        current_admin: User,
        payload: AdminListingModerateRequest,
        ip_address: Optional[str] = None,
    ) -> AdminListingModerateResponse:
        """Apply close, remove, or restore moderation action to a produce listing."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        # Acquire row lock
        listing = self.catalog_repo.get_listing_by_id_for_update(listing_id)
        if listing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing '{listing_id}' not found",
            )

        now_utc = datetime.now(timezone.utc)
        prev_status = listing.status
        action = payload.action

        if action == "close":
            if listing.status == "closed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Listing is already closed",
                )
            listing.status = "closed"
            listing.updated_at = now_utc

        elif action == "remove":
            if listing.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Listing is already removed (soft-deleted)",
                )
            listing.status = "closed"
            listing.is_deleted = True
            listing.deleted_at = now_utc
            listing.updated_at = now_utc

        elif action == "restore":
            if not listing.is_deleted and listing.status in ("active", "partially_fulfilled"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Listing is already active and not deleted",
                )
            expires_at = (
                listing.expires_at.replace(tzinfo=timezone.utc)
                if listing.expires_at.tzinfo is None
                else listing.expires_at
            )
            if expires_at <= now_utc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot restore expired listing (expired at {listing.expires_at.isoformat()})",
                )
            if listing.available_quantity <= Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot restore listing with zero available inventory",
                )

            listing.is_deleted = False
            listing.deleted_at = None
            # Preserve partially fulfilled semantics
            if listing.available_quantity < listing.initial_quantity:
                listing.status = "partially_fulfilled"
            else:
                listing.status = "active"
            listing.updated_at = now_utc

        # Record audit log
        audit = AdminAuditLog(
            admin_user_id=current_admin.id,
            action=f"listing_moderate_{action}",
            target_entity_type="listing",
            target_entity_id=listing.id,
            reason=f"Action '{action}' applied. Reason: {payload.reason.strip()}",
            ip_address=ip_address,
        )
        self.db.add(audit)
        self.db.flush()

        # Send notification to farmer
        notif = Notification(
            user_id=listing.farmer_id,
            event_type="listing_moderation_action",
            title=f"Produce Listing Moderation: {action.title()}",
            body=(
                f"Your produce listing '{listing.product_name}' was moderated with action '{action}'. "
                f"Reason: {payload.reason.strip()}"
            ),
            is_read=False,
        )
        self.db.add(notif)

        self.db.commit()
        self.db.refresh(listing)

        reports_cnt = self.catalog_repo.get_listing_reports_count(listing.id)
        summary = self.listing_to_summary(listing, reports_cnt)

        return AdminListingModerateResponse(
            listing=summary,
            action=action,
            previous_status=prev_status,
            new_status=listing.status,
            is_deleted=listing.is_deleted,
            audit_log_id=audit.id,
            reason=payload.reason.strip(),
            updated_at=now_utc,
        )

    # -----------------------------------------------------------------------
    # Requirement Moderation
    # -----------------------------------------------------------------------

    @staticmethod
    def requirement_to_summary(req: BuyerRequirement, reports_count: int) -> AdminRequirementSummaryRead:
        b = req.buyer
        buyer_name = "Buyer"
        if b:
            buyer_name = (
                b.buyer_profile.contact_person_name
                if b.buyer_profile and b.buyer_profile.contact_person_name
                else (b.email.split("@")[0])
            )

        cat_name = req.category.name if req.category else None

        return AdminRequirementSummaryRead(
            id=req.id,
            buyer_id=req.buyer_id,
            buyer_email=b.email if b else "unknown",
            buyer_name=buyer_name,
            product_name=req.product_name,
            title=req.title,
            category_id=req.category_id,
            category_name=cat_name,
            required_quantity=req.required_quantity,
            remaining_quantity=req.remaining_quantity,
            unit=req.unit,
            target_price_per_unit=req.target_price_per_unit,
            price_condition=req.price_condition,
            required_by_date=req.required_by_date,
            status=req.status,
            is_deleted=req.is_deleted,
            deleted_at=req.deleted_at,
            reports_count=reports_count,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    def list_requirements(
        self,
        current_admin: User,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        buyer_id: Optional[uuid.UUID] = None,
        is_deleted: Optional[bool] = None,
        has_reports: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> AdminRequirementListResponse:
        """Query and paginate buyer requirements for moderation."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        if sort_by not in ("created_at", "product_name", "required_by_date", "status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field '{sort_by}'",
            )
        if sort_order not in ("asc", "desc"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_order '{sort_order}'",
            )

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.catalog_repo.list_requirements(
            search=search,
            status=status_filter,
            category_id=category_id,
            buyer_id=buyer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
            skip=skip,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total = self.catalog_repo.count_requirements(
            search=search,
            status=status_filter,
            category_id=category_id,
            buyer_id=buyer_id,
            is_deleted=is_deleted,
            has_reports=has_reports,
        )

        summaries = [self.requirement_to_summary(r, cnt) for r, cnt in items]
        return AdminRequirementListResponse.create(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    def moderate_requirement(
        self,
        req_id: uuid.UUID,
        current_admin: User,
        payload: AdminRequirementModerateRequest,
        ip_address: Optional[str] = None,
    ) -> AdminRequirementModerateResponse:
        """Apply close, remove, or restore moderation action to a buyer requirement."""
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires administrator privileges",
            )

        # Acquire row lock
        req = self.catalog_repo.get_requirement_by_id_for_update(req_id)
        if req is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Buyer requirement '{req_id}' not found",
            )

        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()
        prev_status = req.status
        action = payload.action

        if action == "close":
            if req.status == "closed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Buyer requirement is already closed",
                )
            req.status = "closed"
            req.updated_at = now_utc

        elif action == "remove":
            if req.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Buyer requirement is already removed (soft-deleted)",
                )
            req.status = "closed"
            req.is_deleted = True
            req.deleted_at = now_utc
            req.updated_at = now_utc

        elif action == "restore":
            if not req.is_deleted and req.status in ("active", "partially_fulfilled"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Buyer requirement is already active and not deleted",
                )
            if req.required_by_date < today:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot restore requirement past required_by_date ({req.required_by_date.isoformat()})",
                )
            if req.remaining_quantity <= Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot restore requirement with zero remaining quantity",
                )

            req.is_deleted = False
            req.deleted_at = None
            if req.remaining_quantity < req.required_quantity:
                req.status = "partially_fulfilled"
            else:
                req.status = "active"
            req.updated_at = now_utc

        # Record audit log
        audit = AdminAuditLog(
            admin_user_id=current_admin.id,
            action=f"requirement_moderate_{action}",
            target_entity_type="requirement",
            target_entity_id=req.id,
            reason=f"Action '{action}' applied. Reason: {payload.reason.strip()}",
            ip_address=ip_address,
        )
        self.db.add(audit)
        self.db.flush()

        # Send notification to buyer
        notif = Notification(
            user_id=req.buyer_id,
            event_type="requirement_moderation_action",
            title=f"Buyer Requirement Moderation: {action.title()}",
            body=(
                f"Your buyer requirement '{req.product_name}' was moderated with action '{action}'. "
                f"Reason: {payload.reason.strip()}"
            ),
            is_read=False,
        )
        self.db.add(notif)

        self.db.commit()
        self.db.refresh(req)

        reports_cnt = self.catalog_repo.get_requirement_reports_count(req.buyer_id)
        summary = self.requirement_to_summary(req, reports_cnt)

        return AdminRequirementModerateResponse(
            requirement=summary,
            action=action,
            previous_status=prev_status,
            new_status=req.status,
            is_deleted=req.is_deleted,
            audit_log_id=audit.id,
            reason=payload.reason.strip(),
            updated_at=now_utc,
        )
