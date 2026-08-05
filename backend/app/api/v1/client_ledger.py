"""Client-scoped ledger endpoint (FEAT-015, TODO-158).

Base path: /api/v1/client/ledger
Client users see only their own client's ledger (advance balance + entries).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_client_user
from app.db.session import get_session
from app.models.client_user import ClientUser
from app.schemas.transactions import ClientLedgerResponse
from app.services import transactions as transaction_service

router = APIRouter(prefix="/client", tags=["client-ledger"])


@router.get("/ledger", response_model=ClientLedgerResponse)
async def get_client_ledger_endpoint(
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> ClientLedgerResponse:
    """Client ledger: advance balance + signed money entries, own client only."""
    result = await transaction_service.build_client_ledger(
        session,
        tenant_id=user.tenant_id,
        client_id=user.client_id,
    )
    return ClientLedgerResponse(**result)
