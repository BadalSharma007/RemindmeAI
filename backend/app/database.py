from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


_celery_engine = None
_celery_session_factory = None


def make_session_factory():
    """Return a cached engine + session factory for Celery tasks.

    Cached so DNS is resolved once at first call, not on every task invocation.
    A fresh DNS lookup on every task caused intermittent gaierror(-5) failures
    when Docker's resolver couldn't reach Render's PostgreSQL hostname.
    """
    global _celery_engine, _celery_session_factory
    if _celery_session_factory is None:
        # NullPool: no persistent connections held between tasks.
        # Celery fork workers each get a new event loop via _run(); a pooled
        # engine would hold connections attached to the parent loop, causing
        # "Future attached to a different loop" errors. NullPool creates a
        # fresh connection per session and closes it immediately after.
        # DNS is still resolved only once (when the engine is first created).
        _celery_engine = create_async_engine(
            settings.database_url,
            echo=False,
            poolclass=NullPool,
        )
        _celery_session_factory = async_sessionmaker(
            _celery_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _celery_session_factory


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Verify database connectivity on startup."""
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
