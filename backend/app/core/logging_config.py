"""Structured JSON logging configuration for RemindmeAI.

Replaces the default plaintext log format with machine-parseable JSON lines,
compatible with Datadog, Loki, CloudWatch, and any log aggregator that
understands JSON.

Each log record includes:
  timestamp  — ISO-8601 UTC
  level      — DEBUG / INFO / WARNING / ERROR / CRITICAL
  logger     — module path (e.g. "app.services.ingestion.gmail_poller")
  message    — human-readable message
  service    — "remindmeai" (for log router filtering)
  *extra*    — any keyword args passed to the logger call

Usage::

    from app.core.logging_config import configure_logging
    configure_logging(level="INFO", json=True)

In ``main.py`` call once during app startup.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    SERVICE = "remindmeai"

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.SERVICE,
        }

        # Include exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Merge any extra fields passed via logger.info("msg", extra={...})
        skip = logging.LogRecord.__dict__.keys() | {
            "message", "asctime", "msg", "args", "exc_info",
            "exc_text", "stack_info",
        }
        for key, value in record.__dict__.items():
            if key not in skip:
                try:
                    json.dumps(value)  # Only include JSON-serialisable extras
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = str(value)

        return json.dumps(payload, ensure_ascii=False)


class _PlainFormatter(logging.Formatter):
    """Human-friendly formatter for local development."""

    FMT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self.FMT, datefmt=self.DATEFMT)


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
    suppress_noisy_loggers: bool = True,
) -> None:
    """Configure the root logger.

    Parameters
    ----------
    level:
        Log level for the root logger (default: ``"INFO"``).
    json_output:
        If ``True``, use JSON formatter (production).
        If ``False``, use human-readable formatter (dev).
    suppress_noisy_loggers:
        Silence chatty third-party loggers (``uvicorn.access``,
        ``sqlalchemy.engine``, ``httpx``) at WARNING level.
    """
    formatter = _JsonFormatter() if json_output else _PlainFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any pre-existing handlers (e.g. from pytest)
    root.handlers.clear()
    root.addHandler(handler)

    if suppress_noisy_loggers:
        for name in (
            "uvicorn.access",
            "sqlalchemy.engine",
            "sqlalchemy.pool",
            "httpx",
            "httpcore",
            "multipart",
        ):
            logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("app").setLevel(getattr(logging, level.upper(), logging.INFO))
