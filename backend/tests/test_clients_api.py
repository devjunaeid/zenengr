"""Integration tests for client management APIs (FEAT-005, US-018..US-022)."""

from __future__ import annotations

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
from app.models.enums import AdminUserRole, ClientStatus, ClientType, ProjectStatus, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession, max_clients: int = 10) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=max_clients,
        max_active_projects=5,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant(
    session: AsyncSession,
    plan_id: uuid.UUID,
    status: TenantStatus = TenantStatus.ACTIVE,
    business_name: str = "TestCo",
) -> Tenant:
    tenant = Tenant(
        business_name=business_name,
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status=status,
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
    tenant_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=email,
        full_name=f"Test {role.value}",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_client(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str = "TestClient",
    status: ClientStatus = ClientStatus.ACTIVE,
    tags: list[str] | None = None,
) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=name,
        client_type=ClientType.COMPANY,
        status=status,
        tags=tags or [],
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
    is_active: bool = True,
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=email,
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=is_active,
    )
    session.add(cu)
    await session.commit()
    await session.refresh(cu)
    return cu


async def _create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    name: str = "TestProject",
    status: ProjectStatus = ProjectStatus.ACTIVE,
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        client_id=client_id,
        name=name,
        status=status,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


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


# ═══════════════════════════════════════════════════════════════════════════
# Contract: /me includes tenant_name + client object
# ═══════════════════════════════════════════════════════════════════════════


class TestClientMeContract:
    @pytest.mark.asyncio
    async def test_me_includes_tenant_name_and_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, business_name="Acme Corp")
        cli = await _create_client(db_session, tenant.id, name="Widget Inc")
        cu = await _create_client_user(db_session, cli.id, tenant.id, "me@client.com")
        headers = await _client_auth_header(cu)

        resp = await client.get("/api/v1/client/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_name"] == "Acme Corp"
        assert data["client"]["id"] == str(cli.id)
        assert data["client"]["name"] == "Widget Inc"
        assert data["client"]["status"] == "active"
        assert data["client"]["email"] is None
        assert data["client"]["phone"] is None


# ═══════════════════════════════════════════════════════════════════════════
# Contract: PATCH /client/profile
# ═══════════════════════════════════════════════════════════════════════════


