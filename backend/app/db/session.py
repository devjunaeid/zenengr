from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# Use NullPool for Neon or external PgBouncer poolers to prevent double-pooling;
# for direct connections (cPanel PostgreSQL / local Postgres), use QueuePool with
# aggressive pool_recycle=60 to prevent cPanel/firewalls from terminating idle connections.
is_pooler = any(
    marker in settings.database_url
    for marker in ("-pooler", "neon.tech", "pgbouncer")
)

if is_pooler:
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "command_timeout": 60,
        },
    )
else:
    engine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=60,  # recycle idle connections every 60s (prevents cPanel timeout disconnects)
        pool_timeout=20,
        connect_args={
            "statement_cache_size": 0,
            "command_timeout": 60,
        },
    )

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

