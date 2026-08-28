"""Integration tests for project management APIs (FEAT-007, US-025..US-027).

Covers TODO-062 (Project model + create API), TODO-064 (milestone
instantiation), TODO-065 (milestone update API), TODO-068 (add service to
project API).
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    InvoiceStatus,
    TenantStatus,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.milestone_step_template import MilestoneStepTemplate
from app.models.plan import Plan
from app.models.service import Service
from app.models.tenant import Tenant

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


async def _create_service(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str = "Test Service",
    steps: list[dict] | None = None,
) -> Service:
    service = Service(
        tenant_id=tenant_id,
        name=f"{name} {uuid.uuid4().hex[:6]}",
        description="",
        default_price="500.00",
        is_active=True,
    )
    session.add(service)
    await session.flush()
    for idx, step in enumerate(steps or [], start=1):
        tmpl = MilestoneStepTemplate(
            service_id=service.id,
            name=step["name"],
            sequence_order=step.get("sequence_order", idx),
            expected_duration_days=step.get("expected_duration_days"),
            description=step.get("description", ""),
        )
        session.add(tmpl)
    await session.commit()
    await session.refresh(service)
    return service


async def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap(
    db_session: AsyncSession,
    *,
    role: AdminUserRole = AdminUserRole.ADMIN,
    extra_admin: bool = False,
):
    """Create plan + tenant + admin + client + 2 services with steps."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session,
        f"admin-{uuid.uuid4().hex[:8]}@testco.com",
        role,
        tenant.id,
    )
    client = await _create_client(db_session, tenant.id)
    svc_a = await _create_service(
        db_session,
        tenant.id,
        name="SvcA",
        steps=[
            {"name": "Step A1", "expected_duration_days": 7},
            {"name": "Step A2", "expected_duration_days": 14},
        ],
    )
    svc_b = await _create_service(
        db_session,
        tenant.id,
        name="SvcB",
        steps=[
            {"name": "Step B1", "expected_duration_days": 3},
        ],
    )
    other_admin = None
    if extra_admin:
        other_admin = await _create_admin(
            db_session,
            f"other-{uuid.uuid4().hex[:8]}@testco.com",
            role,
            tenant.id,
        )
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "client": client,
        "svc_a": svc_a,
        "svc_b": svc_b,
        "other_admin": other_admin,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Auth isolation
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthIsolation:
    @pytest.mark.asyncio
    async def test_unauthenticated_list_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        resp = await client.get("/api/v1/tenant/projects/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_create_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={"name": "X", "client_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_manager_can_create(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, role=AdminUserRole.MANAGER)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Mgr Project",
                "client_id": str(ctx["client"].id),
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_employee_cannot_create(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, role=AdminUserRole.EMPLOYEE)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Should fail",
                "client_id": str(ctx["client"].id),
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_employee_can_read(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, role=AdminUserRole.ADMIN)
        admin_headers = await _admin_auth_header(ctx["admin"])
        # Create project as admin
        await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Readable",
                "client_id": str(ctx["client"].id),
            },
            headers=admin_headers,
        )
        # Employee can list
        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            ctx["tenant"].id,
        )
        resp = await client.get(
            "/api/v1/tenant/projects/", headers=await _admin_auth_header(employee)
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_employee_cannot_patch(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, role=AdminUserRole.ADMIN)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={"name": "Patchable", "client_id": str(ctx["client"].id)},
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]

        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            ctx["tenant"].id,
        )
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"name": "Nope"},
            headers=await _admin_auth_header(employee),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# Project CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectCRUD:
    @pytest.mark.asyncio
    async def test_create_with_two_services(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Web Redesign",
                "client_id": str(ctx["client"].id),
                "start_date": "2026-08-01",
                "service_ids": [str(ctx["svc_a"].id), str(ctx["svc_b"].id)],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Web Redesign"
        assert data["status"] == "draft"
        assert data["service_count"] == 2
        assert data["milestone_count"] == 3  # 2 from svcA + 1 from svcB

    @pytest.mark.asyncio
    async def test_create_with_no_services(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Empty Project",
                "client_id": str(ctx["client"].id),
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["service_count"] == 0
        assert data["milestone_count"] == 0

    @pytest.mark.asyncio
    async def test_list_returns_project(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        await client.post(
            "/api/v1/tenant/projects/",
            json={"name": "Listed", "client_id": str(ctx["client"].id)},
            headers=admin_headers,
        )
        resp = await client.get("/api/v1/tenant/projects/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "Listed"

    @pytest.mark.asyncio
    async def test_get_detail_returns_services_and_milestones(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Detail",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["services"]) == 1
        assert data["services"][0]["service_id"] == str(ctx["svc_a"].id)
        assert data["services"][0]["status"] == "active"
        assert len(data["milestones"]) == 2
        assert [m["sequence_order"] for m in data["milestones"]] == [1, 2]
        assert all(m["status"] == "pending" for m in data["milestones"])

    @pytest.mark.asyncio
    async def test_patch_status_transitions(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={"name": "Patch Status", "client_id": str(ctx["client"].id)},
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        resp2 = await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "on_hold"},
            headers=admin_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "on_hold"

    @pytest.mark.asyncio
    async def test_invalid_client_id_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Bad Client",
                "client_id": str(uuid.uuid4()),
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_owner_id_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Bad Owner",
                "client_id": str(ctx["client"].id),
                "owner_id": str(uuid.uuid4()),
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Milestone instantiation (TODO-064)
# ═══════════════════════════════════════════════════════════════════════════


class TestMilestoneInstantiation:
    @pytest.mark.asyncio
    async def test_milestones_in_correct_order_pending(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Order",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        pid = resp.json()["id"]
        detail = (
            await client.get(
                f"/api/v1/tenant/projects/{pid}",
                headers=await _admin_auth_header(ctx["admin"]),
            )
        ).json()
        names = [m["name"] for m in detail["milestones"]]
        assert names == ["Step A1", "Step A2"]
        assert all(m["status"] == "pending" for m in detail["milestones"])

    @pytest.mark.asyncio
    async def test_planned_date_cumulative_with_start_date(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        start = date(2026, 8, 1)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Planned",
                "client_id": str(ctx["client"].id),
                "start_date": start.isoformat(),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        pid = resp.json()["id"]
        detail = (
            await client.get(
                f"/api/v1/tenant/projects/{pid}",
                headers=await _admin_auth_header(ctx["admin"]),
            )
        ).json()
        # 7 days + 14 days => step 1 = day 0+7=7, step 2 = day 7+14=21
        planned = [m["planned_date"] for m in detail["milestones"]]
        assert planned[0] == (start + timedelta(days=7)).isoformat()
        assert planned[1] == (start + timedelta(days=21)).isoformat()

    @pytest.mark.asyncio
    async def test_planned_date_null_when_no_start_date(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "NoStart",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        pid = resp.json()["id"]
        detail = (
            await client.get(
                f"/api/v1/tenant/projects/{pid}",
                headers=await _admin_auth_header(ctx["admin"]),
            )
        ).json()
        assert all(m["planned_date"] is None for m in detail["milestones"])

    @pytest.mark.asyncio
    async def test_planned_date_null_when_template_has_no_duration(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        svc_no_dur = await _create_service(
            db_session,
            ctx["tenant"].id,
            name="NoDur",
            steps=[{"name": "Mystery"}],  # no expected_duration_days
        )
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "NoDurProj",
                "client_id": str(ctx["client"].id),
                "start_date": "2026-08-01",
                "service_ids": [str(svc_no_dur.id)],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        pid = resp.json()["id"]
        detail = (
            await client.get(
                f"/api/v1/tenant/projects/{pid}",
                headers=await _admin_auth_header(ctx["admin"]),
            )
        ).json()
        assert detail["milestones"][0]["planned_date"] is None

    @pytest.mark.asyncio
    async def test_zero_step_service_creates_no_milestones(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        svc_empty = await _create_service(db_session, ctx["tenant"].id, name="Empty", steps=[])
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "EmptySvc",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(svc_empty.id)],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["service_count"] == 1
        assert data["milestone_count"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# Milestone update (TODO-065)
# ═══════════════════════════════════════════════════════════════════════════


class TestMilestoneUpdate:
    @pytest.mark.asyncio
    async def test_patch_status_in_progress(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        mid = detail["milestones"][0]["id"]

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"status": "in_progress"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_patch_status_completed(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"status": "completed"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_patch_actual_date(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]

        today = date.today().isoformat()
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"actual_date": today},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["actual_date"] == today

    @pytest.mark.asyncio
    async def test_patch_assignee_to_valid_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session, extra_admin=True)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"assignee_id": str(ctx["other_admin"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["assignee_id"] == str(ctx["other_admin"].id)

    @pytest.mark.asyncio
    async def test_patch_assignee_cross_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx_a = await _bootstrap(db_session)
        ctx_b = await _bootstrap(db_session)  # second tenant
        admin_headers = await _admin_auth_header(ctx_a["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx_a["client"].id),
                    "service_ids": [str(ctx_a["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]

        # Try to assign tenant B's admin
        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"assignee_id": str(ctx_b["admin"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_invalid_status_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"status": "nonsense"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_milestone_extra_field_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "P",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]

        resp = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"name": "Hacked"},
            headers=admin_headers,
        )
        assert resp.status_code == 422  # extra="forbid"


# ═══════════════════════════════════════════════════════════════════════════
# Attach service to project (TODO-068)
# ═══════════════════════════════════════════════════════════════════════════


class TestAttachService:
    @pytest.mark.asyncio
    async def test_attach_to_active_project(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Active",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        # Move to active
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )

        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["service_id"] == str(ctx["svc_b"].id)
        assert data["milestone_count"] == 1  # svc_b has 1 step

        # Confirm via detail: now 3 milestones total
        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        assert len(detail["milestones"]) == 3
        assert len(detail["services"]) == 2

    @pytest.mark.asyncio
    async def test_attach_duplicate_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Dup",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )
        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_a"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_attach_to_draft_returns_409(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Draft",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        # Project is draft by default; try to attach
        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_attach_to_cancelled_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Cancel",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "cancelled"},
            headers=admin_headers,
        )
        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_attach_cross_tenant_service_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx_a = await _bootstrap(db_session)
        ctx_b = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx_a["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "X",
                    "client_id": str(ctx_a["client"].id),
                    "service_ids": [str(ctx_a["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )
        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx_b["svc_a"].id)},  # belongs to tenant B
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Price override on service attachment
# ═══════════════════════════════════════════════════════════════════════════


class TestPriceOverride:
    @pytest.mark.asyncio
    async def test_attach_with_price_override(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Override",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )

        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id), "price": "999.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 201

        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        svc_b_item = next(
            s for s in detail["services"] if s["service_id"] == str(ctx["svc_b"].id)
        )
        assert svc_b_item["price_at_attachment"] == "999.00"

        ledger = (
            await client.get(f"/api/v1/tenant/projects/{pid}/ledger", headers=admin_headers)
        ).json()
        charges = [e for e in ledger["entries"] if e["type"] == "charge"]
        assert any(
            e["amount"] == "999.00" and e["description"] == ctx["svc_b"].name for e in charges
        )
        # 500 default (svc_a at create) + 999 override (svc_b)
        assert ledger["summary"]["subtotal"] == "1499.00"

    @pytest.mark.asyncio
    async def test_attach_without_price_uses_default(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={"name": "Default", "client_id": str(ctx["client"].id)},
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )

        resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id)},
            headers=admin_headers,
        )
        assert resp.status_code == 201

        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        assert detail["services"][0]["price_at_attachment"] == "500.00"

        ledger = (
            await client.get(f"/api/v1/tenant/projects/{pid}/ledger", headers=admin_headers)
        ).json()
        assert ledger["summary"]["subtotal"] == "500.00"

    @pytest.mark.asyncio
    async def test_attach_non_positive_price_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "BadPrice",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )

        for bad in ("0.00", "-5.00"):
            resp = await client.post(
                f"/api/v1/tenant/projects/{pid}/services",
                json={"service_id": str(ctx["svc_b"].id), "price": bad},
                headers=admin_headers,
            )
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_with_service_prices_override(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Prices",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id), str(ctx["svc_b"].id)],
                "service_prices": {str(ctx["svc_b"].id): "750.00"},
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        prices = {s["service_id"]: s["price_at_attachment"] for s in detail["services"]}
        assert prices[str(ctx["svc_a"].id)] == "500.00"  # no override -> default
        assert prices[str(ctx["svc_b"].id)] == "750.00"

        ledger = (
            await client.get(f"/api/v1/tenant/projects/{pid}/ledger", headers=admin_headers)
        ).json()
        charges = [e for e in ledger["entries"] if e["type"] == "charge"]
        assert {e["amount"] for e in charges} == {"500.00", "750.00"}
        assert ledger["summary"]["subtotal"] == "1250.00"

    @pytest.mark.asyncio
    async def test_create_without_service_prices_uses_defaults(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "NoPrices",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id), str(ctx["svc_b"].id)],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        assert all(s["price_at_attachment"] == "500.00" for s in detail["services"])

        ledger = (
            await client.get(f"/api/v1/tenant/projects/{pid}/ledger", headers=admin_headers)
        ).json()
        assert ledger["summary"]["subtotal"] == "1000.00"


# ═══════════════════════════════════════════════════════════════════════════
# Audit log
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectAudit:
    @pytest.mark.asyncio
    async def test_project_created_audit(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Auditable",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id), str(ctx["svc_b"].id)],
            },
            headers=admin_headers,
        )
        pid = resp.json()["id"]

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.entity_id == pid,
                        AuditLog.action == "project.created",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].details["service_count"] == 2

    @pytest.mark.asyncio
    async def test_project_updated_audit(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={"name": "ToUpdate", "client_id": str(ctx["client"].id)},
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"name": "Updated Name", "status": "active"},
            headers=admin_headers,
        )
        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.entity_id == pid,
                        AuditLog.action == "project.updated",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert "name" in rows[0].details["changed_keys"]
        assert "status" in rows[0].details["changed_keys"]

    @pytest.mark.asyncio
    async def test_service_attached_audit(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Att",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )
        await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id)},
            headers=admin_headers,
        )
        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.entity_id == pid,
                        AuditLog.action == "project.service_attached",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].details["service_id"] == str(ctx["svc_b"].id)

    @pytest.mark.asyncio
    async def test_milestone_updated_audit(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "MA",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        mid = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "milestones"
        ][0]["id"]
        await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"status": "completed", "actual_date": "2026-08-15"},
            headers=admin_headers,
        )
        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.entity_id == mid,
                        AuditLog.action == "project.milestone_updated",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert "status" in rows[0].details["changed_keys"]
        assert "actual_date" in rows[0].details["changed_keys"]


# ═══════════════════════════════════════════════════════════════════════════
# Project overview (TODO-072)
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectOverview:
    @pytest.mark.asyncio
    async def test_overview_returns_completion_and_placeholders(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Overview",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/tenant/projects/{pid}/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == pid
        assert data["name"] == "Overview"
        assert data["milestone_total"] == 2  # svc_a has 2 milestone steps
        assert data["milestone_completed"] == 0
        assert data["milestone_completion_pct"] == 0.0
        assert data["total_invoiced"] == "0.00"
        assert data["total_paid"] == "0.00"
        assert data["balance_due"] == "0.00"
        assert data["linked_invoices"] == []

    @pytest.mark.asyncio
    async def test_overview_reflects_completed_milestones(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Overview2",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]
        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        mid = detail["milestones"][0]["id"]
        upd = await client.patch(
            f"/api/v1/tenant/projects/{pid}/milestones/{mid}",
            json={"status": "completed"},
            headers=admin_headers,
        )
        assert upd.status_code == 200

        resp = await client.get(f"/api/v1/tenant/projects/{pid}/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["milestone_total"] == 2
        assert data["milestone_completed"] == 1
        assert data["milestone_completion_pct"] == 50.0

    @pytest.mark.asyncio
    async def test_overview_service_breakdown_with_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "Breakdown",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        ps_id = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "services"
        ][0]["id"]

        inv_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
            headers=admin_headers,
        )
        assert inv_resp.status_code == 201
        inv_id = inv_resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=admin_headers)
        pay_resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "200.00", "method": "bank_transfer"},
            headers=admin_headers,
        )
        assert pay_resp.status_code == 201

        resp = await client.get(f"/api/v1/tenant/projects/{pid}/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoiced"] == "500.00"
        assert data["total_paid"] == "200.00"
        assert data["balance_due"] == "300.00"
        assert len(data["service_breakdown"]) == 1
        item = data["service_breakdown"][0]
        assert item["service_id"] == str(ctx["svc_a"].id)
        assert item["service_name"] == ctx["svc_a"].name
        assert item["total_invoiced"] == "500.00"
        assert item["total_paid"] == "200.00"
        assert item["total_outstanding"] == "300.00"

    @pytest.mark.asyncio
    async def test_overview_service_breakdown_custom_line_item(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={"name": "Custom Breakdown", "client_id": str(ctx["client"].id)},
                headers=admin_headers,
            )
        ).json()["id"]

        inv_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": pid,
                "line_items": [
                    {"description": "Setup fee", "unit_price": "250.00", "quantity": "2"}
                ],
            },
            headers=admin_headers,
        )
        assert inv_resp.status_code == 201
        inv_id = inv_resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=admin_headers)

        resp = await client.get(f"/api/v1/tenant/projects/{pid}/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["service_breakdown"]) == 1
        item = data["service_breakdown"][0]
        assert item["service_id"] is None
        assert item["service_name"] == "Custom"
        assert item["total_invoiced"] == "500.00"
        assert item["total_paid"] == "0.00"
        assert item["total_outstanding"] == "500.00"

    @pytest.mark.asyncio
    async def test_overview_not_found(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        resp = await client.get(
            "/api/v1/tenant/projects/00000000-0000-0000-0000-000000000000/overview",
            headers=admin_headers,
        )
        assert resp.status_code == 404
        resp2 = await client.get(
            "/api/v1/tenant/projects/not-a-uuid/overview", headers=admin_headers
        )
        assert resp2.status_code == 404

    @pytest.mark.asyncio
    async def test_overview_paid_includes_advances_and_excludes_refunds(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "AdvanceFin",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        ps_id = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "services"
        ][0]["id"]

        # inv1: 500.00, overpaid by 100 -> advance created
        inv1 = (
            await client.post(
                "/api/v1/tenant/invoices/",
                json={"project_id": pid, "line_items": [{"project_service_id": ps_id}]},
                headers=admin_headers,
            )
        ).json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv1}/issue", headers=admin_headers)
        pay = await client.post(
            f"/api/v1/tenant/invoices/{inv1}/transactions",
            json={"amount": "600.00", "method": "bank_transfer"},
            headers=admin_headers,
        )
        assert pay.status_code == 201

        # refund 200 -> paid drops to 300 for inv1
        refund = await client.post(
            f"/api/v1/tenant/invoices/{inv1}/refund",
            json={"amount": "200.00"},
            headers=admin_headers,
        )
        assert refund.status_code == 201

        # inv2: 300.00 custom, advance of 100 applied -> paid 100
        inv2 = (
            await client.post(
                "/api/v1/tenant/invoices/",
                json={
                    "project_id": pid,
                    "line_items": [{"description": "Custom", "unit_price": "300.00"}],
                },
                headers=admin_headers,
            )
        ).json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv2}/issue", headers=admin_headers)
        applied = await client.post(
            f"/api/v1/tenant/invoices/{inv2}/apply-advance",
            json={},
            headers=admin_headers,
        )
        assert applied.status_code == 200

        resp = await client.get(f"/api/v1/tenant/projects/{pid}/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoiced"] == "800.00"
        assert data["total_paid"] == "400.00"  # 500 + 100 applied - 200 refund
        assert data["balance_due"] == "400.00"

        # client rollup reflects the same net paid
        resp = await client.get(
            f"/api/v1/tenant/clients/{ctx['client'].id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        cdata = resp.json()
        assert cdata["total_invoiced"] == "800.00"
        assert cdata["total_paid"] == "400.00"
        assert cdata["total_outstanding"] == "400.00"


# ═══════════════════════════════════════════════════════════════════════════
# Remove project service (TODO-070)
# ═══════════════════════════════════════════════════════════════════════════


class TestRemoveProjectService:
    @pytest.mark.asyncio
    async def test_remove_uninvoiced_service(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "Remove",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]
        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        ps_id = detail["services"][0]["id"]
        assert len(detail["milestones"]) == 2  # svc_a has 2 steps

        resp = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=admin_headers
        )
        assert resp.status_code == 204

        detail2 = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        assert all(s["id"] != ps_id for s in detail2["services"])
        assert detail2["services"] == []
        assert detail2["milestones"] == []  # cascade removed this service's milestones

    @pytest.mark.asyncio
    async def test_remove_invoiced_service_soft_cancels(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "SoftCancel",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]
        ps_id = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "services"
        ][0]["id"]

        # Invoice against the service, then issue it
        inv_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": pid,
                "line_items": [{"project_service_id": ps_id}],
            },
            headers=admin_headers,
        )
        assert inv_resp.status_code == 201
        inv_id = inv_resp.json()["id"]
        issue_resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/issue", headers=admin_headers
        )
        assert issue_resp.status_code == 200

        resp = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=admin_headers
        )
        assert resp.status_code == 204

        detail = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()
        svc = next(s for s in detail["services"] if s["id"] == ps_id)
        assert svc["status"] == "cancelled"
        assert len(detail["milestones"]) == 2  # milestones stay on soft path

        inv_detail = (
            await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=admin_headers)
        ).json()
        assert len(inv_detail["line_items"]) == 1
        assert inv_detail["line_items"][0]["project_service_id"] == ps_id

    @pytest.mark.asyncio
    async def test_remove_missing_404(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={"name": "Missing", "client_id": str(ctx["client"].id)},
                headers=admin_headers,
            )
        ).json()["id"]

        resp = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{uuid.uuid4()}",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_already_cancelled_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        create_resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "DupCancel",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        pid = create_resp.json()["id"]
        ps_id = (await client.get(f"/api/v1/tenant/projects/{pid}", headers=admin_headers)).json()[
            "services"
        ][0]["id"]

        # First delete: soft-cancel (service is referenced by no invoice -> hard
        # delete would apply; to force the soft path we invoice it first)
        inv_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": pid,
                "line_items": [{"project_service_id": ps_id}],
            },
            headers=admin_headers,
        )
        assert inv_resp.status_code == 201
        inv_id = inv_resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=admin_headers)

        resp = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=admin_headers
        )
        assert resp.status_code == 204

        # Second delete: already cancelled -> 409
        resp2 = await client.delete(
            f"/api/v1/tenant/projects/{pid}/services/{ps_id}", headers=admin_headers
        )
        assert resp2.status_code == 409


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-INVOICE (per-project opt-in)
# ═══════════════════════════════════════════════════════════════════════════


