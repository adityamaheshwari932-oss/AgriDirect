# ADR-010: Off-Platform Payment Tracking, Evidence Archival, and Administrative Dispute Moderation

**Status:** Accepted & Verified  
**Date:** 2026-11-01  

---

## 1. Context

AgriDirect is a direct farmer-to-buyer B2B agricultural marketplace. A foundational architectural principle (mandated in `AGENTS.md` and `PROJECT_CONTEXT.md`) is that **AgriDirect never processes payments, holds funds in escrow, or moves money between accounts**. All financial transactions occur directly off-platform through external banking channels (e.g., UPI, NEFT/RTGS, cash, or cheques).

However, commercial trade participants require authoritative record-keeping and settlement transparency:
1. **Settlement Visibility:** Buyers must be able to record payment claims with reference numbers, payment dates, payment methods, and optional receipt attachments.
2. **Seller Acknowledgement:** Selling farmers must have exclusive authority to acknowledge receipt of funds into their external accounts.
3. **Overpayment Prevention:** The system must prevent cumulative payment claims from exceeding the finalized order ceiling, even under concurrent submissions.
4. **Lifecycle Independence:** Payment tracking status must remain architecturally independent of order and delivery states. Orders may transition through delivery phases while payments are incrementally recorded or acknowledged.
5. **Dispute Moderation:** When payments are contested (e.g., funds debited but unacknowledged, or bouncing cheques), participants require a structured mechanism to lodge complaints with evidence. Administrators must be equipped to moderate disputes, inspect documents, and record resolution findings without interfering with external banking infrastructure.
6. **Attachment Security:** Payment receipts and dispute documents must be protected against malicious executable uploads, path traversal attacks, and unauthorized inspection (anti-enumeration).

---

## 2. Decision & Architecture

### 2.1 Domain Models and Schema Design

The system implements the non-custodial payment tracking architecture defined in `schema-design.md` via tables `payment_records` (Store D13) and `payment_complaints` (Sub-store D17):

1. **`PaymentRecord` (`payment_records`):**
   - Primary key: UUID primary key (`id`).
   - Foreign keys: `order_id` (FK `orders.id` ON DELETE RESTRICT), `recorded_by_user_id` (FK `users.id` ON DELETE RESTRICT).
   - Financial attributes: `amount` (Numeric(12, 2)), `payment_method` (`upi`, `bank_transfer`, `cash`, `other`), `reference_number` (String(128) nullable), `payment_date` (Date).
   - Attachment: `proof_file_uri` (String(512) nullable).
   - Lifecycle & Audit: `status` (`payment_recorded`, `acknowledged`, `disputed`), `acknowledged_at` (DateTime nullable; current active acknowledgement), `original_acknowledged_at` (DateTime nullable; immutable historical record of initial seller confirmation).
   - Database Check Constraints:
     - `chk_payments_amount`: `amount > 0`.
     - `chk_payments_method`: `payment_method IN ('upi', 'bank_transfer', 'cash', 'other')`.
     - `chk_payments_status`: `status IN ('payment_recorded', 'acknowledged', 'disputed')`.

2. **`PaymentComplaint` (`payment_complaints`):**
   - Primary key: UUID primary key (`id`).
   - Foreign keys: `payment_record_id` (FK `payment_records.id` ON DELETE RESTRICT), `complainant_user_id` (FK `users.id` ON DELETE RESTRICT), `resolved_by_admin_id` (FK `users.id` ON DELETE SET NULL nullable).
   - Dispute attributes: `complaint_reason` (Text), `evidence_file_uri` (String(512) nullable).
   - Moderation state: `status` (`open`, `under_review`, `resolved`, `dismissed`), `admin_resolution_notes` (Text nullable).
   - Database Check Constraints:
     - `chk_payment_complaints_status`: `status IN ('open', 'under_review', 'resolved', 'dismissed')`.

---

### 2.2 Concurrency and Canonical 7-Tier Global Lock Hierarchy

To prevent overpayment race conditions, deadlocks, and inconsistent dispute transitions, all database transactions across the platform adhere strictly to the canonical global lock ordering hierarchy established in ADR-008 and extended for Module 6:

