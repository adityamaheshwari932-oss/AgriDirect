"""Centralized PostgreSQL test database lifecycle, safety, and migration checks.

Safety Guarantees:
- Operates exclusively against the isolated `agridirect_module3_test` database.
- Explicitly refuses to execute against `agridirect_db` or any other database.
- Validates Alembic's single revision head and lineage dynamically before running tests.
"""

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

PG_TEST_DB_NAME = "agridirect_module3_test"
PG_FORBIDDEN_PROD_DB_NAME = "agridirect_db"
PG_TEST_DB_URL = (
    "postgresql+psycopg://agridirect_app:agridirect@localhost:5432/agridirect_module3_test"
)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


def assert_isolated_pg_database(conn_or_session: Connection | Session) -> str:
    """Verify the active PostgreSQL connection points strictly to agridirect_module3_test."""
    db_name = conn_or_session.execute(text("SELECT current_database()")).scalar()
    if db_name == PG_FORBIDDEN_PROD_DB_NAME or db_name != PG_TEST_DB_NAME:
        raise RuntimeError(
            f"ABORT: Refusing PostgreSQL test operations on '{db_name}' "
            f"(expected isolated '{PG_TEST_DB_NAME}')."
        )
    return str(db_name)


def _get_alembic_config_and_script() -> tuple[Config, ScriptDirectory]:
    cfg = Config(str(_ALEMBIC_INI))
    script = ScriptDirectory.from_config(cfg)
    return cfg, script


def get_alembic_head_and_lineage() -> tuple[str, list[str]]:
    """Return the single current Alembic head revision and full revision lineage to base."""
    _, script = _get_alembic_config_and_script()
    heads = script.get_heads()
    if len(heads) != 1:
        raise AssertionError(
            f"Expected single linear Alembic head, found {len(heads)}: {heads}"
        )
    head_rev = heads[0]
    lineage = [rev.revision for rev in script.iterate_revisions(head_rev, "base")]
    return head_rev, lineage


@lru_cache(maxsize=1)
def ensure_pg_test_schema_at_head(db_url: str = PG_TEST_DB_URL) -> str:
    """Safely migrate the isolated PostgreSQL test database to Alembic head once per process."""
    head_rev, lineage = get_alembic_head_and_lineage()
    engine: Engine = create_engine(db_url)
    try:
        with engine.connect() as check_conn:
            assert_isolated_pg_database(check_conn)
            current_rev = check_conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()

        if current_rev == head_rev:
            return head_rev

        if current_rev not in lineage:
            raise RuntimeError(
                f"Test database revision '{current_rev}' is not in Alembic lineage "
                f"leading to '{head_rev}'."
            )

        cfg, _ = _get_alembic_config_and_script()
        # Execute upgrade on an explicit verified connection to agridirect_module3_test.
        with engine.begin() as mig_conn:
            assert_isolated_pg_database(mig_conn)
            cfg.attributes["connection"] = mig_conn
            command.upgrade(cfg, "head")
    finally:
        engine.dispose()

    return head_rev


def assert_pg_migration_state(
    session: Session,
    *,
    minimum_revision: str | None = None,
) -> str:
    """Assert isolated PG DB identity, single Alembic head, and migrated revision state."""
    assert_isolated_pg_database(session)
    head_rev, lineage = get_alembic_head_and_lineage()
    if minimum_revision is not None and minimum_revision not in lineage:
        raise AssertionError(
            f"Minimum required revision '{minimum_revision}' not found in Alembic lineage"
        )

    current_rev = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if current_rev != head_rev:
        raise AssertionError(
            f"PostgreSQL test DB revision '{current_rev}' is out of sync with "
            f"Alembic head '{head_rev}'"
        )
    return str(current_rev)


def cleanup_pg_test_tables(session_factory: sessionmaker) -> None:
    """Pre-flight check DB identity and truncate all non-migration tables safely."""
    with session_factory() as db:
        assert_isolated_pg_database(db)
        rows = db.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename <> 'alembic_version'
                ORDER BY tablename
                """
            )
        ).fetchall()
        table_names = [f'"{r[0]}"' for r in rows]
        if table_names:
            db.execute(
                text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE")
            )
            db.commit()

