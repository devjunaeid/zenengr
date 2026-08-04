"""Client management service -- business logic for client CRUD, archive, notes, activity."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_note import ClientNote
from app.models.enums import ActorType, ClientStatus, ClientType
from app.repositories import clients as client_repo
from app.services.audit import log as audit_log
from app.services.financials import get_client_financials, get_client_financials_batch
from app.services.limits import check_limit

# ── Exceptions ───────────────────────────────────────────────────────────────


class ClientNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )


class ClientAlreadyArchivedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client is already archived",
        )


class ClientNotArchivedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client is not archived",
        )


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def create_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    client_type: str = "company",
    email: str | None = None,
    phone: str | None = None,
    billing_address: dict[str, Any] | None = None,
    tax_id: str | None = None,
    tags: list[str] | None = None,
    actor_id: uuid.UUID,
) -> Client:
    """Create client. Checks plan limit first."""
    await check_limit(session, tenant_id, "clients")

    ct = ClientType(client_type)
    client = await client_repo.create(
        session,
        tenant_id=tenant_id,
        name=name,
        client_type=ct,
        email=email,
        phone=phone,
        billing_address=billing_address,
        tax_id=tax_id,
        tags=tags,
    )

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="client.created",
        entity_type="client",
        entity_id=str(client.id),
        details={"name": name, "client_type": client_type},
    )

    await session.commit()
    await session.refresh(client)
    return client


async def get_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client:
    """Get client scoped to tenant. Raises 404 if not found."""
    client = await client_repo.get_by_tenant_id_with_users(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()
    return client


async def get_client_detail(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> dict[str, Any]:
    """Get client detail with live financial rollup merged in (TODO-097).

    Keeps every existing client key and adds total_invoiced / total_paid /
    total_outstanding computed from the invoice + transaction tables.
    """
    client = await get_client(session, tenant_id=tenant_id, client_id=client_id)
    financials = await get_client_financials(session, client_id=client_id)
    return {
        "id": client.id,
        "tenant_id": client.tenant_id,
        "name": client.name,
        "client_type": client.client_type.value,
        "email": client.email,
        "phone": client.phone,
        "billing_address": client.billing_address,
        "tax_id": client.tax_id,
        "status": client.status.value,
        "tags": client.tags,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
        "client_users": client.client_users,
        "total_invoiced": financials["total_invoiced"],
        "total_paid": financials["total_paid"],
        "total_outstanding": financials["total_outstanding"],
    }


async def list_clients(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: ClientStatus | None = None,
    q: str | None = None,
    tag: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    """List clients with pagination, filtering, search, sort."""
    # Default to active if no status filter provided
    if status_filter is None:
        status_filter = ClientStatus.ACTIVE

    items, total = await client_repo.list_paginated(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status=status_filter,
        q=q,
        tag=tag,
        sort=sort,
    )

    result_items = []
    client_ids = [c.id for c in items]
    financials = await get_client_financials_batch(session, client_ids=client_ids)
    for c in items:
        fin = financials.get(c.id, {})
        result_items.append(
            {
                "id": c.id,
                "name": c.name,
                "client_type": c.client_type.value,
                "email": c.email,
                "phone": c.phone,
                "status": c.status.value,
                "tags": c.tags,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "active_projects": 0,  # TODO: wire to Project model
                "total_invoiced": fin.get("total_invoiced", "0.00"),
                "total_outstanding": fin.get("total_outstanding", "0.00"),
            }
        )

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def update_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    updates: dict[str, Any],
    actor_id: uuid.UUID,
) -> Client:
    """Update client fields. Tenant ID and status are immutable."""
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    # Filter out None values
    filtered = {k: v for k, v in updates.items() if v is not None}

    if not filtered:
        return client

    # Track changed keys for audit
    changed_keys = []
    for key, val in filtered.items():
        old_val = getattr(client, key, None)
        if old_val != val:
            changed_keys.append(key)
            setattr(client, key, val)

    if changed_keys:
        await session.flush()
        await session.refresh(client)

        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="client.updated",
            entity_type="client",
            entity_id=str(client.id),
            details={"changed_keys": changed_keys},
        )

        await session.commit()

    return client


async def archive_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Client:
    """Archive client (set status=archived). 409 if already archived."""
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    if client.status == ClientStatus.ARCHIVED:
        raise ClientAlreadyArchivedError()

    client.status = ClientStatus.ARCHIVED
    await session.flush()
    await session.refresh(client)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="client.archived",
        entity_type="client",
        entity_id=str(client.id),
    )

    await session.commit()
    return client


async def unarchive_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Client:
    """Unarchive client (set status=active). 409 if not archived."""
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    if client.status != ClientStatus.ARCHIVED:
        raise ClientNotArchivedError()

    client.status = ClientStatus.ACTIVE
    await session.flush()
    await session.refresh(client)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="client.unarchived",
        entity_type="client",
        entity_id=str(client.id),
    )

    await session.commit()
    return client


# ── Notes ────────────────────────────────────────────────────────────────────


async def add_note(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    body: str,
    author_id: uuid.UUID,
) -> ClientNote:
    """Add append-only note to client."""
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    note = ClientNote(
        client_id=client_id,
        author_id=author_id,
        body=body,
    )
    session.add(note)
    await session.flush()
    await session.refresh(note)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=author_id,
        actor_type=ActorType.ADMIN_USER,
        action="client.note_added",
        entity_type="client_note",
        entity_id=str(note.id),
        details={"client_id": str(client_id)},
    )

    await session.commit()
    return note


async def list_notes(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List notes for a client (newest first)."""
    # Verify client exists in this tenant
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    query = select(ClientNote).where(ClientNote.client_id == client_id)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = (
        query.order_by(ClientNote.created_at.desc(), ClientNote.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
    }


# ── Activity Timeline ────────────────────────────────────────────────────────


async def get_activity(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Get activity timeline for a client.

    Uses audit_logs where entity_type='client' OR details->>'client_id'=id.
    """
    # Verify client exists in this tenant
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    client_id_str = str(client_id)

    # Query audit logs: entity_type=client with entity_id matching,
    # OR details->>'client_id' matching
    query = select(AuditLog).where(
        AuditLog.tenant_id == tenant_id,
        ((AuditLog.entity_type == "client") & (AuditLog.entity_id == client_id_str))
        | (AuditLog.details["client_id"].astext == client_id_str),
    )

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── Tags ─────────────────────────────────────────────────────────────────────


async def get_distinct_tags(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[str]:
    """Get distinct tags across all clients for a tenant."""
    stmt = select(Client.tags).where(Client.tenant_id == tenant_id)
    result = await session.execute(stmt)
    all_tags: set[str] = set()
    for row in result.scalars().all():
        if row:
            all_tags.update(row)
    return sorted(all_tags)


# ── Client Profile Self-Update ───────────────────────────────────────────────


async def update_client_profile(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    email: str | None = None,
    phone: str | None = None,
    actor_id: uuid.UUID,
) -> Client:
    """Client self-service: update contact fields only (email, phone)."""
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise ClientNotFoundError()

    if client.status == ClientStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Archived clients cannot update profile",
        )

    updates = {}
    if email is not None:
        updates["email"] = email
    if phone is not None:
        updates["phone"] = phone

    if not updates:
        return client

    changed_keys = []
    for key, val in updates.items():
        old_val = getattr(client, key, None)
        if old_val != val:
            changed_keys.append(key)
            setattr(client, key, val)

    if changed_keys:
        await session.flush()
        await session.refresh(client)

        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.CLIENT_USER,
            action="client.contact_self_updated",
            entity_type="client",
            entity_id=str(client.id),
            details={"changed_keys": changed_keys},
        )

        await session.commit()

    return client
