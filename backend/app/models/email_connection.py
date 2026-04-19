from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailConnection(Base):
    __tablename__ = "email_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # "gmail" | "outlook"
    provider_email: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_enc: Mapped[str] = mapped_column(String(2048), nullable=False)   # Fernet-encrypted
    refresh_token_enc: Mapped[str] = mapped_column(String(2048), nullable=False)  # Fernet-encrypted
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    history_id: Mapped[str | None] = mapped_column(String(64))  # Gmail incremental sync
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="connections")
    extracted_emails: Mapped[list["ExtractedEmail"]] = relationship(
        "ExtractedEmail", back_populates="connection", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EmailConnection id={self.id} provider={self.provider} email={self.provider_email}>"
