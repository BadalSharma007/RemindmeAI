"""Security headers middleware.

Adds industry-standard HTTP security headers to every response:

  Strict-Transport-Security  — enforce HTTPS for 1 year (includeSubDomains)
  X-Content-Type-Options     — prevent MIME sniffing
  X-Frame-Options            — block clickjacking
  X-XSS-Protection           — legacy browser XSS filter (belt-and-suspenders)
  Referrer-Policy            — limit referrer leakage
  Permissions-Policy         — disable unused browser APIs
  Content-Security-Policy    — restrict resource origins

The CSP is intentionally strict.  Adjust ``ALLOWED_ORIGINS`` in config if your
frontend is served from a non-localhost domain.

Note: ``Strict-Transport-Security`` is only emitted in non-debug mode so that
local HTTP dev isn't pinned to HTTPS accidentally.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# CSP directives — ``'self'`` covers API responses; frontend assets served
# separately via CDN should add their origins here.
_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

_PERMISSIONS = (
    "camera=(), microphone=(), geolocation=(), payment=(), "
    "usb=(), interest-cohort=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attaches security headers to every HTTP response.

    Parameters
    ----------
    debug:
        When ``True``, ``Strict-Transport-Security`` is omitted so that local
        development over plain HTTP works without browser HSTS pinning issues.
    """

    def __init__(self, app, debug: bool = False) -> None:
        super().__init__(app)
        self._debug = debug

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = _PERMISSIONS
        response.headers["Content-Security-Policy"] = _CSP

        # Only send HSTS in production (not over plain HTTP in dev)
        if not self._debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Remove server fingerprinting headers
        response.headers.__delitem__("server") if "server" in response.headers else None
        response.headers.__delitem__("x-powered-by") if "x-powered-by" in response.headers else None

        return response
