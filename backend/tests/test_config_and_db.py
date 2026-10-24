"""Tests for application configuration and database infrastructure.

These tests must run without:
  - A live PostgreSQL connection.
  - The developer's real .env file.
  - Any real credentials in assertion output.

Strategy
--------
* Settings are tested by constructing ``Settings(...)`` with explicit
  keyword arguments, completely bypassing .env file loading and the
  ``get_settings()`` cache.
* The session-lifecycle test creates a *temporary in-memory SQLite*
  database via ``create_engine("sqlite:///:memory:")`` so no PostgreSQL
  connection is needed.
* The ``get_settings()`` cache-clearing tests use ``monkeypatch`` to
  inject environment variables and clear the LRU cache between tests.

Run from the project root:
    backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -v
"""

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


# ===========================================================================
# Helpers
# ===========================================================================

# A minimal set of valid settings values used throughout these tests.
# Using a realistic-looking URL keeps the tests clear; no real connection
# is opened by constructing a Settings object.
_VALID_DB_URL = "postgresql+psycopg://agridirect_app:testpass@localhost:5432/agridirect_db"
_VALID_SECRET = "a" * 32  # exactly 32 chars — minimum acceptable length


def _valid_settings(**overrides: object) -> Settings:
    """Build a Settings object with sensible test values.

    Keyword overrides replace the defaults so individual tests can vary
    exactly one field while keeping everything else valid.

    Args:
        **overrides: Field values to override.

    Returns:
        A validated Settings instance.  Construction raises ValidationError
        if the combination of defaults and overrides is invalid.
    """
    defaults: dict[str, object] = {
        "app_env": "testing",
        "database_url": _VALID_DB_URL,
        "secret_key": _VALID_SECRET,
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ===========================================================================
# Settings — valid construction
# ===========================================================================


class TestSettingsValidConstruction:
    """Settings can be constructed with explicit, valid values."""

    def test_accepts_development_env(self) -> None:
        s = _valid_settings(app_env="development")
        assert s.app_env == "development"

    def test_accepts_testing_env(self) -> None:
        s = _valid_settings(app_env="testing")
        assert s.app_env == "testing"

    def test_accepts_production_env(self) -> None:
        s = _valid_settings(app_env="production")
        assert s.app_env == "production"

    def test_app_env_is_lowercased(self) -> None:
        """app_env is normalised to lowercase by the validator."""
        s = _valid_settings(app_env="Development")
        assert s.app_env == "development"

    def test_database_url_is_stored(self) -> None:
        s = _valid_settings(database_url=_VALID_DB_URL)
        assert s.database_url == _VALID_DB_URL

    def test_secret_key_is_stored(self) -> None:
        s = _valid_settings(secret_key=_VALID_SECRET)
        assert s.secret_key == _VALID_SECRET

    def test_minimum_length_secret_key_is_accepted(self) -> None:
        """A secret key of exactly 32 characters is the minimum valid length."""
        s = _valid_settings(secret_key="x" * 32)
        assert len(s.secret_key) == 32

    def test_long_secret_key_is_accepted(self) -> None:
        s = _valid_settings(secret_key="z" * 64)
        assert len(s.secret_key) == 64


# ===========================================================================
# Settings — validation rejects bad input
# ===========================================================================


class TestSettingsValidation:
    """Settings rejects invalid or missing values."""

    def test_rejects_unknown_app_env(self) -> None:
        """An unrecognised APP_ENV value raises a ValidationError."""
        with pytest.raises(ValidationError):
            _valid_settings(app_env="staging")

    def test_rejects_blank_app_env(self) -> None:
        with pytest.raises(ValidationError):
            _valid_settings(app_env="")

    def test_rejects_empty_database_url(self) -> None:
        """A blank DATABASE_URL raises a ValidationError."""
        with pytest.raises(ValidationError):
            _valid_settings(database_url="")

    def test_rejects_whitespace_database_url(self) -> None:
        with pytest.raises(ValidationError):
            _valid_settings(database_url="   ")

    def test_rejects_missing_database_url(self) -> None:
        """Omitting DATABASE_URL (no env var, no kwarg) raises a ValidationError."""
        # We intentionally do NOT pass database_url so pydantic sees a missing
        # required field.  We also clear DATABASE_URL from the environment so
        # pydantic-settings cannot fall back to it.
        clean_env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, clean_env, clear=True):
            with pytest.raises(ValidationError):
                Settings(app_env="testing", secret_key=_VALID_SECRET)

    def test_rejects_short_secret_key(self) -> None:
        """A secret key shorter than 32 characters is rejected."""
        with pytest.raises(ValidationError):
            _valid_settings(secret_key="tooshort")

    def test_rejects_empty_secret_key(self) -> None:
        with pytest.raises(ValidationError):
            _valid_settings(secret_key="")

    def test_rejects_missing_secret_key(self) -> None:
        """Omitting SECRET_KEY raises a ValidationError."""
        clean_env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
        with patch.dict(os.environ, clean_env, clear=True):
            with pytest.raises(ValidationError):
                Settings(app_env="testing", database_url=_VALID_DB_URL)

    def test_short_secret_key_error_mentions_length(self) -> None:
        """The ValidationError for a short key describes the length requirement.

        Note on pydantic v2 behaviour: pydantic includes the input_value in
        its error output.  We cannot prevent that at the application level;
        it is a framework behaviour.  What we *can* test is that our own
        validator message (about minimum length) is present in the error so
        the developer understands what to fix.
        """
        with pytest.raises(ValidationError) as exc_info:
            _valid_settings(secret_key="tooshort")
        # Our validator message must be present so the developer knows the fix.
        assert "32" in str(exc_info.value), (
            "Expected the ValidationError to mention the minimum key length (32)."
        )


