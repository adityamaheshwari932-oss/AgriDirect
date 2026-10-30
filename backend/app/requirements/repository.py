"""Database repository layer for buyer procurement requirements.

Implements synchronous SQLAlchemy queries, filtering, sorting, pagination, and persistence.
Adheres to ADR-002: Synchronous Session via Psycopg 3, parameterised queries, no raw SQL.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.listing import ProduceCategory
from app.models.requirement_approval import (
    APPROVAL_STATUS_PENDING,
    RequirementFulfillmentApproval,
)
from app.models.user import User
from app.requirements.models import (
    REQUIREMENT_STATUS_ACTIVE,
    REQUIREMENT_STATUS_CLOSED,
    REQUIREMENT_STATUS_PARTIALLY_FULFILLED,
    BuyerRequirement,
)


class RequirementRepository:
    """Manages database operations for buyer procurement requirements."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Categories (Reference Lookup)
    # -----------------------------------------------------------------------

    def get_category_by_id(self, category_id: uuid.UUID) -> Optional[ProduceCategory]:
        """Retrieve a produce category by UUID."""
        return self.db.query(ProduceCategory).filter(ProduceCategory.id == category_id).first()

    # -----------------------------------------------------------------------
    # Buyer Requirements CRUD
    # -----------------------------------------------------------------------

    def create_requirement(self, requirement_data: Dict[str, Any]) -> BuyerRequirement:
        """Create and persist a new buyer requirement."""
        requirement = BuyerRequirement(**requirement_data)
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def get_requirement_by_id(
        self,
        requirement_id: uuid.UUID,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Optional[BuyerRequirement]:
        """Retrieve a requirement by UUID with attached category and buyer profile."""
        query = (
            self.db.query(BuyerRequirement)
            .options(
                joinedload(BuyerRequirement.category),
                joinedload(BuyerRequirement.buyer).joinedload(User.buyer_profile),
            )
            .filter(BuyerRequirement.id == requirement_id)
        )
        if not include_deleted:
            query = query.filter(BuyerRequirement.is_deleted.is_(False))
        if for_update:
            query = query.with_for_update(of=BuyerRequirement).populate_existing()
        return query.first()

    def list_buyer_requirements(
        self,
        buyer_id: uuid.UUID,
        status_filter: Optional[str] = None,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[BuyerRequirement], int]:
        """Retrieve paginated requirements belonging to a specific commercial buyer.

        Args:
            buyer_id: UUID of the posting buyer.
            status_filter: Optional lifecycle status filter.
            include_deleted: Whether to include soft-deleted requirements.
            page: 1-indexed page number.
            page_size: Number of items per page.

        Returns:
            Tuple of (list_of_requirements, total_count).
        """
        query = self.db.query(BuyerRequirement).filter(BuyerRequirement.buyer_id == buyer_id)

        if not include_deleted:
            query = query.filter(BuyerRequirement.is_deleted.is_(False))

        if status_filter:
            query = query.filter(BuyerRequirement.status == status_filter)

        total_count = query.count()

        offset = (page - 1) * page_size
        requirements = (
            query.options(
                joinedload(BuyerRequirement.category),
                joinedload(BuyerRequirement.buyer).joinedload(User.buyer_profile),
            )
            .order_by(BuyerRequirement.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return requirements, total_count

    def search_public_requirements(
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
    ) -> Tuple[List[BuyerRequirement], int]:
        """Search and filter publicly visible active buyer requirements.

        Enforces mandatory public visibility constraints:
        - is_deleted == False
        - status in ('active', 'partially_fulfilled')
        - remaining_quantity > 0
        - required_by_date >= today
        - buyer account_status == 'active'
        - buyer verification_status == 'verified'
        """
        today = date.today()
        query = (
            self.db.query(BuyerRequirement)
            .join(BuyerRequirement.buyer)
            .filter(
                BuyerRequirement.is_deleted.is_(False),
                BuyerRequirement.status.in_([REQUIREMENT_STATUS_ACTIVE, REQUIREMENT_STATUS_PARTIALLY_FULFILLED]),
                BuyerRequirement.remaining_quantity > 0,
                BuyerRequirement.required_by_date >= today,
                User.account_status == "active",
                User.verification_status == "verified",
            )
        )

        # Optional filters
        if category_id:
            query = query.filter(BuyerRequirement.category_id == category_id)

        if category_slug:
            query = query.join(BuyerRequirement.category).filter(ProduceCategory.slug == category_slug)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.filter(
                (BuyerRequirement.product_name.ilike(pattern))
                | (BuyerRequirement.title.ilike(pattern))
                | (BuyerRequirement.description.ilike(pattern))
            )

        if product_name:
            query = query.filter(BuyerRequirement.product_name.ilike(f"%{product_name.strip()}%"))

        if destination_state:
            query = query.filter(BuyerRequirement.destination_state.ilike(f"%{destination_state.strip()}%"))

        if destination_city:
            query = query.filter(BuyerRequirement.destination_city.ilike(f"%{destination_city.strip()}%"))

        if min_price is not None:
            query = query.filter(BuyerRequirement.target_price_per_unit >= min_price)

        if max_price is not None:
            query = query.filter(BuyerRequirement.target_price_per_unit <= max_price)

        if min_quantity is not None:
            query = query.filter(BuyerRequirement.remaining_quantity >= min_quantity)

        if max_quantity is not None:
            query = query.filter(BuyerRequirement.remaining_quantity <= max_quantity)

        if unit:
            query = query.filter(BuyerRequirement.unit == unit.strip())

        if quality_grade:
            query = query.filter(BuyerRequirement.quality_grade.ilike(f"%{quality_grade.strip()}%"))

        if price_condition:
            query = query.filter(BuyerRequirement.price_condition == price_condition.strip().lower())

        if buyer_id:
            query = query.filter(BuyerRequirement.buyer_id == buyer_id)

        total_count = query.count()

        # Deterministic sorting
        sort_col = getattr(BuyerRequirement, sort_by, BuyerRequirement.created_at)
        if sort_order.lower() == "asc":
            order_expression = sort_col.asc()
        else:
            order_expression = sort_col.desc()

        offset = (page - 1) * page_size
        requirements = (
            query.options(
                joinedload(BuyerRequirement.category),
                joinedload(BuyerRequirement.buyer).joinedload(User.buyer_profile),
            )
            .order_by(order_expression, BuyerRequirement.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return requirements, total_count

    def update_requirement(self, requirement: BuyerRequirement, data: Dict[str, Any]) -> BuyerRequirement:
        """Update fields on a buyer requirement."""
        for key, value in data.items():
            setattr(requirement, key, value)
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def soft_delete_requirement(self, requirement: BuyerRequirement) -> BuyerRequirement:
        """Mark a requirement as soft deleted and set status to closed."""
        requirement.is_deleted = True
        requirement.deleted_at = datetime.now(timezone.utc)
        requirement.status = REQUIREMENT_STATUS_CLOSED
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    # -----------------------------------------------------------------------
    # Requirement Fulfillment Approvals (ADR-003)
    # -----------------------------------------------------------------------

    def lock_requirements(self, requirement_ids: List[uuid.UUID]) -> Dict[uuid.UUID, BuyerRequirement]:
        """Acquire row-level locks on buyer requirements in ascending UUID order to minimize deadlocks."""
        if not requirement_ids:
            return {}
        sorted_ids = sorted(list(set(requirement_ids)))
        stmt = (
            self.db.query(BuyerRequirement)
            .filter(BuyerRequirement.id.in_(sorted_ids))
            .order_by(BuyerRequirement.id.asc())
            .with_for_update()
        )
        results = stmt.all()
        return {r.id: r for r in results}

    def get_approval_by_id(
        self,
        approval_id: uuid.UUID,
        for_update: bool = False,
    ) -> Optional[RequirementFulfillmentApproval]:
        """Retrieve a fulfillment approval by UUID with eager loaded requirement and order."""
        query = (
            self.db.query(RequirementFulfillmentApproval)
            .options(
                joinedload(RequirementFulfillmentApproval.requirement),
                joinedload(RequirementFulfillmentApproval.order),
                joinedload(RequirementFulfillmentApproval.order_item),
            )
            .filter(RequirementFulfillmentApproval.id == approval_id)
        )
        if for_update:
            query = query.with_for_update(of=RequirementFulfillmentApproval).populate_existing()
        return query.first()

    def get_approval_by_order_item_id(
        self,
        order_item_id: uuid.UUID,
    ) -> Optional[RequirementFulfillmentApproval]:
        """Retrieve a fulfillment approval by its unique order item ID."""
        return (
            self.db.query(RequirementFulfillmentApproval)
            .filter(RequirementFulfillmentApproval.order_item_id == order_item_id)
            .first()
        )

    def list_approvals_for_buyer(
        self,
        buyer_id: uuid.UUID,
        status_filter: Optional[str] = None,
        requirement_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[RequirementFulfillmentApproval], int]:
        """List fulfillment approvals for requirements owned by the specified buyer."""
        query = (
            self.db.query(RequirementFulfillmentApproval)
            .join(BuyerRequirement, RequirementFulfillmentApproval.requirement_id == BuyerRequirement.id)
            .options(
                joinedload(RequirementFulfillmentApproval.requirement),
                joinedload(RequirementFulfillmentApproval.order),
                joinedload(RequirementFulfillmentApproval.order_item),
            )
            .filter(BuyerRequirement.buyer_id == buyer_id)
        )

        if status_filter:
            query = query.filter(RequirementFulfillmentApproval.status == status_filter)

        if requirement_id:
            query = query.filter(RequirementFulfillmentApproval.requirement_id == requirement_id)

        total = query.count()
        offset = (page - 1) * page_size
        items = (
            query.order_by(RequirementFulfillmentApproval.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return items, total

    def create_approval(self, approval_data: Dict[str, Any]) -> RequirementFulfillmentApproval:
        """Create and persist a new requirement fulfillment approval record."""
        approval = RequirementFulfillmentApproval(**approval_data)
        self.db.add(approval)
        self.db.flush()
        return approval
    def update_approval(
        self,
        approval: RequirementFulfillmentApproval,
        data: Dict[str, Any],
    ) -> RequirementFulfillmentApproval:
        """Update fields on a fulfillment approval record."""
        for key, value in data.items():
            setattr(approval, key, value)
        self.db.flush()
        return approval

