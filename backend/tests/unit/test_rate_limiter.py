"""Unit tests for app.middleware.rate_limiter — no real Redis or FastAPI required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _extract_identifier tests
# ---------------------------------------------------------------------------

def _make_request(headers: dict, client_host: str = "1.2.3.4"):
    req = MagicMock()
    req.headers = headers
    req.client = MagicMock()
    req.client.host = client_host
    return req


def test_extract_identifier_falls_back_to_ip_when_no_auth():
    from app.middleware.rate_limiter import _extract_identifier

    req = _make_request({}, client_host="10.0.0.1")
    identifier = _extract_identifier(req)
    assert identifier == "ip:10.0.0.1"


def test_extract_identifier_uses_forwarded_for():
    from app.middleware.rate_limiter import _extract_identifier

    req = _make_request({"x-forwarded-for": "5.6.7.8, 9.10.11.12"})
    identifier = _extract_identifier(req)
    assert identifier == "ip:5.6.7.8"


def test_extract_identifier_prefers_jwt_subject():
    from app.middleware.rate_limiter import _extract_identifier

    # decode_access_token is lazily imported inside the function;
    # patch it at the source module so the local import resolves to the mock.
    mock_decode = MagicMock(return_value={"sub": "user-uuid-123"})
    with patch("app.core.security.decode_access_token", mock_decode):
        req = _make_request({"authorization": "Bearer faketoken"})
        identifier = _extract_identifier(req)

    assert identifier == "user:user-uuid-123"


def test_extract_identifier_falls_back_if_jwt_invalid():
    from app.middleware.rate_limiter import _extract_identifier

    with patch(
        "app.core.security.decode_access_token",
        side_effect=Exception("bad token"),
    ):
        req = _make_request({"authorization": "Bearer bad"}, client_host="1.1.1.1")
        identifier = _extract_identifier(req)

    assert identifier == "ip:1.1.1.1"


# ---------------------------------------------------------------------------
# RateLimitMiddleware instantiation tests
# ---------------------------------------------------------------------------

def test_middleware_stores_limit_and_window():
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()
    with patch.object(RateLimitMiddleware, "_connect_redis", return_value=None):
        mw = RateLimitMiddleware(mock_app, requests_per_window=50, window_seconds=30)

    assert mw._limit == 50
    assert mw._window == 30


def test_middleware_redis_none_when_unavailable():
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()
    with patch("redis.from_url", side_effect=Exception("no redis")):
        mw = RateLimitMiddleware(mock_app)
    # Should not raise — redis is None (fail-open)
    assert mw._redis is None


# ---------------------------------------------------------------------------
# Exempt path tests (via dispatch logic inspection)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_path_bypasses_rate_limit():
    """Requests to /health must never be counted in Redis."""
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()
    fake_response = MagicMock()

    with patch.object(RateLimitMiddleware, "_connect_redis", return_value=MagicMock()):
        mw = RateLimitMiddleware(mock_app)

    async def fake_call_next(req):
        return fake_response

    request = MagicMock()
    request.url.path = "/health"

    result = await mw.dispatch(request, fake_call_next)
    # Redis pipeline should NOT have been called
    mw._redis.pipeline.assert_not_called()
    assert result is fake_response


@pytest.mark.asyncio
async def test_metrics_path_bypasses_rate_limit():
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()
    fake_response = MagicMock()

    with patch.object(RateLimitMiddleware, "_connect_redis", return_value=MagicMock()):
        mw = RateLimitMiddleware(mock_app)

    async def fake_call_next(req):
        return fake_response

    request = MagicMock()
    request.url.path = "/metrics"

    result = await mw.dispatch(request, fake_call_next)
    mw._redis.pipeline.assert_not_called()
    assert result is fake_response


@pytest.mark.asyncio
async def test_auth_callback_path_bypasses_rate_limit():
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()
    fake_response = MagicMock()

    with patch.object(RateLimitMiddleware, "_connect_redis", return_value=MagicMock()):
        mw = RateLimitMiddleware(mock_app)

    async def fake_call_next(req):
        return fake_response

    request = MagicMock()
    request.url.path = "/auth/callback/gmail"

    result = await mw.dispatch(request, fake_call_next)
    mw._redis.pipeline.assert_not_called()
    assert result is fake_response


@pytest.mark.asyncio
async def test_returns_429_when_limit_exceeded():
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()

    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    # Simulate count=101 (over limit of 100), ttl=45
    mock_pipe.execute.return_value = [101, 45]
    mock_redis.pipeline.return_value = mock_pipe

    with patch.object(RateLimitMiddleware, "_connect_redis", return_value=mock_redis):
        with patch("app.middleware.rate_limiter._extract_identifier", return_value="ip:1.2.3.4"):
            mw = RateLimitMiddleware(mock_app, requests_per_window=100, window_seconds=60)

    async def fake_call_next(req):
        return MagicMock()

    request = MagicMock()
    request.url.path = "/deadlines"
    request.headers = {}

    response = await mw.dispatch(request, fake_call_next)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_fail_open_on_redis_error():
    """If Redis raises an exception, the request should proceed (fail-open)."""
    from app.middleware.rate_limiter import RateLimitMiddleware

    mock_app = MagicMock()
    mock_redis = MagicMock()
    mock_redis.pipeline.side_effect = Exception("Redis gone")
    fake_response = MagicMock()

    with patch.object(RateLimitMiddleware, "_connect_redis", return_value=mock_redis):
        with patch("app.middleware.rate_limiter._extract_identifier", return_value="ip:9.9.9.9"):
            mw = RateLimitMiddleware(mock_app)

    async def fake_call_next(req):
        return fake_response

    request = MagicMock()
    request.url.path = "/deadlines"
    request.headers = {}

    result = await mw.dispatch(request, fake_call_next)
    assert result is fake_response
