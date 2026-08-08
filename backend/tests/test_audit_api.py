"""Integration tests for enriched audit log APIs.

Covers the consolidated list_audit_logs + audit_names service wired into
/tenant/audit-logs and the two super-admin views: server-side actor_name /
entity_label resolution, action-prefix + date filters, pagination, and the
platform-scope (tenant_id IS NULL) semantics.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.enums import (
    ActorType,
    AdminUserRole,
    BillingCycle,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.services.audit import log as audit_log

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant_and_admin(session: AsyncSession) -> tuple[Tenant, AdminUser]:
    plan = await _create_plan(session)
    tenant = Tenant(
        business_name="TestCo",
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan.id,
    )
    session.add(tenant)
    await session.flush()
    session.add(
        TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
        )
    )
    admin = AdminUser(
        tenant_id=tenant.id,
        email=f"admin-{uuid.uuid4().hex[:8]}@testco.com",
        full_name="Tenant Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(tenant)
    await session.refresh(admin)
    return tenant, admin


async def _create_sa(session: AsyncSession) -> AdminUser:
    user = AdminUser(
        tenant_id=None,
        email=f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev",
        full_name="Super Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.SUPER_ADMIN,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════
# Enrichment (server-side name resolution)
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditLogEnrichment:
    """GET /api/v1/tenant/audit-logs resolves actor + entity names."""

    @pytest.mark.anyio
    async def test_tenant_audit_logs_resolve_names(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)

        client_row = Client(
            tenant_id=tenant.id, name="Acme Corp", email="billing@acme.test"
        )
        db_session.add(client_row)
        await db_session.flush()
        project = Project(
            tenant_id=tenant.id, name="Demo Project", client_id=client_row.id
        )
        db_session.add(project)
        await db_session.flush()
        invoice = Invoice(tenant_id=tenant.id, invoice_number="INV-2026-0001")
        db_session.add(invoice)
        await db_session.flush()

        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="project.created",
            entity_type="project",
            entity_id=str(project.id),
        )
        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="invoice.created",
            entity_type="invoice",
            entity_id=str(invoice.id),
        )
        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="client.created",
            entity_type="client",
            entity_id=str(client_row.id),
        )
        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="user.role_updated",
            entity_type="admin_user",
            entity_id=str(admin.id),
        )
        await db_session.commit()

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/audit-logs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        by_action = {item["action"]: item for item in data["items"]}

        for item in data["items"]:
            assert item["actor_name"] == "Tenant Admin"

        assert by_action["project.created"]["entity_label"] == "Demo Project"
        assert by_action["invoice.created"]["entity_label"] == "INV-2026-0001"
        assert by_action["client.created"]["entity_label"] == "Acme Corp"
        assert by_action["user.role_updated"]["entity_label"] == "Tenant Admin"

    @pytest.mark.anyio
    async def test_unresolvable_names_fall_back_to_none(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        # Unknown entity type + dangling actor id (deleted user) -> None
        db_session.add(
            AuditLog(
                tenant_id=tenant.id,
                actor_id=uuid.uuid4(),
                actor_type=ActorType.ADMIN_USER,
                action="mystery.touched",
                entity_type="mystery",
                entity_id=str(uuid.uuid4()),
            )
        )
        await db_session.commit()

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/audit-logs", headers=headers)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["actor_name"] is None
        assert item["entity_label"] is None


# ═══════════════════════════════════════════════════════════════════════════
# Filters + pagination
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditLogFilters:
    """Action-prefix, from/to date window, invalid date, pagination."""

    @pytest.mark.anyio
    async def test_tenant_audit_logs_filters(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        now = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
        db_session.add_all(
            [
                AuditLog(
                    tenant_id=tenant.id,
                    actor_id=admin.id,
                    actor_type=ActorType.ADMIN_USER,
                    action="tenant.profile_updated",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    created_at=now - timedelta(days=3),
                ),
                AuditLog(
                    tenant_id=tenant.id,
                    actor_id=admin.id,
                    actor_type=ActorType.ADMIN_USER,
                    action="invite.created",
                    entity_type="invite",
                    created_at=now - timedelta(days=2),
                ),
                AuditLog(
                    tenant_id=tenant.id,
                    actor_id=admin.id,
                    actor_type=ActorType.ADMIN_USER,
                    action="invoice.issued",
                    entity_type="invoice",
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        await db_session.commit()
        headers = await _auth_header(admin)

        # action prefix
        resp = await client.get(
            "/api/v1/tenant/audit-logs?action=tenant.", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["action"] == "tenant.profile_updated"

        # from/to window: date-only bounds are inclusive (midnight UTC)
        resp = await client.get(
            "/api/v1/tenant/audit-logs?from=2026-08-03&to=2026-08-05",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert {item["action"] for item in data["items"]} == {
            "invite.created",
            "invoice.issued",
        }

        # invalid date -> 422
        resp = await client.get(
            "/api/v1/tenant/audit-logs?from=not-a-date", headers=headers
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_tenant_audit_logs_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        base = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
        for i in range(25):
            db_session.add(
                AuditLog(
                    tenant_id=tenant.id,
                    actor_id=admin.id,
                    actor_type=ActorType.ADMIN_USER,
                    action=f"test.action.{i}",
                    entity_type="test",
                    created_at=base - timedelta(minutes=i),
                )
            )
        await db_session.commit()
        headers = await _auth_header(admin)

        resp = await client.get(
            "/api/v1/tenant/audit-logs?page=1&page_size=10", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["items"][0]["action"] == "test.action.0"  # newest first
        assert data["items"][0]["entity_label"] is None  # unknown type

        resp = await client.get(
            "/api/v1/tenant/audit-logs?page=3&page_size=10", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 5
        assert data["items"][0]["action"] == "test.action.20"


# ═══════════════════════════════════════════════════════════════════════════
# Super-admin views
# ═══════════════════════════════════════════════════════════════════════════


class TestSuperAdminAuditViews:
    """Platform scope (tenant_id IS NULL) + per-tenant SA view."""

    @pytest.mark.anyio
    async def test_sa_platform_and_per_tenant_views(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        # tenant-scoped row (must NOT appear in the platform view)
        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="tenant.profile_updated",
            entity_type="tenant",
            entity_id=str(tenant.id),
        )
        # platform-scoped row
        await audit_log(
            db_session,
            tenant_id=None,
            actor_id=sa.id,
            actor_type=ActorType.SUPER_ADMIN,
            action="plan.created",
            entity_type="plan",
            entity_id=str(uuid.uuid4()),
        )
        await db_session.commit()

        # platform view: only tenant_id IS NULL rows
        resp = await client.get("/api/v1/admin/audit-logs", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "plan.created"
        assert data["items"][0]["actor_name"] == "Super admin"
        assert data["items"][0]["entity_label"] is None  # plan id not in DB

        # per-tenant SA view: that tenant's rows with resolved names
        resp = await client.get(
            f"/api/v1/admin/tenants/{tenant.id}/audit-logs", headers=sa_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "tenant.profile_updated"
        assert data["items"][0]["actor_name"] == "Tenant Admin"
        assert data["items"][0]["entity_label"] == "TestCo"

    @pytest.mark.anyio
    async def test_sa_tenant_audit_view_filters(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="tenant.profile_updated",
            entity_type="tenant",
            entity_id=str(tenant.id),
        )
        await audit_log(
            db_session,
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type=ActorType.ADMIN_USER,
            action="invite.created",
            entity_type="invite",
            entity_id=str(uuid.uuid4()),
        )
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/admin/tenants/{tenant.id}/audit-logs?action=invite.",
            headers=sa_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "invite.created"

        # invalid tenant id -> 404
        resp = await client.get(
            "/api/v1/admin/tenants/not-a-uuid/audit-logs", headers=sa_headers
        )
        assert resp.status_code == 404
