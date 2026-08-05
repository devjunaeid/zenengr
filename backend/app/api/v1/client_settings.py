"""Client-facing formatting settings endpoint (FEAT-014, TODO-151).

Base path: /api/v1/client/settings
Returns the tenant's resolved display settings (stored override or default)
for currency, timezone, date_format and time_format. Client realm only;
permission internals are not exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_client_user
from app.db.session import get_session
from app.models.client_user import ClientUser
from app.schemas.client_portal import ClientSettingsResponse
from app.services.settings import get_client_formatting_settings

router = APIRouter(prefix="/client/settings", tags=["client-settings"])


@router.get("", response_model=ClientSettingsResponse)
async def get_client_settings_endpoint(
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> ClientSettingsResponse:
    """Get the client-facing formatting settings for the caller's tenant."""
    settings = await get_client_formatting_settings(session, user.tenant_id)
    return ClientSettingsResponse(**settings)
