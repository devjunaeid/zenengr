"""Tests for FEAT-017 part 1: NotificationEventType expansion, channel-aware
notification preferences, Notification model (TODO-168/169).

The Notification service/WS dispatch is out of scope (next batch); here we
cover the model, the preference channel dimension, and the API surface.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.client_user import ClientUser
from app.models.comment import Comment
from app.models.enums import (
    CommentAuthorType,
    MilestoneStatus,
    NotificationChannel,
    NotificationEventType,
)
from app.models.notification import Notification
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService
from app.models.role import Role
from app.models.service import Service
from app.models.tenant import Tenant
from app.schemas.roles import RolePermissionInput
from app.services import invoices as invoice_service
from app.services import notifications as notification_service
from app.services.notification_preferences import (
    get_enabled_map,
    list_preferences,
    update_preferences,
)
from app.services.roles import assign_user_role, create_role

_TEST_PWD = "testpass123!"

_ALL_EVENT_VALUES = [
    "new_comment",
    "invoice_issued",
    "payment_received",
    "milestone_completed",
    "refund_recorded",
    "advance_applied",
    "project_created",
]


# ── Helpers (mirror test_feat011_api.py) ────────────────────────────────────


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


async def _create_tenant(session: AsyncSession, plan_id: uuid.UUID) -> Tenant:
    tenant = Tenant(
        business_name="TestCo",
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status="active",
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_admin(session: AsyncSession, tenant_id: uuid.UUID, tag: str = "n") -> AdminUser:
    admin = AdminUser(
        tenant_id=tenant_id,
        email=f"{tag}-{uuid.uuid4().hex[:8]}@testco.com",
        full_name="Test Admin",
        hashed_password=hash_password(_TEST_PWD),
        role="admin",
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════
# Enum surface
# ═══════════════════════════════════════════════════════════════════════════


class TestEnums:
    @pytest.mark.anyio
    async def test_event_type_has_seven_values(self):
        assert [e.value for e in NotificationEventType] == _ALL_EVENT_VALUES

    @pytest.mark.anyio
    async def test_channel_values(self):
        assert [c.value for c in NotificationChannel] == ["email", "inapp"]
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.INAPP == "inapp"


# ═══════════════════════════════════════════════════════════════════════════
# Preference service — channel dimension
# ═══════════════════════════════════════════════════════════════════════════


class TestPreferenceChannels:
    @pytest.mark.anyio
    async def test_list_creates_default_rows_per_channel(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)

        inapp = await list_preferences(
            db_session,
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            channel=NotificationChannel.INAPP,
        )
        assert [p["event_type"] for p in inapp] == _ALL_EVENT_VALUES
        assert all(p["enabled"] is True for p in inapp)

        email = await list_preferences(
            db_session,
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            channel=NotificationChannel.EMAIL,
        )
        assert [p["event_type"] for p in email] == _ALL_EVENT_VALUES
        assert all(p["enabled"] is True for p in email)

    @pytest.mark.anyio
    async def test_update_inapp_leaves_email_untouched(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)

        await update_preferences(
            db_session,
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            channel=NotificationChannel.INAPP,
            entries=[(NotificationEventType.NEW_COMMENT, False)],
        )

        email_map = await get_enabled_map(
            db_session,
            user_type="admin_user",
            user_ids=[admin.id],
            event_type=NotificationEventType.NEW_COMMENT,
            channel=NotificationChannel.EMAIL,
        )
        assert email_map[admin.id] is True

        inapp_map = await get_enabled_map(
            db_session,
            user_type="admin_user",
            user_ids=[admin.id],
            event_type=NotificationEventType.NEW_COMMENT,
            channel=NotificationChannel.INAPP,
        )
        assert inapp_map[admin.id] is False

        # Missing rows default to enabled for an unrelated user
        other = await _create_admin(db_session, tenant.id, tag="other")
        other_map = await get_enabled_map(
            db_session,
            user_type="admin_user",
            user_ids=[other.id],
            event_type=NotificationEventType.REFUND_RECORDED,
            channel=NotificationChannel.INAPP,
        )
        assert other_map[other.id] is True

    @pytest.mark.anyio
    async def test_get_enabled_map_filters_channel(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)

        await update_preferences(
            db_session,
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            channel=NotificationChannel.EMAIL,
            entries=[(NotificationEventType.PAYMENT_RECEIVED, False)],
        )

        email_map = await get_enabled_map(
            db_session,
            user_type="admin_user",
            user_ids=[admin.id],
            event_type=NotificationEventType.PAYMENT_RECEIVED,
            channel=NotificationChannel.EMAIL,
        )
        assert email_map[admin.id] is False

        inapp_map = await get_enabled_map(
            db_session,
            user_type="admin_user",
            user_ids=[admin.id],
            event_type=NotificationEventType.PAYMENT_RECEIVED,
            channel=NotificationChannel.INAPP,
        )
        assert inapp_map[admin.id] is True


# ═══════════════════════════════════════════════════════════════════════════
# Notification-preferences API — channel dimension
# ═══════════════════════════════════════════════════════════════════════════


class TestPreferenceChannelsApi:
    @pytest.mark.anyio
    async def test_get_channel_param_inapp(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.get(
            "/api/v1/auth/notification-preferences?channel=inapp", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [d["event_type"] for d in data] == _ALL_EVENT_VALUES
        assert all(d["enabled"] is True for d in data)

        # Default (no channel) is email; email rows unaffected by inapp reads
        email_resp = await client.get("/api/v1/auth/notification-preferences", headers=headers)
        assert email_resp.status_code == 200
        assert [d["event_type"] for d in email_resp.json()] == _ALL_EVENT_VALUES

    @pytest.mark.anyio
    async def test_patch_channel_updates_inapp_only(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        patch = await client.patch(
            "/api/v1/auth/notification-preferences",
            json={
                "channel": "inapp",
                "preferences": [{"event_type": "new_comment", "enabled": False}],
            },
            headers=headers,
        )
        assert patch.status_code == 200
        by_type = {d["event_type"]: d["enabled"] for d in patch.json()}
        assert by_type["new_comment"] is False
        assert by_type["invoice_issued"] is True

        # Email channel untouched
        email_resp = await client.get("/api/v1/auth/notification-preferences", headers=headers)
        assert email_resp.status_code == 200
        email_by_type = {d["event_type"]: d["enabled"] for d in email_resp.json()}
        assert email_by_type["new_comment"] is True

        # Inapp persisted
        inapp_resp = await client.get(
            "/api/v1/auth/notification-preferences?channel=inapp", headers=headers
        )
        assert inapp_resp.status_code == 200
        inapp_by_type = {d["event_type"]: d["enabled"] for d in inapp_resp.json()}
        assert inapp_by_type["new_comment"] is False

    @pytest.mark.anyio
    async def test_client_endpoints_accept_channel(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        from app.models.client import Client
        from app.models.client_user import ClientUser

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = Client(
            tenant_id=tenant.id,
            name="TestClient",
            client_type="company",
            status="active",
        )
        db_session.add(cli)
        await db_session.commit()
        await db_session.refresh(cli)
        cu = ClientUser(
            client_id=cli.id,
            tenant_id=tenant.id,
            email=f"cu-{uuid.uuid4().hex[:8]}@test.com",
            full_name="Test Client User",
            hashed_password=hash_password(_TEST_PWD),
            is_active=True,
        )
        db_session.add(cu)
        await db_session.commit()
        await db_session.refresh(cu)
        token = create_access_token(
            user_id=str(cu.id),
            tenant_id=str(cu.tenant_id),
            role="client_user",
            realm="client",
            client_id=str(cu.client_id),
        )
        headers = {"Authorization": f"Bearer {token}"}

        get_resp = await client.get(
            "/api/v1/client/auth/notification-preferences?channel=inapp",
            headers=headers,
        )
        assert get_resp.status_code == 200
        assert [d["event_type"] for d in get_resp.json()] == _ALL_EVENT_VALUES

        patch = await client.patch(
            "/api/v1/client/auth/notification-preferences",
            json={
                "channel": "inapp",
                "preferences": [{"event_type": "project_created", "enabled": False}],
            },
            headers=headers,
        )
        assert patch.status_code == 200
        assert {d["event_type"]: d["enabled"] for d in patch.json()}["project_created"] is False


# ═══════════════════════════════════════════════════════════════════════════
# Notification model
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationModel:
    @pytest.mark.anyio
    async def test_create_and_query_by_user(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)

        n = Notification(
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            event_type=NotificationEventType.PROJECT_CREATED,
            title="Project created",
            body="A new project was created.",
            entity_type="project",
            entity_id=str(uuid.uuid4()),
            data={"project_name": "Proj X"},
        )
        db_session.add(n)
        await db_session.commit()
        await db_session.refresh(n)

        assert n.id is not None
        assert n.is_read is False
        assert n.created_at is not None
        assert n.data == {"project_name": "Proj X"}

        result = await db_session.execute(
            select(Notification).where(Notification.user_id == admin.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].id == n.id
        assert rows[0].event_type == NotificationEventType.PROJECT_CREATED

    @pytest.mark.anyio
    async def test_is_read_default_false_and_indexes(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)

        n = Notification(
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            event_type=NotificationEventType.INVOICE_ISSUED,
            title="Invoice issued",
        )
        db_session.add(n)
        await db_session.flush()

        assert n.is_read is False

        result = await db_session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'notifications'")
        )
        index_names = {row[0] for row in result}
        assert {"ix_notifications_user_created", "ix_notifications_user_read"} <= index_names


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-017 part 2 helpers (project/client/service bootstrap)
# ═══════════════════════════════════════════════════════════════════════════


async def _create_admin_with_role(
    session: AsyncSession, tenant_id: uuid.UUID, role: str, tag: str = "n"
) -> AdminUser:
    admin = AdminUser(
        tenant_id=tenant_id,
        email=f"{tag}-{uuid.uuid4().hex[:8]}@testco.com",
        full_name=f"Test {role}",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def _create_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=f"Test Client {uuid.uuid4().hex[:6]}",
        client_type="company",
        status="active",
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_client_user(
    session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=f"cu-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=True,
    )
    session.add(cu)
    await session.commit()
    await session.refresh(cu)
    return cu


async def _create_project(
    session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        client_id=client_id,
        name=f"Proj {uuid.uuid4().hex[:6]}",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def _create_service(session: AsyncSession, tenant_id: uuid.UUID) -> Service:
    service = Service(
        tenant_id=tenant_id,
        name=f"Svc {uuid.uuid4().hex[:6]}",
        default_price="100.00",
        is_active=True,
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


async def _create_milestone(
    session: AsyncSession, project: Project, service: Service
) -> ProjectMilestone:
    ps = ProjectService(project_id=project.id, service_id=service.id)
    session.add(ps)
    await session.flush()
    milestone = ProjectMilestone(
        project_id=project.id,
        project_service_id=ps.id,
        service_id=service.id,
        name="Milestone One",
        sequence_order=1,
    )
    session.add(milestone)
    await session.commit()
    await session.refresh(milestone)
    return milestone


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
# Notification service — row creation + fan-out (TODO-170)
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationServiceCreate:
    @pytest.mark.anyio
    async def test_notify_users_creates_row_per_key(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        client = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, client.id)

        rows = await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.INVOICE_ISSUED,
            title="Invoice INV-1 issued",
            body="",
            entity_type="invoice",
            entity_id="abc-123",
            recipient_keys=[f"admin_user:{admin.id}", f"client_user:{cu.id}"],
        )
        assert len(rows) == 2
        assert rows[0].created_at is not None
        assert rows[0].data == {}

        result = await db_session.execute(
            select(Notification).where(Notification.tenant_id == tenant.id)
        )
        persisted = result.scalars().all()
        assert len(persisted) == 2
        by_type = {row.user_type: row for row in persisted}
        assert by_type["admin_user"].user_id == admin.id
        assert by_type["client_user"].user_id == cu.id
        assert by_type["admin_user"].event_type == NotificationEventType.INVOICE_ISSUED
        assert by_type["admin_user"].title == "Invoice INV-1 issued"
        assert by_type["admin_user"].entity_id == "abc-123"
        assert by_type["admin_user"].is_read is False

    @pytest.mark.anyio
    async def test_notify_users_skips_malformed_keys(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)

        rows = await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.PROJECT_CREATED,
            title="Project created",
            body="",
            recipient_keys=[
                f"admin_user:{admin.id}",
                "admin_user:not-a-uuid",
                "bogus-key",
            ],
        )
        assert len(rows) == 1
        assert rows[0].user_id == admin.id


# ═══════════════════════════════════════════════════════════════════════════
# Recipient resolution helpers (TODO-170)
# ═══════════════════════════════════════════════════════════════════════════


class TestRecipientHelpers:
    @pytest.mark.anyio
    async def test_staff_keys_view_invoices_admin_and_manager(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        employee = await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")

        keys = await notification_service.staff_keys_with_permission(
            db_session,
            tenant_id=tenant.id,
            action="view",
            resource="invoices",
        )
        assert sorted(keys) == sorted([f"admin_user:{admin.id}", f"admin_user:{manager.id}"])
        assert f"admin_user:{employee.id}" not in keys

    @pytest.mark.anyio
    async def test_staff_keys_inactive_user_excluded(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        inactive = await _create_admin_with_role(db_session, tenant.id, "admin", tag="ia")
        inactive.is_active = False
        await db_session.commit()

        keys = await notification_service.staff_keys_with_permission(
            db_session,
            tenant_id=tenant.id,
            action="view",
            resource="invoices",
        )
        assert keys == [f"admin_user:{admin.id}"]

    @pytest.mark.anyio
    async def test_staff_keys_db_backed_role_grant(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        employee = await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")

        role = await create_role(
            db_session,
            tenant_id=tenant.id,
            name=f"BillingViewer-{uuid.uuid4().hex[:6]}",
            description="",
            permissions=[RolePermissionInput(action="view", resource="invoices", granted=True)],
            actor_id=employee.id,
        )
        await assign_user_role(
            db_session,
            tenant_id=tenant.id,
            target_user_id=employee.id,
            role_id=role.id,
            actor_id=employee.id,
        )

        keys = await notification_service.staff_keys_with_permission(
            db_session,
            tenant_id=tenant.id,
            action="view",
            resource="invoices",
        )
        assert f"admin_user:{employee.id}" in keys

    @pytest.mark.anyio
    async def test_staff_keys_admin_role_bypass(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        user = await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")

        admin_role = Role(name="admin", description="", is_system=True, tenant_id=None)
        db_session.add(admin_role)
        await db_session.flush()
        user.role_id = admin_role.id
        await db_session.commit()

        keys = await notification_service.staff_keys_with_permission(
            db_session,
            tenant_id=tenant.id,
            action="view",
            resource="invoices",
        )
        assert f"admin_user:{user.id}" in keys

    @pytest.mark.anyio
    async def test_client_keys_for_client_active_only(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        client = await _create_client(db_session, tenant.id)
        other_client = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, client.id)
        inactive = await _create_client_user(db_session, tenant.id, client.id)
        inactive.is_active = False
        other = await _create_client_user(db_session, tenant.id, other_client.id)
        await db_session.commit()

        keys = await notification_service.client_keys_for_client(db_session, client_id=client.id)
        assert keys == [f"client_user:{cu.id}"]
        assert f"client_user:{inactive.id}" not in keys
        assert f"client_user:{other.id}" not in keys

    @pytest.mark.anyio
    async def test_filter_keys_by_pref_respects_inapp_toggle(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        client = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, client.id)

        await update_preferences(
            db_session,
            user_id=admin.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            channel=NotificationChannel.INAPP,
            entries=[(NotificationEventType.INVOICE_ISSUED, False)],
        )

        keys = [f"admin_user:{admin.id}", f"client_user:{cu.id}"]
        kept = await notification_service.filter_keys_by_pref(
            db_session,
            event_type=NotificationEventType.INVOICE_ISSUED,
            keys=keys,
        )
        # admin disabled in-app; client user has no rows (default enabled)
        assert kept == [f"client_user:{cu.id}"]


# ═══════════════════════════════════════════════════════════════════════════
# Notifications REST API — staff realm (TODO-172)
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationsApiStaff:
    @pytest.mark.anyio
    async def test_list_unread_mark_read_read_all(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.INVOICE_ISSUED,
            title="Invoice INV-1 issued",
            body="",
            entity_type="invoice",
            entity_id="inv-1",
            recipient_keys=[f"admin_user:{admin.id}"],
        )
        await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.MILESTONE_COMPLETED,
            title="Milestone completed: M1",
            body="",
            recipient_keys=[f"admin_user:{admin.id}"],
        )
        await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.PROJECT_CREATED,
            title="Project created: P1",
            body="",
            recipient_keys=[f"admin_user:{admin.id}"],
        )

        resp = await client.get("/api/v1/tenant/notifications", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["unread"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 3
        item = data["items"][0]
        assert set(item) == {
            "id",
            "event_type",
            "title",
            "body",
            "entity_type",
            "entity_id",
            "data",
            "is_read",
            "created_at",
        }
        assert item["is_read"] is False
        assert item["data"] == {}

        count = await client.get("/api/v1/tenant/notifications/unread-count", headers=headers)
        assert count.status_code == 200
        assert count.json() == {"count": 3}

        nid = data["items"][0]["id"]
        mark = await client.post(f"/api/v1/tenant/notifications/{nid}/read", headers=headers)
        assert mark.status_code == 204

        count = await client.get("/api/v1/tenant/notifications/unread-count", headers=headers)
        assert count.json() == {"count": 2}

        # unread_only filter leaves total at 3 but returns 2 items
        unread = await client.get("/api/v1/tenant/notifications?unread_only=true", headers=headers)
        assert unread.status_code == 200
        unread_data = unread.json()
        assert unread_data["total"] == 3
        assert unread_data["unread"] == 2
        assert len(unread_data["items"]) == 2

        all_read = await client.post("/api/v1/tenant/notifications/read-all", headers=headers)
        assert all_read.status_code == 204
        count = await client.get("/api/v1/tenant/notifications/unread-count", headers=headers)
        assert count.json() == {"count": 0}

    @pytest.mark.anyio
    async def test_mark_read_other_users_notification_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        other = await _create_admin(db_session, tenant.id, tag="other")
        headers = await _admin_auth_header(admin)

        rows = await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.PROJECT_CREATED,
            title="For other",
            body="",
            recipient_keys=[f"admin_user:{other.id}"],
        )
        assert len(rows) == 1

        mark = await client.post(f"/api/v1/tenant/notifications/{rows[0].id}/read", headers=headers)
        assert mark.status_code == 404

    @pytest.mark.anyio
    async def test_pagination(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        for idx in range(5):
            await notification_service.notify_users(
                db_session,
                tenant_id=tenant.id,
                event_type=NotificationEventType.PROJECT_CREATED,
                title=f"Project {idx}",
                body="",
                recipient_keys=[f"admin_user:{admin.id}"],
            )

        resp = await client.get("/api/v1/tenant/notifications?page=2&page_size=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert data["unread"] == 5
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert len(data["items"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Notifications REST API — client realm (TODO-172)
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationsApiClient:
    @pytest.mark.anyio
    async def test_client_realm_own_notifications_only(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        headers = await _client_auth_header(cu)

        await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.INVOICE_ISSUED,
            title="Invoice for client",
            body="",
            entity_type="invoice",
            entity_id="inv-c",
            recipient_keys=[f"client_user:{cu.id}", f"admin_user:{admin.id}"],
        )

        resp = await client.get("/api/v1/client/notifications", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1  # admin row invisible to client realm
        assert data["unread"] == 1
        item = data["items"][0]
        assert item["entity_id"] == "inv-c"
        assert item["title"] == "Invoice for client"

        count = await client.get("/api/v1/client/notifications/unread-count", headers=headers)
        assert count.json() == {"count": 1}

        mark = await client.post(f"/api/v1/client/notifications/{item['id']}/read", headers=headers)
        assert mark.status_code == 204
        count = await client.get("/api/v1/client/notifications/unread-count", headers=headers)
        assert count.json() == {"count": 0}

        # unread_only after marking all read
        unread = await client.get("/api/v1/client/notifications?unread_only=true", headers=headers)
        assert unread.status_code == 200
        assert len(unread.json()["items"]) == 0

        all_read = await client.post("/api/v1/client/notifications/read-all", headers=headers)
        assert all_read.status_code == 204

    @pytest.mark.anyio
    async def test_client_mark_read_admin_notification_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        headers = await _client_auth_header(cu)

        rows = await notification_service.notify_users(
            db_session,
            tenant_id=tenant.id,
            event_type=NotificationEventType.PROJECT_CREATED,
            title="For admin",
            body="",
            recipient_keys=[f"admin_user:{admin.id}"],
        )
        mark = await client.post(f"/api/v1/client/notifications/{rows[0].id}/read", headers=headers)
        assert mark.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Emitter smoke tests (TODO-170; wired into business services next batch)
# ═══════════════════════════════════════════════════════════════════════════


class TestEmitterSmoke:
    @pytest.mark.anyio
    async def test_notify_milestone_completed_staff_and_client(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")
        client = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, client.id)
        project = await _create_project(db_session, tenant.id, client.id)
        service = await _create_service(db_session, tenant.id)
        milestone = await _create_milestone(db_session, project, service)

        await notification_service.notify_milestone_completed(db_session, milestone_id=milestone.id)

        result = await db_session.execute(
            select(Notification).where(
                Notification.event_type == NotificationEventType.MILESTONE_COMPLETED
            )
        )
        rows = result.scalars().all()
        user_ids = {row.user_id for row in rows}
        # admin + manager (view/milestones via manage grant) + client user;
        # employee has no milestones permission
        assert user_ids == {admin.id, manager.id, cu.id}
        assert all(row.entity_type == "milestone" for row in rows)
        assert all(row.entity_id == str(milestone.id) for row in rows)
        assert all(row.title == f"Milestone completed: {milestone.name}" for row in rows)

    @pytest.mark.anyio
    async def test_notify_comment_created_excludes_actor_and_internal(
        self, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, tenant.id)
        client = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, client.id)
        project = await _create_project(db_session, tenant.id, client.id)

        # Public comment authored by the admin: client users notified,
        # the acting admin is not.
        public = Comment(
            project_id=project.id,
            author_id=admin.id,
            author_type=CommentAuthorType.TENANT_ADMIN,
            author_name="Test Admin",
            content="Hello from staff",
            is_internal=False,
        )
        db_session.add(public)
        await db_session.commit()
        await notification_service.notify_comment_created(db_session, comment_id=public.id)

        result = await db_session.execute(
            select(Notification).where(Notification.event_type == NotificationEventType.NEW_COMMENT)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].user_id == cu.id
        assert rows[0].entity_type == "project"
        assert rows[0].entity_id == str(project.id)
        assert rows[0].body == "Hello from staff"

        # Internal comment: client users never see it, so no new rows.
        internal = Comment(
            project_id=project.id,
            author_id=cu.id,
            author_type=CommentAuthorType.CLIENT_USER,
            author_name="Test Client User",
            content="Internal note",
            is_internal=True,
        )
        db_session.add(internal)
        await db_session.commit()
        await notification_service.notify_comment_created(db_session, comment_id=internal.id)
        result = await db_session.execute(
            select(Notification).where(Notification.event_type == NotificationEventType.NEW_COMMENT)
        )
        rows = result.scalars().all()
        # Internal comment: staff with post/comments are notified (admin),
        # client users never see it -> exactly one admin row, no new client rows.
        assert len(rows) == 2
        admin_rows = [r for r in rows if r.user_type == "admin_user"]
        assert len(admin_rows) == 1
        assert admin_rows[0].user_id == admin.id
        assert admin_rows[0].body == "Internal note"
        client_rows = [r for r in rows if r.user_type == "client_user"]
        assert [r.user_id for r in client_rows] == [cu.id]


# ═══════════════════════════════════════════════════════════════════════════
# Hook integration tests (TODO-173): business services emit in-app rows
# ═══════════════════════════════════════════════════════════════════════════


async def _grant_role(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    target_user_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    resource: str,
) -> None:
    role = await create_role(
        session,
        tenant_id=tenant_id,
        name=f"Grant-{uuid.uuid4().hex[:6]}",
        description="",
        permissions=[RolePermissionInput(action=action, resource=resource, granted=True)],
        actor_id=actor_id,
    )
    await assign_user_role(
        session,
        tenant_id=tenant_id,
        target_user_id=target_user_id,
        role_id=role.id,
        actor_id=actor_id,
    )


async def _attach_service(
    session: AsyncSession, project_id: uuid.UUID, service: Service
) -> ProjectService:
    ps = ProjectService(
        project_id=project_id,
        service_id=service.id,
        price_at_attachment=service.default_price,
    )
    session.add(ps)
    await session.commit()
    await session.refresh(ps)
    return ps


async def _create_invoice_api(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
) -> str:
    resp = await client.post(
        "/api/v1/tenant/invoices/",
        json={
            "project_id": str(project_id),
            "line_items": [{"project_service_id": str(project_service_id)}],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _issue_api(client: AsyncClient, headers: dict[str, str], invoice_id: str) -> None:
    resp = await client.post(f"/api/v1/tenant/invoices/{invoice_id}/issue", headers=headers)
    assert resp.status_code == 200


async def _notification_rows(
    session: AsyncSession, tenant_id: uuid.UUID, event_type: NotificationEventType
) -> list[Notification]:
    result = await session.execute(
        select(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.event_type == event_type,
        )
    )
    return list(result.scalars().all())


class TestCommentHooks:
    @pytest.mark.anyio
    async def test_shared_comment_notifies_staff_and_client_excluding_actor(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        employee = await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")
        await _grant_role(db_session, tenant.id, employee.id, admin.id, "post", "comments")
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/projects/{project.id}/comments",
            json={"content": "Shared note", "is_internal": False},
            headers=headers,
        )
        assert resp.status_code == 201

        rows = await _notification_rows(db_session, tenant.id, NotificationEventType.NEW_COMMENT)
        # staff with post/comments (manager + employee-with-grant) + client;
        # admin is the actor and excluded
        assert {r.user_id for r in rows} == {manager.id, employee.id, cu.id}
        assert all(r.user_type == "admin_user" or r.user_id == cu.id for r in rows)
        assert all(r.entity_id == str(project.id) for r in rows)

        # Internal comment (posted by manager): staff only, no client rows.
        resp = await client.post(
            f"/api/v1/tenant/projects/{project.id}/comments",
            json={"content": "Internal note", "is_internal": True},
            headers=await _admin_auth_header(manager),
        )
        assert resp.status_code == 201

        rows = await _notification_rows(db_session, tenant.id, NotificationEventType.NEW_COMMENT)
        internal = [r for r in rows if r.body == "Internal note"]
        shared = [r for r in rows if r.body == "Shared note"]
        assert {r.user_id for r in internal} == {admin.id, employee.id}
        assert all(r.user_type == "admin_user" for r in internal)
        assert {r.user_id for r in shared} == {manager.id, employee.id, cu.id}

    @pytest.mark.anyio
    async def test_client_comment_notifies_staff_and_other_clients(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        cli = await _create_client(db_session, tenant.id)
        cu1 = await _create_client_user(db_session, tenant.id, cli.id)
        cu2 = await _create_client_user(db_session, tenant.id, cli.id)
        project = await _create_project(db_session, tenant.id, cli.id)

        resp = await client.post(
            f"/api/v1/client/projects/{project.id}/comments",
            json={"content": "From client", "is_internal": True},
            headers=await _client_auth_header(cu1),
        )
        assert resp.status_code == 201

        rows = await _notification_rows(db_session, tenant.id, NotificationEventType.NEW_COMMENT)
        # staff (admin + manager) and the other client user; actor excluded
        assert {r.user_id for r in rows} == {admin.id, manager.id, cu2.id}


class TestInvoiceHooks:
    @pytest.mark.anyio
    async def test_issue_notifies_staff_and_client_project_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        svc = await _create_service(db_session, tenant.id)
        ps = await _attach_service(db_session, project.id, svc)
        headers = await _admin_auth_header(admin)

        inv_id = await _create_invoice_api(client, headers, project.id, ps.id)
        await _issue_api(client, headers, inv_id)

        rows = await _notification_rows(db_session, tenant.id, NotificationEventType.INVOICE_ISSUED)
        assert {r.user_id for r in rows} == {admin.id, manager.id, cu.id}
        assert all(r.entity_type == "invoice" for r in rows)

    @pytest.mark.anyio
    async def test_issue_general_invoice_no_client_rows(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "line_items": [
                    {"description": "Custom work", "unit_price": "10.00", "quantity": 1}
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        inv_id = resp.json()["id"]
        await _issue_api(client, headers, inv_id)

        rows = await _notification_rows(db_session, tenant.id, NotificationEventType.INVOICE_ISSUED)
        assert {r.user_id for r in rows} == {admin.id, manager.id}
        assert all(r.user_type == "admin_user" for r in rows)
        assert cu.id not in {r.user_id for r in rows}

    @pytest.mark.anyio
    async def test_payment_notifies_staff_and_client_refund_staff_only(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        svc = await _create_service(db_session, tenant.id)
        ps = await _attach_service(db_session, project.id, svc)
        headers = await _admin_auth_header(admin)

        inv_id = await _create_invoice_api(client, headers, project.id, ps.id)
        await _issue_api(client, headers, inv_id)
        total = f"{svc.default_price:.2f}"

        pay = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": total, "method": "bank_transfer"},
            headers=headers,
        )
        assert pay.status_code == 201

        rows = await _notification_rows(
            db_session, tenant.id, NotificationEventType.PAYMENT_RECEIVED
        )
        assert {r.user_id for r in rows} == {admin.id, manager.id, cu.id}

        refund = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/refund",
            json={"amount": "100.00", "method": "other"},
            headers=headers,
        )
        assert refund.status_code == 201

        rows = await _notification_rows(
            db_session, tenant.id, NotificationEventType.REFUND_RECORDED
        )
        assert {r.user_id for r in rows} == {admin.id, manager.id}
        assert all(r.user_type == "admin_user" for r in rows)

    @pytest.mark.anyio
    async def test_advance_applied_notifies_staff(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        cli = await _create_client(db_session, tenant.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        svc = await _create_service(db_session, tenant.id)
        ps = await _attach_service(db_session, project.id, svc)
        headers = await _admin_auth_header(admin)

        # Overpay the first invoice to create an advance balance.
        inv1 = await _create_invoice_api(client, headers, project.id, ps.id)
        await _issue_api(client, headers, inv1)
        over = await client.post(
            f"/api/v1/tenant/invoices/{inv1}/transactions",
            json={"amount": "600.00", "method": "bank_transfer"},
            headers=headers,
        )
        assert over.status_code == 201

        inv2 = await _create_invoice_api(client, headers, project.id, ps.id)
        await _issue_api(client, headers, inv2)
        applied = await client.post(
            f"/api/v1/tenant/invoices/{inv2}/apply-advance", json={}, headers=headers
        )
        assert applied.status_code == 200

        rows = await _notification_rows(
            db_session, tenant.id, NotificationEventType.ADVANCE_APPLIED
        )
        assert {r.user_id for r in rows} == {admin.id, manager.id}
        assert all(r.user_type == "admin_user" for r in rows)
        assert all(r.entity_id == str(inv2) for r in rows)


class TestMilestoneHooks:
    @pytest.mark.anyio
    async def test_completed_milestone_notifies_staff_and_client_pending_does_not(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        svc = await _create_service(db_session, tenant.id)
        milestone = await _create_milestone(db_session, project, svc)
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            f"/api/v1/tenant/projects/{project.id}/milestones/{milestone.id}",
            json={"status": MilestoneStatus.COMPLETED.value},
            headers=headers,
        )
        assert resp.status_code == 200

        rows = await _notification_rows(
            db_session, tenant.id, NotificationEventType.MILESTONE_COMPLETED
        )
        assert {r.user_id for r in rows} == {admin.id, manager.id, cu.id}
        assert all(r.entity_id == str(milestone.id) for r in rows)

        # A second milestone left pending (only moved in_progress -> pending)
        # must NOT emit any rows.
        pending = ProjectMilestone(
            project_id=project.id,
            project_service_id=milestone.project_service_id,
            service_id=svc.id,
            name="Milestone Pending",
            sequence_order=2,
        )
        db_session.add(pending)
        await db_session.commit()
        await db_session.refresh(pending)
        await client.patch(
            f"/api/v1/tenant/projects/{project.id}/milestones/{pending.id}",
            json={"status": MilestoneStatus.IN_PROGRESS.value},
            headers=headers,
        )
        await client.patch(
            f"/api/v1/tenant/projects/{project.id}/milestones/{pending.id}",
            json={"status": MilestoneStatus.PENDING.value},
            headers=headers,
        )
        rows = await _notification_rows(
            db_session, tenant.id, NotificationEventType.MILESTONE_COMPLETED
        )
        assert {r.user_id for r in rows} == {admin.id, manager.id, cu.id}
        assert all(r.entity_id == str(milestone.id) for r in rows)


class TestProjectHook:
    @pytest.mark.anyio
    async def test_project_created_notifies_staff(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        await _create_admin_with_role(db_session, tenant.id, "employee", tag="e")
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/projects/",
            json={"name": f"New Proj {uuid.uuid4().hex[:6]}", "client_id": str(cli.id)},
            headers=headers,
        )
        assert resp.status_code == 201

        rows = await _notification_rows(
            db_session, tenant.id, NotificationEventType.PROJECT_CREATED
        )
        assert {r.user_id for r in rows} == {admin.id, manager.id}
        assert all(r.user_type == "admin_user" for r in rows)


class TestHookPrefAndFailure:
    @pytest.mark.anyio
    async def test_inapp_pref_disabled_skips_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        manager = await _create_admin_with_role(db_session, tenant.id, "manager", tag="m")
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, tenant.id, cli.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        svc = await _create_service(db_session, tenant.id)
        ps = await _attach_service(db_session, project.id, svc)
        headers = await _admin_auth_header(admin)

        await update_preferences(
            db_session,
            user_id=manager.id,
            user_type="admin_user",
            tenant_id=tenant.id,
            channel=NotificationChannel.INAPP,
            entries=[(NotificationEventType.INVOICE_ISSUED, False)],
        )

        inv_id = await _create_invoice_api(client, headers, project.id, ps.id)
        await _issue_api(client, headers, inv_id)

        rows = await _notification_rows(db_session, tenant.id, NotificationEventType.INVOICE_ISSUED)
        assert {r.user_id for r in rows} == {admin.id, cu.id}
        assert manager.id not in {r.user_id for r in rows}

    @pytest.mark.anyio
    async def test_emitter_failure_does_not_break_issue(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin_with_role(db_session, tenant.id, "admin", tag="a")
        cli = await _create_client(db_session, tenant.id)
        project = await _create_project(db_session, tenant.id, cli.id)
        svc = await _create_service(db_session, tenant.id)
        ps = await _attach_service(db_session, project.id, svc)
        headers = await _admin_auth_header(admin)

        inv_id = await _create_invoice_api(client, headers, project.id, ps.id)

        async def _boom(session, *, invoice_id):
            raise RuntimeError("notification dispatch exploded")

        monkeypatch.setattr(invoice_service, "notify_invoice_issued", _boom)
        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "issued"
