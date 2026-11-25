"""Service layer for Transporter operations.

Enforces business rules:
- Only users with role='transporter' can manage transporter profile and service areas.
- Transporters cannot modify other transporters' service areas.
- Duplicate service areas for the same state, district, and coverage type are rejected.
- Order transport coordination is strictly restricted to order participants (farmer, buyer, assigned transporter, admin).
- Off-platform transport coordination only: no vehicle tracking or direct carrier liabilities.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional

from fastapi import HTTPException, status

from app.models.notification import Notification
from app.models.order import Order
from app.models.transporter_connection import (
    TRANSPORT_REQUEST_STATUS_COUNTERPARTY_APPROVED,
    TRANSPORT_REQUEST_STATUS_COUNTERPARTY_REJECTED,
    TRANSPORT_REQUEST_STATUS_TRANSPORTER_ACCEPTED,
    TransportConnectionRequest,
)
from app.models.user import ServiceArea, TransporterProfile, User
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
            user_id=profile.user_id,
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
            verification_status=profile.user.verification_status if profile.user else "verified",
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
                    verification_status=p.user.verification_status if p.user else "verified",
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
            user_id=profile.user_id,
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
            verification_status=profile.user.verification_status if profile.user else "verified",
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

    def _notify(
        self,
        user_id: uuid.UUID,
        event_type: str,
        title: str,
        body: str,
        ref_type: Optional[str] = None,
        ref_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Helper to create an in-app notification record."""
        notification = Notification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            body=body,
            reference_type=ref_type,
            reference_id=ref_id,
        )
        self.repository.db.add(notification)
        self.repository.db.commit()

    def _to_connection_request_read(
        self, req: TransportConnectionRequest, current_user: Optional[User] = None
    ) -> TransportConnectionRequestRead:
        """Convert ORM TransportConnectionRequest to validated Pydantic schema."""
        requester_name = "User"
        if req.requester:
            if getattr(req.requester, "farmer_profile", None):
                fp = req.requester.farmer_profile
                requester_name = fp.full_name or fp.farm_name or req.requester.email
            elif getattr(req.requester, "buyer_profile", None):
                bp = req.requester.buyer_profile
                requester_name = bp.contact_person_name or bp.business_name or req.requester.email
            else:
                requester_name = req.requester.email

        transporter_business_name = "Transport Provider"
        transporter_contact_name = "Transporter"
        transporter_phone = ""
        if req.transporter and getattr(req.transporter, "transporter_profile", None):
            tp = req.transporter.transporter_profile
            transporter_business_name = tp.business_name
            transporter_contact_name = tp.contact_name
            transporter_phone = tp.phone_number

        order_number = req.order.order_number if req.order else None
        offer_number = req.offer.offer_number if req.offer else None

        # Determine counterparty details
        counterparty_name = None
        if req.order:
            counterparty_user = (
                req.order.farmer if req.order.buyer_id == req.requester_id else req.order.buyer
            )
            if counterparty_user:
                if getattr(counterparty_user, "farmer_profile", None):
                    fp = counterparty_user.farmer_profile
                    counterparty_name = fp.full_name or fp.farm_name or counterparty_user.email
                elif getattr(counterparty_user, "buyer_profile", None):
                    bp = counterparty_user.buyer_profile
                    counterparty_name = bp.contact_person_name or bp.business_name or counterparty_user.email
                else:
                    counterparty_name = counterparty_user.email
        elif req.offer:
            counterparty_user = (
                req.offer.recipient if req.offer.sender_id == req.requester_id else req.offer.sender
            )
            if counterparty_user:
                if getattr(counterparty_user, "farmer_profile", None):
                    fp = counterparty_user.farmer_profile
                    counterparty_name = fp.full_name or fp.farm_name or counterparty_user.email
                elif getattr(counterparty_user, "buyer_profile", None):
                    bp = counterparty_user.buyer_profile
                    counterparty_name = bp.contact_person_name or bp.business_name or counterparty_user.email
                else:
                    counterparty_name = counterparty_user.email

        # Determine if current authenticated user has approval/rejection authority
        can_approve = False
        can_reject = False
        if current_user and req.status in ("transporter_accepted", "accepted"):
            if current_user.id != req.requester_id and current_user.id != req.transporter_id:
                if req.order and (
                    (req.order.buyer_id == req.requester_id and current_user.id == req.order.farmer_id)
                    or (req.order.farmer_id == req.requester_id and current_user.id == req.order.buyer_id)
                ):
                    can_approve = True
                    can_reject = True
                elif req.offer and (
                    (req.offer.sender_id == req.requester_id and current_user.id == req.offer.recipient_id)
                    or (req.offer.recipient_id == req.requester_id and current_user.id == req.offer.sender_id)
                ):
                    can_approve = True
                    can_reject = True

        return TransportConnectionRequestRead(
            id=req.id,
            requester_id=req.requester_id,
            transporter_id=req.transporter_id,
            order_id=req.order_id,
            offer_id=req.offer_id,
            order_number=order_number,
            offer_number=offer_number,
            requester_name=requester_name,
            requester_role=req.requester.role if req.requester else "user",
            transporter_business_name=transporter_business_name,
            transporter_contact_name=transporter_contact_name,
            transporter_phone=transporter_phone,
            pickup_state=req.pickup_state,
            pickup_district=req.pickup_district,
            pickup_address=req.pickup_address,
            delivery_state=req.delivery_state,
            delivery_district=req.delivery_district,
            delivery_address=req.delivery_address,
            cargo_description=req.cargo_description,
            weight_kg=req.weight_kg,
            required_delivery_date=req.required_delivery_date,
            notes=req.notes,
            status=req.status,
            rejection_reason=req.rejection_reason,
            response_notes=req.response_notes,
            transporter_accepted_at=getattr(req, "transporter_accepted_at", None),
            counterparty_approved_by_id=getattr(req, "counterparty_approved_by_id", None),
            counterparty_approved_at=getattr(req, "counterparty_approved_at", None),
            counterparty_rejected_by_id=getattr(req, "counterparty_rejected_by_id", None),
            counterparty_rejected_at=getattr(req, "counterparty_rejected_at", None),
            counterparty_rejection_reason=getattr(req, "counterparty_rejection_reason", None),
            counterparty_name=counterparty_name,
            can_current_user_approve=can_approve,
            can_current_user_reject=can_reject,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    def create_connection_request(
        self, current_user: User, payload: TransportConnectionRequestCreate
    ) -> TransportConnectionRequestRead:
        """Create a new transport connection request from a farmer or buyer to a verified transporter."""
        if current_user.role not in ("farmer", "buyer", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only farmers, commercial buyers, or administrators can request transportation",
            )
        if current_user.role != "admin" and current_user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a verified account",
            )

        # Lookup and validate transporter
        transporter_user = (
            self.repository.db.query(User)
            .filter(User.id == payload.transporter_user_id)
            .first()
        )
        if not transporter_user or transporter_user.role != "transporter":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transportation provider not found",
            )
        if transporter_user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected transporter account is currently inactive",
            )
        if transporter_user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request transportation from an unverified provider",
            )
        if transporter_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request transportation from yourself",
            )

        # Check existing pending request
        existing = self.repository.find_existing_pending_request(
            requester_id=current_user.id,
            transporter_id=transporter_user.id,
            order_id=payload.order_id,
            offer_id=payload.offer_id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending transportation request already exists for this provider and transaction",
            )

        order = None
        pickup_address = payload.pickup_address
        delivery_address = payload.delivery_address
        delivery_date = payload.required_delivery_date
        cargo_description = payload.cargo_description
        weight_kg = payload.weight_kg

        if payload.order_id:
            order = self.repository.get_order_by_id(payload.order_id)
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Associated order not found",
                )
            is_participant = (
                order.buyer_id == current_user.id
                or order.farmer_id == current_user.id
                or current_user.role == "admin"
            )
            if not is_participant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to request transport for this order",
                )
            if order.status == "cancelled":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot request transport for a cancelled order",
                )

            # Auto-populate defaults if missing
            if not delivery_address and order.delivery_destination_address:
                delivery_address = order.delivery_destination_address
            if not delivery_date and order.delivery_arranged_date:
                delivery_date = order.delivery_arranged_date
            if not cargo_description and order.items:
                cargo_description = f"Order #{order.order_number}: {len(order.items)} produce item(s)"

        offer = None
        if payload.offer_id:
            offer = self.repository.get_offer_by_id(payload.offer_id)
            if not offer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Associated offer proposal not found",
                )
            is_offer_participant = (
                offer.sender_id == current_user.id
                or offer.recipient_id == current_user.id
                or current_user.role == "admin"
            )
            if not is_offer_participant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to request transport for this negotiation offer",
                )
            if offer.status in ("rejected", "withdrawn", "expired"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot request transport for an offer in '{offer.status}' status",
                )
            if not delivery_date and offer.proposed_delivery_date:
                delivery_date = offer.proposed_delivery_date
            if not cargo_description and offer.items:
                cargo_description = f"Offer #{offer.offer_number}: {len(offer.items)} produce item(s)"

        new_req = TransportConnectionRequest(
            requester_id=current_user.id,
            transporter_id=transporter_user.id,
            order_id=payload.order_id,
            offer_id=payload.offer_id,
            pickup_state=payload.pickup_state,
            pickup_district=payload.pickup_district,
            pickup_address=pickup_address,
            delivery_state=payload.delivery_state,
            delivery_district=payload.delivery_district,
            delivery_address=delivery_address,
            cargo_description=cargo_description,
            weight_kg=weight_kg,
            required_delivery_date=delivery_date,
            notes=payload.notes,
            status="pending",
        )
        saved = self.repository.create_connection_request(new_req)

        # Notify transporter
        deal_label = (
            f"Order #{order.order_number}"
            if order
            else (f"Offer #{offer.offer_number}" if offer else "a potential shipment")
        )
        self._notify(
            user_id=transporter_user.id,
            event_type="transport_connection_requested",
            title="New Transport Connection Request",
            body=f"You received a transportation service request for {deal_label}.",
            ref_type="order" if payload.order_id else ("offer" if payload.offer_id else "transporter"),
            ref_id=saved.id,
        )

        # Also notify counterparty on order or offer if one exists
        counterparty_id = None
        if order:
            counterparty_id = (
                order.farmer_id if current_user.id == order.buyer_id else order.buyer_id
            )
        elif offer:
            counterparty_id = (
                offer.recipient_id if current_user.id == offer.sender_id else offer.sender_id
            )

        if counterparty_id and counterparty_id != current_user.id:
            self._notify(
                user_id=counterparty_id,
                event_type="transport_connection_requested",
                title="Transportation Requested",
                body=f"A transport connection was requested for {deal_label}.",
                ref_type="order" if payload.order_id else ("offer" if payload.offer_id else "transporter"),
                ref_id=saved.id,
            )

        # Reload with joined relations for complete read model
        loaded = self.repository.get_connection_request_by_id(saved.id)
        return self._to_connection_request_read(loaded or saved, current_user=current_user)

    def list_connection_requests(
        self,
        current_user: User,
        status: Optional[str] = None,
        order_id: Optional[uuid.UUID] = None,
        offer_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TransportConnectionRequestListResponse:
        """List transportation connection requests scoped to the authenticated user."""
        offset = (page - 1) * page_size
        total, requests = self.repository.list_connection_requests(
            user_id=current_user.id,
            role=current_user.role,
            status=status,
            order_id=order_id,
            offer_id=offer_id,
            limit=page_size,
            offset=offset,
        )
        items = [self._to_connection_request_read(r, current_user=current_user) for r in requests]
        return TransportConnectionRequestListResponse(total=total, items=items)

    def get_connection_request(
        self, current_user: User, request_id: uuid.UUID
    ) -> TransportConnectionRequestRead:
        """Fetch single connection request ensuring participant authorization."""
        req = self.repository.get_connection_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transport connection request not found",
            )

        is_transporter = req.transporter_id == current_user.id
        is_requester = req.requester_id == current_user.id
        is_order_party = (
            req.order
            and (req.order.buyer_id == current_user.id or req.order.farmer_id == current_user.id)
        )
        is_offer_party = (
            req.offer
            and (req.offer.sender_id == current_user.id or req.offer.recipient_id == current_user.id)
        )
        is_admin = current_user.role == "admin"

        if not (is_transporter or is_requester or is_order_party or is_offer_party or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this transport connection request",
            )

        return self._to_connection_request_read(req, current_user=current_user)

    def accept_connection_request(
        self,
        current_user: User,
        request_id: uuid.UUID,
        payload: TransportConnectionRequestResponse,
    ) -> TransportConnectionRequestRead:
        """Transporter accepts a pending transportation connection request.
        
        Requires subsequent counterparty approval before the transporter is officially assigned to the order.
        """
        req = self.repository.get_connection_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transport connection request not found",
            )
        if req.transporter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the target transportation provider can accept this request",
            )
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept request in '{req.status}' state; must be 'pending'",
            )

        req.status = TRANSPORT_REQUEST_STATUS_TRANSPORTER_ACCEPTED
        req.transporter_accepted_at = datetime.now(timezone.utc)
        req.response_notes = payload.response_notes
        saved = self.repository.save_connection_request(req)

        # Bilateral rule: transporter acceptance does NOT assign the order directly.
        # Order assignment requires explicit approval from the counterparty.

        # Notify requester
        deal_label = (
            f"Order #{req.order.order_number}"
            if req.order
            else (f"Offer #{req.offer.offer_number}" if req.offer else "your request")
        )
        self._notify(
            user_id=req.requester_id,
            event_type="transport_connection_accepted",
            title="Transport Request Accepted by Provider",
            body=f"Transportation provider accepted your request for {deal_label}. Awaiting counterparty approval to confirm assignment.",
            ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
            ref_id=saved.id,
        )

        # Notify counterparty that their approval is required
        counterparty_id = None
        if req.order:
            counterparty_id = (
                req.order.farmer_id
                if req.requester_id == req.order.buyer_id
                else req.order.buyer_id
            )
        elif req.offer:
            counterparty_id = (
                req.offer.recipient_id
                if req.requester_id == req.offer.sender_id
                else req.offer.sender_id
            )

        if counterparty_id and counterparty_id != current_user.id:
            tp_name = (
                req.transporter.transporter_profile.business_name
                if req.transporter and getattr(req.transporter, "transporter_profile", None)
                else "Transportation provider"
            )
            self._notify(
                user_id=counterparty_id,
                event_type="transport_counterparty_approval_pending",
                title="Transportation Assignment Approval Needed",
                body=f"Transporter '{tp_name}' accepted the request for {deal_label}. Please review and approve or reject the assignment.",
                ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
                ref_id=saved.id,
            )

        return self._to_connection_request_read(saved, current_user=current_user)

    def approve_assignment(
        self,
        current_user: User,
        request_id: uuid.UUID,
        payload: Optional[TransportConnectionApprovalResponse] = None,
    ) -> TransportConnectionRequestRead:
        """Deal counterparty approves the transporter assignment for an order or proposal."""
        req = self.repository.get_connection_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transport connection request not found",
            )

        if req.status not in (TRANSPORT_REQUEST_STATUS_TRANSPORTER_ACCEPTED, "accepted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve request in '{req.status}' state; must be 'transporter_accepted'",
            )

        # Enforce bilateral approval authorization: only genuine deal counterparty can approve
        if current_user.id == req.requester_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Initiating requester cannot approve on behalf of the deal counterparty",
            )
        if current_user.id == req.transporter_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transporter cannot approve their own assignment",
            )

        is_order_counterparty = (
            req.order
            and (
                (req.order.buyer_id == req.requester_id and current_user.id == req.order.farmer_id)
                or (req.order.farmer_id == req.requester_id and current_user.id == req.order.buyer_id)
            )
        )
        is_offer_counterparty = (
            req.offer
            and (
                (req.offer.sender_id == req.requester_id and current_user.id == req.offer.recipient_id)
                or (req.offer.recipient_id == req.requester_id and current_user.id == req.offer.sender_id)
            )
        )

        if not (is_order_counterparty or is_offer_counterparty):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the counterparty on this order or deal can approve the transportation assignment",
            )

        if current_user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a verified account",
            )

        now_utc = datetime.now(timezone.utc)
        req.status = TRANSPORT_REQUEST_STATUS_COUNTERPARTY_APPROVED
        req.counterparty_approved_by_id = current_user.id
        req.counterparty_approved_at = now_utc
        if payload and payload.approval_notes:
            note = f"[Counterparty Approved]: {payload.approval_notes}"
            req.response_notes = f"{req.response_notes}\n{note}" if req.response_notes else note

        # Assign order atomically within same transaction, preventing overwriting an already assigned transporter
        if req.order_id and req.order:
            if req.order.transporter_id and req.order.transporter_id != req.transporter_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This order already has an assigned transportation provider",
                )
            req.order.transporter_id = req.transporter_id
            req.order.transport_status = "assigned"
            delivery_note = f"[Transporter Assigned]: Bilaterally approved by {current_user.email}."
            req.order.delivery_notes = (
                f"{req.order.delivery_notes}\n{delivery_note}"
                if req.order.delivery_notes
                else delivery_note
            )
            self.repository.save_order(req.order)

        saved = self.repository.save_connection_request(req)

        deal_label = (
            f"Order #{req.order.order_number}"
            if req.order
            else (f"Offer #{req.offer.offer_number}" if req.offer else "the transaction")
        )

        # Notify requester
        self._notify(
            user_id=req.requester_id,
            event_type="transport_assignment_approved",
            title="Transportation Assignment Approved",
            body=f"Counterparty approved transportation provider for {deal_label}. Transporter is now officially assigned.",
            ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
            ref_id=saved.id,
        )

        # Notify transporter
        self._notify(
            user_id=req.transporter_id,
            event_type="transport_assignment_approved",
            title="Transportation Assignment Confirmed",
            body=f"Both parties approved your transportation assignment for {deal_label}.",
            ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
            ref_id=saved.id,
        )

        # Notify counterparty (confirmation)
        if current_user.id != req.requester_id and current_user.id != req.transporter_id:
            self._notify(
                user_id=current_user.id,
                event_type="transport_assignment_confirmed",
                title="Transportation Assignment Confirmed",
                body=f"You approved the transportation assignment for {deal_label}.",
                ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
                ref_id=saved.id,
            )

        return self._to_connection_request_read(saved, current_user=current_user)

    def reject_assignment(
        self,
        current_user: User,
        request_id: uuid.UUID,
        payload: Optional[TransportConnectionRejectionPayload] = None,
    ) -> TransportConnectionRequestRead:
        """Deal counterparty rejects the proposed transporter assignment."""
        req = self.repository.get_connection_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transport connection request not found",
            )

        if req.status not in (TRANSPORT_REQUEST_STATUS_TRANSPORTER_ACCEPTED, "accepted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject request in '{req.status}' state; must be 'transporter_accepted'",
            )

        # Enforce authorization: only deal counterparty can reject
        if current_user.id == req.requester_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Initiating requester cannot reject on behalf of the deal counterparty; use cancel instead",
            )
        if current_user.id == req.transporter_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transporter cannot reject counterparty approval; use decline instead",
            )

        is_order_counterparty = (
            req.order
            and (
                (req.order.buyer_id == req.requester_id and current_user.id == req.order.farmer_id)
                or (req.order.farmer_id == req.requester_id and current_user.id == req.order.buyer_id)
            )
        )
        is_offer_counterparty = (
            req.offer
            and (
                (req.offer.sender_id == req.requester_id and current_user.id == req.offer.recipient_id)
                or (req.offer.recipient_id == req.requester_id and current_user.id == req.offer.sender_id)
            )
        )

        if not (is_order_counterparty or is_offer_counterparty):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the counterparty on this order or deal can reject the transportation assignment",
            )

        now_utc = datetime.now(timezone.utc)
        req.status = TRANSPORT_REQUEST_STATUS_COUNTERPARTY_REJECTED
        req.counterparty_rejected_by_id = current_user.id
        req.counterparty_rejected_at = now_utc
        reason = payload.counterparty_rejection_reason if payload else None
        req.counterparty_rejection_reason = reason

        # Transporter is NOT assigned.
        saved = self.repository.save_connection_request(req)

        deal_label = (
            f"Order #{req.order.order_number}"
            if req.order
            else (f"Offer #{req.offer.offer_number}" if req.offer else "the transaction")
        )

        reason_text = f" Reason: {reason}" if reason else ""
        # Notify requester
        self._notify(
            user_id=req.requester_id,
            event_type="transport_assignment_rejected",
            title="Transportation Assignment Rejected",
            body=f"Counterparty rejected the proposed transportation provider for {deal_label}.{reason_text}",
            ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
            ref_id=saved.id,
        )

        # Notify transporter
        self._notify(
            user_id=req.transporter_id,
            event_type="transport_assignment_rejected",
            title="Transportation Assignment Not Approved",
            body=f"Deal counterparty did not approve the assignment for {deal_label}.{reason_text}",
            ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
            ref_id=saved.id,
        )

        return self._to_connection_request_read(saved, current_user=current_user)

    def decline_connection_request(
        self,
        current_user: User,
        request_id: uuid.UUID,
        payload: TransportConnectionRequestResponse,
    ) -> TransportConnectionRequestRead:
        """Transporter declines a pending transportation connection request."""
        req = self.repository.get_connection_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transport connection request not found",
            )
        if req.transporter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the target transportation provider can decline this request",
            )
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot decline request in '{req.status}' state; must be 'pending'",
            )

        req.status = "declined"
        req.rejection_reason = payload.rejection_reason
        req.response_notes = payload.response_notes
        saved = self.repository.save_connection_request(req)

        # Notify requester
        reason_msg = f" Reason: {payload.rejection_reason}" if payload.rejection_reason else ""
        deal_label = (
            f"Order #{req.order.order_number}"
            if req.order
            else (f"Offer #{req.offer.offer_number}" if req.offer else "your request")
        )
        self._notify(
            user_id=req.requester_id,
            event_type="transport_connection_declined",
            title="Transport Request Declined",
            body=f"Transportation provider declined your request for {deal_label}.{reason_msg}",
            ref_type="order" if req.order_id else ("offer" if req.offer_id else "transporter"),
            ref_id=saved.id,
        )

        return self._to_connection_request_read(saved, current_user=current_user)

    def cancel_connection_request(
        self, current_user: User, request_id: uuid.UUID
    ) -> TransportConnectionRequestRead:
        """Requester cancels their pending transportation request."""
        req = self.repository.get_connection_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transport connection request not found",
            )
        if req.requester_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the requester can cancel this request",
            )
        if req.status not in ("pending", "transporter_accepted", "accepted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel request in '{req.status}' state",
            )

        req.status = "cancelled"
        saved = self.repository.save_connection_request(req)
        return self._to_connection_request_read(saved, current_user=current_user)
