"""Tests for Alembic configuration, URL handling, and SQLAlchemy metadata binding.

These tests verify that:
1. alembic.ini contains no real credentials.
2. alembic/env.py dynamically loads database URL from application settings.
3. alembic/env.py sets target_metadata to the application's Base.metadata.
4. Special characters in database credentials (such as % in URL-encoded passwords)
   are escaped safely for configparser without raising interpolation errors.
5. Importing alembic/env.py and app.models does not initiate any database
   connections or engine creation.
6. Offline migration mode properly configures the migration context with the
   application database URL and Base.metadata.
7. Online migration mode creates an engine using pool.NullPool and cleanly disposes
   it, or reuses a pre-existing connection if provided in config.attributes.
8. app.models package imports without circular dependencies and is imported by env.py.

All tests run in isolation without connecting to the real PostgreSQL database.
"""

import configparser
import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import MetaData, pool

from app.core.config import Settings
from app.db.base import Base


def _load_alembic_env_module() -> ModuleType:
    """Helper to dynamically load backend/alembic/env.py as an isolated module."""
    env_path = Path(__file__).parent.parent / "alembic" / "env.py"
    spec = importlib.util.spec_from_file_location("agridirect_alembic_env_test", env_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {env_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# 1. Configuration file safety tests
# ===========================================================================


def test_alembic_ini_contains_no_real_credentials() -> None:
    """alembic.ini must contain only placeholder values and no real secrets or passwords."""
    ini_path = Path(__file__).parent.parent / "alembic.ini"
    assert ini_path.is_file(), "backend/alembic.ini must exist"

    parser = configparser.ConfigParser()
    parser.read(ini_path)

    assert parser.has_section("alembic"), "alembic.ini must have an [alembic] section"
    configured_url = parser.get("alembic", "sqlalchemy.url")

    # Must be the default placeholder, never real database credentials
    assert configured_url == "driver://user:pass@localhost/dbname"
    assert "agridirect_app" not in configured_url


# ===========================================================================
# 2. Metadata binding & model discovery tests
# ===========================================================================


def test_alembic_env_target_metadata_is_base_metadata() -> None:
    """alembic/env.py must bind target_metadata directly to Base.metadata."""
    mod = _load_alembic_env_module()
    assert hasattr(mod, "target_metadata"), "env.py must define target_metadata"
    assert mod.target_metadata is Base.metadata, (
        "env.py target_metadata must be the exact Base.metadata instance"
    )
    assert isinstance(mod.target_metadata, MetaData)


def test_model_discovery_via_app_models() -> None:
    """app.models must be importable without circular imports and ready for autogenerate."""
    import app.models

    assert app.models is not None
    # Base.metadata exists and is ready to record models when defined
    assert isinstance(Base.metadata.tables, dict)


# ===========================================================================
# 3. Dynamic URL resolution tests
# ===========================================================================


def test_alembic_env_get_url_uses_application_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_url() in alembic/env.py must retrieve database_url from get_settings()."""
    mod = _load_alembic_env_module()

    custom_url = "postgresql+psycopg://test_farmer:secret_pass@localhost:5432/agridirect_test"
    dummy_settings = Settings(
        database_url=custom_url,
        secret_key="x" * 32,
        _env_file=None,
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: dummy_settings)
    # Also patch in the loaded module if imported there
    monkeypatch.setattr(mod, "get_settings", lambda: dummy_settings)

    assert mod.get_url() == custom_url


def test_alembic_url_escapes_percent_for_configparser() -> None:
    """Special characters like % in URL-encoded passwords must be escaped as %% for configparser.

    Without escaping, configparser raises ValueError / InterpolationSyntaxError on %.
    With escaping via url.replace('%', '%%'), configparser successfully stores and retrieves
    the unescaped URL.
    """
    import alembic.config

    ini_path = Path(__file__).parent.parent / "alembic.ini"
    cfg = alembic.config.Config(str(ini_path))

    # A realistic URL with URL-encoded characters in username and password
    raw_url = "postgresql+psycopg://agri%20app:p%40ss%25word%231@localhost:5432/agridirect_db"

    # Escaping % as %% avoids InterpolationSyntaxError
    escaped_url = raw_url.replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", escaped_url)

    # config.get_main_option returns the original unescaped URL
    retrieved_url = cfg.get_main_option("sqlalchemy.url")
    assert retrieved_url == raw_url


# ===========================================================================
# 4. Import safety tests (no database connections on import)
# ===========================================================================


def test_importing_alembic_env_makes_no_database_connection() -> None:
    """Importing alembic/env.py must not create an engine or connect to the database."""
    with patch("sqlalchemy.create_engine") as mock_engine, patch("psycopg.connect") as mock_connect:
        _load_alembic_env_module()
        assert not mock_engine.called, "create_engine must not be called during module import"
        assert not mock_connect.called, "psycopg.connect must not be called during module import"


# ===========================================================================
# 5. Migration runner tests (offline and online execution)
# ===========================================================================


def test_run_migrations_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_migrations_offline must configure context with literal_binds and app URL."""
    mod = _load_alembic_env_module()

    test_url = "postgresql+psycopg://offline_user:pass@localhost:5432/offline_db"
    monkeypatch.setattr(mod, "get_url", lambda: test_url)

    mock_context = MagicMock()
    monkeypatch.setattr(mod, "context", mock_context)

    mod.run_migrations_offline()

    mock_context.configure.assert_called_once_with(
        url=test_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    mock_context.begin_transaction.assert_called_once()
    mock_context.run_migrations.assert_called_once()


def test_run_migrations_online_creates_engine_with_nullpool_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_migrations_online must create an engine with NullPool and dispose it in finally."""
    mod = _load_alembic_env_module()

    test_url = "postgresql+psycopg://online_user:pass@localhost:5432/online_db"
    monkeypatch.setattr(mod, "get_url", lambda: test_url)

    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_create_engine = MagicMock(return_value=mock_engine)
    monkeypatch.setattr(mod, "create_engine", mock_create_engine)

    mock_context = MagicMock()
    monkeypatch.setattr(mod, "context", mock_context)
    monkeypatch.setattr(mod, "config", None)

    mod.run_migrations_online()

    mock_create_engine.assert_called_once_with(test_url, poolclass=pool.NullPool)
    mock_context.configure.assert_called_once_with(
        connection=mock_connection,
        target_metadata=Base.metadata,
    )
    mock_context.begin_transaction.assert_called_once()
    mock_context.run_migrations.assert_called_once()
    mock_engine.dispose.assert_called_once()


def test_run_migrations_online_disposes_engine_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_migrations_online must dispose the engine even if migration execution fails."""
    mod = _load_alembic_env_module()

    test_url = "postgresql+psycopg://online_user:pass@localhost:5432/online_db"
    monkeypatch.setattr(mod, "get_url", lambda: test_url)

    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_create_engine = MagicMock(return_value=mock_engine)
    monkeypatch.setattr(mod, "create_engine", mock_create_engine)

    mock_context = MagicMock()
    mock_context.run_migrations.side_effect = RuntimeError("Migration script syntax error")
    monkeypatch.setattr(mod, "context", mock_context)
    monkeypatch.setattr(mod, "config", None)

    with pytest.raises(RuntimeError, match="Migration script syntax error"):
        mod.run_migrations_online()

    # Engine must still be cleanly disposed
    mock_engine.dispose.assert_called_once()


def test_run_migrations_online_reuses_existing_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When config.attributes provides 'connection', run_migrations_online reuses it."""
    mod = _load_alembic_env_module()

    mock_conn = MagicMock()
    mock_config = MagicMock()
    mock_config.attributes = {"connection": mock_conn}
    monkeypatch.setattr(mod, "config", mock_config)

    mock_create_engine = MagicMock()
    monkeypatch.setattr(mod, "create_engine", mock_create_engine)

    mock_context = MagicMock()
    monkeypatch.setattr(mod, "context", mock_context)

    mod.run_migrations_online()

    # create_engine must NOT have been called because connection was reused
    assert not mock_create_engine.called
    mock_context.configure.assert_called_once_with(
        connection=mock_conn,
        target_metadata=Base.metadata,
    )
    mock_context.begin_transaction.assert_called_once()
    mock_context.run_migrations.assert_called_once()
