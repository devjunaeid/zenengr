"""File storage service (FEAT-012, TODO-123/124/125/127/128/129/130/131/136/137).

B1 (provisioning):
- Root folders are provisioned lazily on first access (no startup seeding):
  "My files" (USER scope), "Team files" (TENANT scope),
  "Project files" (PROJECT scope) + one subfolder per project.

B2 (tenant file API):
- Folder CRUD + tree, scoped upload, listing, auth-gated download,
  delete/rename/move with RBAC, quota enforcement, audit trail.
- USER scope has no folders (virtual "My files" root): user files with
  folder_id NULL belong to the caller only. TENANT/PROJECT folders and files
  are visible to all tenant staff.
"""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.admin_user import AdminUser
from app.models.enums import ActorType, AdminUserRole, FileScope
from app.models.file_asset import FileAsset
from app.models.file_folder import FileFolder
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant
from app.schemas.files import FolderTreeNode
from app.services.audit import log as audit_log
from app.storage import get_storage

# Root folder names by scope. Created lazily per tenant on first access.
ROOT_NAMES: dict[str, FileScope] = {
    "My files": FileScope.USER,
    "Team files": FileScope.TENANT,
    "Project files": FileScope.PROJECT,
}

# created_by_type recorded on provisioned folders ("admin_user" | "client_user").
_DEFAULT_CREATED_BY_TYPE = "admin_user"


# ── Exceptions ──────────────────────────────────────────────────────────────


class FileFolderNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )


class FileFolderNameConflictError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A folder with this name already exists here",
        )


class FileFolderNotEmptyError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder must be empty before deletion",
        )


class FileFolderScopeError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Folder scope does not match the requested operation",
        )


class FileProjectRequiredError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Project scope requires project_id",
        )


class FileProjectNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


class FileAssetNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )


class FileAccessDeniedError(HTTPException):
    """404 for unauthorized access (leak prevention — no existence leak)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )


class FileQuotaExceededError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Storage quota exceeded",
        )


class FileTooLargeError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds the maximum upload size",
        )


class FileContentError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Empty file upload",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _can_manage_files(user: AdminUser) -> bool:
    """Admin and manager roles can manage tenant/project files (RBAC matrix)."""
    return user.role in (AdminUserRole.ADMIN, AdminUserRole.MANAGER)


async def _get_folder_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    folder_id: uuid.UUID,
) -> FileFolder:
    stmt = select(FileFolder).where(
        FileFolder.id == folder_id,
        FileFolder.tenant_id == tenant_id,
    )
    folder = (await session.execute(stmt)).scalar_one_or_none()
    if folder is None:
        raise FileFolderNotFoundError()
    return folder


async def _get_asset_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
) -> FileAsset:
    stmt = select(FileAsset).where(
        FileAsset.id == file_id,
        FileAsset.tenant_id == tenant_id,
    )
    asset = (await session.execute(stmt)).scalar_one_or_none()
    if asset is None:
        raise FileAssetNotFoundError()
    return asset


async def get_tenant_storage_used(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> int:
    """Total bytes stored by a tenant (sum of FileAsset.size_bytes)."""
    stmt = select(func.coalesce(func.sum(FileAsset.size_bytes), 0)).where(
        FileAsset.tenant_id == tenant_id
    )
    return int((await session.execute(stmt)).scalar_one())


def _visible_folder_query(tenant_id: uuid.UUID) -> Select[tuple[FileFolder]]:
    """Tenant-scoped folders; USER folders excluded (USER has no folders)."""
    return select(FileFolder).where(
        FileFolder.tenant_id == tenant_id,
        FileFolder.scope != FileScope.USER,
    )


def _build_storage_key(
    tenant_id: uuid.UUID,
    scope: FileScope,
    content_type: str,
    filename: str,
) -> str:
    """Key = {tenant_id}/{scope}/{random-hex}{ext}. Ext from content type,
    falling back to the sanitized filename suffix."""
    ext = mimetypes.guess_extension(content_type or "")
    if not ext:
        ext = ""
        suffix = Path(filename).suffix.lower()
        if suffix and len(suffix) <= 11 and suffix[1:].isalnum():
            ext = suffix
    return f"{tenant_id}/{scope.value}/{uuid.uuid4().hex}{ext}"


def _asset_access_ok(asset: FileAsset, actor_id: uuid.UUID, is_manager: bool) -> bool:
    """USER files: creator only. TENANT/PROJECT files: manager only for
    mutations; reads are allowed for all staff (checked in read helpers)."""
    if asset.scope == FileScope.USER:
        return asset.created_by_id == actor_id
    return is_manager


# ── B1: root folder provisioning ────────────────────────────────────────────


async def ensure_root_folders(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Get-or-create the three tenant root folders. Returns {name: folder_id}.

    Idempotent: repeated calls return the same folder ids. Commits once.
    """
    result: dict[str, uuid.UUID] = {}
    for name, scope in ROOT_NAMES.items():
        folder = await _get_or_create_folder(
            session,
            tenant_id=tenant_id,
            parent_id=None,
            name=name,
            scope=scope,
            project_id=None,
            actor_id=actor_id,
        )
        result[name] = folder.id
    await session.commit()
    return result


