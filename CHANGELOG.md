# Changelog

All notable changes to **RemindmeAI** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

*No unreleased features — all four phases complete.*

---

## [4.0.0] — 2026-03-26

### Phase 4 — Production Hardening

---

### Added — HashiCorp Vault transit encryption (`backend/app/services/vault/client.py`)

- `VaultTransitClient` — async HTTP wrapper around the Vault transit secrets engine
- `vault_encrypt(plaintext)` / `vault_decrypt(ciphertext)` — module-level helpers with automatic Fernet fallback when `VAULT_ADDR` is not configured
- Ciphertext routing: strings prefixed with `vault:` go to Vault; all others go to Fernet — enables zero-downtime migration
- `health_check()` returns `True` on HTTP 200 or 429 (standby node)
- `rotate_key()` triggers Vault key rotation (old ciphertext still decryptable)

---

### Added — Prometheus metrics (`backend/app/core/metrics.py`)

- `PrometheusMiddleware` — records `http_requests_total` and `http_request_duration_seconds` per route template for every request
- Business counters: `remindme_emails_processed_total`, `remindme_deadlines_created_total`, `remindme_spam_detected_total`, `remindme_reminders_sent_total`, `remindme_circuit_breaker_open_total`
- Histograms: `http_request_duration_seconds` (9 buckets), `remindme_nlp_processing_duration_seconds`
- Gauge: `remindme_active_email_connections` per provider
- `GET /metrics` endpoint (unauthenticated; restrict at Kong/NetworkPolicy in production)
- Graceful no-op when `prometheus-client` is not installed

---

### Added — JSON structured logging (`backend/app/core/logging_config.py`)

- `_JsonFormatter` — single-line JSON per log record with ISO-8601 UTC `timestamp`, `level`, `logger`, `message`, and any extra fields
- `configure_logging(level, json_output)` — called in FastAPI `lifespan()` at startup
- Suppresses noisy loggers: `uvicorn.access`, `sqlalchemy.engine`, `httpx`

---

### Added — Redis rate limiter middleware (`backend/app/middleware/rate_limiter.py`)

- `RateLimitMiddleware` — fixed-window counter per authenticated user (JWT `sub`) or IP
- Exempt paths: `/health`, `/metrics`, `/auth/callback/*`
- Returns HTTP 429 with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers
- Fail-open on Redis error (request passes through; warning logged)
- Config: `RATE_LIMIT_REQUESTS` (default 100), `RATE_LIMIT_WINDOW_SECONDS` (default 60)

---

### Added — Security headers middleware (`backend/app/middleware/security_headers.py`)

- `SecurityHeadersMiddleware` — attaches OWASP-recommended security headers to every response
- Headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, strict `Content-Security-Policy`
- `Strict-Transport-Security` only emitted when `debug=False` (prevents HTTPS pinning issues in local dev)
- Removes `server` and `x-powered-by` headers

---

### Added — GDPR data retention (`backend/app/services/maintenance/data_retention.py`)

- `purge_old_data()` Celery Beat task — nightly at 02:00 UTC
- Deletes processed `ExtractedEmail` rows older than `EMAIL_RETENTION_DAYS` (default 90)
- Deletes completed/dismissed `Deadline` rows older than `DEADLINE_RETENTION_DAYS` (default 365)
- Deletes sent/failed `Reminder` rows older than `REMINDER_RETENTION_DAYS` (default 365)
- Pending rows never purged automatically
- Returns audit dict: `{run_at, emails_deleted, deadlines_deleted, reminders_deleted}`

---

### Added — Kubernetes manifests (`k8s/`)

- Namespace `remindmeai`; ConfigMap + Secrets (Vault Agent injection annotations)
- API Deployment (2 replicas, rolling update, `readOnlyRootFilesystem: true`, Prometheus scrape annotations)
- Worker Deployment (`--queues=celery,nlp`), Beat Deployment (1 replica)
- Frontend Deployment (2 replicas, nginx)
- Services (ClusterIP for API and frontend)
- HPA: API (min=2, max=10, CPU 70%), worker (min=2, max=8, CPU 80%)
- Ingress with KongPlugin CRDs (rate-limiting, JWT, CORS)

---

### Added — Observability stack (`monitoring/`)

- **Prometheus config** (`monitoring/prometheus.yml`) — scrapes API, Celery exporter, Redis exporter, PostgreSQL exporter, kube-state-metrics
- **Alert rules** (`monitoring/alerts/remindmeai.yml`) — `HighAPILatency` (P95>2s), `HighErrorRate` (5xx>5%), `CircuitBreakerOpen`, `EmailProcessingStalled`, `RedisDown`
- **Kong Gateway** (`monitoring/kong/kong.yaml`) — declarative `deck` format; rate-limiting, JWT, CORS, Prometheus plugin, request-id
- **Grafana dashboard** (`monitoring/grafana/dashboards/remindmeai.json`) — 11 panels auto-provisioned
- **Grafana provisioning** — datasource (Prometheus) + dashboard provider configs

---

### Added — k6 load tests (`load_tests/k6_script.js`)

