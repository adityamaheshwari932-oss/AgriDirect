"""AgriDirect API — FastAPI application factory.

This module creates and configures the FastAPI application instance.
Business feature modules are registered here as the project grows.

Architecture notes (from AGENTS.md):
- All API routes are versioned under /api/v1/
- CORS is explicitly configured; wildcard origins are forbidden in production
- Business logic lives in service modules, not in route handlers
- Database connectivity is established in app/db/session.py (Phase 1)
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db.session import close_db, init_db

# ---------------------------------------------------------------------------
# Lifespan context manager
# Startup and shutdown logic goes here as the application grows.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None — control passes to the running application.
    """
    try:
        # --- Startup ---
        init_db()
        yield
    finally:
        # --- Shutdown ---
        close_db()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title="AgriDirect API",
        summary="B2B agricultural marketplace connecting farmers with commercial buyers.",
        description=(
            "AgriDirect facilitates direct trade between verified farmers and commercial buyers. "
            "It does not own produce, process payments, or manage physical logistics.\n\n"
            "All endpoints that modify state require authentication. "
            "Business-rule enforcement is performed server-side; client-side guards are "
            "supplementary UX only."
        ),
        version="0.1.0",
        # OpenAPI docs are available in development; disable in production via env var (Phase 1).
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS — explicitly configured.
    # Wildcard origins are permitted here only for local development.
    # Phase 1 will replace this with origins read from environment variables.
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Core routes (defined inline — no business logic)
    # -----------------------------------------------------------------------
    _register_core_routes(app)

    # -----------------------------------------------------------------------
    # Feature routers — registered here as each phase is implemented.
    # -----------------------------------------------------------------------
    from app.admin.routes import router as admin_router
    from app.analytics.routes import router as analytics_router
    from app.auth.routes import router as auth_router
    from app.chat.routes import router as chat_router
    from app.listings.routes import router as listings_router
    from app.notifications.routes import router as notifications_router
    from app.offers.routes import router as offers_router
    from app.orders.routes import router as orders_router
    from app.payments.routes import router as payments_router
    from app.reports.routes import router as reports_router
    from app.requirements.routes import router as requirements_router
    from app.reviews.routes import router as reviews_router
    from app.transporters.routes import router as transporters_router
    from app.users.routes import router as users_router
    from app.verification.routes import router as verification_router

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(transporters_router, prefix="/api/v1")
    app.include_router(listings_router, prefix="/api/v1")
    app.include_router(requirements_router, prefix="/api/v1")
    app.include_router(offers_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(verification_router, prefix="/api/v1")
    app.include_router(reviews_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")

    return app


def _register_core_routes(app: FastAPI) -> None:
    """Register core infrastructure routes on the application.

    Args:
        app: The FastAPI application instance.
    """

    @app.get(
        "/health",
        summary="API health check",
        description=(
            "Returns a simple liveness signal for the API process. "
            "Does **not** verify database connectivity at this stage."
        ),
        tags=["infrastructure"],
        response_class=JSONResponse,
    )
    async def health_check() -> dict[str, str]:
        """Return a liveness signal indicating the API process is running.

        Returns:
            A dict with a single ``status`` key set to ``"ok"``.
        """
        return {"status": "ok"}


# ---------------------------------------------------------------------------
# Application instance
# Uvicorn and tests both import this directly:
#   uvicorn app.main:app --reload
# ---------------------------------------------------------------------------

app: FastAPI = create_app()
