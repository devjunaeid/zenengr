"""Model-level tests for FEAT-018 part 1 (TODO-178) + endpoint tests for
FEAT-018 part 2 (TODO-179/180/181/182).

Part 1 covers LedgerEntry persistence/read-back and Project discount field
roundtrip. Part 2 covers the charge hooks, manual adjustment, live Summary
computation, discount editor, and the staff + client ledger APIs.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_user import ClientUser
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    DiscountType,
    LedgerEntryType,
    LedgerSourceType,
    ProjectStatus,
    TenantStatus,
)
from app.models.ledger_entry import LedgerEntry
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"


async def _make_project(db_session) -> tuple[Tenant, Client, Project, AdminUser]:
    plan = Plan(
        name="LedgerPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="Ledger Tenant", slug="ledger-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    client = Client(tenant_id=tenant.id, name="Ledger Client")
    db_session.add(client)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=tenant.id,
        email="ledger-admin@example.com",
        full_name="Ledger Admin",
        hashed_password="pwd",
        role=AdminUserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    project = Project(
        tenant_id=tenant.id,
        name="Ledger Project",
        client_id=client.id,
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return tenant, client, project, admin


@pytest.mark.anyio
async def test_ledger_entry_charge_and_manual_round_trip(db_session):
    """LedgerEntry rows persist with correct enums and entry_date."""
    _, _, project, admin = await _make_project(db_session)

    service = Service(tenant_id=project.tenant_id, name="Design Retainer")
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    ps = ProjectService(
        project_id=project.id,
        service_id=service.id,
        price_at_attachment=Decimal("1500.00"),
    )
    db_session.add(ps)
    await db_session.commit()
    await db_session.refresh(ps)

    charge = LedgerEntry(
        project_id=project.id,
        type=LedgerEntryType.CHARGE,
        amount=Decimal("1500.00"),
        description="Design Retainer",
        source_type=LedgerSourceType.PROJECT_SERVICE,
        source_id=ps.id,
        entry_date=date(2026, 8, 13),
        created_by_id=admin.id,
    )
    adjustment = LedgerEntry(
        project_id=project.id,
        type=LedgerEntryType.CHARGE,
        amount=Decimal("250.00"),
        description="Manual adjustment",
        source_type=LedgerSourceType.MANUAL_ADJUSTMENT,
        entry_date=date(2026, 8, 14),
        created_by_id=admin.id,
    )
    db_session.add_all([charge, adjustment])
    await db_session.commit()
    await db_session.refresh(charge)
    await db_session.refresh(adjustment)

    assert charge.id is not None
    assert isinstance(charge.id, uuid.UUID)
    assert charge.type == LedgerEntryType.CHARGE
    assert charge.amount == Decimal("1500.00")
    assert charge.source_type == LedgerSourceType.PROJECT_SERVICE
    assert charge.source_id == ps.id
    assert charge.entry_date == date(2026, 8, 13)
    assert charge.created_by_id == admin.id
    assert charge.description == "Design Retainer"
    assert charge.created_at is not None

    assert adjustment.type == LedgerEntryType.CHARGE
    assert adjustment.source_type == LedgerSourceType.MANUAL_ADJUSTMENT
    assert adjustment.entry_date == date(2026, 8, 14)
    assert adjustment.invoice_ref is None

    result = await db_session.execute(
        select(LedgerEntry).where(LedgerEntry.project_id == project.id)
    )
    loaded = result.scalars().all()
    assert len(loaded) == 2
    by_id = {e.id: e for e in loaded}
    assert by_id[charge.id].type == LedgerEntryType.CHARGE
    assert by_id[charge.id].source_type == LedgerSourceType.PROJECT_SERVICE
    assert by_id[adjustment.id].source_type == LedgerSourceType.MANUAL_ADJUSTMENT


@pytest.mark.anyio
async def test_ledger_entry_nullable_refs(db_session):
    """Payment/refund rows (derived stream) leave source refs nullable-capable
    and invoice_ref unset until a formal invoice covers the charge."""
    _, _, project, admin = await _make_project(db_session)

    entry = LedgerEntry(
        project_id=project.id,
        type=LedgerEntryType.PAYMENT,
        amount=Decimal("500.00"),
        description="Derived payment placeholder",
        source_type=LedgerSourceType.TRANSACTION,
        source_id=uuid.uuid4(),
        entry_date=date(2026, 8, 13),
        created_by_id=admin.id,
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    assert entry.invoice_ref is None
    assert entry.type == LedgerEntryType.PAYMENT
    assert entry.source_type == LedgerSourceType.TRANSACTION


@pytest.mark.anyio
async def test_project_discount_fields_round_trip(db_session):
    """Project discount fields (type/value/updated_at/updated_by) roundtrip."""
    _, _, project, admin = await _make_project(db_session)

    project.discount_type = DiscountType.PERCENTAGE
    project.discount_value = Decimal("10.00")
    project.discount_updated_by = admin.id
    await db_session.commit()
    await db_session.refresh(project)

    assert project.discount_type == DiscountType.PERCENTAGE
    assert project.discount_value == Decimal("10.00")
    assert project.discount_updated_by == admin.id
    assert project.discount_updated_at is None

    result = await db_session.execute(select(Project).where(Project.id == project.id))
    loaded = result.scalar_one()
    assert loaded.discount_type == DiscountType.PERCENTAGE
    assert loaded.discount_value == Decimal("10.00")
    assert loaded.discount_updated_by == admin.id

    # Replace-on-change semantics: set a fixed discount, old value gone
    loaded.discount_type = DiscountType.FIXED
    loaded.discount_value = Decimal("250.00")
    await db_session.commit()
    await db_session.refresh(loaded)
    assert loaded.discount_type == DiscountType.FIXED
    assert loaded.discount_value == Decimal("250.00")


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-018 part 2 - API tests (TODO-179/180/181/182)
# ═══════════════════════════════════════════════════════════════════════════


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"LedgerPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=20,
        max_active_projects=50,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant(session: AsyncSession, plan_id: uuid.UUID) -> Tenant:
    tenant = Tenant(
        business_name="LedgerCo",
        slug=f"ledger-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_admin(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    role: AdminUserRole = AdminUserRole.ADMIN,
) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=f"ledger-admin-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Ledger Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=f"Ledger Client {uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_service(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str = "Ledger Service",
    price: str = "500.00",
) -> Service:
    service = Service(
        tenant_id=tenant_id,
        name=f"{name} {uuid.uuid4().hex[:6]}",
        description="",
        default_price=price,
        is_active=True,
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


async def _create_client_user(
    session: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=f"cu-{uuid.uuid4().hex[:8]}@client.com",
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=True,
    )
    session.add(cu)
    await session.commit()
    await session.refresh(cu)
    return cu


async def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _client_auth_header(user: ClientUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role="client_user",
        realm="client",
        client_id=str(user.client_id),
    )
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap(db_session: AsyncSession) -> dict:
    """plan + tenant + admin + client + one 500.00 service."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(db_session, tenant.id)
    client = await _create_client(db_session, tenant.id)
    service = await _create_service(db_session, tenant.id)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "client": client,
        "service": service,
    }


