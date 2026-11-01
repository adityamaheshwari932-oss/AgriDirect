"""Service layer implementing mutual ratings, reviews, and reputation aggregation.

Enforces:
- Strict authorization: Only active, verified participants in a completed order can review
- Counterparty derivation: Reviewer must review their designated counterparty (buyer -> farmer or farmer -> buyer)
- Anti-enumeration: Inaccessible order or review returns 404
- Idempotency & Duplicate prevention: Exactly one active review per reviewer per order
- Invariant BR-17: Ratings are restricted to completed orders (ORDER_STATUS_COMPLETED)
- Operational alerts: Notification generated upon review receipt
"""

import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import NOTIFICATION_REF_ORDER
from app.models.order import ORDER_STATUS_COMPLETED, Order
from app.models.review import RatingReview
from app.models.user import User
from app.notifications.service import NotificationService
from app.reviews.repository import ReviewRepository
from app.reviews.schemas import (
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    UserReputationSummaryResponse,
)


class ReviewService:
    """Orchestrates rating and review workflows and validations."""

    def __init__(
        self,
        db: Session,
        repository: Optional[ReviewRepository] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.db = db
        self.repo = repository or ReviewRepository(db)
        self.notification_service = notification_service or NotificationService(db)

    def submit_review(
        self,
        current_user: User,
        review_in: ReviewCreate,
    ) -> RatingReview:
        """Submit a mutual rating and review on an eligible completed transaction.

        Args:
            current_user: Authenticated caller submitting the review.
            review_in: Validated review input schema.

        Returns:
            The committed RatingReview instance.

        Raises:
            HTTPException 403: If caller is unverified or suspended.
            HTTPException 404: If order does not exist or caller is not a participant.
            HTTPException 400: If self-review is attempted.
            HTTPException 409: If order is not completed or review already exists.
        """
        # 1. Verification and active status checks
        if current_user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive or suspended accounts cannot submit reviews",
            )
        if current_user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account must be verified to submit ratings and reviews",
            )

        # 2. Fetch order with anti-enumeration protection
        order = self.db.query(Order).filter(Order.id == review_in.order_id).first()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{review_in.order_id}' not found",
            )

        # Anti-enumeration: Only actual order participants can access
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{review_in.order_id}' not found",
            )

        # Administrators cannot submit a review on behalf of participants
        if current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only actual order participants can submit a review",
            )

        # 3. Eligibility check (BR-17: eligible completed transaction)
        if order.status != ORDER_STATUS_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ratings are only permitted for completed orders. Current order status: '{order.status}'",
            )

        # 4. Determine counterparty
        if current_user.id == order.buyer_id:
            reviewed_user_id = order.farmer_id
        else:
            reviewed_user_id = order.buyer_id

        # 5. Prevent self-review
        if current_user.id == reviewed_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review yourself",
            )

        # 6. Duplicate review prevention (one review per reviewer per order)
        existing = self.repo.get_by_order_and_reviewer(
            order_id=review_in.order_id,
            reviewer_id=current_user.id,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A review has already been submitted by you for this order",
            )

        # 7. Create review record
        review = self.repo.create(
            review_in=review_in,
            reviewer_id=current_user.id,
            reviewed_user_id=reviewed_user_id,
        )

        # 8. Notify reviewed counterparty
        reviewer_role = "Buyer" if current_user.id == order.buyer_id else "Farmer"
        self.notification_service.create_notification(
            user_id=reviewed_user_id,
            event_type="review_received",
            title=f"New Review on Order {order.order_number}",
            body=(
                f"{reviewer_role} submitted a {review.overall_rating}-star review "
                f"for Order {order.order_number}."
            ),
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=order.id,
        )

        self.db.commit()
        self.db.refresh(review)
        return review

    def get_review(self, review_id: uuid.UUID) -> RatingReview:
        """Fetch an individual review by primary key."""
        review = self.repo.get_by_id(review_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review '{review_id}' not found",
            )
        return review

    def list_user_reviews(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> ReviewListResponse:
        """Retrieve paginated public reviews received by a user."""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.repo.list_for_user(reviewed_user_id=user_id, skip=skip, limit=page_size)
        total = self.repo.count_for_user(reviewed_user_id=user_id)

        items_resp = [ReviewResponse.model_validate(item) for item in items]
        return ReviewListResponse.create(
            items=items_resp,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_order_reviews(
        self,
        order_id: uuid.UUID,
        current_user: User,
    ) -> List[RatingReview]:
        """Fetch all reviews associated with a specific order (participant or admin only)."""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )
        if current_user.role != "admin" and current_user.id not in (order.buyer_id, order.farmer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )
        return self.repo.list_for_order(order_id)

    def get_user_reputation(self, user_id: uuid.UUID) -> UserReputationSummaryResponse:
        """Calculate and return aggregate reputation statistics for a user."""
        target_user = self.db.query(User).filter(User.id == user_id).first()
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )
        summary = self.repo.get_user_reputation_summary(user_id)
        return UserReputationSummaryResponse(**summary)
