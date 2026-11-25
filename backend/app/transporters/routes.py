"""FastAPI route handlers for Transporter features.

Endpoints:
- GET /api/v1/transporters/me
- PATCH /api/v1/transporters/me
- GET /api/v1/transporters/service-areas
- POST /api/v1/transporters/service-areas
- PATCH /api/v1/transporters/service-areas/{id}
- DELETE /api/v1/transporters/service-areas/{id}
- GET /api/v1/transporters/discover
- GET /api/v1/transporters/{id}
- POST /api/v1/orders/{order_id}/transport-coordination
"""

from decimal import Decimal
import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.transporters.repository import TransporterRepository
from app.transporters.schemas import (
    OrderTransportCoordinationRequest,
    OrderTransportCoordinationResponse,
    ServiceAreaCreate,
    ServiceAreaRead,
    ServiceAreaUpdate,
    TransportConnectionApprovalResponse,
    TransportConnectionRejectionPayload,
    TransportConnectionRequestCreate,
    TransportConnectionRequestListResponse,
    TransportConnectionRequestRead,
    TransportConnectionRequestResponse,
    TransporterDetailRead,
    TransporterProfileRead,
    TransporterProfileUpdate,
    TransporterSearchResponse,
)
from app.transporters.service import TransporterService

router = APIRouter(tags=["Transporters"])


def get_transporter_service(db: Session = Depends(get_db)) -> TransporterService:
    """Dependency injector for TransporterService."""
    return TransporterService(TransporterRepository(db))


@router.get(
    "/transporters/me",
    response_model=TransporterDetailRead,
    summary="Get current transporter profile and service areas",
)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransporterDetailRead:
    """Fetch current logged-in transporter's profile and active service areas."""
    return service.get_my_profile(current_user)


