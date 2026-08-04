"""Integration tests for service catalog APIs (FEAT-006, US-023..US-026)."""

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
from app.models.enums import AdminUserRole, ClientStatus, ClientType, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=20,
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
    business_name: str = "TestCo",
) -> Tenant:
    tenant = Tenant(
        business_name=business_name,
        slug=f"testco-{uuid.uuid4().hex[:8]}",
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
    tenant_id: uuid.UUID | None = None,
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


async def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════
# Auth isolation
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthIsolation:
    @pytest.mark.asyncio
    async def test_unauthenticated_get_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        resp = await client.get("/api/v1/tenant/services/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_post_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        resp = await client.post("/api/v1/tenant/services/", json={"name": "X"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_manager_can_create(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        manager = await _create_admin(
            db_session,
            f"mgr-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        headers = await _admin_auth_header(manager)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Mgr Created"},
            headers=headers,
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_employee_cannot_create(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _admin_auth_header(employee)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Should fail"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_employee_cannot_patch(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        # Create as admin
        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Patchable"},
            headers=await _admin_auth_header(admin),
        )
        sid = create_resp.json()["id"]

        # Employee cannot patch
        resp = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={"name": "Nope"},
            headers=await _admin_auth_header(employee),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_employee_cannot_delete(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Deletable"},
            headers=await _admin_auth_header(admin),
        )
        sid = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/tenant/services/{sid}",
            headers=await _admin_auth_header(employee),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_employee_can_read(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )

        await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Readable"},
            headers=await _admin_auth_header(admin),
        )

        resp = await client.get(
            "/api/v1/tenant/services/", headers=await _admin_auth_header(employee)
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Happy-path CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceCRUD:
    @pytest.mark.asyncio
    async def test_create_with_steps(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Web Design",
                "description": "Full design package",
                "default_price": "1500.00",
                "steps": [
                    {"name": "Discovery", "sequence_order": 1, "expected_duration_days": 7},
                    {
                        "name": "Mockups",
                        "sequence_order": 2,
                        "expected_duration_days": 14,
                        "description": "Initial wireframes",
                    },
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Web Design"
        assert data["default_price"] == "1500.00"
        assert data["step_count"] == 2
        assert len(data["steps"]) == 2
        assert data["steps"][0]["name"] == "Discovery"
        assert data["steps"][1]["name"] == "Mockups"

    @pytest.mark.asyncio
    async def test_list_includes_step_count(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Service With Steps",
                "steps": [
                    {"name": "S1", "sequence_order": 1},
                    {"name": "S2", "sequence_order": 2},
                ],
            },
            headers=headers,
        )
        await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Service No Steps"},
            headers=headers,
        )

        resp = await client.get("/api/v1/tenant/services/", headers=headers)
        assert resp.status_code == 200
        items = {i["name"]: i for i in resp.json()["items"]}
        assert items["Service With Steps"]["step_count"] == 2
        assert items["Service No Steps"]["step_count"] == 0

    @pytest.mark.asyncio
    async def test_get_detail_returns_steps_in_order(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Ordered",
                "steps": [
                    {"name": "First", "sequence_order": 1},
                    {"name": "Second", "sequence_order": 2},
                    {"name": "Third", "sequence_order": 3},
                ],
            },
            headers=headers,
        )
        sid = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/tenant/services/{sid}", headers=headers)
        assert resp.status_code == 200
        steps = resp.json()["steps"]
        assert [s["name"] for s in steps] == ["First", "Second", "Third"]
        assert [s["sequence_order"] for s in steps] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_update_replaces_steps(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Replaceable",
                "steps": [
                    {"name": "Old A", "sequence_order": 1},
                    {"name": "Old B", "sequence_order": 2},
                ],
            },
            headers=headers,
        )
        sid = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={
                "name": "Replaceable v2",
                "steps": [
                    {"name": "New X", "sequence_order": 1},
                    {"name": "New Y", "sequence_order": 2},
                    {"name": "New Z", "sequence_order": 3},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Replaceable v2"
        step_names = [s["name"] for s in data["steps"]]
        assert step_names == ["New X", "New Y", "New Z"]
        assert "Old A" not in step_names
        assert "Old B" not in step_names

    @pytest.mark.asyncio
    async def test_soft_delete_via_patch(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Soft Deletable"},
            headers=headers,
        )
        sid = create_resp.json()["id"]

        # PATCH is_active=False
        patch_resp = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={"is_active": False},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_active"] is False

        # List with is_active=true filter excludes it
        list_resp = await client.get("/api/v1/tenant/services/?is_active=true", headers=headers)
        assert list_resp.json()["total"] == 0

        # List with is_active=false filter includes it
        list_resp2 = await client.get("/api/v1/tenant/services/?is_active=false", headers=headers)
        assert list_resp2.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_hard_delete_then_404(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "To Delete",
                "steps": [{"name": "S1", "sequence_order": 1}],
            },
            headers=headers,
        )
        sid = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/tenant/services/{sid}", headers=headers)
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/tenant/services/{sid}", headers=headers)
        assert get_resp.status_code == 404

        # Verify cascade: step templates also gone
        from app.models.milestone_step_template import MilestoneStepTemplate

        steps = (
            (
                await db_session.execute(
                    select(MilestoneStepTemplate).where(
                        MilestoneStepTemplate.service_id == uuid.UUID(sid)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert list(steps) == []


# ═══════════════════════════════════════════════════════════════════════════
# Step normalization
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceSteps:
    @pytest.mark.asyncio
    async def test_empty_steps_list(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "No Steps", "steps": []},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["steps"] == []
        assert resp.json()["step_count"] == 0

    @pytest.mark.asyncio
    async def test_out_of_order_sequence_gets_normalized(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        # Submit with sequence_order 99 and 1
        resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Reorderable",
                "steps": [
                    {"name": "Second", "sequence_order": 99},
                    {"name": "First", "sequence_order": 1},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        steps = resp.json()["steps"]
        # Input order preserved; sequence_order renumbered 1..N
        assert [s["name"] for s in steps] == ["Second", "First"]
        assert [s["sequence_order"] for s in steps] == [1, 2]

    @pytest.mark.asyncio
    async def test_invalid_uuid_path_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/tenant/services/not-a-uuid", headers=headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceValidation:
    @pytest.mark.asyncio
    async def test_missing_name_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={"description": "no name"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_price_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "Bad Price", "default_price": "-10.00"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_step_name_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Bad Step",
                "steps": [{"name": "", "sequence_order": 1}],
            },
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_zero_duration_days_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Zero Duration",
                "steps": [
                    {"name": "S1", "sequence_order": 1, "expected_duration_days": 0},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_cross_tenant_get_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_a = await _create_admin(
            db_session, "admin_a@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        # A creates
        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "A's Service"},
            headers=await _admin_auth_header(admin_a),
        )
        sid = create_resp.json()["id"]

        # B cannot get
        resp = await client.get(
            f"/api/v1/tenant/services/{sid}", headers=await _admin_auth_header(admin_b)
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_tenant_patch_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_a = await _create_admin(
            db_session, "admin_a@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "A's Service"},
            headers=await _admin_auth_header(admin_a),
        )
        sid = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={"name": "Hijack"},
            headers=await _admin_auth_header(admin_b),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_tenant_delete_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_a = await _create_admin(
            db_session, "admin_a@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "A's Service"},
            headers=await _admin_auth_header(admin_a),
        )
        sid = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/tenant/services/{sid}",
            headers=await _admin_auth_header(admin_b),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_tenant_list_isolation(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, business_name="TenantA")
        tenant_b = await _create_tenant(db_session, plan.id, business_name="TenantB")
        admin_a = await _create_admin(
            db_session, "admin_a@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        await client.post(
            "/api/v1/tenant/services/",
            json={"name": "A's Service"},
            headers=await _admin_auth_header(admin_a),
        )
        await client.post(
            "/api/v1/tenant/services/",
            json={"name": "B's Service"},
            headers=await _admin_auth_header(admin_b),
        )

        resp_a = await client.get(
            "/api/v1/tenant/services/", headers=await _admin_auth_header(admin_a)
        )
        assert resp_a.json()["total"] == 1
        assert resp_a.json()["items"][0]["name"] == "A's Service"


# ═══════════════════════════════════════════════════════════════════════════
# Audit log
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceAudit:
    @pytest.mark.asyncio
    async def test_created_audit_log(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={
                "name": "Auditable",
                "steps": [{"name": "S1", "sequence_order": 1}],
            },
            headers=headers,
        )
        sid = create_resp.json()["id"]

        # Query audit log directly
        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.entity_id == sid,
                        AuditLog.action == "service.created",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].details["name"] == "Auditable"
        assert rows[0].details["step_count"] == 1

    @pytest.mark.asyncio
    async def test_updated_audit_log_includes_changed_keys(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "To Update"},
            headers=headers,
        )
        sid = create_resp.json()["id"]

        await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={"name": "Updated Name", "is_active": False},
            headers=headers,
        )

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.entity_id == sid,
                        AuditLog.action == "service.updated",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert "name" in rows[0].details["changed_keys"]
        assert "is_active" in rows[0].details["changed_keys"]

    @pytest.mark.asyncio
    async def test_deleted_audit_log(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "To Delete"},
            headers=headers,
        )
        sid = create_resp.json()["id"]

        await client.delete(f"/api/v1/tenant/services/{sid}", headers=headers)

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.entity_id == sid,
                        AuditLog.action == "service.deleted",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


# ═══════════════════════════════════════════════════════════════════════════
# In-use indicator (TODO-060 backend part)
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceInUse:
    @pytest.mark.asyncio
    async def test_service_attached_to_project_in_use(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        create_resp = await client.post(
            "/api/v1/tenant/services/",
            json={"name": "In Use Service"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        sid = create_resp.json()["id"]

        # unattached -> not in use
        resp = await client.get(f"/api/v1/tenant/services/{sid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["in_use"] is False
        assert resp.json()["project_count"] == 0

        # attach to a project directly in the DB
        cli = Client(
            tenant_id=tenant.id,
            name="In Use Client",
            client_type=ClientType.COMPANY,
            status=ClientStatus.ACTIVE,
        )
        db_session.add(cli)
        await db_session.commit()
        await db_session.refresh(cli)
        proj = Project(tenant_id=tenant.id, client_id=cli.id, name="In Use Project")
        db_session.add(proj)
        await db_session.commit()
        await db_session.refresh(proj)
        db_session.add(ProjectService(project_id=proj.id, service_id=uuid.UUID(sid)))
        await db_session.commit()

        # attached -> in use with project count
        resp = await client.get(f"/api/v1/tenant/services/{sid}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["in_use"] is True
        assert data["project_count"] == 1


# ── Template separation helpers ─────────────────────────────────────────────


async def _create_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=f"Sep Client {uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_service_with_steps(
    client: AsyncClient, headers: dict[str, str], name: str, steps: list[dict]
) -> str:
    """Create a service via API with milestone steps; return its id."""
    resp = await client.post(
        "/api/v1/tenant/services/",
        json={"name": name, "steps": steps},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_project(
    client: AsyncClient,
    headers: dict[str, str],
    name: str,
    client_id: uuid.UUID,
    service_ids: list[str],
) -> str:
    """Create a project via API attached to services; return its id."""
    resp = await client.post(
        "/api/v1/tenant/projects/",
        json={
            "name": name,
            "client_id": str(client_id),
            "service_ids": service_ids,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _milestone_fingerprint(project_detail: dict) -> list[tuple[str, int, str]]:
    """Return (name, sequence_order, status) per milestone in API order."""
    return [
        (m["name"], m["sequence_order"], m["status"])
        for m in project_detail["milestones"]
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Template separation (FR-6.5 / US-024, TODO-061)
# Editing a service template must never mutate milestones already
# instantiated into projects (ProjectMilestone rows are snapshots).
# ═══════════════════════════════════════════════════════════════════════════


class TestTemplateSeparation:
    @pytest.mark.asyncio
    async def test_edit_template_after_instantiation_does_not_change_project_milestones(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)
        cli = await _create_client(db_session, tenant.id)

        sid = await _create_service_with_steps(
            client,
            headers,
            "Sep Svc",
            steps=[
                {"name": "Step One", "sequence_order": 1, "expected_duration_days": 7},
                {"name": "Step Two", "sequence_order": 2, "expected_duration_days": 14},
            ],
        )
        pid = await _create_project(
            client, headers, "Sep Project", cli.id, [sid]
        )

        before = (await client.get(
            f"/api/v1/tenant/projects/{pid}", headers=headers
        )).json()
        before_milestones = _milestone_fingerprint(before)
        assert before_milestones == [
            ("Step One", 1, "pending"),
            ("Step Two", 2, "pending"),
        ]

        # Patch template: rename step 1, change sequence, add steps, drop one.
        patch = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={
                "steps": [
                    {"name": "Brand New", "sequence_order": 1, "expected_duration_days": 5},
                    {
                        "name": "Step One Renamed",
                        "sequence_order": 2,
                        "expected_duration_days": 7,
                    },
                    {"name": "Third New", "sequence_order": 3, "expected_duration_days": 9},
                ],
            },
            headers=headers,
        )
        assert patch.status_code == 200, patch.text
        # Template itself changed: reordered + renamed + 3 steps, Step Two gone.
        template_steps = patch.json()["steps"]
        assert [s["name"] for s in template_steps] == [
            "Brand New",
            "Step One Renamed",
            "Third New",
        ]
        assert [s["sequence_order"] for s in template_steps] == [1, 2, 3]

        after = (await client.get(
            f"/api/v1/tenant/projects/{pid}", headers=headers
        )).json()
        assert _milestone_fingerprint(after) == before_milestones
        assert len(after["milestones"]) == 2

    @pytest.mark.asyncio
    async def test_add_step_does_not_add_project_milestones(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)
        cli = await _create_client(db_session, tenant.id)

        sid = await _create_service_with_steps(
            client,
            headers,
            "Add Step Svc",
            steps=[{"name": "Solo", "sequence_order": 1}],
        )
        pid = await _create_project(client, headers, "Add Step Project", cli.id, [sid])
        before = (await client.get(
            f"/api/v1/tenant/projects/{pid}", headers=headers
        )).json()
        assert len(before["milestones"]) == 1

        # Add a second step to the template.
        patch = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={
                "steps": [
                    {"name": "Solo", "sequence_order": 1},
                    {"name": "Extra", "sequence_order": 2},
                ],
            },
            headers=headers,
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["step_count"] == 2

        after = (await client.get(
            f"/api/v1/tenant/projects/{pid}", headers=headers
        )).json()
        assert len(after["milestones"]) == 1
        assert _milestone_fingerprint(after) == _milestone_fingerprint(before)

    @pytest.mark.asyncio
    async def test_remove_step_keeps_project_milestones(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)
        cli = await _create_client(db_session, tenant.id)

        sid = await _create_service_with_steps(
            client,
            headers,
            "Remove Step Svc",
            steps=[
                {"name": "Keep Me", "sequence_order": 1},
                {"name": "Drop Me", "sequence_order": 2},
            ],
        )
        pid = await _create_project(client, headers, "Remove Step Project", cli.id, [sid])
        before = (await client.get(
            f"/api/v1/tenant/projects/{pid}", headers=headers
        )).json()
        assert _milestone_fingerprint(before) == [
            ("Keep Me", 1, "pending"),
            ("Drop Me", 2, "pending"),
        ]

        # Remove one step from the template.
        patch = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={"steps": [{"name": "Keep Me", "sequence_order": 1}]},
            headers=headers,
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["step_count"] == 1

        after = (await client.get(
            f"/api/v1/tenant/projects/{pid}", headers=headers
        )).json()
        assert _milestone_fingerprint(after) == _milestone_fingerprint(before)
        assert len(after["milestones"]) == 2

    @pytest.mark.asyncio
    async def test_detached_service_edit_no_project_impact(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session,
            f"admin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _admin_auth_header(admin)

        # Service never attached to any project.
        sid = await _create_service_with_steps(
            client,
            headers,
            "Detached Svc",
            steps=[{"name": "Only", "sequence_order": 1}],
        )
        detail = (await client.get(
            f"/api/v1/tenant/services/{sid}", headers=headers
        )).json()
        assert detail["in_use"] is False
        assert detail["project_count"] == 0

        # Edit template freely; no error.
        patch = await client.patch(
            f"/api/v1/tenant/services/{sid}",
            json={
                "steps": [
                    {"name": "Changed", "sequence_order": 1},
                    {"name": "Also New", "sequence_order": 2},
                ],
            },
            headers=headers,
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["step_count"] == 2

        # Still unattached: project count stays 0, in_use stays false.
        detail2 = (await client.get(
            f"/api/v1/tenant/services/{sid}", headers=headers
        )).json()
        assert detail2["in_use"] is False
        assert detail2["project_count"] == 0
