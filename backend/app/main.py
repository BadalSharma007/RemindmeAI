from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging_config import configure_logging
from app.routers import auth, deadlines, notifications, preferences, reminders, stats, subscriptions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    logger.info("RemindmeAI starting up (version=4.0.0)")

    # Verify DB connectivity
    try:
        from app.database import init_db
        await init_db()
    except Exception as exc:
        logger.warning("DB not available at startup: %s", exc)

    yield
    logger.info("RemindmeAI shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Intelligent Email-Based Reminder System",
        version="4.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- Middleware stack (order matters: outermost added last) ---

    # Phase 4: Security headers
    from app.middleware.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware, debug=settings.debug)

    # Phase 4: Rate limiting (Redis token bucket)
    from app.middleware.rate_limiter import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    # Phase 4: Prometheus metrics collection
    from app.core.metrics import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)

    # CORS (innermost — applied first on request, last on response)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    app.include_router(auth.router)
    app.include_router(deadlines.router)
    app.include_router(reminders.router)
    app.include_router(preferences.router)
    app.include_router(subscriptions.router)
    app.include_router(stats.router)
    app.include_router(notifications.router)

    # --- Built-in endpoints ---

    @app.get("/health", tags=["ops"])
    async def health_check() -> dict:
        return {"status": "ok", "service": settings.app_name, "version": "4.0.0"}

    @app.get("/health/live", tags=["ops"])
    async def liveness_check() -> dict:
        """Kubernetes liveness probe — is the process alive?"""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["ops"])
    async def readiness_check() -> dict:
        """Deep readiness check: DB + Redis + RabbitMQ connectivity."""
        checks: dict[str, str] = {}

        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"

        try:
            import redis as redis_lib
            r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=1)
            r.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        try:
            broker_url = settings.rabbitmq_url or settings.celery_broker_url
            if broker_url.startswith("amqp"):
                import pika
                params = pika.URLParameters(broker_url)
                params.socket_timeout = 2
                conn = pika.BlockingConnection(params)
                conn.close()
                checks["rabbitmq"] = "ok"
            else:
                checks["rabbitmq"] = "skipped (redis broker)"
        except Exception as exc:
            checks["rabbitmq"] = f"error: {exc}"

        all_ok = all(v in ("ok", "skipped (redis broker)") for v in checks.values())
        status_code = 200 if all_ok else 503
        return JSONResponse(
            content={"status": "ready" if all_ok else "degraded", "checks": checks},
            status_code=status_code,
        )

    # Phase 4: Prometheus metrics endpoint
    from app.core.metrics import metrics_endpoint
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])

    @app.get("/", tags=["ops"])
    async def api_root() -> dict:
        return {"service": settings.app_name, "docs": "/docs", "health": "/health"}

    return app


app = create_app()
