# ADR-012: User Reports, Safety Moderation, and Administrative Audit Trail

## 1. Context

In a direct B2B agricultural marketplace where participants negotiate high-value produce batches and coordinate deliveries off-platform, mechanisms for reporting violations, fraud, quality discrepancies, or conduct issues are critical. Furthermore, all privileged administrative actions (such as moderating user reports, reviewing verification documents, suspending accounts, or mediating payment disputes) must be permanently auditable to maintain institutional integrity.

## 2. Decision

We implement Module 8 across two core capabilities:
1. **User Reporting & Safety Moderation (`user_reports`)**:
   - Authenticated reporting workflow for buyers and farmers to flag misconduct, fraud, quality issues, or payment concerns against users or produce listings.
   - Formal moderation lifecycle: `open` -> `under_review` -> `action_taken` / `dismissed`.
   - Strict confidentiality protection preventing reported parties or third parties from viewing reports or discovering reporter identities.
2. **Administrative Audit Trail (`admin_audit_logs`)**:
   - Reuses existing `AdminAuditLog` model to provide an immutable, append-only ledger of privileged administrative interventions.
   - Transactionally coupled with sensitive operations (report resolution, payment dispute moderation, verification decisions).
   - Read-only querying for administrators with filters for administrator ID, action, target entity type, and target ID.
   - Strictly no creation, modification, or deletion endpoints exposed via API.

## 3. Database Design

Reuses existing schema tables defined in `schema-design.md`:

### 3.1 `user_reports` (Store `D17`)
- `id`: UUID Primary Key.
- `reporter_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE RESTRICT`).
- `reported_user_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE SET NULL`, Nullable).
- `listing_id`: UUID Foreign Key referencing `produce_listings(id)` (`ON DELETE SET NULL`, Nullable).
- `category`: VARCHAR(32) (`CHECK (category IN ('payment', 'quantity_mismatch', 'quality_issue', 'fraud', 'harassment', 'other'))`).
- `description`: TEXT (5 to 2000 chars).
- `status`: VARCHAR(32) (`CHECK (status IN ('open', 'under_review', 'action_taken', 'dismissed')) DEFAULT 'open'`).
- `admin_notes`: TEXT (Nullable).
- `reviewed_by_admin_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE SET NULL`, Nullable).
- `created_at`: TIMESTAMPTZ.
- `updated_at`: TIMESTAMPTZ.
- **Indexes**:
  - `idx_user_reports_status`: Composite index on `(status, created_at DESC)`.

### 3.2 `admin_audit_logs` (Audit Store of `D17`)
- `id`: UUID Primary Key.
- `admin_user_id`: UUID Foreign Key referencing `users(id)` (`ON DELETE RESTRICT`).
- `action`: VARCHAR(64).
- `target_entity_type`: VARCHAR(32).
- `target_entity_id`: UUID.
- `reason`: TEXT (Nullable).
- `ip_address`: VARCHAR(45) (Nullable).
- `created_at`: TIMESTAMPTZ.
- **Indexes**:
  - `idx_audit_logs_admin`: B-Tree index on `admin_user_id`.
  - `idx_audit_logs_target`: Composite index on `(target_entity_type, target_entity_id)`.

## 4. API Design

### User Reports (`/api/v1/reports`)
- `POST /api/v1/reports`: Submit complaint against user or listing (authenticated user).
- `GET /api/v1/reports/me`: List reports filed by the authenticated caller.
- `GET /api/v1/reports/{id}`: Detailed view of a report (accessible only to original reporter and administrators).

### Administrative Moderation (`/api/v1/admin/reports`)
- `GET /api/v1/admin/reports`: Paginated moderation queue with status and category filters.
- `GET /api/v1/admin/reports/{id}`: Full administrative inspection of report evidence and targets.
- `POST /api/v1/admin/reports/{id}/moderate`: Update report status to `under_review`, `action_taken`, or `dismissed` with mandatory administrative findings.

### Administrative Audit Trail (`/api/v1/admin/audit-logs`)
- `GET /api/v1/admin/audit-logs`: Paginated audit log search with filters for actor, action, target entity type, and target ID.
- `GET /api/v1/admin/audit-logs/{id}`: Detail view of single audit record.

## 5. Security & Confidentiality

- **Confidentiality Protection**: The reported party is strictly barred from viewing reports filed against them. Any attempt by a reported user or third party to query `/api/v1/reports/{id}` yields HTTP 404 Not Found to prevent enumeration or retaliation.
- **Self-Reporting Guard**: A user cannot file a report naming themselves as the target.
- **Append-Only Immutability**: No HTTP routes exist for `POST`, `PUT`, `PATCH`, or `DELETE` on `/api/v1/admin/audit-logs`. Audit records can only be created via trusted backend service operations.
- **Sensitive Data Exclusion**: Audit logs never capture credentials, passwords, JWT tokens, bank details, or payload secrets.

## 6. Transaction Boundaries & Atomicity

Administrative moderation actions and `AdminAuditLog` insertion occur within the same database transaction:
```python
# Report status update + AdminAuditLog insertion + Notification dispatch
report.status = moderate_in.status
report.admin_notes = moderate_in.admin_notes
db.add(AdminAuditLog(...))
notification_service.create_notification(...)
db.commit()
```
If an exception occurs or the transaction rolls back, neither the report status update nor the audit log is persisted.

## 7. Testing Strategy

- Unit and API tests in `test_reports_and_audit_api.py`.
- Real PostgreSQL 18.6 check-constraint and atomicity test suite in `test_postgres_module8.py`.

