from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base

# Import all model modules so that their Table definitions attach to Base.metadata
# for Alembic's 'autogenerate' feature. As new model modules are added to app/models/,
# ensure they are imported in app/models/__init__.py or here.
import app.models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL from application settings."""
    return get_settings().database_url


# Configure Alembic with the runtime database URL from application settings.
# Credentials are never stored in alembic.ini.
# Percent signs (%) in URL-encoded passwords must be escaped as '%%' for
# configparser compatibility to prevent interpolation syntax errors.
config.set_main_option("sqlalchemy.url", get_url().replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the SQL statements to stdout/script output.
    """
    url = config.get_main_option("sqlalchemy.url")
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
    connectable = config.attributes.get("connection", None)

    if connectable is not None:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
        )
        # When an external connection is provided, the caller owns the transaction.
        context.run_migrations()
    else:
        url = config.get_main_option("sqlalchemy.url")
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
