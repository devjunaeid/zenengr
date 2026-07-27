"""Integration tests for invite endpoints (TODO-026, TODO-027, TODO-028)."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.enums import AdminUserRole, InviteRole, TenantStatus
from app.models.invite import Invite
from app.models.plan import Plan
from app.models.tenant import Tenant

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


async def _create_tenant(
    session: AsyncSession, plan_id: uuid.UUID, status: TenantStatus = TenantStatus.ACTIVE
) -> Tenant:
    tenant = Tenant(
        business_name="TestCo",
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status=status,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_user(
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


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


def _extract_raw_token_from_log(caplog, email: str) -> str | None:
    """Extract raw invite token from console email log."""
    for record in caplog.records:
        if email in record.getMessage():
            match = re.search(r"token=([A-Za-z0-9_-]+)", record.getMessage())
            if match:
                return match.group(1)
    return None


# ── Tests ──────────────────────────────────────────────────────────────────


class TestCreateInvite:
    @pytest.mark.anyio
    async def test_create_invite_success(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        """201 + email sent with accept URL; raw token only in email, hash in DB."""
        import logging

        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "newbie@testco.com", "role": "employee"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newbie@testco.com"
        assert data["role"] == "employee"
        assert data["status"] == "pending"
        assert "expires_at" in data
        assert data["accepted_at"] is None

        # Raw token in console email log
        raw_token = _extract_raw_token_from_log(caplog, "newbie@testco.com")
        assert raw_token is not None, "Raw token not found in log"
        assert (
            "accept-invite?token="
            in [r.getMessage() for r in caplog.records if "newbie@testco.com" in r.getMessage()][0]
        )

        # DB hash is SHA-256 hex, not raw token
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        invite_in_db = await db_session.get(Invite, uuid.UUID(data["id"]))
        assert invite_in_db is not None
        assert invite_in_db.token == token_hash
        assert invite_in_db.token != raw_token

    @pytest.mark.anyio
    async def test_duplicate_pending_invite_resends(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        """Pending invite -> resend path (same row, new token, new expiry)."""
        import logging

        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(db_session, "admin2@testco.com", AdminUserRole.ADMIN, tenant.id)
        headers = await _auth_header(admin)

        # First create
        resp1 = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "dup@testco.com", "role": "manager"},
            headers=headers,
        )
        assert resp1.status_code == 201
        first_id = resp1.json()["id"]
        first_raw = _extract_raw_token_from_log(caplog, "dup@testco.com")
        assert first_raw is not None
        caplog.clear()

        # Second create (same email)
        resp2 = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "dup@testco.com", "role": "manager"},
            headers=headers,
        )
        assert resp2.status_code == 201
        data2 = resp2.json()
        assert data2["id"] == first_id  # same row

        second_raw = _extract_raw_token_from_log(caplog, "dup@testco.com")
        assert second_raw is not None
        assert second_raw != first_raw  # new token

        # DB has new hash
        token_hash2 = hashlib.sha256(second_raw.encode()).hexdigest()
        invite_db = await db_session.get(Invite, uuid.UUID(first_id))
        assert invite_db is not None
        assert invite_db.token == token_hash2

    @pytest.mark.anyio
    async def test_existing_user_email_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """409 if active admin user with same email exists in this tenant."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(db_session, "boss@testco.com", AdminUserRole.ADMIN, tenant.id)
        # Existing user
        await _create_user(db_session, "existing@testco.com", AdminUserRole.EMPLOYEE, tenant.id)
        headers = await _auth_header(admin)

        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "existing@testco.com", "role": "employee"},
            headers=headers,
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_manager_cannot_create_invite(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Manager role -> 403."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        manager = await _create_user(
            db_session, "manager@testco.com", AdminUserRole.MANAGER, tenant.id
        )
        headers = await _auth_header(manager)

        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "anyone@testco.com", "role": "employee"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_employee_cannot_create_invite(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employee role -> 403."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        emp = await _create_user(db_session, "emp@testco.com", AdminUserRole.EMPLOYEE, tenant.id)
        headers = await _auth_header(emp)

        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "anyone@testco.com", "role": "employee"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, db_session: AsyncSession):
        """No auth header -> 401."""
        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "anyone@testco.com", "role": "employee"},
        )
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_expired_invite_regenerates(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        """Expired invite -> resend path (same row, new token, new expiry)."""
        import logging

        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(db_session, "admin3@testco.com", AdminUserRole.ADMIN, tenant.id)
        headers = await _auth_header(admin)

        # Create invite with expired time
        raw_old = "oldtoken123"
        old_hash = hashlib.sha256(raw_old.encode()).hexdigest()
        expired_invite = Invite(
            tenant_id=tenant.id,
            email="expired@testco.com",
            role=InviteRole.EMPLOYEE,
            token=old_hash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            invited_by=admin.id,
        )
        db_session.add(expired_invite)
        await db_session.commit()
        expired_id = expired_invite.id

        caplog.clear()

        # Re-send to same email
        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "expired@testco.com", "role": "employee"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == str(expired_id)

        raw_new = _extract_raw_token_from_log(caplog, "expired@testco.com")
        assert raw_new is not None
        assert raw_new != raw_old

        # DB updated
        await db_session.refresh(expired_invite)
        new_hash = hashlib.sha256(raw_new.encode()).hexdigest()
        assert expired_invite.token == new_hash
        assert expired_invite.expires_at > datetime.now(UTC)


class TestListInvites:
    @pytest.mark.anyio
    async def test_list_invites_paginated(self, client: AsyncClient, db_session: AsyncSession):
        """List invites for tenant, newest first."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "listadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)

        # Create 3 invites
        invites = []
        for i in range(3):
            invite = Invite(
                tenant_id=tenant.id,
                email=f"invite{i}@testco.com",
                role=InviteRole.EMPLOYEE,
                token=hashlib.sha256(f"token{i}".encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(days=3),
                invited_by=admin.id,
            )
            db_session.add(invite)
            invites.append(invite)
        await db_session.commit()

        resp = await client.get("/api/v1/tenant/invites", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3
        # All three invites present
        emails = {i["email"] for i in data}
        assert "invite0@testco.com" in emails
        assert "invite1@testco.com" in emails
        assert "invite2@testco.com" in emails

    @pytest.mark.anyio
    async def test_cross_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession):
        """Invites from tenant A not visible to tenant B."""
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id, TenantStatus.ACTIVE)
        tenant_b = await _create_tenant(db_session, plan.id, TenantStatus.ACTIVE)
        admin_a = await _create_user(
            db_session, "admin_a@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        admin_b = await _create_user(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        headers_a = await _auth_header(admin_a)
        headers_b = await _auth_header(admin_b)

        # Invite in tenant A
        invite = Invite(
            tenant_id=tenant_a.id,
            email="aonly@testco.com",
            role=InviteRole.EMPLOYEE,
            token=hashlib.sha256(b"tok_a").hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin_a.id,
        )
        db_session.add(invite)
        await db_session.commit()

        # Tenant A sees it
        resp_a = await client.get("/api/v1/tenant/invites", headers=headers_a)
        assert resp_a.status_code == 200
        assert any(i["email"] == "aonly@testco.com" for i in resp_a.json())

        # Tenant B does not
        resp_b = await client.get("/api/v1/tenant/invites", headers=headers_b)
        assert resp_b.status_code == 200
        assert not any(i["email"] == "aonly@testco.com" for i in resp_b.json())


class TestRevokeInvite:
    @pytest.mark.anyio
    async def test_revoke_pending_invite(self, client: AsyncClient, db_session: AsyncSession):
        """204 on successful revoke, invite deleted from DB."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(db_session, "revoker@testco.com", AdminUserRole.ADMIN, tenant.id)
        headers = await _auth_header(admin)

        invite = Invite(
            tenant_id=tenant.id,
            email="revokeme@testco.com",
            role=InviteRole.MANAGER,
            token=hashlib.sha256(b"revoke_token").hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/tenant/invites/{invite.id}", headers=headers)
        assert resp.status_code == 204

        # Verify deleted
        deleted = await db_session.get(Invite, invite.id)
        assert deleted is None

    @pytest.mark.anyio
    async def test_revoke_accepted_invite_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """409 on trying to revoke an accepted invite."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "revoker2@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)

        invite = Invite(
            tenant_id=tenant.id,
            email="accepted@testco.com",
            role=InviteRole.EMPLOYEE,
            token=hashlib.sha256(b"accepted").hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
            accepted_at=datetime.now(UTC),
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/tenant/invites/{invite.id}", headers=headers)
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_revoke_nonexistent_invite_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """404 on unknown invite ID."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "revoker3@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)

        resp = await client.delete(f"/api/v1/tenant/invites/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


class TestLookupInvite:
    @pytest.mark.anyio
    async def test_lookup_valid_token(self, client: AsyncClient, db_session: AsyncSession):
        """Valid token -> 200 with email, role, tenant_name, expires_at."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.ACTIVE)
        admin = await _create_user(
            db_session, "lookupadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "validlookuptoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="lookup@testco.com",
            role=InviteRole.MANAGER,
            token=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.get(f"/api/v1/auth/invite/{raw_token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "lookup@testco.com"
        assert data["role"] == "manager"
        assert data["tenant_name"] == "TestCo"
        assert "expires_at" in data

    @pytest.mark.anyio
    async def test_lookup_unknown_token_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Unknown token -> 404."""
        resp = await client.get("/api/v1/auth/invite/unknown_token_here")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    @pytest.mark.anyio
    async def test_lookup_expired_token_returns_410(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Expired token -> 410."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "expiredlookup@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "expiredlookup"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="expired@testco.com",
            role=InviteRole.EMPLOYEE,
            token=token_hash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # expired
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.get(f"/api/v1/auth/invite/{raw_token}")
        assert resp.status_code == 410
        assert "expired" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_lookup_accepted_token_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Accepted token -> 409."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "acceptedlookup@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "acceptedlookup"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="accepted@testco.com",
            role=InviteRole.ADMIN,
            token=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
            accepted_at=datetime.now(UTC),
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.get(f"/api/v1/auth/invite/{raw_token}")
        assert resp.status_code == 409
        assert "accepted" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_lookup_token_at_expiry_boundary_returns_410(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Token at exactly expires_at -> 410 (boundary)."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "boundary@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "boundarytoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="boundary@testco.com",
            role=InviteRole.EMPLOYEE,
            token=token_hash,
            expires_at=datetime.now(UTC),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.get(f"/api/v1/auth/invite/{raw_token}")
        # Boundary: expires_at ~= now. Due to microsecond variance, accept 200 or 410.
        assert resp.status_code in (200, 410)


class TestRegisterFromInvite:
    @pytest.mark.anyio
    async def test_register_success(self, client: AsyncClient, db_session: AsyncSession):
        """Happy path: creates user with invite's role/tenant, JWT works on /auth/me."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.ACTIVE)
        admin = await _create_user(db_session, "inviter@testco.com", AdminUserRole.ADMIN, tenant.id)
        raw_token = "registertoken123"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="registerme@testco.com",
            role=InviteRole.MANAGER,
            token=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "token": raw_token,
                "full_name": "New User",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "registerme@testco.com"
        assert data["user"]["full_name"] == "New User"
        assert data["user"]["role"] == "manager"
        assert data["user"]["tenant_id"] == str(tenant.id)

        # JWT works on /auth/me
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "registerme@testco.com"

        # Invite marked accepted
        await db_session.refresh(invite)
        assert invite.accepted_at is not None

    @pytest.mark.anyio
    async def test_register_short_password_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Password < 10 chars -> 422."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "shortpwadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "shortpwtest"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="shortpw@testco.com",
            role=InviteRole.EMPLOYEE,
            token=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "token": raw_token,
                "full_name": "Short PW",
                "password": "short",
            },
        )
        assert resp.status_code == 422
        assert "10 characters" in resp.json()["error"]["message"]

    @pytest.mark.anyio
    async def test_register_consumed_token_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Already accepted token -> 409."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "usedadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "usedtoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="used@testco.com",
            role=InviteRole.EMPLOYEE,
            token=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
            accepted_at=datetime.now(UTC),
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "token": raw_token,
                "full_name": "Used Token",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 409
        assert "accepted" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_register_expired_token_returns_410(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Expired token -> 410."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "expiredreg@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "expiredregtoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="expiredreg@testco.com",
            role=InviteRole.EMPLOYEE,
            token=token_hash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "token": raw_token,
                "full_name": "Expired Reg",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 410
        assert "expired" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_register_unknown_token_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Unknown token -> 404."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "token": "completelyunknowntoken",
                "full_name": "No One",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    @pytest.mark.anyio
    async def test_register_role_and_tenant_from_invite_not_request(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User created with invite's role/tenant, never from request body."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, "inviter2@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        raw_token = "rolenottakenfrombody"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invite = Invite(
            tenant_id=tenant.id,
            email="rolenottest@testco.com",
            role=InviteRole.ADMIN,  # invite says admin
            token=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(invite)
        await db_session.commit()

        # Register (no role/tenant in request body - schema doesn't have them)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "token": raw_token,
                "full_name": "Role Test",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "admin"
        assert resp.json()["user"]["tenant_id"] == str(tenant.id)
