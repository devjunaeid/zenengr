"""Idempotent development seed.

Creates:
- Plan "Starter" with sensible limits
- Tenant "Demo Agency" (slug: demo-agency, status: active)
- Super admin user
- Tenant admin user for demo@demo-agency.dev
- Client "Demo Client" with portal user client@demo-agency.dev
- One demo project for that client

Usage: uv run python -m scripts.seed_dev
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.client_user import ClientUser
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    ProjectStatus,
    TenantStatus,
)
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant
from app.services.roles import attach_default_role

SEED_SUPERADMIN_EMAIL = os.getenv("SEED_SUPERADMIN_EMAIL", "admin@zenengr.dev")
SEED_SUPERADMIN_PASSWORD = os.getenv("SEED_SUPERADMIN_PASSWORD", "changeme123!")
SEED_DEMO_EMAIL = os.getenv("SEED_DEMO_EMAIL", "demo@demo-agency.dev")
SEED_DEMO_PASSWORD = os.getenv("SEED_DEMO_PASSWORD", "changeme123!")
SEED_CLIENT_EMAIL = os.getenv("SEED_CLIENT_EMAIL", "client@demo-agency.dev")
SEED_CLIENT_PASSWORD = os.getenv("SEED_CLIENT_PASSWORD", "changeme123!")


async def _seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # ── Plan ─────────────────────────────────────────────────────────
        plan_result = await session.execute(select(Plan).where(Plan.name == "Starter"))
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            plan = Plan(
                name="Starter",
                description="Entry-level plan for small agencies",
                max_admin_users=5,
                max_clients=50,
                max_active_projects=20,
                max_storage_mb=512,
            )
            session.add(plan)
            await session.flush()
            print("Created plan: Starter")
        else:
            print("Plan 'Starter' already exists — skipping")
            await session.refresh(plan)

        # ── Tenant ───────────────────────────────────────────────────────
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == "demo-agency"))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                business_name="Demo Agency",
                slug="demo-agency",
                status=TenantStatus.ACTIVE,
                plan_id=plan.id,
                contact_info={"phone": "+1-555-0100"},
                branding={"color": "#4F46E5"},
            )
            session.add(tenant)
            await session.flush()
            print("Created tenant: Demo Agency (demo-agency)")
        else:
            print("Tenant 'demo-agency' already exists — skipping")
            await session.refresh(tenant)

        # ── Super admin ──────────────────────────────────────────────────
        super_result = await session.execute(
            select(AdminUser).where(AdminUser.email == SEED_SUPERADMIN_EMAIL)
        )
        super_admin = super_result.scalar_one_or_none()
        if super_admin is None:
            super_admin = AdminUser(
                tenant_id=None,
                email=SEED_SUPERADMIN_EMAIL,
                full_name="Super Admin",
                hashed_password=hash_password(SEED_SUPERADMIN_PASSWORD),
                role=AdminUserRole.SUPER_ADMIN,
            )
            session.add(super_admin)
            await attach_default_role(session, super_admin)
            await session.flush()
            print("Created super admin")
        else:
            print("Super admin already exists — skipping")

        # ── Tenant admin ─────────────────────────────────────────────────
        demo_result = await session.execute(
            select(AdminUser).where(AdminUser.email == SEED_DEMO_EMAIL)
        )
        demo_user = demo_result.scalar_one_or_none()
        if demo_user is None:
            demo_user = AdminUser(
                tenant_id=tenant.id,
                email=SEED_DEMO_EMAIL,
                full_name="Demo Admin",
                hashed_password=hash_password(SEED_DEMO_PASSWORD),
                role=AdminUserRole.ADMIN,
            )
            session.add(demo_user)
            await attach_default_role(session, demo_user)
            await session.flush()
            print("Created demo admin: demo@demo-agency.dev")
        else:
            print("Demo admin already exists — skipping")

        # ── Client portal user ───────────────────────────────────────────
        client_result = await session.execute(
            select(Client).where(Client.email == SEED_CLIENT_EMAIL)
        )
        client = client_result.scalar_one_or_none()
        if client is None:
            client = Client(
                tenant_id=tenant.id,
                name="Demo Client",
                client_type=ClientType.COMPANY,
                email=SEED_CLIENT_EMAIL,
                status=ClientStatus.ACTIVE,
            )
            session.add(client)
            await session.flush()
            print("Created client: Demo Client (client@demo-agency.dev)")
        else:
            print("Client 'Demo Client' already exists — skipping")

        client_user_result = await session.execute(
            select(ClientUser).where(ClientUser.email == SEED_CLIENT_EMAIL)
        )
        client_user = client_user_result.scalar_one_or_none()
        if client_user is None:
            client_user = ClientUser(
                client_id=client.id,
                tenant_id=tenant.id,
                email=SEED_CLIENT_EMAIL,
                full_name="Demo Client User",
                hashed_password=hash_password(SEED_CLIENT_PASSWORD),
                is_active=True,
                is_primary_billing_contact=True,
            )
            session.add(client_user)
            await session.flush()
            print("Created client user: client@demo-agency.dev")
        else:
            print("Client user already exists — skipping")

        # ── Demo project for the client ──────────────────────────────────
        project_result = await session.execute(
            select(Project).where(
                Project.tenant_id == tenant.id,
                Project.client_id == client.id,
                Project.name == "Demo Project",
            )
        )
        project = project_result.scalar_one_or_none()
        if project is None:
            project = Project(
                tenant_id=tenant.id,
                name="Demo Project",
                client_id=client.id,
                status=ProjectStatus.ACTIVE,
                start_date=date.today(),
            )
            session.add(project)
            await session.flush()
            print("Created project: Demo Project")
        else:
            print("Project 'Demo Project' already exists — skipping")

        await session.commit()

    await engine.dispose()


def main() -> None:
    asyncio.run(_seed())
    print("\nSeed complete. Credentials:")
    print(f"  Super admin: {SEED_SUPERADMIN_EMAIL} / {SEED_SUPERADMIN_PASSWORD}")
    print(f"  Tenant admin: {SEED_DEMO_EMAIL} / {SEED_DEMO_PASSWORD}")
    print(f"  Client portal: {SEED_CLIENT_EMAIL} / {SEED_CLIENT_PASSWORD}")


if __name__ == "__main__":
    main()
