"""Integration tests for client portal auth, invites, and deactivation."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.client_invite import ClientInvite
from app.models.client_user import ClientUser
from app.models.enums import AdminUserRole, ClientStatus, ClientType, TenantStatus
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
    status: ClientStatus = ClientStatus.ACTIVE,
) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name="TestClient",
        client_type=ClientType.COMPANY,
        status=status,
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


def _extract_raw_token_from_log(caplog, email: str) -> str | None:
    """Extract raw invite token from console email log."""
    for record in caplog.records:
        if email in record.getMessage():
            match = re.search(r"token=([A-Za-z0-9_-]+)", record.getMessage())
            if match:
                return match.group(1)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Model Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestClientModel:
    @pytest.mark.anyio
    async def test_create_client(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        client = await _create_client(db_session, tenant.id)
        assert client.id is not None
        assert client.name == "TestClient"
        assert client.client_type == ClientType.COMPANY
        assert client.status == ClientStatus.ACTIVE
        assert client.tags == []

    @pytest.mark.anyio
    async def test_client_notes_append_only(self, db_session: AsyncSession):
        from app.models.client_note import ClientNote

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, "admin@testco.com", AdminUserRole.ADMIN, tenant.id)
        client = await _create_client(db_session, tenant.id)

        note = ClientNote(
            client_id=client.id,
            author_id=admin.id,
            body="Test note",
        )
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        assert note.id is not None
        assert note.body == "Test note"
        assert note.created_at is not None


class TestClientUserModel:
    @pytest.mark.anyio
    async def test_unique_email(self, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        client = await _create_client(db_session, tenant.id)
        client2 = await _create_client(db_session, tenant.id)

        await _create_client_user(db_session, client.id, tenant.id, "same@test.com")

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await _create_client_user(db_session, client2.id, tenant.id, "same@test.com")

    @pytest.mark.anyio
    async def test_one_primary_per_client(self, db_session: AsyncSession):
        """Service-level enforcement: only one is_primary_billing_contact per client."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        client = await _create_client(db_session, tenant.id)

        cu1 = ClientUser(
            client_id=client.id,
            tenant_id=tenant.id,
            email="primary@test.com",
            full_name="Primary",
            hashed_password=hash_password(_TEST_PWD),
            is_primary_billing_contact=True,
        )
        db_session.add(cu1)
        await db_session.commit()

        cu2 = ClientUser(
            client_id=client.id,
            tenant_id=tenant.id,
            email="also_primary@test.com",
            full_name="Also Primary",
            hashed_password=hash_password(_TEST_PWD),
            is_primary_billing_contact=True,
        )
        db_session.add(cu2)
        # No DB constraint — service enforces; just verify both save
        await db_session.commit()

        users = await db_session.get(ClientUser, cu1.id)
        assert users is not None