async def get_project_folder(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> FileFolder | None:
    """Get-or-create the "Project files" root and a per-project subfolder.

    Subfolder name = project name. Returns None if the project does not
    exist or belongs to another tenant. Commits once.
    """
    project = await session.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        return None

    root = await _get_or_create_folder(
        session,
        tenant_id=tenant_id,
        parent_id=None,
        name="Project files",
        scope=FileScope.PROJECT,
        project_id=None,
        actor_id=actor_id,
    )
    subfolder = await _get_or_create_folder(
        session,
        tenant_id=tenant_id,
        parent_id=root.id,
        name=project.name,
        scope=FileScope.PROJECT,
        project_id=project_id,
        actor_id=actor_id,
    )
    await session.commit()
    return subfolder


async def _get_or_create_folder(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    name: str,
    scope: FileScope,
    project_id: uuid.UUID | None,
    actor_id: uuid.UUID,
) -> FileFolder:
    """Look up by the unique key (tenant_id, parent_id, scope, name, project_id);
    create if absent."""
    q = select(FileFolder).where(
        FileFolder.tenant_id == tenant_id,
        FileFolder.parent_id == parent_id,
        FileFolder.scope == scope,
        FileFolder.name == name,
        FileFolder.project_id == project_id,
    )
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing is not None:
        return existing

    folder = FileFolder(
        tenant_id=tenant_id,
        parent_id=parent_id,
        name=name,
        scope=scope,
        project_id=project_id,
        created_by_id=actor_id,
        created_by_type=_DEFAULT_CREATED_BY_TYPE,
    )
    session.add(folder)
    await session.flush()
    return folder


# ── B2: folders ─────────────────────────────────────────────────────────────


async def list_folder_tree(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> list[FolderTreeNode]:
    """Return the visible folder tree.

    Roots: virtual "My files" (USER, no DB row; the caller's folder-less
    USER files surface under it in the UI) plus the real TENANT "Team files"
    and PROJECT "Project files" roots with nested children (provisioned
    lazily on first access), plus any user-created root-level folders.
    USER folder rows are excluded — USER has no folders in B2.
    """
    await ensure_root_folders(session, tenant_id=tenant_id, actor_id=actor_id)

    rows = list(
        (await session.execute(_visible_folder_query(tenant_id).order_by(FileFolder.name)))
        .scalars()
        .all()
    )
    children_map: dict[uuid.UUID | None, list[FileFolder]] = {}
    for folder in rows:
        children_map.setdefault(folder.parent_id, []).append(folder)

    def build(parent_id: uuid.UUID | None) -> list[FolderTreeNode]:
        nodes: list[FolderTreeNode] = []
        for folder in sorted(children_map.get(parent_id, []), key=lambda f: f.name):
            nodes.append(
                FolderTreeNode(
                    id=folder.id,
                    name=folder.name,
                    scope=folder.scope,
                    project_id=folder.project_id,
                    children=build(folder.id),
                )
            )
        return nodes

    my_files = FolderTreeNode(
        id=None,
        name="My files",
        scope=FileScope.USER,
        project_id=None,
        children=[],
    )
    return [my_files] + build(None)


async def create_folder(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    parent_id: uuid.UUID | None,
    scope: FileScope,
    project_id: uuid.UUID | None,
    actor_id: uuid.UUID,
) -> FileFolder:
    """Create a TENANT or PROJECT folder (USER folders are rejected)."""
    if scope == FileScope.USER:
        raise FileFolderScopeError()

    if scope == FileScope.PROJECT:
        if project_id is None:
            raise FileProjectRequiredError()
        project = await session.get(Project, project_id)
        if project is None or project.tenant_id != tenant_id:
            raise FileProjectNotFoundError()
        if parent_id is not None:
            parent = await _get_folder_for_tenant(session, tenant_id, parent_id)
            # Parent must be the PROJECT root or a PROJECT folder of the same project.
            if parent.scope != FileScope.PROJECT or (
                parent.project_id is not None and parent.project_id != project_id
            ):
                raise FileFolderScopeError()
    else:  # TENANT
        if parent_id is not None:
            parent = await _get_folder_for_tenant(session, tenant_id, parent_id)
            if parent.scope != FileScope.TENANT:
                raise FileFolderScopeError()

    await _ensure_folder_name_available(
        session,
        tenant_id=tenant_id,
        parent_id=parent_id,
        scope=scope,
        name=name,
        project_id=project_id,
    )

    folder = FileFolder(
        tenant_id=tenant_id,
        parent_id=parent_id,
        name=name,
        scope=scope,
        project_id=project_id,
        created_by_id=actor_id,
        created_by_type=_DEFAULT_CREATED_BY_TYPE,
    )
    session.add(folder)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="file.folder_created",
        entity_type="folder",
        entity_id=str(folder.id),
        details={
            "name": name,
            "scope": scope.value,
            "parent_id": str(parent_id) if parent_id is not None else None,
        },
    )
    await session.commit()
    return folder


async def rename_folder(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    folder_id: uuid.UUID,
    name: str,
    actor_id: uuid.UUID,
    is_manager: bool,
) -> FileFolder:
    """Rename a folder (manage/files role gate enforced by the router)."""
    folder = await _get_folder_for_tenant(session, tenant_id, folder_id)
    if folder.name != name:
        await _ensure_folder_name_available(
            session,
            tenant_id=tenant_id,
            parent_id=folder.parent_id,
            scope=folder.scope,
            name=name,
            project_id=folder.project_id,
        )
    old_name = folder.name
    folder.name = name
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="file.folder_renamed",
        entity_type="folder",
        entity_id=str(folder.id),
        details={"old_name": old_name, "new_name": name},
    )
    await session.commit()
    return folder


