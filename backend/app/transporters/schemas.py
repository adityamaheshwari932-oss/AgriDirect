"""Pydantic schemas for the Transporter module.

Covers transporter registration, profile management, service area definitions,
marketplace discovery, and order transport coordination.
"""

from datetime import date, datetime
from decimal import Decimal
import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

VALID_TRANSPORT_TYPES = (
    "mini_truck",
    "open_body",
    "refrigerated",
    "covered_truck",
    "tempo",
    "trailer",
    "other",
)

VALID_COVERAGE_TYPES = ("pickup_only", "delivery_only", "both")

VALID_TRANSPORT_STATUSES = ("none", "assigned", "in_transit", "delivered", "cancelled")


class ServiceAreaCreate(BaseModel):
    """Payload to register a new serviceable area."""

    model_config = ConfigDict(extra="forbid")

    state: str = Field(..., min_length=2, max_length=64, description="State name (e.g. Maharashtra)")
    district: str = Field(..., min_length=2, max_length=64, description="District name (e.g. Pune)")
    taluka_subdistrict: Optional[str] = Field(None, max_length=64, description="Taluka or subdistrict")
    village_town: Optional[str] = Field(None, max_length=64, description="Village or town")
    pincode: Optional[str] = Field(None, max_length=16, description="Postal pincode")
    coverage_type: str = Field(
        "both",
        description="Coverage type: pickup_only, delivery_only, or both",
    )
    is_active: bool = Field(True, description="Whether this service area is currently active")

    @field_validator("state", "district")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        s = value.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s

    @field_validator("coverage_type")
    @classmethod
    def validate_coverage(cls, value: str) -> str:
        s = value.strip().lower()
        if s not in VALID_COVERAGE_TYPES:
            raise ValueError(f"Invalid coverage_type '{value}'. Must be one of: {', '.join(VALID_COVERAGE_TYPES)}")
        return s


class ServiceAreaUpdate(BaseModel):
    """Payload to update an existing service area."""

    model_config = ConfigDict(extra="forbid")

    taluka_subdistrict: Optional[str] = Field(None, max_length=64)
    village_town: Optional[str] = Field(None, max_length=64)
    pincode: Optional[str] = Field(None, max_length=16)
    coverage_type: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)

    @field_validator("coverage_type")
    @classmethod
    def validate_coverage(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        s = value.strip().lower()
        if s not in VALID_COVERAGE_TYPES:
            raise ValueError(f"Invalid coverage_type '{value}'. Must be one of: {', '.join(VALID_COVERAGE_TYPES)}")
        return s


class ServiceAreaRead(BaseModel):
    """Read representation of a service area."""

    id: uuid.UUID
    transporter_profile_id: uuid.UUID
    state: str
    district: str
    taluka_subdistrict: Optional[str] = None
    village_town: Optional[str] = None
    pincode: Optional[str] = None
    coverage_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransporterRegisterRequest(BaseModel):
    """Payload for registering a new Transporter account."""

    email: EmailStr = Field(..., description="Account email address")
    password: str = Field(..., min_length=8, description="Argon2id hashed account password")
    phone_number: str = Field(..., min_length=10, max_length=32, description="Contact phone number")
    business_name: str = Field(..., min_length=2, max_length=128, description="Registered transport business name")
    contact_name: str = Field(..., min_length=2, max_length=128, description="Primary contact person name")
    transport_type: str = Field(..., description="Vehicle or fleet type (e.g. mini_truck, refrigerated)")
    vehicle_capacity_kg: Decimal = Field(..., gt=0, description="Payload capacity in kilograms")
    vehicle_registration_number: str = Field(..., min_length=3, max_length=64, description="Vehicle registration plate")
    experience_years: int = Field(0, ge=0, description="Years in logistics experience")
    operating_states: Optional[str] = Field(None, max_length=255, description="Operating regions / states summary")
    bio: Optional[str] = Field(None, description="Company bio or capability overview")
    initial_service_areas: Optional[List[ServiceAreaCreate]] = Field(None, description="Optional initial service areas")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("business_name", "contact_name", "vehicle_registration_number")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        s = value.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s

    @field_validator("transport_type")
    @classmethod
    def validate_transport_type(cls, value: str) -> str:
        norm = value.strip().lower()
        if norm not in VALID_TRANSPORT_TYPES:
            raise ValueError(f"Invalid transport_type '{value}'. Must be one of: {', '.join(VALID_TRANSPORT_TYPES)}")
        return norm


class TransporterProfileRead(BaseModel):
    """Public read model for transporter profile."""

    id: uuid.UUID
    business_name: str
    contact_name: str
    phone_number: str
    transport_type: str
    vehicle_capacity_kg: Decimal
    vehicle_registration_number: str
    is_available: bool
    experience_years: int
    operating_states: Optional[str] = None
    bio: Optional[str] = None
    verification_status: str = "verified"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransporterDetailRead(TransporterProfileRead):
    """Detailed read model including active service areas."""

    service_areas: List[ServiceAreaRead] = Field(default_factory=list)


class TransporterProfileUpdate(BaseModel):
    """Payload for updating transporter profile."""

    model_config = ConfigDict(extra="forbid")

    business_name: Optional[str] = Field(None, min_length=2, max_length=128)
    contact_name: Optional[str] = Field(None, min_length=2, max_length=128)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=32)
    transport_type: Optional[str] = Field(None)
    vehicle_capacity_kg: Optional[Decimal] = Field(None, gt=0)
    vehicle_registration_number: Optional[str] = Field(None, min_length=3, max_length=64)
    is_available: Optional[bool] = Field(None)
    experience_years: Optional[int] = Field(None, ge=0)
    operating_states: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None)

    @field_validator("transport_type")
    @classmethod
    def validate_transport_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        norm = value.strip().lower()
        if norm not in VALID_TRANSPORT_TYPES:
            raise ValueError(f"Invalid transport_type '{value}'. Must be one of: {', '.join(VALID_TRANSPORT_TYPES)}")
        return norm


