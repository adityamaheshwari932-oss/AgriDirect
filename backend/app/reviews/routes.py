"""FastAPI route handlers for ratings and reviews.

Implements Module 7 / Part A endpoints under /api/v1/reviews:
- ``POST /api/v1/reviews``: Submit a review on an eligible completed order
- ``GET /api/v1/reviews/{id}`: Retrieve an individual review
- ``GET /api/v1/reviews/users/{user_id}``: Paginated reviews received by a user
- ``GET /api/v1/reviews/users/{user_id}/summary``: User reputation summary and rating distribution
- ``GET /api/v1/reviews/orders/{order_id}``: Reviews associated with a specific completed order
"""

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.reviews.schemas import (
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    UserReputationSummaryResponse,
)
from app.reviews.service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a mutual rating and review",
    description=(
        "Submits a rating and optional written testimonial for a completed order. "
        "The caller must be an active, verified participant (buyer or farmer) of the order. "
        "Each participant may submit at most one review per order."
    ),
)
def submit_review(
    review_in: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    """Submit a mutual review on an eligible completed order."""
    service = ReviewService(db)
    review = service.submit_review(current_user=current_user, review_in=review_in)
    return ReviewResponse.model_validate(review)


@router.get(
    "/{id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual review",
    description="Fetches an individual rating and review by its primary key.",
)
def get_review(
    id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ReviewResponse:
    """Retrieve a single review by ID."""
    service = ReviewService(db)
    review = service.get_review(review_id=id)
    return ReviewResponse.model_validate(review)


@router.get(
    "/users/{user_id}",
    response_model=ReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reviews received by a user",
    description="Returns a paginated list of reviews received by a target user, newest first.",
)
def list_user_reviews(
    user_id: uuid.UUID,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    db: Session = Depends(get_db),
) -> ReviewListResponse:
    """List reviews received by a user."""
    service = ReviewService(db)
    return service.list_user_reviews(user_id=user_id, page=page, page_size=page_size)


@router.get(
    "/users/{user_id}/summary",
    response_model=UserReputationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user reputation summary",
    description=(
        "Calculates aggregated reputation metrics for a target user including "
        "average rating, criterion breakdowns, and star rating distribution."
    ),
)
def get_user_reputation_summary(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> UserReputationSummaryResponse:
    """Calculate aggregate reputation statistics for a user."""
    service = ReviewService(db)
    return service.get_user_reputation(user_id=user_id)


@router.get(
    "/orders/{order_id}",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Get reviews for a completed order",
    description=(
        "Returns all reviews submitted for a specific order. "
        "Restricted to participants of the order and platform administrators."
    ),
)
def get_order_reviews(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[ReviewResponse]:
    """Retrieve all reviews attached to an order."""
    service = ReviewService(db)
    reviews = service.get_order_reviews(order_id=order_id, current_user=current_user)
    return [ReviewResponse.model_validate(r) for r in reviews]

