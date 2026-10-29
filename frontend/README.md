# AgriDirect — Frontend Application

Modern React 18+ and TypeScript frontend for **AgriDirect**, a B2B agricultural marketplace directly connecting farmers with commercial buyers.

---

## Technology Stack

- **Framework:** React 18.3.1 with TypeScript (strict mode)
- **Build Tool:** Vite 5.4.21 (deduped with Vitest)
- **Routing:** React Router v6
- **Styling:** Tailwind CSS v3 with custom design tokens (Forest Green primary, Harvest Amber accents)
- **Icons:** Lucide React
- **Testing:** Vitest + React Testing Library + jsdom
- **Linting:** ESLint 9 (Flat config) with TypeScript-ESLint

---

## Directory Structure

```text
frontend/
├── public/                 # Static assets (favicons, logos)
├── src/
│   ├── api/                # Centralized native Fetch API client & endpoints
│   │   ├── client.ts       # Base ApiClient, URL construction, header & error normalization
│   │   ├── auth.ts         # Authentication API (login, registerFarmer, registerBuyer, getCurrentUser)
│   │   ├── errors.ts       # Normalized ApiError class and Pydantic validation field parsing
│   │   ├── tokenStorage.ts # TokenStorage interface (InMemoryTokenStorage, SessionTokenStorage)
│   │   └── index.ts        # Module exports
│   ├── components/         # Reusable UI & layout components
│   │   ├── layout/         # Shell, navigation, footer
│   │   └── ui/             # Reusable primitives (Buttons, Cards, Inputs)
│   ├── features/           # Feature-sliced modules (auth, profile, verification)
│   ├── hooks/              # Custom React hooks
│   ├── pages/              # Route page components
│   ├── store/              # Global state management
│   │   ├── authStore.ts    # Framework-agnostic AuthStore and React useAuth() hook
│   │   └── index.ts        # Module exports
│   ├── test/               # Test setup and helpers
│   ├── types/              # Domain TypeScript types
│   │   ├── user.ts         # User, FarmerProfile, BuyerProfile, Role & Status types
│   │   ├── auth.ts         # LoginRequest, Register requests, TokenResponse
│   │   ├── api.ts          # ApiErrorResponse, ValidationErrorItem
│   │   └── index.ts        # Module exports
│   ├── utils/              # Utility helpers (cn, formatters)
│   ├── App.tsx             # Root application shell
│   ├── index.css           # Global Tailwind CSS and design tokens
│   ├── main.tsx            # Application entry point
│   └── vite-env.d.ts       # Vite client environment types
├── index.html              # HTML template
├── package.json            # Scripts and dependencies
├── tailwind.config.js      # Design tokens and theme configuration
├── tsconfig.json           # TypeScript project references
├── tsconfig.app.json       # Strict TypeScript application compiler configuration
├── tsconfig.node.json      # Strict TypeScript config compiler configuration
└── vite.config.ts          # Vite build, server proxy, and test configuration
```

---

## API Layer & Authentication Foundation

### 1. Centralized Fetch Client (`src/api/client.ts`)
- Configured with relative base `/api/v1` to seamlessly leverage the Vite local development proxy.
- Automatically handles JSON payload encoding, `Accept: application/json`, and attaches `Authorization: Bearer <token>` when an access token is available.
- Safely processes `204 No Content` responses and empty response bodies without parsing errors.
- Never logs sensitive request payloads, passwords, or authentication tokens.

### 2. Error Normalization (`src/api/errors.ts`)
- All non-2xx HTTP responses and network failures are wrapped in a strongly typed `ApiError` instance.
- Parses FastAPI / Pydantic validation errors (`422`) into a structured `fieldErrors` map (`Record<string, string[]>`) for easy form field error binding.
- Handles standard HTTP status codes (`401 Unauthorized`, `403 Forbidden`, `409 Conflict`, `429 Too Many Requests`, and `500 Server Error`).
- Status code `0` designates network reachability failures.

