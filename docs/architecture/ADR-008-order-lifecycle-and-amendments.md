# ADR-008: Orders, Inventory Lifecycle, and Bilateral Amendment Workflow

**Status:** Accepted & Verified  
**Date:** 2026-10-31  

---

## 1. Context

AgriDirect is a direct B2B agricultural marketplace connecting farmers directly with commercial buyers.
Upon offer acceptance, an `Order` and snapshot `OrderItem` records are atomically instantiated, with listing stock deducted via append-only `InventoryAdjustment` records (`order_fulfillment`).

In Module 4 (Orders & Inventory Lifecycle), the platform must support:
1. Seller order confirmation (`pending -> confirmed`).
2. Bilateral delivery coordination and receipt acknowledgement (`not_arranged -> arranged -> completion_marked -> completed`).
3. Atomic order cancellation with zero duplicate inventory or demand restitution.
4. Bilateral post-finalization amendments (quantity, price, delivery date, terms) with cumulative, non-double-counting buyer demand restitution.
5. Append-only inventory audit ledgers for orders and produce listings.

A critical requirement is preserving the canonical global lock hierarchy to prevent deadlocks and race conditions across concurrent operations.

---

## 2. Canonical Five-Tier Database Lock Hierarchy

All transactional operations modifying orders, listings, requirements, or approvals must acquire row-level database locks (`SELECT ... FOR UPDATE`) strictly in this order:

| Tier | Entity | Lock Ordering | Scope |
|---|---|---|---|
| 1 | Offer | Ascending UUID / Module 3 rules | Offer acceptance |
| 2 | Order | Order row | Order confirmation, cancellation, amendments, delivery |
| 3 | ProduceListing | Ascending UUID | Stock deduction, restitution, amendment delta |
| 4 | BuyerRequirement | Ascending UUID | Demand restitution, capacity validation |
| 5 | RequirementFulfillmentApproval | Ascending UUID | Fulfillment status, voiding, consumption audit |

### Rules:
1. Never acquire a lower-tier lock before a higher-tier lock.
2. When accessing Tier 5, relevant Tier 4 locks must be acquired first.
3. Multiple rows within a tier must be acquired in ascending UUID order.
4. `with_for_update(of=Model)` and `populate_existing=True` must be applied to prevent unintended locks on joined tables and stale identity-map reads.

---

## 3. Decisions & Accounting Architecture

### 3.1 Order Confirmation (Seller Exclusivity)
- Only the farmer (`order.farmer_id`) can confirm an order.
- Transitions `pending -> confirmed`.
- Represents the seller's fulfillment commitment.

### 3.2 Atomic Order Cancellation
- Only authorized participants (buyer, farmer, admin) may cancel eligible active orders (`pending`, `confirmed`, `delivery_arranged`).
- Cancellation is strictly forbidden if the order is already terminal (`completed`, `cancelled`), `disputed`, or if any line item has already been `fulfilled` or `disputed`.
- **Inventory Restitution:**
  - Net order inventory impact is calculated authoritatively from the audit ledger:
    $$\text{net\_impact} = \sum_{\text{ORDER\_CHANGE\_TYPES}} \text{quantity\_delta}$$
  - Outstanding deduction to restore:
    $$\text{outstanding} = \max(0, -\text{net\_impact})$$
  - Restores listing stock and records `order_cancellation_release`. The final net ledger balance for the order equals exactly zero.
- **Buyer Demand Restitution:**
  - Approved fulfillment approvals are immutable historical records and are never mutated.
  - Cumulative demand restored by prior effective amendments for the specific item is subtracted:
    $$\text{remaining\_consumption} = \max(0, \text{approved\_quantity} - \text{cumulative\_prior\_demand\_restored})$$
  - Restitution occurs only if the requirement is open (`active` or `partially_fulfilled`), unexpired, and not deleted.
  - Restored quantity is capped by available gap: $\min(\text{remaining\_consumption}, \text{required\_quantity} - \text{remaining\_quantity})$.
  - Closed requirements are **never automatically reopened**.
  - Pending fulfillment approvals are transitioned to `voided` with audit metadata (`voided_by_user_id`, `voided_at`, `void_reason`).

### 3.3 Bilateral Order Amendments
- One counterparty proposes; only the opposite counterparty can accept or reject.
- A proposer cannot accept or reject their own amendment proposal.
- Only one pending amendment is permitted per order at any given time.
- Quantity increases deduct listing stock (rejecting if stock is insufficient) and treat extra quantity as commercial overage (no silent consumption of buyer requirement demand).
- Quantity decreases restore listing stock (`amendment_delta` positive) and restore requirement demand if eligible, recording `"demand_restored"` inside the effective amendment's `new_value` JSON snapshot.
- Successive amendments sum historical `"demand_restored"` values to prevent double-counting.

