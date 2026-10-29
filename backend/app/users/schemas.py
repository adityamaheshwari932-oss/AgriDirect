"""Pydantic v2 schemas for user profile retrieval and updates.

Enforces strict input validation, rejects unknown or forbidden fields via extra='forbid',
and protects server-controlled security attributes (role, status, email, id).
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import VALID_BUYER_TYPES


class FarmerProfileUpdate(BaseModel):
    """Payload for updating farmer-specific profile fields.

    All fields are optional; only provided (unset=False) fields are updated.
    Server-controlled fields (role, verification_status, account_status, id, email)
    are strictly forbidden and rejected via extra='forbid'.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(None, min_length=1, max_length=128, description="Farmer full name")
    farm_name: Optional[str] = Field(None, min_length=1, max_length=128, description="Farm or enterprise name")
    farm_location_address: Optional[str] = Field(None, max_length=255, description="Physical farm address")
    city: Optional[str] = Field(None, max_length=64, description="City, district, or nearest town")
    state: Optional[str] = Field(None, max_length=64, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=16, description="Postal code")

    latitude: Optional[Decimal] = Field(None, ge=-90, le=90, description="Farm GPS latitude")
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180, description="Farm GPS longitude")
    farm_size_acres: Optional[Decimal] = Field(None, gt=0, description="Cultivated area in acres (> 0)")
    farming_practices: Optional[str] = Field(None, max_length=64, description="Farming practices (organic, etc.)")
    primary_crops: Optional[str] = Field(None, description="Primary crops cultivated")
    bio: Optional[str] = Field(None, description="Narrative overview of farm capacity")

    phone_number: Optional[str] = Field(None, max_length=32, description="Contact phone number")

    @field_validator("full_name", "farm_name", "farm_location_address", "city", "state", "postal_code")
    @classmethod
    def validate_non_blank_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value


class BuyerProfileUpdate(BaseModel):
    """Payload for updating buyer-specific profile fields.

    All fields are optional; only provided (unset=False) fields are updated.
    Server-controlled fields (role, verification_status, account_status, id, email)
    are strictly forbidden and rejected via extra='forbid'.
    """

    model_config = ConfigDict(extra="forbid")

    contact_person_name: Optional[str] = Field(
        None, min_length=1, max_length=128, description="Procurement contact name"
    )
    business_name: Optional[str] = Field(
        None, min_length=1, max_length=128, description="Commercial entity name"
    )
    business_type: Optional[str] = Field(
        None,
        max_length=64,
        description="Business category (restaurant, hotel, retailer, wholesaler, processor, caterer, other)",
    )
    business_registration_number: Optional[str] = Field(
        None, max_length=64, description="Corporate CIN, GSTIN, or trade registration ID"
    )
    delivery_receiving_address: Optional[str] = Field(
        None, max_length=255, description="Primary delivery or warehouse receiving dock"
    )
    city: Optional[str] = Field(None, max_length=64, description="City or municipality")
    state: Optional[str] = Field(None, max_length=64, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=16, description="Postal code")

    latitude: Optional[Decimal] = Field(None, ge=-90, le=90, description="Facility GPS latitude")
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180, description="Facility GPS longitude")
    procurement_summary: Optional[str] = Field(None, description="Procurement volume or produce sourcing summary")
    bio: Optional[str] = Field(None, description="Commercial profile narrative")

    phone_number: Optional[str] = Field(None, max_length=32, description="Contact phone number")

    @field_validator(
        "contact_person_name",
        "business_name",
        "delivery_receiving_address",
        "city",
        "state",
        "postal_code",
    )
    @classmethod
    def validate_non_blank_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            normalised = value.strip().lower()
            if normalised not in VALID_BUYER_TYPES:
                raise ValueError(
                    f"Invalid business_type '{value}'. Must be one of: {', '.join(VALID_BUYER_TYPES)}"
                )
            return normalised
        return value


class UserProfileUpdate(BaseModel):
    """Unified payload for PATCH /api/v1/users/me.

    Supports role-appropriate profile updates. Cross-role fields are validated
    and rejected in the service layer (e.g. farmers cannot update business_type;
    buyers cannot update farm_size_acres).
    Server-controlled fields are strictly forbidden via extra='forbid'.
    """

    model_config = ConfigDict(extra="forbid")

    # Shared account fields
    phone_number: Optional[str] = Field(None, max_length=32, description="Contact phone number")

    # Farmer fields
    full_name: Optional[str] = Field(None, min_length=1, max_length=128, description="Farmer full name")
    farm_name: Optional[str] = Field(None, min_length=1, max_length=128, description="Farm name")
    farm_location_address: Optional[str] = Field(None, max_length=255, description="Farm address")
    farm_size_acres: Optional[Decimal] = Field(None, gt=0, description="Farm size in acres")
    farming_practices: Optional[str] = Field(None, max_length=64, description="Farming practices")
    primary_crops: Optional[str] = Field(None, description="Primary crops produced")

    # Buyer fields
    contact_person_name: Optional[str] = Field(None, min_length=1, max_length=128, description="Buyer contact name")
    business_name: Optional[str] = Field(None, min_length=1, max_length=128, description="Business name")
    business_type: Optional[str] = Field(None, max_length=64, description="Business type")
    business_registration_number: Optional[str] = Field(None, max_length=64, description="Registration number")
    delivery_receiving_address: Optional[str] = Field(None, max_length=255, description="Receiving address")
    procurement_summary: Optional[str] = Field(None, description="Procurement requirements summary")

    # Shared geographical and bio fields
    city: Optional[str] = Field(None, max_length=64, description="City")
    state: Optional[str] = Field(None, max_length=64, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=16, description="Postal code")
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90, description="GPS latitude")
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180, description="GPS longitude")
    bio: Optional[str] = Field(None, description="Profile bio or narrative overview")

    @field_validator(
        "full_name",
        "farm_name",
        "farm_location_address",
        "contact_person_name",
        "business_name",
        "delivery_receiving_address",
        "city",
        "state",
        "postal_code",
    )
    @classmethod
    def validate_non_blank_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only")
            return stripped
        return value

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            normalised = value.strip().lower()
            if normalised not in VALID_BUYER_TYPES:
                raise ValueError(
                    f"Invalid business_type '{value}'. Must be one of: {', '.join(VALID_BUYER_TYPES)}"
                )
            return normalised
        return value