@router.patch(
    "/transporters/me",
    response_model=TransporterProfileRead,
    summary="Update current transporter profile",
)
def update_my_profile(
    payload: TransporterProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransporterProfileRead:
    """Update profile details for the authenticated transporter."""
    return service.update_my_profile(current_user, payload)


@router.get(
    "/transporters/service-areas",
    response_model=List[ServiceAreaRead],
    summary="List current transporter's service areas",
)
def get_my_service_areas(
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> List[ServiceAreaRead]:
    """List all service areas registered by the current transporter."""
    return service.get_my_service_areas(current_user)


@router.post(
    "/transporters/service-areas",
    response_model=ServiceAreaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new service area",
)
def add_service_area(
    payload: ServiceAreaCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> ServiceAreaRead:
    """Register a new service area for the authenticated transporter."""
    return service.add_service_area(current_user, payload)


@router.patch(
    "/transporters/service-areas/{area_id}",
    response_model=ServiceAreaRead,
    summary="Update a service area",
)
def update_service_area(
    area_id: uuid.UUID,
    payload: ServiceAreaUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> ServiceAreaRead:
    """Update an existing service area owned by the authenticated transporter."""
    return service.update_service_area(current_user, area_id, payload)


@router.delete(
    "/transporters/service-areas/{area_id}",
    summary="Delete a service area",
)
def delete_service_area(
    area_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> dict:
    """Remove a service area owned by the authenticated transporter."""
    return service.delete_service_area(current_user, area_id)


@router.get(
    "/transporters/discover",
    response_model=TransporterSearchResponse,
    summary="Search and discover transportation providers",
)
def discover_transporters(
    pickup_state: Annotated[Optional[str], Query(description="Origin/pickup state")] = None,
    pickup_district: Annotated[Optional[str], Query(description="Origin/pickup district")] = None,
    delivery_state: Annotated[Optional[str], Query(description="Destination/delivery state")] = None,
    delivery_district: Annotated[Optional[str], Query(description="Destination/delivery district")] = None,
    transport_type: Annotated[Optional[str], Query(description="Filter by vehicle type")] = None,
    min_capacity_kg: Annotated[Optional[Decimal], Query(description="Minimum load capacity in kg")] = None,
    only_available: Annotated[bool, Query(description="Only show available transporters")] = True,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    service: TransporterService = Depends(get_transporter_service),
) -> TransporterSearchResponse:
    """Discover available transportation providers matching origin, destination, and vehicle capacity."""
    return service.discover_transporters(
        pickup_state=pickup_state,
        pickup_district=pickup_district,
        delivery_state=delivery_state,
        delivery_district=delivery_district,
        transport_type=transport_type,
        min_capacity_kg=min_capacity_kg,
        only_available=only_available,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Transport Connection Requests Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/transporters/connection-requests",
    response_model=TransportConnectionRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transportation service connection request",
)
def create_connection_request(
    payload: TransportConnectionRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Initiate a formal transportation service connection request from a farmer or buyer."""
    return service.create_connection_request(current_user, payload)


@router.get(
    "/transporters/connection-requests",
    response_model=TransportConnectionRequestListResponse,
    summary="List transportation connection requests",
)
def list_connection_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    status: Annotated[Optional[str], Query(description="Filter by request status")] = None,
    order_id: Annotated[Optional[uuid.UUID], Query(description="Filter by order ID")] = None,
    offer_id: Annotated[Optional[uuid.UUID], Query(description="Filter by offer proposal ID")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestListResponse:
    """List connection requests scoped to the authenticated user."""
    return service.list_connection_requests(
        current_user=current_user,
        status=status,
        order_id=order_id,
        offer_id=offer_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/transporters/connection-requests/{request_id}",
    response_model=TransportConnectionRequestRead,
    summary="Get single transport connection request details",
)
def get_connection_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Fetch details for a specific connection request ensuring participant authorization."""
    return service.get_connection_request(current_user, request_id)


@router.post(
    "/transporters/connection-requests/{request_id}/accept",
    response_model=TransportConnectionRequestRead,
    summary="Transporter accepts connection request",
)
def accept_connection_request(
    request_id: uuid.UUID,
    payload: TransportConnectionRequestResponse,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Accept a pending transportation connection request."""
    return service.accept_connection_request(current_user, request_id, payload)


@router.post(
    "/transporters/connection-requests/{request_id}/decline",
    response_model=TransportConnectionRequestRead,
    summary="Transporter declines connection request",
)
def decline_connection_request(
    request_id: uuid.UUID,
    payload: TransportConnectionRequestResponse,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Decline a pending transportation connection request."""
    return service.decline_connection_request(current_user, request_id, payload)


@router.post(
    "/transporters/connection-requests/{request_id}/cancel",
    response_model=TransportConnectionRequestRead,
    summary="Requester cancels connection request",
)
def cancel_connection_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Cancel a pending transportation connection request."""
    return service.cancel_connection_request(current_user, request_id)


@router.post(
    "/transporters/connection-requests/{request_id}/approve",
    response_model=TransportConnectionRequestRead,
    summary="Counterparty approves transporter assignment",
)
def approve_assignment(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: Optional[TransportConnectionApprovalResponse] = None,
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Deal counterparty approves the transporter assignment for an order or proposal."""
    return service.approve_assignment(current_user, request_id, payload)


@router.post(
    "/transporters/connection-requests/{request_id}/reject",
    response_model=TransportConnectionRequestRead,
    summary="Counterparty rejects transporter assignment",
)
def reject_assignment(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: Optional[TransportConnectionRejectionPayload] = None,
    service: TransporterService = Depends(get_transporter_service),
) -> TransportConnectionRequestRead:
    """Deal counterparty rejects the proposed transporter assignment."""
    return service.reject_assignment(current_user, request_id, payload)


@router.get(
    "/transporters/{profile_id}",
    response_model=TransporterDetailRead,
    summary="Get transporter public details",
)
def get_transporter_by_id(
    profile_id: uuid.UUID,
    service: TransporterService = Depends(get_transporter_service),
) -> TransporterDetailRead:
    """Get public profile details and active service areas for a transporter."""
    return service.get_transporter_by_id(profile_id)


@router.post(
    "/orders/{order_id}/transport-coordination",
    response_model=OrderTransportCoordinationResponse,
    summary="Coordinate order transportation",
)
def coordinate_order_transport(
    order_id: uuid.UUID,
    payload: OrderTransportCoordinationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: TransporterService = Depends(get_transporter_service),
) -> OrderTransportCoordinationResponse:
    """Assign transporter or update transport coordination status on an active order."""
    return service.coordinate_order_transport(current_user, order_id, payload)
