"""
SlothOps Engine — Async Database Engine
Configures the SQLAlchemy async engine for PostgreSQL via asyncpg.
pool_pre_ping=True handles connection recycling after Docker restarts.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# ── Connection URLs ──────────────────────────────────────────────────────
# Pooled URL for app queries (asyncpg driver)
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://slothops:slothops_dev@localhost:5432/slothops",
)

# Direct URL for Alembic migrations (psycopg sync driver)
DIRECT_DATABASE_URL: str = os.getenv(
    "DIRECT_DATABASE_URL",
    "postgresql+psycopg://slothops:slothops_dev@localhost:5432/slothops",
)

# ── Engine ───────────────────────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,   # recycle stale connections (critical for Docker restarts)
    pool_size=5,
    max_overflow=10,
)

# ── Session Factory ──────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a managed AsyncSession."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """Create all SQLModel tables (used in tests; Alembic handles prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
