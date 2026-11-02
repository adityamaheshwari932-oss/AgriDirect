# ADR-014: Administrative User Moderation & Platform Governance

**Status:** Accepted & Verified  
**Date:** 2026-11-02  

---

## 1. Context

AgriDirect operates as a direct B2B agricultural marketplace connecting verified farmers with commercial wholesale buyers. To protect platform integrity, preserve market trust, and ensure compliance with platform policies, administrators require authoritative oversight and governance tools (SRS Section 4.14, FR-ADM-01 through FR-ADM-08; DFD Process 9.0).

In agricultural commerce, platform governance involves several distinct operational and technical risks:
1. **Rogue or Non-Compliant Account Actions**: Bad actors, non-responsive counter-parties, or fraudulent accounts must be immediately restrained without corrupting historical transactions, orders, or settled contracts.
2. **Account Restriction vs. Outright Lockout**: Users under dispute or temporary investigation should be permitted read-only access to review their own profile, history, and records without permitting new trade mutations (listings, requirements, offers, chat, payments, reviews). In contrast, suspended or blocked users must be prohibited from logging in entirely.
3. **Sole Administrator Deactivation & Lockout**: Concurrent moderation or rogue administrative attempts to deactivate, suspend, or block the platform's last active administrator could render the entire platform permanently unmanageable.
4. **Marketplace Catalog Side-Effects**: Suspending an account must reliably close all active listings and procurement demands to prevent unwitting counter-parties from entering into negotiations with an inaccessible user. Blocking an account permanently must soft-delete active catalog entries while preserving audit records.
5. **Domain Immutability**: Administrative intervention must never alter economic domain facts—such as produce prices, quantities, harvest dates, or order lines. Moderation can only close, soft-remove, or restore entries.
6. **Concurrency and Audit Integrity**: All administrative interventions must be accompanied by a mandatory, auditable justification ($\ge 10$ characters), recorded in immutable audit logs (`AdminAuditLog`), and notified to the affected user (`Notification`) within the same atomic database transaction.

---

## 2. Decision

We implement **Backend Module 10: Administrative User Moderation & Platform Governance** according to the approved **Version 1.0 Architecture Blueprint**:

### 2.1 Zero Database Migrations
Module 10 introduces zero schema migrations. All operations leverage the existing production PostgreSQL schema (Alembic revision `fcf5c991d506`), including the `users.account_status` column with check constraint `chk_users_account_status ('active', 'restricted', 'suspended', 'blocked')`, `admin_audit_logs`, `notifications`, `produce_listings`, and `buyer_requirements`.

### 2.2 Administrative User Directory & Inspection
- **User Directory (`GET /api/v1/admin/users`)**:
  - Filterable by `role` (`farmer`, `buyer`, `admin`), `account_status` (`active`, `restricted`, `suspended`, `blocked`), `verification_status` (`unverified`, `pending`, `verified`, `rejected`), and registration date range (`registered_from`, `registered_to`).
  - Searchable across email, phone number, farmer display name / farm name, and buyer contact name / business name.
  - Sortable by `created_at`, `email`, `role`, and `account_status` (ascending/descending).
  - Sanitized output: excludes sensitive credentials (`password_hash`, tokens) while returning structured profile summaries.
- **User Detail Inspection (`GET /api/v1/admin/users/{id}`)**:
  - Comprehensive view aggregating safe user identity, full attached profile (`FarmerProfile` or `BuyerProfile`), identity verification history (`VerificationSubmission`), platform activity metrics (listings, requirements, completed orders, complaints filed/received), and the latest 5 administrative audit log events.

### 2.3 User Account Status Moderation
- **Endpoint (`PATCH /api/v1/admin/users/{id}/status`)**:
  - Permits transitions across `active`, `restricted`, `suspended`, and `blocked`.
  - **Permitted Transition Matrix**:
    - `active` $\to$ `restricted`, `suspended`, `blocked`
    - `restricted` $\to$ `active`, `suspended`, `blocked`
    - `suspended` $\to$ `active`, `restricted`, `blocked`
    - `blocked` $\to$ `active` (reinstatement via formal appeal; direct transition from `blocked` to `suspended` or `restricted` is rejected with HTTP 400).
- **Enforced Safeguards**:
  1. *Self-Modification Guard*: Administrators cannot modify their own account status (HTTP 400 Bad Request).
  2. *Idempotency Guard*: Transitioning to the user's current status is rejected as a no-op (HTTP 400 Bad Request).
  3. *Mandatory Rationale*: Reason must be non-empty and at least 10 characters in length (HTTP 422 Unprocessable Entity).
  4. *Last Active Administrator Concurrency Protection*:
     - When deactivating an administrator (`account_status != 'active'`), all active administrators are locked in deterministic ascending ID order (`SELECT ... FOR UPDATE ORDER BY id ASC`) **before** evaluating remaining count.
     - If the remaining active administrator count would drop to zero, the operation is rejected with **HTTP 409 Conflict**.
     - Deterministic row-level ordering guarantees serial execution without deadlocks when two administrators concurrently attempt mutual deactivation.