### 3.4 Delivery Coordination & Acknowledgement Policy

Delivery coordination follows a strict state progression: `not_arranged -> arranged -> completion_marked -> completed`.

1. **Delivery Scheduling:**
   - Either counterparty can schedule delivery arrangements (`delivery_status = arranged`, `status = delivery_arranged`).

2. **Delivery Completion Marking:**
   - An authorized participant (farmer, buyer, or administrator) marks that transit/dispatch has completed (`delivery_status = completion_marked`).
   - The system records `delivery_completion_marked_by_user_id` and `delivery_completion_marked_at`.

3. **Delivery Acknowledgement Workflows:**
   - **Scenario A (Farmer-Initiated):**
     - Farmer marks completion.
     - Buyer must acknowledge receipt.
     - Farmer cannot self-acknowledge (HTTP 403).
     - Once Buyer acknowledges, order transitions to `completed`.
   - **Scenario B (Buyer-Initiated / Self-Pickup):**
     - Buyer marks completion.
     - Farmer must acknowledge receipt.
     - Buyer cannot self-acknowledge (HTTP 403).
     - Once Farmer acknowledges, order transitions to `completed`.
   - **Scenario C (Administrator Intervention):**
     - Administrator marks delivery completion (e.g. following third-party logistics dispatch or dispute resolution).
     - **Dual Independent Acknowledgements Required:** Both the farmer and buyer must independently acknowledge receipt.
     - Administrator acknowledgement cannot substitute for either commercial party (HTTP 403).
     - Farmer acknowledgement alone does not complete the order (order remains in `delivery_arranged` / `completion_marked`, awaiting buyer).
     - Buyer acknowledgement alone does not complete the order (order remains in `delivery_arranged` / `completion_marked`, awaiting farmer).
     - Only after **both** independent acknowledgements are recorded does the order transition to `completed`.

| Completion Marked By | Farmer Acknowledgement | Buyer Acknowledgement | Order Completed |
|---|---|---|---|
| Farmer | Not required | Required | After buyer acknowledges |
| Buyer | Required | Not required | After farmer acknowledges |
| Administrator | Required | Required | After both acknowledge |

4. **Dedicated Persistence (`order_delivery_acknowledgements`):**
   - Each acknowledgement is atomically persisted in `order_delivery_acknowledgements`:
     - `id`: UUID Primary Key
     - `order_id`: UUID FK $\to$ `orders.id` (ON DELETE CASCADE)
     - `user_id`: UUID FK $\to$ `users.id` (ON DELETE RESTRICT)
     - `acknowledged_at`: TIMESTAMP WITH TIME ZONE (`server_default=now()`)
     - `notes`: TEXT (optional verification or condition remarks)
     - Unique constraint: `(order_id, user_id)` preventing duplicate acknowledgements.
   - **Legacy Column Synchronization:**
     - `order.delivery_acknowledged_by_user_id` and `order.delivery_acknowledged_at` are preserved for backward compatibility and are updated with the actor and timestamp that formally brought the order to terminal completion (`completed`).

5. **Additional Invariants:**
   - Universal anti-self-dealing: The user who marked delivery completion can never acknowledge that same delivery (HTTP 403).
   - Commercial party exclusivity: Only the actual buyer and farmer linked to the order can acknowledge; unrelated third parties receive HTTP 404 (anti-enumeration).
   - Idempotency & duplicate prevention: Duplicate acknowledgement requests from the same user are rejected with HTTP 409.
   - Terminal finality: Once completed, the order is terminal and line items transition to `fulfilled`.

### 3.5 Append-Only Inventory Audit Ledger
- All inventory mutations (`order_fulfillment`, `order_cancellation_release`, `amendment_delta`, `manual_restock`, `manual_shrinkage`) are recorded in `inventory_adjustments`.
- Order ledger queries filter strictly by `order_id` and order change types.
- Listing ledger queries filter by `listing_id`, restricted to the listing owner.

---

## 4. Consequences & Verification

- **Deadlock Immunity:** Strict Tier 2 $\to$ 3 $\to$ 4 $\to$ 5 ordering guarantees zero deadlocks under concurrent requests.
- **Zero Overselling / Zero Phantom Stock:** PostgreSQL row-level locks and transaction serialisation ensure listing stock is never over-restored or double-sold.
- **Audit Integrity:** Financial and inventory audit trails remain completely tamper-proof and append-only.
- **Test Evidence:** Verified by 21 unit/integration API tests and 11 PostgreSQL multi-threaded concurrency scenarios with zero failures across SQLite and live PostgreSQL 18.6 runtimes.