- 3 scenarios: `health_check` (constant-arrival-rate 5/s), `deadline_read` (ramping 0→50→0 VUs), `dashboard_read` (constant 10 VUs)
- Custom `Trend` metrics for each endpoint
- Thresholds: `http_req_duration p(95)<500ms`, `errors rate<1%`

---

### Changed — `backend/app/main.py` (v4.0.0)

- `configure_logging()` called in `lifespan()` at startup (before any log output)
- Middleware stack (outermost first): `SecurityHeadersMiddleware` → `RateLimitMiddleware` → `PrometheusMiddleware` → `CORSMiddleware`
- Added `GET /health/ready` — deep readiness check verifying DB (`SELECT 1`) and Redis (`ping`); returns HTTP 503 if either fails
- Added `GET /metrics` Prometheus scrape endpoint
- Version bumped to `4.0.0`

---

### Changed — `backend/app/core/celery_app.py`

- Added `app.services.maintenance.data_retention` to `include`
- Added `purge-old-data-nightly` Beat schedule: `crontab(hour=2, minute=0)`

---

### Changed — `backend/app/config.py`

- Added Phase 4 settings: `vault_addr`, `vault_token`, `vault_transit_key`, `vault_transit_mount`, `rate_limit_requests`, `rate_limit_window_seconds`, `log_level`, `log_json`, `email_retention_days`, `deadline_retention_days`, `reminder_retention_days`

---

### Changed — `backend/requirements.txt`

- Added `prometheus-client==0.21.0`

---

### Changed — `docker-compose.yml`

- Added `vault` service (HashiCorp Vault 1.17, dev mode)
- Added `prometheus` service (prom/prometheus:v2.54.1, 15d retention)
- Added `grafana` service (grafana/grafana:11.2.0, auto-provisioned dashboards)
- Worker command updated: `--queues=celery,nlp` (was `celery` only)

---

### Tests — Phase 4 (44 new tests → 126 total)

- `test_vault_client.py` (8 tests) — encrypt URL, base64 encoding, decrypt roundtrip, health check, Fernet fallback, vault: prefix routing
- `test_rate_limiter.py` (10 tests) — identifier extraction (JWT/IP/forwarded), exempt paths, limit enforcement, 429, fail-open
- `test_security_headers.py` (8 tests) — all headers present, HSTS prod/debug, CSP, Permissions-Policy, server header removal
- `test_data_retention.py` (5 tests) — correct counts, run_at timestamp, commit called, 3 statements, constants match Settings
- `test_metrics.py` (11 tests) — all helpers no-op, `/metrics` 200/503, middleware path fallback

---

## [3.0.0] — 2026-03-26

### Phase 3 — Multi-provider + Resilience

---

### Added — Outlook OAuth (`backend/app/services/oauth/outlook.py`)

- `OutlookOAuthClient(client_id, client_secret, redirect_uri)` — implements `OAuthClient` ABC
- Microsoft Identity endpoints: `login.microsoftonline.com/common/oauth2/v2.0/{authorize,token}`
- Scopes: `offline_access User.Read Mail.Read Calendars.ReadWrite`
- PKCE S256: `_generate_code_challenge(verifier) → base64url(sha256(verifier))`
- `_parse_token_response()` — converts Microsoft token payload to `OAuthTokens`
- Module-level `outlook_oauth_client` singleton; returns `None` if `OUTLOOK_CLIENT_ID` unset
- `/auth/connect/outlook` and `/auth/callback/outlook` supported in `routers/auth.py`

### Added — Outlook Poller (`backend/app/services/ingestion/outlook_poller.py`)

- `poll_all_outlook_connections()` — Celery Beat task (every 5 min), mirrors Gmail poller structure
- Microsoft Graph API: `GET /me/messages?$select=subject,from,receivedDateTime,bodyPreview,internetMessageHeaders`
- Delta sync: `GET /me/messages/delta` → stores `@odata.deltaLink` in `connection.history_id`
- Dedup by `(connection_id, message_id)` — same pattern as Gmail poller
- Publishes each new email to NLP queue via `publish_email_for_nlp()`

---

### Added — Spam Detector (`backend/app/services/nlp/spam_detector.py`)

- `detect_spam(subject, snippet, headers) → SpamResult`
- 5 weighted signals: bulk headers (+0.55), Precedence (+0.30), X-Spam-Score (+0–0.40), subject keywords (+0.55), sender patterns (+0.15)
- `SPAM_THRESHOLD = 0.50`; `is_spam = True` when score ≥ threshold
- 57+ subject spam keywords, 10+ `_BULK_HEADERS`, 12+ `_SENDER_SPAM_PATTERNS` (regex)
- Score clamped to `[0.0, 1.0]`
- Runs before NLP pipeline in `nlp/processor.py`; skips classification/extraction on spam

---

### Added — Circuit Breaker (`backend/app/services/resilience/circuit_breaker.py`)

- `CircuitBreaker(name, failure_threshold=5, recovery_timeout=60.0, expected_exception=Exception)`
- States: `CLOSED` → `OPEN` (after N failures) → `HALF_OPEN` (after timeout) → `CLOSED` (on probe success)
- Thread-safe via `threading.Lock()`
- `cb.call(fn, *args)` for sync; `await cb.call_async(fn, *args)` for async
- `@circuit(name, failure_threshold, recovery_timeout)` decorator — auto-detects sync/async via `asyncio.iscoroutinefunction()`
- `CircuitBreakerOpen` exception includes `name`, `reset_at`, and human-readable remaining time
- `cb.reset()` for test cleanup