# ===========================================================================
# get_settings() — cache behaviour
# ===========================================================================


class TestGetSettingsCacheBehaviour:
    """get_settings() is cached but the cache can be cleared between tests."""

    def test_get_settings_returns_settings_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_settings() returns a Settings object when env vars are valid."""
        monkeypatch.setenv("DATABASE_URL", _VALID_DB_URL)
        monkeypatch.setenv("SECRET_KEY", _VALID_SECRET)
        monkeypatch.setenv("APP_ENV", "testing")
        # Point env_file at a nonexistent path so the real .env is not loaded.
        monkeypatch.setattr(
            "app.core.config.Settings.model_config",
            {**Settings.model_config, "env_file": ".env.nonexistent"},
        )
        get_settings.cache_clear()
        try:
            result = get_settings()
            assert isinstance(result, Settings)
        finally:
            get_settings.cache_clear()

    def test_cache_is_cleared_between_calls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After cache_clear(), get_settings() reflects updated env vars."""
        monkeypatch.setenv("DATABASE_URL", _VALID_DB_URL)
        monkeypatch.setenv("SECRET_KEY", _VALID_SECRET)
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setattr(
            "app.core.config.Settings.model_config",
            {**Settings.model_config, "env_file": ".env.nonexistent"},
        )
        get_settings.cache_clear()
        try:
            first = get_settings()
            assert first.app_env == "development"

            monkeypatch.setenv("APP_ENV", "testing")
            get_settings.cache_clear()
            second = get_settings()
            assert second.app_env == "testing"
        finally:
            get_settings.cache_clear()


# ===========================================================================
# Session factory — lifecycle tests using in-memory SQLite
# ===========================================================================
# These tests verify the session-management *pattern* (open, yield, close)
# without connecting to PostgreSQL.  We wire create_engine and sessionmaker
# identically to how session.py does it, but against SQLite in memory.
#
# SQLAlchemy 2.x note on Session.is_active:
#   is_active is True when the session has NOT been rolled back — it does NOT
#   mean the session is "open".  A closed session can still have is_active=True.
#   The correct way to detect that a session has been closed (after a query
#   started a transaction) is db.in_transaction(), which returns False once
#   the session is closed and the transaction is gone.


class TestSessionLifecycle:
    """Session opens, can execute, and closes correctly."""

    @pytest.fixture()
    def sqlite_session_factory(self) -> sessionmaker[Session]:
        """Create a sessionmaker backed by an in-memory SQLite database.

        SQLite is used here purely to test the open/close lifecycle without
        requiring PostgreSQL.  The session configuration mirrors session.py.

        Returns:
            A sessionmaker that produces Session objects.
        """
        engine = create_engine("sqlite:///:memory:", echo=False)
        factory: sessionmaker[Session] = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
        )
        return factory

    def test_session_can_be_created_and_execute_sql(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """A session can be created and used to execute SQL."""
        db = sqlite_session_factory()
        try:
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            db.close()

    def test_session_is_closed_after_generator_exits(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """The get_db generator closes the session when exhausted.

        We check in_transaction() rather than is_active because in
        SQLAlchemy 2.x is_active reflects rollback state, not open/closed
        state.  Executing a query starts a transaction; closing the session
        ends it, so in_transaction() moves from True to False.
        """

        def test_get_db() -> Generator[Session, None, None]:
            db = sqlite_session_factory()
            try:
                yield db
            finally:
                db.close()

        gen = test_get_db()
        db = next(gen)

        # Execute a query to start a transaction.
        db.execute(text("SELECT 1"))
        assert db.in_transaction(), (
            "Session should be in a transaction after executing a query."
        )

        # Exhaust the generator (triggers the finally block → db.close()).
        with pytest.raises(StopIteration):
            next(gen)

        # After close(), the transaction is gone.
        assert not db.in_transaction(), (
            "Session should have no active transaction after the generator exits."
        )

    def test_session_is_closed_even_when_exception_occurs(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """The session closes correctly even when the caller raises an exception."""

        def test_get_db_with_error() -> Generator[Session, None, None]:
            db = sqlite_session_factory()
            try:
                yield db
            finally:
                db.close()

        gen = test_get_db_with_error()
        db = next(gen)

        # Execute a query to start a transaction.
        db.execute(text("SELECT 1"))
        assert db.in_transaction(), (
            "Session should be in a transaction after executing a query."
        )

        # Simulate a route handler raising an exception.
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("simulated route error"))

        assert not db.in_transaction(), (
            "Session should have no active transaction even when an exception "
            "propagated through the generator."
        )


# ===========================================================================
# Declarative base
# ===========================================================================


class TestDeclarativeBase:
    """The shared Base is a valid SQLAlchemy DeclarativeBase."""

    def test_base_has_metadata(self) -> None:
        """Base.metadata exists and is a SQLAlchemy MetaData object."""
        from sqlalchemy import MetaData

        from app.db.base import Base

        assert isinstance(Base.metadata, MetaData)

    def test_base_has_tables_attribute(self) -> None:
        """Base.metadata.tables is a dict (possibly empty before models are added)."""
        from app.db.base import Base

        # No ORM models have been defined yet in this phase, so metadata.tables
        # should be empty.  We assert it is a dict, which is always true.
        assert isinstance(Base.metadata.tables, dict)

    def test_base_has_no_tables_before_models_defined(self) -> None:
        """Before any model is defined, Base.metadata has no tables."""
        from app.db.base import Base

        assert len(Base.metadata.tables) == 0, (
            "Expected no tables in metadata at this phase of the project. "
            f"Found: {list(Base.metadata.tables.keys())}"
        )
