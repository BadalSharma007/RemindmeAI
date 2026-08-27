#!/bin/sh
set -e

echo "=== RemindmeAI API startup ==="
for variable in SECRET_KEY FERNET_KEY DATABASE_URL; do
    value=$(printenv "$variable" || true)
    if [ -z "$value" ]; then
        echo "ERROR: Required environment variable $variable is not set" >&2
        exit 1
    fi
done

if ! python -c "from app.config import settings; print('=== Production configuration validated ===')"; then
    echo "ERROR: Production configuration is invalid" >&2
    exit 1
fi

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