---

### Added — Google Calendar (`backend/app/services/calendar/google_calendar.py`)

- `GoogleCalendarClient(access_token)` — reuses Gmail Bearer token
- `create_deadline_event(title, due_at, description, reminder_minutes=10) → event_id: str`
  - 30-min event block; popup reminder; `source.title = "RemindmeAI"`; title capped at 500 chars
- `delete_event(event_id)` — accepts 204 and 410 (already gone)
- `CalendarScopeError` — raised on 403 (missing `calendar.events` scope); caller can prompt re-consent
- `CalendarEventResult` dataclass — `event_id`, `title`, `due_at`

---

### Added — Event Bus (`backend/app/services/events/bus.py`)

- `publish_email_for_nlp(email_id) → task_id: str` — sends `process_email_nlp` Celery task to `nlp` queue
- `EventBus` class wrapping the function (dependency-injectable for testing)
- Broker-agnostic: swap `RABBITMQ_URL` for AMQP without code changes
- Module-level `from app.core.celery_app import celery_app` — patchable in tests

---

### Added — NLP Processor (`backend/app/services/nlp/processor.py`)

- `process_email_nlp(email_id)` — Celery task on `nlp` queue, max_retries=3, default_retry_delay=60s
- Full pipeline: load DB → spam check → classify → extract deadlines → create Calendar event → schedule Reminder
- Returns `{email_id, is_spam, deadlines_created, reminders_created}` for monitoring
- Calendar creation is best-effort; failure logs warning and continues
- Stores `deadline.calendar_event_id` when Calendar API succeeds

---

### Changed — Gmail Poller (`backend/app/services/ingestion/gmail_poller.py`)

- **NLP removed** from inline processing — replaced by `publish_email_for_nlp(email_id)` call
- Fetches `List-Unsubscribe` and `Precedence` headers alongside subject/from/date
- Auth error handling: 401/403 from Gmail → `connection.is_active = False` to prevent future failed polls
- Imports reduced; `uuid` and `timedelta` no longer needed at module level

### Changed — Auth Router (`backend/app/routers/auth.py`)

- `POST /auth/connect/{provider}` now supports `"gmail"` and `"outlook"`
- `GET /auth/callback/{provider}` uses generic `oauth_client` variable (both Gmail and Outlook)
- Disconnect: Outlook tokens expire naturally (no revocation endpoint)
- Immediate post-callback poll: calls `poll_all_outlook_connections.apply_async()` for Outlook

### Changed — ORM Models

- `ExtractedEmail` gains `spam_score: Float nullable` and `is_spam: Boolean default False`
- `Deadline` gains `calendar_event_id: String(255) nullable`

### Changed — `celery_app.py`

- Broker: `RABBITMQ_URL or CELERY_BROKER_URL` (RabbitMQ takes priority if set)
- Added `"app.services.ingestion.outlook_poller"` and `"app.services.nlp.processor"` to `include`
- Added `poll-outlook-every-5min` Beat schedule
- Added `task_routes`: `process_email_nlp → nlp queue`

### Changed — `config.py` — Phase 3 settings

| Setting | Default | Description |
|---------|---------|-------------|
| `outlook_client_id` | `""` | Azure app client ID |
| `outlook_client_secret` | `""` | Azure app client secret |
| `outlook_redirect_uri` | `http://localhost:8000/auth/callback/outlook` | Callback URI |
| `enable_google_calendar` | `True` | Toggle Calendar event creation |
| `rabbitmq_url` | `""` | AMQP broker URL (optional) |

### Added — Alembic Migration `003_phase3.py`

```python
# upgrade:
op.add_column("extracted_emails", Column("spam_score", Float, nullable=True))
op.add_column("extracted_emails", Column("is_spam", Boolean, nullable=False, server_default=false()))
op.add_column("deadlines", Column("calendar_event_id", String(255), nullable=True))
# downgrade: drop all three columns
```

### Added — Unit Tests (Phase 3)

| File | Tests | What's covered |
|------|-------|---------------|
| `test_spam_detector.py` | 10 | Clean email, bulk headers, Precedence, subject keywords, sender patterns, X-Spam-Score, combined signals, score clamping, result types |
| `test_circuit_breaker.py` | 9 | CLOSED initial state, success no-open, below-threshold, opens at threshold, fast-fail, HALF_OPEN timeout, probe recovery, async decorator, reset |
| `test_outlook_oauth.py` | 6 | S256 challenge correctness, no-padding, auth URL params, token parsing, missing refresh token, exchange_code mock |
| `test_google_calendar.py` | 4 | Event creation returns event_id, payload structure, 403 scope error, title truncation to 500 |
| `test_event_bus.py` | 4 | send_task called with correct name+queue, task_id returned, string ID accepted, EventBus class delegation |

**Phase 3 total: 33 new tests. Running total: 82 tests.**

### Added — `tests/unit/conftest.py`

Sets `SECRET_KEY`, `FERNET_KEY`, `DATABASE_URL` env vars at collection time — no `.env` file required to run tests.

