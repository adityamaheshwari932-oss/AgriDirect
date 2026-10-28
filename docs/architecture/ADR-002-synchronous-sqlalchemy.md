# ADR-002: Synchronous SQLAlchemy Session Architecture

**Status:** Accepted  
**Date:** 2026-10-28  

## Context

The initial project specifications (`AGENTS.md` and early planning notes) suggested using SQLAlchemy 2.x with asynchronous sessions (`AsyncSession` via `asyncpg`). However, during Phase 1 infrastructure implementation, a deliberate design decision was implemented in `backend/app/db/session.py`:
- A synchronous SQLAlchemy 2.x engine was configured with `create_engine` and `sessionmaker` using the modern binary Psycopg 3 driver (`postgresql+psycopg`).
- FastAPI dependency injection yields a synchronous `Session` via `get_db()`.
- Route handlers performing database queries are written as synchronous `def` functions rather than `async def`.

Prior to implementing broader business APIs (Authentication, Listings, Offers, Orders), we audited this approach against the alternative of refactoring to an asynchronous `AsyncSession` architecture across the entire codebase.

## Decision

We retain the **synchronous SQLAlchemy 2.x session architecture** with the following conventions:

1. **Session Factory & Driver**: Use synchronous `create_engine` and `sessionmaker[Session]` with `psycopg` (binary driver).
2. **Dependency Injection**: Route handlers obtain database access via `db: Session = Depends(get_db)`.
3. **Execution Model & Thread Pooling**:
   - Route handlers performing synchronous database I/O are declared as synchronous `def` functions (`def my_endpoint(...)`).
   - FastAPI automatically offloads synchronous route handlers to an external worker thread pool (via `anyio.to_thread.run_sync`), ensuring that blocking database I/O **never blocks the primary asynchronous event loop**.
   - Services and repositories accept synchronous `Session` instances and run synchronously within the thread pool worker for the request.
4. **Pure Asynchronous Operations**: For purely async I/O (e.g. streaming, WebSockets, or external non-blocking HTTP requests), `async def` is used.
5. **Session Lifecycle**: The `get_db()` generator strictly manages session lifetime, closing sessions in a `finally` block to guarantee connection pool health and prevent connection leaks.

## Consequences

### Positive
- **Simplicity and Maintainability**: Avoids `await` proliferation across repository, model, and service layers. ORM relationship lazy-loading and property access function predictably without requiring explicit `awaitable_attrs` or eager-loading gymnastics required by async SQLAlchemy.
- **Robustness**: Synchronous drivers and threadpool execution are battle-tested and eliminate async event-loop deadlocks during nested transactions or complex multi-table joins.
- **Test Stability**: The test suite (including SQLite in-memory and isolated transactional tests) executes cleanly and deterministically without cross-thread connection pooling conflicts.
- **Consistency**: All 25 database models, 7 Alembic migrations, and Group 11 (Notifications) are already built and tested against this architecture.

### Trade-offs & Mitigations
- **Thread Pool Concurrency Limits**: Under extremely high concurrent request loads, thread pool exhaustion could occur if threads are held for long durations.
  - *Mitigation*: Database queries are optimized with appropriate indexes, query pagination is enforced, and long-running analytics queries are separated. The default AnyIO thread pool capacity (40 threads) can be scaled via configuration if necessary.
- **Documentation Alignment**: Project instructions (`AGENTS.md`, `IMPLEMENTATION_PLAN.md`) must be explicitly updated to prevent coding assistants and developers from introducing conflicting `async def` DB patterns or a second session manager.
