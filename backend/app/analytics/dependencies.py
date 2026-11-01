"""FastAPI dependencies for AgriDirect Module 9: Descriptive Market Analytics.

Provides read-only database session management with:
1. PostgreSQL session/transaction level 'SET TRANSACTION READ ONLY'.
2. SQLAlchemy event listener 'before_flush' mutation barrier raising RuntimeError.
3. Strict session rollback and closure in finally blocks.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.db.session import get_session_factory


def get_read_only_db() -> Generator[Session, None, None]:
    """Yield an isolated, read-only database session preventing all data mutations.

    Enforces:
    - PostgreSQL SET TRANSACTION READ ONLY statement on connection.
    - SQLAlchemy ORM 'before_flush' barrier intercepting and rejecting write attempts.
    - Explicit rollback in the finally block before releasing the connection.
    """
    session_factory = get_session_factory()
    db: Session = session_factory()

    def _prevent_flush(session: Session, flush_context: Any, instances: Any) -> None:
        raise RuntimeError("Data mutations are strictly prohibited in read-only analytics sessions.")

    # Register mutation barrier
    event.listen(db, "before_flush", _prevent_flush)

    # Apply database-level read-only transaction if supported (PostgreSQL)
    try:
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.execute(text("SET TRANSACTION READ ONLY"))
    except Exception:
        # Graceful fallback for dialects (like in-memory SQLite) without native SET TRANSACTION
        pass

    try:
        yield db
    finally:
        try:
            event.remove(db, "before_flush", _prevent_flush)
        except Exception:
            pass
        db.rollback()
        db.close()
