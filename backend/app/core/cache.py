"""Unified caching layer for ZenEngr (memory + redis support via cashews).

Configured via CACHE_BACKEND in .env ("memory" | "redis").
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

try:
    from cashews import cache as _cashews_cache
    _HAS_CASHEWS = True
except ImportError:
    _cashews_cache = None  # type: ignore[assignment]
    _HAS_CASHEWS = False

from app.core.config import get_settings

logger = logging.getLogger("zenengr.cache")


class _FallbackCache:
    """Resilient async in-memory cache used when cashews is not yet installed."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def setup(self, _url: str) -> None:
        pass

    async def get(self, key: str) -> Any | None:
        import time

        item = self._store.get(key)
        if item is None:
            return None
        expire_at, val = item
        if time.monotonic() > expire_at:
            self._store.pop(key, None)
            return None
        return val

    async def set(self, key: str, value: Any, expire: int = 60) -> None:
        import time

        self._store[key] = (time.monotonic() + expire, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()


cache = _cashews_cache if _HAS_CASHEWS else _FallbackCache()


def init_cache() -> None:
    """Initialize cache backend according to app settings."""
    settings = get_settings()
    backend = settings.cache_backend.lower().strip()

    if _HAS_CASHEWS and cache is not None:
        if backend == "redis" and settings.redis_url:
            logger.info("Initializing Redis cache backend at %s", settings.redis_url)
            cache.setup(settings.redis_url)
        else:
            logger.info("Initializing in-memory cache backend (mem://)")
            cache.setup("mem://")
    else:
        logger.info("Using built-in async in-memory cache engine")


# ── Cache Key Helpers ──────────────────────────────────────────────────────────


def user_cache_key(user_id: uuid.UUID | str) -> str:
    return f"user:{user_id}"


def client_user_cache_key(user_id: uuid.UUID | str) -> str:
    return f"client_user:{user_id}"


def tenant_catalog_cache_key(tenant_id: uuid.UUID | str) -> str:
    return f"tenant_catalog:{tenant_id}"


def tenant_flags_cache_key(tenant_id: uuid.UUID | str) -> str:
    return f"tenant_flags:{tenant_id}"


def tenant_settings_cache_key(tenant_id: uuid.UUID | str) -> str:
    return f"tenant_settings:{tenant_id}"


# ── Invalidation Helpers ───────────────────────────────────────────────────────


async def invalidate_user(user_id: uuid.UUID | str) -> None:
    """Evict cached admin user."""
    await cache.delete(user_cache_key(user_id))


async def invalidate_client_user(user_id: uuid.UUID | str) -> None:
    """Evict cached client user."""
    await cache.delete(client_user_cache_key(user_id))


async def invalidate_tenant_metadata(tenant_id: uuid.UUID | str) -> None:
    """Evict cached catalog, flags, and settings for a tenant."""
    await cache.delete(tenant_catalog_cache_key(tenant_id))
    await cache.delete(tenant_flags_cache_key(tenant_id))
    await cache.delete(tenant_settings_cache_key(tenant_id))
