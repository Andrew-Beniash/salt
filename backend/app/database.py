"""Async database engine and session factory.

Usage inside FastAPI route handlers::

    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database import get_db

    @router.get("/things")
    async def list_things(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine (cached for the process lifetime)."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # discard stale connections after network blips
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional async DB session.

    Commits on clean exit, rolls back on any exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
