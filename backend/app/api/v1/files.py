"""Tenant-scoped file endpoints (FEAT-012, TODO-127/128/129/130/131/136).

Base path: /api/v1/tenant/files
Guards: manage/files = admin+manager for folder writes; uploads and reads
allow all staff (role rules enforced in the service: USER files are
creator-scoped; TENANT/PROJECT mutations require admin/manager).
"""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import ActorType, FileScope
from app.models.file_asset import FileAsset
from app.models.file_folder import FileFolder
from app.schemas.files import (
    FileAssetItem,
    FileListResponse,
    FileMoveRequest,
    FileRenameRequest,
    FolderCreateRequest,
    FolderItem,
    FolderRenameRequest,
    FolderTreeNode,
)
from app.services import files as files_service

router = APIRouter(prefix="/tenant/files", tags=["files"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


def _to_folder_item(folder: FileFolder) -> FolderItem:
    return FolderItem(
        id=folder.id,
        name=folder.name,
        scope=folder.scope,
        parent_id=folder.parent_id,
        project_id=folder.project_id,
        created_at=folder.created_at,
    )


def _to_asset_item(asset: FileAsset) -> FileAssetItem:
    return FileAssetItem(
        id=asset.id,
        name=asset.name,
        scope=asset.scope,
        folder_id=asset.folder_id,
        project_id=asset.project_id,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        created_by_id=asset.created_by_id,
        created_by_type=asset.created_by_type,
        created_at=asset.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Folders
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/folders", response_model=list[FolderTreeNode])
async def list_folder_tree_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[FolderTreeNode]:
    """Folder tree (incl. virtual "My files" root). All staff can read."""
    tenant_id = _get_tenant_id(user)
    return await files_service.list_folder_tree(session, tenant_id=tenant_id, actor_id=user.id)


@router.post(
    "/folders",
    response_model=FolderItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder_endpoint(
    body: FolderCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "files")),
) -> FolderItem:
    """Create a TENANT or PROJECT folder. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    folder = await files_service.create_folder(
        session,
        tenant_id=tenant_id,
        name=body.name,
        parent_id=body.parent_id,
        scope=body.scope,
        project_id=body.project_id,
        actor_id=user.id,
    )
    return _to_folder_item(folder)


@router.patch("/folders/{folder_id}", response_model=FolderItem)
async def rename_folder_endpoint(
    folder_id: str,
    body: FolderRenameRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "files")),
) -> FolderItem:
    """Rename a folder. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(folder_id, kind="Folder")
    folder = await files_service.rename_folder(
        session,
        tenant_id=tenant_id,
        folder_id=fid,
        name=body.name,
        actor_id=user.id,
        is_manager=files_service._can_manage_files(user),
    )
    return _to_folder_item(folder)


@router.delete(
    "/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_folder_endpoint(
    folder_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "files")),
) -> Response:
    """Delete an empty folder. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(folder_id, kind="Folder")
    await files_service.delete_folder(
        session,
        tenant_id=tenant_id,
        folder_id=fid,
        actor_id=user.id,
        is_manager=files_service._can_manage_files(user),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════════
# Files
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/upload",
    response_model=FileAssetItem,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    scope: FileScope = Form(...),
    folder_id: str | None = Form(default=None),
    project_id: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> FileAssetItem:
    """Multipart upload into a visibility scope. All staff may upload; USER
    files are creator-scoped, TENANT/PROJECT visibility rules are enforced
    in the service."""
    tenant_id = _get_tenant_id(user)
    content = await file.read()
    parsed_folder_id = _parse_uuid(folder_id, kind="Folder") if folder_id else None
    parsed_project_id = _parse_uuid(project_id, kind="Project") if project_id else None
    asset = await files_service.upload_file(
        session,
        tenant_id=tenant_id,
        actor_id=user.id,
        actor_type=ActorType.ADMIN_USER.value,
        filename=file.filename or "unnamed",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        scope=scope,
        folder_id=parsed_folder_id,
        project_id=parsed_project_id,
    )
    return _to_asset_item(asset)


@router.get("/", response_model=FileListResponse)
async def list_files_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    folder_id: str | None = Query(default=None),
    scope: FileScope | None = Query(default=None),
    project_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> FileListResponse:
    """List files for a tenant with optional scope/folder/project/q filters."""
    tenant_id = _get_tenant_id(user)
    parsed_folder_id = _parse_uuid(folder_id, kind="Folder") if folder_id else None
    parsed_project_id = _parse_uuid(project_id, kind="Project") if project_id else None
    result = await files_service.list_files(
        session,
        tenant_id=tenant_id,
        actor_id=user.id,
        folder_id=parsed_folder_id,
        scope=scope,
        project_id=parsed_project_id,
        page=page,
        page_size=page_size,
        q=q,
    )
    return FileListResponse(
        items=[_to_asset_item(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{file_id}", response_model=FileAssetItem)
async def get_file_endpoint(
    file_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> FileAssetItem:
    """File metadata. Access-checked (USER files are creator-only)."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(file_id, kind="File")
    asset = await files_service.get_file_for_access(
        session,
        tenant_id=tenant_id,
        file_id=fid,
        actor_id=user.id,
        actor_type=ActorType.ADMIN_USER.value,
    )
    return _to_asset_item(asset)


@router.get("/{file_id}/content")
async def get_file_content_endpoint(
    file_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> Response:
    """Download a file. Access-checked; presigned URL (S3) redirects with 307,
    local backend streams bytes as an attachment. PROJECT downloads are audited."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(file_id, kind="File")
    content, presigned, asset = await files_service.get_file_content(
        session,
        tenant_id=tenant_id,
        file_id=fid,
        actor_id=user.id,
        actor_type=ActorType.ADMIN_USER.value,
    )
    if presigned is not None:
        return RedirectResponse(presigned, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return Response(
        content=content or b"",
        media_type=asset.content_type,
        headers={"Content-Disposition": f'attachment; filename="{asset.name}"'},
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_file_endpoint(
    file_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> Response:
    """Delete a file. All staff may attempt; the service decides: USER files
    by their creator, TENANT/PROJECT files by admin/manager only."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(file_id, kind="File")
    await files_service.delete_file(
        session,
        tenant_id=tenant_id,
        file_id=fid,
        actor_id=user.id,
        is_manager=files_service._can_manage_files(user),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{file_id}", response_model=FileAssetItem)
async def rename_file_endpoint(
    file_id: str,
    body: FileRenameRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> FileAssetItem:
    """Rename a file (same access rules as delete)."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(file_id, kind="File")
    asset = await files_service.rename_file(
        session,
        tenant_id=tenant_id,
        file_id=fid,
        name=body.name,
        actor_id=user.id,
        is_manager=files_service._can_manage_files(user),
    )
    return _to_asset_item(asset)


@router.post("/{file_id}/move", response_model=FileAssetItem)
async def move_file_endpoint(
    file_id: str,
    body: FileMoveRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> FileAssetItem:
    """Move a file into a same-scope folder (or scope root when folder_id is
    null). Same access rules as delete."""
    tenant_id = _get_tenant_id(user)
    fid = _parse_uuid(file_id, kind="File")
    asset = await files_service.move_file(
        session,
        tenant_id=tenant_id,
        file_id=fid,
        folder_id=body.folder_id,
        actor_id=user.id,
        is_manager=files_service._can_manage_files(user),
    )
    return _to_asset_item(asset)
