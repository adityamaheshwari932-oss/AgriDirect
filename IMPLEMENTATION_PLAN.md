# AgriDirect — Implementation Plan

This plan lists all development phases in strict dependency order. **Do not begin a phase until its predecessors are complete and all tests pass.**

Each phase corresponds to a slice of the system. The goal is always a working, tested, deployable vertical slice — not scaffolding.

---

## Phase 0 — Project Foundation ✅ (Current)

**Goal:** Establish project structure, documentation, and tooling. No application code.

### Deliverables
- [x] `.gitignore`
- [x] `README.md`
- [x] `AGENTS.md`
- [x] `PROJECT_CONTEXT.md`
- [x] `IMPLEMENTATION_PLAN.md`
- [x] `docs/` directory structure

### Acceptance Criteria
- Repository is clean and well-documented.
- All documentation files are present and accurate.

---

## Phase 1 — Infrastructure & Configuration

**Depends on:** Phase 0

**Goal:** Set up the core project skeleton — Docker, environment configuration, database connectivity, and the FastAPI application factory. No business logic yet.

### Deliverables
- `docker-compose.yml` (PostgreSQL, backend, frontend services)
- `backend/app/main.py` — FastAPI app factory with CORS, lifespan, and exception handlers
- `backend/app/config.py` — Pydantic `BaseSettings` (reads `.env`)
- `backend/app/db/session.py` — Synchronous SQLAlchemy engine and session management (`get_db`)
- `backend/requirements.txt` and `backend/Dockerfile`
- `frontend/` — Vite + React + TypeScript scaffold
- `frontend/Dockerfile`
- `alembic/` — migration infrastructure (no tables yet)
- `backend/.env.example`

### Acceptance Criteria
- `docker-compose up` starts all services without errors.
- `GET /health` returns `{"status": "ok"}`.
- Database connection is established; Alembic can run (no migrations yet).
- Frontend dev server starts at `localhost:5173`.

---

## Phase 2 — User Management & Authentication

**Depends on:** Phase 1

**Goal:** Full user registration (farmer + buyer), login, JWT authentication, and profile management.

### Deliverables
- `User` database model and Alembic migration
- Farmer registration endpoint: `POST /api/v1/auth/register/farmer`
- Buyer registration endpoint: `POST /api/v1/auth/register/buyer`
- Login endpoint: `POST /api/v1/auth/login` (returns access + refresh tokens)
- Token refresh: `POST /api/v1/auth/refresh`
- Logout: `POST /api/v1/auth/logout`
- `GET /api/v1/users/me` — authenticated user profile
- `PATCH /api/v1/users/me` — update own profile
- Password hashing with bcrypt
- JWT middleware / FastAPI dependency (`get_current_user`)

### Acceptance Criteria
- Farmers and buyers can register with separate flows.
- Passwords are never stored in plain text.
- JWT tokens are issued on login and validated on protected endpoints.
- Unverified users can log in and view their profile.
- Tests cover registration, login, duplicate email, invalid credentials.

---

## Phase 3 — Verification Workflow (Admin)

**Depends on:** Phase 2

**Goal:** Document upload for verification, admin review, approval/rejection, and role state transitions.

### Deliverables
- `VerificationDocument` model and migration
- `POST /api/v1/users/me/verification` — submit verification documents
- `GET /api/v1/admin/verifications` — list pending verifications (admin only)
- `POST /api/v1/admin/verifications/{id}/approve`
- `POST /api/v1/admin/verifications/{id}/reject`
- Admin role and admin-only dependency
- User `verification_status` field: `unverified | pending | verified | rejected`

### Acceptance Criteria
- Users can submit documents; status changes to `pending`.
- Admin can approve (status → `verified`) or reject (status → `rejected`) with a reason.
- Verified status gates all subsequent business operations.
- Non-admin access to admin endpoints returns 403.

---

## Phase 4 — Produce Listings

**Depends on:** Phase 3

**Goal:** Verified farmers can create, update, and manage produce listings. All users can browse.

