"""Targeted test for US-079 / TODO-230 / TODO-231:
Service price update at any time with persistent ledger balance consistency.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_ledger_api import (
    _bootstrap,
    _admin_auth_header,
    _create_project_with_service,
    _get_ledger,
)


@pytest.mark.asyncio
async def test_service_price_update_maintains_ledger_consistency(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _bootstrap(db_session)
    headers = await _admin_auth_header(ctx["admin"])
    pid, ps_id = await _create_project_with_service(client, headers, ctx)

    # Initial state: service price is 500.00
    ledger1 = await _get_ledger(client, headers, pid)
    assert ledger1["summary"]["total"] == "500.00"
    assert ledger1["summary"]["paid"] == "0.00"
    assert ledger1["summary"]["due"] == "500.00"

    # 1. Issue an invoice for the service
    inv_resp = await client.post(
        "/api/v1/tenant/invoices/",
        json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
        headers=headers,
    )
    assert inv_resp.status_code == 201
    inv_id = inv_resp.json()["id"]

    issue_resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
    assert issue_resp.status_code == 200

    # 2. Record payment of 200.00 on the invoice
    pay_resp = await client.post(
        f"/api/v1/tenant/invoices/{inv_id}/transactions",
        json={"amount": "200.00", "method": "bank_transfer", "reference_note": "Initial installment"},
        headers=headers,
    )
    assert pay_resp.status_code == 201

    ledger2 = await _get_ledger(client, headers, pid)
    assert ledger2["summary"]["total"] == "500.00"
    assert ledger2["summary"]["paid"] == "200.00"
    assert ledger2["summary"]["due"] == "300.00"

    # 3. Mid-project: update service price to 800.00 due to work increase
    # This must NOT be blocked (previously raised 409 conflict when invoiced)
    update_price_resp = await client.patch(
        f"/api/v1/tenant/projects/{pid}/services/{ps_id}",
        json={"price": "800.00"},
        headers=headers,
    )
    assert update_price_resp.status_code == 200
    assert update_price_resp.json()["price_at_attachment"] == "800.00"

    # 4. Verify project ledger summary is consistent:
    # total=800.00, paid=200.00, due=600.00
    ledger3 = await _get_ledger(client, headers, pid)
    assert ledger3["summary"]["subtotal"] == "800.00"
    assert ledger3["summary"]["total"] == "800.00"
    assert ledger3["summary"]["paid"] == "200.00"
    assert ledger3["summary"]["due"] == "600.00"
    assert ledger3["summary"]["advance_balance"] == "0.00"

    # 5. Record a direct project payment of 300.00
    direct_pay_resp = await client.post(
        f"/api/v1/tenant/projects/{pid}/payments",
        json={"amount": "300.00", "method": "cash", "reference_note": "Mid-project direct cash"},
        headers=headers,
    )
    assert direct_pay_resp.status_code == 201

    # Both invoice payment (200) and direct payment (300) must be recognized!
    ledger4 = await _get_ledger(client, headers, pid)
    assert ledger4["summary"]["total"] == "800.00"
    assert ledger4["summary"]["paid"] == "500.00"
    assert ledger4["summary"]["due"] == "300.00"

    # 6. Update price downwards to 400.00 (below total paid 500.00)
    update_price_down_resp = await client.patch(
        f"/api/v1/tenant/projects/{pid}/services/{ps_id}",
        json={"price": "400.00"},
        headers=headers,
    )
    assert update_price_down_resp.status_code == 200

    ledger5 = await _get_ledger(client, headers, pid)
    assert ledger5["summary"]["total"] == "400.00"
    assert ledger5["summary"]["paid"] == "500.00"
    assert ledger5["summary"]["due"] == "0.00"
    assert ledger5["summary"]["advance_balance"] == "100.00"
