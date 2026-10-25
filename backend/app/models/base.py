"""Reusable SQLAlchemy model mixins for AgriDirect.

Provides standard columns and behaviors across all domain entities:
- ``UUIDPrimaryKeyMixin``: Surrogate UUID primary keys using PostgreSQL's native
  ``UUID(as_uuid=True)`` and ``gen_random_uuid()``.
- ``TimestampMixin``: Timezone-aware UTC timestamps for ``created_at`` and ``updated_at``.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Provides a surrogate UUID primary key.

    Uses PostgreSQL native UUID with Python ``uuid.uuid4`` generation on the
    client side and ``gen_random_uuid()`` as the server default.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    """Provides timezone-aware UTC audit timestamps.

    Columns:
        created_at: Set on initial row insertion via ``server_default=func.now()``.
        updated_at: Initialized on insert and updated on each modification.

    Note on ``onupdate``:
        SQLAlchemy's ``onupdate=func.now()`` is managed at the Python ORM / Session
        level when an entity is modified via SQLAlchemy. It emits an explicit
        ``SET updated_at = now()`` in generated UPDATE statements. It does NOT
        create an automatic PostgreSQL database trigger for out-of-band raw SQL updates;
        if external systems perform direct SQL updates, a migration-level trigger
        would be required.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