### 3. Authentication Store (`src/store/authStore.ts`)
- State states: `uninitialized` -> `restoring` -> `authenticated` / `unauthenticated`.
- Exposes `login(credentials)`, `registerFarmer(payload)`, `registerBuyer(payload)`, `restoreSession()`, and `logout()`.
- **Registration Separation:** Farmer and buyer registration create server accounts returning `201 Created` (`UserRead`), but do **not** automatically authenticate or issue a session. Users must explicitly log in.
- **Concurrent Request Deduplication:** Concurrent `restoreSession()` calls share the in-flight restoration promise, preventing duplicate `/users/me` requests.
- **Network Failure Resilience:** A temporary network error during session restoration sets the UI state to unauthenticated without destroying stored credentials, distinguishing between an invalid token (HTTP 401) and transient network disconnects.
- React components subscribe via the `useAuth()` hook powered by React 18's `useSyncExternalStore`.

---

## Layout Architecture & Routing (Steps 3 & 4)

### 1. Application Layouts (`src/components/layout/`)
- **`AppLayout`:** Master layout shell wrapping all public and protected pages with `PublicHeader`, dynamic `<Outlet />`, and `PublicFooter`.
- **`PublicHeader`:** Responsive navigation bar featuring AgriDirect sprout branding, marketplace announcement banner, active session indicator (displaying user role badge and email when signed in), sign out trigger, and mobile hamburger navigation drawer.
- **`PublicFooter`:** Clean platform footer with marketplace overview, compliance and regulatory notices, quick links, and active copyright statement.
- **`AuthLayout`:** Centered card layout tailored for authentication and registration flows with platform branding, back-navigation links, responsive width constraints, and accessible titles.
- **`PageContainer`:** Standardized responsive container utility supporting configurable max widths (`sm`, `default`, `lg`, `full`).

### 2. Route Configuration & Hierarchy
The application router (`src/App.tsx`) manages the following routes under `AppLayout`:

| Route | Guard | Description |
|---|---|---|
| `/` | Public | Marketplace overview and value propositions for farmers and commercial buyers |
| `/login` | `GuestOnly` | Commercial account sign in with client validation, rate limit handling, and password toggles |
| `/register` | `GuestOnly` | Role selection page directing users to role-specific registration workflows |
| `/register/farmer` | `GuestOnly` | Agricultural producer registration form (credentials, farm details, crops, land size) |
| `/register/buyer` | `GuestOnly` | Commercial buyer registration form (credentials, business entity details, business types) |
| `/dashboard` | `RequireAuth` | Role-aware landing hub redirecting farmers to `/dashboard/farmer` and buyers to `/dashboard/buyer` |
| `/dashboard/farmer` | `RequireAuth`, `RequireRole(farmer)` | Farmer dashboard with producer overview, live verification card, completion tracker, and next actions |
| `/dashboard/buyer` | `RequireAuth`, `RequireRole(buyer)` | Buyer dashboard with business overview, commercial verification card, completion tracker, and next actions |
| `/dashboard/profile` | `RequireAuth` | Account & commercial profile viewer/editor with server-field locking and role-specific updates |
| `/dashboard/verification` | `RequireAuth` | Educational verification portal displaying status lifecycle and role-specific document requirements |
| `/protected-test` | `RequireAuth` | Verification placeholder validating session gating and authenticated user state |
| `*` | Public | Accessible 404 Not Found error page with recovery link to `/` |

### 3. Route Guards & Navigation Security (`src/components/guards/`)
- **`RequireAuth`:** Inspects `useAuth()`. While status is `uninitialized` or `restoring`, displays an accessible session restoration spinner. If `unauthenticated`, redirects to `/login` preserving the attempted destination in `location.state.from`.
- **`RequireRole`:** Enforces role-based authorization for protected dashboard sections (e.g. `["farmer"]` or `["buyer"]`). If an authenticated user attempts to access a route belonging to another role, they are redirected to their appropriate role dashboard without redirect loops.
- **`GuestOnly`:** Prevents authenticated users from accessing login or registration forms, redirecting them to their prior destination or `/`.
- **Open-Redirect Protection (`src/utils/redirect.ts`):** All redirects originating from URL query parameters or location state are validated with `getSafeRedirectUrl()`. Disallows external schemes (`https://`, `http:`, `javascript:`, data URIs) and protocol-relative URLs (`//evil.com`), falling back to safe local routes.