async def _invoices_for_project(
    session: AsyncSession, project_id: str
) -> list[Invoice]:
    stmt = (
        select(Invoice)
        .where(Invoice.project_id == project_id)
        .order_by(Invoice.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _line_items_for_invoice(
    session: AsyncSession, invoice_id: str
) -> list[InvoiceLineItem]:
    stmt = (
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice_id)
        .order_by(InvoiceLineItem.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())


class TestAutoInvoice:
    @pytest.mark.asyncio
    async def test_create_and_attach_services_without_auto_drafts(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={
                "name": "ProjectOnDemand",
                "client_id": str(ctx["client"].id),
                "service_ids": [str(ctx["svc_a"].id)],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        # Projects are created without auto-generating draft invoices
        invoices = await _invoices_for_project(db_session, pid)
        assert len(invoices) == 0

        # Attaching services also keeps financial tracking on the live statement without auto-drafting
        await client.patch(
            f"/api/v1/tenant/projects/{pid}",
            json={"status": "active"},
            headers=admin_headers,
        )
        attach_resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/services",
            json={"service_id": str(ctx["svc_b"].id)},
            headers=admin_headers,
        )
        assert attach_resp.status_code == 201
        assert len(await _invoices_for_project(db_session, pid)) == 0

    @pytest.mark.asyncio
    async def test_generate_statement_invoice_on_demand(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        pid = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "StatementOnDemand",
                    "client_id": str(ctx["client"].id),
                    "service_ids": [str(ctx["svc_a"].id)],
                },
                headers=admin_headers,
            )
        ).json()["id"]

        # Generate statement invoice on demand
        gen_resp = await client.post(
            f"/api/v1/tenant/projects/{pid}/statement-invoice",
            headers=admin_headers,
        )
        assert gen_resp.status_code == 200
        inv_data = gen_resp.json()
        assert inv_data["is_auto"] is True
        assert inv_data["status"] == "draft"