- **Catalog Side-Effects**:
  - Transition to `suspended`: Closes all currently active or partially fulfilled listings and requirements (`status='closed'`).
  - Transition to `blocked`: Closes and soft-deletes active/partially fulfilled listings and requirements (`status='closed'`, `is_deleted=True`, `deleted_at=now()`).

### 2.4 Produce Listing & Buyer Requirement Moderation
- **Moderation Queues (`GET /api/v1/admin/listings`, `GET /api/v1/admin/requirements`)**:
  - Filterable by lifecycle status, category ID, user ID, deletion status (`is_deleted`), and complaint presence (`has_reports`).
  - Joined dynamically with `UserReport` to report complaint frequencies.
- **Moderation Actions (`POST /api/v1/admin/listings/{id}/moderate`, `POST /api/v1/admin/requirements/{id}/moderate`)**:
  - Supported actions: `close`, `remove`, `restore`.
  - `close`: Sets `status='closed'`. Rejects if already closed (HTTP 400).
  - `remove`: Sets `status='closed'`, `is_deleted=True`, `deleted_at=now()`. Rejects if already removed (HTTP 400).
  - `restore`: Reinstates catalog visibility (`is_deleted=False`, `deleted_at=None`). Rejects if already active (HTTP 400).
    - Listings: Validates `expires_at > now` and `available_quantity > 0`. Restores to `active` if available equals initial quantity, else `partially_fulfilled`.
    - Requirements: Validates `required_by_date >= today` and `remaining_quantity > 0`. Restores to `active` if remaining equals required quantity, else `partially_fulfilled`.
  - **Domain Immutability Invariant**: Moderation never mutates prices, units, quantities, or order associations.

### 2.5 Cross-Module Account Status Enforcement
- `active`: Full platform access according to assigned role and verification status.
- `restricted`: Permitted to authenticate and view own account profile in read-only mode (`GET /api/v1/users/me`), but strictly blocked from mutations and marketplace actions:
  - Profile updates (`PATCH /api/v1/users/me`) $\to$ HTTP 403 Forbidden
  - Creating produce listings (`POST /api/v1/listings`) $\to$ HTTP 403 Forbidden
  - Creating buyer requirements (`POST /api/v1/requirements`) $\to$ HTTP 403 Forbidden
  - Initiating offers, chats, payments, or reviews $\to$ HTTP 403 Forbidden
- `suspended` & `blocked`: Prohibited from logging in (`POST /api/v1/auth/login` returns HTTP 403 Forbidden: "Account is suspended or restricted"). Any preexisting token is rejected across all protected endpoints including `GET /api/v1/users/me` with HTTP 403 Forbidden.

### 2.6 Atomic Audit Logging & In-App Notifications
Every administrative status change or catalog moderation action creates:
1. An `AdminAuditLog` record (`admin_user_id`, `action`, `target_entity_type`, `target_entity_id`, `reason`, `ip_address`).
2. An in-app `Notification` record delivered to the affected counter-party.
Both records are added to the active database session and committed atomically with the entity status update within a single synchronous PostgreSQL transaction.

---

## 3. Consequences

### Positive
- **Guaranteed Platform Survival**: Concurrency-safe last active administrator protection ensures the platform cannot be accidentally or maliciously left without administrative control.
- **Proportional Discipline**: The `restricted` state provides a middle ground for compliance reviews and trade disputes without locking users out of historical account review.
- **Zero Orphaned Side-Effects**: Closing or removing catalog entries on user suspension/blocking prevents marketplace counter-parties from interacting with dead accounts.
- **Strict Domain Preservation**: Commercial trade data, inventory numbers, and prices remain uncorrupted by administrative moderation actions.
- **Complete Audit Trail**: Every action is permanently recorded with actor identity, target, timestamp, rationale, and client IP address.

### Negative / Trade-Offs
- Administrative directory queries perform multi-table aggregations for activity counts; mitigated by indexed foreign keys on `user_id` and limit-bounded queries.

---

## 4. Verification & Testing

Module 10 implementation is verified by:
1. `backend/tests/test_admin_moderation_api.py` (40 comprehensive unit and integration tests across directory pagination, filters, status transitions, catalog moderation lifecycles, and cross-module enforcement).
2. `backend/tests/test_postgres_module10.py` (4 isolated PostgreSQL concurrency tests verifying multi-threaded mutual suspension race conditions, row-level locking, and transactional atomicity against `agridirect_module3_test`).
3. Full backend regression test suite: 866 passing tests (baseline: 822; new: 44; 0 failures).

