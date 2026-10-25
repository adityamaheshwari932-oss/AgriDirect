"""SQLAlchemy engine and session factory.

This module provides explicit database engine and session factory management,
as well as the ``get_db`` generator for FastAPI dependency injection.

Key design decisions
---------------------
* **Synchronous API** — we use ``create_engine`` and ``sessionmaker`` from
  ``sqlalchemy`` (not ``sqlalchemy.ext.asyncio``).  All I/O in route
  handlers is therefore blocking.  This keeps the code simple and avoids
  the additional complexity of ``async``/``await`` at this stage.

* **Explicit lifecycle** — importing this module does **not** create an engine
  or read settings.  The engine and sessionmaker are explicitly initialized via
  ``init_db()`` (e.g. during FastAPI application lifespan startup) and cleanly
  disposed via ``close_db()`` during shutdown.

* **Import safety** — this module can be imported anywhere without requiring
  valid database settings or a running database.

* **Clear error reporting** — if ``get_db()``, ``get_engine()``, or
  ``get_session_factory()`` is called before ``init_db()``, a clear
  ``RuntimeError`` is raised directing the developer to call ``init_db()``.

* **Session lifetime** — the ``get_db`` generator opens a session, yields it
  to the caller, and always closes it in the ``finally`` block — even if the
  route handler raises an exception.  The caller (route handler) is
  responsible for committing or rolling back the transaction before the
  session is closed.

No tables are created here.  Schema management is handled by Alembic
migrations (to be implemented in Phase 2).
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

# Module-level singletons, initialized explicitly via init_db()
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


# ---------------------------------------------------------------------------
# Lifecycle management
# ---------------------------------------------------------------------------

def init_db(
    database_url: str | None = None,
    *,
    engine: Engine | None = None,
    echo: bool = False,
) -> None:
    """Initialize the database engine and session factory.

    Args:
        database_url: Optional connection URL. If omitted and ``engine`` is None,
            the URL is read from application settings via ``get_settings().database_url``.
        engine: Optional pre-configured SQLAlchemy ``Engine`` instance (useful for
            testing with in-memory SQLite or custom mocks).
        echo: If True, SQLAlchemy logs all executed SQL statements.

    Raises:
        ValidationError: If database_url is not provided and application settings
            are missing or invalid.
    """
    global _engine, _session_factory

    # Clean up and reset any existing engine and session factory first.
    close_db()

    new_engine: Engine | None = None
    try:
        if engine is not None:
            new_engine = engine
        else:
            url = database_url if database_url is not None else get_settings().database_url
            new_engine = create_engine(url, echo=echo)

        new_factory = sessionmaker(
            bind=new_engine,
            autocommit=False,
            autoflush=False,
        )
    except Exception:
        # If a newly created engine was instantiated before an error occurred
        # (e.g. sessionmaker failing), dispose it. Do not dispose if caller passed `engine`.
        if new_engine is not None and new_engine is not engine:
            new_engine.dispose()
        _engine = None
        _session_factory = None
        raise

    _engine = new_engine
    _session_factory = new_factory


def close_db() -> None:
    """Dispose of the database engine and reset session factory.

    Disposes the connection pool of the active engine and resets
    module-level references to None. Safe to call even if the database
    has not been initialized.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _session_factory = None


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

def get_engine() -> Engine:
    """Return the initialized SQLAlchemy engine.

    Returns:
        The active ``Engine`` instance.

    Raises:
        RuntimeError: If database initialization has not been performed.
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine has not been initialized. "
            "Call init_db() during application startup before accessing the engine."
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the initialized sessionmaker factory.

    Returns:
        The active ``sessionmaker[Session]`` instance.

    Raises:
        RuntimeError: If database initialization has not been performed.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database session factory has not been initialized. "
            "Call init_db() during application startup before requesting a session."
        )
    return _session_factory


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session for use in a FastAPI route handler.

    This function is designed to be used with FastAPI's ``Depends()``
    mechanism::

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db.session import get_db

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    The session is always closed when the request finishes, whether it
    succeeded or raised an exception.  The route handler is responsible
    for calling ``db.commit()`` after successful writes.  If an exception
    propagates out of the handler, the session is closed without committing
    (effectively rolling back the transaction).

    Yields:
        An open SQLAlchemy ``Session`` bound to the configured engine.

    Raises:
        RuntimeError: If called before ``init_db()`` has initialized the database.
    """
    session_factory = get_session_factory()
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()
