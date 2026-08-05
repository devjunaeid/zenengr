"""Integration tests for per-tenant email routing (FEAT-013, TODO-142).

Verifies every outgoing email site resolves the sender via the tenant SMTP
factory, SMTP send failures are audited as `email.send_failed` without
breaking the underlying action, and tenants without SMTP keep using the
console sender (dev log, no audit).
"""

from __future__ import annotations

import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_user import ClientUser
from app.models.enums import AdminUserRole, ClientStatus, ClientType, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant
from app.services import tenant_smtp as tenant_smtp_service

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
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
        business_name="RouteCo",
        slug=f"routeco-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_admin(
    session: AsyncSession,
    email: str,
    role: AdminUserRole,
    tenant_id: uuid.UUID,
) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=email,
        full_name=f"Test {role.value}",
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
        name=f"Test Client {uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_client_user(
    session: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID,
    email: str,
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=email,
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=True,
    )
    session.add(cu)
    await session.commit()
    await session.refresh(cu)
    return cu


async def _create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    *,
    owner_id: uuid.UUID | None = None,
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        client_id=client_id,
        name=f"Proj {uuid.uuid4().hex[:6]}",
        owner_id=owner_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def _bootstrap(db_session: AsyncSession):
    """Plan + tenant + admin (ADMIN) + employee + client + client_user + project."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session,
        f"admin-{uuid.uuid4().hex[:8]}@routeco.com",
        AdminUserRole.ADMIN,
        tenant.id,
    )
    employee = await _create_admin(
        db_session,
        f"emp-{uuid.uuid4().hex[:8]}@routeco.com",
        AdminUserRole.EMPLOYEE,
        tenant.id,
    )
    client = await _create_client(db_session, tenant.id)
    client_user = await _create_client_user(
        db_session,
        client.id,
        tenant.id,
        f"cu-{uuid.uuid4().hex[:8]}@client.com",
    )
    project = await _create_project(db_session, tenant.id, client.id, owner_id=admin.id)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "employee": employee,
        "client": client,
        "client_user": client_user,
        "project": project,
    }


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _enable_broken_smtp(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    """Enable SMTP pointing at an unreachable host (127.0.0.1:1)."""
    await tenant_smtp_service.upsert_smtp_config(
        db_session,
        tenant_id=tenant_id,
        data={
            "host": "127.0.0.1",
            "port": 1,
            "from_email": "noreply@example.com",
            "enabled": True,
        },
        actor_id=actor_id,
    )


async def _send_failed_rows(db_session: AsyncSession, tenant_id: uuid.UUID) -> list[AuditLog]:
    rows = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.action == "email.send_failed",
                )
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Broken SMTP: failure audited, action continues
# ═══════════════════════════════════════════════════════════════════════════


class TestSmtpFailureRouting:
    @pytest.mark.asyncio
    async def test_send_failure_audited_and_action_continues(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        await _enable_broken_smtp(db_session, ctx["tenant"].id, ctx["admin"].id)

        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "shared note"},
            headers=await _auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201, resp.text

        rows = await _send_failed_rows(db_session, ctx["tenant"].id)
        assert rows, "expected email.send_failed audit rows"
        row = rows[0]
        assert row.entity_type == "smtp"
        assert row.entity_id == str(ctx["tenant"].id)
        assert row.details["host"] == "127.0.0.1"
        assert "error" in row.details and row.details["error"]

    @pytest.mark.asyncio
    async def test_invite_with_broken_smtp_still_creates_invite(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        await _enable_broken_smtp(db_session, ctx["tenant"].id, ctx["admin"].id)

        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "newbie@routeco.com", "role": "employee"},
            headers=await _auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201, resp.text

        rows = await _send_failed_rows(db_session, ctx["tenant"].id)
        assert rows, "expected email.send_failed audit rows"
        assert rows[0].entity_type == "smtp"
        assert rows[0].entity_id == str(ctx["tenant"].id)

    @pytest.mark.asyncio
    async def test_forgot_password_uses_tenant_sender(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        await _enable_broken_smtp(db_session, ctx["tenant"].id, ctx["admin"].id)

        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": ctx["admin"].email},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "ok"

        rows = await _send_failed_rows(db_session, ctx["tenant"].id)
        assert rows, "expected email.send_failed audit rows"
        assert rows[0].entity_type == "smtp"
        assert rows[0].entity_id == str(ctx["tenant"].id)


# ═══════════════════════════════════════════════════════════════════════════
# Disabled SMTP: console fallback, no audit
# ═══════════════════════════════════════════════════════════════════════════


class TestConsoleFallback:
    @pytest.mark.asyncio
    async def test_disabled_smtp_uses_console(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO, logger="app.services.email")
        ctx = await _bootstrap(db_session)

        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "shared note"},
            headers=await _auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201, resp.text

        email_msgs = [r.getMessage() for r in caplog.records if "Email to=" in r.getMessage()]
        assert email_msgs, "no email was dispatched for shared comment"
        assert ctx["project"].name in email_msgs[0]

        rows = await _send_failed_rows(db_session, ctx["tenant"].id)
        assert not rows, "console fallback must not emit email.send_failed audit rows"
