"""Storage migration/backfill tool (FEAT-012, TODO-126).

Usage (from backend/):
    uv run python -m scripts.migrate_storage backfill-legacy
    uv run python -m scripts.migrate_storage transfer --from local --to s3
    uv run python -m scripts.migrate_storage transfer --from s3 --to local

- `backfill-legacy` migrates pre-storage branding logos: tenants whose
  branding.logo_url still points at "/uploads/<name>" get the file copied
  into storage under `public/{tenant_id}/...` and branding.logo_url/logo_key
  (+ the logo_url column) updated to the public endpoint URL. Idempotent:
  tenants already on a public URL are skipped, missing files are skipped.
- `transfer` copies every object key from one backend to the other with
  identical keys (local storage dir <-> S3 bucket). The DB is untouched.
"""

from __future__ import annotations

import argparse
import asyncio
import mimetypes
from pathlib import Path

import boto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.storage import get_storage
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend

_PUBLIC_LOGO_URL_TEMPLATE = "/api/v1/public/tenant/{tenant_id}/logo"
_LEGACY_UPLOADS_PREFIX = "/uploads/"


# ── Backfill: legacy uploads_dir logos -> storage public namespace ─────────


async def backfill_legacy_logos(session: AsyncSession) -> int:
    """Migrate legacy /uploads/<name> branding logos into storage.

    Returns the number of tenants updated. Commits once at the end.
    """
    settings = get_settings()
    storage = get_storage()
    count = 0

    result = await session.execute(select(Tenant))
    for tenant in result.scalars().all():
        branding = dict(tenant.branding or {})
        logo_url = branding.get("logo_url")
        if not isinstance(logo_url, str) or not logo_url.startswith(_LEGACY_UPLOADS_PREFIX):
            continue

        legacy_path = Path(settings.uploads_dir) / Path(logo_url).name
        if not legacy_path.is_file():
            continue

        data = legacy_path.read_bytes()
        key = f"public/{tenant.id}/{legacy_path.name}"
        mime = mimetypes.guess_type(legacy_path.name)[0] or "application/octet-stream"
        await storage.put(key, data, mime)

        branding["logo_key"] = key
        branding["logo_url"] = _PUBLIC_LOGO_URL_TEMPLATE.format(tenant_id=tenant.id)
        tenant.branding = branding
        tenant.logo_url = branding["logo_url"]
        count += 1

    await session.commit()
    return count


# ── Transfer: move object keys between backends ─────────────────────────────


async def transfer_keys(
    source: StorageBackend,
    target: StorageBackend,
    *,
    keys: list[str],
) -> tuple[int, int]:
    """Copy each key from source to target with identical keys.

    Returns (transferred_count, total_bytes). Keys with no object on the
    source are skipped.
    """
    transferred = 0
    total_bytes = 0
    for key in keys:
        data = await source.get(key)
        if data is None:
            continue
        total_bytes += len(data)
        await target.put(key, data, mimetypes.guess_type(key)[0] or "application/octet-stream")
        transferred += 1
    return transferred, total_bytes


def _list_local_keys(settings: object) -> list[str]:
    root = Path(settings.storage_local_dir)  # type: ignore[attr-defined]
    return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]


def _list_s3_keys(settings: object) -> list[str]:
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,  # type: ignore[attr-defined]
        aws_access_key_id=settings.s3_access_key_id,  # type: ignore[attr-defined]
        aws_secret_access_key=settings.s3_secret_access_key,  # type: ignore[attr-defined]
        region_name=settings.s3_region,  # type: ignore[attr-defined]
    )
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket):  # type: ignore[attr-defined]
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def _build_backend(settings: object, name: str) -> StorageBackend:
    if name == "local":
        return LocalStorageBackend(root=Path(settings.storage_local_dir))  # type: ignore[attr-defined]
    if name == "s3":
        if (
            not settings.s3_bucket  # type: ignore[attr-defined]
            or not settings.s3_access_key_id  # type: ignore[attr-defined]
            or not settings.s3_secret_access_key  # type: ignore[attr-defined]
        ):
            raise ValueError(
                "S3 storage backend requires s3_bucket, s3_access_key_id, "
                "and s3_secret_access_key settings"
            )
        return S3StorageBackend(
            bucket=settings.s3_bucket,  # type: ignore[attr-defined]
            access_key_id=settings.s3_access_key_id,  # type: ignore[attr-defined]
            secret_access_key=settings.s3_secret_access_key,  # type: ignore[attr-defined]
            endpoint_url=settings.s3_endpoint_url,  # type: ignore[attr-defined]
            region=settings.s3_region,  # type: ignore[attr-defined]
        )
    raise ValueError(f"unknown storage backend: {name}")


# ── CLI ─────────────────────────────────────────────────────────────────────


async def _run_backfill() -> None:
    async with async_session_factory() as session:
        count = await backfill_legacy_logos(session)
    print(f"backfilled {count} tenant(s)")


async def _run_transfer(source_name: str, target_name: str) -> None:
    if source_name == target_name:
        raise SystemExit("source and target must differ")
    settings = get_settings()
    keys = _list_local_keys(settings) if source_name == "local" else _list_s3_keys(settings)
    source = _build_backend(settings, source_name)
    target = _build_backend(settings, target_name)
    transferred, total_bytes = await transfer_keys(source, target, keys=keys)
    print(f"transferred {transferred} key(s), {total_bytes} byte(s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="migrate_storage",
        description="Storage migration/backfill tool (FEAT-012, TODO-126).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("backfill-legacy", help="migrate legacy /uploads logos into storage")

    transfer_parser = sub.add_parser("transfer", help="copy object keys between backends")
    transfer_parser.add_argument(
        "--from",
        dest="source",
        choices=["local", "s3"],
        required=True,
        help="source backend",
    )
    transfer_parser.add_argument(
        "--to",
        dest="target",
        choices=["local", "s3"],
        required=True,
        help="target backend",
    )

    args = parser.parse_args()
    if args.command == "backfill-legacy":
        asyncio.run(_run_backfill())
    else:
        asyncio.run(_run_transfer(args.source, args.target))


if __name__ == "__main__":
    main()
