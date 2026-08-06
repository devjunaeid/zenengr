"""Role + role_id wiring tests (FEAT-016 part 1, TODO-161).

Covers: seeded system roles/permissions vs the permission matrix,
default role attachment (bootstrap admin + employee), and the partial
uniqueness constraints on roles.name.

Part 2 (TODO-162/163): DB-backed enforcement (role_has_permission +
cache), the tenant roles API, and role assignment with the last-admin
guard.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_permission
from app.core.errors import register_error_handlers
from app.core.security import create_access_token, hash_password
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    TenantStatus,
)
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService
from app.models.role import Role, RolePermission
from app.models.service import Service
from app.models.tenant import Tenant
from app.schemas.roles import RolePermissionInput
from app.services.permissions import PERMISSION_CATALOG, role_has_permission
from app.services.roles import (
    SYSTEM_ROLE_PERMISSIONS,
    assign_user_role,
    attach_default_role,
    create_role,
    get_system_role,
    update_role,
)
from app.services.tenants import create_tenant

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _seed_system_roles(session: AsyncSession) -> None:
    """Insert system roles + permissions from SYSTEM_ROLE_PERMISSIONS."""
    for name, perms in SYSTEM_ROLE_PERMISSIONS.items():
        role = Role(
            tenant_id=None,
            name=name,
            description=f"System role: {name}",
            is_system=True,
        )
        session.add(role)
        await session.flush()
        for action, resource in perms:
            session.add(
                RolePermission(
                    role_id=role.id,
                    action=action,
                    resource=resource,
                    granted=True,
                )
            )
    await session.flush()


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"RolesPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.flush()
    return plan


async def _create_tenant(session: AsyncSession, plan_id: uuid.UUID) -> Tenant:
    tenant = Tenant(
        business_name="RolesCo",
        slug=f"rolesco-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.flush()
    return tenant


# ── Seed matches matrix ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_seeded_roles_and_permissions_match_matrix(db_session: AsyncSession):
    """System roles seeded from SYSTEM_ROLE_PERMISSIONS match the matrix."""
    await _seed_system_roles(db_session)

    roles = (await db_session.execute(select(Role).where(Role.tenant_id.is_(None)))).scalars().all()
    assert len(roles) == len(SYSTEM_ROLE_PERMISSIONS)
    assert {r.name for r in roles} == set(SYSTEM_ROLE_PERMISSIONS)

    for role in roles:
        assert role.is_system is True
        perms = (
            (
                await db_session.execute(
                    select(RolePermission).where(RolePermission.role_id == role.id)
                )
            )
            .scalars()
            .all()
        )
        got = {(p.action, p.resource) for p in perms}
        assert got == set(SYSTEM_ROLE_PERMISSIONS[role.name])
        assert all(p.granted for p in perms)


# ── Default role attachment ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_bootstrap_admin_maps_to_admin_role(db_session: AsyncSession):
    """Tenant bootstrap admin (create_tenant) gets the admin system role."""
    await _seed_system_roles(db_session)
    plan = await _create_plan(db_session)
    email = f"bootadmin-{uuid.uuid4().hex[:8]}@rolesco.dev"

    await create_tenant(
        db_session,
        actor_id=uuid.uuid4(),
        business_name="Bootstrap Co",
        slug=f"bootco-{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
        admin_email=email,
        admin_full_name="Bootstrap Admin",
    )

    user = (
        (
            await db_session.execute(
                select(AdminUser)
                .where(AdminUser.email == email)
                .options(selectinload(AdminUser.role_ref))
            )
        )
        .scalars()
        .one()
    )
    assert user.role == AdminUserRole.ADMIN
    assert user.role_id is not None
    assert user.role_ref is not None
    assert user.role_ref.name == "admin"


@pytest.mark.anyio
async def test_employee_user_maps_to_employee_role(db_session: AsyncSession):
    """attach_default_role maps an EMPLOYEE user to the employee role."""
    await _seed_system_roles(db_session)
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)

    emp = AdminUser(
        tenant_id=tenant.id,
        email=f"emp-{uuid.uuid4().hex[:8]}@rolesco.dev",
        full_name="Test Employee",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.EMPLOYEE,
        is_active=True,
    )
    db_session.add(emp)
    await attach_default_role(db_session, emp)
    await db_session.flush()

    emp = (
        (
            await db_session.execute(
                select(AdminUser)
                .where(AdminUser.id == emp.id)
                .options(selectinload(AdminUser.role_ref))
            )
        )
        .scalars()
        .one()
    )
    assert emp.role_id is not None
    assert emp.role_ref is not None
    assert emp.role_ref.name == "employee"


# ── Uniqueness constraints ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_duplicate_system_role_name_raises_integrity_error(db_session: AsyncSession):
    """Two system roles (tenant_id NULL) cannot share a name."""
    await _seed_system_roles(db_session)

    db_session.add(Role(tenant_id=None, name="admin", description="duplicate", is_system=True))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.anyio
async def test_duplicate_tenant_role_name_raises_integrity_error(db_session: AsyncSession):
    """Two custom roles in the same tenant cannot share a name."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)

    db_session.add(Role(tenant_id=tenant.id, name="ops", description="first"))
    await db_session.flush()
    db_session.add(Role(tenant_id=tenant.id, name="ops", description="second"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ── FEAT-016 part 2: roles API + DB-backed enforcement (TODO-162/163) ──────


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap_admin(
    session: AsyncSession, *, role: AdminUserRole = AdminUserRole.ADMIN
) -> dict:
    """System roles + plan + tenant + a user mapped to the given system role."""
    await _seed_system_roles(session)
    plan = await _create_plan(session)
    tenant = await _create_tenant(session, plan.id)
    role_row = await get_system_role(session, role.value)
    assert role_row is not None
    user = AdminUser(
        tenant_id=tenant.id,
        email=f"user-{uuid.uuid4().hex[:8]}@rolesco.dev",
        full_name=f"Test {role.value}",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    user.role_id = role_row.id
    user.role_ref = role_row
    await session.commit()
    return {"plan": plan, "tenant": tenant, "user": user, "role": role_row}


async def _make_employee(session: AsyncSession, tenant_id: uuid.UUID) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=f"emp-{uuid.uuid4().hex[:8]}@rolesco.dev",
        full_name="Test Employee",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.EMPLOYEE,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=f"Acme-{uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.flush()
    return client


class TestPermissionCatalog:
    @pytest.mark.anyio
    async def test_catalog_includes_roles_resource(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /tenant/roles/permissions has roles entries with labels/groups."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])

        resp = await client.get("/api/v1/tenant/roles/permissions", headers=headers)
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list) and items

        for item in items:
            assert set(item) == {"action", "resource", "label", "group"}
            assert item["label"]
            assert item["group"]

        roles_entries = [i for i in items if i["resource"] == "roles"]
        assert {i["action"] for i in roles_entries} == {"manage", "view"}
        manage = next(i for i in roles_entries if i["action"] == "manage")
        assert manage["label"] == "Manage Roles"
        assert manage["group"] == "Roles"
        view = next(i for i in roles_entries if i["action"] == "view")
        assert view["label"] == "View Roles"
        assert view["group"] == "Roles"


class TestCreateRole:
    @pytest.mark.anyio
    async def test_create_custom_role(self, client: AsyncClient, db_session: AsyncSession):
        """POST /tenant/roles -> 201 with permission subset; list reflects it."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])

        resp = await client.post(
            "/api/v1/tenant/roles/",
            json={
                "name": "ops",
                "description": "Operations",
                "permissions": [
                    {"action": "view", "resource": "clients", "granted": True},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "ops"
        assert data["description"] == "Operations"
        assert data["is_system"] is False
        assert data["tenant_id"] == str(ctx["tenant"].id)
        assert data["permissions"] == [{"action": "view", "resource": "clients", "granted": True}]

        # list = system roles + new custom role
        lst = await client.get("/api/v1/tenant/roles/", headers=headers)
        assert lst.status_code == 200
        names = {r["name"] for r in lst.json()}
        assert {"super_admin", "admin", "manager", "employee", "ops"} <= names

    @pytest.mark.anyio
    async def test_duplicate_and_reserved_names_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Duplicate tenant name -> 409; reserved system name -> 409."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])
        body = {"name": "ops", "permissions": []}

        r1 = await client.post("/api/v1/tenant/roles/", json=body, headers=headers)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/tenant/roles/", json=body, headers=headers)
        assert r2.status_code == 409
        reserved = await client.post(
            "/api/v1/tenant/roles/",
            json={"name": "manager", "permissions": []},
            headers=headers,
        )
        assert reserved.status_code == 409


class TestRoleEnforcement:
    @pytest.mark.anyio
    async def test_custom_role_gates_project_creation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """No manage/projects grant -> 403; re-grant -> 201 (cache cleared)."""
        ctx = await _bootstrap_admin(db_session)
        admin_headers = await _auth_header(ctx["user"])

        basic = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="basic",
            description="Read-only",
            permissions=[RolePermissionInput(action="view", resource="clients", granted=True)],
            actor_id=ctx["user"].id,
        )
        employee = await _make_employee(db_session, ctx["tenant"].id)
        await assign_user_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            target_user_id=employee.id,
            role_id=basic.id,
            actor_id=ctx["user"].id,
        )
        client_obj = await _make_client(db_session, ctx["tenant"].id)
        await db_session.commit()
        emp_headers = await _auth_header(employee)

        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={"name": "Blocked", "client_id": str(client_obj.id)},
            headers=emp_headers,
        )
        assert resp.status_code == 403, resp.text

        await update_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            role_id=basic.id,
            name=None,
            description=None,
            permissions=[
                RolePermissionInput(action="view", resource="clients", granted=True),
                RolePermissionInput(action="manage", resource="projects", granted=True),
            ],
            actor_id=ctx["user"].id,
        )

        resp2 = await client.post(
            "/api/v1/tenant/projects/",
            json={"name": "Allowed", "client_id": str(client_obj.id)},
            headers=emp_headers,
        )
        assert resp2.status_code == 201, resp2.text

        lst = await client.get("/api/v1/tenant/roles/", headers=admin_headers)
        role = next(r for r in lst.json() if r["name"] == "basic")
        perms = {(p["action"], p["resource"]) for p in role["permissions"]}
        assert ("manage", "projects") in perms


class TestSystemRoleGuards:
    @pytest.mark.anyio
    async def test_system_role_guards(self, client: AsyncClient, db_session: AsyncSession):
        """admin edit -> 422; manager delete -> 422; super_admin edit -> 422; rename -> 422."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])
        admin_role = await get_system_role(db_session, "admin")
        manager_role = await get_system_role(db_session, "manager")
        super_role = await get_system_role(db_session, "super_admin")
        assert admin_role is not None and manager_role is not None and super_role is not None

        r = await client.patch(
            f"/api/v1/tenant/roles/{admin_role.id}",
            json={"name": "x"},
            headers=headers,
        )
        assert r.status_code == 422

        r = await client.delete(f"/api/v1/tenant/roles/{manager_role.id}", headers=headers)
        assert r.status_code == 422

        r = await client.patch(
            f"/api/v1/tenant/roles/{super_role.id}",
            json={"name": "x"},
            headers=headers,
        )
        assert r.status_code == 422

        r = await client.patch(
            f"/api/v1/tenant/roles/{manager_role.id}",
            json={"name": "renamed"},
            headers=headers,
        )
        assert r.status_code == 422


class TestResetRoleDefaults:
    @pytest.mark.anyio
    async def test_reset_manager_defaults(self, client: AsyncClient, db_session: AsyncSession):
        """Reset restores the seeded SYSTEM_ROLE_PERMISSIONS set."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])
        manager_role = await get_system_role(db_session, "manager")
        assert manager_role is not None

        r = await client.patch(
            f"/api/v1/tenant/roles/{manager_role.id}",
            json={
                "permissions": [
                    {"action": "view", "resource": "admin_users", "granted": True},
                    {"action": "manage", "resource": "clients", "granted": True},
                ]
            },
            headers=headers,
        )
        assert r.status_code == 200

        r = await client.post(f"/api/v1/tenant/roles/{manager_role.id}/reset", headers=headers)
        assert r.status_code == 200
        got = {(p["action"], p["resource"]) for p in r.json()["permissions"]}
        assert got == set(SYSTEM_ROLE_PERMISSIONS["manager"])


class TestDeleteRole:
    @pytest.mark.anyio
    async def test_delete_assigned_409_unassigned_204(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Assigned custom role -> 409; unassigned -> 204."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])

        assigned_role = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="assigned",
            description="",
            permissions=[],
            actor_id=ctx["user"].id,
        )
        free_role = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="free",
            description="",
            permissions=[],
            actor_id=ctx["user"].id,
        )
        employee = await _make_employee(db_session, ctx["tenant"].id)
        await assign_user_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            target_user_id=employee.id,
            role_id=assigned_role.id,
            actor_id=ctx["user"].id,
        )

        r = await client.delete(f"/api/v1/tenant/roles/{assigned_role.id}", headers=headers)
        assert r.status_code == 409
        r = await client.delete(f"/api/v1/tenant/roles/{free_role.id}", headers=headers)
        assert r.status_code == 204


class TestAssignUserRole:
    @pytest.mark.anyio
    async def test_assign_flows(self, client: AsyncClient, db_session: AsyncSession):
        """Custom -> enum EMPLOYEE; manager -> enum MANAGER; super_admin -> 422."""
        ctx = await _bootstrap_admin(db_session)
        headers = await _auth_header(ctx["user"])
        manager_role = await get_system_role(db_session, "manager")
        super_role = await get_system_role(db_session, "super_admin")
        custom = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="ops",
            description="",
            permissions=[RolePermissionInput(action="view", resource="clients", granted=True)],
            actor_id=ctx["user"].id,
        )
        employee = await _make_employee(db_session, ctx["tenant"].id)
        url = f"/api/v1/tenant/users/{employee.id}/role"

        r = await client.patch(url, json={"role_id": str(custom.id)}, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "employee"
        assert r.json()["role_name"] == "ops"
        await db_session.refresh(employee, attribute_names=["role_ref"])
        assert employee.role == AdminUserRole.EMPLOYEE
        assert employee.role_ref is not None and employee.role_ref.name == "ops"

        r = await client.patch(url, json={"role_id": str(manager_role.id)}, headers=headers)
        assert r.status_code == 200, r.text
        await db_session.refresh(employee)
        assert employee.role == AdminUserRole.MANAGER

        r = await client.patch(url, json={"role_id": str(super_role.id)}, headers=headers)
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_last_admin_guard(self, client: AsyncClient, db_session: AsyncSession):
        """Demoting the only effective admin -> 409; with another admin -> 200."""
        # Bootstrap user is a MANAGER so it does not count as an effective admin.
        ctx = await _bootstrap_admin(db_session, role=AdminUserRole.MANAGER)

        operator = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="operator",
            description="",
            permissions=[
                RolePermissionInput(action="manage", resource="admin_users", granted=True)
            ],
            actor_id=ctx["user"].id,
        )
        actor = AdminUser(
            tenant_id=ctx["tenant"].id,
            email=f"actor-{uuid.uuid4().hex[:8]}@rolesco.dev",
            full_name="Operator",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.MANAGER,
            is_active=True,
        )
        db_session.add(actor)
        await db_session.flush()
        actor.role_id = operator.id
        actor.role_ref = operator
        await db_session.commit()

        manager_role = await get_system_role(db_session, "manager")
        admin_role = await get_system_role(db_session, "admin")
        assert manager_role is not None and admin_role is not None

        target = AdminUser(
            tenant_id=ctx["tenant"].id,
            email=f"target-{uuid.uuid4().hex[:8]}@rolesco.dev",
            full_name="Target Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(target)
        await db_session.flush()
        target.role_id = admin_role.id
        target.role_ref = admin_role
        await db_session.commit()

        actor_headers = await _auth_header(actor)
        url = f"/api/v1/tenant/users/{target.id}/role"
        payload = {"role_id": str(manager_role.id)}

        r = await client.patch(url, json=payload, headers=actor_headers)
        assert r.status_code == 409, r.text

        other = AdminUser(
            tenant_id=ctx["tenant"].id,
            email=f"other-{uuid.uuid4().hex[:8]}@rolesco.dev",
            full_name="Other Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(other)
        await db_session.flush()
        other.role_id = admin_role.id
        other.role_ref = admin_role
        await db_session.commit()

        r = await client.patch(url, json=payload, headers=actor_headers)
        assert r.status_code == 200, r.text
        await db_session.refresh(target)
        assert target.role == AdminUserRole.MANAGER


class TestEnforcementBypass:
    @pytest.mark.anyio
    async def test_admin_role_name_bypasses_grant_check(self, db_session: AsyncSession):
        """admin/super_admin role names grant without any permission rows."""
        admin_role = Role(
            id=uuid.uuid4(), tenant_id=None, name="admin", description="", is_system=True
        )
        assert (
            await role_has_permission(
                db_session, role=admin_role, action="manage", resource="anything"
            )
            is True
        )
        super_role = Role(
            id=uuid.uuid4(), tenant_id=None, name="super_admin", description="", is_system=True
        )
        assert (
            await role_has_permission(
                db_session, role=super_role, action="manage", resource="tenants"
            )
            is True
        )

    @pytest.mark.anyio
    async def test_super_admin_passes_permission_endpoint(self, db_session: AsyncSession):
        """Super admin bypasses require_permission at the dependency layer."""
        app = FastAPI()
        register_error_handlers(app)
        router = APIRouter(prefix="/test")

        @router.get("/manage-clients")
        async def _manage_clients(_=Depends(require_permission("manage", "clients"))):
            return {"ok": True}

        app.include_router(router)

        async def _override_session():
            yield db_session

        app.dependency_overrides[get_session] = _override_session
        transport = ASGITransport(app=app)

        su = AdminUser(
            tenant_id=None,
            email=f"su-{uuid.uuid4().hex[:8]}@platform.dev",
            full_name="Super Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.SUPER_ADMIN,
            is_active=True,
        )
        db_session.add(su)
        await db_session.commit()

        token = create_access_token(
            user_id=str(su.id), tenant_id=None, role="super_admin", realm="admin"
        )
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/test/manage-clients",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200


class TestPermissionCache:
    @pytest.mark.anyio
    async def test_cache_invalidation_on_update(self, db_session: AsyncSession):
        """role_has_permission flips after update_role clears the cache."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        actor = AdminUser(
            tenant_id=tenant.id,
            email=f"actor-{uuid.uuid4().hex[:8]}@rolesco.dev",
            full_name="Actor",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(actor)
        await db_session.flush()

        role = await create_role(
            db_session,
            tenant_id=tenant.id,
            name="cached",
            description="",
            permissions=[RolePermissionInput(action="manage", resource="projects", granted=True)],
            actor_id=actor.id,
        )
        assert (
            await role_has_permission(db_session, role=role, action="manage", resource="projects")
            is True
        )

        await update_role(
            db_session,
            tenant_id=tenant.id,
            role_id=role.id,
            name=None,
            description=None,
            permissions=[RolePermissionInput(action="view", resource="clients", granted=True)],
            actor_id=actor.id,
        )
        assert (
            await role_has_permission(db_session, role=role, action="manage", resource="projects")
            is False
        )


class TestOwnerSpecialCaseRemoval:
    @pytest.mark.anyio
    async def test_employee_with_custom_role_updates_any_milestone(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Custom-role employee can update milestones on a project they don't own."""
        ctx = await _bootstrap_admin(db_session)

        field_role = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="fieldops",
            description="",
            permissions=[RolePermissionInput(action="manage", resource="milestones", granted=True)],
            actor_id=ctx["user"].id,
        )
        employee = await _make_employee(db_session, ctx["tenant"].id)
        await assign_user_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            target_user_id=employee.id,
            role_id=field_role.id,
            actor_id=ctx["user"].id,
        )

        client_obj = await _make_client(db_session, ctx["tenant"].id)
        service = Service(tenant_id=ctx["tenant"].id, name="Web Dev", default_price=None)
        db_session.add(service)
        await db_session.flush()
        # Project owned by the admin, NOT the employee
        project = Project(
            tenant_id=ctx["tenant"].id,
            client_id=client_obj.id,
            name="Owned Elsewhere",
            owner_id=ctx["user"].id,
        )
        db_session.add(project)
        await db_session.flush()
        ps = ProjectService(project_id=project.id, service_id=service.id)
        db_session.add(ps)
        await db_session.flush()
        milestone = ProjectMilestone(
            project_id=project.id,
            project_service_id=ps.id,
            service_id=service.id,
            name="Step 1",
            sequence_order=1,
        )
        db_session.add(milestone)
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/tenant/projects/{project.id}/milestones/{milestone.id}",
            json={"status": "completed"},
            headers=await _auth_header(employee),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"


class TestEffectivePermissionsInAuthResponse:
    @pytest.mark.anyio
    async def test_me_admin_full_catalog(self, client: AsyncClient, db_session: AsyncSession):
        """/auth/me for admin -> all catalog grants + role_id set."""
        ctx = await _bootstrap_admin(db_session)
        resp = await client.get("/api/v1/auth/me", headers=await _auth_header(ctx["user"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_id"] == str(ctx["role"].id)
        assert len(data["permissions"]) == len(PERMISSION_CATALOG)

    @pytest.mark.anyio
    async def test_me_manager_seeded_grants(self, client: AsyncClient, db_session: AsyncSession):
        """/auth/me for manager -> seeded manager permission grants."""
        ctx = await _bootstrap_admin(db_session, role=AdminUserRole.MANAGER)
        resp = await client.get("/api/v1/auth/me", headers=await _auth_header(ctx["user"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_id"] == str(ctx["role"].id)
        expected = sorted(f"{a}.{r}" for a, r in SYSTEM_ROLE_PERMISSIONS["manager"])
        assert data["permissions"] == expected

    @pytest.mark.anyio
    async def test_me_custom_role_subset(self, client: AsyncClient, db_session: AsyncSession):
        """/auth/me for custom-role user -> exactly the granted subset."""
        ctx = await _bootstrap_admin(db_session)
        custom = await create_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            name="subset",
            description="",
            permissions=[
                RolePermissionInput(action="view", resource="clients", granted=True),
                RolePermissionInput(action="manage", resource="projects", granted=True),
            ],
            actor_id=ctx["user"].id,
        )
        employee = await _make_employee(db_session, ctx["tenant"].id)
        await assign_user_role(
            db_session,
            tenant_id=ctx["tenant"].id,
            target_user_id=employee.id,
            role_id=custom.id,
            actor_id=ctx["user"].id,
        )
        await db_session.commit()

        resp = await client.get("/api/v1/auth/me", headers=await _auth_header(employee))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_id"] == str(custom.id)
        assert data["permissions"] == ["manage.projects", "view.clients"]

    @pytest.mark.anyio
    async def test_login_includes_permissions(self, client: AsyncClient, db_session: AsyncSession):
        """Login response user carries role_id + full catalog for admin."""
        ctx = await _bootstrap_admin(db_session)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": ctx["user"].email, "password": _TEST_PWD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role_id"] == str(ctx["role"].id)
        assert len(data["user"]["permissions"]) == len(PERMISSION_CATALOG)
