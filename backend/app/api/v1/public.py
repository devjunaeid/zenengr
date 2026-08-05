"""Public (unauthenticated) endpoints (FEAT-012, TODO-133).

Branding logos are public assets: the logo endpoint intentionally has NO
auth dependency. Storage keys live under the `public/` namespace; the local
backend exposes them via the static /uploads mount (307 redirect), S3 via a
presigned URL. Legacy /uploads/<name> logo_urls (pre-storage uploads) are
served from uploads_dir for backward compatibility until backfilled.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models.tenant import Tenant
from app.storage import get_storage

router = APIRouter(prefix="/public", tags=["public"])


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


def _guess_media_type(key: str) -> str:
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


@router.get("/tenant/{tenant_id}/logo")
async def get_tenant_logo_endpoint(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Serve a tenant's branding logo. Unauthenticated by design.

    Resolution order:
    1. branding.logo_key in storage: presigned/static URL -> 307 redirect,
       else stream bytes.
    2. Legacy branding.logo_url "/uploads/<name>" with a real file under
       uploads_dir (local-only backward compat).
    3. 404.
    """
    tid = _parse_uuid(tenant_id, kind="Tenant")
    tenant = await session.get(Tenant, tid)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    branding = tenant.branding or {}
    logo_key = branding.get("logo_key")
    if isinstance(logo_key, str) and logo_key:
        storage = get_storage()
        url = storage.url(logo_key)
        if url is not None:
            return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        data = await storage.get(logo_key)
        if data:
            return Response(content=data, media_type=_guess_media_type(logo_key))

    legacy_url = branding.get("logo_url")
    if isinstance(legacy_url, str) and legacy_url.startswith("/uploads/"):
        legacy_path = Path(get_settings().uploads_dir) / Path(legacy_url).name
        if legacy_path.is_file():
            return FileResponse(legacy_path)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found")