async def delete_folder(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    folder_id: uuid.UUID,
    actor_id: uuid.UUID,
    is_manager: bool,
) -> None:
    """Delete an empty folder (manage/files role gate enforced by the router)."""
    folder = await _get_folder_for_tenant(session, tenant_id, folder_id)

    child_stmt = select(FileFolder.id).where(FileFolder.parent_id == folder.id)
    has_children = (await session.execute(child_stmt)).first() is not None
    file_stmt = select(FileAsset.id).where(FileAsset.folder_id == folder.id)
    has_files = (await session.execute(file_stmt)).first() is not None
    if has_children or has_files:
        raise FileFolderNotEmptyError()

    await session.delete(folder)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="file.folder_deleted",
        entity_type="folder",
        entity_id=str(folder.id),
        details={"name": folder.name},
    )
    await session.commit()


async def _ensure_folder_name_available(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    scope: FileScope,
    name: str,
    project_id: uuid.UUID | None,
) -> None:
    """Raise 409 when a sibling folder with the same key already exists."""
    q = select(FileFolder).where(
        FileFolder.tenant_id == tenant_id,
        FileFolder.parent_id == parent_id,
        FileFolder.scope == scope,
        FileFolder.name == name,
        FileFolder.project_id == project_id,
    )
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing is not None:
        raise FileFolderNameConflictError()


# ── B2: files ───────────────────────────────────────────────────────────────