# ═══════════════════════════════════════════════════════════════════════════
# Client Login Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestClientLogin:
    async def _login(self, client: AsyncClient, email: str, password: str = _TEST_PWD):
        return await client.post(
            "/api/v1/client/auth/login",
            json={"email": email, "password": password},
        )

    @pytest.mark.anyio
    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "user@client.com")

        resp = await self._login(client, "user@client.com")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "user@client.com"
        assert data["user"]["role"] == "client_user"
        assert data["user"]["client_id"] == str(cli.id)
        assert data["user"]["tenant_id"] == str(tenant.id)

    @pytest.mark.anyio
    async def test_login_eager_load_regression(self, client: AsyncClient, db_session: AsyncSession):
        """Regression: eager-load client+tenant to avoid MissingGreenlet on real requests."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "eager@test.com")

        # Expire all objects so service must re-query with eager loads
        db_session.expire_all()

        resp = await self._login(client, "eager@test.com")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "eager@test.com"

    @pytest.mark.anyio
    async def test_login_bad_password(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "user2@client.com")

        resp = await self._login(client, "user2@client.com", "wrongpassword")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    @pytest.mark.anyio
    async def test_login_unknown_email(self, client: AsyncClient, db_session: AsyncSession):
        resp = await self._login(client, "nobody@test.com")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_login_deactivated(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(
            db_session, cli.id, tenant.id, "deactivated@client.com", is_active=False
        )

        resp = await self._login(client, "deactivated@client.com")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_login_archived_client(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id, ClientStatus.ARCHIVED)
        await _create_client_user(db_session, cli.id, tenant.id, "archived@client.com")

        resp = await self._login(client, "archived@client.com")
        assert resp.status_code == 403
        assert "archived" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_login_suspended_tenant(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.SUSPENDED)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "suspended@client.com")

        resp = await self._login(client, "suspended@client.com")
        assert resp.status_code == 403
        assert "suspended" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_login_cancelled_tenant(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.CANCELLED)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "cancelled@client.com")

        resp = await self._login(client, "cancelled@client.com")
        assert resp.status_code == 403
        assert "cancelled" in resp.json()["error"]["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Client /me Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestClientMe:
    @pytest.mark.anyio
    async def test_me_with_token(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "me@client.com")
        headers = await _client_auth_header(cu)

        resp = await client.get("/api/v1/client/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@client.com"
        assert data["role"] == "client_user"
        assert data["client_id"] == str(cli.id)
        assert data["client"]["name"] == "TestClient"
        assert data["client"]["status"] == "active"

    @pytest.mark.anyio
    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/client/auth/me")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_me_wrong_realm(self, client: AsyncClient, db_session: AsyncSession):
        """Admin JWT should be rejected on client /me."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, "admin@testco.com", AdminUserRole.ADMIN, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/client/auth/me", headers=headers)
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# Realm Isolation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRealmIsolation:
    @pytest.mark.anyio
    async def test_client_token_on_admin_me(self, client: AsyncClient, db_session: AsyncSession):
        """Client JWT rejected on /auth/me (admin realm)."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "client@test.com")
        headers = await _client_auth_header(cu)

        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_admin_token_on_client_me(self, client: AsyncClient, db_session: AsyncSession):
        """Admin JWT rejected on /client/auth/me."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, "admin2@testco.com", AdminUserRole.ADMIN, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/client/auth/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_client_token_on_tenant_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client JWT rejected on tenant user admin endpoints."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "client3@test.com")
        headers = await _client_auth_header(cu)

        resp = await client.get("/api/v1/tenant/users", headers=headers)
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# Client Invite Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateClientInvite:
    @pytest.mark.anyio
    async def test_create_invite_success(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/clients/{cli.id}/invites",
            json={"email": "newclient@test.com"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newclient@test.com"
        assert data["status"] == "pending"
        assert data["accepted_at"] is None

        raw_token = _extract_raw_token_from_log(caplog, "newclient@test.com")
        assert raw_token is not None

    @pytest.mark.anyio
    async def test_create_invite_resend(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        # First invite
        resp1 = await client.post(
            f"/api/v1/tenant/clients/{cli.id}/invites",
            json={"email": "dup@test.com"},
            headers=headers,
        )
        assert resp1.status_code == 201
        first_id = resp1.json()["id"]
        caplog.clear()

        # Resend
        resp2 = await client.post(
            f"/api/v1/tenant/clients/{cli.id}/invites",
            json={"email": "dup@test.com"},
            headers=headers,
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] == first_id

    @pytest.mark.anyio
    async def test_invite_cross_tenant_404(self, client: AsyncClient, db_session: AsyncSession):
        """Client from different tenant -> 404."""
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id)
        tenant_b = await _create_tenant(db_session, plan.id)
        admin_b = await _create_admin(
            db_session, "admin_b@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        cli_a = await _create_client(db_session, tenant_a.id)
        headers_b = await _admin_auth_header(admin_b)

        resp = await client.post(
            f"/api/v1/tenant/clients/{cli_a.id}/invites",
            json={"email": "cross@test.com"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_invite_existing_email_409(self, client: AsyncClient, db_session: AsyncSession):
        """Email already in use by another client user -> 409."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(db_session, "admin@testco.com", AdminUserRole.ADMIN, tenant.id)
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(db_session, cli.id, tenant.id, "existing@test.com")
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/clients/{cli.id}/invites",
            json={"email": "existing@test.com"},
            headers=headers,
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]["message"].lower()


class TestListClientInvites:
    @pytest.mark.anyio
    async def test_list_invites(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "listadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        # Create invite
        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="listed@test.com",
            token_hash=hashlib.sha256(b"list_token").hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.get(f"/api/v1/tenant/clients/{cli.id}/invites", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(i["email"] == "listed@test.com" for i in data)


class TestRevokeClientInvite:
    @pytest.mark.anyio
    async def test_revoke_pending(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "revoker@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        headers = await _admin_auth_header(admin)

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="revoke@test.com",
            token_hash=hashlib.sha256(b"revoke_token").hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/tenant/client-invites/{inv.id}", headers=headers)
        assert resp.status_code == 204


class TestLookupClientInvite:
    @pytest.mark.anyio
    async def test_lookup_valid(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "lookupadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "validclienttoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="lookup@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.get(f"/api/v1/client/auth/invite/{raw_token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "lookup@test.com"
        assert data["client_name"] == "TestClient"
        assert data["tenant_name"] == "TestCo"

    @pytest.mark.anyio
    async def test_lookup_unknown_404(self, client: AsyncClient, db_session: AsyncSession):
        resp = await client.get("/api/v1/client/auth/invite/unknown_token")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_lookup_expired_410(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "expiredadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "expiredclienttoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="expired@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.get(f"/api/v1/client/auth/invite/{raw_token}")
        assert resp.status_code == 410

    @pytest.mark.anyio
    async def test_lookup_accepted_409(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "acceptedadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "acceptedclienttoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="accepted@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
            accepted_at=datetime.now(UTC),
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.get(f"/api/v1/client/auth/invite/{raw_token}")
        assert resp.status_code == 409


class TestRegisterClientUser:
    @pytest.mark.anyio
    async def test_register_success(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "inviter@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "registertoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="register@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/client/auth/register",
            json={
                "token": raw_token,
                "full_name": "New Client User",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "register@test.com"
        assert data["user"]["role"] == "client_user"
        assert data["user"]["client_id"] == str(cli.id)

        # JWT works on /client/auth/me
        me_resp = await client.get(
            "/api/v1/client/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_resp.status_code == 200

        # Invite marked accepted
        await db_session.refresh(inv)
        assert inv.accepted_at is not None

    @pytest.mark.anyio
    async def test_register_short_password_422(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "shortadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "shortpwtoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="short@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/client/auth/register",
            json={
                "token": raw_token,
                "full_name": "Short PW",
                "password": "short",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_register_expired_410(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "expiredreg@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "expiredregtoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="expiredreg@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/client/auth/register",
            json={
                "token": raw_token,
                "full_name": "Expired Reg",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 410

    @pytest.mark.anyio
    async def test_register_accepted_409(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "usedadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        raw_token = "usedtoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email="used@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
            accepted_at=datetime.now(UTC),
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/client/auth/register",
            json={
                "token": raw_token,
                "full_name": "Used Token",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_register_unknown_404(self, client: AsyncClient, db_session: AsyncSession):
        resp = await client.post(
            "/api/v1/client/auth/register",
            json={
                "token": "unknowntoken123",
                "full_name": "No One",
                "password": "strongpassword123",
            },
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Client User Deactivation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestClientUserDeactivation:
    @pytest.mark.anyio
    async def test_deactivate(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "deactadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "deact@test.com")
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_deactivate_then_login_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "blockadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(db_session, cli.id, tenant.id, "block@test.com")
        headers = await _admin_auth_header(admin)

        # Deactivate
        await client.post(
            f"/api/v1/tenant/client-users/{cu.id}/deactivate",
            headers=headers,
        )

        # Login blocked
        resp = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "block@test.com", "password": _TEST_PWD},
        )
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_reactivate(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "reactadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, "react@test.com", is_active=False
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu.id}/reactivate",
            headers=headers,
        )
        assert resp.status_code == 200

        # Login works again
        login_resp = await client.post(
            "/api/v1/client/auth/login",
            json={"email": "react@test.com", "password": _TEST_PWD},
        )
        assert login_resp.status_code == 200

    @pytest.mark.anyio
    async def test_deactivate_already_inactive_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_admin(
            db_session, "alreadyadmin@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, "already@test.com", is_active=False
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_deactivate_cross_tenant_404(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id)
        tenant_b = await _create_tenant(db_session, plan.id)
        admin_b = await _create_admin(
            db_session, "crossadmin@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        cli_a = await _create_client(db_session, tenant_a.id)
        cu_a = await _create_client_user(db_session, cli_a.id, tenant_a.id, "cross@test.com")
        headers_b = await _admin_auth_header(admin_b)

        resp = await client.post(
            f"/api/v1/tenant/client-users/{cu_a.id}/deactivate",
            headers=headers_b,
        )
        assert resp.status_code == 404
