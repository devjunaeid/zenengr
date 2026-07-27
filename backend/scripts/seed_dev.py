"""Idempotent development seed.

Creates:
- Plan "Starter" with sensible limits
- Tenant "Demo Agency" (slug: demo-agency, status: active)
- Super admin user
- Tenant admin user for demo@demo-agency.dev

Usage: uv run python -m scripts.seed_dev
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.admin_user import AdminUser
from app.models.enums import AdminUserRole, TenantStatus
from app.models.plan import Plan
from app.models.tenant import Tenant

SEED_SUPERADMIN_EMAIL = os.getenv("SEED_SUPERADMIN_EMAIL", "admin@zenengr.dev")
SEED_SUPERADMIN_PASSWORD = os.getenv("SEED_SUPERADMIN_PASSWORD", "changeme123!")
SEED_DEMO_EMAIL = os.getenv("SEED_DEMO_EMAIL", "demo@demo-agency.dev")
SEED_DEMO_PASSWORD = os.getenv("SEED_DEMO_PASSWORD", "changeme123!")


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
            await session.flush()
            print("Created demo admin: demo@demo-agency.dev")
        else:
            print("Demo admin already exists — skipping")

        await session.commit()

    await engine.dispose()


def main() -> None:
    asyncio.run(_seed())
    print("\nSeed complete. Credentials:")
    print(f"  Super admin: {SEED_SUPERADMIN_EMAIL} / {SEED_SUPERADMIN_PASSWORD}")
    print(f"  Tenant admin: {SEED_DEMO_EMAIL} / {SEED_DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