async def upload_file(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_type: str,
    filename: str,
    content: bytes,
    content_type: str,
    scope: FileScope,
    folder_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
) -> FileAsset:
    """Upload a file into the given visibility scope (all staff may upload).

    - scope USER: no folder (virtual root); the file belongs to the actor.
    - scope TENANT: optional folder must be TENANT-scope.
    - scope PROJECT: project_id required (tenant-owned); optional folder must
      be PROJECT-scope and belong to the same project.
    Enforces the per-file size cap and the tenant plan storage quota.
    """
    if not content:
        raise FileContentError()
    settings = get_settings()
    if len(content) > settings.file_max_upload_mb * 1024 * 1024:
        raise FileTooLargeError()

    if scope == FileScope.USER:
        if folder_id is not None:
            raise FileFolderScopeError()
    elif scope == FileScope.TENANT:
        if folder_id is not None:
            folder = await _get_folder_for_tenant(session, tenant_id, folder_id)
            if folder.scope != FileScope.TENANT:
                raise FileFolderScopeError()
    elif scope == FileScope.PROJECT:
        if project_id is None:
            raise FileProjectRequiredError()
        project = await session.get(Project, project_id)
        if project is None or project.tenant_id != tenant_id:
            raise FileProjectNotFoundError()
        if folder_id is not None:
            folder = await _get_folder_for_tenant(session, tenant_id, folder_id)
            if folder.scope != FileScope.PROJECT or folder.project_id != project_id:
                raise FileFolderScopeError()
    else:
        raise FileFolderScopeError()

    tenant = await session.get(Tenant, tenant_id)
    plan = await session.get(Plan, tenant.plan_id) if tenant is not None else None
    if plan is not None:
        used = await get_tenant_storage_used(session, tenant_id=tenant_id)
        if used + len(content) > plan.max_storage_mb * 1024 * 1024:
            raise FileQuotaExceededError()

    storage_key = _build_storage_key(tenant_id, scope, content_type, filename)
    sha256 = hashlib.sha256(content).hexdigest()
    await get_storage().put(storage_key, content, content_type)

    asset = FileAsset(
        tenant_id=tenant_id,
        folder_id=folder_id,
        scope=scope,
        project_id=project_id,
        created_by_id=actor_id,
        created_by_type=actor_type,
        name=filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    session.add(asset)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType(actor_type),
        action="file.uploaded",
        entity_type="file",
        entity_id=str(asset.id),
        details={
            "scope": scope.value,
            "project_id": str(project_id) if project_id is not None else None,
            "size_bytes": len(content),
        },
    )
    await session.commit()
    return asset


