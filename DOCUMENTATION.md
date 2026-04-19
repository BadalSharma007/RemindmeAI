# RemindmeAI — Complete Project Documentation

> Intelligent Email-Based Reminder System
> Last updated: 2026-03-26 | Phase: 4 — Production Hardening Complete

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [File Structure](#3-file-structure)
4. [Backend — File-by-File Reference](#4-backend--file-by-file-reference)
5. [Frontend — File-by-File Reference](#5-frontend--file-by-file-reference)
6. [Infrastructure & Config](#6-infrastructure--config)
7. [API Reference](#7-api-reference)
8. [Database Schema](#8-database-schema)
9. [Security Model](#9-security-model)
10. [NLP Pipeline](#10-nlp-pipeline)
11. [Testing](#11-testing)
12. [Environment Variables](#12-environment-variables)
13. [Phase Roadmap](#13-phase-roadmap)

---

## 1. Project Overview

RemindmeAI automatically connects to a user's Gmail account via OAuth 2.0, monitors incoming emails, extracts deadlines and action items using an NLP pipeline, and sends timely reminders via email (Phase 1), push notifications, and calendar events (Phase 2+).

### Core principles
| Principle | Implementation |
|-----------|---------------|
| **Privacy-first** | Only snippets (≤500 chars) stored — never full email bodies |
| **Event-driven** | Ingestion saves email → publishes to NLP event bus → NLP Celery task processes asynchronously |
| **Fault-tolerant** | Circuit breakers on external APIs; Redis sorted sets; idempotent dedup by message_id |
| **Modular** | Each service is independently testable; NLP decoupled from ingestion via event bus |
| **Multi-provider** | Gmail + Outlook via shared `OAuthClient` ABC; same NLP pipeline for both |

---

## 2. Architecture

```
Gmail / Outlook
      │
      ▼ OAuth 2.0 + PKCE (S256)
┌─────────────────┐
│  Auth Service   │ ──── Fernet-encrypted tokens ──▶ PostgreSQL
└─────────────────┘
      │ trigger immediate poll
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Ingestion Service  (Celery Beat — every 5 min)                 │
│  Gmail Poller    → extract metadata (subject, sender, snippet)  │
│  Outlook Poller  → Microsoft Graph API + delta sync ✅          │
│  → publish_email_for_nlp(email_id) → Celery nlp queue           │
└─────────────────────────────────────────────────────────────────┘
      │ (event bus — Redis / RabbitMQ)
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  NLP Processor  (nlp queue — decoupled Celery task) ✅           │
│  1. spam_detector.detect_spam()    — header + keyword analysis  │
│  2. cleaner.clean_text()           — strip HTML, replies, sigs  │
│  3. classifier.classify_email_combined() — Tier1 + Tier2 ML     │
│  4. deadline_extractor.extract_deadlines() — spaCy NER + dateparser│
│  5. google_calendar.create_deadline_event()  ✅ (best-effort)   │
│  6. scheduler.schedule()           — Redis ZADD                 │
└─────────────────────────────────────────────────────────────────┘
      │ Deadline + Reminder rows in PostgreSQL
      │ Reminder IDs in Redis sorted set (score = fire Unix ts)
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Reminder Dispatcher  (Celery Beat — every 30 s)                │
│  Redis ZRANGEBYSCORE → fan-out to channels                      │
│  Email (AWS SES) ✅ · Push (FCM) ✅                              │
└─────────────────────────────────────────────────────────────────┘

Circuit Breakers: CLOSED/OPEN/HALF_OPEN on all external API calls ✅
Infrastructure:   PostgreSQL 16 · Redis 7 · Celery 5 · RabbitMQ (opt.) · FastAPI 0.115 · Vault · Prometheus · Grafana
Frontend:         React 18 · Vite 6 · TailwindCSS 3 · React Query 5
```

### Data flow summary
```
Gmail API / Microsoft Graph API
  └─▶ gmail_poller.py / outlook_poller.py  (Celery Beat, every 5min)
        └─▶ extractor.py          → EmailMetadata (subject/sender/snippet only)
        └─▶ INSERT ExtractedEmail
        └─▶ events/bus.publish_email_for_nlp(email_id)
              └─▶ Celery send_task → nlp queue

nlp/processor.py (Celery, nlp queue)
  └─▶ spam_detector.detect_spam()   → SpamResult (score, is_spam)
  └─▶ [if spam] → mark processed, done
  └─▶ cleaner.clean_text()
  └─▶ classifier.classify_email_combined() → ClassificationResult (Tier1+Tier2)
  └─▶ [if not deadline-related] → mark processed, done
  └─▶ deadline_extractor.extract_deadlines() → [ExtractedDeadline, ...]
        └─▶ INSERT Deadline row (with calendar_event_id if created)
        └─▶ google_calendar.create_deadline_event()  (best-effort)
        └─▶ INSERT Reminder row
        └─▶ scheduler.schedule()  (Redis ZADD)

dispatcher.py (Celery Beat, 30s)
  └─▶ scheduler.get_due()     (Redis ZRANGEBYSCORE)
        └─▶ email_sender.py   → AWS SES           (channel="email")
        └─▶ push_sender.py    → Firebase FCM      (channel="push")
        └─▶ DB update (status = "sent")
        └─▶ scheduler.mark_processed()
```

---

## 3. File Structure

```
RemindmeAI/
├── DOCUMENTATION.md         ← This file
├── CHANGELOG.md             ← Version history
├── plan.md                  ← Quick-start guide
├── .env.example             ← Environment variable template
├── docker-compose.yml       ← Dev environment (6 services)
│
├── backend/
│   ├── requirements.txt     ← Python dependencies (pinned)
│   ├── pytest.ini           ← Test configuration
│   ├── alembic.ini          ← Migration configuration
│   ├── Dockerfile           ← Backend container
│   │
│   ├── alembic/
│   │   ├── env.py           ← Async migration setup
│   │   ├── script.py.mako   ← Migration template
│   │   └── versions/
│   │       ├── 001_initial_schema.py  ← All 6 tables
│   │       └── 002_phase2.py          ← fcm_token, user_confirmed, classifier_tier
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          ← FastAPI app factory + CORS + lifespan
│   │   ├── config.py        ← Settings (pydantic-settings)
│   │   ├── database.py      ← Async SQLAlchemy engine + session
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py      ← JWT + Fernet encryption
│   │   │   ├── celery_app.py    ← Celery instance + Beat schedule
│   │   │   ├── metrics.py       ← Prometheus counters/histograms + PrometheusMiddleware  (Phase 4)
│   │   │   └── logging_config.py← JSON structured logging (configure_logging)           (Phase 4)
│   │   │
│   │   ├── middleware/                                                                    (Phase 4)
│   │   │   ├── __init__.py
│   │   │   ├── rate_limiter.py  ← Redis fixed-window rate limiter (429 + Retry-After)
│   │   │   └── security_headers.py ← HSTS, CSP, X-Frame-Options, etc.
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py  ← Exports all models
│   │   │   ├── user.py
│   │   │   ├── email_connection.py
│   │   │   ├── extracted_email.py
│   │   │   ├── deadline.py
│   │   │   ├── reminder.py
│   │   │   └── unsubscribe_action.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── deadline.py
│   │   │   ├── reminder.py
│   │   │   ├── preference.py
│   │   │   └── dashboard.py
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           ← /auth/*
│   │   │   ├── deadlines.py      ← /deadlines/*
│   │   │   ├── reminders.py      ← /reminders/*
│   │   │   ├── preferences.py    ← /preferences
│   │   │   ├── subscriptions.py  ← /subscriptions/*
│   │   │   ├── stats.py          ← /stats/dashboard
│   │   │   └── notifications.py  ← /notifications/* + /deadlines/{id}/feedback  (Phase 2)
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── oauth/
│   │       │   ├── __init__.py
│   │       │   ├── base.py      ← OAuthClient ABC
│   │       │   ├── gmail.py     ← GmailOAuthClient (PKCE)
│   │       │   └── outlook.py   ← OutlookOAuthClient (Microsoft Identity, Phase 3)
│   │       ├── ingestion/
│   │       │   ├── __init__.py
│   │       │   ├── extractor.py       ← EmailMetadata extraction
│   │       │   ├── gmail_poller.py    ← Celery task → event bus
│   │       │   └── outlook_poller.py  ← Graph API + delta sync  (Phase 3)
│   │       ├── nlp/
│   │       │   ├── __init__.py
│   │       │   ├── cleaner.py              ← HTML → clean text
│   │       │   ├── classifier.py           ← Tier 1 rule-based + Tier 2 ML combined
│   │       │   ├── deadline_extractor.py   ← spaCy NER-first + dateparser → deadlines
│   │       │   ├── ner_extractor.py        ← spaCy DATE/TIME entity extraction  (Phase 2)
│   │       │   ├── ml_classifier.py        ← DistilBERT zero-shot classifier    (Phase 2)
│   │       │   ├── spam_detector.py        ← Header + keyword spam analysis     (Phase 3)
│   │       │   └── processor.py            ← Decoupled NLP Celery task           (Phase 3)
│   │       ├── reminders/
│   │       │   ├── __init__.py
│   │       │   ├── scheduler.py    ← Redis sorted-set ops
│   │       │   └── dispatcher.py   ← Celery Beat task
│   │       ├── notifications/
│   │       │   ├── __init__.py
│   │       │   ├── email_sender.py ← AWS SES
│   │       │   └── push_sender.py  ← Firebase Cloud Messaging  (Phase 2)
│   │       ├── resilience/                          ← Phase 3
│   │       │   ├── __init__.py
│   │       │   └── circuit_breaker.py  ← CLOSED/OPEN/HALF_OPEN state machine
│   │       ├── events/                              ← Phase 3
│   │       │   ├── __init__.py
│   │       │   └── bus.py              ← publish_email_for_nlp() → nlp queue
│   │       ├── calendar/                            ← Phase 3
│   │       │   ├── __init__.py
│   │       │   └── google_calendar.py  ← GoogleCalendarClient (create/delete events)
│   │       ├── vault/                               ← Phase 4
│   │       │   ├── __init__.py
│   │       │   └── client.py           ← VaultTransitClient; vault_encrypt/decrypt; Fernet fallback
│   │       └── maintenance/                         ← Phase 4
│   │           ├── __init__.py
│   │           └── data_retention.py   ← GDPR nightly purge Celery task
│   │
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py  ← All 6 tables
│   │       ├── 002_phase2.py          ← fcm_token, user_confirmed, classifier_tier
│   │       └── 003_phase3.py          ← spam_score, is_spam, calendar_event_id
│   │
│   └── tests/
│       ├── __init__.py
│       └── unit/
│           ├── __init__.py
│           ├── conftest.py                        ← env var setup (Phase 3)
│           ├── test_cleaner.py           (8 tests)
│           ├── test_classifier.py        (6 tests)
│           ├── test_deadline_extractor.py(7 tests)
│           ├── test_scheduler.py         (5 tests)
│           ├── test_security.py          (5 tests)
│           ├── test_schemas.py           (4 tests)
│           ├── test_ner_extractor.py     (8 tests)  ← Phase 2
│           ├── test_ml_classifier.py     (6 tests)  ← Phase 2
│           ├── test_push_sender.py       (4 tests)  ← Phase 2
│           ├── test_spam_detector.py    (10 tests)  ← Phase 3
│           ├── test_circuit_breaker.py   (9 tests)  ← Phase 3
│           ├── test_outlook_oauth.py     (6 tests)  ← Phase 3
│           ├── test_google_calendar.py   (4 tests)  ← Phase 3
│           ├── test_event_bus.py         (4 tests)  ← Phase 3
│           ├── test_vault_client.py      (8 tests)  ← Phase 4
│           ├── test_rate_limiter.py     (10 tests)  ← Phase 4
│           ├── test_security_headers.py  (8 tests)  ← Phase 4
│           ├── test_data_retention.py    (5 tests)  ← Phase 4
│           └── test_metrics.py          (11 tests)  ← Phase 4
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── tailwind.config.ts
    ├── postcss.config.js
    ├── index.html
    ├── Dockerfile
    └── src/
        ├── main.tsx           ← QueryClient + BrowserRouter mount
        ├── App.tsx            ← Routes + ProtectedRoute
        ├── index.css          ← Tailwind directives
        ├── vite-env.d.ts      ← Vite env types
        ├── api/
        │   ├── client.ts      ← axios + JWT interceptor + 401 redirect
        │   ├── auth.ts        ← connectGmail, getMe, disconnect
        │   ├── deadlines.ts   ← getDeadlines, patchDeadline
        │   ├── reminders.ts   ← getReminders, snooze
        │   └── stats.ts       ← getDashboard
        ├── hooks/
        │   ├── useAuth.ts     ← useCurrentUser, isAuthenticated
        │   ├── useDeadlines.ts← useDeadlines, usePatchDeadline
        │   └── useReminders.ts← useReminders, useSnoozeReminder
        └── components/
            ├── Dashboard.tsx  ← Stats cards + Connect Gmail CTA
            ├── Deadlines.tsx  ← Deadline list + Done/Dismiss
            ├── Reminders.tsx  ← Reminder list + Snooze 1h
            ├── Settings.tsx   ← Lead-time prefs + Disconnect
            └── shared/
                ├── Layout.tsx        ← Nav bar + content wrapper
                └── ProtectedRoute.tsx← Redirect if no JWT
```

---

## 4. Backend — File-by-File Reference

### `app/config.py`
Central configuration via `pydantic-settings`. All values come from environment variables or `.env` file.

```python
class Settings(BaseSettings):
    app_name: str = "RemindmeAI"
    debug: bool = False
    secret_key: str          # JWT signing (min 32 chars)
    fernet_key: str          # Fernet AES-128 key (base64)
    database_url: str        # postgresql+asyncpg://...
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    gmail_client_id: str
    gmail_client_secret: str
    gmail_redirect_uri: str
    gmail_scopes: list[str]
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    ses_sender_email: str
    frontend_url: str
    access_token_expire_minutes: int = 1440  # 24h
```

**`get_settings()`** — LRU-cached singleton, safe to call anywhere.

---

### `app/database.py`
Async SQLAlchemy setup.

| Symbol | Type | Purpose |
|--------|------|---------|
| `engine` | `AsyncEngine` | Connection pool (size=10, max_overflow=20) |
| `AsyncSessionLocal` | `async_sessionmaker` | Session factory |
| `Base` | `DeclarativeBase` | Parent for all ORM models |
| `get_db()` | `AsyncGenerator` | FastAPI dependency — yields session, auto-commit/rollback |
| `init_db()` | `async fn` | Called on startup to verify DB connectivity |

---

### `app/core/security.py`

**JWT functions:**
| Function | Description |
|----------|-------------|
| `create_access_token(subject, expires_delta)` | Sign HS256 JWT with sub + exp |
| `decode_access_token(token)` | Validate JWT → payload dict; raises `HTTPException(401)` |
| `get_current_user_id(token)` | FastAPI `Depends` — extracts user UUID string from Bearer |

**Fernet functions (OAuth token encryption):**
| Function | Description |
|----------|-------------|
| `encrypt_token(plaintext)` | Fernet-encrypt → base64 ciphertext string |
| `decrypt_token(ciphertext)` | Fernet-decrypt → plaintext; raises `ValueError` on failure |

> **Security boundary:** Plaintext OAuth tokens exist only in memory during `_ensure_fresh_token()`. Everything in the DB is ciphertext.

---

### `app/core/celery_app.py`
Celery instance with three Beat jobs and dedicated NLP queue routing:

| Job | Task | Schedule |
|-----|------|----------|
| `poll-gmail-every-5min` | `poll_all_gmail_connections` | `crontab(minute="*/5")` |
| `poll-outlook-every-5min` | `poll_all_outlook_connections` | `crontab(minute="*/5")` |
| `dispatch-reminders-every-30s` | `dispatch_due_reminders` | `30.0` seconds |
| `purge-old-data-nightly` | `purge_old_data` | `crontab(hour=2, minute=0)` — 02:00 UTC |

**Queue routing:** `process_email_nlp` tasks are routed to the `nlp` queue, allowing a separate worker pool for CPU-heavy NLP inference. Broker: `RABBITMQ_URL` if set, else `CELERY_BROKER_URL` (Redis).

Settings: `acks_late=True`, `reject_on_worker_lost=True`, `prefetch_multiplier=1` — ensures no task is silently dropped if a worker crashes.

---

### `app/models/` — ORM Models

#### `user.py` — `User`
```
id (UUID PK) | email (unique) | display_name | timezone | reminder_lead_minutes | is_active
created_at | updated_at
→ connections, deadlines, reminders (cascade delete)
```

#### `email_connection.py` — `EmailConnection`
```
id | user_id (FK→users) | provider | provider_email
access_token_enc | refresh_token_enc  ← Fernet ciphertext
token_expiry | last_polled_at | history_id | is_active | created_at
→ extracted_emails (cascade delete)
```

#### `extracted_email.py` — `ExtractedEmail`
```
id | connection_id (FK→email_connections)
message_id (indexed) | subject | sender | received_at
snippet (max 500 chars — NEVER full body) | is_processed | created_at
spam_score FLOAT nullable | is_spam BOOL default False   ← Phase 3
→ deadlines (cascade delete)
```

#### `deadline.py` — `Deadline`
```
id | user_id (FK→users) | extracted_email_id (FK→extracted_emails, SET NULL)
title | due_at (indexed) | confidence_score | source_text | status (indexed)
status values: "pending" | "reminded" | "dismissed" | "completed"
user_confirmed BOOL nullable | classifier_tier INT nullable  ← Phase 2
calendar_event_id VARCHAR(255) nullable                      ← Phase 3
created_at
→ reminders (cascade delete)
```

#### `reminder.py` — `Reminder`
```
id | deadline_id (FK→deadlines) | user_id (FK→users)
scheduled_at (indexed) | channel | status (indexed)
channel values: "email" | "push" | "calendar"
status values: "pending" | "sent" | "failed" | "snoozed"
sent_at | snooze_until | last_error | created_at
```

#### `unsubscribe_action.py` — `UnsubscribeAction`
```
id | user_id (FK→users) | sender_pattern | sender_email
unsubscribe_url | status | created_at
status: "pending" | "confirmed" | "executed" | "failed"
```

---

### `app/schemas/` — Pydantic v2 Schemas

| Schema | Key Validators |
|--------|---------------|
| `DeadlineRead` | `due_at` must be timezone-aware |
| `SnoozeRequest` | `snooze_until` must be in the future |
| `PreferencePatch` | `exclude_unset=True` for partial updates |
| `DashboardStats` | All fields default to `0` |

---

### `app/routers/` — REST Endpoints

#### `auth.py`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/connect/{provider}` | JWT | Generate PKCE pair, return provider redirect URL |
| GET | `/auth/callback/{provider}` | — | Exchange code, upsert User+Connection, return JWT |
| DELETE | `/auth/disconnect/{provider}` | JWT | Revoke tokens, deactivate connection |
| GET | `/auth/me` | JWT | Return current user profile |

**Supported providers:** `gmail` | `outlook` (Phase 3). PKCE state backed by Redis (TTL=600s), in-memory fallback for dev.

#### `deadlines.py`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/deadlines?status=&limit=` | List deadlines (default: all, sorted by due_at) |
| GET | `/deadlines/{id}` | Single deadline |
| PATCH | `/deadlines/{id}` | Update status or title |

#### `reminders.py`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reminders?status=&limit=` | List reminders |
| POST | `/reminders/{id}/snooze` | Snooze: updates DB + Redis sorted set |

#### `preferences.py`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/preferences` | Get timezone + lead minutes |
| PUT | `/preferences` | Update preferences |

#### `subscriptions.py`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/subscriptions` | List detected promotional senders |
| POST | `/subscriptions/{id}/unsubscribe` | Mark as unsubscribed (execution in Phase 3) |

#### `stats.py`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/stats/dashboard` | Aggregate counts for dashboard |

---

### `app/services/oauth/`

#### `base.py` — Abstract Interface
```python
class OAuthClient(ABC):
    get_authorization_url(state, code_verifier) → str
    exchange_code(code, code_verifier) → OAuthTokens
    refresh_access_token(refresh_token) → OAuthTokens
    get_user_info(access_token) → OAuthUserInfo
```

#### `gmail.py` — Gmail PKCE Implementation
```python
generate_pkce_pair() → (code_verifier: str, code_challenge: str)
# code_verifier: 128-char URL-safe random string
# code_challenge: SHA-256(code_verifier) → base64url (no padding)
```

Token lifecycle:
1. `get_authorization_url()` — builds consent URL with `code_challenge`
2. `exchange_code()` — exchanges code + `code_verifier` for tokens
3. `refresh_access_token()` — obtains new access_token; preserves refresh_token if not returned
4. `revoke_token()` — best-effort revocation at `https://oauth2.googleapis.com/revoke`

#### `outlook.py` — Outlook / Microsoft Identity PKCE Implementation (Phase 3)
```python
OutlookOAuthClient(client_id, client_secret, redirect_uri)
# Endpoints: login.microsoftonline.com/common/oauth2/v2.0/{authorize,token}
# Scopes: offline_access User.Read Mail.Read Calendars.ReadWrite
# PKCE: S256 — same approach as Gmail
# _generate_code_challenge(verifier) → base64url(sha256(verifier))
```

Module-level singleton `outlook_oauth_client` returns `None` if `OUTLOOK_CLIENT_ID` not set (provider disabled).

---

### `app/services/ingestion/`

#### `extractor.py`
```python
@dataclass
class EmailMetadata:
    message_id: str       # Gmail message ID (dedup key)
    subject: str          # max 500 chars
    sender: str           # max 255 chars
    received_at: datetime # UTC-aware
    snippet: str          # Gmail's own snippet, max 500 chars

def extract_email_metadata(raw_message: dict) -> EmailMetadata
```
Privacy guarantee: The `payload.parts[].body.data` (base64 body) is **never decoded**. Only the existing `snippet` field from Gmail API is used.

#### `gmail_poller.py` (Phase 3 updated)
NLP is no longer inline — emails are published to the event bus:
```
poll_all_gmail_connections()
  └─▶ SELECT all active Gmail connections
  └─▶ for each connection:
        └─▶ _ensure_fresh_token()    ← decrypt/refresh/re-encrypt
        └─▶ GET /messages?q=is:unread&maxResults=20
        └─▶ for each message_id (not already in DB):
              └─▶ GET /messages/{id}?format=metadata + spam headers
              └─▶ extract_email_metadata()
              └─▶ INSERT ExtractedEmail
              └─▶ publish_email_for_nlp(email_id)  ← event bus (nlp queue)
        └─▶ UPDATE connection.last_polled_at + COMMIT
```

**Auth error handling:** 401/403 from Gmail API → `connection.is_active = False` (prevents further failed polls until user re-connects).

#### `outlook_poller.py` (Phase 3 new)
Microsoft Graph API poller with delta sync:
```
poll_all_outlook_connections()
  └─▶ SELECT all active Outlook connections
  └─▶ for each connection:
        └─▶ _ensure_fresh_token()  ← Outlook token refresh via microsoft identity
        └─▶ GET /me/messages/delta (incremental if history_id set, else full sync)
             params: $select=subject,from,receivedDateTime,bodyPreview,headers
        └─▶ Store @odata.deltaLink → connection.history_id
        └─▶ for each new message (dedup by message_id):
              └─▶ INSERT ExtractedEmail
              └─▶ publish_email_for_nlp(email_id)
        └─▶ UPDATE connection.last_polled_at + COMMIT
```

---

### `app/services/nlp/`

#### `cleaner.py`

**Pipeline (`clean_text`):**
1. `strip_html(raw)` — BeautifulSoup `replace_with("\n" + text + "\n")` on block elements
2. `remove_reply_chain(text)` — Line-by-line scan:
   - Break on `on .{0,100}wrote:` (case-insensitive)
   - Skip lines starting with `>`
3. `remove_signature(text)` — Regex: `\n[ \t]*(best regards|regards,|--|sincerely|...)` → truncate
4. Whitespace normalization: collapse `[ \t]+` → `" "`, `\n{3,}` → `"\n\n"`
5. Truncate to `MAX_NLP_CHARS = 2000`

#### `classifier.py`

`DEADLINE_KEYWORDS` (57 entries) includes: `deadline`, `due`, `action required`, `rsvp`, `confirm by`, `meeting`, `interview`, `registration closes`, day-of-week prefixed with "by", etc.

**Confidence formula:**
```python
confidence = min(0.4 + (len(matched) - 1) * 0.11, 0.95)
# 0 matches → 0.0  (not deadline-related)
# 1 match   → 0.40
# 2 matches → 0.51
# 3 matches → 0.62
# 5+ matches→ 0.95
```

#### `deadline_extractor.py`

```python
DATEPARSER_SETTINGS = {
    "RETURN_AS_TIMEZONE_AWARE": True,
    "PREFER_DATES_FROM": "future",
    "TO_TIMEZONE": "UTC",
}
```

Deduplication: dates within the same **hour bucket** (`dt.replace(minute=0, second=0, microsecond=0)`) are merged — avoids two reminders for "April 10 at 5pm" and "5pm April 10".

Confidence scoring:
- Contains month name (jan–dec): **0.85**
- Contains relative/weekday term: **0.65**
- Other (time only, ambiguous): **0.45**

---

### `app/services/reminders/`

#### `scheduler.py` — Redis Sorted Set Operations

```
Key: "reminders:pending"
Member: str(reminder_id)
Score: fire_at.timestamp()  (Unix float)
```

| Method | Redis Command | Description |
|--------|--------------|-------------|
| `schedule(id, fire_at)` | `ZADD` | Add or update |
| `cancel(id)` | `ZREM` | Remove |
| `snooze(id, until)` | `ZADD` (update) | New fire time |
| `get_due(now, batch=100)` | `ZRANGEBYSCORE 0 now LIMIT 0 100` | Fetch due IDs |
| `mark_processed(ids)` | `PIPELINE ZREM` | Atomic bulk remove |

#### `dispatcher.py` — Celery Beat Task
```
dispatch_due_reminders() [every 30s]
  └─▶ scheduler.get_due(now, batch_size=100)
  └─▶ for each reminder_id:
        └─▶ SELECT Reminder WHERE status='pending'
        └─▶ SELECT Deadline, User
        └─▶ _send_reminder() → SESEmailSender.send_reminder_email()
        └─▶ UPDATE reminder.status = "sent"
        └─▶ collect processed_ids
  └─▶ db.commit()
  └─▶ scheduler.mark_processed(processed_ids)
```

**Failure behavior:** If SES fails, `reminder.status = "failed"`, `last_error` is saved, ID is still removed from Redis (no re-attempt in Phase 1). Add retry queue in Phase 4.

---

### `app/services/nlp/spam_detector.py` (Phase 3)

**`detect_spam(subject, snippet, headers) → SpamResult`**

Weighted signal scoring:

| Signal | Weight | Condition |
|--------|--------|-----------|
| Bulk header (`List-Unsubscribe`, `X-Campaign-Id`, etc.) | +0.55 | Any one present |
| `Precedence: bulk/list/junk` | +0.30 | header value in set |
| `X-Spam-Score ≥ 5.0` | +0–0.40 | proportional |
| Subject keyword match (57 terms) | +0.55 | Any one keyword |
| Sender pattern (`noreply`, `newsletter`, …) | +0.15 | regex match |

`is_spam = True` when `spam_score ≥ 0.50`. Score clamped to `[0, 1]`.

---

### `app/services/resilience/circuit_breaker.py` (Phase 3)

**`CircuitBreaker(name, failure_threshold=5, recovery_timeout=60.0, expected_exception=Exception)`**

State machine:
```
CLOSED → (N consecutive failures) → OPEN → (recovery_timeout) → HALF_OPEN
HALF_OPEN → (probe succeeds) → CLOSED
HALF_OPEN → (probe fails)   → OPEN
```

Thread-safe via `threading.Lock()`. Supports both sync (`cb.call(fn)`) and async (`await cb.call_async(fn)`) invocations.

**`@circuit(name, failure_threshold, recovery_timeout)` decorator** — wraps sync or async functions; exposes `.circuit_breaker` attribute on the wrapper for inspection.

---

### `app/services/calendar/google_calendar.py` (Phase 3)

**`GoogleCalendarClient(access_token)`**

```python
await client.create_deadline_event(title, due_at, description, reminder_minutes=10) → event_id: str
await client.delete_event(event_id) → None
```

Reuses the Gmail Bearer token (token must include `calendar.events` scope). Raises `CalendarScopeError` on 403 so the caller can prompt re-consent.

---

### `app/services/events/bus.py` (Phase 3)

```python
publish_email_for_nlp(email_id: UUID | str | int) → task_id: str
```

Sends `process_email_nlp` to the `nlp` Celery queue. With Redis broker this is a Redis list push; swap `RABBITMQ_URL` for AMQP without code changes.

---

### `app/services/vault/client.py` (Phase 4)

**`VaultTransitClient(vault_addr, vault_token, key_name, mount, timeout)`**

```python
await client.encrypt(plaintext) → ciphertext_str   # "vault:v1:..."
await client.decrypt(ciphertext) → plaintext_str
await client.rotate_key()                           # key rotation (old versions still decrypt)
await client.health_check() → bool                 # 200 or 429 = healthy
```

Module-level helpers with **automatic Fernet fallback**:
```python
ciphertext = await vault_encrypt("oauth-token")   # Vault if configured, else Fernet
plaintext  = await vault_decrypt(ciphertext)      # routes by vault: prefix
```

Detection: ciphertext starting with `vault:` is sent to Vault; all other strings go to Fernet. This allows zero-downtime migration from Fernet to Vault.

---

### `app/services/maintenance/data_retention.py` (Phase 4)

Celery Beat task registered as `purge_old_data`, scheduled nightly at 02:00 UTC:

```
purge_old_data()
  └─▶ DELETE ExtractedEmail WHERE is_processed=True AND created_at < now-90d
  └─▶ DELETE Deadline WHERE status IN ('completed','dismissed') AND created_at < now-365d
  └─▶ DELETE Reminder WHERE status IN ('sent','failed') AND created_at < now-365d
  └─▶ COMMIT
  Returns: {run_at, emails_deleted, deadlines_deleted, reminders_deleted}
```

Rows in `pending` status are **never purged automatically** — they remain actionable.

---

### `app/core/metrics.py` (Phase 4)

**Prometheus metrics** (requires `prometheus-client`):

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | `method`, `path`, `status_code` |
| `http_request_duration_seconds` | Histogram | `method`, `path` |
| `remindme_emails_processed_total` | Counter | `provider` |
| `remindme_deadlines_created_total` | Counter | `classifier_tier` |
| `remindme_spam_detected_total` | Counter | — |
| `remindme_reminders_sent_total` | Counter | `channel` |
| `remindme_active_email_connections` | Gauge | `provider` |
| `remindme_circuit_breaker_open_total` | Counter | `circuit_name` |
| `remindme_nlp_processing_duration_seconds` | Histogram | — |

`PrometheusMiddleware` automatically records HTTP metrics for every request. The `/metrics` endpoint is unauthenticated — restrict at Kong/NetworkPolicy in production.

---

### `app/core/logging_config.py` (Phase 4)

`configure_logging(level, json_output)` — called once at FastAPI startup in `lifespan()`.

| Mode | Format | Use |
|------|--------|-----|
| `json_output=False` | Human-readable | Local development |
| `json_output=True` | Single-line JSON: `{timestamp, level, logger, message, ...extra}` | Production / log aggregation |

Noisy loggers silenced: `uvicorn.access`, `sqlalchemy.engine`, `httpx`.

---

### `app/middleware/rate_limiter.py` (Phase 4)

**Algorithm:** Fixed-window counter in Redis with TTL reset per window.
**Key:** `remindme:ratelimit:user:{UUID}` (JWT) or `remindme:ratelimit:ip:{addr}` (unauthenticated).
**Behavior on Redis failure:** fail-open (request passes through).

Response headers on every non-exempt request:
- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: N`
- `X-RateLimit-Reset: <unix timestamp>`

On limit exceeded (HTTP 429): `Retry-After: <seconds>` added.

---

### `app/middleware/security_headers.py` (Phase 4)

| Header | Value | Note |
|--------|-------|------|
| `X-Content-Type-Options` | `nosniff` | Always |
| `X-Frame-Options` | `DENY` | Always |
| `X-XSS-Protection` | `1; mode=block` | Always |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Always |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()...` | Always |
| `Content-Security-Policy` | `default-src 'self'...frame-ancestors 'none'` | Always |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | **Production only** (`debug=False`) |

Removes `server` and `x-powered-by` response headers.

---

### `app/services/nlp/processor.py` (Phase 3)

Celery task registered as `process_email_nlp` on the `nlp` queue:

```
process_email_nlp(email_id)
  └─▶ Load ExtractedEmail + EmailConnection + User from DB
  └─▶ detect_spam() → store spam_score/is_spam; skip if is_spam
  └─▶ classify_email_combined() → skip if not deadline-related
  └─▶ clean_text() + extract_deadlines()
  └─▶ for each deadline:
        └─▶ INSERT Deadline
        └─▶ GoogleCalendarClient.create_deadline_event() (best-effort)
        └─▶ INSERT Reminder + scheduler.schedule()
  └─▶ mark email is_processed=True + COMMIT
  Returns: {email_id, is_spam, deadlines_created, reminders_created}
```

Auto-retries 3× with 60s backoff on failure.

---

### `app/services/notifications/`

#### `email_sender.py` — `SESEmailSender`

```python
async def send_reminder_email(
    to_address: str,
    deadline_title: str,
    due_at: datetime,
    reminder_id: str,
) -> None
```

Sends both HTML and plain-text versions via `boto3.client("ses").send_email()`. The HTML includes a "Dismiss" link pointing to `{FRONTEND_URL}/reminders/{reminder_id}/dismiss`.

---

## 5. Frontend — File-by-File Reference

### `src/api/client.ts`
```typescript
apiClient = axios.create({ baseURL: VITE_API_BASE_URL })

// Request interceptor: Authorization: Bearer <JWT>
// Response interceptor: 401 → localStorage.removeItem + redirect to /login
```

### `src/api/auth.ts`
| Function | Method | Path | Returns |
|----------|--------|------|---------|
| `connectGmail()` | POST | `/auth/connect/gmail` | `{redirect_url, state}` |
| `getMe()` | GET | `/auth/me` | `UserProfile` |
| `disconnect(provider)` | DELETE | `/auth/disconnect/{provider}` | void |

### `src/api/deadlines.ts`
| Function | Method | Path |
|----------|--------|------|
| `getDeadlines(params?)` | GET | `/deadlines` |
| `getDeadline(id)` | GET | `/deadlines/{id}` |
| `patchDeadline(id, patch)` | PATCH | `/deadlines/{id}` |

### `src/api/reminders.ts`
| Function | Method | Path |
|----------|--------|------|
| `getReminders(params?)` | GET | `/reminders` |
| `snooze(id, snoozeUntil)` | POST | `/reminders/{id}/snooze` |

### `src/api/stats.ts`
| Function | Method | Path |
|----------|--------|------|
| `getDashboard()` | GET | `/stats/dashboard` |

### Hooks
| Hook | Underlying Query | Stale Time |
|------|-----------------|-----------|
| `useCurrentUser()` | `authApi.getMe` | default |
| `useDeadlines(status?)` | `deadlinesApi.getDeadlines` | 30s |
| `useReminders(status?)` | `remindersApi.getReminders` | 30s |
| `usePatchDeadline()` | mutation → `patchDeadline` | invalidates `["deadlines"]` |
| `useSnoozeReminder()` | mutation → `snooze` | invalidates `["reminders"]` |

### Components

| Component | Key Features |
|-----------|-------------|
| `Dashboard` | 5 stat cards; Connect Gmail CTA; auto-refetch every 60s |
| `Deadlines` | Pending deadlines list; Done + Dismiss actions; status badges |
| `Reminders` | Reminder list; Snooze 1h button; status color coding |
| `Settings` | Lead-time input (5–10080 min); Save; Disconnect Gmail |
| `Layout` | Top nav with active-link highlight |
| `ProtectedRoute` | Redirect to `/login` if no JWT in localStorage |

---

## 6. Infrastructure & Config

### `docker-compose.yml` — 9 Services (Phase 4)
| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `db` | postgres:16-alpine | 5432 | PostgreSQL with health check |
| `redis` | redis:7-alpine | 6379 | Broker + scheduler + rate-limiter cache |
| `vault` | hashicorp/vault:1.17 | 8200 | HashiCorp Vault (dev mode) — transit encryption |
| `api` | backend Dockerfile | 8000 | FastAPI (uvicorn --reload) |
| `worker` | backend Dockerfile | — | Celery worker (queues: celery,nlp) |
| `beat` | backend Dockerfile | — | Celery Beat scheduler |
| `frontend` | frontend Dockerfile | 5173 | Vite dev server (HMR) |
| `prometheus` | prom/prometheus:v2.54.1 | 9090 | Metrics scraping (15d retention) |
| `grafana` | grafana/grafana:11.2.0 | 3000 | Dashboards (auto-provisioned from `monitoring/`) |

### `requirements.txt` — Pinned Dependencies
| Category | Package | Version |
|----------|---------|---------|
| Web | fastapi, uvicorn[standard], python-multipart | 0.115.6, 0.32.1, 0.0.20 |
| Database | sqlalchemy[asyncio], asyncpg, alembic | 2.0.36, 0.30.0, 1.14.0 |
| Validation | pydantic, pydantic-settings | 2.10.3, 2.7.0 |
| Auth | python-jose[cryptography], cryptography, httpx | 3.3.0, 44.0.0, 0.28.1 |
| Queue | celery[redis], redis | 5.4.0, 5.2.1 |
| NLP | dateparser, beautifulsoup4, lxml | 1.2.0, 4.12.3, 5.3.0 |
| AWS | boto3 | 1.36.0 |
| Observability | prometheus-client | 0.21.0 |
| Test | pytest, pytest-asyncio, fakeredis | 8.3.4, 0.24.0, 2.26.2 |

### `alembic/versions/001_initial_schema.py`
Creates all 6 tables with indexes:
- `ix_users_email` (unique)
- `ix_email_connections_user_id`
- `ix_extracted_emails_connection_id`, `ix_extracted_emails_message_id`
- `ix_deadlines_user_id`, `ix_deadlines_due_at`, `ix_deadlines_status`
- `ix_reminders_deadline_id`, `ix_reminders_user_id`, `ix_reminders_scheduled_at`, `ix_reminders_status`
- `ix_unsubscribe_actions_user_id`

---

## 7. API Reference

### Base URL
- Development: `http://localhost:8000`
- Docs: `http://localhost:8000/docs` (Swagger UI)

### Authentication
All endpoints except `/health` and `/auth/callback/*` require:
```
Authorization: Bearer <JWT>
```

### Endpoints

#### Health
```
GET /health        → {"status": "ok", "service": "RemindmeAI", "version": "4.0.0"}
GET /health/ready  → {"status": "ready"|"degraded", "checks": {"database": "ok", "redis": "ok"}}
                     HTTP 200 if all checks pass, 503 if any fail
GET /metrics       → Prometheus text format (unauthenticated; restrict at Kong/NetworkPolicy)
```

#### Auth
```
POST   /auth/connect/{provider}          → ConnectResponse
GET    /auth/callback/{provider}         → TokenResponse
DELETE /auth/disconnect/{provider}       → 204
GET    /auth/me                          → UserProfile
```

#### Deadlines
```
GET    /deadlines?status=pending&limit=50 → Deadline[]
GET    /deadlines/{id}                    → Deadline
PATCH  /deadlines/{id}                    → Deadline
  body: {"status": "completed"|"dismissed"|..., "title": "..."}
```

#### Reminders
```
GET  /reminders?status=pending&limit=50   → Reminder[]
POST /reminders/{id}/snooze               → Reminder
  body: {"snooze_until": "2026-04-01T10:00:00+00:00"}
```

#### Preferences
```
GET /preferences         → PreferenceRead
PUT /preferences         → PreferenceRead
  body: {"timezone": "America/New_York", "reminder_lead_minutes": 120}
```

#### Notifications (Phase 2)
```
POST   /notifications/register-device      → 204
  body: {"fcm_token": "device-token-string"}
DELETE /notifications/unregister-device    → 204
POST   /deadlines/{id}/feedback            → 204
  body: {"helpful": true|false}
```

#### Subscriptions
```
GET  /subscriptions                      → [{id, sender_email, status, ...}]
POST /subscriptions/{id}/unsubscribe     → {status, id}
```

#### Stats
```
GET /stats/dashboard → {
  total_deadlines, pending_deadlines,
  upcoming_reminders, emails_processed_today, connected_accounts
}
```

---

## 8. Database Schema

```sql
users
  id UUID PK | email VARCHAR(255) UNIQUE | display_name | timezone | reminder_lead_minutes | is_active | created_at | updated_at

email_connections
  id UUID PK | user_id UUID FK(users CASCADE) | provider VARCHAR(20)
  provider_email | access_token_enc | refresh_token_enc
  token_expiry | last_polled_at | history_id | is_active | created_at

extracted_emails
  id UUID PK | connection_id UUID FK(email_connections CASCADE)
  message_id VARCHAR(255) | subject VARCHAR(500) | sender VARCHAR(255)
  received_at | snippet VARCHAR(500) | is_processed | created_at
  spam_score FLOAT nullable | is_spam BOOL default false          -- Phase 3

deadlines
  id UUID PK | user_id UUID FK(users CASCADE)
  extracted_email_id UUID FK(extracted_emails SET NULL)
  title VARCHAR(500) | due_at TIMESTAMPTZ | confidence_score FLOAT
  source_text VARCHAR(500) | status VARCHAR(20)
  user_confirmed BOOL nullable | classifier_tier INT nullable     -- Phase 2
  calendar_event_id VARCHAR(255) nullable                        -- Phase 3
  created_at

reminders
  id UUID PK | deadline_id UUID FK(deadlines CASCADE)
  user_id UUID FK(users CASCADE) | scheduled_at TIMESTAMPTZ
  channel VARCHAR(20) | status VARCHAR(20) | sent_at
  snooze_until | last_error TEXT | created_at

unsubscribe_actions
  id UUID PK | user_id UUID FK(users CASCADE)
  sender_pattern | sender_email | unsubscribe_url TEXT
  status VARCHAR(20) | created_at
```

---

## 9. Security Model

### Token encryption boundary
```
Browser/client
    │ never sees plaintext OAuth tokens
    ▼
FastAPI router
    │ calls encrypt_token() before DB write
    ▼
PostgreSQL
    │ stores only Fernet ciphertext
    ▼
gmail_poller → _ensure_fresh_token()
    │ calls decrypt_token() — ONLY location with plaintext in memory
    │ passes plaintext token to Gmail API
    │ calls encrypt_token() on new tokens before DB update
```

### Key generation commands
```bash
# SECRET_KEY (JWT signing)
python -c "import secrets; print(secrets.token_hex(32))"

# FERNET_KEY (OAuth token encryption)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### PKCE flow
1. Backend generates `code_verifier` (128 random URL-safe chars)
2. `code_challenge = base64url(SHA-256(code_verifier))`
3. Redirect URL includes `code_challenge` — verifier never leaves server
4. On callback, Google validates that `SHA-256(received verifier) == stored challenge`
5. Prevents authorization code interception attacks

---

## 10. NLP Pipeline

### Stage 1 — Text Cleaning (`cleaner.py`)
```
Input: Raw email (HTML or plain text, subject + snippet)
Output: Clean text, max 2000 chars

Steps:
1. BeautifulSoup: block elements → "\n{content}\n"; get_text()
2. Line scan: break on "On ... wrote:"; skip lines starting with ">"
3. Regex: "\n[ \t]*(best regards|--|sincerely|...)" → truncate
4. Collapse whitespace; strip; truncate to 2000
```

### Stage 2 — Classification (`classifier.py` + `ml_classifier.py`)
```
Input: subject (str), snippet (str)
Output: ClassificationResult { is_deadline_related, confidence, matched_keywords, tier }

classify_email_combined() — two-tier pipeline:
  Tier 1 (always): Case-insensitive scan across 57 DEADLINE_KEYWORDS
    Confidence: 0.0 (0 matches) | 0.40-0.95 (1-5+ matches)
    If confidence ≥ 0.5 → return immediately (no ML overhead)

  Tier 2 (when Tier 1 < 0.5 and ENABLE_ML_CLASSIFIER=true):
    Model: cross-encoder/nli-distilroberta-base (~82 MB, CPU)
    Method: zero-shot classification over two candidate labels
    Weights: 40% Tier 1 + 60% Tier 2 → blended confidence
    Fallback: if model unavailable → return Tier 1 unchanged
    Result: tier=2 on ClassificationResult

  tier field: 1 = rule-based only, 2 = ML blend
  Stored in deadline.classifier_tier for training data collection
```

### Stage 2.5 — NER Entity Extraction (`ner_extractor.py`) — Phase 2
```
Input: cleaned text
Output: [NERDateEntity { text, label("DATE"|"TIME"), start_char, end_char }]

Model: spaCy en_core_web_sm (lazy-loaded, ~12 MB)
Fallback: empty list if model not installed → Stage 3 full-text mode
```

### Stage 3 — Deadline Extraction (`deadline_extractor.py`)
```
Input: cleaned text, reference_time (email received_at)
Output: [ExtractedDeadline { due_at(UTC), source_text, confidence, ner_used }]

Phase 2 NER-first strategy:
  1. Run spaCy NER → collect DATE/TIME entity spans
  2. If entities found:
     a. Parse each entity.text with dateparser.parse()    ← NER-first path
     b. Set ner_used=True, confidence += 0.10 (NER boost, capped 0.95)
  3. If no entities (or spaCy unavailable):
     a. dateparser.search.search_dates() over full text   ← Phase 1 fallback
     b. ner_used=False

Common post-processing:
  4. Filter: drop dates > 1h before reference_time
  5. Deduplicate: same hour bucket → keep first
  6. Extract context: ±80 chars around matched phrase
  7. Confidence base: month name=0.85 | weekday/relative=0.65 | other=0.45
  8. Return sorted by due_at ascending
```

---

## 11. Testing

### Running tests
```bash
cd backend
python -m pytest tests/unit -q
# Minimum env vars auto-set by tests/unit/conftest.py (no .env needed)
```

### Test coverage (126 tests, 19 files)

| File | Tests | What's covered |
|------|-------|---------------|
| `test_cleaner.py` | 8 | HTML stripping, reply chain removal, signature removal, truncation |
| `test_classifier.py` | 6 | Keyword detection, confidence scaling, case insensitivity |
| `test_deadline_extractor.py` | 7 | Date parsing, relative dates, filtering, dedup, context extraction |
| `test_scheduler.py` | 5 | Redis ZADD/ZREM/ZRANGEBYSCORE via fakeredis |
| `test_security.py` | 5 | JWT roundtrip, expiry, tampering, Fernet encrypt/decrypt |
| `test_schemas.py` | 4 | Timezone-aware validation, snooze future check, partial updates |
| `test_ner_extractor.py` | 8 | DATE/TIME entity extraction, non-date filter, multi-entity, model fallback |
| `test_ml_classifier.py` | 6 | Deadline positive/negative, model fallback, inference exception, truncation |
| `test_push_sender.py` | 4 | FCM send path, no-Firebase RuntimeError, title truncation, cache reset |
| `test_spam_detector.py` | 10 | Clean email, List-Unsubscribe, Precedence, X-Spam-Score, combined signals, score clamping |
| `test_circuit_breaker.py` | 9 | CLOSED/OPEN/HALF_OPEN transitions, threshold, timeout recovery, async decorator, reset |
| `test_outlook_oauth.py` | 6 | S256 challenge, auth URL params, token parsing, exchange_code mock |
| `test_google_calendar.py` | 4 | Event creation payload, event_id returned, 403 scope error, title truncation |
| `test_event_bus.py` | 4 | send_task called with correct name+queue, task_id returned, string/UUID ids |
| `test_vault_client.py` | 8 | Encrypt URL, base64 encoding, decrypt roundtrip, health check, Fernet fallback, vault: prefix routing |
| `test_rate_limiter.py` | 10 | Identifier extraction (JWT/IP/forwarded), exempt paths, limit enforcement, 429 response, fail-open on Redis error |
| `test_security_headers.py` | 8 | nosniff, X-Frame-Options, HSTS prod/debug, CSP, Permissions-Policy, server header removal |
| `test_data_retention.py` | 5 | Correct counts, run_at timestamp, commit called, 3 statements executed, constants match Settings |
| `test_metrics.py` | 11 | All helpers no-op without crash, `/metrics` 200/503, PrometheusMiddleware path fallback |

### Design principles
- **No network calls** — all HTTP mocked; firebase_admin injected via `sys.modules`
- **No database** — fakeredis for scheduler; all DB-touching code uses async mocks
- **No file I/O** — pure Python logic tests
- **`conftest.py`** — sets minimum env vars (`SECRET_KEY`, `FERNET_KEY`, `DATABASE_URL`) at collection time so tests run without a `.env` file

---

## 12. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key (32+ chars). Generate: `secrets.token_hex(32)` |
| `FERNET_KEY` | ✅ | AES encryption key. Generate: `Fernet.generate_key().decode()` |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host:port/db` |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | ✅ | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | ✅ | `redis://localhost:6379/2` |
| `GMAIL_CLIENT_ID` | ✅ | From Google Cloud Console |
| `GMAIL_CLIENT_SECRET` | ✅ | From Google Cloud Console |
| `GMAIL_REDIRECT_URI` | ✅ | `http://localhost:8000/auth/callback/gmail` |
| `AWS_ACCESS_KEY_ID` | ✅ | IAM user with `ses:SendEmail` permission |
| `AWS_SECRET_ACCESS_KEY` | ✅ | IAM secret |
| `AWS_REGION` | — | Default: `us-east-1` |
| `SES_SENDER_EMAIL` | ✅ | Verified sender in SES |
| `FRONTEND_URL` | — | Default: `http://localhost:5173` |
| `DEBUG` | — | Default: `false` |
| `VITE_API_BASE_URL` | — | Frontend build: `http://localhost:8000` |
| **Phase 2** | | |
| `FCM_SERVICE_ACCOUNT_JSON` | — | Full JSON string of Firebase service-account credentials. Firebase Console → Project Settings → Service Accounts → Generate new private key |
| `ENABLE_ML_CLASSIFIER` | — | Default: `true`. Set `false` to skip DistilBERT Tier 2 inference |
| `ML_CLASSIFIER_MODEL` | — | Default: `cross-encoder/nli-distilroberta-base` |
| `PKCE_TTL_SECONDS` | — | Default: `600`. Redis TTL (seconds) for PKCE state entries |
| **Phase 3** | | |
| `OUTLOOK_CLIENT_ID` | — | Azure app registration client ID |
| `OUTLOOK_CLIENT_SECRET` | — | Azure app client secret |
| `OUTLOOK_REDIRECT_URI` | — | Default: `http://localhost:8000/auth/callback/outlook` |
| `ENABLE_GOOGLE_CALENDAR` | — | Default: `true`. Set `false` to disable Calendar event creation |
| `RABBITMQ_URL` | — | `amqp://user:pass@host:5672/vhost`. If set, overrides Redis as Celery broker |
| **Phase 4** | | |
| `VAULT_ADDR` | — | HashiCorp Vault URL e.g. `https://vault.internal:8200`. If unset, Fernet is used. |
| `VAULT_TOKEN` | — | Vault auth token (app-role / k8s service-account) |
| `VAULT_TRANSIT_KEY` | — | Transit key name. Default: `remindmeai` |
| `VAULT_TRANSIT_MOUNT` | — | Transit mount path. Default: `transit` |
| `RATE_LIMIT_REQUESTS` | — | Max requests per window. Default: `100` |
| `RATE_LIMIT_WINDOW_SECONDS` | — | Window size in seconds. Default: `60` |
| `LOG_LEVEL` | — | Logging level (`DEBUG`/`INFO`/`WARNING`). Default: `INFO` |
| `LOG_JSON` | — | `true` for JSON-lines output (production). Default: `false` |
| `EMAIL_RETENTION_DAYS` | — | Processed emails purged after N days. Default: `90` |
| `DEADLINE_RETENTION_DAYS` | — | Completed/dismissed deadlines purged after N days. Default: `365` |
| `REMINDER_RETENTION_DAYS` | — | Sent/failed reminders purged after N days. Default: `365` |

---

## 13. Phase Roadmap

### Phase 1 — MVP ✅
- Gmail OAuth 2.0 with PKCE
- Rule-based keyword classifier (57 keywords, Tier 1)
- dateparser temporal extraction → UTC deadlines
- AWS SES email reminders
- Redis sorted-set scheduling
- Celery Beat (5min poll, 30s dispatch)
- PostgreSQL schema (6 tables, 12+ indexes)
- React 18 dashboard + deadlines + reminders + settings
- 35 unit tests passing

### Phase 2 — Intelligence ✅
- spaCy `en_core_web_sm` NER-first date extraction (boosts confidence +0.10 on confirmed entities)
- DistilBERT zero-shot classifier (`cross-encoder/nli-distilroberta-base`) — Tier 2 with 40/60 weighted blend
- `classify_email_combined()` — automatic Tier 1 → Tier 2 escalation when confidence < 0.5
- Firebase Cloud Messaging (FCM) push notifications — `channel="push"` in dispatcher
- User feedback loop — `POST /deadlines/{id}/feedback` stores `user_confirmed` for future training
- Redis-backed PKCE store with 600 s TTL (replaces in-memory dict)
- FCM token registration API (`POST/DELETE /notifications/register-device`)
- Alembic migration `002_phase2` — `users.fcm_token`, `deadlines.user_confirmed`, `deadlines.classifier_tier`
- 18 new unit tests (53 total); all models mock-injectable for zero-network testing

### Phase 3 — Multi-provider ✅
- **Outlook OAuth** — `OutlookOAuthClient` (Microsoft Identity, PKCE S256); `/auth/connect/outlook` + `/auth/callback/outlook`
- **Outlook Poller** — Microsoft Graph API with delta sync (`@odata.deltaLink` → `connection.history_id`)
- **Spam detector** — `detect_spam()` with header analysis (`List-Unsubscribe`, `Precedence`, `X-Spam-Score`) + 27 subject keywords; runs before NLP
- **NLP event bus** — `publish_email_for_nlp()` via Celery `nlp` queue; ingestion decoupled from NLP; compatible with Redis and RabbitMQ
- **Decoupled NLP processor** — `process_email_nlp` Celery task: spam → classify → extract → calendar → schedule; 3× auto-retry
- **Google Calendar** — `GoogleCalendarClient.create_deadline_event()` using Gmail Bearer token; stores `calendar_event_id` on deadline
- **Circuit Breaker** — `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN); `@circuit()` decorator for sync + async; thread-safe
- **Alembic migration `003_phase3`** — `extracted_emails.spam_score`, `extracted_emails.is_spam`, `deadlines.calendar_event_id`
- 29 new unit tests (82 total); `conftest.py` eliminates need for `.env` file in CI

### Phase 4 — Production Hardening ✅ (Current)
- **HashiCorp Vault transit** — `VaultTransitClient` async HTTP wrapper; `vault_encrypt`/`vault_decrypt` with automatic Fernet fallback; detects vault ciphertext by `vault:` prefix
- **Prometheus metrics** — `PrometheusMiddleware` per-route request count/latency; business counters (emails, deadlines, spam, reminders, circuit breaker opens); `/metrics` endpoint
- **JSON structured logging** — `_JsonFormatter` producing single-line JSON per record; ISO-8601 UTC timestamps; `configure_logging()` called at startup
- **Redis token-bucket rate limiter** — `RateLimitMiddleware`; fixed-window counter; fail-open on Redis error; 429 with `Retry-After` + `X-RateLimit-*` headers; exempt: `/health`, `/metrics`, `/auth/callback/*`
- **Security headers middleware** — `SecurityHeadersMiddleware`; HSTS (production only), CSP, X-Frame-Options DENY, X-Content-Type-Options, Permissions-Policy; removes `server`/`x-powered-by`
- **GDPR data retention** — `purge_old_data()` Celery Beat task nightly at 02:00 UTC; deletes processed emails >90d, completed/dismissed deadlines >365d, sent/failed reminders >365d
- **Kubernetes manifests** — Deployments (api ×2, worker ×2, beat ×1, frontend ×2); HPA (API: min=2, max=10; worker: min=2, max=8); Ingress with Kong plugins
- **Kong Gateway** — declarative `deck` format; rate-limiting (Redis policy), JWT validation, CORS, Prometheus plugin, request-id
- **Prometheus alerts** — `HighAPILatency` (P95>2s), `HighErrorRate` (5xx>5%), `CircuitBreakerOpen`, `EmailProcessingStalled`, `RedisDown`
- **Grafana dashboard** — 11 panels: request rate, error rate, P95 latency, emails/deadlines/spam counts, NLP duration histograms, circuit breaker opens, reminders by channel
- **k6 load tests** — 3 scenarios (health_check, deadline_read, dashboard_read); thresholds: P95 <500ms reads, <1000ms writes, error rate <1%
- **`/health/ready`** deep readiness endpoint verifying DB (`SELECT 1`) + Redis (`ping`)
- 44 new unit tests (126 total, 19 test files)

---

*Documentation auto-maintained. Run the project, check `CHANGELOG.md` for version history.*
