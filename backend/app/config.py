from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Application ---
    app_name: str = "RemindmeAI"
    debug: bool = False
    secret_key: str = Field(..., description="JWT signing key (min 32 chars)")
    fernet_key: str = Field(..., description="Fernet encryption key (base64 32-byte)")

    # --- Database ---
    database_url: str = Field(..., description="asyncpg DSN e.g. postgresql+asyncpg://...")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("fernet_key")
    @classmethod
    def validate_fernet_key(cls, value: str) -> str:
        from cryptography.fernet import Fernet, InvalidToken

        try:
            Fernet(value.encode())
        except (ValueError, TypeError, InvalidToken) as exc:
            raise ValueError("FERNET_KEY must be a valid Fernet key") from exc
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value[len("postgresql://"):]
        return value

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Celery ---
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Gmail OAuth 2.0 ---
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/auth/callback/gmail"
    gmail_scopes: List[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "openid",
        "email",
        "profile",
    ]

    # --- AWS SES ---
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    ses_sender_email: str = "noreply@example.com"

    # --- Frontend ---
    frontend_url: str = "http://localhost:5173"

    # --- JWT ---
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # --- Phase 2: Firebase Cloud Messaging ---
    # Full JSON string of the Firebase service-account credentials.
    # Firebase Console → Project Settings → Service Accounts → Generate new private key
    fcm_service_account_json: str = ""

    # --- Phase 2: ML Classifier ---
    enable_ml_classifier: bool = True
    ml_classifier_model: str = "cross-encoder/nli-distilroberta-base"

    # --- Phase 2: Redis PKCE ---
    pkce_ttl_seconds: int = 600  # seconds before PKCE state expires

    # --- Phase 3: Outlook OAuth 2.0 ---
    outlook_client_id: str = ""
    outlook_client_secret: str = ""
    outlook_redirect_uri: str = "http://localhost:8000/auth/callback/outlook"

    # --- Phase 3: Google Calendar ---
    # Reuses Gmail OAuth token — just ensure calendar.events scope is requested.
    # Set to false to disable calendar event creation.
    enable_google_calendar: bool = True

    # --- Phase 3: RabbitMQ (optional broker override) ---
    # When set, overrides celery_broker_url for RabbitMQ-based deployments.
    # Format: amqp://user:pass@host:port/vhost
    rabbitmq_url: str = ""

    # --- Phase 4: HashiCorp Vault ---
    vault_addr: str = ""          # e.g. https://vault.internal:8200
    vault_token: str = ""         # App-role or K8s service-account token
    vault_transit_key: str = "remindmeai"
    vault_transit_mount: str = "transit"

    # --- Phase 4: Rate limiting ---
    rate_limit_requests: int = 100    # Max requests per window
    rate_limit_window_seconds: int = 60

    # --- Phase 4: Structured logging ---
    log_level: str = "INFO"
    log_json: bool = False  # True in production (JSON lines), False for dev

    # --- Phase 4: Data retention (GDPR) ---
    email_retention_days: int = 90
    deadline_retention_days: int = 365
    reminder_retention_days: int = 365

    # --- LangGraph + LangSmith ---
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "RemindmeAI"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3"
    enable_langgraph: bool = False
    gemini_api_key: str = ""
    use_gemini: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
