# Database Documentation

**Project:** AgriDirect  
**Status:** 🟢 Baseline Schema Design Complete (`schema-design.md`)

---

## Purpose

This folder contains the database schema documentation, Entity-Relationship Diagrams (ERDs), and the data dictionary for AgriDirect's PostgreSQL database.

## Documents

| File | Description | Status |
|---|---|---|
| [`schema-design.md`](./schema-design.md) | Authoritative database design specification, 25-table data dictionary, Mermaid ERD, state machines, normalization & concurrency analysis | Complete (Phase 1 Baseline) |
| `migration-log.md` | Human-readable log of all Alembic migrations | Pending (Phase 2+) |

## Entity Summary (Planned)

| Entity | Module | Description |
|---|---|---|
| `users` | users | All registered users (farmers and buyers) |
| `verification_documents` | users | Documents submitted for identity/business verification |
| `listings` | listings | Produce listings created by verified farmers |
| `listing_categories` | listings | Produce categories (hierarchy) |
| `buyer_requirements` | requirements | Procurement requirements posted by buyers |
| `offers` | offers | Offer and counter-offer records |
| `orders` | orders | Orders created from accepted offers |
| `order_amendments` | orders | Recorded changes to finalised orders |
| `chat_threads` | chat | Conversation threads (linked to offers/orders) |
| `chat_messages` | chat | Individual messages within threads |
| `payment_records` | payments | Payment information records (no processing) |
| `notifications` | notifications | In-app notification events |

## Indexing Strategy

- Primary keys: always UUID, auto-indexed.
- Foreign keys: always indexed.
- Frequently filtered columns: `user_id`, `status`, `created_at`, `is_deleted`.
- Full-text search on listing titles and descriptions: PostgreSQL `tsvector` / `GIN` index (Phase 4).
