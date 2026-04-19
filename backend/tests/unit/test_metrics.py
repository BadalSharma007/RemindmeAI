"""Unit tests for app.core.metrics — Prometheus helpers and middleware."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: ensure prometheus_client is available
# ---------------------------------------------------------------------------

def _skip_if_no_prometheus():
    try:
        import prometheus_client  # noqa: F401
    except ImportError:
        pytest.skip("prometheus_client not installed")


# ---------------------------------------------------------------------------
# Public helper function tests
# ---------------------------------------------------------------------------

def test_inc_emails_processed_does_not_raise():
    from app.core.metrics import inc_emails_processed
    # Should never raise regardless of prometheus availability
    inc_emails_processed("gmail")
    inc_emails_processed("outlook")


def test_inc_deadlines_created_does_not_raise():
    from app.core.metrics import inc_deadlines_created
    inc_deadlines_created(1)
    inc_deadlines_created(2)


def test_inc_spam_detected_does_not_raise():
    from app.core.metrics import inc_spam_detected
    inc_spam_detected()


def test_inc_reminders_sent_does_not_raise():
    from app.core.metrics import inc_reminders_sent
    inc_reminders_sent("email")
    inc_reminders_sent("push")


def test_set_active_connections_does_not_raise():
    from app.core.metrics import set_active_connections
    set_active_connections("gmail", 5)
    set_active_connections("outlook", 0)


def test_inc_circuit_open_does_not_raise():
    from app.core.metrics import inc_circuit_open
    inc_circuit_open("gmail_api")


def test_observe_nlp_duration_does_not_raise():
    from app.core.metrics import observe_nlp_duration
    observe_nlp_duration(1.234)


# ---------------------------------------------------------------------------
# metrics_endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_endpoint_returns_503_when_prometheus_unavailable():
    with patch("app.core.metrics._PROMETHEUS_AVAILABLE", False):
        from app.core.metrics import metrics_endpoint
        request = MagicMock()
        response = await metrics_endpoint(request)
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200_when_prometheus_available():
    _skip_if_no_prometheus()

    from app.core.metrics import metrics_endpoint, _PROMETHEUS_AVAILABLE
    if not _PROMETHEUS_AVAILABLE:
        pytest.skip("prometheus_client not available")

    request = MagicMock()
    response = await metrics_endpoint(request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_content_type_prometheus():
    _skip_if_no_prometheus()
    from app.core.metrics import metrics_endpoint, _PROMETHEUS_AVAILABLE
    if not _PROMETHEUS_AVAILABLE:
        pytest.skip("prometheus_client not available")

    request = MagicMock()
    response = await metrics_endpoint(request)
    assert "text/plain" in response.media_type or "prometheus" in response.media_type


# ---------------------------------------------------------------------------
# PrometheusMiddleware tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prometheus_middleware_passes_through_when_unavailable():
    """When prometheus_client is absent, middleware is transparent."""
    from app.middleware.security_headers import SecurityHeadersMiddleware

    fake_response = MagicMock()

    with patch("app.core.metrics._PROMETHEUS_AVAILABLE", False):
        from app.core.metrics import PrometheusMiddleware
        mock_app = MagicMock()
        mw = PrometheusMiddleware(mock_app)

        async def call_next(req):
            return fake_response

        request = MagicMock()
        request.app.routes = []
        request.url.path = "/deadlines"
        request.method = "GET"

        result = await mw.dispatch(request, call_next)

    assert result is fake_response


def test_get_path_template_returns_raw_path_when_no_match():
    from app.core.metrics import PrometheusMiddleware

    request = MagicMock()
    request.app.routes = []
    request.url.path = "/unknown/route"
    request.scope = {}

    path = PrometheusMiddleware._get_path_template(request)
    assert path == "/unknown/route"
