"""Shared FastAPI dependencies for authentication and database sessions.

Provides JWT token verification, user retrieval, active-user validation,
and role/verification status authorization guards.
Adheres to the security requirements defined in AGENTS.md.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

# Standard bearer token extractor
http_bearer = HTTPBearer(auto_error=False)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload claims to encode into the token.
        expires_delta: Optional custom expiration timedelta.

    Returns:
        Encoded and signed JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer JWT token and return the authenticated User.

    Args:
        credentials: The Bearer authorization credentials header.
        db: Database session.

    Returns:
        The authenticated User model instance.

    Raises:
        HTTPException: 401 Unauthorized if missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id_str: Optional[str] = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify that the authenticated user's account is active.

    Args:
        current_user: The authenticated User model.

    Returns:
        The active User model instance.

    Raises:
        HTTPException: 403 Forbidden if account is suspended or restricted.
    """
    if current_user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended",
        )
    return current_user


def require_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify that the authenticated user's account is verified.

    Args:
        current_user: Active User instance from get_current_active_user.

    Returns:
        The verified User model instance.

    Raises:
        HTTPException: 403 Forbidden if user is unverified, pending, or rejected.
    """
    if current_user.verification_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a verified account",
        )
    return current_user


def require_verified_farmer(
    current_user: User = Depends(require_verified_user),
) -> User:
    """Verify that the authenticated user is an active, verified farmer.

    Args:
        current_user: Verified User instance from require_verified_user.

    Returns:
        The verified farmer User model instance.

    Raises:
        HTTPException: 403 Forbidden if user role is not farmer.
    """
    if current_user.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a verified farmer account",
        )
    return current_user


def require_farmer(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify that the authenticated user is an active farmer (verified or unverified).

    Args:
        current_user: Active User instance from get_current_active_user.

    Returns:
        The farmer User model instance.

    Raises:
        HTTPException: 403 Forbidden if user role is not farmer.
    """
    if current_user.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a farmer account",
        )
    return current_user


def require_verified_buyer(
    current_user: User = Depends(require_verified_user),
) -> User:
    """Verify that the authenticated user is an active, verified buyer.

    Args:
        current_user: Verified User instance from require_verified_user.

    Returns:
        The verified buyer User model instance.

    Raises:
        HTTPException: 403 Forbidden if user role is not buyer.
    """
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a verified buyer account",
        )
    return current_user


def require_buyer(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify that the authenticated user is an active buyer (verified or unverified).

    Args:
        current_user: Active User instance from get_current_active_user.

    Returns:
        The buyer User model instance.

    Raises:
        HTTPException: 403 Forbidden if user role is not buyer.
    """
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a buyer account",
        )
    return current_user


def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify that the authenticated user has administrator privileges.

    Args:
        current_user: Active User instance from get_current_active_user.

    Returns:
        The admin User model instance.

    Raises:
        HTTPException: 403 Forbidden if user role is not admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires administrator privileges",
        )
    return current_user
