"""Repository layer for Transporter profile, service areas, and transport discovery.

Executes parameterized SQLAlchemy queries scoped to TransporterProfile,
ServiceArea, and Order transport coordination.
"""

from decimal import Decimal
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.offer import Offer
from app.models.order import Order
from app.models.transporter_connection import TransportConnectionRequest
from app.models.user import ServiceArea, TransporterProfile, User


class TransporterRepository:
    """Database persistence handler for transporter operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile_by_user_id(self, user_id: uuid.UUID) -> Optional[TransporterProfile]:
        """Fetch transporter profile by user ID with eager loaded service areas."""
        return (
            self.db.query(TransporterProfile)
            .options(joinedload(TransporterProfile.service_areas))
            .filter(TransporterProfile.user_id == user_id)
            .first()
        )

    def get_profile_by_id(self, profile_id: uuid.UUID) -> Optional[TransporterProfile]:
        """Fetch transporter profile by profile primary key."""
        return (
            self.db.query(TransporterProfile)
            .options(
                joinedload(TransporterProfile.service_areas),
                joinedload(TransporterProfile.user),
            )
            .filter(TransporterProfile.id == profile_id)
            .first()
        )

    def update_profile(
        self, profile: TransporterProfile, update_data: dict
    ) -> TransporterProfile:
        """Update mutable fields of a transporter profile."""
        for field, value in update_data.items():
            if hasattr(profile, field) and value is not None:
                setattr(profile, field, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_service_areas(self, profile_id: uuid.UUID) -> List[ServiceArea]:
        """List all service areas for a given transporter profile."""
        return (
            self.db.query(ServiceArea)
            .filter(ServiceArea.transporter_profile_id == profile_id)
            .order_by(ServiceArea.state.asc(), ServiceArea.district.asc())
            .all()
        )

    def get_service_area_by_id(self, service_area_id: uuid.UUID) -> Optional[ServiceArea]:
        """Fetch single service area by primary key."""
        return (
            self.db.query(ServiceArea)
            .filter(ServiceArea.id == service_area_id)
            .first()
        )

    def find_duplicate_service_area(
        self,
        profile_id: uuid.UUID,
        state: str,
        district: str,
        coverage_type: str,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> Optional[ServiceArea]:
        """Check for existing duplicate service area."""
        query = self.db.query(ServiceArea).filter(
            ServiceArea.transporter_profile_id == profile_id,
            func.lower(ServiceArea.state) == state.strip().lower(),
            func.lower(ServiceArea.district) == district.strip().lower(),
            ServiceArea.coverage_type == coverage_type,
        )
        if exclude_id:
            query = query.filter(ServiceArea.id != exclude_id)
        return query.first()

    def add_service_area(self, service_area: ServiceArea) -> ServiceArea:
        """Persist a new service area."""
        self.db.add(service_area)
        self.db.commit()
        self.db.refresh(service_area)
        return service_area

    def update_service_area(
        self, service_area: ServiceArea, update_data: dict
    ) -> ServiceArea:
        """Update service area attributes."""
        for field, value in update_data.items():
            if hasattr(service_area, field) and value is not None:
                setattr(service_area, field, value)
        self.db.commit()
        self.db.refresh(service_area)
        return service_area

    def delete_service_area(self, service_area: ServiceArea) -> None:
        """Permanently delete a service area."""
        self.db.delete(service_area)
        self.db.commit()

    def search_transporters(
        self,
        pickup_state: Optional[str] = None,
        pickup_district: Optional[str] = None,
        delivery_state: Optional[str] = None,
        delivery_district: Optional[str] = None,
        transport_type: Optional[str] = None,
        min_capacity_kg: Optional[Decimal] = None,
        only_available: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[TransporterProfile]]:
        """Search available transporters based on location coverage and vehicle specs.

        Matches transporters where:
        - Active transporter with active account
        - If pickup location given: has active service area covering pickup (pickup_only or both)
        - If delivery location given: has active service area covering delivery (delivery_only or both)
        - If transport_type given: matches type
        - If min_capacity_kg given: vehicle_capacity_kg >= min_capacity_kg
        """
        query = (
            self.db.query(TransporterProfile)
            .join(TransporterProfile.user)
            .filter(User.account_status == "active")
            .filter(User.verification_status == "verified")
            .options(
                joinedload(TransporterProfile.service_areas),
                joinedload(TransporterProfile.user),
            )
        )

        if only_available:
            query = query.filter(TransporterProfile.is_available == True)  # noqa: E712

        if transport_type:
            query = query.filter(
                func.lower(TransporterProfile.transport_type) == transport_type.strip().lower()
            )

        if min_capacity_kg is not None:
            query = query.filter(TransporterProfile.vehicle_capacity_kg >= min_capacity_kg)

        # Apply pickup coverage filter if specified
        if pickup_state:
            pickup_filter = ServiceArea.is_active == True  # noqa: E712
            pickup_filter = pickup_filter & (func.lower(ServiceArea.state) == pickup_state.strip().lower())
            if pickup_district:
                pickup_filter = pickup_filter & (func.lower(ServiceArea.district) == pickup_district.strip().lower())
            pickup_filter = pickup_filter & (ServiceArea.coverage_type.in_(("pickup_only", "both")))

            matching_profile_ids = (
                self.db.query(ServiceArea.transporter_profile_id)
                .filter(pickup_filter)
                .scalar_subquery()
            )
            query = query.filter(TransporterProfile.id.in_(matching_profile_ids))

        # Apply delivery coverage filter if specified
        if delivery_state:
            delivery_filter = ServiceArea.is_active == True  # noqa: E712
            delivery_filter = delivery_filter & (func.lower(ServiceArea.state) == delivery_state.strip().lower())
            if delivery_district:
                delivery_filter = delivery_filter & (func.lower(ServiceArea.district) == delivery_district.strip().lower())
            delivery_filter = delivery_filter & (ServiceArea.coverage_type.in_(("delivery_only", "both")))

            matching_delivery_ids = (
                self.db.query(ServiceArea.transporter_profile_id)
                .filter(delivery_filter)
                .scalar_subquery()
            )
            query = query.filter(TransporterProfile.id.in_(matching_delivery_ids))

        total = query.distinct().count()
        results = (
            query.distinct()
            .order_by(TransporterProfile.experience_years.desc(), TransporterProfile.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, results

    def get_order_by_id(self, order_id: uuid.UUID) -> Optional[Order]:
        """Fetch order by ID for transport coordination."""
        return (
            self.db.query(Order)
            .options(joinedload(Order.transporter))
            .filter(Order.id == order_id)
            .first()
        )

    def save_order(self, order: Order) -> Order:
        """Persist order modifications."""
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_offer_by_id(self, offer_id: uuid.UUID) -> Optional[Offer]:
        """Fetch offer by ID for transport connection verification."""
        return (
            self.db.query(Offer)
            .options(joinedload(Offer.sender), joinedload(Offer.recipient), joinedload(Offer.items))
            .filter(Offer.id == offer_id)
            .first()
        )

    def create_connection_request(
        self, request: TransportConnectionRequest
    ) -> TransportConnectionRequest:
        """Persist a new transport connection request."""
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_connection_request_by_id(
        self, request_id: uuid.UUID
    ) -> Optional[TransportConnectionRequest]:
        """Fetch transport connection request by ID with relations."""
        return (
            self.db.query(TransportConnectionRequest)
            .options(
                joinedload(TransportConnectionRequest.requester),
                joinedload(TransportConnectionRequest.transporter),
                joinedload(TransportConnectionRequest.order),
                joinedload(TransportConnectionRequest.offer),
            )
            .filter(TransportConnectionRequest.id == request_id)
            .first()
        )

    def find_existing_pending_request(
        self,
        requester_id: uuid.UUID,
        transporter_id: uuid.UUID,
        order_id: Optional[uuid.UUID] = None,
        offer_id: Optional[uuid.UUID] = None,
    ) -> Optional[TransportConnectionRequest]:
        """Check if an active pending or awaiting-approval request already exists between requester and transporter for this deal."""
        query = self.db.query(TransportConnectionRequest).filter(
            TransportConnectionRequest.requester_id == requester_id,
            TransportConnectionRequest.transporter_id == transporter_id,
            TransportConnectionRequest.status.in_(["pending", "transporter_accepted", "accepted"]),
        )
        if order_id:
            query = query.filter(TransportConnectionRequest.order_id == order_id)
        if offer_id:
            query = query.filter(TransportConnectionRequest.offer_id == offer_id)
        return query.first()

    def list_connection_requests(
        self,
        user_id: uuid.UUID,
        role: str,
        status: Optional[str] = None,
        order_id: Optional[uuid.UUID] = None,
        offer_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[TransportConnectionRequest]]:
        """List connection requests relevant to the user (transporter or requester/deal participant)."""
        query = (
            self.db.query(TransportConnectionRequest)
            .options(
                joinedload(TransportConnectionRequest.requester),
                joinedload(TransportConnectionRequest.transporter),
                joinedload(TransportConnectionRequest.order),
                joinedload(TransportConnectionRequest.offer),
            )
        )

        if role == "transporter":
            query = query.filter(TransportConnectionRequest.transporter_id == user_id)
        elif role in ("farmer", "buyer"):
            # Can see requests where they are requester, or participant on the order/offer
            if order_id:
                query = query.filter(TransportConnectionRequest.order_id == order_id)
            elif offer_id:
                query = query.filter(TransportConnectionRequest.offer_id == offer_id)
            else:
                query = query.outerjoin(TransportConnectionRequest.order).outerjoin(TransportConnectionRequest.offer).filter(
                    or_(
                        TransportConnectionRequest.requester_id == user_id,
                        Order.buyer_id == user_id,
                        Order.farmer_id == user_id,
                        Offer.sender_id == user_id,
                        Offer.recipient_id == user_id,
                    )
                )
        elif role != "admin":
            query = query.filter(TransportConnectionRequest.requester_id == user_id)

        if order_id and role not in ("farmer", "buyer"):
            query = query.filter(TransportConnectionRequest.order_id == order_id)
        if offer_id and role not in ("farmer", "buyer"):
            query = query.filter(TransportConnectionRequest.offer_id == offer_id)

        if status:
            query = query.filter(TransportConnectionRequest.status == status.strip().lower())

        total = query.distinct().count()
        results = (
            query.distinct()
            .order_by(TransportConnectionRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, results

    def save_connection_request(
        self, request: TransportConnectionRequest
    ) -> TransportConnectionRequest:
        """Persist state updates to a connection request."""
        self.db.commit()
        self.db.refresh(request)
        return request
