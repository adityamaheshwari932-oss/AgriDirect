# AgriDirect — Backend

Python 3.13 · FastAPI · PostgreSQL · SQLAlchemy 2 (synchronous) · Pydantic v2

This directory contains the AgriDirect backend service — a modular FastAPI application.

---

## Prerequisites

- Python 3.12+ installed
- Virtual environment already created at `backend/.venv`
- PostgreSQL 16+ running locally (required from Phase 1 onwards)

---

## Activate the Virtual Environment (PowerShell)

Run this from the **project root** (`AgriDirect/`):

```powershell
backend\.venv\Scripts\Activate.ps1
```

Or, if you are already inside `backend/`:

```powershell
.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your prompt once activated.

> **Note:** If PowerShell blocks script execution with a security error, you can run
> the virtual environment's Python interpreter directly without activating the script:
> ```powershell
> backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
> ```
> Alternatively, consult your organisation's PowerShell execution policy before changing it.

---

## Install / Sync Dependencies

With the virtual environment active:

```powershell
python -m pip install -r requirements.txt
```

---

## Run the API (Development)

From the `backend/` directory with the virtual environment active:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/health` | Liveness check |
| `http://127.0.0.1:8000/docs` | Swagger UI (interactive) |
| `http://127.0.0.1:8000/redoc` | ReDoc API reference |
| `http://127.0.0.1:8000/openapi.json` | Raw OpenAPI schema |

---

## Run the Tests

The test suite does **not** require a live PostgreSQL connection or the real
`.env` credentials.  Tests that need database access use an in-memory SQLite
database instead.

From the `backend/` directory with the virtual environment active:

```powershell
# Run all tests (concise output)
python -m pytest

# Run with verbose output
python -m pytest -v

# Run a specific test file
python -m pytest tests/test_health.py -v
python -m pytest tests/test_config_and_db.py -v
```

From the project root (also works, and is shown in CI examples):

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```

> **Note:** `pytest` and `httpx` must be installed. They are listed in
> `requirements.txt` under the development section.

---

## Configuration

Application settings are read from environment variables via `app/core/config.py`
(using `pydantic-settings`).

### Setting up your local `.env` file

1. Copy the template:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```
2. Open `backend/.env` and replace the placeholder values:
   - `DATABASE_URL` — use the real password for the `agridirect_app` role.
   - `SECRET_KEY` — generate a random value:
     ```powershell
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

The `.env` file is listed in `.gitignore` and will **never** be committed.
The `.env.example` template is safe to commit (it contains no real credentials).

### Required environment variables

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Runtime environment (`development`\|`testing`\|`production`) | `development` |
| `DATABASE_URL` | Full SQLAlchemy connection URL (`postgresql+psycopg://...`) | **required** |
| `SECRET_KEY` | Random string ≥ 32 chars for signing JWTs (Phase 2) | **required** |

The application refuses to start if `DATABASE_URL` or `SECRET_KEY` is missing or invalid.

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py              ← FastAPI app factory + /health endpoint
│   ├── core/
│   │   └── config.py        ← Settings via pydantic-settings (reads .env)
│   ├── db/
│   │   ├── base.py          ← Shared SQLAlchemy declarative base
│   │   └── session.py       ← Engine, sessionmaker, get_db() dependency
│   ├── api/                 ← Versioned route registrations
│   ├── models/              ← SQLAlchemy ORM model definitions (Phase 2+)
│   ├── schemas/             ← Pydantic v2 request/response schemas
│   ├── repositories/        ← Database query logic (called from services only)
│   └── services/            ← Business logic and rule enforcement
├── tests/
│   ├── test_health.py       ← Health endpoint tests (no DB required)
│   └── test_config_and_db.py ← Config and session lifecycle tests (no DB required)
├── .env.example             ← Environment variable template (safe to commit)
├── pyproject.toml           ← pytest configuration
├── requirements.txt         ← Runtime and dev/test dependencies
└── README.md                ← This file
```

---

## Current Phase

**Phase 1 — Infrastructure & Configuration** (in progress)

What is implemented:
- FastAPI application factory with `/health` endpoint
- Central settings module (`app/core/config.py`) with validation
- SQLAlchemy synchronous engine and session factory (`app/db/session.py`)
- Shared declarative base for future ORM models (`app/db/base.py`)

What is **not** implemented yet:
- Database tables and Alembic migrations (Phase 2)
- User models, authentication, or any marketplace features
- The session is wired and ready, but no route uses it yet

See [`IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md) for the full roadmap.