async def _create_project_with_service(
    client: AsyncClient,
    headers: dict[str, str],
    ctx: dict,
    *,
    activate: bool = True,
) -> tuple[str, str]:
    """Create a project with the service attached; returns (project_id, ps_id)."""
    resp = await client.post(
        "/api/v1/tenant/projects/",
        json={
            "name": f"Ledger Proj {uuid.uuid4().hex[:6]}",
            "client_id": str(ctx["client"].id),
            "service_ids": [str(ctx["service"].id)],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]
    detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=headers)).json()
    ps_id = detail["services"][0]["id"]
    if activate:
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=headers,
        )
    return pid, ps_id


async def _get_ledger(client: AsyncClient, headers: dict[str, str], pid: str) -> dict:
    resp = await client.get(f"/api/v1/tenant/projects/{pid}/ledger", headers=headers)
    assert resp.status_code == 200
    return resp.json()


class TestChargeHooks:
    @pytest.mark.asyncio
    async def test_attach_service_creates_charge_and_summary(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["type"] == "charge"
        assert entry["amount"] == "500.00"
        assert entry["source_type"] == "project_service"
        assert entry["source_id"] == ps_id
        assert entry["description"] == ctx["service"].name
        assert entry["invoice_number"] is None
        summary = data["summary"]
        assert summary["subtotal"] == "500.00"
        assert summary["discount_type"] is None
        assert summary["discount_value"] is None
        assert summary["discount_amount"] == "0.00"
        assert summary["total"] == "500.00"
        assert summary["paid"] == "0.00"
        assert summary["due"] == "500.00"

    @pytest.mark.asyncio
    async def test_create_project_with_service_ids_creates_charge(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": f"Proj {uuid.uuid4().hex[:6]}",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["service"].id)],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 1
        assert data["entries"][0]["type"] == "charge"
        assert data["entries"][0]["amount"] == "500.00"
        assert data["summary"]["subtotal"] == "500.00"

    @pytest.mark.asyncio
    async def test_remove_invoiced_service_soft_cancel_writes_reversal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        inv = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        assert inv.status_code == 201
        inv_id = inv.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=headers
        )
        assert resp.status_code == 204

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 2
        reversal = data["entries"][1]
        assert reversal["type"] == "charge"
        assert reversal["amount"] == "-500.00"
        assert reversal["source_type"] == "project_service"
        assert reversal["source_id"] == ps_id
        assert reversal["description"].startswith("Service removed:")
        assert data["summary"]["subtotal"] == "0.00"
        assert data["summary"]["total"] == "0.00"
        assert data["summary"]["due"] == "0.00"

    @pytest.mark.asyncio
    async def test_remove_uninvoiced_service_hard_delete_writes_reversal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        resp = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=headers
        )
        assert resp.status_code == 204

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 2
        reversal = data["entries"][1]
        assert reversal["type"] == "charge"
        assert reversal["amount"] == "-500.00"
        assert reversal["source_type"] == "project_service"
        assert data["summary"]["subtotal"] == "0.00"
        assert data["summary"]["due"] == "0.00"

    @pytest.mark.asyncio
    async def test_removal_writes_exactly_one_reversal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        await client.delete(f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=headers)
        rows = (
            (
                await db_session.execute(
                    select(LedgerEntry).where(
                        LedgerEntry.project_id == uuid.UUID(pid),
                        LedgerEntry.amount < 0,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


class TestManualAdjustment:
    @pytest.mark.asyncio
    async def test_manual_adjustments_are_signed_and_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/ledger/adjustments",
            json={"amount": "100.00", "description": "Scope bonus"},
            headers=headers,
        )
        assert resp.status_code == 201
        entry = resp.json()
        assert entry["type"] == "charge"
        assert entry["amount"] == "100.00"
        assert entry["source_type"] == "manual_adjustment"
        assert entry["description"] == "Scope bonus"

        data = await _get_ledger(client, headers, pid)
        assert data["summary"]["subtotal"] == "600.00"
        assert data["summary"]["total"] == "600.00"
        assert data["summary"]["due"] == "600.00"

        resp2 = await client.post(
            f"/api/v1/tenant/projects/{pid}/ledger/adjustments",
            json={"amount": "-50.00", "description": "Credit"},
            headers=headers,
        )
        assert resp2.status_code == 201
        assert resp2.json()["amount"] == "-50.00"

        data2 = await _get_ledger(client, headers, pid)
        assert data2["summary"]["subtotal"] == "550.00"

        audit_rows = (
            (
                await db_session.execute(
                    select(AuditLog)
                    .where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.entity_id == pid,
                        AuditLog.action == "project.ledger_adjusted",
                    )
                    .order_by(AuditLog.created_at)
                )
            )
            .scalars()
            .all()
        )
        assert len(audit_rows) == 2
        assert audit_rows[0].details["amount"] == "100.00"
        assert audit_rows[1].details["amount"] == "-50.00"

    @pytest.mark.asyncio
    async def test_manual_adjustment_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        employee = await _create_admin(db_session, ctx["tenant"].id, role=AdminUserRole.EMPLOYEE)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/ledger/adjustments",
            json={"amount": "10.00", "description": "nope"},
            headers=await _admin_auth_header(employee),
        )
        assert resp.status_code == 403


class TestDiscountEditor:
    @pytest.mark.asyncio
    async def test_percentage_and_fixed_and_clear_and_invalid(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        # percentage 10 -> 10% of 500
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "percentage", "discount_value": "10"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == {"discount_type": "percentage", "discount_value": "10.00"}
        data = await _get_ledger(client, headers, pid)
        s = data["summary"]
        assert s["discount_type"] == "percentage"
        assert s["discount_value"] == "10.00"
        assert s["discount_amount"] == "50.00"
        assert s["total"] == "450.00"
        assert s["due"] == "450.00"

        # fixed 50 -> min(50, 500)
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "fixed", "discount_value": "50"},
            headers=headers,
        )
        assert resp.status_code == 200
        s = (await _get_ledger(client, headers, pid))["summary"]
        assert s["discount_amount"] == "50.00"
        assert s["total"] == "450.00"

        # fixed above subtotal -> capped at subtotal
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "fixed", "discount_value": "600"},
            headers=headers,
        )
        assert resp.status_code == 200
        s = (await _get_ledger(client, headers, pid))["summary"]
        assert s["discount_amount"] == "500.00"
        assert s["total"] == "0.00"
        assert s["due"] == "0.00"

        # clear via null -> 0 discount
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": None, "discount_value": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == {"discount_type": None, "discount_value": None}
        s = (await _get_ledger(client, headers, pid))["summary"]
        assert s["discount_amount"] == "0.00"
        assert s["discount_value"] is None
        assert s["total"] == "500.00"

        # invalid percentage -> 422
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "percentage", "discount_value": "150"},
            headers=headers,
        )
        assert resp.status_code == 422

        # negative fixed -> 422
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "fixed", "discount_value": "-5"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_discount_audited_with_old_and_new(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "percentage", "discount_value": "10"},
            headers=headers,
        )
        await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "fixed", "discount_value": "75"},
            headers=headers,
        )

        rows = (
            (
                await db_session.execute(
                    select(AuditLog)
                    .where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.entity_id == pid,
                        AuditLog.action == "project.discount_updated",
                    )
                    .order_by(AuditLog.created_at)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2
        first = rows[0].details
        assert first["old_type"] is None
        assert first["old_value"] is None
        assert first["new_type"] == "percentage"
        assert first["new_value"] == "10.00"
        second = rows[1].details
        assert second["old_type"] == "percentage"
        assert second["old_value"] == "10.00"
        assert second["new_type"] == "fixed"
        assert second["new_value"] == "75.00"

    @pytest.mark.asyncio
    async def test_discount_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        employee = await _create_admin(db_session, ctx["tenant"].id, role=AdminUserRole.EMPLOYEE)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/discount",
            json={"discount_type": "percentage", "discount_value": "10"},
            headers=await _admin_auth_header(employee),
        )
        assert resp.status_code == 403


class TestPaymentStream:
    @pytest.mark.asyncio
    async def test_payments_and_refunds_derive_from_transactions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        inv = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        assert inv.status_code == 201
        inv_id = inv.json()["id"]
        issued = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert issued.status_code == 200
        inv_number = issued.json()["invoice_number"]

        pay = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "200.00", "method": "bank_transfer"},
            headers=headers,
        )
        assert pay.status_code == 201

        data = await _get_ledger(client, headers, pid)
        payment = next(e for e in data["entries"] if e["type"] == "payment")
        assert payment["amount"] == "200.00"
        assert payment["invoice_number"] == inv_number
        assert payment["invoice_ref"] == inv_id
        assert payment["source_type"] == "transaction"
        s = data["summary"]
        assert s["paid"] == "200.00"
        assert s["due"] == "300.00"

        refund = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/refund",
            json={"amount": "50.00"},
            headers=headers,
        )
        assert refund.status_code == 201

        data2 = await _get_ledger(client, headers, pid)
        refund_entry = next(e for e in data2["entries"] if e["type"] == "refund")
        assert refund_entry["amount"] == "-50.00"
        assert refund_entry["invoice_number"] == inv_number
        s2 = data2["summary"]
        assert s2["paid"] == "150.00"
        assert s2["due"] == "350.00"
        assert s2["total"] == "500.00"

    @pytest.mark.asyncio
    async def test_draft_invoice_transactions_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Transactions on DRAFT invoices are not part of the payment stream."""
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        data = await _get_ledger(client, headers, pid)
        assert data["summary"]["paid"] == "0.00"
        assert data["summary"]["due"] == "500.00"
        assert all(e["type"] == "charge" for e in data["entries"])


class TestLedgerScoping:
    @pytest.mark.asyncio
    async def test_staff_ledger_404_for_other_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx_a = await _bootstrap(db_session)
        ctx_b = await _bootstrap(db_session)
        headers_a = await _admin_auth_header(ctx_a["admin"])
        pid, _ = await _create_project_with_service(client, headers_a, ctx_a)

        resp = await client.get(
            f"/api/v1/tenant/projects/{pid}/ledger",
            headers=await _admin_auth_header(ctx_b["admin"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_ledger_scoped_to_own_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)
        inv = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        inv_id = inv.json()["id"]
        issued = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        inv_number = issued.json()["invoice_number"]
        await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "200.00", "method": "card"},
            headers=headers,
        )

        # Own client sees the full timeline + summary
        client_user = await _create_client_user(db_session, ctx["client"].id, ctx["tenant"].id)
        resp = await client.get(
            f"/api/v1/client/projects/{pid}/ledger",
            headers=await _client_auth_header(client_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        types = [e["type"] for e in data["entries"]]
        assert types == ["charge", "payment"]
        payment = next(e for e in data["entries"] if e["type"] == "payment")
        assert payment["amount"] == "200.00"
        assert payment["invoice_number"] == inv_number
        s = data["summary"]
        assert s["subtotal"] == "500.00"
        assert s["paid"] == "200.00"
        assert s["due"] == "300.00"

        # Other client in the same tenant -> 404 (leak prevention)
        other_client = await _create_client(db_session, ctx["tenant"].id)
        other_user = await _create_client_user(db_session, other_client.id, ctx["tenant"].id)
        resp2 = await client.get(
            f"/api/v1/client/projects/{pid}/ledger",
            headers=await _client_auth_header(other_user),
        )
        assert resp2.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-018 part 3 - invoice tagging (TODO-185)
# ═══════════════════════════════════════════════════════════════════════════


class TestInvoiceTagging:
    @pytest.mark.asyncio
    async def test_issue_tags_charge_with_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        inv = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        assert inv.status_code == 201
        inv_id = inv.json()["id"]
        issued = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert issued.status_code == 200
        inv_number = issued.json()["invoice_number"]

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 1
        charge = data["entries"][0]
        assert charge["type"] == "charge"
        assert charge["invoice_ref"] == inv_id
        assert charge["invoice_number"] == inv_number

        rows = (
            (
                await db_session.execute(
                    select(LedgerEntry).where(
                        LedgerEntry.project_id == uuid.UUID(pid),
                        LedgerEntry.source_type == LedgerSourceType.PROJECT_SERVICE,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].invoice_ref == uuid.UUID(inv_id)

    @pytest.mark.asyncio
    async def test_second_invoice_does_not_retag(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        inv1 = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        inv1_id = inv1.json()["id"]
        issued1 = await client.post(f"/api/v1/tenant/invoices/{inv1_id}/issue", headers=headers)
        assert issued1.status_code == 200
        inv1_number = issued1.json()["invoice_number"]

        inv2 = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        inv2_id = inv2.json()["id"]
        issued2 = await client.post(f"/api/v1/tenant/invoices/{inv2_id}/issue", headers=headers)
        assert issued2.status_code == 200

        data = await _get_ledger(client, headers, pid)
        charges = [e for e in data["entries"] if e["source_type"] == "project_service"]
        assert len(charges) == 1
        assert charges[0]["invoice_ref"] == inv1_id
        assert charges[0]["invoice_number"] == inv1_number

        rows = (
            (
                await db_session.execute(
                    select(LedgerEntry).where(
                        LedgerEntry.project_id == uuid.UUID(pid),
                        LedgerEntry.source_type == LedgerSourceType.PROJECT_SERVICE,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].invoice_ref == uuid.UUID(inv1_id)

    @pytest.mark.asyncio
    async def test_custom_line_items_not_tagged(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, _ = await _create_project_with_service(client, headers, ctx)

        inv = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": pid,
                "line_items": [{"description": "Setup fee", "unit_price": "250.00"}],
            },
            headers=headers,
        )
        assert inv.status_code == 201
        inv_id = inv.json()["id"]
        issued = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert issued.status_code == 200

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 1
        assert data["entries"][0]["invoice_ref"] is None
        assert data["entries"][0]["invoice_number"] is None

    @pytest.mark.asyncio
    async def test_draft_invoice_not_tagged(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        pid, ps_id = await _create_project_with_service(client, headers, ctx)

        inv = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=headers,
        )
        assert inv.status_code == 201
        # draft only - never issued

        data = await _get_ledger(client, headers, pid)
        assert len(data["entries"]) == 1
        assert data["entries"][0]["invoice_ref"] is None
        assert data["entries"][0]["invoice_number"] is None

        rows = (
            (
                await db_session.execute(
                    select(LedgerEntry).where(
                        LedgerEntry.project_id == uuid.UUID(pid),
                        LedgerEntry.source_type == LedgerSourceType.PROJECT_SERVICE,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].invoice_ref is None