### Deliverables
- `Listing` and `ListingCategory` models and migrations
- `POST /api/v1/listings` — create listing (verified farmer only)
- `GET /api/v1/listings` — public listing search/browse (pagination, filters)
- `GET /api/v1/listings/{id}` — listing detail
- `PATCH /api/v1/listings/{id}` — update listing (owner only)
- `DELETE /api/v1/listings/{id}` — soft delete (owner or admin)
- Inventory management fields (`quantity_available`, `unit`, `price_per_unit`)
- Inventory approval workflow stub (required for Phase 7 deduction)

### Acceptance Criteria
- Unverified farmers cannot create listings (403).
- Buyers can browse and view listings.
- Listing owner can edit; others cannot.
- Inventory is tracked but never silently deducted.

---

## Phase 5 — Buyer Requirements

**Depends on:** Phase 3

**Goal:** Verified buyers can post procurement requirements; farmers can browse and respond.

### Deliverables
- `BuyerRequirement` model and migration
- `POST /api/v1/requirements` — post requirement (verified buyer only)
- `GET /api/v1/requirements` — browse requirements (verified farmers + buyers)
- `GET /api/v1/requirements/{id}` — detail
- `PATCH /api/v1/requirements/{id}` — update (owner only)
- `DELETE /api/v1/requirements/{id}` — soft delete (owner or admin)

### Acceptance Criteria
- Unverified buyers cannot post requirements (403).
- Farmers can view requirements and use them to target offer responses.

---

## Phase 6 — Offers, Negotiation & Requirement Fulfillment Approvals ✅ (Completed & Verified)

**Depends on:** Phases 4 and 5

**Goal:** Structured offer, negotiation, and requirement fulfillment approval flow between verified farmers and commercial buyers (Backend Module 3 & ADR-003).

### Deliverables
- `Offer` and `OfferItem` models and Alembic migration `d4e5f6a1b2c3`
- `RequirementFulfillmentApproval` model (ADR-003) with composite FK `fk_approvals_order_item_composite`
- `POST /api/v1/offers` — create structured offer (multi-item, multi-requirement support)
- `GET /api/v1/offers` — list user offers with status, role, and pagination filters
- `GET /api/v1/offers/{id}` — detailed offer view with line items and participants
- `POST /api/v1/offers/{id}/counter` — counter-offer maintaining parent-child lineage
- `POST /api/v1/offers/{id}/accept` — accept offer → atomically creates order, deducts listing stock, and triggers ADR-003 fulfillment approval
- `POST /api/v1/offers/{id}/reject` — reject offer
- `POST /api/v1/offers/{id}/withdraw` — withdraw offer
- `GET /api/v1/offers/{id}/history` — retrieve chronological negotiation history chain
- `GET /api/v1/requirements/approvals` — list pending/reviewed fulfillment approvals for buyer
- `GET /api/v1/requirements/approvals/{id}` — approval detail with anti-enumeration security (404)
- `POST /api/v1/requirements/approvals/{id}/approve` — buyer approval with custom quantity and explicit closure
- `POST /api/v1/requirements/approvals/{id}/reject` — buyer rejection preserving open demand (FR-REQ-08)
- Offer state machine: `pending → countered | accepted | rejected | withdrawn`
- Approval state machine: `pending → approved | rejected | not_applied | voided`

### Acceptance Criteria & Verification Evidence
- [x] Only verified farmers and buyers can initiate or respond to offers (403 for unverified).
- [x] Strict state machine enforcement; terminal approval and offer states are immutable.
- [x] Farmer acceptance creates pending approval without premature demand deduction.
- [x] Buyer subsequent review applies exact deduction without silent quantity clamping.
- [x] Order cancellation voids pending approvals while retaining terminal audit records.
- [x] Atomic acceptance creates order, order items, and `InventoryAdjustment` audit rows.
- [x] PostgreSQL migration verified on isolated database `agridirect_module3_test` (`upgrade -> downgrade -> upgrade` to `d4e5f6a1b2c3`).
- [x] Development database `agridirect_db` remained safely untouched at revision `fcf5c991d506`.
- [x] 23 dedicated live PostgreSQL 18.6 integration & multi-connection concurrency tests passed.
- [x] 58 targeted SQLite tests and 81 combined Module 3 tests passed.
- [x] 644 full backend regression suite tests passed.
- [x] Verified zero overselling, zero duplicate deductions, and zero `40P01` deadlocks across 4 concurrent scenarios.
- [x] Resolved PostgreSQL runtime `FOR UPDATE` on eager outer joins via `with_for_update(of=Model)` and stale reads via `.populate_existing()`.
- [x] Enforced global 5-tier lock hierarchy: `Tier 1: Offer -> Tier 2: Order -> Tier 3: Listing (asc UUID) -> Tier 4: Requirement (asc UUID) -> Tier 5: Approval`. Future modules must strictly adhere to this order.