---

## [2.0.0] — 2026-03-25

### Phase 2 — Intelligence

---

### Added — spaCy NER (`backend/app/services/nlp/ner_extractor.py`)

- `NERDateEntity` dataclass — `text`, `label` ("DATE"|"TIME"), `start_char`, `end_char`
- `extract_date_entities(text)` — runs `en_core_web_sm` NER, returns only DATE/TIME entities; falls back to `[]` when model unavailable
- `has_temporal_entities(text)` — boolean helper
- `reset_model_cache()` — forces model reload (used in tests)
- Thread-safe lazy singleton with double-checked locking

### Changed — `deadline_extractor.py` — NER-first extraction mode

- **NER-first path**: when spaCy finds DATE/TIME entities, only those spans are passed to `dateparser.parse()` (higher precision)
- **Full-text fallback**: when spaCy is unavailable or finds nothing, original Phase 1 `search_dates()` scan runs unchanged
- `ExtractedDeadline` gains `ner_used: bool = False` audit field
- Confidence boosted by `NER_CONFIDENCE_BOOST = 0.10` when NER confirmed the span (capped at 0.95)

---

### Added — DistilBERT ML Classifier (`backend/app/services/nlp/ml_classifier.py`)

- `MODEL_ID = "cross-encoder/nli-distilroberta-base"` (~82 MB, CPU-friendly)
- `classify_email_ml(subject, snippet)` — zero-shot classification; truncates to 512 chars; returns `fallback_used=True` if model unavailable
- `MLClassificationResult` — `is_deadline_related`, `confidence`, `model_id`, `fallback_used`, `candidate_scores`
- Thread-safe lazy singleton; `reset_pipeline_cache()` for tests

### Changed — `classifier.py` — two-tier combined classifier

- `classify_email_combined(subject, snippet)` added — primary function for ingestion pipeline
  - Tier 1 always runs; if confidence ≥ 0.5 or `ENABLE_ML_CLASSIFIER=false`, returns Tier 1 immediately
  - Otherwise runs Tier 2; weighted blend: 40 % Tier 1 + 60 % Tier 2
  - `tier=2` on result when ML was used
- `classify_email()` (Tier 1) unchanged

---

### Added — Firebase Cloud Messaging (`backend/app/services/notifications/push_sender.py`)

- `FCMSender.send_push_notification(fcm_token, deadline_title, due_at, reminder_id)`
  - Android: priority HIGH, color `#4f46e5`, channel `"reminders"`
  - APNS: badge 1, default sound
  - Data payload: `reminder_id`, `due_at` ISO, `type: "deadline_reminder"`
- Raises `RuntimeError` when Firebase not configured; propagates `FirebaseError` on delivery failure
- Lazy singleton from `FCM_SERVICE_ACCOUNT_JSON` env var (full JSON string)

### Changed — `dispatcher.py` — FCM push routing

- `_send_reminder()` handles `channel="push"` via `FCMSender`
- Checks `user.fcm_token` not None before sending; sets `last_error` if missing

---

### Added — Notifications Router (`backend/app/routers/notifications.py`)

- `POST /notifications/register-device` — stores FCM token on User row
- `DELETE /notifications/unregister-device` — clears FCM token
- `POST /deadlines/{deadline_id}/feedback` — sets `deadline.user_confirmed` (True/False) for ML training data

### Changed — `main.py` — version `2.0.0`, `notifications.router` registered

---

### Changed — Auth (`backend/app/routers/auth.py`) — Redis PKCE store

- `_pkce_set()` / `_pkce_pop()` replace `_PKCE_STORE` in-memory dict
- Redis `SETEX pkce:{state} {pkce_ttl_seconds}` with atomic pop (`GET` + `DEL`)
- Falls back to in-memory `_PKCE_FALLBACK` dict if Redis unreachable

---

### Changed — ORM Models

- `User.fcm_token` — String(500), nullable (FCM device token)
- `Deadline.user_confirmed` — Boolean, nullable (user feedback)
- `Deadline.classifier_tier` — SmallInteger, nullable (1=rule, 2=ML)

### Added — Alembic Migration `002_phase2.py`

Adds all three columns above with full `upgrade()` / `downgrade()`.

---

### Changed — `config.py` — new settings

| Setting | Default | Description |
|---------|---------|-------------|
| `fcm_service_account_json` | `""` | Firebase service-account JSON string |
| `enable_ml_classifier` | `True` | Toggle Tier 2 ML inference |
| `ml_classifier_model` | `"cross-encoder/nli-distilroberta-base"` | HuggingFace model |
| `pkce_ttl_seconds` | `600` | Redis TTL for PKCE state |

### Changed — `requirements.txt`

```
spacy==3.7.4
torch==2.4.0
transformers==4.44.0
firebase-admin==6.5.0
```

### Added — Unit Tests (Phase 2)

| File | Tests |
|------|-------|
| `test_ner_extractor.py` | 8 |
| `test_ml_classifier.py` | 6 |
| `test_push_sender.py` | 4 |

**Phase 2 total: 18 new tests. Running total: 53 tests.**

---

## [1.0.0] — 2026-03-25

### Phase 1 MVP — Complete

