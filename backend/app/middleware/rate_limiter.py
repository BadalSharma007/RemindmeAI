"""Redis token-bucket rate limiter middleware.

Implements a sliding-window counter per authenticated user (identified by JWT
``sub`` claim) and per-IP for unauthenticated endpoints.

Algorithm: fixed-window counter in Redis with TTL reset per window.
  - Window size: ``RATE_LIMIT_WINDOW_SECONDS`` (default 60 s)
  - Max requests per window: ``RATE_LIMIT_REQUESTS`` (default 100)
  - Key pattern: ``remindme:ratelimit:{identifier}``

Returns HTTP 429 with ``Retry-After`` and ``X-RateLimit-*`` headers when
the limit is exceeded.

Exempt paths (never rate-limited):
  - ``/health``
  - ``/metrics``
  - ``/auth/callback/*``   (OAuth callback — must never be blocked)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Paths that bypass rate limiting entirely
_EXEMPT_PREFIXES = ("/health", "/metrics", "/auth/callback/")


def _extract_identifier(request: Request) -> str:
    """Return a stable string key for rate-limit bucketing.

    Prefers the JWT subject (user UUID) from the Authorization header so
    authenticated users share a per-user bucket rather than a per-IP bucket.
    Falls back to ``X-Forwarded-For`` → ``client.host``.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from app.core.security import decode_access_token  # noqa: PLC0415
            token = auth[7:]
            payload = decode_access_token(token)
            return f"user:{payload['sub']}"
        except Exception:
            pass

    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return f"ip:{ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter backed by Redis.

    Parameters
    ----------
    app:
        The ASGI application.
    requests_per_window:
        Maximum requests allowed per window (default: 100).
    window_seconds:
        Window duration in seconds (default: 60).
    """

    def __init__(self, app, requests_per_window: int = 100, window_seconds: int = 60) -> None:
        super().__init__(app)
        self._limit = requests_per_window
        self._window = window_seconds
        self._redis = self._connect_redis()

    @staticmethod
    def _connect_redis():
        """Return a Redis client or None if unavailable."""
        try:
            import redis as redis_lib  # noqa: PLC0415
            from app.config import settings  # noqa: PLC0415
            return redis_lib.from_url(settings.redis_url, socket_connect_timeout=1)
        except Exception:
            return None

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Bypass exempt paths
        if any(path.startswith(pfx) for pfx in _EXEMPT_PREFIXES):
            return await call_next(request)

        # No Redis → pass through (fail-open)
        if self._redis is None:
            return await call_next(request)

        identifier = _extract_identifier(request)
        key = f"remindme:ratelimit:{identifier}"

        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            count_raw, ttl = pipe.execute()
            count = int(count_raw)

            # Set TTL on first request in window
            if count == 1:
                self._redis.expire(key, self._window)
                ttl = self._window

            remaining = max(0, self._limit - count)
            reset_at = int(time.time()) + (ttl if ttl > 0 else self._window)

            if count > self._limit:
                logger.warning("Rate limit exceeded for %s (%d/%d)", identifier, count, self._limit)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                    headers={
                        "Retry-After": str(ttl if ttl > 0 else self._window),
                        "X-RateLimit-Limit": str(self._limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self._limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_at)
            return response

        except Exception as exc:
            # Fail-open: if Redis errors, let the request through
            logger.warning("Rate limiter Redis error (fail-open): %s", exc)
            return await call_next(request)
