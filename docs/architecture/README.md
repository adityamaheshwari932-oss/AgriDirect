# Architecture Documentation

**Project:** AgriDirect  
**Status:** 🔴 Draft — to be populated during Phase 1+

---

## Purpose

This folder contains Architecture Decision Records (ADRs) and system design documents that explain the *why* behind key architectural choices.

## Architecture Decision Records (ADRs)

ADRs follow this format:

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNN
**Date:** YYYY-MM-DD

## Context
What situation or problem prompted this decision?

## Decision
What was decided?

## Consequences
What are the trade-offs, benefits, and risks?
```

## Planned ADRs

| File | Decision | Status |
|---|---|---|
| `ADR-001-modular-monolith.md` | Use modular monolith vs microservices | Pending |
| `ADR-002-synchronous-sqlalchemy.md` | Synchronous SQLAlchemy 2.x Session with threadpool execution | Accepted |
| `ADR-003-requirement-fulfillment-approval.md` | Requirement fulfillment approval workflow & schema | Accepted & Verified |
| `ADR-004-jwt-authentication.md` | JWT with refresh tokens vs session-based auth | Pending |
| `ADR-005-postgresql.md` | PostgreSQL as primary data store | Pending |
| `ADR-006-soft-deletes.md` | Soft delete strategy for user-facing entities | Pending |
| `ADR-007-inventory-workflow.md` | Explicit approval workflow for inventory changes | Pending |
| `ADR-008-order-lifecycle-and-amendments.md` | Orders, inventory lifecycle, and bilateral amendment workflow | Accepted & Verified |
| `ADR-009-contextual-messaging-and-communication.md` | Contextual messaging, media attachments, contact disclosure, and communication system | Accepted & Verified |

## Planned Design Documents

| File | Description | Status |
|---|---|---|
| `system-overview.md` | High-level system component diagram | Pending |
| `api-design.md` | REST API design conventions and versioning | Pending |
| `security-model.md` | Authentication, authorisation, and data protection | Pending |
| `deployment.md` | Deployment architecture and Docker Compose setup | Pending |
