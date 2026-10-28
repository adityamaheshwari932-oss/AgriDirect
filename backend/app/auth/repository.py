"""Repository layer for user and profile persistence.

Executes parameterized SQLAlchemy queries scoped to User identity and profiles.
"""

import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import BuyerProfile, FarmerProfile, User


class DuplicateEntityException(Exception):
    """Raised when a unique constraint violation occurs during user creation."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


class AuthRepository:
    """Encapsulates database access for authentication and registration."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve a User by normalized email address.

        Args:
            email: Lowercased, stripped email string.

        Returns:
            The User instance if found, None otherwise.
        """
        normalized = email.strip().lower()
        return (
            self.db.query(User)
            .filter(func.lower(User.email) == normalized)
            .first()
        )

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Retrieve a User by unique phone number.

        Args:
            phone: Raw phone number string.

        Returns:
            The User instance if found, None otherwise.
        """
        if not phone:
            return None
        return self.db.query(User).filter(User.phone_number == phone.strip()).first()

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a User by primary key ID.

        Args:
            user_id: User UUID.

        Returns:
            The User instance if found, None otherwise.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def create_farmer(self, user: User, profile: FarmerProfile) -> User:
        """Create a farmer user and attached profile in a single atomic transaction.

        Args:
            user: Initialized User model instance with role='farmer'.
            profile: Initialized FarmerProfile instance.

        Returns:
            The committed User model instance with populated relationships.

        Raises:
            DuplicateEntityException: If email or phone number conflicts with existing records.
        """
        try:
            self.db.add(user)
            profile.user = user
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            if "users_email_key" in error_msg or "email" in error_msg.lower():
                raise DuplicateEntityException(
                    "email", "An account with this email address already exists"
                ) from exc
            if "users_phone_number_key" in error_msg or "phone_number" in error_msg.lower():
                raise DuplicateEntityException(
                    "phone_number", "An account with this phone number already exists"
                ) from exc
            raise DuplicateEntityException(
                "unknown", "Registration conflict detected"
            ) from exc

    def create_buyer(self, user: User, profile: BuyerProfile) -> User:
        """Create a buyer user and attached profile in a single atomic transaction.

        Args:
            user: Initialized User model instance with role='buyer'.
            profile: Initialized BuyerProfile instance.

        Returns:
            The committed User model instance with populated relationships.

        Raises:
            DuplicateEntityException: If email or phone number conflicts with existing records.
        """
        try:
            self.db.add(user)
            profile.user = user
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            if "users_email_key" in error_msg or "email" in error_msg.lower():
                raise DuplicateEntityException(
                    "email", "An account with this email address already exists"
                ) from exc
            if "users_phone_number_key" in error_msg or "phone_number" in error_msg.lower():
                raise DuplicateEntityException(
                    "phone_number", "An account with this phone number already exists"
                ) from exc
            raise DuplicateEntityException(
                "unknown", "Registration conflict detected"
            ) from exc
