"""Service layer for user profile management.

Implements business logic, cross-role field enforcement, phone number uniqueness checks,
and atomic profile updates adhering to the permissions defined in AGENTS.md and SRS.
"""

from typing import Set

from fastapi import HTTPException, status

from app.models.user import User
from app.users.repository import DuplicatePhoneException, UserRepository
from app.users.schemas import BuyerProfileUpdate, FarmerProfileUpdate, UserProfileUpdate

FARMER_SPECIFIC_FIELDS: Set[str] = {
    "farm_name",
    "farm_location_address",
    "farm_size_acres",
    "farming_practices",
    "primary_crops",
}

BUYER_SPECIFIC_FIELDS: Set[str] = {
    "contact_person_name",
    "business_name",
    "business_type",
    "business_registration_number",
    "delivery_receiving_address",
    "procurement_summary",
}


class UserService:
    """Orchestrates user profile retrieval and role-enforced updates."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def get_profile(self, user: User) -> User:
        """Retrieve the profile model for an authenticated user.

        Args:
            user: Authenticated active user.

        Returns:
            The User instance with populated profile relationships.
        """
        return user

    def update_profile(self, user: User, payload: UserProfileUpdate) -> User:
        """Update profile fields for the authenticated user based on their role.

        Args:
            user: Authenticated active user.
            payload: Validated update payload.

        Returns:
            Updated User model instance.

        Raises:
            HTTPException: 400 Bad Request if cross-role fields are submitted.
            HTTPException: 409 Conflict if updated phone number is already taken.
        """
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return user

        # Check phone number uniqueness if provided
        phone_number = data.pop("phone_number", None)
        if phone_number is not None:
            self._validate_phone_uniqueness(user, phone_number)

        provided_keys = set(data.keys())

        if user.role == "farmer":
            forbidden = provided_keys & BUYER_SPECIFIC_FIELDS
            if forbidden:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Farmers cannot update buyer-specific profile fields: {', '.join(sorted(forbidden))}",
                )
            try:
                return self.repository.update_farmer_profile(user, data, phone_number=phone_number)
            except DuplicatePhoneException as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        elif user.role == "buyer":
            forbidden = provided_keys & FARMER_SPECIFIC_FIELDS
            if forbidden:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Buyers cannot update farmer-specific profile fields: {', '.join(sorted(forbidden))}",
                )
            try:
                return self.repository.update_buyer_profile(user, data, phone_number=phone_number)
            except DuplicatePhoneException as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        else:
            # Other roles (e.g. admin)
            if provided_keys:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrator accounts do not maintain farmer or buyer commercial profiles",
                )
            if phone_number is not None:
                user.phone_number = phone_number.strip() if phone_number else None
                self.repository.db.commit()
                self.repository.db.refresh(user)
            return user

    def update_farmer_profile(self, user: User, payload: FarmerProfileUpdate) -> User:
        """Update dedicated farmer profile fields.

        Args:
            user: Authenticated user (must have role='farmer').
            payload: Validated farmer update payload.

        Returns:
            Updated User model instance.

        Raises:
            HTTPException: 403 Forbidden if user role is not farmer.
            HTTPException: 409 Conflict if updated phone number is already taken.
        """
        if user.role != "farmer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a farmer account",
            )

        data = payload.model_dump(exclude_unset=True)
        phone_number = data.pop("phone_number", None)
        if phone_number is not None:
            self._validate_phone_uniqueness(user, phone_number)

        try:
            return self.repository.update_farmer_profile(user, data, phone_number=phone_number)
        except DuplicatePhoneException as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    def update_buyer_profile(self, user: User, payload: BuyerProfileUpdate) -> User:
        """Update dedicated buyer profile fields.

        Args:
            user: Authenticated user (must have role='buyer').
            payload: Validated buyer update payload.

        Returns:
            Updated User model instance.

        Raises:
            HTTPException: 403 Forbidden if user role is not buyer.
            HTTPException: 409 Conflict if updated phone number is already taken.
        """
        if user.role != "buyer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires a buyer account",
            )

        data = payload.model_dump(exclude_unset=True)
        phone_number = data.pop("phone_number", None)
        if phone_number is not None:
            self._validate_phone_uniqueness(user, phone_number)

        try:
            return self.repository.update_buyer_profile(user, data, phone_number=phone_number)
        except DuplicatePhoneException as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    def _validate_phone_uniqueness(self, user: User, phone_number: str) -> None:
        """Check if phone number is already associated with another account."""
        stripped = phone_number.strip()
        if not stripped:
            return
        existing = self.repository.get_user_by_phone(stripped)
        if existing is not None and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this phone number already exists",
            )
