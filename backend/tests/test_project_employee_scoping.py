"""Tests for employee project scoping and financial sensitivity protection."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    ProjectMemberRole,
    ProjectStatus,
    TenantStatus,
)
from app.models.plan import Plan
from app.models.project import Project, ProjectMember
from app.models.tenant import Tenant
from app.services.roles import attach_default_role

_TEST_PWD = "testpass123!"


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=10,
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
        business_name=f"TestCo-{uuid.uuid4().hex[:6]}",
        slug=f"testco-{uuid.uuid4().hex[:6]}",
        plan_id=plan_id,
        status=TenantStatus.ACTIVE,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role: AdminUserRole,
    email_prefix: str,
) -> tuple[AdminUser, str]:
    user = AdminUser(
        email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password(_TEST_PWD),
        full_name=f"User {email_prefix}",
        tenant_id=tenant_id,
        role=role,
        is_active=True,
    )
    session.add(user)
    await attach_default_role(session, user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant_id),
        role=role.value,
        realm="admin",
    )
    return user, token


async def _create_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    c = Client(
        tenant_id=tenant_id,
        name=f"Client-{uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        email=f"client-{uuid.uuid4().hex[:6]}@example.com",
        status=ClientStatus.ACTIVE,
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


async def _create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    name: str,
) -> Project:
    p = Project(
        tenant_id=tenant_id,
        client_id=client_id,
        name=name,
        status=ProjectStatus.ACTIVE,
        start_date=date.today(),
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest.mark.asyncio
async def test_employee_project_listing_and_access_scoping(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """Verify that employee only sees assigned projects and cannot access unassigned projects."""
    plan = await _create_plan(session)
    tenant = await _create_tenant(session, plan.id)
    c = await _create_client(session, tenant.id)

    admin, admin_token = await _create_user(session, tenant.id, AdminUserRole.ADMIN, "admin")
    emp, emp_token = await _create_user(session, tenant.id, AdminUserRole.EMPLOYEE, "emp")

    # Create 2 projects
    proj_assigned = await _create_project(session, tenant.id, c.id, "Assigned Project")
    proj_unassigned = await _create_project(session, tenant.id, c.id, "Unassigned Project")

    # Assign employee to proj_assigned only
    membership = ProjectMember(
        project_id=proj_assigned.id,
        user_id=emp.id,
        tenant_id=tenant.id,
        role=ProjectMemberRole.CONTRIBUTOR,
    )
    session.add(membership)
    await session.commit()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 1. Admin lists projects -> sees both (2)
    res_admin = await client.get("/api/v1/tenant/projects", headers=admin_headers)
    assert res_admin.status_code == 200
    admin_items = res_admin.json()["items"]
    admin_ids = [item["id"] for item in admin_items]
    assert str(proj_assigned.id) in admin_ids
    assert str(proj_unassigned.id) in admin_ids
    assert res_admin.json()["total"] == 2

    # 2. Employee lists projects -> sees only assigned project (1)
    res_emp = await client.get("/api/v1/tenant/projects", headers=emp_headers)
    assert res_emp.status_code == 200
    emp_items = res_emp.json()["items"]
    assert len(emp_items) == 1
    assert emp_items[0]["id"] == str(proj_assigned.id)
    assert res_emp.json()["total"] == 1

    # 3. Employee accesses assigned project detail -> 200
    res_detail_ok = await client.get(
        f"/api/v1/tenant/projects/{proj_assigned.id}", headers=emp_headers
    )
    assert res_detail_ok.status_code == 200
    assert res_detail_ok.json()["name"] == "Assigned Project"

    # 4. Employee accesses unassigned project detail -> 403 Forbidden
    res_detail_denied = await client.get(
        f"/api/v1/tenant/projects/{proj_unassigned.id}", headers=emp_headers
    )
    assert res_detail_denied.status_code == 403
    err_payload = res_detail_denied.json()
    err_text = str(err_payload.get("detail") or err_payload.get("error") or err_payload).lower()
    assert "access" in err_text or "forbidden" in err_text

    # 5. Project picker scoping for employee
    res_picker = await client.get("/api/v1/tenant/projects/picker", headers=emp_headers)
    assert res_picker.status_code == 200
    picker_items = res_picker.json()["items"]
    assert len(picker_items) == 1
    assert picker_items[0]["id"] == str(proj_assigned.id)


@pytest.mark.asyncio
async def test_employee_financial_masking_and_ledger_protection(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """Verify that employee cannot see financial figures or access ledger without permission."""
    plan = await _create_plan(session)
    tenant = await _create_tenant(session, plan.id)
    c = await _create_client(session, tenant.id)

    admin, admin_token = await _create_user(session, tenant.id, AdminUserRole.ADMIN, "admin")
    emp, emp_token = await _create_user(session, tenant.id, AdminUserRole.EMPLOYEE, "emp")

    proj = await _create_project(session, tenant.id, c.id, "Financial Masking Project")

    # Assign employee to project
    membership = ProjectMember(
        project_id=proj.id,
        user_id=emp.id,
        tenant_id=tenant.id,
        role=ProjectMemberRole.CONTRIBUTOR,
    )
    session.add(membership)
    await session.commit()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 1. Admin overview -> has financial figures
    res_admin_ov = await client.get(
        f"/api/v1/tenant/projects/{proj.id}/overview", headers=admin_headers
    )
    assert res_admin_ov.status_code == 200
    admin_data = res_admin_ov.json()
    assert admin_data["total_billed"] is not None
    assert admin_data["total_invoiced"] is not None

    # 2. Employee overview -> financial figures are MASKED (None)
    res_emp_ov = await client.get(
        f"/api/v1/tenant/projects/{proj.id}/overview", headers=emp_headers
    )
    assert res_emp_ov.status_code == 200
    emp_data = res_emp_ov.json()
    assert emp_data["project_id"] == str(proj.id)
    assert emp_data["name"] == "Financial Masking Project"
    # Milestone progress is visible:
    assert emp_data["milestone_total"] == 0
    # Financial fields are safely masked:
    assert emp_data["total_billed"] is None
    assert emp_data["total_invoiced"] is None
    assert emp_data["total_paid"] is None
    assert emp_data["balance_due"] is None
    assert emp_data["due"] is None
    assert emp_data["advance_balance"] is None
    assert emp_data["linked_invoices"] == []

    # 3. Employee accessing ledger -> 403 Forbidden
    res_emp_ledger = await client.get(
        f"/api/v1/tenant/projects/{proj.id}/ledger", headers=emp_headers
    )
    assert res_emp_ledger.status_code == 403

    # 4. Employee accessing payments endpoint -> 403 Forbidden
    res_emp_payments = await client.get(
        f"/api/v1/tenant/projects/{proj.id}/payments", headers=emp_headers
    )
    assert res_emp_payments.status_code == 403

    # 5. Admin accessing ledger & payments -> 200 OK
    res_admin_ledger = await client.get(
        f"/api/v1/tenant/projects/{proj.id}/ledger", headers=admin_headers
    )
    assert res_admin_ledger.status_code == 200

    res_admin_payments = await client.get(
        f"/api/v1/tenant/projects/{proj.id}/payments", headers=admin_headers
    )
    assert res_admin_payments.status_code == 200