---

## Authenticated Experience & Profile Management (Step 5)

### 1. Dashboard Layout (`src/components/layout/DashboardLayout.tsx`)
- Role-adaptive layout displaying sprout branding, portal tags, role-based navigation, verification status pill, profile dropdown, logout trigger, and responsive mobile navigation drawer.
- Shows live verification badge in the top portal bar and navigation links.

### 2. Farmer & Buyer Dashboards (`src/pages/FarmerDashboardPage.tsx`, `BuyerDashboardPage.tsx`)
- **Truthful Status Display:** Presents authentic database-backed attributes without fabricated marketplace metrics, fake order volumes, or placeholder revenue counters.
- **Verification Summary Card (`VerificationSummaryCard.tsx`):** Displays current verification status (`verified`, `pending`, `under_review`, `rejected`, `unverified`) with role-specific guidance and a direct link to the verification requirements portal.
- **Profile Completion Tracker (`ProfileCompletionCard.tsx`):** Computes profile completeness percentage across role-specific fields and surfaces clear suggestions for missing data.
- **Quick Actions:** Context-appropriate action cards guiding users to profile completion, verification preparation, and informational next steps.

### 3. Account & Profile Management (`src/pages/ProfilePage.tsx`)
- **Dual Mode Interface (View / Edit):** Seamless transition between read-only presentation and controlled form editing.
- **Server-Managed Attribute Locking:** Uneditable security attributes (Account ID, Registered Email, System Role, Verification Status, Account Status, and Timestamps) are strictly locked in both View and Edit modes with distinct visual indicators.
- **Role-Permitted Editing:**
  - Farmers can update: Full Name, Farm Name, Farm Location Address, City, State, Postal Code, Farm Size (Acres), Farming Practices, and Primary Crops.
  - Buyers can update: Contact Person Name, Business Name, Business Registration Number, Delivery Receiving Address, City, State, Postal Code, and Procurement Summary.
- **Robust Error Handling:** Detects and surfaces HTTP `409 Conflict` (duplicate phone numbers), HTTP `422 Unprocessable Entity` (Pydantic field validations), and network failures without data corruption or accidental resets.
- **Optimistic State Synchronization:** Updates global auth store state via `authStore.setUser()` upon successful profile patch responses.

### 4. Registration & Authentication Workflow
- **No Silent Auto-Login on Registration:** Aligning strictly with backend architecture, farmer and buyer registration endpoints return `201 Created` with `UserRead`. The frontend displays a dedicated confirmation screen explaining verification status (`pending`) and provides an explicit action to navigate to `/login`.
- **Form Validation & Backend Error Mapping:** Client-side validations check required fields, email formatting, minimum 8-character passwords, password matching, and positive acreage. Backend errors are mapped seamlessly:
  - `401 Unauthorized`: Displays invalid credential notice.
  - `403 Forbidden`: Displays account suspension notification.
  - `409 Conflict`: Alerts on duplicate email or phone number collisions.
  - `422 Unprocessable Entity`: Maps Pydantic field-level errors directly beneath the respective form inputs.
  - `429 Too Many Requests`: Informs user of temporary rate limit cooldown.
  - Status `0`: Displays clean network disconnect feedback without leaving the form in a disabled state.

---

## Verification System & Document Evidence Workflow (Step 6)

### 1. Verification Hub (`src/pages/VerificationPage.tsx`)
- Mounted at protected route `/dashboard/verification`. Requires authenticated session (`RequireAuth`).
- Adapts dynamically to user roles (`farmer` vs. `buyer`). Rejects unauthorized/unsupported roles.
- Back-links cleanly to the active dashboard (`/dashboard/farmer` or `/dashboard/buyer`).

### 2. Live Verification Status & Audit Lifecycle
- Consumes real backend submission state via `GET /api/v1/users/me/verification`.
- Accurately distinguishes between:
  - **Not Submitted / Unverified:** Guides user to attach evidence documents or submit application notes.
  - **Pending Review (`pending`):** Visual indicators confirming administrative review is in progress.
  - **Verified (`approved` / `verified`):** Confirms trade clearance and disables further document uploads.
  - **Rejected (`rejected`):** Displays administrative rejection rationale from backend response and invites evidence re-upload.

