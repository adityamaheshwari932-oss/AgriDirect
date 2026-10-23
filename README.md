# AgriDirect

**AgriDirect** is a B2B agricultural marketplace that directly connects farmers with commercial buyers — restaurants, hotels, retailers, grocery businesses, caterers, and food processors — removing intermediary friction from the agricultural supply chain.

> **AgriDirect facilitates transactions. It does not own produce, process payments, or manage logistics.**

---

## Project Status

🟡 **Phase 0 — Foundation & Documentation** (in progress)

See [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) for the full roadmap.

---

## Key Features (Planned)

- **Separate onboarding** for farmers and buyers with document-based verification
- **Produce listings** created by verified farmers
- **Buyer requirements** posted by verified buyers
- **Offer & counter-offer negotiation** with structured offers and contextual chat
- **Order lifecycle management** with recorded amendments and mutual confirmation
- **Basic delivery arrangement** and dual-party completion confirmation
- **Payment record capture** (no payment processing)
- **Descriptive market analytics** based on real transaction data
- **Role-based access control** enforced on the backend

---

## Architecture Overview

AgriDirect uses a **modular monolith** architecture with a clear separation between:

```
AgriDirect/
├── backend/           # Python / FastAPI (modular monolith)
│   ├── app/
│   │   ├── auth/          # Authentication & JWT
│   │   ├── users/         # Registration, profiles, verification
│   │   ├── listings/      # Produce listings
│   │   ├── requirements/  # Buyer requirements
│   │   ├── offers/        # Offer negotiation
│   │   ├── orders/        # Order lifecycle
│   │   ├── chat/          # Contextual messaging
│   │   ├── analytics/     # Descriptive market analytics
│   │   ├── admin/         # Admin verification workflows
│   │   └── notifications/ # Event-driven notifications
│   ├── alembic/           # Database migrations
│   └── tests/             # pytest test suite
│
├── frontend/          # React 18 / TypeScript (Vite)
│   └── src/
│       ├── features/      # Feature-sliced modules
│       ├── components/    # Reusable UI components
│       ├── api/           # Typed API client
│       └── pages/         # Route-level components
│
├── docs/              # Project documentation
│   ├── srs/               # Software Requirements Specification
│   ├── dfd/               # Data Flow Diagrams
│   ├── architecture/      # Architecture Decision Records
│   └── database/          # Schema documentation & ERDs
│
├── docker-compose.yml
├── AGENTS.md          # AI agent instructions
├── PROJECT_CONTEXT.md # Business context & rules
└── IMPLEMENTATION_PLAN.md
```

### Backend Layer Responsibilities

| Layer | Responsibility |
|---|---|
| `routes.py` | HTTP request/response handling, input validation delegation |
| `service.py` | Business logic and rule enforcement |
| `repository.py` | Database queries via SQLAlchemy ORM |
| `models.py` | SQLAlchemy table definitions |
| `schemas.py` | Pydantic request/response schemas |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18+ / TypeScript / Vite |
| Backend | Python 3.12+ / FastAPI |
| Database | PostgreSQL 16+ |
| ORM | SQLAlchemy 2.x (async) |
| Validation | Pydantic v2 |
| Authentication | JWT + bcrypt |
| API | REST — versioned at `/api/v1/` |
| Containerisation | Docker + Docker Compose |
| Version Control | Git + GitHub |

---

## Actors

| Actor | Description |
|---|---|
| **Farmer** | Registers, lists produce, negotiates, fulfils orders |
| **Buyer** | Registers, posts requirements, purchases produce |
| **Administrator** | Reviews and approves verification documents |

---

## Business Rules (Summary)

1. Unverified users can browse and manage profiles, but cannot trade.
2. Only verified farmers create listings; only verified buyers place orders.
3. Inventory is never silently deducted — farmer approval is required.
4. Finalised orders are immutable; changes go through recorded amendments.
5. AgriDirect records payment info but never processes or holds money.
6. All security enforcement is on the backend — UI-only restrictions are insufficient.

Full rules: [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)

---

## Getting Started (coming in Phase 1)

Prerequisites, environment setup, and local development instructions will be added when Phase 1 infrastructure is implemented.

---

## Documentation

| Document | Location |
|---|---|
| Project context & business rules | [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) |
| AI agent instructions | [`AGENTS.md`](./AGENTS.md) |
| Implementation roadmap | [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) |
| SRS | [`docs/srs/`](./docs/srs/) |
| Data Flow Diagrams | [`docs/dfd/`](./docs/dfd/) |
| Architecture decisions | [`docs/architecture/`](./docs/architecture/) |
| Database schema | [`docs/database/`](./docs/database/) |

---

## Contributing

This project is under active development. See `AGENTS.md` for coding standards, `IMPLEMENTATION_PLAN.md` for the current phase, and `docs/` for requirements and design documentation.

Feature branches required for all changes. No direct commits to `main`.
