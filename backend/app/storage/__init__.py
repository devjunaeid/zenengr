"""Storage backend factory (FEAT-012, FR-12.1).

Switching local <-> S3 is a config change (settings.storage_backend);
application code only ever talks to the StorageBackend protocol.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend


def create_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "s3":
        if (
            not settings.s3_bucket
            or not settings.s3_access_key_id
            or not settings.s3_secret_access_key
        ):
            raise ValueError(
                "S3 storage backend requires s3_bucket, s3_access_key_id, "
                "and s3_secret_access_key settings"
            )
        return S3StorageBackend(
            bucket=settings.s3_bucket,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
        )
    return LocalStorageBackend(root=Path(settings.storage_local_dir))


@lru_cache
def get_storage() -> StorageBackend:
    return create_storage()
