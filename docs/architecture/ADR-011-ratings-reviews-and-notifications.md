# ADR-011: Mutual Ratings & Reviews and Operational Notification Infrastructure

## 1. Context

AgriDirect facilitates B2B trade between verified agricultural producers and commercial buyers. To establish trust, accountability, and counterparty reputation in an off-platform payment and delivery ecosystem, users require bilateral feedback mechanisms following completed transactions. Furthermore, to eliminate the need for users to repeatedly poll orders, negotiation offers, payments, and messaging threads, the platform requires persistent, event-driven in-app notifications.

## 2. Decision

We implement Module 7 in two integrated components:
1. **Ratings and Reviews (`ratings_reviews`)**:
   - Strictly transaction-linked mutual feedback between buyer and farmer on eligible completed transactions (`ORDER_STATUS_COMPLETED`).
   - One review per reviewer per order (`uq_order_reviewer`).
   - Standard 1–5 integer rating scale with optional structured criteria for product quality, quantity accuracy, communication, and reliability.
   - Server-side SQL reputation aggregation.
2. **Persistent In-App Notifications (`notifications`)**:
   - In-app event store capturing domain lifecycle events across verifications, offers, orders, delivery, payments, reviews, and reports.
   - Synchronous SQLAlchemy persistence within originating business transactions.
   - Scoped retrieval, aggregate unread counts, and bulk read mutation.

## 3. Database Design

Reuses existing schema tables defined in `schema-design.md`:

### 3.1 `ratings_reviews` (Store `D15`)
- `id`: UUID Primary Key (`UUIDPrimaryKeyMixin`).
- `order_id`: UUID Foreign Key referencing `orders(id)` (`ON DELETE RESTRICT`).
- `reviewer_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE RESTRICT`).
- `reviewed_user_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE RESTRICT`).
- `overall_rating`: Integer (1 to 5, `CHECK (overall_rating BETWEEN 1 AND 5)`).
- `quality_rating`: Integer (Nullable, 1 to 5).
- `accuracy_rating`: Integer (Nullable, 1 to 5).
- `communication_rating`: Integer (Nullable, 1 to 5).
- `reliability_rating`: Integer (Nullable, 1 to 5).
- `review_text`: Text (Nullable, max length 2000).
- `created_at`: TIMESTAMPTZ.
- **Constraints & Indexes**:
  - `uq_order_reviewer`: `UNIQUE (order_id, reviewer_id)`.
  - `chk_reviewer_different`: `CHECK (reviewer_id <> reviewed_user_id)`.
  - `idx_reviews_reviewed_user`: B-tree composite index on `(reviewed_user_id, overall_rating)`.

### 3.2 `notifications` (Store `D16`)
- `id`: UUID Primary Key.
- `user_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE CASCADE`).
- `event_type`: VARCHAR(64).
- `title`: VARCHAR(128).
- `body`: TEXT.
- `reference_type`: VARCHAR(32) Nullable (`'order'`, `'offer'`, `'listing'`, `'verification'`).
- `reference_id`: UUID Nullable.
- `is_read`: BOOLEAN Default False.
- `read_at`: TIMESTAMPTZ Nullable.
- `created_at`: TIMESTAMPTZ.
- **Indexes**:
  - `idx_notifications_user_unread`: Composite index on `(user_id, is_read, created_at DESC)`.

## 4. API Design

### Ratings and Reviews (`/api/v1/reviews`)
- `POST /api/v1/reviews`: Submit review on completed order (authenticated verified participant).
- `GET /api/v1/reviews/{id}`: Retrieve single review.
- `GET /api/v1/reviews/users/{user_id}`: Paginated reviews received by a user.
- `GET /api/v1/reviews/users/{user_id}/summary`: Aggregated reputation statistics and star distribution.
- `GET /api/v1/reviews/orders/{order_id}`: Reviews associated with an order (participant or admin only).

### Notifications (`/api/v1/notifications`)
- `GET /api/v1/notifications`: List authenticated user's notifications (unread first, newest first).
- `GET /api/v1/notifications/unread-count`: Fast unread notification counter.
- `GET /api/v1/notifications/{id}`: Retrieve single notification details with ownership check.
- `POST /api/v1/notifications/{id}/read`: Mark single notification as read.
- `POST /api/v1/notifications/read-all`: Bulk mark all caller's notifications as read.

## 5. Authorization & Anti-Enumeration

- **Order Participant Enforcement**: Only active, verified users who are actual participants (`buyer_id` or `farmer_id`) in the order may submit reviews.
- **Self-Review Prevention**: A buyer cannot review themselves, nor can a farmer review themselves.
- **Anti-Enumeration**: Unrelated third parties querying `/api/v1/reviews/orders/{id}` or attempting to review an inaccessible order receive HTTP 404 rather than disclosing order existence.
- **Notification Isolation**: Users can only inspect and mutate notifications where `notification.user_id == current_user.id`. Requests for other users' notifications return HTTP 403 / 404.

## 6. Business Rules

- **BR-17 Eligibility**: Reviews are permitted strictly on completed transactions (`ORDER_STATUS_COMPLETED`). Pending, confirmed, in-delivery, or cancelled orders reject reviews with HTTP 409 Conflict.
- **Duplicate Prevention**: A reviewer may submit at most one active review per order (`uq_order_reviewer`).
- **Reputation Precision**: Aggregation uses SQL `func.avg()` and `func.count()`, rounded to 2 decimal places.

## 7. Transaction Boundaries & Concurrency

- Review submission and notification dispatch occur in the same transactional unit. If database commit fails, no orphan review or false notification persists.
- PostgreSQL unique constraint `uq_order_reviewer` provides database-enforced concurrency protection against race conditions during simultaneous submission attempts.

## 8. Alternatives Rejected

- **Public Unrestricted Reviews**: Rejected. Anonymous or non-transactional reviews open marketplace manipulation and defamation vectors.
- **Asynchronous Message Broker (Redis/Celery/RabbitMQ)**: Rejected. AgriDirect uses a synchronous modular monolith. Background message broker infrastructure introduces unnecessary operational complexity.

## 9. Testing Strategy

- Unit and API tests in `test_reviews_api.py` and `test_notifications_api.py`.
- Real PostgreSQL 18.6 concurrency and check-constraint suite in `test_postgres_module7.py`.

