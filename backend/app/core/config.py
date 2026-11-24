"""Central application configuration.

All settings are read from environment variables.  When a ``backend/.env``
file is present, pydantic-settings loads it automatically before falling back
to the real environment.

Usage (anywhere in the application)
-------------------------------------
    from app.core.config import get_settings

    settings = get_settings()
    # Never print settings.database_url — it contains the database password.
    # Never print settings.secret_key — it is the JWT signing key.

How environment variables map to fields
-----------------------------------------
pydantic-settings uppercases the field name and looks for a matching
environment variable.  Every field here therefore maps 1-to-1 to a
variable name in ALL_CAPS:

    app_env            -> APP_ENV
    database_url       -> DATABASE_URL
    secret_key         -> SECRET_KEY

For an example of all required variables, see ``backend/.env.example``.
"""

from functools import lru_cache
from typing import ClassVar

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Fields
    ------
    app_env:
        The runtime environment name.  Recognised values are
        ``"development"``, ``"testing"``, and ``"production"``.
        Defaults to ``"development"`` so the application starts without
        configuration when working locally.  Must be changed to
        ``"production"`` before deploying.

    database_url:
        A full SQLAlchemy-compatible connection string for the PostgreSQL
        database.  The synchronous Psycopg driver requires the scheme
        ``postgresql+psycopg``.

        Example::

            postgresql+psycopg://agridirect_app:PASSWORD@localhost:5432/agridirect_db

        This field has **no default** and must be supplied via the
        environment or a ``.env`` file.  The application will refuse to
        start if it is missing.

    secret_key:
        A long random string used to sign JWT tokens (implemented in
        Phase 2).  This field has **no default** — a missing or empty
        value will be rejected at startup.  Generate a suitable value
        with::

            python -c "import secrets; print(secrets.token_hex(32))"

        Never log or print this value.
    """

    model_config = SettingsConfigDict(
        # Look for a .env file relative to the working directory.
        # If the file does not exist, pydantic-settings silently continues
        # and reads from the real environment instead.
        env_file=".env",
        env_file_encoding="utf-8",
        # Reject unrecognised keys found in the .env file so that spelling
        # mistakes (e.g. DATABSE_URL) are detected early rather than silently
        # dropped.  This applies only to .env file entries; unrelated variables
        # that already exist in the process environment (PATH, TEMP, etc.) are
        # NOT subject to this check, so it is safe to use on Windows.
        extra="forbid",
        # Field names are case-insensitive when matched against env vars.
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Non-secret settings — safe development defaults are provided.
    # ------------------------------------------------------------------

    app_env: str = "development"
    """Runtime environment: "development", "testing", or "production"."""

    # ------------------------------------------------------------------
    # Secret / required settings — NO defaults.
    # Missing values raise a ValidationError at startup.
    # ------------------------------------------------------------------

    database_url: str
    """Full SQLAlchemy connection URL including credentials.
    
    Scheme must be ``postgresql+psycopg`` for the synchronous Psycopg
    driver used in this project.
    """

    secret_key: str
    """Random secret used to sign JWTs.  Never log or expose this value."""

    # ------------------------------------------------------------------
    # JWT / Authentication settings
    # ------------------------------------------------------------------

    jwt_algorithm: str = "HS256"
    """Algorithm used for signing and verifying JWT tokens."""

    access_token_expire_minutes: int = 60
    """Access token lifetime in minutes (default 60)."""

    # ------------------------------------------------------------------
    # Rate Limiting settings (Authentication)
    # ------------------------------------------------------------------

    enable_auth_rate_limit: bool = True
    """Toggle rate limiting on sensitive authentication endpoints."""

    auth_rate_limit_max_attempts: int = 5
    """Maximum allowed login attempts per client IP within the rate limit window."""

    auth_rate_limit_window_seconds: int = 60
    """Duration in seconds for the sliding rate limit window (default: 60s)."""

    # ------------------------------------------------------------------
    # Document Storage Settings (Verification)
    # ------------------------------------------------------------------

    upload_dir: str = "uploads/verification"
    """Base filesystem directory for private verification document storage."""

    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    """Maximum permitted file upload size in bytes (default 10 MB)."""

    # ------------------------------------------------------------------
    # Listing Media Storage Settings (Produce Catalog)
    # ------------------------------------------------------------------

    listing_images_dir: str = "uploads/listings"
    """Base filesystem directory for produce listing photographic assets."""

    product_images_dir: str = "uploads/products"
    """Configurable dedicated directory for product photographs."""

    max_product_images_per_listing: int = 10
    """Maximum permitted photographs per produce listing (default 10)."""

    max_product_image_size_bytes: int = 5 * 1024 * 1024
    """Maximum permitted file upload size for product photographs in bytes (default 5 MB)."""

    def get_product_images_dir(self) -> str:
        """Resolve and ensure the local product images directory exists."""
        import os
        target = self.product_images_dir or self.listing_images_dir
        os.makedirs(target, exist_ok=True)
        return target

    # ------------------------------------------------------------------
    # Offers and Negotiation Settings
    # ------------------------------------------------------------------

    default_offer_expiry_hours: int = 72
    """Default offer validity window in hours when expires_at is not explicitly provided."""

    # ------------------------------------------------------------------
    # Operational Email Notifications (optional feature flag)
    # ------------------------------------------------------------------

    enable_email_notifications: bool = False
    """Feature flag to toggle operational email alerts."""

    smtp_host: str | None = None
    """SMTP server hostname."""

    smtp_port: int = 587
    """SMTP port number (default 587)."""

    smtp_user: str | None = None
    """SMTP username for authentication."""

    smtp_password: str | None = None
    """SMTP password or app-specific token. Never log this value."""

    smtp_from_email: str | None = None
    """Sender email address for operational alerts."""

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("app_env")
    @classmethod
    def app_env_must_be_known(cls, value: str) -> str:
        """Reject unrecognised environment names.

        Args:
            value: The raw APP_ENV string from the environment.

        Returns:
            The validated, lowercased environment name.

        Raises:
            ValueError: If the value is not one of the recognised names.
        """
        known = {"development", "testing", "production"}
        normalised = value.strip().lower()
        if normalised not in known:
            raise ValueError(
                f"APP_ENV must be one of {sorted(known)!r}, got {value!r}."
            )
        return normalised

    # The placeholder written in .env.example.  We reject it explicitly so
    # that copying the template without editing fails at startup rather than
    # silently running with a publicly known value.
    _SECRET_KEY_PLACEHOLDER: ClassVar[str] = "REPLACE_ME"

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_valid(cls, value: str) -> str:
        """Reject a blank, too-short, or known-placeholder secret key.

        Rules (applied in order):
        1. The value must not be blank.
        2. The value must be at least 32 characters long.
        3. The value must not equal the well-known placeholder from
           ``.env.example`` (``REPLACE_ME``).

        Rule 3 catches the case where a developer copies ``.env.example``
        to ``.env`` and forgets to replace the placeholder.  A placeholder
        long enough to satisfy rule 2 would otherwise pass silently and the
        application would sign JWTs with a publicly known secret.

        Args:
            value: The raw SECRET_KEY string from the environment.

        Returns:
            The validated secret key (unchanged).

        Raises:
            ValueError: If the key is blank, too short, or a known placeholder.
        """
        stripped = value.strip() if value else ""

        if not stripped:
            raise ValueError(
                "SECRET_KEY must not be empty.  "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        # Placeholder check comes before length so the error message is
        # actionable: "you left the example value" is clearer than "too short".
        if stripped.upper() == cls._SECRET_KEY_PLACEHOLDER:
            raise ValueError(
                "SECRET_KEY is set to the example placeholder value.  "
                "Replace it with a real secret before starting the application.  "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        if len(stripped) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long.  "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def jwt_algorithm_must_be_supported(cls, value: str) -> str:
        """Reject unsupported JWT signing algorithms."""
        supported = {"HS256", "HS384", "HS512"}
        normalised = value.strip().upper()
        if normalised not in supported:
            raise ValueError(
                f"JWT_ALGORITHM must be one of {sorted(supported)!r}, got {value!r}."
            )
        return normalised

    @field_validator("access_token_expire_minutes")
    @classmethod
    def access_token_expire_minutes_must_be_positive(cls, value: int) -> int:
        """Reject non-positive token expiration duration."""
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0.")
        return value

    @field_validator("auth_rate_limit_max_attempts")
    @classmethod
    def auth_rate_limit_max_attempts_must_be_positive(cls, value: int) -> int:
        """Reject non-positive max attempts."""
        if value <= 0:
            raise ValueError("AUTH_RATE_LIMIT_MAX_ATTEMPTS must be greater than 0.")
        return value

    @field_validator("auth_rate_limit_window_seconds")
    @classmethod
    def auth_rate_limit_window_seconds_must_be_positive(cls, value: int) -> int:
        """Reject non-positive window duration."""
        if value <= 0:
            raise ValueError("AUTH_RATE_LIMIT_WINDOW_SECONDS must be greater than 0.")
        return value

    @field_validator("max_upload_size_bytes")
    @classmethod
    def max_upload_size_bytes_must_be_positive(cls, value: int) -> int:
        """Reject non-positive max upload size."""
        if value <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_BYTES must be greater than 0.")
        return value

    @field_validator("max_product_images_per_listing")
    @classmethod
    def max_product_images_per_listing_must_be_positive(cls, value: int) -> int:
        """Reject non-positive maximum product images limit."""
        if value <= 0:
            raise ValueError("MAX_PRODUCT_IMAGES_PER_LISTING must be greater than 0.")
        return value

    @field_validator("max_product_image_size_bytes")
    @classmethod
    def max_product_image_size_bytes_must_be_positive(cls, value: int) -> int:
        """Reject non-positive maximum product image file size."""
        if value <= 0:
            raise ValueError("MAX_PRODUCT_IMAGE_SIZE_BYTES must be greater than 0.")
        return value

    @field_validator("smtp_port")
    @classmethod
    def smtp_port_must_be_valid(cls, value: int) -> int:
        """Reject invalid TCP port numbers."""
        if value < 1 or value > 65535:
            raise ValueError("SMTP_PORT must be between 1 and 65535.")
        return value

    @field_validator("database_url")
    @classmethod
    def database_url_must_not_be_empty(cls, value: str) -> str:
        """Reject a blank or placeholder database URL.

        Args:
            value: The raw DATABASE_URL string from the environment.

        Returns:
            The validated URL (unchanged).

        Raises:
            ValueError: If the URL is blank.
        """
        if not value or not value.strip():
            raise ValueError("DATABASE_URL must not be empty.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings singleton.

    The result is cached after the first call so the ``.env`` file is
    read only once per process.  The cache is intentionally global: in
    production all requests share the same settings object.

    In tests, call ``get_settings.cache_clear()`` after patching
    environment variables to force a fresh read.

    Returns:
        The validated ``Settings`` instance.
    """
    return Settings()
