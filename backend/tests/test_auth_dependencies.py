"""Focused unit and security tests for authentication and authorization dependencies."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.dependencies import (
    create_access_token,
    get_current_active_user,
    get_current_user,
    require_admin,
    require_buyer,
    require_farmer,
    require_verified_buyer,
    require_verified_farmer,
    require_verified_user,
)
from app.models.user import User


def _make_mock_user(
    *,
    user_id: uuid.UUID | None = None,
    role: str = "farmer",
    verification_status: str = "verified",
    account_status: str = "active",
) -> User:
    """Create a mock User instance with specified attributes."""
    user = User(
        id=user_id or uuid.uuid4(),
        email="user@example.com",
        password_hash="fakehash",
        role=role,
        verification_status=verification_status,
        account_status=account_status,
    )
    return user


class TestTokenCreationAndVerification:
    """Tests for create_access_token and get_current_user."""

    def test_create_access_token_default_expiration(self) -> None:
        settings = get_settings()
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id})

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == user_id
        assert "exp" in payload
        assert "iat" in payload
        # Default expiration is approximately 60 minutes
        diff = payload["exp"] - payload["iat"]
        assert 3500 <= diff <= 3700

    def test_create_access_token_custom_delta(self) -> None:
        settings = get_settings()
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id}, expires_delta=timedelta(minutes=15))

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        diff = payload["exp"] - payload["iat"]
        assert 890 <= diff <= 910

    def test_get_current_user_success(self) -> None:
        mock_user = _make_mock_user()
        token = create_access_token({"sub": str(mock_user.id)})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        resolved = get_current_user(credentials=credentials, db=mock_db)
        assert resolved.id == mock_user.id

    def test_get_current_user_missing_credentials_raises_401(self) -> None:
        mock_db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_get_current_user_expired_token_raises_401(self) -> None:
        settings = get_settings()
        user_id = str(uuid.uuid4())
        expired_token = jwt.encode(
            {
                "sub": user_id,
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_signature_raises_401(self) -> None:
        user_id = str(uuid.uuid4())
        bad_token = jwt.encode(
            {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key-that-does-not-match",
            algorithm="HS256",
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad_token)
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_missing_sub_claim_raises_401(self) -> None:
        settings = get_settings()
        token = jwt.encode(
            {"email": "user@example.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_not_found_in_db_raises_401(self) -> None:
        token = create_access_token({"sub": str(uuid.uuid4())})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_malformed_sub_claim_raises_401(self) -> None:
        settings = get_settings()
        token = jwt.encode(
            {"sub": "not-a-valid-uuid", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_disallowed_algorithm_raises_401(self) -> None:
        settings = get_settings()
        # Even if signed with secret, using HS512 when app config expects HS256 must be rejected
        token = jwt.encode(
            {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.secret_key,
            algorithm="HS512" if settings.jwt_algorithm != "HS512" else "HS384",
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestAccountStatusAndAuthorizationGuards:
    """Tests for get_current_active_user, require_verified_*, and require_admin."""

    def test_get_current_active_user_success(self) -> None:
        user = _make_mock_user(account_status="active")
        assert get_current_active_user(user) == user

    @pytest.mark.parametrize("bad_status", ["suspended", "restricted", "blocked"])
    def test_get_current_active_user_rejects_non_active(self, bad_status: str) -> None:
        user = _make_mock_user(account_status=bad_status)
        with pytest.raises(HTTPException) as exc_info:
            get_current_active_user(user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "inactive or suspended" in exc_info.value.detail

    def test_require_verified_user_success(self) -> None:
        user = _make_mock_user(account_status="active", verification_status="verified")
        assert require_verified_user(user) == user

    @pytest.mark.parametrize("status_val", ["unverified", "pending", "rejected"])
    def test_require_verified_user_rejects_unverified(self, status_val: str) -> None:
        user = _make_mock_user(account_status="active", verification_status=status_val)
        with pytest.raises(HTTPException) as exc_info:
            require_verified_user(user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "verified account" in exc_info.value.detail

    def test_require_verified_farmer_success(self) -> None:
        user = _make_mock_user(role="farmer", verification_status="verified", account_status="active")
        assert require_verified_farmer(user) == user

    def test_require_verified_farmer_rejects_non_farmer(self) -> None:
        buyer = _make_mock_user(role="buyer", verification_status="verified", account_status="active")
        with pytest.raises(HTTPException) as exc_info:
            require_verified_farmer(buyer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "farmer account" in exc_info.value.detail

    def test_require_verified_buyer_success(self) -> None:
        user = _make_mock_user(role="buyer", verification_status="verified", account_status="active")
        assert require_verified_buyer(user) == user

    def test_require_verified_buyer_rejects_non_buyer(self) -> None:
        farmer = _make_mock_user(role="farmer", verification_status="verified", account_status="active")
        with pytest.raises(HTTPException) as exc_info:
            require_verified_buyer(farmer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "buyer account" in exc_info.value.detail

    def test_require_admin_success(self) -> None:
        admin = _make_mock_user(role="admin", account_status="active")
        assert require_admin(admin) == admin

    def test_require_admin_rejects_farmer_and_buyer(self) -> None:
        farmer = _make_mock_user(role="farmer", account_status="active")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(farmer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "administrator privileges" in exc_info.value.detail

        buyer = _make_mock_user(role="buyer", account_status="active")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(buyer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "administrator privileges" in exc_info.value.detail

    @pytest.mark.parametrize("verification", ["unverified", "pending", "verified", "rejected"])
    def test_require_farmer_allows_active_farmer_regardless_of_verification(
        self, verification: str
    ) -> None:
        user = _make_mock_user(role="farmer", verification_status=verification, account_status="active")
        assert require_farmer(user) == user

    def test_require_farmer_rejects_non_farmer(self) -> None:
        buyer = _make_mock_user(role="buyer", account_status="active")
        with pytest.raises(HTTPException) as exc_info:
            require_farmer(buyer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "farmer account" in exc_info.value.detail

    @pytest.mark.parametrize("verification", ["unverified", "pending", "verified", "rejected"])
    def test_require_buyer_allows_active_buyer_regardless_of_verification(
        self, verification: str
    ) -> None:
        user = _make_mock_user(role="buyer", verification_status=verification, account_status="active")
        assert require_buyer(user) == user

    def test_require_buyer_rejects_non_buyer(self) -> None:
        farmer = _make_mock_user(role="farmer", account_status="active")
        with pytest.raises(HTTPException) as exc_info:
            require_buyer(farmer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "buyer account" in exc_info.value.detail
