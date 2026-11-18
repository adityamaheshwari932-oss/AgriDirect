"""Service layer for authentication, registration, and credential validation.

Enforces business rules defined in AGENTS.md and schema specifications:
- Passwords hashed using Argon2id via app.core.security.
- Roles assigned strictly on the server.
- Initial verification status set to 'unverified'.
- Initial account status set to 'active'.
- Uniqueness conflicts handled and translated to 409 Conflict.
- Generic error messages for failed authentication (401 Unauthorized).
- Suspended or restricted accounts rejected on login (403 Forbidden).
"""

from fastapi import HTTPException, status

from app.auth.repository import AuthRepository, DuplicateEntityException
from app.auth.schemas import (
    BuyerRegisterRequest,
    FarmerRegisterRequest,
    LoginRequest,
    TokenResponse,
    TransporterRegisterRequest,
    UserRead,
)
from app.core.security import hash_password, verify_password
from app.dependencies import create_access_token
from app.models.user import BuyerProfile, FarmerProfile, ServiceArea, TransporterProfile, User


class AuthService:
    """Orchestrates authentication, user registration, and access token issuance."""

    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    def register_farmer(self, payload: FarmerRegisterRequest) -> User:
        """Register a new farmer account and initialize their farm profile.

        Args:
            payload: Validated farmer registration data.

        Returns:
            The newly created User model instance.

        Raises:
            HTTPException: 409 Conflict if email or phone number already exists.
        """
        normalized_email = payload.email.strip().lower()

        # Database-backed duplicate check
        if self.repository.get_user_by_email(normalized_email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists",
            )

        if payload.phone_number and self.repository.get_user_by_phone(payload.phone_number) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this phone number already exists",
            )

        # Hash password securely using Argon2id
        hashed_password = hash_password(payload.password)

        # Server-enforced role and defaults
        user = User(
            email=normalized_email,
            phone_number=payload.phone_number,
            password_hash=hashed_password,
            role="farmer",
            verification_status="unverified",
            account_status="active",
        )

        profile = FarmerProfile(
            full_name=payload.full_name,
            farm_name=payload.farm_name or f"{payload.full_name}'s Farm",
            farm_location_address=payload.farm_location_address or "Not Specified",
            city=payload.city or "Not Specified",
            state=payload.state or "Not Specified",
            postal_code=payload.postal_code or "000000",
            latitude=payload.latitude,
            longitude=payload.longitude,
            farm_size_acres=payload.farm_size_acres,
            farming_practices=payload.farming_practices,
            primary_crops=payload.primary_crops,
            bio=payload.bio,
        )

        try:
            return self.repository.create_farmer(user, profile)
        except DuplicateEntityException as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    def register_buyer(self, payload: BuyerRegisterRequest) -> User:
        """Register a new commercial buyer account and initialize their profile.

        Args:
            payload: Validated buyer registration data.

        Returns:
            The newly created User model instance.

        Raises:
            HTTPException: 409 Conflict if email or phone number already exists.
        """
        normalized_email = payload.email.strip().lower()

        # Database-backed duplicate check
        if self.repository.get_user_by_email(normalized_email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists",
            )

        if payload.phone_number and self.repository.get_user_by_phone(payload.phone_number) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this phone number already exists",
            )

        # Hash password securely using Argon2id
        hashed_password = hash_password(payload.password)

        contact_name = payload.contact_person_name or payload.full_name or "Contact Person"

        # Server-enforced role and defaults
        user = User(
            email=normalized_email,
            phone_number=payload.phone_number,
            password_hash=hashed_password,
            role="buyer",
            verification_status="unverified",
            account_status="active",
        )

        profile = BuyerProfile(
            contact_person_name=contact_name,
            business_name=payload.business_name or f"{contact_name}'s Business",
            business_type=payload.business_type,
            business_registration_number=payload.business_registration_number,
            delivery_receiving_address=payload.delivery_receiving_address or "Not Specified",
            city=payload.city or "Not Specified",
            state=payload.state or "Not Specified",
            postal_code=payload.postal_code or "000000",
            latitude=payload.latitude,
            longitude=payload.longitude,
            procurement_summary=payload.procurement_summary,
            bio=payload.bio,
        )

        try:
            return self.repository.create_buyer(user, profile)
        except DuplicateEntityException as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    def register_transporter(self, payload: TransporterRegisterRequest) -> User:
        """Register a new transporter account and initialize their profile.

        Args:
            payload: Validated transporter registration data.

        Returns:
            The newly created User model instance.

        Raises:
            HTTPException: 409 Conflict if email or phone number already exists.
        """
        normalized_email = payload.email.strip().lower()

        if self.repository.get_user_by_email(normalized_email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists",
            )

        if payload.phone_number and self.repository.get_user_by_phone(payload.phone_number) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this phone number already exists",
            )

        hashed_password = hash_password(payload.password)

        user = User(
            email=normalized_email,
            phone_number=payload.phone_number,
            password_hash=hashed_password,
            role="transporter",
            verification_status="unverified",
            account_status="active",
        )

        profile = TransporterProfile(
            business_name=payload.business_name,
            contact_name=payload.contact_name,
            phone_number=payload.phone_number,
            transport_type=payload.transport_type,
            vehicle_capacity_kg=payload.vehicle_capacity_kg,
            vehicle_registration_number=payload.vehicle_registration_number,
            is_available=True,
            experience_years=payload.experience_years,
            operating_states=payload.operating_states,
            bio=payload.bio,
        )

        service_areas = []
        if payload.initial_service_areas:
            for sa in payload.initial_service_areas:
                service_areas.append(
                    ServiceArea(
                        state=sa.state,
                        district=sa.district,
                        taluka_subdistrict=sa.taluka_subdistrict,
                        village_town=sa.village_town,
                        pincode=sa.pincode,
                        coverage_type=sa.coverage_type,
                        is_active=sa.is_active,
                    )
                )

        try:
            return self.repository.create_transporter(user, profile, service_areas)
        except DuplicateEntityException as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    def authenticate(self, payload: LoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue a signed JWT access token.

        Args:
            payload: User login credentials.

        Returns:
            TokenResponse containing Bearer access token and safe UserRead profile.

        Raises:
            HTTPException: 401 Unauthorized if email or password is invalid.
            HTTPException: 403 Forbidden if account is inactive, suspended, or blocked.
        """
        normalized_email = payload.email.strip().lower()
        user = self.repository.get_user_by_email(normalized_email)

        # Generic 401 response without disclosing whether email or password was wrong
        generic_unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if user is None or not verify_password(payload.password, user.password_hash):
            raise generic_unauthorized

        # Account status check: suspended and blocked users cannot log in
        if user.account_status in ("suspended", "blocked"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended or restricted",
            )

        # Generate JWT token using configured algorithm and expiration
        token_claims = {
            "sub": str(user.id),
            "role": user.role,
            "status": user.verification_status,
        }
        access_token = create_access_token(token_claims)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        )
