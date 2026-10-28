"""Unit tests for password hashing and verification utilities."""

import pytest
from app.core.security import hash_password, verify_password


class TestPasswordSecurity:
    """Test suite for password hashing and verification."""

    def test_hash_password_returns_argon2_string(self) -> None:
        raw_password = "SuperSecretPassword123!"
        hashed = hash_password(raw_password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2id$")
        assert hashed != raw_password

    def test_verify_password_success(self) -> None:
        raw_password = "FarmerValidPassword2026"
        hashed = hash_password(raw_password)

        assert verify_password(raw_password, hashed) is True

    def test_verify_password_failure_wrong_password(self) -> None:
        raw_password = "CorrectPassword123"
        hashed = hash_password(raw_password)

        assert verify_password("IncorrectPassword456", hashed) is False

    def test_different_salts_for_same_password(self) -> None:
        raw_password = "IdenticalPassword"
        hash1 = hash_password(raw_password)
        hash2 = hash_password(raw_password)

        assert hash1 != hash2
        assert verify_password(raw_password, hash1) is True
        assert verify_password(raw_password, hash2) is True

    def test_hash_password_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Password must not be empty"):
            hash_password("")

    def test_verify_password_handles_empty_inputs_safely(self) -> None:
        hashed = hash_password("ValidPassword123")

        assert verify_password("", hashed) is False
        assert verify_password("ValidPassword123", "") is False
        assert verify_password("", "") is False

    def test_verify_password_handles_malformed_hash_gracefully(self) -> None:
        assert verify_password("password", "not-a-valid-argon2-hash") is False
        assert verify_password("password", "$argon2id$garbage$payload") is False
