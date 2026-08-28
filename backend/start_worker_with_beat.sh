#!/bin/sh
set -eu

worker_pid=""
beat_pid=""
health_pid=""

stop_processes() {
    if [ -n "$health_pid" ]; then
        kill "$health_pid" 2>/dev/null || true
    fi
    if [ -n "$worker_pid" ]; then
        kill "$worker_pid" 2>/dev/null || true
    fi
    if [ -n "$beat_pid" ]; then
        kill "$beat_pid" 2>/dev/null || true
    fi
}

trap stop_processes INT TERM EXIT

# Minimal HTTP health server — responds 200 to GET /health
# Uses Python stdlib only (no extra deps). Reads $PORT injected by Railway.
HEALTH_PORT="${PORT:-8000}"
echo "=== Starting health server on port $HEALTH_PORT ==="
python3 -c "
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{\"status\": \"ok\", \"service\": \"worker\"}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress per-request access logs

port = int(os.environ.get('PORT', 8000))
httpd = HTTPServer(('0.0.0.0', port), HealthHandler)
httpd.serve_forever()
" &
health_pid=$!

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
kill "$health_pid" 2>/dev/null || true
wait "$beat_pid" 2>/dev/null || true
wait "$worker_pid" 2>/dev/null || true
wait "$health_pid" 2>/dev/null || true
exit 1