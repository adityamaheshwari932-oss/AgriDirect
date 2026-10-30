# ADR-003: Requirement Fulfillment Approval Workflow

**Status:** Accepted & Verified (Implemented via Migration d4e5f6a1b2c3; Step 2 PostgreSQL Concurrency Verified)  
**Date:** 2026-10-30  

---

## 1. Context

In the AgriDirect marketplace, trade is initiated either from farmer produce listings (Catalog-Driven) or from commercial buyer procurement postings (Requirement-Driven).

When negotiations occur against a **Buyer Requirement** (SRS FR-REQ-01 through FR-REQ-08), a critical business tension exists regarding when, how, and by whom a buyer requirement's remaining open quantity (`remaining_quantity`) is decremented, and when the requirement is marked closed.

### 1.1 The 5 Distinct Commercial & Fulfillment Events

AgriDirect strictly distinguishes five separate, sequential commercial, legal, and operational lifecycle events:

1. **Commercial Offer Acceptance (Mutual Agreement):**
   - The buyer and farmer reach mutual agreement on counterparties, produce specifications, quantities, prices, and delivery windows.
   - Transitions the negotiation offer status to `accepted` (FR-OFF-08).

2. **Order Creation (Contractual Instantiation):**
   - Atomically generates an immutable `Order` and associated `OrderItem` records (BR-09).
   - Agreed terms and prices are permanently snapshotted into the order.
   - For farmer listings referenced in the offer, physical inventory is immediately deducted (`available_quantity -= order_quantity`) to prevent double-selling (BR-01, BR-02).

3. **Requirement Fulfillment Approval (Buyer Procurement Accounting):**
   - A buyer requirement represents an open commercial tender published by a buyer (e.g., *"Seeking 5,000 kg Grade-A Hass Avocados by Nov 15"*).
   - Adjusting the tender's remaining quantity (`remaining_quantity`) and deciding whether to close or keep open the tender is an **internal administrative decision belonging exclusively to the buyer organization** (FR-REQ-06, FR-REQ-07, BR-07).
   - A farmer accepting an offer has legal authority to sell produce and commit inventory, but **zero administrative authority** over the buyer's procurement tender.

4. **Physical Delivery & Order Fulfillment (Logistical Quality Inspection):**
   - Logistics transit occurs; produce is delivered to the buyer's intake facility.
   - Line items progress from `confirmed` $\rightarrow$ `shipped` $\rightarrow$ `delivered` $\rightarrow$ `fulfilled` (or `rejected` on quality inspection failure).
   - This physical fulfillment is distinct from the buyer requirement's open tender accounting.

5. **Payment Acknowledgement (Invoice & Settlement Record):**
   - Counterparties record external payment and invoice settlement. AgriDirect does not process or hold payments.

### 1.2 Conflation Risks and Business Rules

Conflating Order Creation (Event 2) with Requirement Fulfillment (Event 3) creates severe system failures:
- **Violation of Buyer Sovereignty (BR-07):** A farmer acceptance would unilaterally alter a buyer's procurement posting.
- **Tender Mismanagement:** If a buyer negotiates with multiple farmers to mitigate supply risk, an acceptance by Farmer A must not silently curtail the buyer's open market posting without buyer approval.
- **Audit Void:** Requirement quantities changing implicitly without an auditable record makes reconciliation impossible.
- **Premature Tender Closure:** Automatically closing a requirement because a single order matched the quantity removes buyer discretion to keep the tender open for secondary suppliers or safety stock.

---

## 2. Decision & Core Principles

We introduce a first-class **Requirement Fulfillment Approval** entity (`requirement_fulfillment_approvals`), an atomic transaction-safe approval service, and dedicated buyer REST API endpoints under `/api/v1/requirements/fulfillment-approvals`.

### 2.1 Core Architectural Principles

