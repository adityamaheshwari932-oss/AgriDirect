"""FastAPI route handlers for user profiles and account management.

Endpoints:
- GET /api/v1/users/me — Get authenticated user account and profile
- PATCH /api/v1/users/me — Update own profile (role-aware partial update)
- PATCH /api/v1/users/me/farmer — Dedicated farmer profile update
- PATCH /api/v1/users/me/buyer — Dedicated buyer profile update
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.schemas import UserRead
from app.db.session import get_db
from app.dependencies import (
    get_current_active_user,
    require_buyer,
    require_farmer,
)
from app.models.user import User
from app.users.repository import UserRepository
from app.users.schemas import (
    BuyerProfileUpdate,
    FarmerProfileUpdate,
    UserProfileUpdate,
)
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description=(
        "Returns the safe account details and attached profile (farmer or buyer) "
        "for the currently authenticated active user. Requires a valid JWT Bearer token."
    ),
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    """Return the profile for the authenticated active user."""
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update current authenticated user profile",
    description=(
        "Updates permitted profile fields for the authenticated active user. "
        "Rejects cross-role fields (e.g. farmers updating buyer fields or vice versa) "
        "and server-controlled attributes (role, verification status, account status, email)."
    ),
)
def update_current_user_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Update own profile with role-enforced field validation."""
    service = UserService(UserRepository(db))
    updated_user = service.update_profile(current_user, payload)
    return UserRead.model_validate(updated_user)


@router.patch(
    "/me/farmer",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update dedicated farmer profile",
    description=(
        "Updates farm location, land acreage, farming practices, and contact details. "
        "Requires authenticated active farmer role."
    ),
)
def update_farmer_profile(
    payload: FarmerProfileUpdate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> UserRead:
    """Update farmer profile fields."""
    service = UserService(UserRepository(db))
    updated_user = service.update_farmer_profile(current_user, payload)
    return UserRead.model_validate(updated_user)


@router.patch(
    "/me/buyer",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update dedicated buyer profile",
    description=(
        "Updates commercial entity name, business type, delivery receiving address, and details. "
        "Requires authenticated active buyer role."
    ),
)
def update_buyer_profile(
    payload: BuyerProfileUpdate,
    current_user: User = Depends(require_buyer),
    db: Session = Depends(get_db),
) -> UserRead:
    """Update commercial buyer profile fields."""
    service = UserService(UserRepository(db))
    updated_user = service.update_buyer_profile(current_user, payload)
    return UserRead.model_validate(updated_user)