### 3. Document Upload Pipeline (`src/components/verification/VerificationDocumentUploadForm.tsx`)
- Formats supported: **PDF (`.pdf`), JPEG (`.jpg`, `.jpeg`), PNG (`.png`), WebP (`.webp`)**.
- Maximum file size: **10 MiB** (`10 * 1024 * 1024` bytes).
- Client-side validation validates MIME type, file extension, and file size before network transmission.
- Streams files to backend `POST /api/v1/users/me/verification/documents` via multipart `FormData` without overriding the browser-generated boundary.
- Supports role-specific document categories:
  - **Agricultural Producers:** Land Ownership Records / Title, Kisan Credit Card (KCC) / Passbook, Government Photo Identity, Organic / GAP Certifications, Other Evidence.
  - **Commercial Buyers:** GSTIN Certificate, Certificate of Incorporation / CIN, FSSAI Food Business License, Municipal Trade License, Entity PAN Card, Other Corporate Document.
- Supports optional Document / Certificate registration numbers.
- Automatic pending submission creation: Respects backend behavior where uploading an evidence document automatically creates an active pending review if none existed.

### 4. Attached Document Management & Secure Download (`src/components/verification/VerificationDocumentsList.tsx`)
- Lists attached documents with metadata (category badge, document number, MIME type, formatted file size, and upload date).
- **Secure Binary Downloads:** Integrates with `GET /api/v1/users/me/verification/documents/{document_id}/download` via `apiClient.downloadBlob()`. Downloads files as secure binary blobs via short-lived in-memory object URLs without creating public links.

### 5. Application Review Audit History (`src/components/verification/VerificationHistoryList.tsx`)
- Fetches reverse-chronological submission records from `GET /api/v1/users/me/verification/history`.
- Displays submission timestamps, administrative review dates, status transitions, applicant notes, and past rejection feedback.

---

## Token Storage Architecture & Known Limitations

### Current Backend State
- The backend authentication service (`POST /api/v1/auth/login`) issues a signed JWT access token (`access_token`, `token_type: "bearer"`, lifetime: 60 minutes).
- The backend does **not** currently implement a refresh token endpoint (`/api/v1/auth/refresh`), nor does it set `HttpOnly` session cookies.

### Storage Implementations
1. **`InMemoryTokenStorage`:**
   - Stores the access token in private memory closure.
   - **Advantage:** Maximum security against cross-site scripting (XSS) persistence; storage cannot be accessed via `window.localStorage` or `window.sessionStorage`.
   - **Trade-off:** Does not survive a page refresh; reloading the tab resets the session.
2. **`SessionTokenStorage` (Active Default for Development):**
   - Stores the token in `window.sessionStorage` under `agridirect_access_token`.
   - **Advantage:** Allows session restoration across page reloads within the same browser tab during local development and testing.
   - **Trade-off:** Clears automatically when the tab is closed, but remains accessible to JavaScript, carrying XSS exposure risks.

### Production Recommendation
When Phase 13 (Hardening & Security Audit) is implemented, the backend should introduce an `HttpOnly`, `SameSite=Strict` cookie for refresh tokens alongside short-lived access tokens, completely removing tokens from JavaScript-accessible browser storage.

---

## Getting Started

### Prerequisites

- Node.js `v20+` (tested on `v24.22.0`)
- npm `10+` (tested on `11.19.1`)

### Installation

From the `frontend/` directory:

```bash
npm install
```

### Local Development

Start the Vite development server:

```bash
npm run dev
```

The application will start at **http://localhost:5173**.
- Port `5173` is strictly enforced (`strictPort: true`) to match backend CORS settings.
- Requests to `/api/v1` are automatically proxied to the backend at `http://127.0.0.1:8000`.

### Running Tests

Execute the Vitest test suite:

```bash
npm run test
```

For watch mode during development:

```bash
npm run test:watch
```

### Linting

Check for TypeScript and React code standard issues:

```bash
npm run lint
```

### Production Build

Type-check and bundle the application for production:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```