class TestClientProfileUpdate:
    @pytest.mark.asyncio
    async def test_update_email_and_phone(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "profile@client.com")
        headers = await _client_auth_header(cu)

        resp = await client.patch(
            "/api/v1/client/auth/profile",
            json={"email": "newemail@client.com", "phone": "+1234567890"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["client"]["email"] == "newemail@client.com"
        assert data["client"]["phone"] == "+1234567890"

    @pytest.mark.asyncio
    async def test_update_tax_id_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "forbid@client.com")
        headers = await _client_auth_header(cu)

        resp = await client.patch(
            "/api/v1/client/auth/profile",
            json={"tax_id": "EVIL-123"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_archived_client_forbidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id, status=ClientStatus.ARCHIVED)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "archived@client.com")
        headers = await _client_auth_header(cu)

        resp = await client.patch(
            "/api/v1/client/auth/profile",
            json={"email": "nope@client.com"},
            headers=headers,
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# CRUD: Create client
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateClient:
    @pytest.mark.asyncio
    async def test_create_client_success(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/clients/",
            json={
                "name": "Acme Corp",
                "client_type": "company",
                "tags": ["VIP"],
                "email": "info@acme.com",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme Corp"
        assert data["tags"] == ["VIP"]
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_client_limit_exceeded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session, max_clients=1)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        # First create succeeds
        resp1 = await client.post(
            "/api/v1/tenant/clients/",
            json={"name": "First Client"},
            headers=headers,
        )
        assert resp1.status_code == 201

        # Second create hits limit
        resp2 = await client.post(
            "/api/v1/tenant/clients/",
            json={"name": "Second Client"},
            headers=headers,
        )
        assert resp2.status_code == 403
        assert resp2.json()["error"]["message"]["code"] == "PLAN_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_create_client_employee_forbidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        employee = await _create_admin(
            db_session, f"emp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, tenant.id
        )
        headers = await _admin_auth_header(employee)

        resp = await client.post(
            "/api/v1/tenant/clients/",
            json={"name": "Should Fail"},
            headers=headers,
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# Create client with user (invite flow replaced)
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateClientWithUser:
    @pytest.mark.asyncio
    async def test_create_client_with_user(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/clients/",
            json={
                "name": "Acme Corp",
                "client_type": "company",
                "client_user_email": "billing@acme.com",
                "client_user_password": "StrongPass123!",
            },
            headers=headers,
        )
        assert resp.status_code == 201

        # Client user exists and login works
        login = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "billing@acme.com", "password": "StrongPass123!"},
        )
        assert login.status_code == 200

        # First user is active primary billing contact; full_name = client name
        cu = (
            (
                await db_session.execute(
                    select(ClientUser).where(ClientUser.email == "billing@acme.com")
                )
            )
            .scalars()
            .one()
        )
        assert cu.is_primary_billing_contact is True
        assert cu.is_active is True
        assert cu.full_name == "Acme Corp"
        assert cu.client_id is not None

        # Audit client_user.created written
        logs = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.action == "client_user.created",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(logs) == 1
        assert logs[0].entity_type == "client_user"
        assert logs[0].details["client_id"] == str(cu.client_id)
        assert logs[0].details["email"] == "billing@acme.com"

    @pytest.mark.asyncio
    async def test_create_client_weak_password_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        # 8 chars passes schema min_length=8 but fails tenant policy (default 10)
        resp = await client.post(
            "/api/v1/tenant/clients/",
            json={
                "name": "Weak Co",
                "client_user_email": "weak@acme.com",
                "client_user_password": "12345678",
            },
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_client_duplicate_email_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp1 = await client.post(
            "/api/v1/tenant/clients/",
            json={
                "name": "Alpha Co",
                "client_user_email": "dup@acme.com",
                "client_user_password": "StrongPass123!",
            },
            headers=headers,
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/tenant/clients/",
            json={
                "name": "Beta Co",
                "client_user_email": "dup@acme.com",
                "client_user_password": "StrongPass123!",
            },
            headers=headers,
        )
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_create_client_without_user_still_works(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/clients/",
            json={"name": "Plain Co", "client_type": "company"},
            headers=headers,
        )
        assert resp.status_code == 201
        cli_id = resp.json()["id"]

        # No client user created when credentials omitted (back-compat)
        users = (
            (
                await db_session.execute(
                    select(ClientUser).where(ClientUser.client_id == uuid.UUID(cli_id))
                )
            )
            .scalars()
            .all()
        )
        assert users == []


# ═══════════════════════════════════════════════════════════════════════════
# Admin password reset for client user
# ═══════════════════════════════════════════════════════════════════════════


class TestResetClientUserPassword:
    @pytest.mark.asyncio
    async def test_admin_reset_password(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "reset@test.com")
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu.id}/reset-password",
            json={"password": "NewStrongPass123!"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        # Old password no longer works
        old = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "reset@test.com", "password": _TEST_PWD},
        )
        assert old.status_code == 401

        # New password works
        new = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "reset@test.com", "password": "NewStrongPass123!"},
        )
        assert new.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_weak_password_422(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "weakreset@test.com")
        headers = await _admin_auth_header(admin)

        # 8 chars passes schema min_length=8 but fails tenant policy (default 10)
        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu.id}/reset-password",
            json={"password": "12345678"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reset_cross_tenant_404(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        cli_a = await _create_client(db_session, tenant_a.id)
        cu_a = await _create_client_user(db_session, cli_a.id, tenant_a.id, "cross@test.com")
        headers_b = await _admin_auth_header(admin_b)

        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu_a.id}/reset-password",
            json={"password": "NewStrongPass123!"},
            headers=headers_b,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# CRUD: List clients
# ═══════════════════════════════════════════════════════════════════════════


class TestListClients:
    @pytest.mark.asyncio
    async def test_list_clients_empty(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_clients_with_q_filter(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_client(db_session, tenant.id, name="Acme Corp")
        await _create_client(db_session, tenant.id, name="Beta Inc")
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/?q=acme", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_list_clients_with_tag_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_client(db_session, tenant.id, name="VIP Client", tags=["VIP"])
        await _create_client(db_session, tenant.id, name="Regular Client", tags=["regular"])
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/?tag=VIP", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "VIP Client"

    @pytest.mark.asyncio
    async def test_list_clients_with_status_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_client(db_session, tenant.id, name="Active Client")
        await _create_client(
            db_session, tenant.id, name="Archived Client", status=ClientStatus.ARCHIVED
        )
        headers = await _admin_auth_header(admin)

        # Default: active only
        resp = await client.get("/api/v1/tenant/clients/", headers=headers)
        assert resp.json()["total"] == 1

        # Explicit archived
        resp2 = await client.get("/api/v1/tenant/clients/?status=archived", headers=headers)
        assert resp2.json()["total"] == 1
        assert resp2.json()["items"][0]["name"] == "Archived Client"

    @pytest.mark.asyncio
    async def test_list_clients_sort(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_client(db_session, tenant.id, name="Zebra")
        await _create_client(db_session, tenant.id, name="Alpha")
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/?sort=name", headers=headers)
        assert resp.json()["items"][0]["name"] == "Alpha"

        resp2 = await client.get("/api/v1/tenant/clients/?sort=-name", headers=headers)
        assert resp2.json()["items"][0]["name"] == "Zebra"

    @pytest.mark.asyncio
    async def test_list_clients_rollup_fields_present(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_client(db_session, tenant.id, name="Rollup Client")
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/", headers=headers)
        item = resp.json()["items"][0]
        assert "active_projects" in item
        assert "total_invoiced" in item
        assert "total_outstanding" in item
        assert item["active_projects"] == 0
        assert item["total_invoiced"] == "0.00"

    @pytest.mark.asyncio
    async def test_list_clients_active_projects_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli_a = await _create_client(db_session, tenant.id, name="Many Projects")
        await _create_client(db_session, tenant.id, name="No Projects")
        await _create_project(
            db_session, tenant.id, cli_a.id, name="A-1", status=ProjectStatus.ACTIVE
        )
        await _create_project(
            db_session, tenant.id, cli_a.id, name="A-2", status=ProjectStatus.ACTIVE
        )
        await _create_project(
            db_session, tenant.id, cli_a.id, name="A-3", status=ProjectStatus.COMPLETED
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        by_name = {item["name"]: item["active_projects"] for item in data["items"]}
        assert by_name["Many Projects"] == 2
        assert by_name["No Projects"] == 0

    @pytest.mark.asyncio
    async def test_list_clients_employee_can_view(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        employee = await _create_admin(
            db_session, f"emp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, tenant.id
        )
        await _create_client(db_session, tenant.id, name="Viewable")
        headers = await _admin_auth_header(employee)

        resp = await client.get("/api/v1/tenant/clients/", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_clients_cross_tenant_isolation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_a = await _create_admin(
            db_session, "admin_a@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        await _create_client(db_session, tenant_a.id, name="Client A")
        await _create_client(db_session, tenant_b.id, name="Client B")
        headers = await _admin_auth_header(admin_a)

        resp = await client.get("/api/v1/tenant/clients/", headers=headers)
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "Client A"


# ═══════════════════════════════════════════════════════════════════════════
# CRUD: Get client detail
# ═══════════════════════════════════════════════════════════════════════════


class TestGetClientDetail:
    @pytest.mark.asyncio
    async def test_get_client_detail(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, name="Detail Client")
        await _create_client_user(db_session, cli.id, tenant.id, "cu@test.com")
        headers = await _admin_auth_header(admin)

        resp = await client.get(f"/api/v1/tenant/clients/{cli.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Detail Client"
        assert len(data["client_users"]) == 1
        assert data["client_users"][0]["email"] == "cu@test.com"
        assert "recent_activity" in data

    @pytest.mark.asyncio
    async def test_get_client_detail_active_projects_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, name="Detail Projects Client")
        await _create_project(
            db_session, tenant.id, cli.id, name="P-active", status=ProjectStatus.ACTIVE
        )
        await _create_project(
            db_session, tenant.id, cli.id, name="P-hold", status=ProjectStatus.ON_HOLD
        )
        await _create_project(
            db_session, tenant.id, cli.id, name="P-done", status=ProjectStatus.COMPLETED
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get(f"/api/v1/tenant/clients/{cli.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_projects"] == 1

    @pytest.mark.asyncio
    async def test_get_client_cross_tenant_404(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        cli_a = await _create_client(db_session, tenant_a.id, name="Client A")
        headers = await _admin_auth_header(admin_b)

        resp = await client.get(f"/api/v1/tenant/clients/{cli_a.id}", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_client_invalid_uuid_404(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/not-a-uuid", headers=headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# CRUD: Update client
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateClient:
    @pytest.mark.asyncio
    async def test_update_client_success(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, name="Old Name")
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            f"/api/v1/tenant/clients/{cli.id}",
            json={"name": "New Name", "phone": "+999"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["phone"] == "+999"

    @pytest.mark.asyncio
    async def test_update_client_status_forbidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            f"/api/v1/tenant/clients/{cli.id}",
            json={"status": "archived"},
            headers=headers,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Archive / Unarchive
# ═══════════════════════════════════════════════════════════════════════════


class TestArchiveUnarchive:
    @pytest.mark.asyncio
    async def test_archive_client(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(f"/api/v1/tenant/clients/{cli.id}/archive", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    @pytest.mark.asyncio
    async def test_archive_already_archived_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, status=ClientStatus.ARCHIVED)
        headers = await _admin_auth_header(admin)

        resp = await client.post(f"/api/v1/tenant/clients/{cli.id}/archive", headers=headers)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_unarchive_client(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, status=ClientStatus.ARCHIVED)
        headers = await _admin_auth_header(admin)

        resp = await client.post(f"/api/v1/tenant/clients/{cli.id}/unarchive", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_unarchive_not_archived_409(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(f"/api/v1/tenant/clients/{cli.id}/unarchive", headers=headers)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_archive_blocks_client_login(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "archive-block@test.com")
        headers = await _admin_auth_header(admin)

        # Archive
        await client.post(f"/api/v1/tenant/clients/{cli.id}/archive", headers=headers)

        # Login blocked
        resp = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "archive-block@test.com", "password": _TEST_PWD},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unarchive_restores_client_login(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, status=ClientStatus.ARCHIVED)
        await _create_client_user(db_session, cli.id, tenant.id, "unarchive@test.com")
        headers = await _admin_auth_header(admin)

        # Unarchive
        await client.post(f"/api/v1/tenant/clients/{cli.id}/unarchive", headers=headers)

        # Login works
        resp = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "unarchive@test.com", "password": _TEST_PWD},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_archive_cross_tenant_404(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        cli_a = await _create_client(db_session, tenant_a.id)
        headers = await _admin_auth_header(admin_b)

        resp = await client.post(f"/api/v1/tenant/clients/{cli_a.id}/archive", headers=headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Notes
# ═══════════════════════════════════════════════════════════════════════════


class TestClientNotes:
    @pytest.mark.asyncio
    async def test_add_note(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/clients/{cli.id}/notes",
            json={"body": "Important note about this client"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["body"] == "Important note about this client"
        assert data["author_id"] == str(admin.id)
        assert data["author_name"] == admin.full_name

    @pytest.mark.asyncio
    async def test_list_notes(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        # Add two notes
        await client.post(
            f"/api/v1/tenant/clients/{cli.id}/notes",
            json={"body": "First note"},
            headers=headers,
        )
        await client.post(
            f"/api/v1/tenant/clients/{cli.id}/notes",
            json={"body": "Second note"},
            headers=headers,
        )

        resp = await client.get(f"/api/v1/tenant/clients/{cli.id}/notes", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        # Both notes present (order non-deterministic within same DB transaction)
        note_bodies = [item["body"] for item in data["items"]]
        assert set(note_bodies) == {"First note", "Second note"}
        # Author name included for each note
        for item in data["items"]:
            assert item["author_id"] == str(admin.id)
            assert item["author_name"] == admin.full_name

    @pytest.mark.asyncio
    async def test_list_notes_different_authors_show_correct_names(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin1 = await _create_admin(
            db_session, f"admin1-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        admin2 = await _create_admin(
            db_session,
            f"admin2-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        cli = await _create_client(db_session, tenant.id)
        headers1 = await _admin_auth_header(admin1)
        headers2 = await _admin_auth_header(admin2)

        await client.post(
            f"/api/v1/tenant/clients/{cli.id}/notes",
            json={"body": "Note by admin1"},
            headers=headers1,
        )
        await client.post(
            f"/api/v1/tenant/clients/{cli.id}/notes",
            json={"body": "Note by admin2"},
            headers=headers2,
        )

        resp = await client.get(f"/api/v1/tenant/clients/{cli.id}/notes", headers=headers1)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        by_author = {item["author_id"]: item["author_name"] for item in data["items"]}
        assert by_author[str(admin1.id)] == admin1.full_name
        assert by_author[str(admin2.id)] == admin2.full_name

    @pytest.mark.asyncio
    async def test_notes_no_patch_delete_routes(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        # No PATCH route
        resp = await client.patch(
            f"/api/v1/tenant/clients/{cli.id}/notes/some-id",
            json={"body": "nope"},
            headers=headers,
        )
        assert resp.status_code in (404, 405)

        # No DELETE route
        resp = await client.delete(
            f"/api/v1/tenant/clients/{cli.id}/notes/some-id",
            headers=headers,
        )
        assert resp.status_code in (404, 405)

    @pytest.mark.asyncio
    async def test_client_realm_cannot_add_notes(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "notes-blocked@test.com")
        headers = await _client_auth_header(cu)

        resp = await client.post(
            f"/api/v1/tenant/clients/{cli.id}/notes",
            json={"body": "Should fail"},
            headers=headers,
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# Tags
# ═══════════════════════════════════════════════════════════════════════════


class TestClientTags:
    @pytest.mark.asyncio
    async def test_get_distinct_tags(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_client(db_session, tenant.id, name="C1", tags=["VIP", "Enterprise"])
        await _create_client(db_session, tenant.id, name="C2", tags=["VIP", "Startup"])
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/clients/tags", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "Enterprise" in data["tags"]
        assert "Startup" in data["tags"]
        assert "VIP" in data["tags"]
        assert len(data["tags"]) == 3


# ═══════════════════════════════════════════════════════════════════════════
# Activity Timeline
# ═══════════════════════════════════════════════════════════════════════════


class TestClientActivity:
    @pytest.mark.asyncio
    async def test_activity_shows_created_and_note(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        # Create client via API so audit log is written
        create_resp = await client.post(
            "/api/v1/tenant/clients/",
            json={"name": "Activity Client"},
            headers=headers,
        )
        cli_id = create_resp.json()["id"]

        # Add a note
        await client.post(
            f"/api/v1/tenant/clients/{cli_id}/notes",
            json={"body": "A note"},
            headers=headers,
        )

        resp = await client.get(f"/api/v1/tenant/clients/{cli_id}/activity", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Should have: client.created + client.note_added = 2 events
        assert data["total"] == 2
        actions = [e["action"] for e in data["items"]]
        assert "client.created" in actions
        assert "client.note_added" in actions

    @pytest.mark.asyncio
    async def test_activity_archive_events(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        # Create client via API so audit log is written
        create_resp = await client.post(
            "/api/v1/tenant/clients/",
            json={"name": "Archive Client"},
            headers=headers,
        )
        cli_id = create_resp.json()["id"]

        # Archive
        await client.post(f"/api/v1/tenant/clients/{cli_id}/archive", headers=headers)
        # Unarchive
        await client.post(f"/api/v1/tenant/clients/{cli_id}/unarchive", headers=headers)

        resp = await client.get(f"/api/v1/tenant/clients/{cli_id}/activity", headers=headers)
        data = resp.json()
        actions = [e["action"] for e in data["items"]]
        assert "client.created" in actions
        assert "client.archived" in actions
        assert "client.unarchived" in actions


# ═══════════════════════════════════════════════════════════════════════════
# Usage endpoint reflects real client count
# ═══════════════════════════════════════════════════════════════════════════


class TestUsageEndpoint:
    @pytest.mark.asyncio
    async def test_usage_reflects_client_count(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        # Before creating any clients
        resp = await client.get("/api/v1/tenant/plan", headers=headers)
        assert resp.json()["usage"]["clients"] == 0

        # Create 2 clients
        await _create_client(db_session, tenant.id, name="C1")
        await _create_client(db_session, tenant.id, name="C2")

        resp2 = await client.get("/api/v1/tenant/plan", headers=headers)
        assert resp2.json()["usage"]["clients"] == 2

        # Archive one
        cli = await _create_client(db_session, tenant.id, name="C3")
        await client.post(f"/api/v1/tenant/clients/{cli.id}/archive", headers=headers)

        resp3 = await client.get("/api/v1/tenant/plan", headers=headers)
        assert resp3.json()["usage"]["clients"] == 2  # archived not counted
