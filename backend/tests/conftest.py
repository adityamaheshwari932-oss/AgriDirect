"""Global pytest fixtures and test suite configuration."""

import pytest

from app.core.rate_limit import login_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the global in-memory rate limiter before and after each test."""
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()

