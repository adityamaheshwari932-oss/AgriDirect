"""FastAPI route handlers for Orders, Line Items, Amendments, Delivery, and Inventory Audit (Module 4).

Exposes RESTful endpoints versioned under /api/v1:
- GET    /api/v1/orders
- GET    /api/v1/orders/{id}
- POST   /api/v1/orders/{id}/confirm
- POST   /api/v1/orders/{id}/cancel
- POST   /api/v1/orders/{id}/amendments
- GET    /api/v1/orders/{id}/amendments
- GET    /api/v1/orders/{id}/amendments/{aid}
- POST   /api/v1/orders/{id}/amendments/{aid}/accept
- POST   /api/v1/orders/{id}/amendments/{aid}/reject
- POST   /api/v1/orders/{id}/delivery/arrange
- POST   /api/v1/orders/{id}/delivery/mark-completed
- POST   /api/v1/orders/{id}/delivery/acknowledge
- GET    /api/v1/orders/{id}/inventory-adjustments
- GET    /api/v1/listings/{id}/inventory-adjustments
"""

import uuid
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_verified_user
from app.models.user import User
from app.orders.schemas import (
    DeliveryAcknowledgeRequest,
    DeliveryArrangeRequest,
    InventoryAdjustmentListResponse,
    OrderAmendmentCreate,
    OrderAmendmentListResponse,
    OrderAmendmentResponse,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderDetailResponse,
    OrderImageResponse,
    OrderListResponse,
)
from app.orders.service import OrderService

