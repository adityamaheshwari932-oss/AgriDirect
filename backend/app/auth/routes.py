"""FastAPI route handlers for authentication and user registration.

Endpoints:
- POST /api/v1/auth/register/farmer
- POST /api/v1/auth/register/buyer
- POST /api/v1/auth/login
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.repository import AuthRepository
from app.auth.schemas import (
    BuyerRegisterRequest,
    FarmerRegisterRequest,
    LoginRequest,
    TokenResponse,
    TransporterRegisterRequest,
    UserRead,
)
from app.auth.service import AuthService
from app.core.rate_limit import check_login_rate_limit
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register/farmer",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new farmer account",
    description=(
        "Registers a verified farmer account, initializes their farmer profile, "
        "and hashes their password using Argon2id. Server sets role to 'farmer', "
        "verification_status to 'unverified', and account_status to 'active'."
    ),
)
def register_farmer(
    payload: FarmerRegisterRequest,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new farmer."""
    service = AuthService(AuthRepository(db))
    user = service.register_farmer(payload)
    return UserRead.model_validate(user)


@router.post(
    "/register/buyer",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new commercial buyer account",
    description=(
        "Registers a commercial buyer account, initializes their business profile, "
        "and hashes their password using Argon2id. Server sets role to 'buyer', "
        "verification_status to 'unverified', and account_status to 'active'."
    ),
)
def register_buyer(
    payload: BuyerRegisterRequest,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new commercial buyer."""
    service = AuthService(AuthRepository(db))
    user = service.register_buyer(payload)
    return UserRead.model_validate(user)


@router.post(
    "/register/transporter",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new transportation provider account",
    description=(
        "Registers a transportation provider account, initializes their transporter profile "
        "and fleet details, and hashes their password using Argon2id. Server sets role to 'transporter', "
        "verification_status to 'unverified', and account_status to 'active'."
    ),
)
def register_transporter(
    payload: TransporterRegisterRequest,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new transporter."""
    service = AuthService(AuthRepository(db))
    user = service.register_transporter(payload)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
    description=(
        "Authenticates credentials against stored Argon2id password hash and returns "
        "a signed JWT Bearer access token. Rejects invalid credentials with a generic "
        "401 response, checks that account is active, and applies rate limiting."
    ),
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(check_login_rate_limit),
) -> TokenResponse:
    """Authenticate and obtain an access token."""
    service = AuthService(AuthRepository(db))
    return service.authenticate(payload)
