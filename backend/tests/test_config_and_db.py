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
* The ``extra="forbid"`` test writes a temporary .env file in a temp
  directory and points ``env_file`` at it, so the developer's real .env
  is never read.
* The session-lifecycle test creates a *temporary in-memory SQLite*
  database via ``create_engine("sqlite:///:memory:")`` so no PostgreSQL
  connection is needed.
* The ``get_settings()`` cache-clearing tests use ``monkeypatch`` to
  inject environment variables and clear the LRU cache between tests.

Run from the project root:
    backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -v
"""

import importlib
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import close_db, get_db, get_engine, get_session_factory, init_db
from app.main import app


@pytest.fixture(autouse=True)
def clean_db_state() -> Generator[None, None, None]:
    """Ensure database global state is reset before and after each test."""
    close_db()
    yield
    close_db()


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
                Settings(_env_file=None, app_env="testing", secret_key=_VALID_SECRET)

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
                Settings(_env_file=None, app_env="testing", database_url=_VALID_DB_URL)

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

    # ------------------------------------------------------------------
    # Placeholder rejection
    # ------------------------------------------------------------------

    def test_rejects_replace_me_placeholder(self) -> None:
        """The literal value REPLACE_ME (from .env.example) is rejected.

        This prevents accidentally running with the publicly known placeholder
        value from the committed template file.
        """
        with pytest.raises(ValidationError):
            _valid_settings(secret_key="REPLACE_ME")

    def test_rejects_replace_me_lowercase(self) -> None:
        """The placeholder check is case-insensitive."""
        with pytest.raises(ValidationError):
            _valid_settings(secret_key="replace_me")

    def test_rejects_replace_me_mixed_case(self) -> None:
        with pytest.raises(ValidationError):
            _valid_settings(secret_key="Replace_Me")

    def test_placeholder_error_mentions_placeholder(self) -> None:
        """The placeholder ValidationError explains what went wrong.

        The message must mention the placeholder so a developer reading the
        error immediately knows to replace it.
        """
        with pytest.raises(ValidationError) as exc_info:
            _valid_settings(secret_key="REPLACE_ME")
        assert "placeholder" in str(exc_info.value).lower(), (
            "Expected the error to mention 'placeholder' so the developer "
            "understands the problem."
        )

    def test_long_genuine_secret_is_accepted(self) -> None:
        """A long, randomly-generated secret that is not a placeholder is accepted."""
        genuine_secret = "a1b2c3d4e5f6" * 6  # 72 hex chars, clearly not REPLACE_ME
        s = _valid_settings(secret_key=genuine_secret)
        assert len(s.secret_key) >= 32


# ===========================================================================
# extra="forbid" — unknown .env key detection
# ===========================================================================


class TestExtraForbidBehaviour:
    """Settings rejects unrecognised keys found in a .env file.

    pydantic-settings with ``extra="forbid"`` raises a ValidationError when
    the .env file contains a key that does not match any declared field.  This
    catches spelling mistakes such as ``DATABSE_URL`` early.

    Importantly, the check applies only to .env file entries.  Variables that
    already exist in the process environment (PATH, TEMP, USERNAME, etc.) are
    NOT subject to this check, so it is safe to use on Windows.
    """

    def _make_env_file(self, tmp_path: Path, content: str) -> Path:
        """Write content to a .env file in tmp_path and return its path.

        Args:
            tmp_path: pytest's temporary directory fixture.
            content: Lines to write (one VAR=VALUE per line).

        Returns:
            Absolute Path to the written file.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(content, encoding="utf-8")
        return env_file

    def test_unknown_dotenv_key_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """A .env file with an unknown key causes a ValidationError.

        This simulates a developer who mistyped a variable name in their
        local .env file, e.g. DATABSE_URL instead of DATABASE_URL.
        """
        env_file = self._make_env_file(
            tmp_path,
            f"DATABASE_URL={_VALID_DB_URL}\n"
            f"SECRET_KEY={'a' * 32}\n"
            "APP_ENV=development\n"
            "TYPO_VARIABLE=should_cause_error\n",  # unknown key
        )
        # Patch model_config to point at our temp file instead of the real .env.
        patched_config = {**Settings.model_config, "env_file": str(env_file)}
        with patch.object(Settings, "model_config", patched_config):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
        errors = exc_info.value.errors()
        error_types = [e["type"] for e in errors]
        assert "extra_forbidden" in error_types, (
            f"Expected 'extra_forbidden' error for unknown .env key. Got: {error_types}"
        )

    def test_valid_dotenv_file_with_no_unknown_keys_succeeds(
        self, tmp_path: Path
    ) -> None:
        """A .env file with only known, valid keys does not raise an error."""
        env_file = self._make_env_file(
            tmp_path,
            f"DATABASE_URL={_VALID_DB_URL}\n"
            f"SECRET_KEY={'b' * 32}\n"
            "APP_ENV=development\n",
        )
        patched_config = {**Settings.model_config, "env_file": str(env_file)}
        # Remove DATABASE_URL and SECRET_KEY from the process environment so
        # pydantic-settings must read them exclusively from the temp .env file.
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("DATABASE_URL", "SECRET_KEY", "APP_ENV")
        }
        with patch.object(Settings, "model_config", patched_config):
            with patch.dict(os.environ, clean_env, clear=True):
                s = Settings()
        assert s.app_env == "development"

    def test_os_env_vars_are_not_rejected_by_extra_forbid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unrelated OS environment variables (PATH, TEMP, etc.) are not rejected.

        This verifies that extra="forbid" does not break the application on
        Windows, where the process environment contains many variables that
        are not declared as Settings fields.
        """
        # Point env_file at a nonexistent path so no .env is loaded.
        # All required values come from explicit env vars patched below.
        monkeypatch.setattr(
            "app.core.config.Settings.model_config",
            {**Settings.model_config, "env_file": ".env.nonexistent"},
        )
        monkeypatch.setenv("DATABASE_URL", _VALID_DB_URL)
        monkeypatch.setenv("SECRET_KEY", "c" * 32)
        monkeypatch.setenv("APP_ENV", "testing")
        get_settings.cache_clear()
        try:
            # If extra="forbid" incorrectly applied to OS env vars, this
            # would raise because PATH, TEMP, USERNAME etc. are present.
            s = get_settings()
            assert isinstance(s, Settings)
        finally:
            get_settings.cache_clear()


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
# Database lifecycle, import safety, and session tests
# ===========================================================================


class TestDatabaseImportSafety:
    """Importing app.db.session must not require settings or a live database."""

    def test_import_session_module_without_database_url_or_secret_key(
        self,
    ) -> None:
        """app.db.session can be imported when required settings are absent.

        This ensures importing database utilities never raises a ValidationError
        due to missing environment variables.
        """
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("DATABASE_URL", "SECRET_KEY", "APP_ENV")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            if "app.db.session" in sys.modules:
                del sys.modules["app.db.session"]
            imported_mod = importlib.import_module("app.db.session")

            assert imported_mod._engine is None
            assert imported_mod._session_factory is None


class TestDatabaseExplicitInitialization:
    """The database engine and session factory can be initialized explicitly."""

    def test_init_db_with_explicit_test_url(self) -> None:
        """init_db creates an engine and sessionmaker bound to the provided URL."""
        init_db("sqlite:///:memory:")
        engine = get_engine()
        assert engine.url.drivername == "sqlite"

        factory = get_session_factory()
        assert isinstance(factory, sessionmaker)

    def test_init_db_with_explicit_engine_instance(self) -> None:
        """init_db can accept a pre-configured Engine instance."""
        custom_engine = create_engine("sqlite:///:memory:")
        try:
            init_db(engine=custom_engine)
            assert get_engine() is custom_engine
        finally:
            custom_engine.dispose()

    def test_init_db_disposes_previous_engine(self) -> None:
        """Re-initializing disposes the previous engine cleanly."""
        init_db("sqlite:///:memory:")
        first_engine = get_engine()
        init_db("sqlite:///:memory:")
        second_engine = get_engine()
        assert first_engine is not second_engine

    def test_failed_reinitialization_resets_state_and_allows_recovery(self) -> None:
        """Failed reinitialization leaves state reset to None and allows subsequent recovery."""
        # 1. Successful initialization
        init_db("sqlite:///:memory:")
        first_engine = get_engine()
        assert first_engine is not None
        assert get_session_factory() is not None

        # 2. Reinitialization with an invalid database URL
        with pytest.raises(Exception):
            init_db("invalid_dialect_nonexistent://bad_url")

        # 3. Resulting state after failed reinitialization:
        # Must not reference the old disposed engine or stale factory.
        with pytest.raises(RuntimeError, match="not been initialized"):
            get_engine()

        with pytest.raises(RuntimeError, match="not been initialized"):
            get_session_factory()

        # 4. Successful initialization after the failed attempt
        init_db("sqlite:///:memory:")
        recovered_engine = get_engine()
        assert recovered_engine is not None
        assert recovered_engine is not first_engine
        assert get_session_factory() is not None


class TestUninitializedDatabaseErrors:
    """Calling accessors or get_db before init_db produces clear, actionable errors."""

    def test_get_db_before_initialization_raises_runtime_error(self) -> None:
        """Calling get_db() before initialization raises RuntimeError."""
        with pytest.raises(RuntimeError) as exc_info:
            gen = get_db()
            next(gen)
        assert "not been initialized" in str(exc_info.value).lower()
        assert "init_db()" in str(exc_info.value)

    def test_get_engine_before_initialization_raises_runtime_error(self) -> None:
        """Calling get_engine() before initialization raises RuntimeError."""
        with pytest.raises(RuntimeError) as exc_info:
            get_engine()
        assert "not been initialized" in str(exc_info.value).lower()
        assert "init_db()" in str(exc_info.value)

    def test_get_session_factory_before_initialization_raises_runtime_error(
        self,
    ) -> None:
        """Calling get_session_factory() before initialization raises RuntimeError."""
        with pytest.raises(RuntimeError) as exc_info:
            get_session_factory()
        assert "not been initialized" in str(exc_info.value).lower()
        assert "init_db()" in str(exc_info.value)


class TestProductionGetDbDependency:
    """Tests for the actual get_db generator dependency."""

    @pytest.fixture(autouse=True)
    def setup_sqlite_database(self) -> Generator[None, None, None]:
        """Initialize database with in-memory SQLite for each test."""
        init_db("sqlite:///:memory:")
        yield
        close_db()

    def test_get_db_yields_working_session(self) -> None:
        """The actual get_db yields a Session that can execute SQL."""
        gen = get_db()
        db = next(gen)
        try:
            assert isinstance(db, Session)
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            with pytest.raises(StopIteration):
                next(gen)

    def test_get_db_closes_session_after_generator_exhausted(self) -> None:
        """The actual get_db closes its session after normal use."""
        gen = get_db()
        db = next(gen)

        # Executing a query starts a transaction.
        db.execute(text("SELECT 1"))
        assert db.in_transaction(), (
            "Session should be in a transaction after query."
        )

        with patch.object(db, "close", wraps=db.close) as spy_close:
            # Exhaust the generator (triggers finally: db.close())
            with pytest.raises(StopIteration):
                next(gen)

            spy_close.assert_called_once()

        # After closing, the transaction is ended.
        assert not db.in_transaction(), (
            "Session must have no active transaction after close."
        )

    def test_get_db_closes_session_on_exception(self) -> None:
        """The actual get_db closes its session even when an exception is raised."""
        gen = get_db()
        db = next(gen)

        db.execute(text("SELECT 1"))
        assert db.in_transaction(), (
            "Session should be in a transaction after query."
        )

        with patch.object(db, "close", wraps=db.close) as spy_close:
            with pytest.raises(RuntimeError, match="simulated route handler failure"):
                gen.throw(RuntimeError("simulated route handler failure"))

            spy_close.assert_called_once()

        assert not db.in_transaction(), (
            "Session must have closed its transaction even when an exception was raised."
        )


class TestApplicationLifespanDatabaseManagement:
    """FastAPI application lifespan initializes and disposes the database engine."""

    def test_lifespan_manages_database_lifecycle(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Application startup initializes engine; shutdown disposes it."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setenv("SECRET_KEY", _VALID_SECRET)
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setattr(
            "app.core.config.Settings.model_config",
            {**Settings.model_config, "env_file": ".env.nonexistent"},
        )
        get_settings.cache_clear()
        close_db()

        try:
            with TestClient(app) as client:
                # During lifespan startup, engine must be initialized
                engine = get_engine()
                assert engine is not None
                assert engine.url.drivername == "sqlite"

                # Health endpoint continues to work
                response = client.get("/health")
                assert response.status_code == 200

            # After exiting lifespan context (shutdown), engine must be disposed/reset
            with pytest.raises(RuntimeError):
                get_engine()
        finally:
            close_db()
            get_settings.cache_clear()

    def test_lifespan_cleans_up_on_startup_failure(self) -> None:
        """When init_db fails during lifespan startup, close_db is called and startup halts."""
        close_db()
        with patch("app.main.init_db", side_effect=RuntimeError("simulated init failure")):
            with patch("app.main.close_db", wraps=close_db) as spy_close:
                with pytest.raises(RuntimeError, match="simulated init failure"):
                    with TestClient(app):
                        pytest.fail("Application should not have continued normal startup.")

                # close_db must have been called in the finally block
                spy_close.assert_called()

        # Database state remains uninitialized
        with pytest.raises(RuntimeError):
            get_engine()


# ===========================================================================
# Declarative base
# ===========================================================================


class TestDeclarativeBase:
    """The shared Base is a valid SQLAlchemy DeclarativeBase with clean decoupling from models."""

    def test_base_has_metadata(self) -> None:
        """Base.metadata exists and is a SQLAlchemy MetaData object."""
        from sqlalchemy import MetaData

        from app.db.base import Base

        assert isinstance(Base.metadata, MetaData)

    def test_base_alone_does_not_implicitly_import_models(self) -> None:
        """Importing app.db.base.Base alone does not implicitly import application models.

        Uses an isolated Python subprocess to guarantee that earlier tests in the
        session that imported app.models do not leak imported module state into this verification.
        """
        import subprocess
        import sys

        verify_script = (
            "import sys\n"
            "from app.db.base import Base\n"
            "assert 'app.models' not in sys.modules, (\n"
            "    f'Importing app.db.base implicitly imported app.models'\n"
            ")\n"
            "assert len(Base.metadata.tables) == 0, (\n"
            "    f'Base.metadata must have 0 tables before models are imported, '\n"
            "    f'found: {list(Base.metadata.tables.keys())}'\n"
            ")\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", verify_script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (
            f"Importing Base alone implicitly imported models or registered tables:\n"
            f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        )

    def test_importing_models_registers_exact_implemented_tables(self) -> None:
        """Importing app.models registers exactly the implemented Phase 2 models."""
        import app.models  # noqa: F401
        from app.db.base import Base

        expected_tables = {
            "users",
            "farmer_profiles",
            "buyer_profiles",
            "verification_submissions",
            "verification_documents",
            "admin_audit_logs",
            "produce_categories",
            "produce_listings",
            "listing_images",
            "buyer_requirements",
            "requirement_fulfillment_approvals",
            "conversations",
            "conversation_participants",
            "messages",
            "message_attachments",
            "contact_share_requests",
            "offers",
            "offer_items",
            "orders",
            "order_items",
            "order_amendments",
            "order_delivery_acknowledgements",
            "inventory_adjustments",
            "payment_records",
            "payment_complaints",
            "ratings_reviews",
            "notifications",
            "user_reports",
            "transporter_profiles",
            "service_areas",
        }
        actual_tables = set(Base.metadata.tables.keys())
        assert actual_tables == expected_tables, (
            f"Base.metadata must register exactly the Phase 2 implemented tables.\n"
            f"Expected: {expected_tables}\n"
            f"Actual:   {actual_tables}\n"
            f"Missing:  {expected_tables - actual_tables}\n"
            f"Extra:    {actual_tables - expected_tables}"
        )


# ===========================================================================
# Settings — JWT and Email Notification settings
# ===========================================================================


class TestSettingsJWT:
    """Settings properly validates JWT configuration."""

    def test_default_jwt_settings(self) -> None:
        s = _valid_settings()
        assert s.jwt_algorithm == "HS256"
        assert s.access_token_expire_minutes == 60

    def test_custom_valid_jwt_settings(self) -> None:
        s = _valid_settings(jwt_algorithm="HS512", access_token_expire_minutes=120)
        assert s.jwt_algorithm == "HS512"
        assert s.access_token_expire_minutes == 120

    def test_unsupported_jwt_algorithm_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="JWT_ALGORITHM must be one of"):
            _valid_settings(jwt_algorithm="UNSUPPORTED_ALG")

    def test_non_positive_expire_minutes_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0"):
            _valid_settings(access_token_expire_minutes=0)

        with pytest.raises(ValidationError, match="ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0"):
            _valid_settings(access_token_expire_minutes=-10)


class TestSettingsEmailNotification:
    """Settings properly validates email notification configuration."""

    def test_default_email_settings(self) -> None:
        s = _valid_settings()
        assert s.enable_email_notifications is False
        assert s.smtp_host is None
        assert s.smtp_port == 587
        assert s.smtp_user is None
        assert s.smtp_password is None
        assert s.smtp_from_email is None

    def test_custom_valid_email_settings(self) -> None:
        s = _valid_settings(
            enable_email_notifications=True,
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_user="user@example.com",
            smtp_password="app_password",
            smtp_from_email="noreply@example.com",
        )
        assert s.enable_email_notifications is True
        assert s.smtp_host == "smtp.example.com"
        assert s.smtp_port == 465
        assert s.smtp_user == "user@example.com"
        assert s.smtp_password == "app_password"
        assert s.smtp_from_email == "noreply@example.com"

    def test_invalid_smtp_port_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="SMTP_PORT must be between 1 and 65535"):
            _valid_settings(smtp_port=0)

        with pytest.raises(ValidationError, match="SMTP_PORT must be between 1 and 65535"):
            _valid_settings(smtp_port=70000)
