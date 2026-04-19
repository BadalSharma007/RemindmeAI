"""Unit tests for app.middleware.security_headers."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_middleware(debug: bool = False):
    from app.middleware.security_headers import SecurityHeadersMiddleware
    mock_app = MagicMock()
    return SecurityHeadersMiddleware(mock_app, debug=debug)


async def _dispatch(mw, path: str = "/test") -> MagicMock:
    """Run dispatch and return the response mock."""
    response = MagicMock()
    response.headers = {}

    async def call_next(req):
        return response

    request = MagicMock()
    request.url.path = path

    return await mw.dispatch(request, call_next)


@pytest.mark.asyncio
async def test_x_content_type_options_nosniff():
    mw = _make_middleware()
    resp = await _dispatch(mw)
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_x_frame_options_deny():
    mw = _make_middleware()
    resp = await _dispatch(mw)
    assert resp.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_referrer_policy_set():
    mw = _make_middleware()
    resp = await _dispatch(mw)
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_csp_header_present():
    mw = _make_middleware()
    resp = await _dispatch(mw)
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_hsts_present_in_production():
    """HSTS must be set when debug=False (production mode)."""
    mw = _make_middleware(debug=False)
    resp = await _dispatch(mw)
    hsts = resp.headers.get("Strict-Transport-Security", "")
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


@pytest.mark.asyncio
async def test_hsts_absent_in_debug():
    """HSTS must NOT be set when debug=True (local development)."""
    mw = _make_middleware(debug=True)
    resp = await _dispatch(mw)
    assert "Strict-Transport-Security" not in resp.headers


@pytest.mark.asyncio
async def test_server_header_removed():
    mw = _make_middleware()
    response = MagicMock()
    response.headers = {"server": "uvicorn", "x-powered-by": "python"}

    async def call_next(req):
        return response

    request = MagicMock()
    await mw.dispatch(request, call_next)

    assert "server" not in response.headers
    assert "x-powered-by" not in response.headers


@pytest.mark.asyncio
async def test_permissions_policy_present():
    mw = _make_middleware()
    resp = await _dispatch(mw)
    pp = resp.headers.get("Permissions-Policy", "")
    assert "camera=()" in pp
    assert "microphone=()" in pp