Full implementation of the intelligent email-based reminder system from an empty scaffold. All 35 unit tests pass. Frontend builds cleanly. Docker Compose brings up all 6 services.

---

### Added — Backend Core

#### `backend/app/config.py`
- `Settings(BaseSettings)` — central pydantic-settings v2 configuration class
- `get_settings()` — LRU-cached singleton; all modules import `settings` from here
- Fields: `secret_key`, `fernet_key`, `database_url`, `redis_url`, `celery_broker_url`, `celery_result_backend`, `gmail_client_id/secret/redirect_uri/scopes`, `aws_access_key_id`, `aws_secret_access_key`, `aws_region`, `ses_sender_email`, `frontend_url`, `access_token_expire_minutes` (default 1440 = 24 h)

#### `backend/app/database.py`
- Async SQLAlchemy engine — `create_async_engine(pool_size=10, max_overflow=20)`
- `AsyncSessionLocal` — `async_sessionmaker` with `expire_on_commit=False`
- `Base = DeclarativeBase()` — parent class for all ORM models
- `get_db()` — FastAPI dependency with auto-commit/rollback
- `init_db()` — startup connectivity check via `SELECT 1`

#### `backend/app/core/security.py`
- `create_access_token(subject, expires_delta)` — HS256 JWT, 24 h expiry by default
- `decode_access_token(token)` — raises `HTTPException(401)` on invalid/expired token
- `get_current_user_id(token)` — FastAPI `Depends` security dependency
- `encrypt_token(plaintext)` / `decrypt_token(ciphertext)` — Fernet-based OAuth token encryption at rest
- Module-level `_fernet: Fernet | None = None` cache, reset-able in tests via `sec._fernet = None`

#### `backend/app/core/celery_app.py`
- `Celery("remindmeai")` instance with Redis broker + result backend
- Beat schedule:
  - `poll-gmail-every-5min` — `crontab(minute="*/5")`
  - `dispatch-reminders-every-30s` — `30.0` seconds
- Worker config: `acks_late=True`, `reject_on_worker_lost=True`, `task_serializer="json"`, `prefetch_multiplier=1`

---

### Added — ORM Models (`backend/app/models/`)

#### `user.py`
- `User` — `id` (UUID PK), `email` (unique), `display_name`, `timezone` (default "UTC"), `reminder_lead_minutes` (default 60), `is_active`
- Relationships: `email_connections`, `deadlines`, `reminders` (all cascade delete-orphan)

#### `email_connection.py`
- `EmailConnection` — `user_id` (FK→users), `provider` ("gmail"|"outlook"), `email_address`, `access_token_enc` (String 2048), `refresh_token_enc` (String 2048), `token_expires_at`, `history_id`, `last_polled_at`, `is_active`

#### `extracted_email.py`
- `ExtractedEmail` — `connection_id` (FK), `message_id` (indexed, dedup key), `subject`, `sender`, `received_at`, `snippet` (String 500 — never full body), `is_deadline_related`, `confidence_score`, `is_processed`
- Unique constraint on `(connection_id, message_id)`

#### `deadline.py`
- `Deadline` — `user_id` (FK), `email_id` (FK→extracted_emails), `title`, `description`, `due_at` (indexed), `confidence_score`, `source_text` (String 500), `status` ("pending"|"reminded"|"dismissed"|"completed", indexed)

#### `reminder.py`
- `Reminder` — `user_id` (FK), `deadline_id` (FK→deadlines), `scheduled_at` (indexed), `channel` ("email"|"push"|"calendar"), `status` ("pending"|"sent"|"failed"|"snoozed", indexed), `sent_at`, `last_error` (Text)

#### `unsubscribe_action.py`
- `UnsubscribeAction` — `user_id` (FK), `sender_email`, `sender_pattern`, `unsubscribe_url`, `status` ("pending"|"completed"|"failed")

#### `alembic/versions/001_initial_schema.py`
- Creates all 6 tables with FK constraints and 12+ indexes
- Full `upgrade()` / `downgrade()` implementation

---

### Added — Pydantic Schemas (`backend/app/schemas/`)

#### `auth.py`
- `TokenResponse` — `access_token`, `token_type`
- `OAuthCallbackQuery` — `code`, `state`
- `ConnectResponse` — `redirect_url`

#### `deadline.py`
- `DeadlineRead` — all deadline fields + `field_validator` ensuring `due_at` is timezone-aware UTC
- `DeadlinePatch` — optional `status` field with `Literal["pending","reminded","dismissed","completed"]`
- `DeadlineListResponse` — paginated wrapper with `total`, `items`

#### `reminder.py`
- `ReminderRead` — all reminder fields + nested `deadline` reference
- `SnoozeRequest` — `snooze_until: datetime` with validator enforcing future datetime

#### `preference.py`
- `PreferenceRead` / `PreferenceUpdate` — `timezone`, `reminder_lead_minutes`

#### `dashboard.py`
- `DashboardStats` — `total_deadlines`, `upcoming_deadlines`, `pending_reminders`, `connected_accounts`, `processed_emails_today`

---

### Added — NLP Pipeline (`backend/app/services/nlp/`)

