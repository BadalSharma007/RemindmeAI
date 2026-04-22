"""Prometheus metrics for RemindmeAI.

Exposes application-level counters, histograms, and gauges consumed by
Prometheus.  Metrics are served at ``GET /metrics`` (unauthenticated — restrict
at the Kubernetes NetworkPolicy / Kong plugin level in production).

Middleware
----------
``PrometheusMiddleware`` wraps every HTTP request:
  - Increments ``http_requests_total{method, path, status_code}``
  - Records ``http_request_duration_seconds{method, path}`` histogram

Business metrics
----------------
Call the helper functions from service code:

    from app.core.metrics import (
        inc_emails_processed,
        inc_deadlines_created,
        inc_spam_detected,
        inc_reminders_sent,
        set_active_connections,
    )
"""
from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        REGISTRY,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Metric definitions (only created when prometheus_client is installed)
# ---------------------------------------------------------------------------

if _PROMETHEUS_AVAILABLE:
    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status_code"],
    )

    HTTP_REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    EMAILS_PROCESSED = Counter(
        "remindme_emails_processed_total",
        "Emails processed through the NLP pipeline",
        ["provider"],  # "gmail" | "outlook"
    )

    DEADLINES_CREATED = Counter(
        "remindme_deadlines_created_total",
        "Deadline rows created",
        ["classifier_tier"],  # "1" | "2"
    )

    SPAM_DETECTED = Counter(
        "remindme_spam_detected_total",
        "Emails classified as spam/marketing",
    )

    REMINDERS_SENT = Counter(
        "remindme_reminders_sent_total",
        "Reminders dispatched",
        ["channel"],  # "email" | "push"
    )

    ACTIVE_CONNECTIONS = Gauge(
        "remindme_active_email_connections",
        "Currently active OAuth email connections",
        ["provider"],
    )

    CIRCUIT_BREAKER_OPEN = Counter(
        "remindme_circuit_breaker_open_total",
        "Number of times a circuit breaker transitioned to OPEN",
        ["circuit_name"],
    )

    NLP_PROCESSING_DURATION = Histogram(
        "remindme_nlp_processing_duration_seconds",
        "Time taken by the NLP processor task",
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 15.0, 30.0, 60.0),
    )

    GEMINI_CALLS = Counter(
        "remindme_gemini_api_calls_total",
        "Gemini API calls made by the LangGraph agent",
        ["node", "status"],  # node: classify|extract_dates|resolve_dates, status: success|error|rate_limited
    )

    GEMINI_LATENCY = Histogram(
        "remindme_gemini_api_latency_seconds",
        "Gemini API response time per node",
        ["node"],
        buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
    )


# ---------------------------------------------------------------------------
# Public helpers — safe to call whether or not prometheus_client is installed
# ---------------------------------------------------------------------------

def inc_emails_processed(provider: str = "gmail") -> None:
    if _PROMETHEUS_AVAILABLE:
        EMAILS_PROCESSED.labels(provider=provider).inc()


def inc_deadlines_created(tier: int = 1) -> None:
    if _PROMETHEUS_AVAILABLE:
        DEADLINES_CREATED.labels(classifier_tier=str(tier)).inc()


def inc_spam_detected() -> None:
    if _PROMETHEUS_AVAILABLE:
        SPAM_DETECTED.inc()


def inc_reminders_sent(channel: str = "email") -> None:
    if _PROMETHEUS_AVAILABLE:
        REMINDERS_SENT.labels(channel=channel).inc()


def set_active_connections(provider: str, count: int) -> None:
    if _PROMETHEUS_AVAILABLE:
        ACTIVE_CONNECTIONS.labels(provider=provider).set(count)


def inc_circuit_open(name: str) -> None:
    if _PROMETHEUS_AVAILABLE:
        CIRCUIT_BREAKER_OPEN.labels(circuit_name=name).inc()


def observe_nlp_duration(seconds: float) -> None:
    if _PROMETHEUS_AVAILABLE:
        NLP_PROCESSING_DURATION.observe(seconds)


def inc_gemini_call(node: str, status: str = "success") -> None:
    if _PROMETHEUS_AVAILABLE:
        GEMINI_CALLS.labels(node=node, status=status).inc()


def observe_gemini_latency(node: str, seconds: float) -> None:
    if _PROMETHEUS_AVAILABLE:
        GEMINI_LATENCY.labels(node=node).observe(seconds)


# ---------------------------------------------------------------------------
# Starlette middleware
# ---------------------------------------------------------------------------

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Records per-route request count and latency for every HTTP call."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not _PROMETHEUS_AVAILABLE:
            return await call_next(request)

        # Resolve the matched route template (e.g. /deadlines/{id} not /deadlines/abc)
        path = self._get_path_template(request)
        method = request.method

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        HTTP_REQUESTS_TOTAL.labels(
            method=method, path=path, status_code=str(response.status_code)
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration)

        return response

    @staticmethod
    def _get_path_template(request: Request) -> str:
        """Return the route template string, falling back to raw path."""
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return getattr(route, "path", request.url.path)
        return request.url.path


# ---------------------------------------------------------------------------
# /metrics endpoint handler
# ---------------------------------------------------------------------------

async def metrics_endpoint(request: Request) -> Response:
    """FastAPI route handler: ``GET /metrics``."""
    if not _PROMETHEUS_AVAILABLE:
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain",
            status_code=503,
        )
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
