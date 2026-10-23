# AgriDirect — Project Context

## What Is AgriDirect?

AgriDirect is a **B2B agricultural marketplace** that directly connects **farmers** (sellers) with **commercial buyers** (restaurants, hotels, retailers, grocery businesses, caterers, and food processors). It removes intermediaries from the agricultural supply chain, enabling price transparency and direct trade relationships.

> AgriDirect **facilitates** transactions. It does not own, sell, hold payment for, or physically transport agricultural produce.

---

## Actors

| Actor | Role |
|---|---|
| **Farmer** | Registers, lists produce, responds to buyer requirements, negotiates, fulfils orders |
| **Buyer** | Registers, posts requirements, discovers listings, negotiates, places orders |
| **Administrator** | Reviews and approves/rejects verification documents for farmers and buyers |
| **System** | Enforces business rules, guards API endpoints, manages state transitions |

---

## Core Scope

### In Scope
- Separate farmer and buyer registration and onboarding
- Document-based identity/business verification (reviewed by admin)
- Produce listings created by verified farmers
- Buyer requirement posts
- Offer and counter-offer negotiation (structured + contextual chat)
- Order creation from accepted offers
- Order amendments (recorded, requiring mutual agreement)
- Basic delivery arrangement and completion confirmation
- Role-based access control enforced on the backend
- Descriptive market analytics from real transaction data
- Payment record capture (no payment processing or fund holding)

### Out of Scope (Current Phase)
- Payment processing, escrow, or money transfers
- Physical logistics or transport management
- ML-based demand or price forecasting
- Consumer-facing (B2C) functionality

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18+ with TypeScript |
| Backend | Python 3.12+ with FastAPI |
| Database | PostgreSQL 16+ |
| ORM | SQLAlchemy 2.x (async) |
| Validation | Pydantic v2 |
| Authentication | JWT (access + refresh tokens), bcrypt password hashing |
| API Style | REST |
| Containerisation | Docker + Docker Compose |
| Version Control | Git + GitHub |

---

## Key Business Rules

1. AgriDirect facilitates transactions; it does not own or sell produce.
2. Farmer and buyer registration flows are distinct.
3. Verification is role-specific and document-based; administrators review submissions.
4. Unverified users may register, manage their profile, and browse; they **cannot** create listings, post requirements, make offers, initiate orders, or initiate chats.
5. Only **verified farmers** may create produce listings and respond to buyer requirements.
6. Only **verified buyers** may purchase produce.
7. Both sides may negotiate through contextual chat and structured offers.
8. Accepted offers automatically create orders.
9. Inventory changes require the defined farmer approval workflow — **silent inventory deduction is forbidden**.
10. Finalized orders cannot be silently edited. All changes require a recorded amendment and mutual agreement.
11. AgriDirect records payment information but **does not process, hold, or transfer money**.
12. Physical transportation is outside scope. Only basic delivery arrangements and completion confirmation are included.
13. Market analytics are descriptive and based on clearly identified data. ML forecasting is not in scope.
14. **Backend authorization and business-rule enforcement are mandatory.** Hiding UI buttons is not sufficient security.

---

## User States & Permissions Matrix

| Action | Unverified Farmer | Verified Farmer | Unverified Buyer | Verified Buyer | Admin |
|---|:---:|:---:|:---:|:---:|:---:|
| Register / Login | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage own profile | ✅ | ✅ | ✅ | ✅ | — |
| Browse marketplace | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create produce listing | ❌ | ✅ | ❌ | ❌ | — |
| Post buyer requirement | ❌ | ❌ | ❌ | ✅ | — |
| Make / respond to offers | ❌ | ✅ | ❌ | ✅ | — |
| Initiate chat | ❌ | ✅ | ❌ | ✅ | — |
| Place / receive orders | ❌ | ✅ | ❌ | ✅ | — |
| Review verifications | ❌ | ❌ | ❌ | ❌ | ✅ |
| View analytics | — | ✅ | — | ✅ | ✅ |
