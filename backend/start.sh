#!/bin/sh
set -e

echo "=== RemindmeAI API startup ==="
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

echo "=== Starting API server ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
