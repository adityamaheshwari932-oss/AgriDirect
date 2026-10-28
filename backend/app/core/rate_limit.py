"""In-memory sliding window rate limiter for sensitive authentication endpoints.

Architecture & Security Notes:
------------------------------
- Process-local, in-memory implementation suitable for single-instance or dev deployments.
- Resets on application restart; for distributed multi-instance production environments,
  a centralized Redis-backed store or reverse-proxy rate limiting (e.g. Nginx, Cloudflare)
  is recommended.
- Resolves client IP securely: prevents client IP spoofing by refusing to trust arbitrary
  X-Forwarded-For headers unless explicitly enabled or behind trusted reverse proxies.
- Enforces HTTP 429 Too Many Requests with a compliant Retry-After header.
"""

import math
import threading
import time
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class InMemoryRateLimiter:
    """Thread-safe, sliding-window in-memory rate limiter.

    Tracks timestamps of requests keyed by client identifier (e.g. IP address).
    Expired entries outside the sliding window are pruned on each check.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempts: Dict[str, List[float]] = {}

    def is_allowed(
        self,
        key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """Check if request is within rate limit and record the attempt if allowed.

        Args:
            key: Unique client identifier (e.g. client IP).
            max_attempts: Maximum allowed requests in the sliding window.
            window_seconds: Sliding window duration in seconds.

        Returns:
            Tuple of (is_allowed: bool, retry_after: int seconds).
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            history = self._attempts.get(key, [])
            # Prune attempts outside the sliding window
            valid_history = [t for t in history if t > cutoff]

            if len(valid_history) >= max_attempts:
                # Compute remaining wait time until the oldest recorded attempt expires
                oldest = valid_history[0]
                retry_after = max(1, math.ceil(oldest + window_seconds - now))
                self._attempts[key] = valid_history
                return False, retry_after

            # Record this attempt
            valid_history.append(now)
            self._attempts[key] = valid_history
            return True, 0

    def clear(self) -> None:
        """Reset all rate limiting state. Intended for test isolation."""
        with self._lock:
            self._attempts.clear()


# Global singleton instance for login rate limiting
login_rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request, trusted_proxies: Optional[List[str]] = None) -> str:
    """Resolve client IP address securely.

    To prevent header injection and IP spoofing:
    - Never blindly trust X-Forwarded-For from untrusted remote clients.
    - Only parse forwarded headers if the immediate peer (request.client.host)
      matches a configured trusted proxy IP.

    Args:
        request: The incoming FastAPI/Starlette request.
        trusted_proxies: Optional list of trusted proxy IP addresses.

    Returns:
        The resolved client IP string, or '127.0.0.1' fallback.
    """
    client_host = request.client.host if request.client else "127.0.0.1"

    if trusted_proxies and client_host in trusted_proxies:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Client IP is the leftmost address in X-Forwarded-For chain
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip

    return client_host


def check_login_rate_limit(request: Request) -> None:
    """FastAPI dependency to rate limit login attempts.

    Args:
        request: Current HTTP request.

    Raises:
        HTTPException: 429 Too Many Requests if the limit is exceeded.
    """
    settings = get_settings()

    if not getattr(settings, "enable_auth_rate_limit", True):
        return

    max_attempts = getattr(settings, "auth_rate_limit_max_attempts", 5)
    window_seconds = getattr(settings, "auth_rate_limit_window_seconds", 60)

    client_ip = get_client_ip(request)
    allowed, retry_after = login_rate_limiter.is_allowed(
        key=client_ip,
        max_attempts=max_attempts,
        window_seconds=window_seconds,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