router = APIRouter(tags=["Orders & Inventory Lifecycle"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Dependency provider for OrderService."""
    return OrderService(db)


# ---------------------------------------------------------------------------
# Batch 1: Order Creation, Listing, Details & Confirmation
# ---------------------------------------------------------------------------

@router.post(
    "/orders",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create direct purchase order",
    description="Place a direct order against an active produce listing with atomic inventory deduction and idempotency.",
)
def create_direct_order(
    payload: OrderCreateRequest,
    x_idempotency_key: Optional[str] = Header(default=None, alias="X-Idempotency-Key"),
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    if x_idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = x_idempotency_key
    return service.create_direct_order(current_user=current_user, payload=payload)


@router.get(
    "/orders",
    response_model=OrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List orders",
    description="Retrieve paginated orders for the authenticated participant (buyer or farmer).",
)
def list_orders(
    role: Optional[str] = Query(default=None, description="Optional role filter: 'buyer' or 'farmer'"),
    status: Optional[str] = Query(default=None, description="Optional order status filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    return service.list_orders(
        current_user=current_user,
        role_filter=role,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/orders/{id}",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get order details",
    description="Retrieve complete order details including snapshot items, participants, and delivery status.",
)
def get_order_detail(
    id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    return service.get_order_detail(current_user=current_user, order_id=id)


@router.post(
    "/orders/{id}/confirm",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm order (Farmer only)",
    description="Acknowledge fulfillment commitment by the farmer, transitioning order from pending to confirmed.",
)
def confirm_order(
    id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    return service.confirm_order(current_user=current_user, order_id=id)


# ---------------------------------------------------------------------------
# Batch 2: Atomic Order Cancellation
# ---------------------------------------------------------------------------

@router.post(
    "/orders/{id}/cancel",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel order",
    description="Atomically cancel an active order with authoritative inventory and buyer demand restitution.",
)
def cancel_order(
    id: uuid.UUID,
    payload: OrderCancelRequest,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    return service.cancel_order(current_user=current_user, order_id=id, payload=payload)


# ---------------------------------------------------------------------------
# Batch 3: Order Amendments
# ---------------------------------------------------------------------------

@router.post(
    "/orders/{id}/amendments",
    response_model=OrderAmendmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose order amendment",
    description="Propose a post-finalization change (quantity, price, delivery_date, terms) requiring bilateral agreement.",
)
def propose_amendment(
    id: uuid.UUID,
    payload: OrderAmendmentCreate,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderAmendmentResponse:
    return service.propose_amendment(current_user=current_user, order_id=id, payload=payload)


@router.get(
    "/orders/{id}/amendments",
    response_model=OrderAmendmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List order amendments",
    description="Retrieve all proposed and historical amendments for the order.",
)
def list_amendments(
    id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderAmendmentListResponse:
    return service.list_amendments(current_user=current_user, order_id=id)


@router.get(
    "/orders/{id}/amendments/{aid}",
    response_model=OrderAmendmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get order amendment details",
    description="Retrieve a single order amendment by ID.",
)
def get_amendment(
    id: uuid.UUID,
    aid: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderAmendmentResponse:
    return service.get_amendment(current_user=current_user, order_id=id, amendment_id=aid)


@router.post(
    "/orders/{id}/amendments/{aid}/accept",
    response_model=OrderAmendmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept order amendment",
    description="Counterparty confirms proposed amendment, executing atomic inventory and demand updates.",
)
def accept_amendment(
    id: uuid.UUID,
    aid: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderAmendmentResponse:
    return service.accept_amendment(current_user=current_user, order_id=id, amendment_id=aid)


@router.post(
    "/orders/{id}/amendments/{aid}/reject",
    response_model=OrderAmendmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject order amendment",
    description="Counterparty rejects proposed amendment.",
)
def reject_amendment(
    id: uuid.UUID,
    aid: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderAmendmentResponse:
    return service.reject_amendment(current_user=current_user, order_id=id, amendment_id=aid)


# ---------------------------------------------------------------------------
# Batch 4: Delivery Coordination
# ---------------------------------------------------------------------------

@router.post(
    "/orders/{id}/delivery/arrange",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Arrange delivery details",
    description="Record logistics method, destination address, and scheduled date.",
)
def arrange_delivery(
    id: uuid.UUID,
    payload: DeliveryArrangeRequest,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    return service.arrange_delivery(current_user=current_user, order_id=id, payload=payload)


@router.post(
    "/orders/{id}/delivery/mark-completed",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark delivery completed",
    description="One counterparty indicates physical goods transit/dispatch has completed.",
)
def mark_delivery_completed(
    id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    return service.mark_delivery_completed(current_user=current_user, order_id=id)


@router.post(
    "/orders/{id}/delivery/acknowledge",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge delivery receipt",
    description="Acknowledge physical receipt of delivered produce, progressing or completing the order.",
)
def acknowledge_delivery(
    id: uuid.UUID,
    payload: Optional[DeliveryAcknowledgeRequest] = None,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    return service.acknowledge_delivery(current_user=current_user, order_id=id, payload=payload)


# ---------------------------------------------------------------------------
# Batch 5: Inventory Audit Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/orders/{id}/inventory-adjustments",
    response_model=InventoryAdjustmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get order inventory adjustments",
    description="Retrieve append-only inventory adjustment audit entries associated with an order.",
)
def get_order_inventory_adjustments(
    id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> InventoryAdjustmentListResponse:
    return service.get_order_inventory_adjustments(
        current_user=current_user,
        order_id=id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/listings/{id}/inventory-adjustments",
    response_model=InventoryAdjustmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get listing inventory adjustments",
    description="Retrieve append-only inventory audit records for a produce listing (owner farmer only).",
)
def get_listing_inventory_adjustments(
    id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> InventoryAdjustmentListResponse:
    return service.get_listing_inventory_adjustments(
        current_user=current_user,
        listing_id=id,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Batch 6: Order Photographic Evidence & Quality Assets (Phase 2)
# ---------------------------------------------------------------------------

@router.post(
    "/orders/{id}/images",
    response_model=List[OrderImageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload order image(s)",
    description="Upload photographic quality inspection, delivery dispatch, or receipt verification assets to an order.",
)
def upload_order_images(
    id: uuid.UUID,
    file: Optional[UploadFile] = File(None, description="Single image file"),
    files: Optional[List[UploadFile]] = File(None, description="Multiple image files"),
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> List[OrderImageResponse]:
    upload_files: List[UploadFile] = []
    if files:
        upload_files.extend(files)
    if file:
        upload_files.append(file)
    if not upload_files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one image file ('file' or 'files') must be provided",
        )
    return service.upload_order_images(
        current_user=current_user,
        order_id=id,
        upload_files=upload_files,
    )


@router.get(
    "/orders/{id}/images",
    response_model=List[OrderImageResponse],
    status_code=status.HTTP_200_OK,
    summary="List order images",
    description="Retrieve all photographic assets attached to an order.",
)
def list_order_images(
    id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> List[OrderImageResponse]:
    return service.list_order_images(current_user=current_user, order_id=id)


@router.get(
    "/orders/{id}/images/{image_id}",
    summary="Download or stream order image",
    description="Streams an attached order photograph. Restricted to order counterparties or administrators.",
    status_code=status.HTTP_200_OK,
)
def download_order_image(
    id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    service: OrderService = Depends(get_order_service),
) -> FileResponse:
    file_path = service.get_order_image_file_path(
        current_user=current_user,
        order_id=id,
        image_id=image_id,
    )
    return FileResponse(path=file_path)


