"""Pydantic v2 schemas for ratings, reviews, and reputation aggregation.

Implements Module 7 (Accountability & Operational Alerts / Part A — Ratings & Reviews):
- ``ReviewCreate``: Inbound payload for submitting a mutual counterparty review
- ``ReviewResponse``: Serialized representation of a rating and review
- ``ReviewListResponse``: Paginated collection of reviews
- ``UserReputationSummaryResponse``: Aggregated reputation statistics for a user
"""

import math
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    """Payload for submitting a review on an eligible completed transaction."""

    order_id: uuid.UUID = Field(
        ...,
        description="Primary key of the completed order being reviewed",
    )
    overall_rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Overall counterparty rating (1 to 5)",
    )
    quality_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Product quality rating (1 to 5, typically buyer rating farmer)",
    )
    accuracy_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Quantity match and description accuracy rating (1 to 5)",
    )
    communication_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Communication responsiveness and clarity rating (1 to 5)",
    )
    reliability_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Reliability and fulfillment timeliness rating (1 to 5)",
    )
    review_text: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional written testimonial or feedback narrative",
    )


class ReviewResponse(BaseModel):
    """Public serialized review entity."""

    id: uuid.UUID
    order_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewed_user_id: uuid.UUID
    overall_rating: int
    quality_rating: Optional[int] = None
    accuracy_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    reliability_rating: Optional[int] = None
    review_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """Paginated collection of reviews."""

    items: List[ReviewResponse]
    total: int = Field(..., ge=0, description="Total matching reviews")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages available")

    @classmethod
    def create(
        cls,
        items: List[ReviewResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "ReviewListResponse":
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class UserReputationSummaryResponse(BaseModel):
    """Aggregated counterparty reputation metrics calculated from verified reviews."""

    user_id: uuid.UUID
    total_reviews: int = Field(..., ge=0, description="Total verified reviews received")
    average_rating: float = Field(..., ge=0.0, le=5.0, description="Mean overall rating (rounded to 2 decimal places)")
    quality_rating_avg: Optional[float] = Field(None, description="Average quality score if rated")
    accuracy_rating_avg: Optional[float] = Field(None, description="Average accuracy score if rated")
    communication_rating_avg: Optional[float] = Field(None, description="Average communication score if rated")
    reliability_rating_avg: Optional[float] = Field(None, description="Average reliability score if rated")
    rating_distribution: Dict[str, int] = Field(
        ...,
        description="Count of reviews grouped by star rating: '1', '2', '3', '4', '5'",
    )

