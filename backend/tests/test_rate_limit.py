"""Comprehensive tests for authentication rate limiting:
- Unit tests for InMemoryRateLimiter and get_client_ip
- Integration tests for POST /api/v1/auth/login rate limiting behavior
- Header injection / IP spoofing protection tests
"""

import threading
import time
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip, login_rate_limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(autouse=True)
def clean_rate_limiter():
    """Ensure the global rate limiter is cleared before and after each test."""
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database supporting multi-threaded access."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(sqlite_engine) -> TestClient:
    """Provide a TestClient with overridden get_db dependency."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ===========================================================================
# Unit Tests: InMemoryRateLimiter
# ===========================================================================


class TestInMemoryRateLimiter:
    """Unit tests for the thread-safe in-memory sliding window rate limiter."""

    def test_allows_attempts_up_to_limit(self) -> None:
        limiter = InMemoryRateLimiter()
        key = "192.168.1.100"

        for _ in range(5):
            allowed, retry_after = limiter.is_allowed(key, max_attempts=5, window_seconds=60)
            assert allowed is True
            assert retry_after == 0

    def test_blocks_attempt_exceeding_limit(self) -> None:
        limiter = InMemoryRateLimiter()
        key = "192.168.1.100"

        for _ in range(5):
            limiter.is_allowed(key, max_attempts=5, window_seconds=60)

        # 6th attempt must be rejected with positive retry_after
        allowed, retry_after = limiter.is_allowed(key, max_attempts=5, window_seconds=60)
        assert allowed is False
        assert 1 <= retry_after <= 60

    def test_keys_are_isolated(self) -> None:
        limiter = InMemoryRateLimiter()
        key1 = "10.0.0.1"
        key2 = "10.0.0.2"

        # Exhaust key1
        for _ in range(3):
            limiter.is_allowed(key1, max_attempts=3, window_seconds=60)

        assert limiter.is_allowed(key1, max_attempts=3, window_seconds=60)[0] is False
        # key2 is completely unaffected
        assert limiter.is_allowed(key2, max_attempts=3, window_seconds=60)[0] is True

    def test_sliding_window_prunes_old_attempts(self) -> None:
        limiter = InMemoryRateLimiter()
        key = "10.0.0.5"

        # Record attempt with short window of 0 seconds (simulating expired)
        limiter.is_allowed(key, max_attempts=1, window_seconds=1)
        # Sleep slightly so window expires
        time.sleep(1.05)

        # Next attempt should be allowed because previous attempt fell out of window
        allowed, _ = limiter.is_allowed(key, max_attempts=1, window_seconds=1)
        assert allowed is True

    def test_clear_resets_history(self) -> None:
        limiter = InMemoryRateLimiter()
        key = "10.0.0.9"

        for _ in range(3):
            limiter.is_allowed(key, max_attempts=3, window_seconds=60)
        assert limiter.is_allowed(key, max_attempts=3, window_seconds=60)[0] is False

        limiter.clear()
        assert limiter.is_allowed(key, max_attempts=3, window_seconds=60)[0] is True

    def test_thread_safety_under_concurrency(self) -> None:
        limiter = InMemoryRateLimiter()
        key = "concurrent_client"
        results = []

        def worker():
            for _ in range(10):
                allowed, _ = limiter.is_allowed(key, max_attempts=25, window_seconds=60)
                results.append(allowed)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 25 should have succeeded, 25 failed
        assert results.count(True) == 25
        assert results.count(False) == 25


# ===========================================================================
# Unit Tests: get_client_ip
# ===========================================================================


class TestGetClientIp:
    """Tests for secure client IP address resolution."""

    def test_direct_client_ip(self) -> None:
        request = MagicMock(spec=Request)
        request.client.host = "203.0.113.195"
        request.headers = {}

        ip = get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_fallback_when_client_is_none(self) -> None:
        request = MagicMock(spec=Request)
        request.client = None
        request.headers = {}

        ip = get_client_ip(request)
        assert ip == "127.0.0.1"

    def test_ignores_spoofed_forwarded_for_from_untrusted_client(self) -> None:
        request = MagicMock(spec=Request)
        request.client.host = "198.51.100.5"  # Direct caller
        # Attacker injects fake header to try to blame another IP or bypass rate limits
        request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}

        ip = get_client_ip(request, trusted_proxies=None)
        assert ip == "198.51.100.5"

    def test_honors_forwarded_for_when_client_is_trusted_proxy(self) -> None:
        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"  # Local Nginx reverse proxy
        request.headers = {"x-forwarded-for": "203.0.113.50, 127.0.0.1"}

        ip = get_client_ip(request, trusted_proxies=["127.0.0.1"])
        assert ip == "203.0.113.50"


# ===========================================================================
# Integration Tests: /api/v1/auth/login Rate Limiting
# ===========================================================================


class TestLoginRateLimitingApi:
    """Integration tests verifying HTTP 429 and Retry-After on POST /api/v1/auth/login."""

    def test_login_attempts_within_limit_do_not_return_429(self, client: TestClient) -> None:
        settings = get_settings()
        limit = settings.auth_rate_limit_max_attempts

        # Attempts with invalid credentials return 401, not 429
        for _ in range(limit):
            res = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "WrongPassword123!"},
            )
            assert res.status_code == 401

    def test_login_attempt_exceeding_limit_returns_429(self, client: TestClient) -> None:
        settings = get_settings()
        limit = settings.auth_rate_limit_max_attempts

        # Exhaust limit
        for _ in range(limit):
            client.post(
                "/api/v1/auth/login",
                json={"email": "attacker@example.com", "password": "WrongPassword123!"},
            )

        # Next request must be rate limited
        blocked_res = client.post(
            "/api/v1/auth/login",
            json={"email": "attacker@example.com", "password": "WrongPassword123!"},
        )
        assert blocked_res.status_code == 429
        assert "Too many login attempts" in blocked_res.json()["detail"]
        assert "Retry-After" in blocked_res.headers
        retry_after = int(blocked_res.headers["Retry-After"])
        assert retry_after >= 1

    def test_rate_limiting_is_scoped_per_client_ip(self, client: TestClient) -> None:
        settings = get_settings()
        limit = settings.auth_rate_limit_max_attempts

        # Pre-seed the rate limiter to exhaust one IP
        for _ in range(limit):
            login_rate_limiter.is_allowed(
                key="192.168.1.50",
                max_attempts=limit,
                window_seconds=60,
            )

        # A request from default TestClient IP (testclient) is unaffected
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "WrongPassword123!"},
        )
        assert res.status_code == 401  # Not 429!