async def list_files(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    folder_id: uuid.UUID | None,
    scope: FileScope | None,
    project_id: uuid.UUID | None,
    page: int,
    page_size: int,
    q: str | None,
) -> dict[str, Any]:
    """List files tenant-scoped.

    - scope USER: only the caller's own files with folder_id NULL
      (virtual "My files" root).
    - folder_id given: files inside that folder (TENANT/PROJECT folders are
      visible to all staff; USER folders are excluded).
    - optional q: name ILIKE filter. Ordered by created_at desc.
    """
    query = select(FileAsset).where(FileAsset.tenant_id == tenant_id)

    if folder_id is not None:
        folder = await _get_folder_for_tenant(session, tenant_id, folder_id)
        if folder.scope == FileScope.USER:
            raise FileFolderNotFoundError()
        query = query.where(FileAsset.folder_id == folder_id)
    elif scope == FileScope.USER:
        query = query.where(
            FileAsset.scope == FileScope.USER,
            FileAsset.created_by_id == actor_id,
            FileAsset.folder_id.is_(None),
        )
    elif scope is not None:
        query = query.where(FileAsset.scope == scope)

    if project_id is not None:
        query = query.where(FileAsset.project_id == project_id)
    if q:
        query = query.where(FileAsset.name.ilike(f"%{q}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    stmt = (
        query.order_by(FileAsset.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_file_for_access(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_type: str,
) -> FileAsset:
    """Fetch a file with access rules: USER files are creator-only;
    TENANT/PROJECT files are visible to all tenant staff (client rules later)."""
    asset = await _get_asset_for_tenant(session, tenant_id, file_id)
    if asset.scope == FileScope.USER and asset.created_by_id != actor_id:
        raise FileAccessDeniedError()
    return asset


async def list_project_files_for_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    project_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List PROJECT-scope files for a client's own project (client portal).

    The project must exist, belong to the tenant, and belong to the client
    (404 otherwise — no existence leak). Files may live in any project folder
    or at the project root (folder_id NULL).
    """
    project = await session.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id or project.client_id != client_id:
        raise FileProjectNotFoundError()

    query = select(FileAsset).where(
        FileAsset.tenant_id == tenant_id,
        FileAsset.scope == FileScope.PROJECT,
        FileAsset.project_id == project_id,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    stmt = (
        query.order_by(FileAsset.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = list((await session.execute(stmt)).scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_file_for_client_access(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    file_id: uuid.UUID,
) -> FileAsset:
    """Fetch a file a client user may access: PROJECT scope only, and the
    file's project must belong to the caller's client (404 otherwise)."""
    asset = await _get_asset_for_tenant(session, tenant_id, file_id)
    if asset.scope != FileScope.PROJECT or asset.project_id is None:
        raise FileAccessDeniedError()
    project = await session.get(Project, asset.project_id)
    if project is None or project.tenant_id != tenant_id or project.client_id != client_id:
        raise FileAccessDeniedError()
    return asset


async def get_file_content_for_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    file_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_type: str,
) -> tuple[bytes | None, str | None, FileAsset]:
    """Client-portal download: (bytes, presigned_url, asset) — exactly one of
    bytes/url is set. Same content logic as the tenant path; only PROJECT
    files are reachable and every download is audited (client rule: all
    client-visible files are PROJECT scope)."""
    asset = await get_file_for_client_access(
        session,
        tenant_id=tenant_id,
        client_id=client_id,
        file_id=file_id,
    )

    presigned = get_storage().url(asset.storage_key)
    if presigned is not None:
        await _log_file_download(session, tenant_id, asset, actor_id, actor_type)
        return None, presigned, asset

    content = await get_storage().get(asset.storage_key)
    await _log_file_download(session, tenant_id, asset, actor_id, actor_type)
    return content, None, asset


async def get_file_content(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_type: str,
) -> tuple[bytes | None, str | None, FileAsset]:
    """Return (bytes, presigned_url, asset): exactly one of bytes/url is set.

    Presigned URL path is used when the backend supports browser-usable URLs
    (S3); local backend streams bytes through the auth-gated endpoint.
    PROJECT-scope downloads are audited ("file.downloaded").
    """
    asset = await get_file_for_access(
        session,
        tenant_id=tenant_id,
        file_id=file_id,
        actor_id=actor_id,
        actor_type=actor_type,
    )

    presigned = get_storage().url(asset.storage_key)
    if presigned is not None:
        if asset.scope == FileScope.PROJECT:
            await _log_file_download(session, tenant_id, asset, actor_id, actor_type)
        return None, presigned, asset

    content = await get_storage().get(asset.storage_key)
    if asset.scope == FileScope.PROJECT:
        await _log_file_download(session, tenant_id, asset, actor_id, actor_type)
    return content, None, asset


async def delete_file(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    actor_id: uuid.UUID,
    is_manager: bool,
) -> None:
    """Delete a file: USER files by their creator; TENANT/PROJECT files by
    admin/manager only (404 for unauthorized — no existence leak)."""
    asset = await _get_asset_for_tenant(session, tenant_id, file_id)
    if not _asset_access_ok(asset, actor_id, is_manager):
        raise FileAccessDeniedError()

    await get_storage().delete(asset.storage_key)
    await session.delete(asset)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="file.deleted",
        entity_type="file",
        entity_id=str(asset.id),
        details={"name": asset.name},
    )
    await session.commit()


async def rename_file(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    name: str,
    actor_id: uuid.UUID,
    is_manager: bool,
) -> FileAsset:
    """Rename a file (same access rules as delete)."""
    asset = await _get_asset_for_tenant(session, tenant_id, file_id)
    if not _asset_access_ok(asset, actor_id, is_manager):
        raise FileAccessDeniedError()

    asset.name = name
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="file.renamed",
        entity_type="file",
        entity_id=str(asset.id),
        details={"name": name},
    )
    await session.commit()
    return asset


async def move_file(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    folder_id: uuid.UUID | None,
    actor_id: uuid.UUID,
    is_manager: bool,
) -> FileAsset:
    """Move a file (same access rules as delete). Target folder must have the
    same scope as the file; None moves to the scope root (no folder)."""
    asset = await _get_asset_for_tenant(session, tenant_id, file_id)
    if not _asset_access_ok(asset, actor_id, is_manager):
        raise FileAccessDeniedError()

    if folder_id is not None:
        folder = await _get_folder_for_tenant(session, tenant_id, folder_id)
        if folder.scope == FileScope.USER:
            raise FileFolderScopeError()
        if folder.scope == FileScope.TENANT and asset.scope != FileScope.TENANT:
            raise FileFolderScopeError()
        if folder.scope == FileScope.PROJECT:
            if asset.scope != FileScope.PROJECT:
                raise FileFolderScopeError()
            if asset.project_id != folder.project_id:
                raise FileFolderScopeError()

    asset.folder_id = folder_id
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="file.moved",
        entity_type="file",
        entity_id=str(asset.id),
        details={
            "folder_id": str(folder_id) if folder_id is not None else None,
        },
    )
    await session.commit()
    return asset


async def _log_file_download(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    asset: FileAsset,
    actor_id: uuid.UUID,
    actor_type: str,
) -> None:
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType(actor_type),
        action="file.downloaded",
        entity_type="file",
        entity_id=str(asset.id),
        details={"file_id": str(asset.id), "name": asset.name},
    )
    await session.commit()
