from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.config import settings

celery_app = Celery(
    "remindmeai",
    broker=settings.rabbitmq_url or settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.services.ingestion.gmail_poller",
        "app.services.ingestion.outlook_poller",
        "app.services.reminders.dispatcher",
        "app.services.nlp.processor",
        "app.services.nlp.rescue",
        "app.services.maintenance.data_retention",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Priority queues: reminders dispatched first, then NLP, then polling
    task_queues=[
        Queue("reminders", queue_arguments={"x-max-priority": 10}),
        Queue("nlp", queue_arguments={"x-max-priority": 10}),
        Queue("polling"),
        Queue("celery"),
    ],
    task_default_priority=5,
    task_routes={
        "app.services.reminders.dispatcher.dispatch_due_reminders": {"queue": "reminders"},
        "app.services.nlp.processor.process_email_nlp": {"queue": "nlp"},
        "app.services.ingestion.gmail_poller.poll_all_gmail_connections": {"queue": "polling"},
        "app.services.ingestion.outlook_poller.poll_all_outlook_connections": {"queue": "polling"},
        "app.services.nlp.rescue.rescue_orphaned_emails": {"queue": "celery"},
        "app.services.maintenance.data_retention.purge_old_data": {"queue": "celery"},
    },
)

celery_app.conf.beat_schedule = {
    "poll-gmail-every-1min": {
        "task": "app.services.ingestion.gmail_poller.poll_all_gmail_connections",
        "schedule": 60.0,
    },
    "poll-outlook-every-1min": {
        "task": "app.services.ingestion.outlook_poller.poll_all_outlook_connections",
        "schedule": 60.0,
    },
    "dispatch-reminders-every-30s": {
        "task": "app.services.reminders.dispatcher.dispatch_due_reminders",
        "schedule": 30.0,
    },
    # Phase 4: GDPR data retention — nightly at 02:00 UTC
    "purge-old-data-nightly": {
        "task": "app.services.maintenance.data_retention.purge_old_data",
        "schedule": crontab(hour=2, minute=0),
    },
    # Rescue: re-queue orphaned emails every 5 minutes
    "rescue-orphaned-emails": {
        "task": "app.services.nlp.rescue.rescue_orphaned_emails",
        "schedule": 300.0,
    },
}
