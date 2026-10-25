from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base

# Import all model modules so that their Table definitions attach to Base.metadata
# for Alembic's 'autogenerate' feature. As new model modules are added to app/models/,
# ensure they are imported in app/models/__init__.py or here.
import app.models  # noqa: F401

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL from application settings."""
    return get_settings().database_url


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
try:
    config = context.config
except AttributeError:
    config = None

# Interpret the config file for Python logging.
if config is not None:
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    # Configure Alembic with the runtime database URL from application settings.
    # Credentials are never stored in alembic.ini.
    # Percent signs (%) in URL-encoded passwords must be escaped as '%%' for
    # configparser compatibility to prevent interpolation syntax errors.
    try:
        _runtime_url = get_url()
        config.set_main_option("sqlalchemy.url", _runtime_url.replace("%", "%%"))
    except Exception:
        # Fall back safely if settings are unconfigured (e.g. during test imports)
        _runtime_url = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the SQL statements to stdout/script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates a synchronous SQLAlchemy Engine and associates a connection
    with the Alembic migration context.
    """
    # Reuse an existing connection if provided via config attributes (e.g. in tests)
    connectable = config.attributes.get("connection", None) if config is not None else None

    if connectable is not None:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        url = get_url()
        engine = create_engine(
            url,
            poolclass=pool.NullPool,
        )
        try:
            with engine.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                )

                with context.begin_transaction():
                    context.run_migrations()
        finally:
            engine.dispose()


try:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
except (AttributeError, NameError):
    # When env.py is imported outside an active Alembic command (e.g. in tests or
    # documentation tooling), the Alembic context proxy is not yet bound.
    pass
