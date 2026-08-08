"""Tenant-scoped client management endpoints.

Base path: /api/v1/tenant/clients
Guard: manage/clients = admin+manager for writes; employee = view only on GETs.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import ClientStatus
from app.schemas.clients import (
    ClientActivityEntry,
    ClientActivityResponse,
    ClientArchiveResponse,
    ClientCreateRequest,
    ClientDetailResponse,
    ClientListItem,
    ClientListResponse,
    ClientNoteCreateRequest,
    ClientNoteListResponse,
    ClientNoteResponse,
    ClientTagsResponse,
    ClientUpdateRequest,
    ClientUserSummary,
)
from app.schemas.transactions import ClientLedgerResponse
from app.services import clients as client_service
from app.services import transactions as transaction_service

router = APIRouter(prefix="/tenant/clients", tags=["clients"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    """Extract tenant_id from user or raise 403."""
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=ClientListItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_client_endpoint(
    body: ClientCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "clients")),
) -> ClientListItem:
    """Create a new client. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    client = await client_service.create_client(
        session,
        tenant_id=tenant_id,
        name=body.name,
        client_type=body.client_type,
        email=body.email,
        phone=body.phone,
        billing_address=body.billing_address,
        tax_id=body.tax_id,
        tags=body.tags,
        actor_id=user.id,
    )
    return ClientListItem(
        id=client.id,
        name=client.name,
        client_type=client.client_type.value,
        email=client.email,
        phone=client.phone,
        status=client.status.value,
        tags=client.tags,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.get("/", response_model=ClientListResponse)
async def list_clients_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_val: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=1),
    tag: str | None = Query(default=None, min_length=1),
    sort: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ClientListResponse:
    """List clients with pagination, filtering, search. All staff can view."""
    tenant_id = _get_tenant_id(user)

    status_filter = None
    if status_val:
        try:
            status_filter = ClientStatus(status_val)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid status: {status_val}. Must be 'active' or 'archived'.",
            ) from None

    result = await client_service.list_clients(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        q=q,
        tag=tag,
        sort=sort,
    )

    items = [ClientListItem(**item) for item in result["items"]]
    return ClientListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/tags", response_model=ClientTagsResponse)
async def list_tags_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ClientTagsResponse:
    """Get distinct tags across all clients for this tenant."""
    tenant_id = _get_tenant_id(user)
    tags = await client_service.get_distinct_tags(session, tenant_id=tenant_id)
    return ClientTagsResponse(tags=tags)


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client_endpoint(
    client_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ClientDetailResponse:
    """Get client detail with client_users and recent activity."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    client = await client_service.get_client_detail(session, tenant_id=tenant_id, client_id=cid)

    # Get recent 10 activity entries
    activity = await client_service.get_activity(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        page=1,
        page_size=10,
    )

    client_users = [
        ClientUserSummary(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_primary_billing_contact=u.is_primary_billing_contact,
        )
        for u in client["client_users"]
    ]

    recent_activity = [
        {
            "id": e.id,
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "details": e.details,
            "actor_id": e.actor_id,
            "actor_type": e.actor_type,
            "created_at": e.created_at.isoformat(),
        }
        for e in activity["items"]
    ]

    return ClientDetailResponse(
        id=client["id"],
        tenant_id=client["tenant_id"],
        name=client["name"],
        client_type=client["client_type"],
        email=client["email"],
        phone=client["phone"],
        billing_address=client["billing_address"],
        tax_id=client["tax_id"],
        status=client["status"],
        tags=client["tags"],
        created_at=client["created_at"],
        updated_at=client["updated_at"],
        client_users=client_users,
        recent_activity=recent_activity,
        total_invoiced=client["total_invoiced"],
        total_paid=client["total_paid"],
        total_outstanding=client["total_outstanding"],
    )


@router.get("/{client_id}/ledger", response_model=ClientLedgerResponse)
async def get_client_ledger_endpoint(
    client_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ClientLedgerResponse:
    """Client ledger: advance balance + signed money entries. All staff can view."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    client = await session.get(Client, cid)
    if client is None or client.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    result = await transaction_service.build_client_ledger(
        session,
        tenant_id=tenant_id,
        client_id=cid,
    )
    return ClientLedgerResponse(**result)


@router.patch("/{client_id}", response_model=ClientListItem)
async def update_client_endpoint(
    client_id: str,
    body: ClientUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "clients")),
) -> ClientListItem:
    """Update client fields. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    updates = body.model_dump(exclude_unset=True)

    # tenant_id and status are immutable
    forbidden = {"tenant_id", "status"}
    if forbidden & set(updates.keys()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Fields 'tenant_id' and 'status' are immutable. Use archive/unarchive for status."
            ),
        )

    client = await client_service.update_client(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        updates=updates,
        actor_id=user.id,
    )

    return ClientListItem(
        id=client.id,
        name=client.name,
        client_type=client.client_type.value,
        email=client.email,
        phone=client.phone,
        status=client.status.value,
        tags=client.tags,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Archive / Unarchive
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{client_id}/archive",
    response_model=ClientArchiveResponse,
)
async def archive_client_endpoint(
    client_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "clients")),
) -> ClientArchiveResponse:
    """Archive client. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    client = await client_service.archive_client(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        actor_id=user.id,
    )

    return ClientArchiveResponse(
        id=client.id,
        name=client.name,
        status=client.status.value,
    )


@router.post(
    "/{client_id}/unarchive",
    response_model=ClientArchiveResponse,
)
async def unarchive_client_endpoint(
    client_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "clients")),
) -> ClientArchiveResponse:
    """Unarchive client. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    client = await client_service.unarchive_client(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        actor_id=user.id,
    )

    return ClientArchiveResponse(
        id=client.id,
        name=client.name,
        status=client.status.value,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Notes (internal-only)
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{client_id}/notes",
    response_model=ClientNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_note_endpoint(
    client_id: str,
    body: ClientNoteCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "clients")),
) -> ClientNoteResponse:
    """Add note to client. Admin/Manager only. Append-only."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    note = await client_service.add_note(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        body=body.body,
        author_id=user.id,
    )

    return ClientNoteResponse(
        id=note.id,
        body=note.body,
        author_id=note.author_id,
        author_name=note.author.full_name if note.author else None,
        created_at=note.created_at,
    )


@router.get(
    "/{client_id}/notes",
    response_model=ClientNoteListResponse,
)
async def list_notes_endpoint(
    client_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ClientNoteListResponse:
    """List notes for client. All staff can view (employee included)."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    result = await client_service.list_notes(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        page=page,
        page_size=page_size,
    )

    items = [
        ClientNoteResponse(
            id=n.id,
            body=n.body,
            author_id=n.author_id,
            author_name=n.author.full_name if n.author else None,
            created_at=n.created_at,
        )
        for n in result["items"]
    ]

    return ClientNoteListResponse(items=items, total=result["total"])


# ═══════════════════════════════════════════════════════════════════════════
# Activity Timeline
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/{client_id}/activity",
    response_model=ClientActivityResponse,
)
async def get_activity_endpoint(
    client_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ClientActivityResponse:
    """Get activity timeline for client. All staff can view."""
    tenant_id = _get_tenant_id(user)

    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    result = await client_service.get_activity(
        session,
        tenant_id=tenant_id,
        client_id=cid,
        page=page,
        page_size=page_size,
    )

    entries = [ClientActivityEntry.model_validate(e) for e in result["items"]]

    return ClientActivityResponse(
        items=entries,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
