# Database Documentation

**Project:** AgriDirect  
**Status:** 🔴 Draft — to be populated during Phase 2+

---

## Purpose

This folder contains the database schema documentation, Entity-Relationship Diagrams (ERDs), and the data dictionary for AgriDirect's PostgreSQL database.

## Conventions

- All tables use **UUID primary keys**.
- All tables include `created_at` and `updated_at` timestamp columns (UTC, non-nullable).
- User-facing entities use **soft deletes** via `is_deleted` (boolean) and `deleted_at` (timestamp, nullable).
- All schema changes are managed through **Alembic** migrations — never manual `CREATE TABLE`.
- Foreign keys are explicitly defined and indexed.

## Planned Documents

| File | Description | Status |
|---|---|---|
| `ERD-overview.md` | Full entity-relationship diagram (Mermaid) | Pending |
| `data-dictionary.md` | Table-by-table column definitions, types, and constraints | Pending |
| `migration-log.md` | Human-readable log of all Alembic migrations | Pending |

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
