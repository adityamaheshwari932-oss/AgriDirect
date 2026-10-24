"""SQLAlchemy engine and session factory.

This module creates the database engine and a session factory from the
validated application settings.  It also provides a ``get_db`` generator
that FastAPI route handlers will use as a dependency injection.

Key design decisions
---------------------
* **Synchronous API** — we use ``create_engine`` and ``sessionmaker`` from
  ``sqlalchemy`` (not ``sqlalchemy.ext.asyncio``).  All I/O in route
  handlers is therefore blocking.  This keeps the code simple and avoids
  the additional complexity of ``async``/``await`` at this stage.

* **Lazy connection** — importing this module does **not** open a connection
  to PostgreSQL.  The connection pool is created when the engine is first
  used (i.e. when a session executes a query).  This means the application
  can import and test this module without a running database.

* **Engine singleton** — ``_engine`` and ``_SessionLocal`` are module-level
  variables created once at import time from the current settings.  This is
  straightforward and appropriate for a single-process application.

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

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# ``create_engine`` records the connection parameters but does not open a
# TCP connection until the engine is first used.  SQLAlchemy maintains an
# internal connection pool (default: 5 connections) that is created on
# first use and reused across requests.
#
# echo=False  — set to True temporarily to log every SQL statement to stdout
#               during debugging.  Do not leave True in committed code.
# ---------------------------------------------------------------------------

_engine: Engine = create_engine(
    get_settings().database_url,
    echo=False,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
# ``sessionmaker`` is a factory that produces new ``Session`` objects.
# ``autocommit=False`` means every session starts in a transaction that
# must be explicitly committed or rolled back — the safe default.
# ``autoflush=False`` means pending changes are NOT sent to the database
# before every query; we control flushes explicitly.  This prevents
# surprising behaviour when building up a batch of changes.
# ``bind=_engine`` wires every session to our engine.
# ---------------------------------------------------------------------------

_SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=_engine,
    autocommit=False,
    autoflush=False,
)


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
        An open SQLAlchemy ``Session`` bound to the application database.
    """
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public helpers (used by tests and future application code)
# ---------------------------------------------------------------------------

def get_engine() -> Engine:
    """Return the module-level SQLAlchemy engine.

    Exposed primarily for testing and diagnostic purposes.

    Returns:
        The application's ``Engine`` instance.
    """
    return _engine
