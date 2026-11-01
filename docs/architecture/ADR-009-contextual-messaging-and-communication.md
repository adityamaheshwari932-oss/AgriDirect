# ADR-009: Contextual Messaging, Media Attachments, Contact Disclosure, and Communication System

**Status:** Accepted & Verified  
**Date:** 2026-10-31  

---

## 1. Context

AgriDirect is a B2B agricultural marketplace facilitating trade between verified farmers and commercial buyers. To negotiate terms, discuss produce quality, arrange logistics, and coordinate order delivery, buyers and farmers require a direct, contextual communication channel.

Prior to Module 5, the database schema contained baseline tables for `conversations`, `conversation_participants`, `messages`, and `message_attachments` created in early migrations. However, these models lacked support for:
1. **Dynamic Context Linking:** Associating conversations directly with `Order` records in addition to listings and requirements.
2. **Mutual-Consent Contact Sharing:** Strict privacy and anti-circumvention protection where contact information (phone, email, business address) remains confidential unless both parties bilaterally agree to share details.
3. **Delivery & Read Status Lifecycle:** Real-time visibility into message states (`sent -> delivered -> read`) with unread counters.
4. **Media & Document Handling:** Secure attachment handling with magic byte validation, size limits, filesystem isolation, path traversal defense, and automatic file cleanup on transaction rollback.
5. **Anti-Enumeration Security:** Guaranteeing that non-participants cannot probe or discover thread existence, returning HTTP 404 for unauthorized threads, messages, or attachments.
6. **Concurrency Safety:** Deterministic conversation deduplication under concurrent creation attempts and race-free contact sharing request handling.

---

## 2. Decision & Architecture

### 2.1 Domain Models and Schema Extensions

Module 5 extends the chat schema via Alembic migration `f6a1b2c3d4e5` and ORM definitions in `backend/app/models/chat.py`:

1. **`Conversation` (`conversations`):**
   - Canonical 1-on-1 thread between a farmer and a buyer (`uq_conversations_counterparts`).
   - Added `order_id` (UUID nullable, FK `orders.id` ON DELETE SET NULL, indexed) for order-linked threads.
   - Added `status` (`active`, `archived`) with check constraint `chk_conversations_status`.
   - `last_message_at` updated atomically upon new message arrival.

2. **`ConversationParticipant` (`conversation_participants`):**
   - Per-user membership record with `share_contact_details` boolean flag and `last_read_at` timestamp.
   - Unique constraint `uq_conversation_participants` on `(conversation_id, user_id)`.

3. **`Message` (`messages`):**
   - Added `message_type` (`text`, `system`, `contact_request`) with check constraint `chk_messages_type`.
   - Added `delivery_status` (`sent`, `delivered`, `read`) with check constraint `chk_messages_delivery_status`.
   - Added `delivered_at` and `read_at` nullable timestamps.
   - Added optional `order_id` (FK `orders.id` ON DELETE SET NULL) for context reference.
   - Composite index `idx_messages_status` on `(conversation_id, delivery_status)` for fast unread queries.

4. **`MessageAttachment` (`message_attachments`):**
   - Added `attachment_type` (`image`, `document`) with check constraint `chk_msg_attachments_type`.
   - Foreign key to `messages.id` ON DELETE CASCADE.
   - Preserves size constraint `chk_msg_attachments_file_size` ($> 0$).

5. **`ContactShareRequest` (`contact_share_requests`):**
   - Implements bilateral mutual-consent contact disclosure.
   - Fields: `id`, `conversation_id`, `requester_id`, `recipient_id`, `status` (`pending`, `approved`, `rejected`, `cancelled`), `requested_at`, `responded_at`, `notes`.
   - Counterpart check constraint: `chk_contact_share_counterparts` (`requester_id <> recipient_id`).
   - Status check constraint: `chk_contact_share_status`.
   - Partial unique index `uq_contact_share_pending_conv` on `(conversation_id) WHERE status = 'pending'` to guarantee at most one pending request per conversation at any time.

---

### 2.2 Concurrency and Locking Strategy

To ensure zero race conditions and total thread safety across concurrent requests:

1. **Conversation Creation Deduplication:**
   - Conversations enforce canonical uniqueness on `(farmer_id, buyer_id)`.
   - Under concurrent thread creation by both parties, the second transaction catches `IntegrityError`, rolls back, and automatically re-fetches the winner's conversation.