1. **Strict Buyer Control of Requirement Status (Elimination of Automatic Closure):**
   - The system **never automatically closes** a buyer requirement merely because `remaining_quantity` reaches zero.
   - In accordance with the canonical requirement statuses (`draft`, `active`, `partially_fulfilled`, `closed`, `expired` defined in [`backend/app/models/requirement.py`](file:///c:/Users/WINDOWS%2011/AgriDirect/backend/app/models/requirement.py#L36-L48)):
     - When `remaining_quantity == required_quantity`, status is `active`.
     - When `0 <= remaining_quantity < required_quantity` and not closed, status is `partially_fulfilled` (even when remaining quantity reaches `0.000`).
     - A requirement transitions to `closed` **only when explicitly instructed by the buyer** (via `close_requirement: bool = true` on acceptance/approval, or through the dedicated requirement close endpoint).
2. **Partial Fulfillment Approval:**
   - Buyers can approve an `approved_quantity` that is smaller than the order line item's `proposed_quantity` without altering the commercial order.
   - The commercial order remains intact at the agreed quantity (e.g. 70 kg), while the requirement's open demand is reduced by the buyer-approved quantity (e.g. 50 kg).
3. **Strict No-Clamping Invariant:**
   - If an approved quantity exceeds the current remaining requirement quantity, the system **never silently clamps** to zero. It returns an explicit `409 Conflict`.
4. **Audit Preservation via Strict Foreign Keys:**
   - Physical deletion is blocked via `ON DELETE RESTRICT` on all relationships (`requirement_id`, `order_id`, `order_item_id`, `reviewed_by_user_id`, `voided_by_user_id`). AgriDirect utilizes soft-deletion and status archiving.

---

## 3. Workflow Scenarios and Request Contracts

### 3.1 Scenario 1: Immediate Buyer Offer Acceptance Contract

When a buyer accepts an offer from a farmer, the negotiation may contain one or more items referencing buyer requirements. The acceptance contract allows the buyer to decide fulfillment immediately.

#### Request Endpoint & Contract
`POST /api/v1/offers/{offer_id}/accept`

```python
class ItemFulfillmentDecision(BaseModel):
    offer_item_id: UUID = Field(
        description="ID of the specific offer item linked to a buyer requirement."
    )
    apply_to_requirement: bool = Field(
        default=True,
        description="Whether to apply this item's quantity toward requirement fulfillment."
    )
    approved_quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        decimal_places=3,
        description="Quantity to deduct. If omitted and apply_to_requirement=True, defaults to the full proposed offer item quantity."
    )
    close_requirement: bool = Field(
        default=False,
        description="Explicitly mark the linked requirement as 'closed'. Never auto-closed."
    )

class OfferAcceptRequest(BaseModel):
    apply_to_requirement: bool = Field(
        default=True,
        description="Default fulfillment action for requirement-linked items if item_fulfillments is omitted."
    )
    approved_quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        decimal_places=3,
        description="Default approved quantity if item_fulfillments is omitted (defaults to full item quantity)."
    )
    close_requirement: bool = Field(
        default=False,
        description="Default close flag if item_fulfillments is omitted."
    )
    item_fulfillments: Optional[List[ItemFulfillmentDecision]] = Field(
        default=None,
        description="Optional granular per-item fulfillment decisions for multi-item offers."
    )
```

#### Acceptance Processing Rules
1. **Quantity Validation:**
   - For each requirement-linked item where `apply_to_requirement == True`:
     $$\text{effective\_qty} = \text{decision.approved\_quantity} \lor \text{item.quantity}$$
     $$0 < \text{effective\_qty} \le \min(\text{item.quantity}, \text{requirement.remaining\_quantity})$$
   - If $\text{effective\_qty} > \text{requirement.remaining\_quantity}$:
     - Transaction rolls back immediately and raises `HTTPException(409, detail="Approved quantity exceeds current remaining requirement quantity. No quantity clamped.")`.
2. **Atomic Execution:**
   - Order is created atomically (`Order` and `OrderItem` records instantiated).
   - Farmer listing inventory is deducted immediately (`BR-01`, `BR-09`).
   - If `apply_to_requirement == True`:
     - Decrement requirement: `requirement.remaining_quantity -= effective_qty`.
     - Update status: If `close_requirement == True`: `requirement.status = 'closed'`. Else if `requirement.status == 'active'`: `requirement.status = 'partially_fulfilled'`.
     - Create `requirement_fulfillment_approvals` record with:
       - `status = 'approved'`
       - `proposed_quantity = item.quantity`
       - `approved_quantity = effective_qty`
       - `reviewed_by_user_id = buyer.id`
       - `reviewed_at = clock_timestamp()`
   - If `apply_to_requirement == False`:
     - Requirement `remaining_quantity` and `status` remain completely untouched.
     - Create `requirement_fulfillment_approvals` record with:
       - `status = 'not_applied'`
       - `proposed_quantity = item.quantity`
       - `approved_quantity = NULL`
       - `reviewed_by_user_id = buyer.id`
       - `reviewed_at = clock_timestamp()`
     - **No pending approval record is created.**

---

### 3.2 Multi-Item Offer Acceptance Atomicity & Rollback Guarantee

An offer may contain multiple items ($N \ge 2$) referencing different buyer requirements, different farmer listings, or a combination.

#### The All-or-Nothing Transactional Boundary
Offer acceptance is executed as **one single atomic database transaction** covering:
1. `Order` record creation.
2. `OrderItem` records creation for all line items.
3. Farmer listing inventory deductions and append-only `InventoryAdjustment` records (`BR-01`, `BR-02`, `BR-09`).
4. `RequirementFulfillmentApproval` records creation for all requirement-linked items.
5. Buyer requirement `remaining_quantity` decrements and status updates for approved fulfillments.
6. `Offer` state transition to `accepted` (`FR-OFF-08`).

#### Strict Failure Rule
- If **any** item fails validation (e.g. Item 1 has valid quantities, but Item 2 requests an approved quantity exceeding Requirement 2's remaining demand):
- If **any** inventory deduction fails (e.g. insufficient available quantity on a listing):
- If **any** database constraint fails:
- **The ENTIRE transaction rolls back immediately (`db.rollback()`).**
- **No partial order acceptance, partial inventory deduction, or partial requirement fulfillment is permitted.**
- The offer remains in `pending` status.
- Zero database rows are altered or committed.

#### Intentional Partial Acceptance Clarification
AgriDirect commercial negotiations treat an Offer as an indivisible commercial instrument. Accepting a subset of items while dropping others is **not supported** in the current business design (any item alteration requires a counter-offer). Supporting intentional partial acceptance would constitute a major new business workflow and is not assumed.

#### External Side-Effects Rule
Notifications (in-app alerts, emails, push notices) and external webhooks **never execute inside the transaction block**. They are staged in a post-commit task buffer and dispatched **only after `db.commit()` successfully executes**.

---

### 3.3 Scenario 2: Farmer Accepts Buyer's Offer

1. Farmer calls `POST /api/v1/offers/{offer_id}/accept`.
2. Order is created atomically; farmer listing inventory is decremented immediately (`BR-09`).
3. Buyer requirement `remaining_quantity` and `status` are **not modified** (`BR-07`, `FR-REQ-06`).
4. System automatically creates a `requirement_fulfillment_approvals` record:
   - `status = 'pending'`
   - `proposed_quantity = order_item.quantity`
   - `approved_quantity = NULL`
   - `reviewed_by_user_id = NULL`
   - `reviewed_at = NULL`
   - `rejection_reason = NULL`
   - `voided_by_user_id = NULL`
   - `voided_at = NULL`
   - `void_reason = NULL`
5. Buyer receives in-app/email notification to review the pending fulfillment deduction.

---

### 3.4 Scenario 3: Subsequent Buyer Fulfillment Approval (Partial / Full)

#### Request Endpoint & Contract
`POST /api/v1/requirements/fulfillment-approvals/{id}/approve`

```python
class ApproveFulfillmentRequest(BaseModel):
    approved_quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        decimal_places=3,
        description="Quantity to deduct from requirement. If omitted, defaults to proposed_quantity."
    )
    close_requirement: bool = Field(
        default=False,
        description="Explicitly mark requirement as 'closed'. Never auto-closed on zero remaining."
    )
```

#### Processing Rules
1. Locks acquired per the Global Lock Hierarchy (Section 6): **`BuyerRequirement` row FIRST (Tier 4), then `RequirementFulfillmentApproval` row (Tier 5)**.
2. Verify ownership: `requirement.buyer_id == current_user.id` (returns `404 Not Found` if mismatched to prevent resource enumeration).
3. Verify state: `approval.status == 'pending'` (returns `409 Conflict` if already reviewed).
4. Verify requirement status: Must be `active` or `partially_fulfilled` (returns `409 Conflict` if `closed` or `expired`).
5. Validate quantity:
   $$\text{effective\_qty} = \text{approved\_quantity} \lor \text{approval.proposed\_quantity}$$
   $$0 < \text{effective\_qty} \le \min(\text{approval.proposed\_quantity}, \text{requirement.remaining\_quantity})$$
   - If $\text{effective\_qty} > \text{requirement.remaining\_quantity}$:
     - Return `409 Conflict` (*"Approved quantity ({effective_qty}) exceeds current remaining requirement quantity ({remaining_quantity}). Approval remains pending."*).
     - **No silent quantity clamping.**
6. Atomic Update:
   - `requirement.remaining_quantity -= effective_qty`
   - If `close_requirement == True`: `requirement.status = 'closed'`
   - Else if `requirement.status == 'active'`: `requirement.status = 'partially_fulfilled'`
   - `approval.status = 'approved'`
   - `approval.approved_quantity = effective_qty`
   - `approval.reviewed_by_user_id = current_user.id`
   - `approval.reviewed_at = clock_timestamp()`
7. Commercial order quantity remains unchanged at `proposed_quantity`.
8. Post-commit notification sent to farmer.

---

### 3.5 Scenario 4: Subsequent Buyer Rejection

#### Request Endpoint & Contract
`POST /api/v1/requirements/fulfillment-approvals/{id}/reject`

```python
class RejectFulfillmentRequest(BaseModel):
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for rejecting the fulfillment deduction."
    )
```

#### Processing Rules
1. Locks acquired per Global Lock Hierarchy: **`BuyerRequirement` row (Tier 4), then `RequirementFulfillmentApproval` row (Tier 5)**.
2. Verify ownership: `requirement.buyer_id == current_user.id` (returns `404 Not Found` if mismatched).
3. Verify state: `approval.status == 'pending'` (returns `409 Conflict` if already reviewed).
4. Atomic Update:
   - `approval.status = 'rejected'`
   - `approval.approved_quantity = NULL`
   - `approval.rejection_reason = reason`
   - `approval.reviewed_by_user_id = current_user.id`
   - `approval.reviewed_at = clock_timestamp()`
5. Requirement `remaining_quantity` and `status` remain **completely untouched**, preserving open market demand (`FR-REQ-08`).
6. Commercial order and farmer inventory deduction remain valid and unchanged.

---

## 4. Approval States and Invariant Audit Rules

### 4.1 State Definitions

| State | Category | Meaning | Initiator |
|---|---|---|---|
| `pending` | Transient | Waiting for buyer review. Initial state when farmer accepts offer. | System (on farmer acceptance) |
| `approved` | Terminal | Buyer reviewed and approved deducting `approved_quantity` from the requirement. | Buyer |
| `rejected` | Terminal | Buyer reviewed and deliberately rejected deducting this order from the requirement. Requirement demand preserved. | Buyer |
| `not_applied` | Terminal | Buyer explicitly decided at offer acceptance not to apply fulfillment to this requirement. | Buyer |
| `voided` | Terminal | Approval rendered moot/invalid before buyer review because the parent order was cancelled or rescinded. | System / Buyer / Admin |

### 4.2 Complete Status-to-Column Invariant Table

| Column | `pending` | `approved` | `rejected` | `not_applied` | `voided` (System Action) | `voided` (User Action) |
|---|---|---|---|---|---|---|
| `status` | `'pending'` | `'approved'` | `'rejected'` | `'not_applied'` | `'voided'` | `'voided'` |
| `approved_quantity` | **NULL** | **NOT NULL**<br>($0 < q \le \text{proposed}$) | **NULL** | **NULL** | **NULL** | **NULL** |
| `reviewed_by_user_id` | **NULL** | **NOT NULL** (buyer UUID) | **NOT NULL** (buyer UUID) | **NOT NULL** (buyer UUID) | **NULL** | **NULL** |
| `reviewed_at` | **NULL** | **NOT NULL** (timestamptz) | **NOT NULL** (timestamptz) | **NOT NULL** (timestamptz) | **NULL** | **NULL** |
| `rejection_reason` | **NULL** | **NULL** | **OPTIONAL** ($\le 500$ chars) | **NULL** | **NULL** | **NULL** |
| `voided_by_user_id` | **NULL** | **NULL** | **NULL** | **NULL** | **NULL** (Indicates System) | **NOT NULL** (Actor UUID) |
| `voided_at` | **NULL** | **NULL** | **NULL** | **NULL** | **NOT NULL** (timestamptz) | **NOT NULL** (timestamptz) |
| `void_reason` | **NULL** | **NULL** | **NULL** | **NULL** | **NOT NULL** ($\le 500$ chars) | **NOT NULL** ($\le 500$ chars) |

#### Representation of System vs. User Voiding
- When voiding is triggered automatically by the system (e.g. parent order cancelled via timeout or system reconciliation hook):
  - `voided_by_user_id` is strictly **`NULL`**. No synthetic or dummy user UUID is invented.
  - `voided_at` records the exact clock timestamp.
  - `void_reason` records the system trigger (e.g. `"System [Order Cancellation Hook]: Order #O102 cancelled due to payment window expiration"`).
- When voiding is triggered by a human user (e.g. buyer or platform administrator cancelling an order):
  - `voided_by_user_id` records the foreign key to `users.id`.
  - `voided_at` records the timestamp.
  - `void_reason` records the human justification.

---

## 5. Database Schema & Integrity Constraints

### 5.1 SQL DDL Definition

```sql
CREATE TABLE requirement_fulfillment_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES buyer_requirements(id) ON DELETE RESTRICT,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    order_item_id UUID NOT NULL UNIQUE REFERENCES order_items(id) ON DELETE RESTRICT,
    proposed_quantity NUMERIC(12, 3) NOT NULL CHECK (proposed_quantity > 0),
    approved_quantity NUMERIC(12, 3) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'approved', 'rejected', 'not_applied', 'voided')),
    
    -- Buyer review audit fields (for approved, rejected, not_applied)
    reviewed_by_user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT,
    reviewed_at TIMESTAMPTZ NULL,
    rejection_reason VARCHAR(500) NULL,

    -- Voiding audit fields (for voided status)
    voided_by_user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT,
    voided_at TIMESTAMPTZ NULL,
    void_reason VARCHAR(500) NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    -- Exhaustive Invariant Enforcement across all 5 states
    CONSTRAINT chk_approval_complete_invariants CHECK (
        -- 1. PENDING: No review, no rejection, no void, no approved quantity
        (
            status = 'pending'
            AND approved_quantity IS NULL
            AND reviewed_by_user_id IS NULL
            AND reviewed_at IS NULL
            AND rejection_reason IS NULL
            AND voided_by_user_id IS NULL
            AND voided_at IS NULL
            AND void_reason IS NULL
        )
        OR
        -- 2. APPROVED: approved_quantity positive and <= proposed_quantity, review audit mandatory, rejection and void fields NULL
        (
            status = 'approved'
            AND approved_quantity IS NOT NULL
            AND approved_quantity > 0
            AND approved_quantity <= proposed_quantity
            AND reviewed_by_user_id IS NOT NULL
            AND reviewed_at IS NOT NULL
            AND rejection_reason IS NULL
            AND voided_by_user_id IS NULL
            AND voided_at IS NULL
            AND void_reason IS NULL
        )
        OR
        -- 3. REJECTED: approved_quantity NULL, review audit mandatory, rejection_reason allowed, void fields NULL
        (
            status = 'rejected'
            AND approved_quantity IS NULL
            AND reviewed_by_user_id IS NOT NULL
            AND reviewed_at IS NOT NULL
            AND voided_by_user_id IS NULL
            AND voided_at IS NULL
            AND void_reason IS NULL
        )
        OR
        -- 4. NOT_APPLIED: approved_quantity NULL, review audit mandatory, rejection_reason NULL, void fields NULL
        (
            status = 'not_applied'
            AND approved_quantity IS NULL
            AND reviewed_by_user_id IS NOT NULL
            AND reviewed_at IS NOT NULL
            AND rejection_reason IS NULL
            AND voided_by_user_id IS NULL
            AND voided_at IS NULL
            AND void_reason IS NULL
        )
        OR
        -- 5. VOIDED: approved_quantity NULL, review audit NULL, rejection_reason NULL, voided_at and void_reason mandatory; voided_by_user_id optional (NULL for system, populated for user)
        (
            status = 'voided'
            AND approved_quantity IS NULL
            AND reviewed_by_user_id IS NULL
            AND reviewed_at IS NULL
            AND rejection_reason IS NULL
            AND voided_at IS NOT NULL
            AND void_reason IS NOT NULL
        )
    )
);

-- Indexes
CREATE INDEX idx_req_approvals_requirement_status 
    ON requirement_fulfillment_approvals (requirement_id, status);

CREATE INDEX idx_req_approvals_buyer_pending 
    ON requirement_fulfillment_approvals (requirement_id) 
    WHERE status = 'pending';

CREATE INDEX idx_req_approvals_order 
    ON requirement_fulfillment_approvals (order_id);

CREATE INDEX idx_req_approvals_reviewed_by 
    ON requirement_fulfillment_approvals (reviewed_by_user_id) 
    WHERE reviewed_by_user_id IS NOT NULL;
```

---

### 5.2 Verification of Existing `order_items` Schema & Cross-Table Integrity Strategy

#### Inspection Findings of the Existing Repository
Inspection of [`backend/app/models/order.py`](file:///c:/Users/WINDOWS%2011/AgriDirect/backend/app/models/order.py#L307-L400) and [`backend/alembic/versions/d4e5f6a1b2c3_add_buyer_requirement_id_to_offer_items_and_order_items.py`](file:///c:/Users/WINDOWS%2011/AgriDirect/backend/alembic/versions/d4e5f6a1b2c3_add_buyer_requirement_id_to_offer_items_and_order_items.py#L41-L58) reveals:
1. `order_items` has a primary key on `id` (UUID).
2. Migration `d4e5f6a1b2c3` adds a nullable column `buyer_requirement_id UUID NULL` with a standard foreign key `fk_order_items_buyer_requirement_id` and a non-unique index `idx_order_items_requirement`.
3. **There is currently NO unique constraint on `(id, order_id, buyer_requirement_id)` in the existing schema or migration.**

#### PostgreSQL Enforcement Rules for Composite Foreign Keys
PostgreSQL explicitly requires that any referenced column list in a `FOREIGN KEY (a, b, c) REFERENCES table (x, y, z)` must match a `PRIMARY KEY` or `UNIQUE` constraint on `(x, y, z)` in the referenced table. Without such a constraint, PostgreSQL raises error code `42830` (`invalid_foreign_key: there is no unique constraint matching given keys for referenced table`).

Furthermore, in `order_items`, `buyer_requirement_id` is nullable (catalog listing orders have `buyer_requirement_id IS NULL`).

#### Corrected Database-Level Integrity Strategy
To make the composite foreign key enforceable at the database engine level, the migration and models must execute in strict topological order:

1. **Step 1: Model-Level Unique Constraint (`backend/app/models/order.py`):**
   Add to `OrderItem.__table_args__`:
   ```python
   UniqueConstraint(
       "id", "order_id", "buyer_requirement_id",
       name="uq_order_items_identity_requirement"
   )
   ```
2. **Step 2: Migration Execution Order:**
   In the Alembic migration script:
   - **Phase 2A (alter `order_items`):**
     1. Add column `buyer_requirement_id UUID NULL` with foreign key `fk_order_items_buyer_requirement_id` to `buyer_requirements(id) ON DELETE SET NULL`.
     2. Create the unique constraint:
        ```python
        batch_op.create_unique_constraint(
            'uq_order_items_identity_requirement',
            ['id', 'order_id', 'buyer_requirement_id']
        )
        ```
   - **Phase 2B (create `requirement_fulfillment_approvals`):**
     1. Create table `requirement_fulfillment_approvals` with `requirement_id UUID NOT NULL`, `order_id UUID NOT NULL`, `order_item_id UUID NOT NULL UNIQUE`.
     2. Create the composite foreign key:
        ```python
        batch_op.create_foreign_key(
            'fk_approvals_order_item_composite',
            'order_items',
            ['order_item_id', 'order_id', 'requirement_id'],
            ['id', 'order_id', 'buyer_requirement_id'],
            ondelete='RESTRICT'
        )
        ```
   *Crucial Rule:* The composite FK cannot be created until the referenced unique constraint `uq_order_items_identity_requirement` is established on `order_items`.

3. **Behavior of Existing `buyer_requirement_id ON DELETE SET NULL` vs. Composite FK:**
   - In `order_items`, `buyer_requirement_id` was originally specified with `ON DELETE SET NULL`.
   - However, when an approval record exists referencing an order item:
     - `requirement_fulfillment_approvals.requirement_id` has `ON DELETE RESTRICT` directly referencing `buyer_requirements(id)`.
     - Therefore, if any SQL client attempts `DELETE FROM buyer_requirements WHERE id = :id`, PostgreSQL checks `requirement_fulfillment_approvals.requirement_id` and **blocks the deletion immediately with error 23503 (`foreign_key_violation`)**.
     - The `ON DELETE SET NULL` cascade on `order_items` is never executed because the parent requirement deletion is completely blocked by `RESTRICT` on the approval table!
   - What if someone attempts `UPDATE order_items SET buyer_requirement_id = NULL`?
     - If an approval record exists, the composite foreign key `(order_item_id, order_id, requirement_id)` requires the matching row in `order_items` to have `buyer_requirement_id == requirement_id`.
     - Updating `order_items.buyer_requirement_id` to `NULL` would violate the composite foreign key constraint, and PostgreSQL **immediately aborts the update with error 23503**.
   - **Prevention of NULL `buyer_requirement_id` References:**
     - Because `requirement_id` in `requirement_fulfillment_approvals` is `NOT NULL`, attempting to create an approval referencing an order item where `buyer_requirement_id IS NULL` fails the composite foreign key match (non-null value cannot match `NULL`). PostgreSQL rejects the insert with error `23503`.

#### Defense-in-Depth & Error Handling Standards
Rather than allowing an unhandled Python `ValueError` or `AssertionError` to crash into an unhandled HTTP 500 error, service-layer relationship validation uses AgriDirect's established FastAPI exception mechanism:
```python
if order_item.buyer_requirement_id is None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Cannot create fulfillment approval for order item without buyer_requirement_id",
    )
if order_item.buyer_requirement_id != approval_requirement_id:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Requirement ID mismatch between order item and approval request",
    )
if order_item.order_id != approval_order_id:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Order ID mismatch between order item and approval request",
    )
```

---

### 5.3 Foreign-Key Deletion Policies & Audit Preservation

| Foreign Key | Policy | Technical Justification |
|---|---|---|
| `requirement_id` | `ON DELETE RESTRICT` | Prevents hard-deletion of a buyer requirement while procurement audit records reference it. Requirements utilize soft-deletion (`deleted_at`). |
| `order_id` | `ON DELETE RESTRICT` | Prevents hard-deletion of the legal commercial contract. |
| `order_item_id` | `ON DELETE RESTRICT` | Prevents hard-deletion of contracted line items. `ON DELETE CASCADE` is strictly prohibited. |
| `reviewed_by_user_id` | `ON DELETE RESTRICT` | Retains permanent accountability for user approval/rejection decisions. Users utilize soft-deletion (`is_deleted = true`). |
| `voided_by_user_id` | `ON DELETE RESTRICT` | Retains permanent accountability for human cancellation/voiding actions. |

---

## 6. Global Lock Hierarchy & Concurrency Resilience

### 6.1 The 5-Tier Monotonic Lock Hierarchy

Multiple concurrent workflows mutate `offers`, `orders`, `produce_listings`, `buyer_requirements`, and `requirement_fulfillment_approvals`. To prevent deadlocks, all database transactions modifying these entities MUST acquire row-level locks strictly following the **5-Tier Monotonic Lock Hierarchy**:

```
[Tier 1: Offer] ──> [Tier 2: Order] ──> [Tier 3: ProduceListing] ──> [Tier 4: BuyerRequirement] ──> [Tier 5: FulfillmentApproval]
```

| Tier | Entity / Table | Order Within Tier | Mutating Workflows Involved |
|---|---|---|---|
| **Tier 1** | `Offer` (`offers`) | Single Row | Offer acceptance, counter-offer, rejection, withdrawal |
| **Tier 2** | `Order` (`orders`) | Single Row | Order confirmation, cancellation, amendment, delivery marking |
| **Tier 3** | `ProduceListing` (`produce_listings`) | Ascending UUID (`id.asc()`) | Offer creation/acceptance, inventory deduction, listing editing |
| **Tier 4** | `BuyerRequirement` (`buyer_requirements`) | Ascending UUID (`id.asc()`) | Offer acceptance, approval, rejection, manual requirement edit/close |
| **Tier 5** | `RequirementFulfillmentApproval` (`requirement_fulfillment_approvals`) | Ascending UUID (`id.asc()`) | Offer acceptance (insert), approval/rejection (update), cancellation (void) |

### 6.2 Lock Acquisition Sequence by Workflow

Every workflow acquires locks strictly top-to-bottom according to this hierarchy:

1. **Immediate Offer Acceptance (`POST /api/v1/offers/{id}/accept`):**
   - Step 1: Lock existing `Offer` row (Tier 1).
   - Step 2: Lock existing `ProduceListing` rows in `id.asc()` (Tier 3).
   - Step 3: Lock existing `BuyerRequirement` rows in `id.asc()` (Tier 4).
   - Step 4: Insert new `Order` and `OrderItem` rows (Tier 2 entity instantiation).
   - Step 5: Insert new `RequirementFulfillmentApproval` rows (Tier 5 entity instantiation).
   - *Hierarchy Rule:* Monotonic row-lock acquisition progression on existing records: Tier 1 $\rightarrow$ Tier 3 $\rightarrow$ Tier 4. Newly inserted rows (Tier 2 and Tier 5) carry fresh UUIDs and are held exclusively by the inserting transaction until commit, introducing zero lock inversion or deadlock hazard. `Order` is designated as Tier 2 in the system-wide hierarchy because order-centric workflows operating on existing orders (such as Module 4's order cancellation or amendments) must lock `Order` (Tier 2) prior to accessing downstream listings (Tier 3) or requirements (Tier 4).
2. **Subsequent Fulfillment Approval (`POST /requirements/fulfillment-approvals/{id}/approve`):**
   - Step 1: Lock `BuyerRequirement` row (Tier 4):
     `SELECT r.* FROM buyer_requirements r JOIN requirement_fulfillment_approvals a ON a.requirement_id = r.id WHERE a.id = :approval_id FOR UPDATE OF r;`
   - Step 2: Lock `RequirementFulfillmentApproval` row (Tier 5):
     `SELECT * FROM requirement_fulfillment_approvals WHERE id = :approval_id FOR UPDATE;`
   - *Hierarchy Rule:* Monotonic progression: Tier 4 $\rightarrow$ Tier 5.
3. **Subsequent Fulfillment Rejection (`POST /requirements/fulfillment-approvals/{id}/reject`):**
   - Step 1: Lock `BuyerRequirement` row (Tier 4):
     `SELECT r.* FROM buyer_requirements r JOIN requirement_fulfillment_approvals a ON a.requirement_id = r.id WHERE a.id = :approval_id FOR UPDATE OF r;`
   - Step 2: Lock `RequirementFulfillmentApproval` row (Tier 5):
     `SELECT * FROM requirement_fulfillment_approvals WHERE id = :approval_id FOR UPDATE;`
   - *Hierarchy Rule:* Monotonic progression: Tier 4 $\rightarrow$ Tier 5.
4. **Manual Requirement Quantity Edit (`PUT /api/v1/requirements/{id}`):**
   - Step 1: Lock `BuyerRequirement` row (Tier 4):
     `SELECT * FROM buyer_requirements WHERE id = :id FOR UPDATE;`
   - *Hierarchy Rule:* Tier 4 only.
5. **Manual Requirement Closure (`POST /api/v1/requirements/{id}/close`):**
   - Step 1: Lock `BuyerRequirement` row (Tier 4):
     `SELECT * FROM buyer_requirements WHERE id = :id FOR UPDATE;`
   - *Hierarchy Rule:* Tier 4 only.
6. **Order Cancellation (`POST /api/v1/orders/{id}/cancel` — Module 4):**
   - Step 1: Lock `Order` (Tier 2).
   - Step 2: Lock associated `ProduceListing` rows in `id.asc()` (Tier 3) to restore available inventory.
   - Step 3: If order contains requirement-linked items, lock `BuyerRequirement` rows in `id.asc()` (Tier 4).
   - Step 4: Lock associated `RequirementFulfillmentApproval` rows in `id.asc()` (Tier 5) to transition pending approvals to `voided`.
   - *Hierarchy Rule:* Monotonic progression: Tier 2 $\rightarrow$ Tier 3 $\rightarrow$ Tier 4 $\rightarrow$ Tier 5.

### 6.3 Required Implementation Changes in Existing Services

To enforce this safe global hierarchy without regressions, the following codebase changes are required during implementation:
1. **`BuyerRequirementRepository` (`backend/app/requirements/repository.py`):**
   - Add parameter `for_update: bool = False` to `get_requirement_by_id`. When true, append `.with_for_update()`.
2. **`BuyerRequirementService` (`backend/app/requirements/service.py`):**
   - In `update_requirement` and `update_requirement_status`, call `get_requirement_by_id(..., for_update=True)` to ensure manual edits serialize through the Tier 4 lock.
3. **`OfferService` (`backend/app/offers/service.py`):**
   - Retain current locking sequence: `offer = self.repo.get_by_id(for_update=True)` (Tier 1) $\rightarrow$ `self.repo.lock_listings(listing_ids)` (Tier 3 in `id.asc()`) $\rightarrow$ `self.repo.lock_requirements(requirement_ids)` (Tier 4 in `id.asc()`). Approval records (Tier 5) are inserted into the database after inventory adjustments.
4. **`FulfillmentApprovalService` (new):**
   - In both `/approve` and `/reject` methods, acquire the `BuyerRequirement` lock (Tier 4) **before** acquiring the `RequirementFulfillmentApproval` lock (Tier 5).

### 6.4 Deadlock and Transient Retry Handling

We do **not** claim that lock ordering guarantees total deadlock freedom across an entire enterprise database, because unrelated background workers, analytics queries, or external transactions may access tables in differing orders.

#### Retry Rules
1. **Eligible Transient Errors Only:**
   - Only PostgreSQL SQLSTATE `40P01` (`deadlock_detected`) and `40001` (`serialization_failure`) are eligible for automatic retry.
   - Non-transient errors (`400 Bad Request`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`, check constraint violations) are **never retried**.
2. **Atomic Rollback & Clean Retry:**
   - Upon encountering `40P01` or `40001`, the service executes an immediate `db.rollback()`.
   - The entire transaction is re-attempted from the beginning.
   - Bounded retries: Maximum **3 retry attempts** with exponential backoff and randomized jitter (50ms, 100ms, 200ms + random jitter).
   - If retries are exhausted, raise `HTTPException(503, detail="Database temporarily busy. Please retry your request.")`.
3. **Post-Commit Side Effects:**
   - External notifications (emails, push notifications, webhooks) must **never fire inside the transaction block**.
   - Side effects are collected in an in-memory queue and dispatched **only after `db.commit()` succeeds**.

---

## 7. Order Cancellation & Post-Approval Lifecycle

The platform enforces distinct rules depending on the approval status when an order is cancelled:

### 7.1 Case A: Order Cancelled While Approval is `pending`
- The requirement quantity was never decremented.
- System transitions approval: `status = 'voided'`.
- System records: `voided_at = clock_timestamp()`, `voided_by_user_id = cancelling_user_id` (or `NULL` if system automated cancellation), `void_reason = "Parent order #{order_number} cancelled"`.
- Requirement `remaining_quantity` and `status` remain unchanged.

### 7.2 Case B: Order Cancelled While Approval is `rejected` or `not_applied`
- The requirement quantity was never decremented.
- Approval remains in its terminal status (`rejected` or `not_applied`).
- No change to requirement quantity.

### 7.3 Case C: Order Cancelled AFTER Approval has Decremented Requirement Quantity

#### The Safe Interim Decision
**Cancelling an already-approved order does NOT automatically restore or replenish requirement remaining quantity.**

#### Numerical Walkthrough Example
- **Initial Posting:** Buyer posts Requirement #R-100:
  `required_quantity = 5,000.000 kg`, `remaining_quantity = 5,000.000 kg`, `status = 'active'`.
- **Step 1 (Fulfillment Approved):** An offer for 1,500.000 kg is accepted and approved:
  - Deducted: $5,000.000 - 1,500.000 = 3,500.000\text{ kg}$.
  - Requirement #R-100 state: `remaining_quantity = 3,500.000 kg`, `status = 'partially_fulfilled'`.
  - Approval #A-201 state: `status = 'approved'`, `approved_quantity = 1,500.000 kg`.
- **Step 2 (Interim Buyer Demand Adjustment):** Buyer subsequently adjusts required quantity from `5,000.000 kg` down to `4,000.000 kg` due to facility intake constraints:
  - Previously fulfilled portion preserved: $1,500.000\text{ kg}$.
  - Requirement #R-100 `remaining_quantity` recalculated to: $4,000.000 - 1,500.000 = 2,500.000\text{ kg}$.
- **Step 3 (Order Cancellation Occurs):** The farmer experiences harvest failure; Order #O-301 is cancelled.
  - **Exact Numerical Outcome:** Requirement #R-100's `remaining_quantity` **remains strictly 2,500.000 kg**. It is **not** restored to 4,000.000 kg or 5,000.000 kg.
  - **Why Automatic Restoration is Prohibited:**
    If the platform automatically re-credited the 1,500.000 kg, `remaining_quantity` would become $2,500.000 + 1,500.000 = 4,000.000\text{ kg}$. But if the buyer had reduced required quantity to 3,000.000 kg, adding 1,500 kg would produce `remaining_quantity = 3,500 kg > required_quantity = 3,000 kg`, violating the database check constraint `chk_requirements_remaining_quantity` (`remaining_quantity <= required_quantity`) and throwing a fatal 500 error!
    Furthermore, if the buyer had already closed or expired the requirement, restoring demand would resurrect open demand on an inactive posting without buyer consent.

#### Operational Remedy for Buyer
The buyer receives an automated alert:
*"Order #O-301 (1,500 kg) has been cancelled. Requirement #R-100 remaining demand remains at 2,500 kg. If replacement produce is needed, please manually edit requirement #R-100 or post a new procurement requirement."*

#### Deferred Scope Boundary
Automated fulfillment reversal, re-crediting, and amendment accounting are explicitly out-of-scope for Module 3 and deferred to a dedicated future ADR (e.g., ADR-008 Order Amendments & Cancellations). No part of the AgriDirect platform automatically replenishes requirement demand on order cancellation.

---

## 8. Authorization & Ownership Security

### 8.1 Role & Ownership Requirements
Only the **verified commercial buyer who owns the linked buyer requirement** (`requirement.buyer_id == current_user.id`) may:
1. List their fulfillment approvals (`GET /fulfillment-approvals`).
2. View approval details (`GET /fulfillment-approvals/{id}`).
3. Approve fulfillment (`POST /fulfillment-approvals/{id}/approve`).
4. Reject fulfillment (`POST /fulfillment-approvals/{id}/reject`).
5. Close the requirement as part of an approval decision (`close_requirement: true`).

### 8.2 Security Response Specification
- **Non-Buyer / Unverified User:** Returns `403 Forbidden` (`{"detail": "Only verified commercial buyers can access requirement fulfillment approvals"}`).
- **Unauthorized Ownership Access:**
  - If a verified buyer requests an approval record associated with another buyer's requirement:
  - The system returns **`404 Not Found`** (`{"detail": "Fulfillment approval not found"}`).
  - **Security Rationale:** Returning `404 Not Found` instead of `403 Forbidden` prevents enumeration attacks and information leakage regarding whether a specific approval ID, requirement ID, or commercial order exists.

---

## 9. Migration Strategy & Assumptions

### 9.1 Verified Local Facts vs Sharing Assumptions
- **Verified Fact 1:** Local PostgreSQL database revision is `fcf5c991d506`. Migration `d4e5f6a1b2c3` has **not been applied** to PostgreSQL in this environment.
- **Verified Fact 2:** File `backend/alembic/versions/d4e5f6a1b2c3_add_buyer_requirement_id_to_offer_items_and_order_items.py` is an **untracked local file** (`git status`).
- **Verified Fact 3:** `d4e5f6a1b2c3` is **not present** in the local commit history of `main` or any inspected remote tracking branch.
- **Explicit Assumption Requiring Confirmation:** Whether `d4e5f6a1b2c3` was shared out-of-band (e.g., via Slack, email, another developer's fork, or a draft pull request) **cannot be established by local Git inspection alone**.
  - If the project owner confirms it was **never shared**, consolidating the `requirement_fulfillment_approvals` table and the composite unique constraint `uq_order_items_identity_requirement` into `d4e5f6a1b2c3` produces a clean single-revision migration for Module 3.
  - If there is **any possibility** it was shared, the safe path is creating a sequential migration `e5f6a7b8c9d0`.
- **Enforcement Rule:** No migration file will be edited, created, or executed until explicit authorization is granted.

---

## 10. Concrete Test Plan & SRS Traceability

### 10.1 Automated Test Plan

#### Unit Tests (SQLite in-memory)
1. `test_buyer_accepts_offer_immediate_approved`: Verifies buyer acceptance with `apply_to_requirement=true` decrements requirement and creates `approved` record with `approved_quantity`.
2. `test_buyer_accepts_offer_immediate_not_applied`: Verifies buyer acceptance with `apply_to_requirement=false` leaves requirement untouched and creates `not_applied` record.
3. `test_buyer_accepts_offer_excess_quantity_fails_409`: Verifies acceptance fails with 409 when approved quantity > remaining requirement quantity.
4. `test_multi_item_offer_acceptance_atomicity_failure_rolls_back_everything`:
   - Setup: Offer contains at least two items referencing different requirements (Req 1 and Req 2).
   - Execution: Item 1 passes validation. Item 2 requests an approved quantity exceeding Req 2's remaining quantity.
   - Verification:
     - The call fails with `409 Conflict`.
     - Zero `Order` rows exist.
     - Zero `OrderItem` rows exist.
     - Zero `InventoryAdjustment` rows exist; farmer listing inventory is unadjusted.
     - Zero `RequirementFulfillmentApproval` rows exist.
     - Req 1 and Req 2 quantities and statuses are completely unchanged.
     - The offer remains in `pending` status.
5. `test_farmer_accepts_offer_creates_pending_approval`: Verifies order created, inventory deducted, requirement untouched, approval marked `pending`.
6. `test_subsequent_partial_approval`: Verifies approving 50 kg on 70 kg proposed deducts 50 kg from requirement; order stays 70 kg.
7. `test_subsequent_approval_exceeding_remaining_fails_409`: Verifies 409 Conflict when approved quantity > remaining demand. Verifies zero silent clamping.
8. `test_zero_remaining_remains_open_without_close_flag`: Verifies requirement remaining reaching 0.000 remains `partially_fulfilled` when `close_requirement=false`.
9. `test_subsequent_rejection_preserves_demand`: Verifies `/reject` records reason and leaves requirement quantity completely untouched (`FR-REQ-08`).
10. `test_order_cancellation_voids_pending_approval`: Verifies cancelling order transitions pending approval to `voided` with audit fields.
11. `test_system_voiding_records_null_user_and_valid_reason`: Verifies automated voiding populates `voided_by_user_id = NULL` and valid `void_reason`.
12. `test_terminal_state_immutability`: Verifies terminal states (`approved`, `rejected`, `not_applied`, `voided`) reject subsequent review attempts with 409.
13. `test_ownership_enforcement_returns_404`: Verifies that another buyer attempting to access or review an approval receives `404 Not Found`.

#### Integration & Concurrency Tests (PostgreSQL)
1. `test_composite_foreign_key_rejects_mismatched_requirement`: Verifies database engine rejects approval records referencing mismatched order item/requirement IDs.
2. `test_composite_foreign_key_rejects_null_requirement_order_item`: Verifies database engine rejects approval records referencing order items whose `buyer_requirement_id` is NULL.
3. `test_concurrent_approvals_serialization`: Verifies concurrent approval requests serialize on requirement lock without double-decrementing.
4. `test_deadlock_retry_handler`: Simulates PostgreSQL `40P01` error and verifies automatic rollback and clean retry.
5. `test_foreign_key_delete_restrictions`: Verifies `ON DELETE RESTRICT` prevents physical deletion of requirement, order, order item, or user.

---

### 10.2 SRS Traceability Matrix

| SRS Requirement | Architectural Mechanism |
|---|---|
| **FR-REQ-06** | Dedicated `requirement_fulfillment_approvals` table audits each order line item against requirement fulfillment. |
| **FR-REQ-07** | Immediate acceptance payload and dedicated `/approve` endpoint give buyer explicit control over deduction. |
| **FR-REQ-08** | `/reject` marks approval `rejected` and leaves `remaining_quantity` untouched, preserving open demand. |
| **BR-07** | Farmer acceptance generates `pending` approval without modifying requirement; buyer retains sole authority. |
| **FR-OFF-08** | Mutual offer acceptance creates commercial `Order` atomically across all items and deductions. |
| **BR-09** | Farmer listing inventory is decremented atomically upon order creation without waiting for requirement fulfillment approval. |

---

## 11. Conclusion & Next Steps

All global lock hierarchies, composite foreign key lifecycle rules, post-approval cancellation semantics, and service-level exception models are reconciled without contradictions.

**Status:** **READY FOR ARCHITECTURE APPROVAL**.
