"""Shared SQLAlchemy declarative base for all ORM models.

Every ORM model in this project must inherit from ``Base``::

    from app.db.base import Base

    class SomeModel(Base):
        __tablename__ = "some_table"
        ...

Why a shared base?
------------------
SQLAlchemy's ``Base`` tracks every model class that inherits from it.
Alembic's ``autogenerate`` feature reads ``Base.metadata`` to discover
tables and generate migration scripts automatically.  All models must
share *the same* ``Base`` instance; using separate bases would cause
Alembic to miss tables.

What does NOT belong here?
---------------------------
* No model classes — those live in ``app/models/`` (Phase 2 onwards).
* No engine or session — those are in ``app/db/session.py``.
* No import of ``app/db/session.py`` — that would create a circular import
  (session imports config, config should not import base, etc.).

Adding timestamp and UUID helpers
-----------------------------------
Common column helpers (``created_at``, ``updated_at``, UUID primary key)
will be added to a ``TimestampMixin`` or similar class in a later phase,
once the first real model is defined.  They do not belong here yet.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all AgriDirect ORM models.

    Inherit from this class to register a model with SQLAlchemy's
    metadata and make it visible to Alembic::

        from app.db.base import Base

        class MyModel(Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """
