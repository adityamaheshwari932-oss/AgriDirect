"""Service layer for Transporter operations.

Enforces business rules:
- Only users with role='transporter' can manage transporter profile and service areas.
- Transporters cannot modify other transporters' service areas.
- Duplicate service areas for the same state, district, and coverage type are rejected.
- Order transport coordination is strictly restricted to order participants (farmer, buyer, assigned transporter, admin).
- Off-platform transport coordination only: no vehicle tracking or direct carrier liabilities.
"""

from decimal import Decimal
import uuid
from typing import List, Optional

from fastapi import HTTPException, status

from app.models.order import Order
from app.models.user import ServiceArea, TransporterProfile, User
from app.transporters.repository import TransporterRepository
from app.transporters.schemas import (
    OrderTransportCoordinationRequest,
    OrderTransportCoordinationResponse,
    ServiceAreaCreate,
    ServiceAreaRead,
    ServiceAreaUpdate,
    TransporterDetailRead,
    TransporterProfileRead,
    TransporterProfileUpdate,
    TransporterSearchResponse,
    TransporterSearchResult,
)


class TransporterService:
    """Business logic coordinator for transportation services."""

    def __init__(self, repository: TransporterRepository) -> None:
        self.repository = repository

    def _require_transporter(self, current_user: User) -> TransporterProfile:
        """Verify that current_user has role='transporter' and retrieve their profile."""
        if current_user.role != "transporter":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation permitted only for users with role='transporter'",
            )
        profile = self.repository.get_profile_by_user_id(current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transporter profile not found for this user",
            )
        return profile

    def get_my_profile(self, current_user: User) -> TransporterDetailRead:
        """Fetch current transporter's profile and service areas."""
        profile = self._require_transporter(current_user)
        return TransporterDetailRead(
            id=profile.id,
            business_name=profile.business_name,
            contact_name=profile.contact_name,
            phone_number=profile.phone_number,
            transport_type=profile.transport_type,
            vehicle_capacity_kg=profile.vehicle_capacity_kg,
            vehicle_registration_number=profile.vehicle_registration_number,
            is_available=profile.is_available,
            experience_years=profile.experience_years,
            operating_states=profile.operating_states,
            bio=profile.bio,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            service_areas=[ServiceAreaRead.model_validate(sa) for sa in profile.service_areas],
        )

    def update_my_profile(
        self, current_user: User, payload: TransporterProfileUpdate
    ) -> TransporterProfileRead:
        """Update current transporter's profile information."""
        profile = self._require_transporter(current_user)
        update_data = payload.model_dump(exclude_unset=True)
        updated = self.repository.update_profile(profile, update_data)
        return TransporterProfileRead.model_validate(updated)

    def get_my_service_areas(self, current_user: User) -> List[ServiceAreaRead]:
        """List all service areas owned by the current transporter."""
        profile = self._require_transporter(current_user)
        areas = self.repository.get_service_areas(profile.id)
        return [ServiceAreaRead.model_validate(a) for a in areas]

    def add_service_area(
        self, current_user: User, payload: ServiceAreaCreate
    ) -> ServiceAreaRead:
        """Create a new service area for the transporter, preventing duplicates."""
        profile = self._require_transporter(current_user)

        # Check duplicate
        existing = self.repository.find_duplicate_service_area(
            profile_id=profile.id,
            state=payload.state,
            district=payload.district,
            coverage_type=payload.coverage_type,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A service area for '{payload.state} - {payload.district}' "
                    f"with coverage '{payload.coverage_type}' already exists"
                ),
            )

        new_area = ServiceArea(
            transporter_profile_id=profile.id,
            state=payload.state.strip(),
            district=payload.district.strip(),
            taluka_subdistrict=payload.taluka_subdistrict.strip() if payload.taluka_subdistrict else None,
            village_town=payload.village_town.strip() if payload.village_town else None,
            pincode=payload.pincode.strip() if payload.pincode else None,
            coverage_type=payload.coverage_type,
            is_active=payload.is_active,
        )
        saved = self.repository.add_service_area(new_area)
        return ServiceAreaRead.model_validate(saved)

    def update_service_area(
        self, current_user: User, service_area_id: uuid.UUID, payload: ServiceAreaUpdate
    ) -> ServiceAreaRead:
        """Update a specific service area ensuring ownership."""
        profile = self._require_transporter(current_user)
        service_area = self.repository.get_service_area_by_id(service_area_id)
        if not service_area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service area not found",
            )
        if service_area.transporter_profile_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify another provider's service area",
            )

        update_dict = payload.model_dump(exclude_unset=True)
        if "coverage_type" in update_dict:
            existing = self.repository.find_duplicate_service_area(
                profile_id=profile.id,
                state=service_area.state,
                district=service_area.district,
                coverage_type=update_dict["coverage_type"],
                exclude_id=service_area.id,
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another service area with this coverage type already exists for this district",
                )

        updated = self.repository.update_service_area(service_area, update_dict)
        return ServiceAreaRead.model_validate(updated)

    def delete_service_area(
        self, current_user: User, service_area_id: uuid.UUID
    ) -> dict:
        """Remove a service area belonging to the current transporter."""
        profile = self._require_transporter(current_user)
        service_area = self.repository.get_service_area_by_id(service_area_id)
        if not service_area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service area not found",
            )
        if service_area.transporter_profile_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete another provider's service area",
            )

        self.repository.delete_service_area(service_area)
        return {"status": "success", "message": "Service area deleted successfully"}

    def discover_transporters(
        self,
        pickup_state: Optional[str] = None,
        pickup_district: Optional[str] = None,
        delivery_state: Optional[str] = None,
        delivery_district: Optional[str] = None,
        transport_type: Optional[str] = None,
        min_capacity_kg: Optional[Decimal] = None,
        only_available: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> TransporterSearchResponse:
        """Marketplace discovery of available transportation providers."""
        offset = (page - 1) * page_size
        total, profiles = self.repository.search_transporters(
            pickup_state=pickup_state,
            pickup_district=pickup_district,
            delivery_state=delivery_state,
            delivery_district=delivery_district,
            transport_type=transport_type,
            min_capacity_kg=min_capacity_kg,
            only_available=only_available,
            limit=page_size,
            offset=offset,
        )

        items = []
        for p in profiles:
            items.append(
                TransporterSearchResult(
                    id=p.id,
                    user_id=p.user_id,
                    business_name=p.business_name,
                    contact_name=p.contact_name,
                    phone_number=p.phone_number,
                    transport_type=p.transport_type,
                    vehicle_capacity_kg=p.vehicle_capacity_kg,
                    vehicle_registration_number=p.vehicle_registration_number,
                    is_available=p.is_available,
                    experience_years=p.experience_years,
                    operating_states=p.operating_states,
                    bio=p.bio,
                    service_areas=[
                        ServiceAreaRead.model_validate(sa)
                        for sa in p.service_areas
                        if sa.is_active
                    ],
                )
            )

        return TransporterSearchResponse(total=total, items=items)

    def get_transporter_by_id(self, profile_id: uuid.UUID) -> TransporterDetailRead:
        """Get public transporter profile details."""
        profile = self.repository.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transporter not found",
            )
        return TransporterDetailRead(
            id=profile.id,
            business_name=profile.business_name,
            contact_name=profile.contact_name,
            phone_number=profile.phone_number,
            transport_type=profile.transport_type,
            vehicle_capacity_kg=profile.vehicle_capacity_kg,
            vehicle_registration_number=profile.vehicle_registration_number,
            is_available=profile.is_available,
            experience_years=profile.experience_years,
            operating_states=profile.operating_states,
            bio=profile.bio,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            service_areas=[
                ServiceAreaRead.model_validate(sa)
                for sa in profile.service_areas
                if sa.is_active
            ],
        )

    def coordinate_order_transport(
        self,
        current_user: User,
        order_id: uuid.UUID,
        payload: OrderTransportCoordinationRequest,
    ) -> OrderTransportCoordinationResponse:
        """Coordinate transportation details on an existing order."""
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        # Authorization check: only order buyer, farmer, assigned transporter, or admin
        is_buyer = order.buyer_id == current_user.id
        is_farmer = order.farmer_id == current_user.id
        is_assigned_transporter = order.transporter_id == current_user.id
        is_admin = current_user.role == "admin"

        if not (is_buyer or is_farmer or is_assigned_transporter or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to coordinate transport for this order",
            )

        # Assigned transporter must be verified to perform transport coordination operations
        if is_assigned_transporter and not (is_admin or is_buyer or is_farmer):
            if current_user.verification_status != "verified":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operation requires a verified transportation provider account",
                )

        # Transporter assignment can only be done by buyer or farmer or admin
        if payload.transporter_user_id is not None:
            if not (is_buyer or is_farmer or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the buyer or farmer can assign a transporter to the order",
                )
            transporter_user = self.repository.db.query(User).filter(User.id == payload.transporter_user_id).first()
            if not transporter_user or transporter_user.role != "transporter":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected user is not a valid registered transporter",
                )
            if transporter_user.verification_status != "verified":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign unverified transportation provider to an order",
                )
            order.transporter_id = transporter_user.id
            if order.transport_status == "none":
                order.transport_status = "assigned"

        if payload.transport_status is not None:
            order.transport_status = payload.transport_status
            if payload.transport_status == "delivered" and order.delivery_status != "completed":
                order.delivery_status = "completion_marked"

        if payload.delivery_notes is not None:
            if order.delivery_notes:
                order.delivery_notes += f"\n[Transport Update]: {payload.delivery_notes}"
            else:
                order.delivery_notes = payload.delivery_notes

        saved_order = self.repository.save_order(order)
        transporter_name = None
        transporter_phone = None
        if saved_order.transporter and saved_order.transporter.transporter_profile:
            transporter_name = saved_order.transporter.transporter_profile.business_name
            transporter_phone = saved_order.transporter.transporter_profile.phone_number

        return OrderTransportCoordinationResponse(
            order_id=saved_order.id,
            order_number=saved_order.order_number,
            transporter_id=saved_order.transporter_id,
            transporter_business_name=transporter_name,
            transporter_phone=transporter_phone,
            transport_status=saved_order.transport_status,
            delivery_notes=saved_order.delivery_notes,
        )