---

## Phase 7 — Orders & Inventory

**Depends on:** Phase 6

**Goal:** Order lifecycle, inventory deduction via approval workflow, delivery confirmation, and order amendments.

### Deliverables
- `Order` and `OrderAmendment` models and migrations
- Order created atomically when offer is accepted
- `GET /api/v1/orders` — list own orders
- `GET /api/v1/orders/{id}` — order detail
- `PATCH /api/v1/orders/{id}` — request amendment (creates `OrderAmendment`)
- `POST /api/v1/orders/{id}/amendments/{aid}/accept`
- `POST /api/v1/orders/{id}/amendments/{aid}/reject`
- `POST /api/v1/orders/{id}/delivery/confirm` — both sides confirm delivery
- Inventory deduction happens only after farmer explicitly confirms via approval workflow
- Order status machine: `created → confirmed → in_delivery → delivered | cancelled | disputed`

### Acceptance Criteria
- Orders are immutable once finalised; all changes go through amendments.
- Inventory is never silently deducted.
- Delivery requires confirmation from both parties.
- Cancelled/completed orders cannot be re-opened.

---

## Phase 8 — Contextual Chat

**Depends on:** Phase 6 (offers exist to attach chat context to)

**Goal:** Contextual messaging between offer/order counterparties. Unverified users cannot chat.

### Deliverables
- `ChatThread` and `ChatMessage` models and migrations
- `GET /api/v1/chat/threads` — list own threads
- `GET /api/v1/chat/threads/{id}/messages` — message history
- `POST /api/v1/chat/threads/{id}/messages` — send message
- Thread auto-created when offer is accepted (linked to order)
- Optional: WebSocket endpoint for real-time delivery

### Acceptance Criteria
- Only verified counterparties of an offer/order can chat.
- Message history is paginated and persisted.
- Unverified users receive 403.

---

## Phase 9 — Payment Records

**Depends on:** Phase 7

**Goal:** Capture payment information against orders for record-keeping only. No payment processing.

### Deliverables
- `PaymentRecord` model and migration
- `POST /api/v1/orders/{id}/payment` — record payment details (method, reference, amount)
- `GET /api/v1/orders/{id}/payment` — view payment record
- Payment details must not appear in general order list responses

### Acceptance Criteria
- Payment info is stored but never sent to a payment gateway.
- Sensitive fields are excluded from list endpoints.

---

## Phase 10 — Descriptive Market Analytics ✅ (Completed)

**Depends on:** Phases 4, 7 (real listings and orders data)

**Goal:** Aggregate descriptive statistics for farmers, buyers, and admins. No ML or forecasting.

### Deliverables
- [x] `GET /api/v1/analytics/market-summary` — unit-safe supply and completed trade summary with Version 2.5 statistical privacy controls
- [x] `GET /api/v1/analytics/demand-summary` — active buyer demands and permanent fulfillment audit retention
- [x] `GET /api/v1/analytics/my-performance` — role-specialized farmer/buyer dashboard with non-pending denominators and payment settlement
- [x] `GET /api/v1/analytics/admin/platform` & `GET /api/v1/admin/analytics/platform` — platform GMV, pipeline GMV, inventory, outcomes, velocity
- [x] All queries use clearly identified, real transaction data with read-only transaction enforcement

### Acceptance Criteria
- [x] Analytics are read-only and never modify data (enforced via `get_read_only_db` and ORM `before_flush` barrier).
- [x] All figures are traceable to source records.
- [x] ML/forecasting is explicitly absent.
- [x] Version 2.5 statistical privacy protections (diversity k>=3, dominance >=50%, coarse count bands, extrema clustering, median ownership).

