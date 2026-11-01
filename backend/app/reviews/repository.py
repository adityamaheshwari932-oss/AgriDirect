"""Repository layer for mutual transaction ratings and reviews.

Provides database access to the ``ratings_reviews`` table:
- Atomic review insertion
- Scoped lookups by ID, order, and reviewer
- Paginated retrieval of reviews received by a user
- SQL-level aggregation for user reputation statistics and distribution
"""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.review import RatingReview
from app.reviews.schemas import ReviewCreate


class ReviewRepository:
    """Encapsulates all database interactions for the RatingReview model."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        review_in: ReviewCreate,
        reviewer_id: uuid.UUID,
        reviewed_user_id: uuid.UUID,
    ) -> RatingReview:
        """Insert a new mutual rating and review record.

        Args:
            review_in: Validated review input schema.
            reviewer_id: User ID of the participant submitting the review.
            reviewed_user_id: User ID of the counterparty being reviewed.

        Returns:
            The created RatingReview model instance (not yet committed).
        """
        review = RatingReview(
            order_id=review_in.order_id,
            reviewer_id=reviewer_id,
            reviewed_user_id=reviewed_user_id,
            overall_rating=review_in.overall_rating,
            quality_rating=review_in.quality_rating,
            accuracy_rating=review_in.accuracy_rating,
            communication_rating=review_in.communication_rating,
            reliability_rating=review_in.reliability_rating,
            review_text=review_in.review_text.strip() if review_in.review_text else None,
        )
        self.db.add(review)
        self.db.flush()
        return review

    def get_by_id(self, review_id: uuid.UUID) -> Optional[RatingReview]:
        """Fetch a single review by primary key."""
        stmt = select(RatingReview).where(RatingReview.id == review_id)
        return self.db.scalars(stmt).first()

    def get_by_order_and_reviewer(
        self,
        order_id: uuid.UUID,
        reviewer_id: uuid.UUID,
    ) -> Optional[RatingReview]:
        """Check if a reviewer has already reviewed a specific order."""
        stmt = select(RatingReview).where(
            RatingReview.order_id == order_id,
            RatingReview.reviewer_id == reviewer_id,
        )
        return self.db.scalars(stmt).first()

    def list_for_user(
        self,
        reviewed_user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[RatingReview]:
        """Retrieve paginated reviews received by a specific user, newest first."""
        stmt = (
            select(RatingReview)
            .where(RatingReview.reviewed_user_id == reviewed_user_id)
            .order_by(RatingReview.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def count_for_user(self, reviewed_user_id: uuid.UUID) -> int:
        """Count total reviews received by a specific user."""
        stmt = select(func.count(RatingReview.id)).where(
            RatingReview.reviewed_user_id == reviewed_user_id
        )
        return self.db.scalar(stmt) or 0

    def list_for_order(self, order_id: uuid.UUID) -> List[RatingReview]:
        """Fetch all reviews associated with a specific order."""
        stmt = (
            select(RatingReview)
            .where(RatingReview.order_id == order_id)
            .order_by(RatingReview.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_user_reputation_summary(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Calculate aggregate reputation statistics using SQL aggregation functions.

        Performs a single efficient query over indexed columns to compute:
        - Total reviews count
        - Average overall rating
        - Average criterion scores (quality, accuracy, communication, reliability)
        - Star rating distribution (1 to 5)
        """
        stmt = select(
            func.count(RatingReview.id).label("total_reviews"),
            func.avg(RatingReview.overall_rating).label("avg_overall"),
            func.avg(RatingReview.quality_rating).label("avg_quality"),
            func.avg(RatingReview.accuracy_rating).label("avg_accuracy"),
            func.avg(RatingReview.communication_rating).label("avg_communication"),
            func.avg(RatingReview.reliability_rating).label("avg_reliability"),
            func.sum(case((RatingReview.overall_rating == 1, 1), else_=0)).label("star_1"),
            func.sum(case((RatingReview.overall_rating == 2, 1), else_=0)).label("star_2"),
            func.sum(case((RatingReview.overall_rating == 3, 1), else_=0)).label("star_3"),
            func.sum(case((RatingReview.overall_rating == 4, 1), else_=0)).label("star_4"),
            func.sum(case((RatingReview.overall_rating == 5, 1), else_=0)).label("star_5"),
        ).where(RatingReview.reviewed_user_id == user_id)

        row = self.db.execute(stmt).first()

        if not row or row.total_reviews == 0:
            return {
                "user_id": user_id,
                "total_reviews": 0,
                "average_rating": 0.0,
                "quality_rating_avg": None,
                "accuracy_rating_avg": None,
                "communication_rating_avg": None,
                "reliability_rating_avg": None,
                "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            }

        avg_overall = round(float(row.avg_overall), 2) if row.avg_overall is not None else 0.0
        avg_quality = round(float(row.avg_quality), 2) if row.avg_quality is not None else None
        avg_accuracy = round(float(row.avg_accuracy), 2) if row.avg_accuracy is not None else None
        avg_comm = round(float(row.avg_communication), 2) if row.avg_communication is not None else None
        avg_rel = round(float(row.avg_reliability), 2) if row.avg_reliability is not None else None

        return {
            "user_id": user_id,
            "total_reviews": int(row.total_reviews),
            "average_rating": avg_overall,
            "quality_rating_avg": avg_quality,
            "accuracy_rating_avg": avg_accuracy,
            "communication_rating_avg": avg_comm,
            "reliability_rating_avg": avg_rel,
            "rating_distribution": {
                "1": int(row.star_1 or 0),
                "2": int(row.star_2 or 0),
                "3": int(row.star_3 or 0),
                "4": int(row.star_4 or 0),
                "5": int(row.star_5 or 0),
            },
        }