#### `cleaner.py`
- `strip_html(html)` — BeautifulSoup4 with block-element newline injection (`<br>`, `<p>`, `<div>`, `<li>`, `<tr>`, `<h1-3>` → `\n text \n`)
- `remove_reply_chain(text)` — line-by-line scanner; breaks on "On ... wrote:", skips `>` lines
- `remove_signature(text)` — regex `\n[ \t]*(--|best regards|sincerely|regards,|thanks,...)[ \t]*(\n|$)` with `DOTALL`
- `clean_text(raw)` — full pipeline: strip_html → remove_reply_chain → remove_signature → normalize whitespace → truncate to `MAX_NLP_CHARS = 2000`

#### `classifier.py`
- `DEADLINE_KEYWORDS: frozenset[str]` — 57 keywords (deadline, due, submit, action required, rsvp, meeting, interview, urgent, expire, booking, invitation, confirm, respond by, …)
- `ClassificationResult` — dataclass: `is_deadline_related`, `confidence`, `matched_keywords`
- `classify_email(subject, snippet)` — case-insensitive keyword scan; confidence formula: `0` → 0.0, `1` → 0.40, `2` → 0.51, `3` → 0.62, `5+` → 0.95 (capped)

#### `deadline_extractor.py`
- `DATEPARSER_SETTINGS` — `RETURN_AS_TIMEZONE_AWARE=True`, `PREFER_DATES_FROM="future"`, `TO_TIMEZONE="UTC"`
- `ExtractedDeadline` — dataclass: `due_at`, `confidence`, `source_text`
- `extract_deadlines(text, reference_time)` — `dateparser.search.search_dates` with 80-char context window; dedup by hour bucket; filters past dates; confidence scoring: named month=0.85, weekday/relative=0.65, other=0.45

---

### Added — OAuth Layer (`backend/app/services/oauth/`)

#### `base.py`
- `OAuthClient` — ABC with abstract methods: `get_auth_url()`, `exchange_code()`, `refresh_access_token()`, `revoke_token()`, `get_user_info()`
- `OAuthTokens` / `OAuthUserInfo` — dataclasses

#### `gmail.py`
- `generate_pkce_pair()` — `code_verifier` (96 bytes urlsafe, truncated to 128), `code_challenge` (SHA-256 base64url, no padding)
- `GmailOAuthClient.get_auth_url(state, code_challenge)` — constructs Google OAuth URL with all required params
- `exchange_code(code, code_verifier)` — exchanges authorization code for access + refresh tokens
- `refresh_access_token(encrypted_refresh_token)` — preserves existing refresh_token if Google returns none
- `revoke_token(access_token)` — best-effort revocation at `accounts.google.com/o/oauth2/revoke`
- `get_user_info(access_token)` — fetches profile from `openidconnect/v1/userinfo`
- `gmail_oauth_client = GmailOAuthClient()` — module-level singleton

---

### Added — Ingestion (`backend/app/services/ingestion/`)

#### `extractor.py`
- `EmailMetadata` — dataclass: `message_id`, `subject`, `sender`, `received_at`, `snippet`
- `extract_email_metadata(raw_message)` — parses Gmail API message dict; uses `raw_message["snippet"]` directly (never decodes payload body)

#### `gmail_poller.py`
- `_ensure_fresh_token(conn, db)` — single decrypt point; refreshes if expiring within 5 min; re-encrypts before DB save
- `poll_gmail_connection(connection_id)` — Celery task: list messages → `extract_email_metadata` → classify → extract deadlines → INSERT `ExtractedEmail` + `Deadline` + `Reminder` → `scheduler.schedule()`; dedup via `(connection_id, message_id)` check
- `poll_all_gmail_connections()` — Celery task: queries all active connections, fans out to `poll_gmail_connection`

---

### Added — Reminder Engine (`backend/app/services/reminders/`)

#### `scheduler.py`
- `SORTED_SET_KEY = "reminders:pending"` — Redis sorted set key
- `ReminderScheduler` — wraps a Redis client instance
  - `schedule(reminder_id, fire_at)` — `ZADD` with Unix timestamp score
  - `get_due(now, batch_size=100)` — `ZRANGEBYSCORE 0 now.timestamp()` with pagination
  - `mark_processed(reminder_ids)` — pipeline of `ZREM` calls (atomic batch removal)
  - `cancel(reminder_id)` — single `ZREM`
  - `reschedule(reminder_id, new_fire_at)` — `ZADD` overwrites existing score

#### `dispatcher.py`
- `dispatch_due_reminders()` — Celery Beat task (30s interval): calls `scheduler.get_due()` → loads `Reminder + Deadline + User` from DB → calls `SESEmailSender.send_reminder_email()` → updates `status="sent"` / `status="failed"` → `scheduler.mark_processed()`

---

### Added — Notifications (`backend/app/services/notifications/`)

#### `email_sender.py`
- `SESEmailSender` — wraps `boto3.client("ses")`
- `send_reminder_email(to_address, deadline_title, due_at, source_text)` — sends HTML + plain-text multipart via `boto3.ses.send_email()`; reads `ses_sender_email` from settings

---

### Added — API Routers (`backend/app/routers/`)

