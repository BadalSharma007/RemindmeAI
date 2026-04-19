"""Unit tests for app.services.events.bus — no Celery/broker required."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.events.bus import EventBus, publish_email_for_nlp


_EMAIL_ID = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
_TASK_ID = "celery-task-abc-456"


def _mock_celery_app():
    mock_result = MagicMock()
    mock_result.id = _TASK_ID

    mock_app = MagicMock()
    mock_app.send_task.return_value = mock_result
    return mock_app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_publish_email_calls_send_task():
    mock_app = _mock_celery_app()
    with patch("app.services.events.bus.celery_app", mock_app):
        publish_email_for_nlp(_EMAIL_ID)

    mock_app.send_task.assert_called_once()
    call_kwargs = mock_app.send_task.call_args
    task_name = call_kwargs[0][0]
    task_args = call_kwargs[1].get("args", [])
    assert task_name == "app.services.nlp.processor.process_email_nlp"
    assert str(_EMAIL_ID) in task_args


def test_publish_email_returns_task_id():
    mock_app = _mock_celery_app()
    with patch("app.services.events.bus.celery_app", mock_app):
        task_id = publish_email_for_nlp(_EMAIL_ID)
    assert task_id == _TASK_ID


def test_publish_email_accepts_string_id():
    mock_app = _mock_celery_app()
    with patch("app.services.events.bus.celery_app", mock_app):
        publish_email_for_nlp("some-string-id")
    mock_app.send_task.assert_called_once()


def test_event_bus_class_delegates_to_publish():
    mock_app = _mock_celery_app()
    with patch("app.services.events.bus.celery_app", mock_app):
        bus = EventBus()
        task_id = bus.publish_email(_EMAIL_ID)
    assert task_id == _TASK_ID
    mock_app.send_task.assert_called_once()
