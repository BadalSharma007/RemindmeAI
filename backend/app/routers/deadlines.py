from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.deadline import Deadline
from app.schemas.deadline import DeadlineCreate, DeadlinePatch, DeadlineRead

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("", response_model=list[DeadlineRead])
async def list_deadlines(
    status: str | None = Query(None, description="Filter by status: pending, dismissed, completed"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> list[DeadlineRead]:
    """List deadlines for the authenticated user."""
    stmt = select(Deadline).where(Deadline.user_id == uuid.UUID(current_user_id))
    if status:
        stmt = stmt.where(Deadline.status == status)
    stmt = stmt.order_by(Deadline.due_at.asc()).limit(limit)

    result = await db.execute(stmt)
    deadlines = result.scalars().all()
    return [DeadlineRead.model_validate(d) for d in deadlines]


@router.post("", response_model=DeadlineRead, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    body: DeadlineCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> DeadlineRead:
    """Manually create a deadline."""
    deadline = Deadline(
        user_id=uuid.UUID(current_user_id),
        title=body.title,
        due_at=body.due_at,
        source_text=body.source_text or "Manual entry",
        confidence_score=1.0,
        status="pending",
    )
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return DeadlineRead.model_validate(deadline)


@router.get("/{deadline_id}", response_model=DeadlineRead)
async def get_deadline(
    deadline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> DeadlineRead:
    """Get a single deadline by ID."""
    result = await db.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_id == uuid.UUID(current_user_id),
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return DeadlineRead.model_validate(deadline)


@router.patch("/{deadline_id}", response_model=DeadlineRead)
async def patch_deadline(
    deadline_id: uuid.UUID,
    patch: DeadlinePatch,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> DeadlineRead:
    """Update deadline status or title."""
    result = await db.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_id == uuid.UUID(current_user_id),
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    update_data = patch.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deadline, field, value)

    await db.commit()
    await db.refresh(deadline)
    return DeadlineRead.model_validate(deadline)


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_deadline(
    deadline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    """Permanently delete a deadline and its reminders."""
    result = await db.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_id == uuid.UUID(current_user_id),
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    await db.delete(deadline)
    await db.commit()