class TransporterSearchResult(BaseModel):
    """Result item for transporter discovery."""

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    contact_name: str
    phone_number: str
    transport_type: str
    vehicle_capacity_kg: Decimal
    vehicle_registration_number: str
    is_available: bool
    experience_years: int
    operating_states: Optional[str] = None
    bio: Optional[str] = None
    verification_status: str = "verified"
    service_areas: List[ServiceAreaRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TransporterSearchResponse(BaseModel):
    """Search results response wrapper."""

    total: int
    items: List[TransporterSearchResult]


VALID_TRANSPORT_REQUEST_STATUSES = ("pending", "accepted", "declined", "cancelled")


class TransportConnectionRequestCreate(BaseModel):
    """Payload to initiate a transportation service connection request."""

    model_config = ConfigDict(extra="forbid")

    transporter_user_id: uuid.UUID = Field(..., description="Target transporter user ID")
    order_id: Optional[uuid.UUID] = Field(None, description="Optional associated order ID")
    offer_id: Optional[uuid.UUID] = Field(None, description="Optional associated offer ID")

    pickup_state: Optional[str] = Field(None, max_length=64)
    pickup_district: Optional[str] = Field(None, max_length=64)
    pickup_address: Optional[str] = Field(None)

    delivery_state: Optional[str] = Field(None, max_length=64)
    delivery_district: Optional[str] = Field(None, max_length=64)
    delivery_address: Optional[str] = Field(None)

    cargo_description: Optional[str] = Field(None, max_length=255)
    weight_kg: Optional[Decimal] = Field(None, gt=0)
    required_delivery_date: Optional[date] = Field(None)
    notes: Optional[str] = Field(None)


class TransportConnectionRequestResponse(BaseModel):
    """Payload to respond to a connection request (accept or decline)."""

    model_config = ConfigDict(extra="forbid")

    response_notes: Optional[str] = Field(None, description="Optional transporter response notes")
    rejection_reason: Optional[str] = Field(None, description="Reason if declining the request")


class TransportConnectionRequestRead(BaseModel):
    """Read model for transport connection request."""

    id: uuid.UUID
    requester_id: uuid.UUID
    transporter_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    offer_id: Optional[uuid.UUID] = None
    order_number: Optional[str] = None
    offer_number: Optional[str] = None

    requester_name: str
    requester_role: str
    transporter_business_name: str
    transporter_contact_name: str
    transporter_phone: str

    pickup_state: Optional[str] = None
    pickup_district: Optional[str] = None
    pickup_address: Optional[str] = None

    delivery_state: Optional[str] = None
    delivery_district: Optional[str] = None
    delivery_address: Optional[str] = None

    cargo_description: Optional[str] = None
    weight_kg: Optional[Decimal] = None
    required_delivery_date: Optional[date] = None
    notes: Optional[str] = None

    status: str
    rejection_reason: Optional[str] = None
    response_notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransportConnectionRequestListResponse(BaseModel):
    """List response wrapper for connection requests."""

    total: int
    items: List[TransportConnectionRequestRead]


class OrderTransportCoordinationRequest(BaseModel):
    """Payload to coordinate transportation for an order."""

    model_config = ConfigDict(extra="forbid")

    transporter_user_id: Optional[uuid.UUID] = Field(None, description="Selected transporter user ID")
    transport_status: Optional[str] = Field(None, description="New transport status: assigned, in_transit, delivered")
    delivery_notes: Optional[str] = Field(None, description="Optional transport notes or dispatch instructions")

    @field_validator("transport_status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        norm = value.strip().lower()
        if norm not in VALID_TRANSPORT_STATUSES:
            raise ValueError(f"Invalid transport_status '{value}'. Must be one of: {', '.join(VALID_TRANSPORT_STATUSES)}")
        return norm


class OrderTransportCoordinationResponse(BaseModel):
    """Response after updating order transport coordination."""

    order_id: uuid.UUID
    order_number: str
    transporter_id: Optional[uuid.UUID] = None
    transporter_business_name: Optional[str] = None
    transporter_phone: Optional[str] = None
    transport_status: str
    delivery_notes: Optional[str] = None
