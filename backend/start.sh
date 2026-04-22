#!/bin/sh
set -e

echo "=== RemindmeAI startup ==="
echo "=== Running database migrations ==="

if alembic upgrade head; then
    echo "=== Migration successful ==="
else
    echo "=== Migration failed — attempting recovery ==="
    alembic stamp 004 || true
    echo "=== Retrying migration from revision 004 ==="
    alembic upgrade head
    echo "=== Recovery migration successful ==="
fi

echo "=== Starting Celery worker ==="
celery -A app.core.celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=celery,nlp,polling,reminders \
    --logfile=/tmp/celery-worker.log &
WORKER_PID=$!

echo "=== Starting Celery beat ==="
celery -A app.core.celery_app.celery_app beat \
    --loglevel=info \
    --scheduler celery.beat.PersistentScheduler \
    --schedule /tmp/celerybeat-schedule \
    --logfile=/tmp/celery-beat.log &
BEAT_PID=$!

echo "=== Starting API server ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