---

## Module 10 — Administrative User Moderation & Platform Governance ✅ (Completed)

**Depends on:** All prior modules (users, listings, requirements, reports, audit logs)

**Goal:** Authoritative administrative capabilities for platform governance, user moderation, catalog queues, and audit logging.

### Deliverables
- [x] `GET /api/v1/admin/users` — paginated user directory with role, status, verification, date range filters, and search
- [x] `GET /api/v1/admin/users/{id}` — detailed user inspection view with profile, activity metrics, verification history, and recent audit logs
- [x] `PATCH /api/v1/admin/users/{id}/status` — account status moderation (`active`, `restricted`, `suspended`, `blocked`) with permitted transitions, self-modification prevention, and concurrency-safe last active admin protection
- [x] `GET /api/v1/admin/listings` & `POST /api/v1/admin/listings/{id}/moderate` — produce listing moderation queue and actions (`close`, `remove`, `restore`) with domain field immutability
- [x] `GET /api/v1/admin/requirements` & `POST /api/v1/admin/requirements/{id}/moderate` — buyer requirement moderation queue and actions (`close`, `remove`, `restore`) with domain field immutability
- [x] Cross-module account status enforcement: `restricted` permitted read-only profile access while blocked from mutations; `suspended` and `blocked` prohibited from authentication and operations
- [x] Atomic persistence of status changes, `AdminAuditLog` records, and in-app `Notification` alerts within a single database transaction

### Acceptance Criteria
- [x] Concurrency-safe last active administrator protection guarantees platform cannot lose administrative access under race conditions.
- [x] Zero database migrations required; leverages production PostgreSQL schema at revision `fcf5c991d506`.
- [x] All 44 Module 10 unit, integration, and PostgreSQL concurrency tests pass cleanly (866 total passing tests).

---

## Phase 11 — Notifications

**Depends on:** Phases 2–9 (events to notify about)

**Goal:** In-app notifications for key lifecycle events. Optional email notifications.

### Deliverables
- `Notification` model and migration
- Event hooks on: offer received, offer accepted/rejected, order status change, amendment requested, verification status change
- `GET /api/v1/notifications` — list own notifications (unread first)
- `POST /api/v1/notifications/{id}/read` — mark as read
- Optional: Email notification via SMTP/SendGrid (behind feature flag)

---

## Phase 12 — Frontend Implementation

**Depends on:** Phases 2–11 (stable API)

**Goal:** Implement the React/TypeScript frontend against the completed backend API.

### Sub-phases
1. Auth flows (register farmer, register buyer, login, token refresh)
2. Profile and verification submission UI
3. Listings browse + detail (public)
4. Farmer: create/manage listings
5. Buyer: post/manage requirements
6. Offer flow (create, counter, accept, reject)
7. Order management and amendments
8. Chat interface
9. Payment record UI
10. Analytics dashboard
11. Notifications

---

## Phase 13 — Hardening, Security Audit & CI/CD

**Depends on:** All prior phases

**Goal:** Production readiness — security audit, performance baseline, CI/CD pipeline, and deployment documentation.

### Deliverables
- Full security review against OWASP Top 10
- Rate limiting on auth and offer endpoints
- Structured logging (JSON, no sensitive data)
- GitHub Actions CI: lint → test → build → push image
- `docker-compose.prod.yml` with production settings
- Deployment guide in `docs/architecture/deployment.md`

---

## Phase Summary

| # | Phase | Key Dependency |
|---|---|---|
| 0 | Foundation & Documentation | — |
| 1 | Infrastructure & Config | 0 |
| 2 | Users & Authentication | 1 |
| 3 | Verification Workflow | 2 |
| 4 | Produce Listings | 3 |
| 5 | Buyer Requirements | 3 |
| 6 | Offers & Negotiation | 4, 5 |
| 7 | Orders & Inventory | 6 |
| 8 | Contextual Chat | 6 |
| 9 | Payment Records | 7 |
| 10 | Market Analytics | 4, 7 |
| 11 | Notifications | 2–9 |
| 12 | Frontend | 2–11 |
| 13 | Hardening & CI/CD | All |
