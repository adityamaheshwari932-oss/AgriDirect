"""FastAPI route handlers for AgriDirect Module 9: Descriptive Market Analytics.

Versioned under /api/v1/analytics/ and /api/v1/admin/analytics/:
1. GET /api/v1/analytics/market-summary (Public / Optional Auth)
2. GET /api/v1/analytics/demand-summary (Public / Optional Auth)
3. GET /api/v1/analytics/my-performance (Authenticated Farmer / Buyer)
4. GET /api/v1/analytics/admin/platform (Admin Only)
5. GET /api/v1/admin/analytics/platform (Admin Only alias)
"""

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analytics.dependencies import get_read_only_db
from app.analytics.schemas import (
    DemandSummaryResponse,
    MarketSummaryResponse,
    MyPerformanceResponse,
    PlatformAnalyticsResponse,
)
from app.analytics.service import AnalyticsService
from app.dependencies import get_current_active_user, require_admin
from app.models.user import User

router = APIRouter(tags=["analytics"])


@router.get(
    "/analytics/market-summary",
    response_model=MarketSummaryResponse,
    summary="Descriptive marketplace supply and completed trade summary",
    description=(
        "Returns unit-safe, privacy-preserving aggregate metrics for active listings "
        "and realized trades from completed orders. Strict diversity (k>=3) and "
        "dominance suppression (>=50%) apply. Payment settlement totals are excluded."
    ),
)
def get_market_summary(
    product_name: Optional[str] = Query(None, description="Filter by crop/commodity name"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by produce category ID"),
    state: Optional[str] = Query(None, description="Geographic state filter"),
    city: Optional[str] = Query(None, description="Geographic city filter"),
    unit: Optional[str] = Query(None, description="Produce measurement unit (e.g. kg, quintal)"),
    start_date: Optional[date] = Query(None, description="Filter start date (inclusive, YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter end date (inclusive, YYYY-MM-DD)"),
    db: Session = Depends(get_read_only_db),
) -> MarketSummaryResponse:
    """Retrieve descriptive market summary."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date.",
        )

    return AnalyticsService.get_market_summary(
        db,
        product_name=product_name,
        category_id=category_id,
        state=state,
        city=city,
        unit=unit,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/analytics/demand-summary",
    response_model=DemandSummaryResponse,
    summary="Descriptive open demand and audited fulfillment accounting summary",
    description=(
        "Returns active buyer procurement demands and audited approved fulfillment volume. "
        "Approved fulfillment is permanently retained regardless of parent requirement closure "
        "or soft deletion."
    ),
)
def get_demand_summary(
    product_name: Optional[str] = Query(None, description="Filter by commodity name"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by produce category ID"),
    state: Optional[str] = Query(None, description="Geographic destination state"),
    city: Optional[str] = Query(None, description="Geographic destination city"),
    unit: Optional[str] = Query(None, description="Produce measurement unit"),
    start_date: Optional[date] = Query(None, description="Filter start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter end date (inclusive)"),
    db: Session = Depends(get_read_only_db),
) -> DemandSummaryResponse:
    """Retrieve descriptive demand summary."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date.",
        )

    return AnalyticsService.get_demand_summary(
        db,
        product_name=product_name,
        category_id=category_id,
        state=state,
        city=city,
        unit=unit,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/analytics/my-performance",
    response_model=MyPerformanceResponse,
    summary="Role-specialized personal trade and settlement dashboard",
    description=(
        "Returns individual order outcome execution rates (with non-pending denominator), "
        "realized sales/purchase volumes, commodity breakdown, and payment settlement metrics."
    ),
)
def get_my_performance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_read_only_db),
) -> MyPerformanceResponse:
    """Retrieve personal performance report for active farmer or buyer."""
    if current_user.role not in ("farmer", "buyer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Performance analytics is only available for farmer or buyer accounts.",
        )

    return AnalyticsService.get_user_performance(
        db,
        user_id=current_user.id,
        role=current_user.role,
    )


@router.get(
    "/analytics/admin/platform",
    response_model=PlatformAnalyticsResponse,
    summary="Platform-wide descriptive market metrics (Administrator only)",
    description=(
        "Returns complete unsuppressed marketplace statistics including platform GMV, "
        "pipeline GMV, active supply inventory, demand fulfillment ledger, order lifecycle "
        "breakdown, external payment settlement velocity, and user composition."
    ),
)
def get_platform_analytics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_read_only_db),
) -> PlatformAnalyticsResponse:
    """Retrieve platform-wide operational and market analytics."""
    return AnalyticsService.get_platform_analytics(db)


@router.get(
    "/admin/analytics/platform",
    response_model=PlatformAnalyticsResponse,
    include_in_schema=False,
    summary="Platform analytics alias under /admin/ path",
)
def get_platform_analytics_alias(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_read_only_db),
) -> PlatformAnalyticsResponse:
    """Administrative alias for platform analytics."""
    return AnalyticsService.get_platform_analytics(db)

