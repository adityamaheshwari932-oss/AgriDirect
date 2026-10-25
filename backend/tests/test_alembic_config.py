"""Tests for Alembic configuration, URL handling, metadata binding, and migration runners.

These tests verify:
1. Configuration file safety:
   - alembic.ini contains no real credentials.
2. Declarative metadata binding & model discovery:
   - Base.metadata is shared and ready for autogenerate.
   - app.models can be imported without circular dependencies.
3. URL handling across the complete path:
   - Special characters in passwords are escaped safely for ConfigParser (%%)
     and accurately decoded by SQLAlchemy URL parsing without corruption.
4. Offline SQL generation:
   - alembic.command.upgrade(cfg, "head", sql=True) executes offline migration
     environment, emits static SQL (BEGIN; COMMIT;), and requires no live database.
5. Online migration with supplied connection & transaction ownership:
   - Reuses an existing connection provided in config.attributes["connection"].
   - Caller preserves transaction ownership without interference from context.begin_transaction.
6. Online migration engine cleanup:
   - Creates an engine with pool.NullPool when no connection is supplied.
   - Disposes the engine in a finally block even when migration execution raises.
7. Configuration failure propagation:
   - When application settings or database_url are invalid/missing, Alembic
     raises the exception directly rather than silently swallowing it.
8. Application import safety:
   - Importing app.core.config, app.db.base, app.db.session, and app.models
     makes no database connection.

All tests run in isolation without connecting to the real PostgreSQL database.
"""

import configparser
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import MetaData, create_engine, make_url, pool

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.db.base import Base


@pytest.fixture
def alembic_cfg() -> Config:
    """Return an Alembic Config pointing to backend/alembic.ini."""
    ini_path = Path(__file__).parent.parent / "alembic.ini"
    assert ini_path.is_file(), "backend/alembic.ini must exist"
    return Config(str(ini_path))


# ===========================================================================
# 1. Configuration file safety
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
# 2. Metadata binding & model discovery
# ===========================================================================


def test_base_metadata_and_model_discovery() -> None:
    """Base.metadata must exist and app.models must import without circular dependencies."""
    assert isinstance(Base.metadata, MetaData)
    import app.models

    assert app.models is not None
    assert isinstance(Base.metadata.tables, dict)


# ===========================================================================
# 3. URL handling across the complete path
# ===========================================================================


