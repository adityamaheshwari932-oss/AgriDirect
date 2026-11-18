"""Pydantic v2 schemas for authentication, registration, and user profiles.

Enforces input validation, password security constraints, and safe serialization
excluding sensitive credentials.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.user import VALID_BUYER_TYPES


class PasswordConfirmationMixin(BaseModel):
    """Mixin to validate that password_confirm matches password when provided."""

    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")
    password_confirm: Optional[str] = Field(
        None, min_length=8, max_length=128, description="Password confirmation"
    )

    @field_validator("password")
    @classmethod
    def validate_password_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Password must not be blank")
        return value

    @model_validator(mode="after")
    def verify_password_match(self) -> "PasswordConfirmationMixin":
        if self.password_confirm is not None and self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class FarmerRegisterRequest(PasswordConfirmationMixin):
    """Payload for farmer registration."""

    email: EmailStr = Field(..., description="Unique email address")
    full_name: str = Field(..., min_length=1, max_length=128, description="Full name of farmer")
    phone_number: Optional[str] = Field(None, max_length=32, description="Optional phone number")

    # Optional initial profile details with sensible defaults
    farm_name: Optional[str] = Field(None, max_length=128, description="Farm or enterprise name")
    farm_location_address: Optional[str] = Field(
        None, max_length=255, description="Physical farm address"
    )
    city: Optional[str] = Field(None, max_length=64, description="City or nearest town")
    state: Optional[str] = Field(None, max_length=64, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=16, description="Postal code")

    latitude: Optional[Decimal] = Field(None, description="Farm GPS latitude")
    longitude: Optional[Decimal] = Field(None, description="Farm GPS longitude")
    farm_size_acres: Optional[Decimal] = Field(
        None, gt=0, description="Total farm size in acres (must be > 0)"
    )
    farming_practices: Optional[str] = Field(None, max_length=64, description="Farming practices")
    primary_crops: Optional[str] = Field(None, description="Primary crops produced")
    bio: Optional[str] = Field(None, description="Short biography or farm overview")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("full_name must not be empty or blank")
        return stripped


class BuyerRegisterRequest(PasswordConfirmationMixin):
    """Payload for buyer registration."""

    email: EmailStr = Field(..., description="Unique commercial email address")
    contact_person_name: Optional[str] = Field(
        None, max_length=128, description="Name of procurement contact person"
    )
    full_name: Optional[str] = Field(
        None, max_length=128, description="Alternative field for contact person name"
    )
    business_name: Optional[str] = Field(None, max_length=128, description="Commercial entity name")
    business_type: str = Field(
        "other",
        max_length=64,
        description="Type of business (restaurant, hotel, retailer, wholesaler, processor, caterer, other)",
    )
    business_registration_number: Optional[str] = Field(
        None, max_length=64, description="Tax or corporate registration ID"
    )
    phone_number: Optional[str] = Field(None, max_length=32, description="Contact phone number")

    delivery_receiving_address: Optional[str] = Field(
        None, max_length=255, description="Receiving dock or delivery address"
    )
    city: Optional[str] = Field(None, max_length=64, description="City")
    state: Optional[str] = Field(None, max_length=64, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=16, description="Postal code")

    latitude: Optional[Decimal] = Field(None, description="Facility GPS latitude")
    longitude: Optional[Decimal] = Field(None, description="Facility GPS longitude")
    procurement_summary: Optional[str] = Field(None, description="Procurement volume or produce summary")
    bio: Optional[str] = Field(None, description="Business description")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, value: str) -> str:
        normalised = value.strip().lower()
        if normalised not in VALID_BUYER_TYPES:
            raise ValueError(
                f"Invalid business_type '{value}'. Must be one of: {', '.join(VALID_BUYER_TYPES)}"
            )
        return normalised

    @model_validator(mode="after")
    def validate_contact_name_provided(self) -> "BuyerRegisterRequest":
        name = self.contact_person_name or self.full_name
        if not name or not name.strip():
            raise ValueError("Either contact_person_name or full_name must be provided")
        return self


class LoginRequest(BaseModel):
    """Credentials payload for account login."""

    email: EmailStr = Field(..., description="Account email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class FarmerProfileRead(BaseModel):
    """Public read model for farmer profile."""

    id: uuid.UUID
    full_name: str
    farm_name: str
    farm_location_address: str
    city: str
    state: str
    postal_code: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    farm_size_acres: Optional[Decimal] = None
    farming_practices: Optional[str] = None
    primary_crops: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuyerProfileRead(BaseModel):
    """Public read model for buyer profile."""

    id: uuid.UUID
    contact_person_name: str
    business_name: str
    business_type: str
    business_registration_number: Optional[str] = None
    delivery_receiving_address: str
    city: str
    state: str
    postal_code: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    procurement_summary: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


from app.transporters.schemas import (
    TransporterProfileRead,
    TransporterRegisterRequest,
)


class UserRead(BaseModel):
    """Public read model for user account, excluding password hash."""

    id: uuid.UUID
    email: str
    phone_number: Optional[str] = None
    role: str
    verification_status: str
    account_status: str
    created_at: datetime
    updated_at: datetime

    farmer_profile: Optional[FarmerProfileRead] = None
    buyer_profile: Optional[BuyerProfileRead] = None
    transporter_profile: Optional[TransporterProfileRead] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT Bearer access token response."""

    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field("bearer", description="Token type")
    user: UserRead = Field(..., description="Authenticated user account details")
