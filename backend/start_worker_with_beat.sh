#!/bin/sh
set -eu

worker_pid=""
beat_pid=""

stop_processes() {
    if [ -n "$worker_pid" ]; then
        kill "$worker_pid" 2>/dev/null || true
    fi
    if [ -n "$beat_pid" ]; then
        kill "$beat_pid" 2>/dev/null || true
    fi
}

trap stop_processes INT TERM EXIT

echo "=== Starting Celery worker ==="
celery -A app.core.celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=celery,nlp,polling,reminders \
    &
worker_pid=$!

echo "=== Starting Celery beat ==="
celery -A app.core.celery_app.celery_app beat \
    --loglevel=info \
    --scheduler celery.beat.PersistentScheduler \
    --schedule /tmp/celerybeat-schedule \
    &
beat_pid=$!

set +e
        while kill -0 "$worker_pid" 2>/dev/null && kill -0 "$beat_pid" 2>/dev/null; do
            sleep 1
        done

kill "$beat_pid" 2>/dev/null || true
        kill "$worker_pid" 2>/dev/null || true
        wait "$beat_pid" 2>/dev/null || true
        wait "$worker_pid" 2>/dev/null || true
        exit 1