- **Tier 1:** `Offer` (negotiation lock)
- **Tier 2:** `Order` (order lifecycle and payment ceiling lock)
- **Tier 3:** `ProduceListing` (inventory lock; ascending UUID ordering)
- **Tier 4:** `BuyerRequirement` (demand fulfillment lock; ascending UUID ordering)
- **Tier 5:** `RequirementFulfillmentApproval` (farmer approval lock; ascending UUID ordering)
- **Tier 6:** `PaymentRecord` (payment tracking lock; ascending UUID ordering)
- **Tier 7:** `PaymentComplaint` (dispute moderation lock; ascending UUID ordering)

Within Module 6, transactions acquire locks strictly according to this global hierarchy:

$$\text{Tier 2 (Order)} \longrightarrow \text{Tier 6 (PaymentRecord)} \longrightarrow \text{Tier 7 (PaymentComplaint)}$$

1. **Overpayment Prevention Algorithm:**
   - On every payment submission, the transaction acquires an exclusive row lock on the parent order:
     ```sql
     SELECT * FROM orders WHERE id = :order_id FOR UPDATE;
     ```
   - The authoritative payment aggregate is computed synchronously across all active financial claims:
     $$\text{committed\_amount} = \text{total\_acknowledged} + \text{unacknowledged\_amount} + \text{total\_disputed}$$
     $$\text{max\_available\_for\_new\_payment} = \max(0.00, \text{order.total\_amount} - \text{committed\_amount})$$
     $$\text{remaining\_payable\_amount} = \max(0.00, \text{order.total\_amount} - \text{committed\_amount})$$
   - If $\text{new\_amount} > \text{max\_available\_for\_new\_payment}$, the request is rejected immediately with `HTTP 409 Conflict`.
   - Serialized row-level locking ensures that concurrent payment submissions cannot bypass this ceiling under any race condition.
   - Including `total_disputed` in the committed ceiling guarantees that a buyer cannot exploit an active dispute to record duplicate payments that exceed the order total.

2. **Dispute and Acknowledgement Race Handling:**
   - Operations on existing payments look up the target payment to discover the associated `order_id`, lock the `Order` row first (Tier 2) with `with_for_update(of=Order).populate_existing()`, lock the `PaymentRecord` (Tier 6), and finally lock the `PaymentComplaint` (Tier 7).
   - This strict ascending tier ordering prevents deadlock cycles between concurrent farmer acknowledgement, buyer dispute filing, and administrative dispute moderation transactions.

---

### 2.3 Financial Reconciliation and Summary Aggregates

The repository computes authoritative reconciliation metrics:
- **`total_recorded`:** Aggregate sum of all payments recorded against the order (`total_acknowledged + unacknowledged_amount + total_disputed`).
- **`total_acknowledged`:** Sum of payments confirmed by the selling farmer (`status = 'acknowledged'`).
- **`total_disputed`:** Sum of contested payments currently under dispute (`status = 'disputed'`).
- **`unacknowledged_amount`:** Sum of payments recorded and awaiting seller acknowledgement (`status = 'payment_recorded'`).
- **`remaining_acknowledged_balance`:** Unsettled balance on the order: $\max(0.00, \text{order\_total} - \text{total\_acknowledged})$.
- **`remaining_payable_amount` / `max_available_for_new_payment`:** Remaining allowable payment capacity before reaching the order total: $\max(0.00, \text{order\_total} - (\text{total\_acknowledged} + \text{unacknowledged\_amount} + \text{total\_disputed}))$.
- **`settlement_status`:** Categorical settlement state defining both fund confirmation and claim presence:
  - `"fully_settled"` if $\text{total\_acknowledged} \ge \text{order\_total}$. (Seller confirmed 100% of order total).
  - `"partially_settled"` if $0 < \text{total\_acknowledged} < \text{order\_total}$. (Seller confirmed partial payment; an acknowledged balance remains).
  - `"payment_pending_acknowledgement"` if $\text{unacknowledged\_amount} > 0$ and $\text{total\_acknowledged} = 0$. (Buyer has submitted claims; awaiting seller confirmation).
  - `"disputed"` if $\text{total\_disputed} > 0$ and $\text{total\_acknowledged} = 0$ and $\text{unacknowledged\_amount} = 0$. (Zero confirmed funds; all recorded payment claims are actively locked in formal dispute).
  - `"unpaid"` strictly if $\text{total\_recorded} = 0.00$. (No payment claims have been recorded against the order; zero payment activity).

