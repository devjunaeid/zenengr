"""Test configuration.

Uses a separate `app_test` database on the same PostgreSQL service.
Created/dropped per session. Schema via Base.metadata.create_all.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app

TEST_DB_NAME = "app_test"
_CONFIG = get_settings()
_BASE_SYNC_URL = _CONFIG.database_url.replace("postgresql+asyncpg://", "postgresql://")
_MAINTENANCE_URL = _BASE_SYNC_URL.rsplit("/", 1)[0] + "/postgres"
_ASYNC_BASE = _CONFIG.database_url.rsplit("/", 1)[0]
_TEST_URL = f"{_ASYNC_BASE}/{TEST_DB_NAME}"


@pytest.fixture(scope="session", autouse=True)
async def _setup_test_db() -> AsyncGenerator[None]:
    """Create test database before tests, drop after. Schema once."""
    conn = await asyncpg.connect(_MAINTENANCE_URL)
    try:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
        )
        if not db_exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()

    # Create schema once for entire session
    engine = create_async_engine(_TEST_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    yield

    conn = await asyncpg.connect(_MAINTENANCE_URL)
    try:
        await conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB_NAME}'
        """
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    """Transaction rollback per test. Schema already exists from session fixture."""
    engine = create_async_engine(_TEST_URL)
    connection = await engine.connect()
    transaction = await connection.begin()
    s = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        yield s
    finally:
        await s.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(session: AsyncSession) -> AsyncGenerator[AsyncSession]:
    """Alias for explicit session usage in tests."""
    yield session


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app, session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Override DB session dependency for tests."""

    async def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
