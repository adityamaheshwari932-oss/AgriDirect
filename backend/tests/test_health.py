"""Tests for the /health endpoint.

These tests use FastAPI's synchronous TestClient (backed by httpx) and
require no database or external services to be running.

Run with:
    python -m pytest backend/tests/test_health.py -v
or from the backend/ directory:
    python -m pytest tests/test_health.py -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Provide a reusable TestClient for the FastAPI application.

    The client is created once per test module and shared across all tests
    in this file, avoiding repeated app initialisation overhead.

    Returns:
        A configured TestClient bound to the AgriDirect FastAPI application.
    """
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """GET /health must respond with HTTP 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200, (
            f"Expected HTTP 200, got {response.status_code}. Body: {response.text}"
        )

    def test_health_returns_json_content_type(self, client: TestClient) -> None:
        """GET /health must respond with a JSON content-type header."""
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", ""), (
            f"Expected application/json content-type, got: {response.headers.get('content-type')}"
        )

    def test_health_response_body(self, client: TestClient) -> None:
        """GET /health must return exactly {\"status\": \"ok\"}."""
        response = client.get("/health")
        body = response.json()
        assert body == {"status": "ok"}, (
            f"Unexpected response body: {body}"
        )

    def test_health_status_key_is_ok(self, client: TestClient) -> None:
        """The 'status' field in the health response must be the string 'ok'."""
        response = client.get("/health")
        assert response.json().get("status") == "ok"
