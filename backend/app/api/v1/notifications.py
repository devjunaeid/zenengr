"""Notifications REST API — staff + client realms (FEAT-017, TODO-172).

Staff:  /api/v1/tenant/notifications...
Client: /api/v1/client/notifications...

Both expose the same surface: paginated list, unread count, mark one
read, mark all read. Read state is per user; rows never leave the owner's
tenant scope. mark-read is not audited (read-state churn).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, get_current_client_user
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.client_user import ClientUser
from app.schemas.notifications import NotificationListResponse, UnreadCountResponse
from app.services import notifications as notification_service

router = APIRouter(prefix="/tenant/notifications", tags=["notifications"])
client_router = APIRouter(prefix="/client/notifications", tags=["client-notifications"])


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> UnreadCountResponse:
    count = await notification_service.unread_count(
        session,
        user_id=user.id,
        user_type="admin_user",
    )
    return UnreadCountResponse(count=count)


@router.get("", response_model=NotificationListResponse)
async def list_notifications_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool | None = Query(None),
) -> NotificationListResponse:
    result = await notification_service.list_notifications(
        session,
        user_id=user.id,
        user_type="admin_user",
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return NotificationListResponse(**result)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> Response:
    await notification_service.mark_all_read(
        session,
        user_id=user.id,
        user_type="admin_user",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read_endpoint(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> Response:
    await notification_service.mark_read(
        session,
        user_id=user.id,
        user_type="admin_user",
        notification_id=notification_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@client_router.get("/unread-count", response_model=UnreadCountResponse)
async def client_unread_count_endpoint(
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> UnreadCountResponse:
    count = await notification_service.unread_count(
        session,
        user_id=user.id,
        user_type="client_user",
    )
    return UnreadCountResponse(count=count)


@client_router.get("", response_model=NotificationListResponse)
async def client_list_notifications_endpoint(
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool | None = Query(None),
) -> NotificationListResponse:
    result = await notification_service.list_notifications(
        session,
        user_id=user.id,
        user_type="client_user",
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return NotificationListResponse(**result)


@client_router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def client_mark_all_read_endpoint(
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> Response:
    await notification_service.mark_all_read(
        session,
        user_id=user.id,
        user_type="client_user",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@client_router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def client_mark_read_endpoint(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> Response:
    await notification_service.mark_read(
        session,
        user_id=user.id,
        user_type="client_user",
        notification_id=notification_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
