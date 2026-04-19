"""Event bus — decouple ingestion from NLP via Celery task routing.

Publishing an email to the bus sends a ``process_email_nlp`` Celery task
to the dedicated ``nlp`` queue.  With Redis as broker this is a simple
Redis list; swap in RabbitMQ by changing ``CELERY_BROKER_URL`` — no code
changes required.

Usage::

    from app.services.events.bus import publish_email_for_nlp
    await publish_email_for_nlp(email_id=row.id)

The NLP processor (``nlp/processor.py``) picks up the task from the queue,
loads the email from the DB, and runs the full spam → classify → extract →
calendar → schedule pipeline.
"""
from __future__ import annotations

import logging
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

# Celery task name — must match the @celery_app.task(name=...) in processor.py
_NLP_TASK_NAME = "app.services.nlp.processor.process_email_nlp"
_NLP_QUEUE = "nlp"


def publish_email_for_nlp(email_id: uuid.UUID | str | int) -> str:
    """Publish an ``ExtractedEmail`` ID to the NLP queue.

    Returns the Celery async-result ID (str) for optional tracking.

    Parameters
    ----------
    email_id:
        Primary key of the ``ExtractedEmail`` row.  Passed as the first
        positional argument to ``process_email_nlp``.
    """
    result = celery_app.send_task(
        _NLP_TASK_NAME,
        args=[str(email_id)],
        queue=_NLP_QUEUE,
    )
    logger.debug(
        "Published email %s to NLP queue (task_id=%s)", email_id, result.id
    )
    return result.id


class EventBus:
    """Thin wrapper around ``publish_email_for_nlp`` for dependency injection
    and easier mocking in tests."""

    def publish_email(self, email_id: uuid.UUID | str | int) -> str:
        return publish_email_for_nlp(email_id)
