"""Client-scoped file content endpoints (FEAT-012, TODO-132).

Base path: /api/v1/client/files
Read-only: clients download PROJECT-scope files on their own client's
projects; anything else (other clients' files, TENANT/USER scope) returns
404. Downloads are audited with actor_type CLIENT_USER.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_client_user
from app.db.session import get_session
from app.models.client_user import ClientUser
from app.models.enums import ActorType
from app.services import files as files_service

router = APIRouter(prefix="/client/files", tags=["client-files"])


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


@router.get("/{file_id}/content")
async def get_client_file_content_endpoint(
    file_id: str,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> Response:
    """Download a file (own client only). Presigned URL (S3) redirects with
    307, local backend streams bytes as an attachment. PROJECT downloads are
    audited."""
    fid = _parse_uuid(file_id, kind="File")
    content, presigned, asset = await files_service.get_file_content_for_client(
        session,
        tenant_id=user.tenant_id,
        client_id=user.client_id,
        file_id=fid,
        actor_id=user.id,
        actor_type=ActorType.CLIENT_USER.value,
    )
    if presigned is not None:
        return RedirectResponse(presigned, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return Response(
        content=content or b"",
        media_type=asset.content_type,
        headers={"Content-Disposition": f'attachment; filename="{asset.name}"'},
    )
