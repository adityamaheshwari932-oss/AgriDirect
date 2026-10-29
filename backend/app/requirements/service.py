"""Service layer for buyer procurement requirements management.

Enforces business rules:
- Verified commercial buyer ownership and verification guards.
- Positive quantity and remaining quantity integrity (0 <= remaining <= required).
- Canonical lifecycle status state machine.
- Public marketplace demand visibility rules.
- Automatic buyer profile location defaults.
"""

import logging
import math
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.listing import ProduceCategory
from app.models.user import User
from app.requirements.models import (
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_DRAFT,
    REQUIREMENT_STATUS_EXPIRED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    VALID_REQUIREMENT_STATUSES,
    BuyerRequirement,
)
from app.requirements.repository import RequirementRepository
from app.requirements.schemas import (
    BuyerRequirementDetailResponse,
    BuyerRequirementListResponse,
    BuyerRequirementPublicListResponse,
    BuyerRequirementPublicSummary,
    BuyerSummary,
    CategoryResponse,
    RequirementCreate,
    RequirementStatusUpdate,
    RequirementUpdate,
)

# Permitted lifecycle state transitions (from_status -> allowed_target_statuses)
PERMITTED_STATUS_TRANSITIONS: Dict[str, set[str]] = {
    REQUIREMENT_STATUS_DRAFT: {REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_CLOSED},
    REQUIREMENT_STATUS_ACTIVE: {REQUIREMENT_STATUS_DRAFT, REQUIREMENT_STATUS_CLOSED},
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED: {REQUIREMENT_STATUS_CLOSED},
    REQUIREMENT_STATUS_CLOSED: {REQUIREMENT_STATUS_ACTIVE},  # Reopening active if quantity and deadline permit
    REQUIREMENT_STATUS_EXPIRED: {REQUIREMENT_STATUS_CLOSED},
}


def _ensure_date(val: Any) -> date:
    """Ensure value is a datetime.date object for portable comparisons."""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        return date.fromisoformat(val)
    return val


