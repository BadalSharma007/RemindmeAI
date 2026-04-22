#!/bin/sh
set -e

echo "=== RemindmeAI API startup ==="
echo "=== Running database migrations ==="

# Try normal migration first
if alembic upgrade head; then
    echo "=== Migration successful ==="
else
    echo "=== Migration failed — attempting recovery ==="
    # Stamp back to last known good revision and retry
    # This recovers from a stuck alembic_version (e.g. partial write, bad rollback)
    alembic stamp 004 || true
    echo "=== Retrying migration from revision 004 ==="
    alembic upgrade head
    echo "=== Recovery migration successful ==="
fi

echo "=== Starting API server ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