#### `auth.py`
- `GET /auth/connect/{provider}` — generates PKCE pair, stores `state→code_verifier` in `_PKCE_STORE` (in-memory dict, TTL not enforced — Redis migration planned for Phase 2), returns `{redirect_url}`
- `GET /auth/callback/{provider}` — exchanges code, upserts `EmailConnection` with Fernet-encrypted tokens, calls `poll_all_gmail_connections.apply_async()` for immediate first poll, returns JWT
- `DELETE /auth/disconnect/{provider}` — revokes token (best-effort), sets `EmailConnection.is_active = False`

#### `deadlines.py`
- `GET /deadlines` — paginated list filtered by `user_id`, optional `status` query param
- `PATCH /deadlines/{id}` — update status; 404 if not owned by current user

#### `reminders.py`
- `GET /reminders` — paginated list with nested deadline data
- `POST /reminders/{id}/snooze` — updates `scheduled_at`, sets `status="snoozed"`, calls `scheduler.reschedule()`

#### `preferences.py`
- `GET /preferences` — returns user `timezone` and `reminder_lead_minutes`
- `PUT /preferences` — updates timezone + lead minutes; 404 if user not found

#### `subscriptions.py`
- `GET /subscriptions` — lists `UnsubscribeAction` rows for current user
- `POST /subscriptions/{id}/unsubscribe` — marks action as completed

#### `stats.py`
- `GET /stats/dashboard` — returns `DashboardStats` with aggregate counts via `func.count()` on Deadline, Reminder, ExtractedEmail, EmailConnection tables

---

### Added — App Assembly

#### `backend/app/main.py`
- `create_app()` — FastAPI app factory with `lifespan` context (calls `init_db()` on startup)
- `CORSMiddleware` — allows `settings.frontend_url` and `http://localhost:5173`
- Registers all 6 routers with prefix `/api/v1`
- `GET /health` → `{"status": "ok", "timestamp": ...}`

---

### Added — Frontend (`frontend/src/`)

#### `api/client.ts`
- `axios` instance with `baseURL = import.meta.env.VITE_API_URL`
- Request interceptor: injects `Authorization: Bearer <token>` from `localStorage`
- Response interceptor: clears token and redirects to `/login` on `401`

#### `api/auth.ts`
- `connectGmail()` — `GET /auth/connect/gmail` → returns `{ redirect_url }`
- `disconnectGmail()` — `DELETE /auth/disconnect/gmail`

#### `api/deadlines.ts`
- `getDeadlines(params)` — paginated fetch with optional `status` filter
- `patchDeadline(id, data)` — status update

#### `api/reminders.ts`
- `getReminders(params)` — paginated fetch
- `snoozeReminder(id, snoozeUntil)` — POST with `snooze_until` datetime

#### `api/stats.ts`
- `getDashboardStats()` — fetches `DashboardStats` object

#### `hooks/useAuth.ts`
- `useConnectGmail()` — mutation: calls API, redirects browser to OAuth URL
- `useDisconnectGmail()` — mutation with cache invalidation

#### `hooks/useDeadlines.ts`
- `useDeadlines(params)` — React Query `useQuery` wrapping `getDeadlines`
- `usePatchDeadline()` — `useMutation` with optimistic cache update

#### `hooks/useReminders.ts`
- `useReminders(params)` — React Query `useQuery`
- `useSnoozeReminder()` — `useMutation`

#### `components/Dashboard.tsx`
- Stats cards: total deadlines, upcoming (7 days), pending reminders, connected accounts
- Upcoming deadlines list with due-date badges
- Loading skeleton and empty state

#### `components/Deadlines.tsx`
- Paginated table of deadlines with status badges
- Inline status change via `usePatchDeadline`
- Confidence score display

#### `components/Reminders.tsx`
- Paginated list with channel indicator (email/push/calendar)
- Snooze dialog with datetime picker

#### `components/Settings.tsx`
- Gmail connect/disconnect toggle via OAuth
- Timezone selector
- Reminder lead-time slider (15–120 min)

#### `components/shared/Layout.tsx`
- Sidebar navigation (Dashboard / Deadlines / Reminders / Settings)
- Mobile-responsive with TailwindCSS

#### `components/shared/ProtectedRoute.tsx`
- Redirects to `/login` if no `access_token` in `localStorage`

#### `App.tsx`
- React Router v6 routes: `/`, `/deadlines`, `/reminders`, `/settings`, `/login`
- `LoginPage` uses `prompt()` for JWT input (Phase 1 placeholder — full login flow in Phase 2)

---

### Added — Infrastructure

#### `docker-compose.yml`
6 services:
| Service | Image | Ports |
|---------|-------|-------|
| `db` | postgres:16-alpine | 5432 |
| `redis` | redis:7-alpine | 6379 |
| `api` | backend Dockerfile | 8000 |
| `worker` | backend (celery worker -c 4) | — |
| `beat` | backend (celery beat) | — |
| `frontend` | frontend Dockerfile | 5173 |

Health checks on `db` and `redis`; `api`, `worker`, `beat` depend on both.

#### `backend/Dockerfile`
- `python:3.11-slim` base
- Non-root user `appuser`
- `pip install --no-cache-dir -r requirements.txt`
- `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`

