# AgriDirect — AGENTS.md
# Project-Wide Instructions for AI Coding Agents

This file provides authoritative, binding guidance for all AI agents (including Antigravity IDE) working on the AgriDirect codebase. Read this file before making any changes.

---

## Project Identity

**AgriDirect** is a B2B agricultural marketplace connecting farmers directly with commercial buyers. It facilitates trade — it does not own produce, process payments, or manage logistics.

For full context, read [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md).

---

## Technology Stack (Non-Negotiable)

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 18+ / TypeScript | Vite build tool; strict TypeScript mode |
| Backend | Python 3.12+ / FastAPI | Async-first; structured package layout |
| Database | PostgreSQL 16+ | Primary data store |
| ORM | SQLAlchemy 2.x (async) | Use `AsyncSession`; no raw SQL except analytics |
| Validation | Pydantic v2 | All request/response schemas must use Pydantic |
| Auth | JWT + bcrypt | Access + refresh token pattern; bcrypt via passlib |
| API | REST | JSON responses; versioned under `/api/v1/` |
| Containerisation | Docker + Docker Compose | Multi-service compose file |
| Version Control | Git + GitHub | Feature branches; PRs for all changes |

Do **not** introduce alternative frameworks, ORMs, or languages without an explicit instruction and documented justification.

---

## Architectural Rules

### General
- Use a **modular monolith**: one deployable backend service with clearly separated internal modules.
- Every module must have its own `routes.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`.
- Cross-module access goes through **service interfaces**, never directly between repositories.
- No circular imports. No business logic in route handlers or models.

### Backend Directory Structure (target)
```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory
│   ├── config.py                # Settings via Pydantic BaseSettings
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── dependencies.py          # Shared FastAPI dependency injections
│   ├── auth/                    # JWT, password hashing, auth middleware
│   ├── users/                   # Registration, profile, verification
│   ├── listings/                # Produce listings (farmers)
│   ├── requirements/            # Buyer requirements
│   ├── offers/                  # Offer / counter-offer negotiation
│   ├── orders/                  # Order lifecycle, amendments
│   ├── chat/                    # Contextual messaging
│   ├── analytics/               # Descriptive market analytics
│   ├── admin/                   # Admin verification workflows
│   └── notifications/           # In-app / email notifications
├── alembic/                     # Database migrations
├── tests/                       # pytest-based test suite
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Frontend Directory Structure (target)
```
frontend/
├── src/
│   ├── api/            # Typed API client (axios / fetch wrappers)
│   ├── components/     # Reusable UI components
│   ├── features/       # Feature-sliced modules (auth, listings, orders…)
│   ├── hooks/          # Custom React hooks
│   ├── pages/          # Route-level page components
│   ├── store/          # Global state (Zustand or Redux Toolkit)
│   ├── types/          # Shared TypeScript interfaces
│   └── utils/          # Pure utility functions
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── Dockerfile
```

---

## Security Requirements (Mandatory)

1. **Backend enforces all business rules.** The frontend may hide UI elements as UX sugar, but the API must independently reject unauthorised requests.
2. All protected endpoints must use FastAPI dependency injection to verify JWT tokens and check user role + verification status.
3. Passwords must never be stored in plain text. Use `passlib[bcrypt]`.
4. JWT secrets must come from environment variables; they must never be hardcoded.
5. All user inputs must be validated by Pydantic schemas before reaching service or repository layers.
6. Use parameterised queries only. SQLAlchemy ORM handles this; never use f-strings to build SQL.
7. Sensitive data (passwords, tokens, payment details) must never appear in logs.
8. CORS must be explicitly configured; do not use wildcard origins in production settings.
9. Rate limiting must be applied to authentication endpoints.
10. HTTP-only, Secure cookies for refresh tokens in production.

---

## Business Rule Enforcement (Mandatory)

These rules must be enforced on the **backend**. Violations must return appropriate HTTP error responses (4xx), not silently succeed.

| Rule | Enforcement Point |
|---|---|
| Unverified users cannot create listings, offers, orders, or chats | Service layer + route dependency |
| Only verified farmers create listings | `listings` service |
| Only verified buyers place orders | `orders` service |
| Inventory changes require farmer approval workflow | `listings` service |
| Finalized orders cannot be silently edited | `orders` service; all changes recorded as amendments |
| AgriDirect never processes payments | No payment gateway code; only record-keeping |
| Accepted offers create orders atomically | `offers` service, database transaction |

---

## Testing Requirements

- Use **pytest** for all backend tests.
- Use **Vitest** + **React Testing Library** for frontend unit/component tests.
- Every service function must have unit tests with mocked repositories.
- Every API route must have integration tests using `httpx.AsyncClient` against a test database.
- Test coverage target: **≥ 80%** for backend business logic.
- Tests must run in isolation; never depend on external services or shared state.
- CI must run the full test suite before any merge.
- Test files live in `backend/tests/` and `frontend/src/**/__tests__/`.

---

## Database & Migration Rules

- All schema changes go through **Alembic** migrations. Never use `Base.metadata.create_all()` in production.
- Each migration must be reversible (include `downgrade()`).
- Never rename or drop columns without a deprecation migration.
- Use soft deletes (`is_deleted`, `deleted_at`) for user-facing entities where audit trails matter.
- UUID primary keys for all user-facing tables.
- Timestamps: `created_at`, `updated_at` on every table (UTC).

---

## Incremental Implementation Workflow

**Never implement features out of order.** Respect data and dependency relationships.

Phases are defined in [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md). At each phase:

1. Read the phase description and its dependencies.
2. Write failing tests first (TDD preferred).
3. Implement the minimum required code to pass tests.
4. Run the full test suite before declaring a phase complete.
5. Update relevant documentation in `docs/`.
6. Do not begin the next phase until the current phase's tests pass and code is reviewed.

---

## Code Style

### Python
- Follow **PEP 8**; enforced via `ruff`.
- Type-annotate all function signatures.
- Use `async def` for all route handlers and service/repository methods that perform I/O.
- Docstrings on all public functions and classes (Google style).
- Maximum line length: **100 characters**.

### TypeScript / React
- Strict mode enabled in `tsconfig.json`.
- Functional components only; no class components.
- Custom hooks for all data-fetching logic.
- No `any` type without explicit justification comment.
- ESLint + Prettier enforced.

---

## What Agents Must NOT Do

- ❌ Do not install packages globally or modify the system Python.
- ❌ Do not hardcode credentials, secrets, or environment-specific URLs.
- ❌ Do not bypass the verification check in business logic.
- ❌ Do not silently deduct inventory or silently modify finalized orders.
- ❌ Do not implement payment processing or fund movement.
- ❌ Do not implement ML forecasting.
- ❌ Do not create migrations with irreversible column drops without explicit instruction.
- ❌ Do not skip tests to save time.
- ❌ Do not commit directly to `main`; use feature branches.
- ❌ Do not ignore the `IMPLEMENTATION_PLAN.md` phase order.

---

## Documentation

- Architecture decisions must be recorded in `docs/architecture/` as ADR (Architecture Decision Record) files.
- Database schema changes must be reflected in `docs/database/`.
- API endpoints must be documented via FastAPI's automatic OpenAPI generation (no separate Postman collections).
- User-facing flows and data flows must be documented in `docs/dfd/`.
