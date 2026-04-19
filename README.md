# RemindmeAI

An intelligent email-based reminder system that automatically reads your Gmail, detects deadlines and important events using NLP, and sends you reminders before they're due.

## Features

- **Gmail OAuth 2.0** — connect your Gmail account securely
- **Smart NLP Pipeline** — keyword-anchored extraction detects deadlines, meetings, exams, payments, and any important email
- **Automatic Reminders** — email reminders sent before every deadline
- **Multi-user Support** — multiple users, multiple Gmail accounts
- **Dashboard** — view all deadlines, reminders, and connected accounts
- **Real-time Processing** — new emails processed within 5 minutes automatically

## Tech Stack

**Backend**
- FastAPI + Python 3.11
- PostgreSQL 16 (via asyncpg + SQLAlchemy)
- Redis 7 + Celery (task queue + scheduler)
- spaCy + dateparser (NLP pipeline)
- Gmail API (OAuth 2.0 PKCE)
- AWS SES (email notifications)
- HashiCorp Vault (token encryption)

**Frontend**
- React 18 + Vite
- TailwindCSS
- React Query
- Axios

**Infrastructure**
- Docker Compose (9 services)
- Prometheus + Grafana (monitoring)
- Celery Beat (scheduled polling every 5 min)

## Project Structure

```
RemindmeAI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic v2 schemas
│   │   ├── routers/             # API endpoints
│   │   ├── core/                # Security, Celery, metrics
│   │   └── services/
│   │       ├── ingestion/       # Gmail poller (Celery task)
│   │       ├── nlp/             # Cleaner, classifier, deadline extractor
│   │       ├── reminders/       # Scheduler + dispatcher
│   │       ├── notifications/   # AWS SES email sender
│   │       ├── oauth/           # Gmail OAuth client
│   │       └── calendar/        # Google Calendar integration
│   ├── alembic/                 # DB migrations
│   ├── tests/                   # Unit tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/                 # Axios API clients
│       ├── components/          # Dashboard, Deadlines, Reminders, Settings
│       └── hooks/               # React Query hooks
├── docker-compose.yml
└── .env.example
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/auth/start/gmail` | Start Gmail OAuth |
| GET | `/auth/callback/gmail` | OAuth callback |
| DELETE | `/auth/disconnect/gmail` | Disconnect Gmail |
| GET | `/stats/dashboard` | Dashboard stats |
| GET | `/deadlines` | List deadlines |
| PATCH | `/deadlines/{id}` | Update deadline status |
| GET | `/reminders` | List reminders |
| POST | `/reminders/{id}/snooze` | Snooze reminder |
| GET | `/preferences` | Get user preferences |
| PUT | `/preferences` | Update preferences |

Full interactive docs available at: `{BASE_URL}/docs`

## Setup

### Prerequisites
- Docker + Docker Compose
- Gmail API credentials (Google Cloud Console)
- AWS SES credentials (for email notifications)

### 1. Clone the repo
```bash
git clone https://github.com/BadalSharma007/RemindmeAI.git
cd RemindmeAI
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run
```bash
docker-compose up -d
```

App runs at `http://localhost:8000` (API) and `http://localhost:5173` (Frontend).

### 4. Google Cloud Setup
1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Add redirect URI: `http://localhost:8000/auth/callback/gmail`
5. Add test users under OAuth consent screen

## Environment Variables

See `.env.example` for all required variables. Key ones:

```env
SECRET_KEY=           # JWT signing key (min 32 chars)
FERNET_KEY=           # Fernet encryption key
DATABASE_URL=         # PostgreSQL connection string
REDIS_URL=            # Redis connection string
GMAIL_CLIENT_ID=      # From Google Cloud Console
GMAIL_CLIENT_SECRET=  # From Google Cloud Console
GMAIL_REDIRECT_URI=   # Must match Google Cloud Console
```

## How It Works

```
Gmail ──OAuth──▶ Stored Connection
                      │
              Celery Beat (every 5 min)
                      │
              Gmail API → fetch new emails
                      │
              NLP Pipeline:
                1. Spam detection
                2. Classification (is it important?)
                3. Deadline extraction (keyword-anchored NLP)
                      │
              Create Deadline + Reminder rows in DB
                      │
              Celery Beat (every 30 sec)
                      │
              Dispatch due reminders → AWS SES email
```

## Author

Badal Kumar Sharma
