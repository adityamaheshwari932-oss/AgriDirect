"""FastAPI route handlers for user profiles and account management.

Endpoints:
- GET /api/v1/users/me
"""

from fastapi import APIRouter, Depends, status

from app.auth.schemas import UserRead
from app.dependencies import get_current_active_user
from app.models.user import User

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
