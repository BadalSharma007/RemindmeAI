from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExtractedEmail(Base):
    """Stores only metadata + snippet — never the full email body."""

    __tablename__ = "extracted_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(500))
    sender: Mapped[str | None] = mapped_column(String(255))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snippet: Mapped[str | None] = mapped_column(String(500))  # max 500 chars, never full body
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Phase 3: spam detection
    spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    connection: Mapped["EmailConnection"] = relationship(
        "EmailConnection", back_populates="extracted_emails"
    )
    deadlines: Mapped[list["Deadline"]] = relationship(
        "Deadline", back_populates="extracted_email", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ExtractedEmail id={self.id} subject={self.subject!r}>"
