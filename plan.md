# RemindmeAI — Project Plan

> Intelligent Email-Based Reminder System

## Status: Phase 1 MVP — Implementation Complete

---

## Quick Start

### 1. Configure environment
```bash
cp .env.example .env
# Fill in SECRET_KEY, FERNET_KEY, Gmail OAuth credentials, AWS SES keys
# Generate keys:
#   python -c "import secrets; print(secrets.token_hex(32))"          # SECRET_KEY
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # FERNET_KEY
```

### 2. Run with Docker Compose
```bash
docker-compose up --build
```
- API:      http://localhost:8000/docs
- Frontend: http://localhost:5173
- Health:   http://localhost:8000/health

### 3. Run database migrations
```bash
cd backend
alembic upgrade head
```

### 4. Run unit tests
```bash
cd backend
SECRET_KEY=... FERNET_KEY=... DATABASE_URL=... python3.11 -m pytest tests/unit -q
```

---

## Architecture

```
Gmail ──OAuth──▶ Ingestion (Celery, 5min) ──▶ NLP Pipeline
                                                    │
                                           classify + extract deadlines
                                                    │
                                         Reminder Engine (Redis sorted set)
                                                    │
                                        Dispatcher (Celery Beat, 30s)
                                                    │
                                           SES Email notifications
```

## Directory Structure

```
backend/            FastAPI + Celery + PostgreSQL + Redis
  app/
    config.py       All environment variables (pydantic-settings)
    database.py     Async SQLAlchemy engine + session
    main.py         FastAPI app factory + CORS + routers
    core/
      security.py   JWT + Fernet encryption
      celery_app.py Celery instance + Beat schedule
    models/         ORM: User, EmailConnection, ExtractedEmail, Deadline, Reminder
    schemas/        Pydantic v2 validation
    routers/        REST API endpoints
    services/
      oauth/        Gmail PKCE OAuth client
      ingestion/    Email fetching (Gmail API)
      nlp/          clean → classify → extract deadlines
      reminders/    Redis scheduler + Celery dispatcher
      notifications/ AWS SES email sender
  tests/unit/       35 pure-Python unit tests (no network/DB)
  alembic/          Database migrations

frontend/           React 18 + Vite + TailwindCSS
  src/
    api/            Typed API clients (axios)
    hooks/          React Query wrappers
    components/     Dashboard, Deadlines, Reminders, Settings
```

## Phase Roadmap

| Phase | What's added |
|-------|-------------|
| **1 — MVP** ✅ | Gmail OAuth, rule-based classifier, dateparser NLP, SES email, React dashboard |
| **2 — Intelligence** | spaCy NER, DistilBERT classifier, FCM push notifications |
| **3 — Multi-provider** | Outlook, Google Calendar, spam detection, RabbitMQ |
| **4 — Production** | HashiCorp Vault, Kong API gateway, Kubernetes, load testing |