2. **Contact Share Request Concurrency:**
   - The partial unique index `uq_contact_share_pending_conv` prevents multiple concurrent pending requests.
   - Service responses use row-level locking (`SELECT ... FOR UPDATE`) on `ContactShareRequest` during `respond_contact_share_request` to serialize accept/reject decisions.
3. **Unread Counter Computation:**
   - Calculated by querying messages in the conversation where `sender_id != current_user.id` and `delivery_status != 'read'` (or `is_read = False`).

---

### 2.3 Attachment Storage, Magic Byte Validation, and Path Traversal Protection

Storage abstraction is encapsulated in `ChatStorageService` (`backend/app/chat/storage.py`):

1. **Storage Isolation:**
   - Files are stored in dedicated directories: `<upload_root>/chat/images/` and `<upload_root>/chat/documents/`.
   - Absolute canonical path normalization (`os.path.realpath`) verifies that all file targets reside strictly within the allowed directory tree, neutralizing path traversal attacks (`../`, `..\\`).
2. **Magic Byte Inspection:**
   - Content types are never trusted from the client's MIME headers alone.
   - **Allowed Images (Max 10 MB):**
     - JPEG: `\xFF\xD8\xFF`
     - PNG: `\x89PNG\r\n\x1A\n`
     - WebP: `RIFF....WEBP`
   - **Allowed Documents (Max 25 MB):**
     - PDF: `%PDF-`
     - DOCX / XLSX: ZIP magic bytes `\x50\x4B\x03\x04`
     - CSV / TXT: Validated UTF-8 / ASCII text streams.
   - **Executable Blocking:**
     - Explicit rejection of Windows PE / DOS executables (`MZ` / `0x4D5A`), Linux ELF (`\x7FELF`), and Mach-O binaries regardless of declared file extension.
3. **Atomic Storage Cleanup:**
   - If database insertion of `Message` or `MessageAttachment` fails or rolls back, saved disk files are immediately and unrecoverably cleaned up via `storage.delete_file()` in the exception handler.

---

### 2.4 Contact Disclosure Privacy Workflow

1. **Default State:**
   - Participant profiles returned in chat metadata mask sensitive contact fields (`phone`, `email`, physical addresses) with `None`.
2. **Request Workflow:**
   - Participant A submits `POST /api/v1/chat/conversations/{id}/contact-share` (`pending`).
   - Participant B submits `POST /api/v1/chat/conversations/{id}/contact-share/{request_id}/respond` with `status: "approved"`.
3. **Post-Consent State:**
   - Both `ConversationParticipant` records update `share_contact_details = True`.
   - A system message is appended to the conversation recording consent.
   - Subsequent `GET /api/v1/chat/conversations/{id}` requests disclose the counterpart's email, phone number, and location details.
   - If rejected, `share_contact_details` remains `False`, and contact details remain masked.

---

### 2.5 Security, Authorization & Anti-Enumeration

1. **Role and Verification Enforcement:**
   - Only verified users (`is_verified = True`) with role `farmer` or `buyer` can participate in chat.
   - Suspended or inactive users (`is_active = False`) are rejected with HTTP 403 Forbidden.
2. **Strict Anti-Enumeration (HTTP 404):**
   - When a user requests a conversation, message, or attachment for which they are not a participant, the API returns `404 Not Found` (never 403 Forbidden).
   - This prevents attackers from enumerating valid conversation or attachment UUIDs.
3. **Order Lifecycle Independence:**
   - Order-linked conversations allow participants to communicate regarding order execution.
   - Chat operations have **zero capability** to mutate order statuses, line items, or inventory balances. All order mutations remain strictly guarded inside Module 4 order services.

---

## 3. Consequences

### Positive
- **Thread Safety:** Proven concurrent creation and contact sharing safety verified against PostgreSQL with row-level locks and partial indexes.
- **Data Protection:** Contact details cannot be leaked or scraped without bilateral consent.
- **Attachment Security:** Zero vulnerability to executable upload or path traversal exploits.
- **Clean Audit Trail:** System messages record contact share events, and order references link conversations without coupling transactional order code to messaging.

### Negative / Trade-offs
- File attachments reside on the local filesystem in development/single-instance mode. For multi-node distributed deployments, `ChatStorageService` should be extended to support S3 / GCS cloud object storage via the same interface.

