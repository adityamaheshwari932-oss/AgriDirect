"""Security utilities for password hashing and verification.

Implements secure password management using Argon2id via pwdlib.
Adheres to the security requirements defined in AGENTS.md.
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Initialize password hash context with Argon2id hasher
_password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: The plaintext password string to hash.

    Returns:
        The Argon2id password hash string.

    Raises:
        ValueError: If password is empty or blank.
    """
    if not password:
        raise ValueError("Password must not be empty")
    return _password_hash.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an existing password hash.

    Args:
        plain_password: The plaintext password candidate.
        password_hash: The stored password hash string.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not plain_password or not password_hash:
        return False
    try:
        return _password_hash.verify(plain_password, password_hash)
    except Exception:
        return False
