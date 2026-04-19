from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extracted_email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extracted_emails.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    source_text: Mapped[str | None] = mapped_column(String(500))  # excerpt context
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # "pending" | "reminded" | "dismissed" | "completed"
    # Phase 2: user feedback + ML audit
    user_confirmed: Mapped[bool | None] = mapped_column(nullable=True)
    classifier_tier: Mapped[int | None] = mapped_column(nullable=True)  # 1=rule-based, 2=ML
    # Phase 3: Google Calendar integration
    calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="deadlines")
    extracted_email: Mapped["ExtractedEmail | None"] = relationship(
        "ExtractedEmail", back_populates="deadlines"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder", back_populates="deadline", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Deadline id={self.id} title={self.title!r} due_at={self.due_at}>"