class RequirementService:
    """Orchestrates buyer requirement management and public demand catalog."""

    def __init__(self, db: Session) -> None:
        self.repository = RequirementRepository(db)

    # -----------------------------------------------------------------------
    # Buyer Requirement Management
    # -----------------------------------------------------------------------

    def create_requirement(
        self,
        user: User,
        payload: RequirementCreate,
    ) -> BuyerRequirementDetailResponse:
        """Create a buyer procurement requirement.

        Args:
            user: Authenticated active, verified buyer.
            payload: Validated requirement creation schema.

        Returns:
            Detailed requirement response.

        Raises:
            HTTPException: 403 if user is not a verified buyer.
            HTTPException: 422 if category is invalid/inactive or destination cannot be resolved.
        """
        self._require_verified_buyer(user)

        # Validate category reference if supplied
        if payload.category_id:
            category = self.repository.get_category_by_id(payload.category_id)
            if not category or not category.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Category with ID '{payload.category_id}' does not exist or is inactive",
                )

        # Resolve destination location defaults from buyer profile if omitted
        state = payload.destination_state
        city = payload.destination_city
        profile = getattr(user, "buyer_profile", None)

        if not state and profile:
            state = getattr(profile, "state", None)
        if not city and profile:
            city = getattr(profile, "city", None)

        if not state or not city:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Destination state and city are required. Please provide them or update your buyer profile.",
            )

        # On creation, remaining_quantity is server-initialized equal to required_quantity
        requirement_data = {
            "buyer_id": user.id,
            "category_id": payload.category_id,
            "product_name": payload.product_name,
            "title": payload.title,
            "description": payload.description,
            "required_quantity": payload.required_quantity,
            "remaining_quantity": payload.required_quantity,
            "unit": payload.unit,
            "target_price_per_unit": payload.target_price_per_unit,
            "price_condition": payload.price_condition,
            "quality_grade": payload.quality_grade,
            "destination_state": state,
            "destination_city": city,
            "required_by_date": payload.required_by_date,
            "status": payload.status or REQUIREMENT_STATUS_ACTIVE,
            "is_deleted": False,
        }

        try:
            requirement = self.repository.create_requirement(requirement_data)
        except Exception:
            self.repository.db.rollback()
            raise

        loaded = self.repository.get_requirement_by_id(requirement.id) or requirement
        return self._to_detail_response(loaded)

    def list_buyer_requirements(
        self,
        user: User,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> BuyerRequirementListResponse:
        """List procurement requirements owned by the authenticated buyer."""
        self._require_verified_buyer(user)

        if status_filter and status_filter not in VALID_REQUIREMENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid status filter '{status_filter}'. "
                    f"Must be one of: {', '.join(VALID_REQUIREMENT_STATUSES)}"
                ),
            )

        requirements, total = self.repository.list_buyer_requirements(
            buyer_id=user.id,
            status_filter=status_filter,
            include_deleted=False,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = [self._to_detail_response(req) for req in requirements]

        return BuyerRequirementListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_requirement_detail(
        self,
        requirement_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> BuyerRequirementDetailResponse:
        """Retrieve full details of a buyer requirement.

        If caller is the owner or administrator, returns full details regardless of status.
        If caller is public or unrelated user, returns details only if requirement is active
        or partially fulfilled, unexpired, has remaining quantity > 0, and buyer is in good standing.
        """
        req = self.repository.get_requirement_by_id(requirement_id, include_deleted=True)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Buyer requirement '{requirement_id}' not found",
            )

        is_owner = current_user is not None and (req.buyer_id == current_user.id)
        is_admin = current_user is not None and (current_user.role == "admin")

        if req.is_deleted and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Buyer requirement '{requirement_id}' not found",
            )

        if not (is_owner or is_admin):
            today = date.today()
            buyer = req.buyer
            buyer_active_and_verified = (
                buyer is not None
                and buyer.account_status == "active"
                and buyer.verification_status == "verified"
            )
            if (
                req.is_deleted
                or req.status not in (REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED)
                or req.remaining_quantity <= 0
                or _ensure_date(req.required_by_date) < today
                or not buyer_active_and_verified
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Buyer requirement '{requirement_id}' is not currently available",
                )

        return self._to_detail_response(req)

    def update_requirement(
        self,
        requirement_id: uuid.UUID,
        user: User,
        payload: RequirementUpdate,
    ) -> BuyerRequirementDetailResponse:
        """Update permitted fields on a requirement owned by the caller."""
        req = self._get_owned_requirement(requirement_id, user)

        data = payload.model_dump(exclude_unset=True)
        if not data:
            return self._to_detail_response(req)

        # Validate category if updating
        if "category_id" in data and data["category_id"] is not None:
            category = self.repository.get_category_by_id(data["category_id"])
            if not category or not category.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Category with ID '{data['category_id']}' does not exist or is inactive",
                )

        # Validate deadline if updating
        if "required_by_date" in data and data["required_by_date"] is not None:
            if data["required_by_date"] < date.today():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Procurement deadline date cannot be in the past",
                )

        # Quantity integrity preservation
        new_required = data.get("required_quantity", req.required_quantity)
        new_remaining = data.get("remaining_quantity")

        if new_remaining is not None:
            if new_remaining > new_required:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Remaining quantity ({new_remaining}) cannot exceed required quantity ({new_required})",
                )
        elif "required_quantity" in data and data["required_quantity"] is not None:
            # If required_quantity changed but remaining_quantity was omitted:
            if req.remaining_quantity == req.required_quantity:
                # Wholly unfilled requirement: remaining quantity tracks updated required quantity
                data["remaining_quantity"] = new_required
            else:
                # Partially fulfilled requirement: preserve fulfilled portion
                fulfilled_quantity = req.required_quantity - req.remaining_quantity
                if new_required < fulfilled_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Cannot reduce required quantity ({new_required}) below "
                            f"already fulfilled quantity ({fulfilled_quantity})"
                        ),
                    )
                data["remaining_quantity"] = new_required - fulfilled_quantity

        # Validate status transition if requested
        if "status" in data and data["status"] is not None:
            new_status = data["status"]
            effective_remaining = data.get("remaining_quantity", req.remaining_quantity)
            effective_deadline = data.get("required_by_date", req.required_by_date)
            self._validate_status_transition(
                req,
                new_status,
                effective_remaining_quantity=effective_remaining,
                effective_required_by_date=effective_deadline,
            )

        try:
            updated = self.repository.update_requirement(req, data)
        except Exception:
            self.repository.db.rollback()
            raise

        loaded = self.repository.get_requirement_by_id(updated.id) or updated
        return self._to_detail_response(loaded)

    def update_requirement_status(
        self,
        requirement_id: uuid.UUID,
        user: User,
        payload: RequirementStatusUpdate,
    ) -> BuyerRequirementDetailResponse:
        """Transition requirement lifecycle status."""
        req = self._get_owned_requirement(requirement_id, user)
        self._validate_status_transition(req, payload.status)

        try:
            updated = self.repository.update_requirement(req, {"status": payload.status})
        except Exception:
            self.repository.db.rollback()
            raise

        loaded = self.repository.get_requirement_by_id(updated.id) or updated
        return self._to_detail_response(loaded)

    def soft_delete_requirement(
        self,
        requirement_id: uuid.UUID,
        user: User,
    ) -> None:
        """Soft-delete a requirement owned by the caller (or by platform admin)."""
        req = self.repository.get_requirement_by_id(requirement_id, include_deleted=True)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Buyer requirement '{requirement_id}' not found",
            )

        if req.buyer_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this requirement",
            )

        if req.is_deleted:
            return

        try:
            self.repository.soft_delete_requirement(req)
        except Exception:
            self.repository.db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Marketplace Demand Catalog (Public)
    # -----------------------------------------------------------------------

    def search_marketplace(
        self,
        category_id: Optional[uuid.UUID] = None,
        category_slug: Optional[str] = None,
        search_query: Optional[str] = None,
        product_name: Optional[str] = None,
        destination_state: Optional[str] = None,
        destination_city: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        min_quantity: Optional[Decimal] = None,
        max_quantity: Optional[Decimal] = None,
        unit: Optional[str] = None,
        quality_grade: Optional[str] = None,
        price_condition: Optional[str] = None,
        buyer_id: Optional[uuid.UUID] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> BuyerRequirementPublicListResponse:
        """Search and filter public marketplace buyer requirements."""
        valid_sort_fields = {
            "created_at",
            "required_by_date",
            "required_quantity",
            "remaining_quantity",
            "target_price_per_unit",
            "product_name",
        }
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"

        if sort_order.lower() not in ("asc", "desc"):
            sort_order = "desc"

        requirements, total = self.repository.search_public_requirements(
            category_id=category_id,
            category_slug=category_slug,
            search_query=search_query,
            product_name=product_name,
            destination_state=destination_state,
            destination_city=destination_city,
            min_price=min_price,
            max_price=max_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            unit=unit,
            quality_grade=quality_grade,
            price_condition=price_condition,
            buyer_id=buyer_id,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = [self._to_public_summary(req) for req in requirements]

        return BuyerRequirementPublicListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # -----------------------------------------------------------------------
    # Helper & Validation Methods
    # -----------------------------------------------------------------------

    def _require_verified_buyer(self, user: User) -> None:
        """Enforce that caller is an active, verified commercial buyer."""
        if user.role != "buyer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a buyer account",
            )
        if user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a verified buyer account",
            )
        if user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended",
            )

    def _get_owned_requirement(self, requirement_id: uuid.UUID, user: User) -> BuyerRequirement:
        """Retrieve requirement ensuring caller is the buyer owner and it is not deleted."""
        self._require_verified_buyer(user)

        req = self.repository.get_requirement_by_id(requirement_id, include_deleted=True)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Buyer requirement '{requirement_id}' not found",
            )

        if req.buyer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access or modify this requirement",
            )

        if req.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a deleted requirement",
            )

        return req

    def _validate_status_transition(
        self,
        requirement: BuyerRequirement,
        new_status: str,
        effective_remaining_quantity: Optional[Decimal] = None,
        effective_required_by_date: Optional[date] = None,
    ) -> None:
        """Validate that a requested status transition is legally permitted."""
        current_status = requirement.status
        if current_status == new_status:
            return

        allowed = PERMITTED_STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from '{current_status}' to '{new_status}'. "
                    f"Permitted target statuses: {', '.join(sorted(allowed)) if allowed else 'none'}"
                ),
            )

        # When reopening to active from closed, ensure remaining quantity > 0 and deadline is today or future
        if new_status == REQUIREMENT_STATUS_ACTIVE:
            target_quantity = (
                effective_remaining_quantity
                if effective_remaining_quantity is not None
                else requirement.remaining_quantity
            )
            if target_quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot activate requirement with 0 remaining quantity",
                )

            target_date = (
                effective_required_by_date
                if effective_required_by_date is not None
                else requirement.required_by_date
            )
            today = date.today()
            if _ensure_date(target_date) < today:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot activate requirement that has already expired; please update required-by date first",
                )

    def _to_detail_response(self, req: BuyerRequirement) -> BuyerRequirementDetailResponse:
        """Map ORM BuyerRequirement model to BuyerRequirementDetailResponse."""
        category_resp = None
        if req.category:
            category_resp = CategoryResponse.model_validate(req.category)

        buyer_summary = None
        buyer_user = req.buyer
        if buyer_user:
            profile = getattr(buyer_user, "buyer_profile", None)
            buyer_summary = BuyerSummary(
                id=buyer_user.id,
                contact_person_name=getattr(profile, "contact_person_name", "Buyer"),
                business_name=getattr(profile, "business_name", "Enterprise"),
                business_type=getattr(profile, "business_type", "commercial"),
                city=getattr(profile, "city", req.destination_city),
                state=getattr(profile, "state", req.destination_state),
            )

        return BuyerRequirementDetailResponse(
            id=req.id,
            buyer_id=req.buyer_id,
            category_id=req.category_id,
            category=category_resp,
            product_name=req.product_name,
            title=req.title,
            description=req.description,
            required_quantity=req.required_quantity,
            remaining_quantity=req.remaining_quantity,
            unit=req.unit,
            target_price_per_unit=req.target_price_per_unit,
            price_condition=req.price_condition,
            quality_grade=req.quality_grade,
            destination_state=req.destination_state,
            destination_city=req.destination_city,
            required_by_date=req.required_by_date,
            status=req.status,
            is_deleted=req.is_deleted,
            created_at=req.created_at,
            updated_at=req.updated_at,
            buyer=buyer_summary,
        )

    def _to_public_summary(self, req: BuyerRequirement) -> BuyerRequirementPublicSummary:
        """Map ORM BuyerRequirement model to BuyerRequirementPublicSummary."""
        buyer_summary = None
        buyer_user = req.buyer
        if buyer_user:
            profile = getattr(buyer_user, "buyer_profile", None)
            buyer_summary = BuyerSummary(
                id=buyer_user.id,
                contact_person_name=getattr(profile, "contact_person_name", "Buyer"),
                business_name=getattr(profile, "business_name", "Enterprise"),
                business_type=getattr(profile, "business_type", "commercial"),
                city=getattr(profile, "city", req.destination_city),
                state=getattr(profile, "state", req.destination_state),
            )

        return BuyerRequirementPublicSummary(
            id=req.id,
            category_id=req.category_id,
            category_name=req.category.name if req.category else None,
            product_name=req.product_name,
            title=req.title,
            description=req.description,
            required_quantity=req.required_quantity,
            remaining_quantity=req.remaining_quantity,
            unit=req.unit,
            target_price_per_unit=req.target_price_per_unit,
            price_condition=req.price_condition,
            quality_grade=req.quality_grade,
            destination_state=req.destination_state,
            destination_city=req.destination_city,
            required_by_date=req.required_by_date,
            status=req.status,
            created_at=req.created_at,
            buyer=buyer_summary,
        )