---

### 2.4 Administrative Moderation Workflow & Explicit Seller Reaffirmation

Administrators facilitate dispute resolution without moving funds and without usurping seller authority:
1. **Administrative Non-Custodial Principle:**
   - Administrators review external evidence (bank statements, counterparty claims, UTR traces) and record findings.
   - **Administrators NEVER acknowledge payments** on behalf of either participant, neither directly nor indirectly.
   - Payment receipt acknowledgement remains strictly and exclusively the prerogative of the designated selling farmer.
   - Administrative findings never automatically claim or certify that funds were received off-platform.
2. **Queue Listing & Detail:** Administrators review paginated open disputes, inspecting complainant details, order terms, transaction references, and attached evidence.
3. **Status Progression:**
   - An administrator marks a complaint `under_review` while investigating external transaction records.
   - Upon completing review, the administrator transitions the complaint to `resolved` or `dismissed`.
   - Mandatory resolution notes ($\ge 5$ characters) must be recorded for auditability and transparency.
   - An immutable record is created in `admin_audit_logs` capturing the administrative moderation action.
4. **Payment Record Adjustment Upon Dispute Resolution:**
   - When a complaint is `resolved` or `dismissed`, the associated payment transitions from `disputed` back to `payment_recorded`.
   - `acknowledged_at` is set to `None` (current confirmation is inactive pending seller reaffirmation).
   - **Historical Acknowledgement Evidence is NEVER Erased:** `original_acknowledged_at` retains the exact timestamp of initial farmer confirmation, preserving an immutable audit record.
   - The payment amount remains reserved in `committed_amount` to prevent overpayment exploits.
   - **Mandatory Farmer Reaffirmation:** To finalize settlement, the designated selling farmer must explicitly reaffirm receipt by executing `POST /api/v1/payments/{payment_id}/acknowledge`. Only upon explicit seller reaffirmation does the payment return to `acknowledged` status with an updated `acknowledged_at` timestamp.
5. **Bilateral Notification:** Both parties receive structured in-app notifications whenever dispute moderation actions are executed.

---

### 2.5 File Security & Anti-Traversal Architecture

The `PaymentStorageService` enforces strict defense-in-depth:
1. **Binary Magic Bytes Validation:** Re-inspects initial file chunks to verify valid JPEG (`\xFF\xD8\xFF`), PNG (`\x89PNG\r\n\x1a\n`), or PDF (`%PDF-`) signatures.
2. **Explicit Executable Rejection:** Scans for and rejects Windows PE (`MZ`), Linux ELF (`\x7fELF`), Mach-O/Java bytecode (`\xca\xfe\xba\xbe`), and shell scripts (`#!`).
3. **Size Limit:** Enforces a 10 MB maximum upload size limit; rejects 0-byte uploads.
4. **Server-Generated Filenames:** Client filenames are discarded and replaced with random UUIDs (`<uuid>.<ext>`) to prevent shell injection or filename manipulation.
5. **Path Containment (`Path.is_relative_to`):** Verifies that resolved file paths are strictly within the designated storage directory, preventing directory traversal (`../`) and string-prefix sibling directory bypasses.
6. **Anti-Enumeration Download Protection:** Only authorized transaction participants (order buyer, order farmer) and administrators may download payment proof or dispute evidence files; all other callers receive `HTTP 404 Not Found`.

---

## 3. Consequences

### Positive
- **Zero Financial Liability:** AgriDirect remains strictly non-custodial, avoiding regulatory escrow and banking compliance burdens.
- **Accurate Settlement Visibility:** Both buyers and farmers retain real-time visibility into paid, pending, and disputed balances.
- **Concurrency Safety:** Row-level locking guarantees zero overpayment leaks under concurrent requests.
- **Defense in Depth:** Filesystem isolation, magic byte verification, and anti-enumeration protect against malware delivery and unauthorized inspection.
- **Authoritative Auditability:** Immutable timestamped records with administrative resolution notes establish a defensible dispute paper trail.

### Negative / Trade-offs
- Off-platform payment claims rely on bilateral honesty and administrative facilitation; AgriDirect cannot physically reverse a fraudulent bank transfer.
- Row-level locking on the `Order` table temporarily serializes concurrent payment submissions for the same order (mitigated by brief lock duration within a single transaction).