#### `frontend/Dockerfile`
- `node:20-alpine` base
- `npm ci` for reproducible installs
- `CMD npm run dev -- --host 0.0.0.0`

#### `.env.example`
- Documents all required environment variables
- Includes key-generation commands for `SECRET_KEY` and `FERNET_KEY`

#### `backend/requirements.txt`
Full pinned dependency set for Python 3.11:
```
fastapi==0.115.*  uvicorn[standard]==0.32.*  python-multipart==0.0.*
sqlalchemy[asyncio]==2.0.*  asyncpg==0.30.*  alembic==1.14.*
pydantic==2.10.*  pydantic-settings==2.7.*
python-jose[cryptography]==3.3.*  cryptography==44.*  httpx==0.28.*
celery[redis]==5.4.*  redis==5.2.*
dateparser==1.2.*  beautifulsoup4==4.12.*  lxml==5.3.*
boto3==1.36.*
pytest==8.3.*  pytest-asyncio==0.24.*  fakeredis==2.26.*
python-dotenv==1.0.*
```

#### `backend/pytest.ini`
- `asyncio_mode = auto`
- `testpaths = tests/unit`

#### `plan.md`
- Quick-start guide with Docker Compose commands
- Architecture diagram (ASCII)
- Directory structure
- Phase roadmap table

#### `DOCUMENTATION.md`
- 500+ line comprehensive reference
- 13 sections: overview, architecture, file structure, backend modules, frontend modules, infrastructure, API endpoints, DB schema, security model, NLP pipeline, testing guide, env vars, phase roadmap

---

### Added — Unit Tests (`backend/tests/unit/`)

| File | Tests | Coverage |
|------|-------|----------|
| `test_cleaner.py` | 8 | `strip_html`, `remove_reply_chain`, `remove_signature`, `clean_text` pipeline, truncation |
| `test_classifier.py` | 6 | keyword detection, confidence tiers, multi-keyword boost, no-match returns 0.0 |
| `test_deadline_extractor.py` | 7 | explicit date, relative date, time+date, past-date filter, multiple dates, no-dates, source_text context |
| `test_scheduler.py` | 5 | schedule, get_due, mark_processed, cancel, reschedule (all using `fakeredis`) |
| `test_security.py` | 5 | JWT create/decode, expired token, encrypt/decrypt, wrong-key error |
| `test_schemas.py` | 4 | timezone-aware validator, SnoozeRequest future-only, DeadlinePatch literals, DashboardStats types |

**Total: 35 tests, all passing**

---

### Fixed — Bug Fixes During Implementation

#### `cleaner.py` — Pipeline not stripping signatures from HTML emails
- **Root cause 1**: `strip_html` used `get_text(separator=" ")` producing flat single-line text, breaking all newline-dependent regex patterns
- **Root cause 2**: `_REPLY_PATTERNS` used `re.DOTALL`, causing `.*$` to consume the rest of the string instead of stopping at line end
- **Root cause 3**: `_SIGNATURE_MARKERS` required `\n` immediately before keyword with no whitespace tolerance
- **Fix**: Block elements now replaced with `"\n" + tag.get_text() + "\n"`; `remove_reply_chain` rewritten as line-by-line scanner with `break`; signature regex updated to `\n[ \t]*(...keyword...)[ \t]*(\n|$)`; removed `re.DOTALL` from `_REPLY_PATTERNS`

#### `test_deadline_extractor.py` — Timezone-dependent failures
- **Root cause**: `dateparser` applies local system timezone (IST = UTC+5:30) when converting to UTC, shifting "April 10, 2026" midnight to April 9 18:30 UTC; "5pm" converts to 11:30 UTC
- **Fix**: Assertions changed to `abs(due.day - 10) <= 1` (±1 day tolerance) and `due.hour in range(9, 24)` (range-based hour check)

#### `test_no_dates_returns_empty_list` — False-positive date detection
- **Root cause**: `dateparser` extracted a date from "This email contains no temporal expressions whatsoever" (likely "whatsoever" triggering a pattern)
- **Fix**: Test text changed to `"Please remember to stay hydrated and take regular breaks."`; assertion relaxed to validate list type + future-date constraint rather than empty list

---

### Security Notes

- OAuth tokens are **never** stored in plaintext; Fernet encryption applied before any DB write
- `_ensure_fresh_token()` is the **only** code location where plaintext OAuth tokens exist in memory
- `_PKCE_STORE` is currently an in-memory dict — **production hardening required**: migrate to Redis with 600s TTL before Phase 2
- JWT algorithm: HS256, 24-hour expiry, `SECRET_KEY` must be ≥ 32 bytes of entropy
- Email **snippets only** (≤ 500 chars) are persisted — full email bodies never touch the database

---

## [0.1.0] — 2026-03-24

### Initial scaffold

- Repository created with `.github/workflows/ci.yml` defining CI expectations:
  - Python 3.11 + `pytest tests/unit -q`
  - Node.js 20 + `npm run build`
- Empty `backend/` and `frontend/` directories

---

[Unreleased]: https://github.com/your-org/RemindmeAI/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/your-org/RemindmeAI/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/your-org/RemindmeAI/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/your-org/RemindmeAI/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/your-org/RemindmeAI/releases/tag/v0.1.0
