"""FastAPI route handlers for Structured Offers and Negotiation (Module 3).

Exposes RESTful endpoints under /api/v1/offers:
- POST   /api/v1/offers: Create initial structured proposal
- GET    /api/v1/offers: List sent and received offers
- GET    /api/v1/offers/{offer_id}: Retrieve detailed offer view
- GET    /api/v1/offers/{offer_id}/history: Retrieve negotiation lineage
- POST   /api/v1/offers/{offer_id}/counter: Create counter-proposal
- POST   /api/v1/offers/{offer_id}/accept: Accept offer & instantiate Order atomically
- POST   /api/v1/offers/{offer_id}/reject: Reject pending offer
- POST   /api/v1/offers/{offer_id}/withdraw: Withdraw own pending offer
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_verified_user
from app.models.user import User
from app.offers.schemas import (
    CounterOfferCreate,
    OfferAcceptRequest,
    OfferAcceptResponse,
    OfferCreate,
    OfferDetailResponse,
    OfferHistoryResponse,
    OfferListResponse,
    OfferRejectRequest,
)
from app.offers.service import OfferService

router = APIRouter(prefix="/offers", tags=["Offers & Negotiation"])


def get_offer_service(db: Session = Depends(get_db)) -> OfferService:
    """Dependency provider for OfferService."""
    return OfferService(db)


@router.post(
    "",
    response_model=OfferDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create structured offer",
    description="Submit an initial structured trade offer against a listing or requirement.",
)
def create_offer(
    payload: OfferCreate,
    current_user: User = Depends(require_verified_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferDetailResponse:
    return service.create_offer(current_user=current_user, payload=payload)


@router.get(
    "",
    response_model=OfferListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user's offers",
    description="Retrieve paginated sent and received offers with status/role filters.",
)
def list_offers(
    role: Optional[str] = Query(None, description="Filter: 'sent', 'received', or all"),
    status: Optional[str] = Query(None, description="Filter by status ('pending', 'accepted', etc.)"),
    conversation_id: Optional[uuid.UUID] = Query(None, description="Filter by conversation thread"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_verified_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferListResponse:
    return service.list_user_offers(
        current_user=current_user,
        role_filter=role,
        status_filter=status,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{offer_id}",
    response_model=OfferDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get offer details",
    description="Retrieve full proposal details including line items and participant metadata.",
)
def get_offer(
    offer_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferDetailResponse:
    return service.get_offer(current_user=current_user, offer_id=offer_id)


@router.get(
    "/{offer_id}/history",
    response_model=OfferHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get negotiation history",
    description="Retrieve the chronological negotiation history chain from initial proposal to latest counter-offer.",
)
def get_offer_history(
    offer_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferHistoryResponse:
    return service.get_offer_history(current_user=current_user, offer_id=offer_id)


@router.post(
    "/{offer_id}/counter",
    response_model=OfferDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit counter-offer",
    description="Counter a pending offer. Reverses sender/recipient roles and preserves negotiation history.",
)
def counter_offer(
    offer_id: uuid.UUID,
    payload: CounterOfferCreate,
    current_user: User = Depends(require_verified_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferDetailResponse:
    return service.counter_offer(
        current_user=current_user,
        parent_offer_id=offer_id,
        payload=payload,
    )


@router.post(
    "/{offer_id}/accept",
    response_model=OfferAcceptResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept offer",
    description="Accept a pending offer. Atomically updates inventory, calculates requirement fulfillment, and creates Order.",
)
def accept_offer(
    offer_id: uuid.UUID,
    payload: Optional[OfferAcceptRequest] = None,
    approve_requirement_update: Optional[bool] = Query(
        True,
        description="Buyer approval of system-calculated remaining quantity deduction under FR-REQ-07/BR-07",
    ),
    close_requirement: Optional[bool] = Query(None, description="Explicit buyer instruction to close requirement"),
    current_user: User = Depends(require_verified_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferAcceptResponse:
    return service.accept_offer(
        current_user=current_user,
        offer_id=offer_id,
        payload=payload,
        approve_requirement_update=approve_requirement_update,
        close_requirement=close_requirement,
    )


@router.post(
    "/{offer_id}/reject",
    response_model=OfferDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject offer",
    description="Reject a pending offer with an optional reason.",
)
def reject_offer(
    offer_id: uuid.UUID,
    payload: Optional[OfferRejectRequest] = None,
    current_user: User = Depends(require_verified_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferDetailResponse:
    req = payload or OfferRejectRequest()
    return service.reject_offer(
        current_user=current_user,
        offer_id=offer_id,
        payload=req,
    )


@router.post(
    "/{offer_id}/withdraw",
    response_model=OfferDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Withdraw offer",
    description="Withdraw an offer previously sent by the current user before it is accepted or countered.",
)
def withdraw_offer(
    offer_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OfferService = Depends(get_offer_service),
) -> OfferDetailResponse:
    return service.withdraw_offer(
        current_user=current_user,
        offer_id=offer_id,
    )

