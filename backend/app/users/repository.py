"""Repository layer for user and profile persistence.

Executes parameterized SQLAlchemy queries scoped to authenticated User identity and profiles.
"""

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import BuyerProfile, FarmerProfile, User


class DuplicatePhoneException(Exception):
    """Raised when a unique constraint violation occurs during phone number update."""

    def __init__(self, message: str = "An account with this phone number already exists") -> None:
        super().__init__(message)


class UserRepository:
    """Encapsulates database access for user account and profile operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a User by primary key UUID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Retrieve a User by phone number."""
        if not phone:
            return None
        return self.db.query(User).filter(User.phone_number == phone.strip()).first()

    def update_farmer_profile(
        self,
        user: User,
        profile_data: Dict[str, Any],
        phone_number: Optional[str] = None,
    ) -> User:
        """Update a farmer's profile fields and optional phone number.

        Args:
            user: The authenticated farmer User instance.
            profile_data: Dictionary of profile fields to update.
            phone_number: Optional updated phone number string.

        Returns:
            Refreshed User instance with updated profile.

        Raises:
            DuplicatePhoneException: If phone_number conflicts with another account.
        """
        try:
            if phone_number is not None:
                user.phone_number = phone_number.strip() if phone_number else None

            profile = user.farmer_profile
            if profile is None:
                # Initialize profile if absent
                profile = FarmerProfile(
                    user=user,
                    full_name=profile_data.get("full_name") or "Farmer",
                    farm_name=profile_data.get("farm_name") or "Farm",
                    farm_location_address=profile_data.get("farm_location_address") or "Not Specified",
                    city=profile_data.get("city") or "Not Specified",
                    state=profile_data.get("state") or "Not Specified",
                    postal_code=profile_data.get("postal_code") or "000000",
                )
                self.db.add(profile)

            # Apply partial updates
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            if "phone_number" in error_msg.lower() or "users_phone_number_key" in error_msg.lower():
                raise DuplicatePhoneException() from exc
            raise

    def update_buyer_profile(
        self,
        user: User,
        profile_data: Dict[str, Any],
        phone_number: Optional[str] = None,
    ) -> User:
        """Update a buyer's profile fields and optional phone number.

        Args:
            user: The authenticated buyer User instance.
            profile_data: Dictionary of profile fields to update.
            phone_number: Optional updated phone number string.

        Returns:
            Refreshed User instance with updated profile.

        Raises:
            DuplicatePhoneException: If phone_number conflicts with another account.
        """
        try:
            if phone_number is not None:
                user.phone_number = phone_number.strip() if phone_number else None

            profile = user.buyer_profile
            if profile is None:
                # Initialize profile if absent
                profile = BuyerProfile(
                    user=user,
                    contact_person_name=profile_data.get("contact_person_name") or "Buyer",
                    business_name=profile_data.get("business_name") or "Business",
                    business_type=profile_data.get("business_type") or "other",
                    delivery_receiving_address=profile_data.get("delivery_receiving_address") or "Not Specified",
                    city=profile_data.get("city") or "Not Specified",
                    state=profile_data.get("state") or "Not Specified",
                    postal_code=profile_data.get("postal_code") or "000000",
                )
                self.db.add(profile)

            # Apply partial updates
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            if "phone_number" in error_msg.lower() or "users_phone_number_key" in error_msg.lower():
                raise DuplicatePhoneException() from exc
            raise
