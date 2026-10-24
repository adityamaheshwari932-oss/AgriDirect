"""Central application configuration.

All settings are read from environment variables.  When a ``backend/.env``
file is present, pydantic-settings loads it automatically before falling back
to the real environment.

Usage (anywhere in the application)
-------------------------------------
    from app.core.config import get_settings

    settings = get_settings()
    print(settings.database_url)   # safe; not a secret
    # Never print settings.secret_key in real code.

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
        # Raise an error for unknown fields in the .env file so typos are
        # caught early rather than silently ignored.
        extra="ignore",
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

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_empty(cls, value: str) -> str:
        """Reject a blank or placeholder secret key.

        A secret key shorter than 32 characters is almost certainly a
        placeholder or an accident.  Refuse to start rather than run with
        a weak secret.

        Args:
            value: The raw SECRET_KEY string from the environment.

        Returns:
            The validated secret key (unchanged).

        Raises:
            ValueError: If the key is blank or fewer than 32 characters.
        """
        if not value or len(value.strip()) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long.  "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
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