def test_url_escaping_through_complete_path(
    alembic_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test URL handling from Settings through env.py to ConfigParser and SQLAlchemy URL.

    Verifies that URL-encoded characters (%40, %25, %3A) survive Alembic
    configuration handling, that the exact URL is passed to offline context.configure,
    and that make_url recovers the exact decoded credentials without corruption.
    """
    from alembic.runtime.environment import EnvironmentContext

    synthetic_url = (
        "postgresql+psycopg://agri%20app:p%40ss%25word%3A123@localhost:5432/agridirect_test"
    )
    dummy_settings = Settings(
        database_url=synthetic_url,
        secret_key="a" * 32,
        _env_file=None,
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: dummy_settings)

    passed_configure_args: dict[str, object] = {}
    orig_configure = EnvironmentContext.configure

    def spy_configure(self, *args: object, **kwargs: object) -> object:
        passed_configure_args.update(kwargs)
        return orig_configure(self, *args, **kwargs)

    monkeypatch.setattr(EnvironmentContext, "configure", spy_configure)

    # Executing offline upgrade exercises env.py in full:
    # 1. reads get_settings().database_url
    # 2. sets config.set_main_option("sqlalchemy.url", ...) with %% escaping
    # 3. retrieves config.get_main_option("sqlalchemy.url") without InterpolationSyntaxError
    # 4. passes the unescaped URL to context.configure(url=...)
    command.upgrade(alembic_cfg, "head", sql=True)

    retrieved = alembic_cfg.get_main_option("sqlalchemy.url")
    assert retrieved == synthetic_url
    assert passed_configure_args.get("url") == synthetic_url

    parsed = make_url(retrieved)
    assert parsed.username == "agri app"
    assert parsed.password == "p@ss%word:123"


# ===========================================================================
# 4. Offline SQL generation
# ===========================================================================


def test_offline_sql_generation(
    alembic_cfg: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    """Offline migration execution emits static DDL without connecting to a database."""
    command.upgrade(alembic_cfg, "head", sql=True)
    captured = capsys.readouterr()
    assert "BEGIN;" in captured.out
    assert "COMMIT;" in captured.out


# ===========================================================================
# 5. Supplied connection & transaction ownership
# ===========================================================================


def test_online_migration_with_supplied_connection_preserves_transaction(
    alembic_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Supplied connection in config.attributes is reused and preserves caller transaction."""
    mock_create_engine = MagicMock()
    monkeypatch.setattr("sqlalchemy.create_engine", mock_create_engine)

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")

        # 1. Secondary engine must not be created
        assert not mock_create_engine.called
        # 2. Caller's connection must not be closed by Alembic
        assert not conn.closed
        # 3. Caller's transaction must remain active and not prematurely committed
        assert conn.in_transaction()


# ===========================================================================
# 6. Online connection cleanup & NullPool
# ===========================================================================


def test_online_migration_creates_nullpool_and_cleans_up(
    alembic_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no connection is supplied, creates NullPool engine and disposes it cleanly.

    Also verifies that the URL retrieved by the online runner and passed to
    create_engine matches the configured application database URL.
    """
    synthetic_url = (
        "postgresql+psycopg://agri%20app:p%40ss%25word%3A123@localhost:5432/agridirect_test"
    )
    dummy_settings = Settings(
        database_url=synthetic_url,
        secret_key="a" * 32,
        _env_file=None,
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: dummy_settings)

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    mock_create_engine = MagicMock(return_value=mock_engine)
    monkeypatch.setattr("sqlalchemy.create_engine", mock_create_engine)

    with patch("alembic.context.run_migrations"):
        command.upgrade(alembic_cfg, "head")

    assert mock_create_engine.call_count == 1
    passed_url = mock_create_engine.call_args[0][0]
    kwargs = mock_create_engine.call_args[1]
    assert passed_url == synthetic_url
    assert kwargs.get("poolclass") is pool.NullPool
    mock_engine.dispose.assert_called_once()


def test_online_migration_disposes_engine_on_failure(
    alembic_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Engine is disposed even if run_migrations raises an exception."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    mock_create_engine = MagicMock(return_value=mock_engine)
    monkeypatch.setattr("sqlalchemy.create_engine", mock_create_engine)

    with patch("alembic.context.run_migrations", side_effect=RuntimeError("Migration failed")):
        with pytest.raises(RuntimeError, match="Migration failed"):
            command.upgrade(alembic_cfg, "head")

    mock_engine.dispose.assert_called_once()


# ===========================================================================
# 7. Configuration failure propagation
# ===========================================================================


def test_configuration_failure_propagates_directly(
    alembic_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configuration failures in get_settings() propagate directly without being swallowed."""
    monkeypatch.setattr(
        "app.core.config.get_settings",
        MagicMock(side_effect=ValueError("DATABASE_URL is missing")),
    )

    # Verifies offline fails fast without fallback to placeholder URL
    with pytest.raises(ValueError, match="DATABASE_URL is missing"):
        command.upgrade(alembic_cfg, "head", sql=True)

    # Verifies online fails fast without fallback to placeholder URL
    with pytest.raises(ValueError, match="DATABASE_URL is missing"):
        command.upgrade(alembic_cfg, "head")


# ===========================================================================
# 8. Import safety
# ===========================================================================


def test_importing_application_modules_makes_no_db_connection() -> None:
    """Importing application modules must not open connections or create engines."""
    with patch("sqlalchemy.create_engine") as mock_engine, patch("psycopg.connect") as mock_connect:
        import app.core.config
        import app.db.base
        import app.db.session
        import app.models

        assert not mock_engine.called
        assert not mock_connect.called
