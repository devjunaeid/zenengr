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
from app.models.enums import AdminUserRole, TenantStatus
from app.models.plan import Plan
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
    async def test_employee_cannot_create(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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
    async def test_employee_cannot_patch(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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
    async def test_employee_cannot_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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
    async def test_employee_can_read(
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
    async def test_list_includes_step_count(
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
    async def test_update_replaces_steps(
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
    async def test_soft_delete_via_patch(
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
        list_resp = await client.get(
            "/api/v1/tenant/services/?is_active=true", headers=headers
        )
        assert list_resp.json()["total"] == 0

        # List with is_active=false filter includes it
        list_resp2 = await client.get(
            "/api/v1/tenant/services/?is_active=false", headers=headers
        )
        assert list_resp2.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_hard_delete_then_404(
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
                "name": "To Delete",
                "steps": [{"name": "S1", "sequence_order": 1}],
            },
            headers=headers,
        )
        sid = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/tenant/services/{sid}", headers=headers
        )
        assert del_resp.status_code == 204

        get_resp = await client.get(
            f"/api/v1/tenant/services/{sid}", headers=headers
        )
        assert get_resp.status_code == 404

        # Verify cascade: step templates also gone
        from app.models.milestone_step_template import MilestoneStepTemplate

        steps = (
            await db_session.execute(
                select(MilestoneStepTemplate).where(
                    MilestoneStepTemplate.service_id == uuid.UUID(sid)
                )
            )
        ).scalars().all()
        assert list(steps) == []


# ═══════════════════════════════════════════════════════════════════════════
# Step normalization
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceSteps:
    @pytest.mark.asyncio
    async def test_empty_steps_list(
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

        resp = await client.get(
            "/api/v1/tenant/services/not-a-uuid", headers=headers
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceValidation:
    @pytest.mark.asyncio
    async def test_missing_name_returns_422(
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
            json={"description": "no name"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_price_returns_422(
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
            json={"name": "Bad Price", "default_price": "-10.00"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_step_name_returns_422(
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
    async def test_cross_tenant_list_isolation(
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
    async def test_created_audit_log(
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
                "name": "Auditable",
                "steps": [{"name": "S1", "sequence_order": 1}],
            },
            headers=headers,
        )
        sid = create_resp.json()["id"]

        # Query audit log directly
        rows = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant.id,
                    AuditLog.entity_id == sid,
                    AuditLog.action == "service.created",
                )
            )
        ).scalars().all()
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
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant.id,
                    AuditLog.entity_id == sid,
                    AuditLog.action == "service.updated",
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert "name" in rows[0].details["changed_keys"]
        assert "is_active" in rows[0].details["changed_keys"]

    @pytest.mark.asyncio
    async def test_deleted_audit_log(
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
            json={"name": "To Delete"},
            headers=headers,
        )
        sid = create_resp.json()["id"]

        await client.delete(
            f"/api/v1/tenant/services/{sid}", headers=headers
        )

        rows = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant.id,
                    AuditLog.entity_id == sid,
                    AuditLog.action == "service.deleted",
                )
            )
        ).scalars().all()
        assert len(rows) == 1
