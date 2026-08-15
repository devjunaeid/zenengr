"""Seeder feature-flag default + system role permission steps.

Both steps are additive and idempotent: re-running the seed functions
inserts nothing new.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.plan_feature_default import PlanFeatureDefault
from app.models.role import Role, RolePermission
from app.services.feature_flags import FEATURE_KEYS
from app.services.roles import SYSTEM_ROLE_PERMISSIONS
from scripts.seed_dev import seed_plan_flag_defaults, seed_system_role_permissions


async def _seed_system_roles(session: AsyncSession) -> None:
    """Insert system role rows only (no permission rows)."""
    for name in SYSTEM_ROLE_PERMISSIONS:
        session.add(
            Role(
                tenant_id=None,
                name=name,
                description=f"System role: {name}",
                is_system=True,
            )
        )
    await session.flush()


@pytest.mark.anyio
async def test_plan_flag_defaults_seeded_and_idempotent(db_session: AsyncSession):
    """All FEATURE_KEYS get PlanFeatureDefault rows; re-run inserts nothing."""
    plan = Plan(
        name=f"SeedPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    db_session.add(plan)
    await db_session.commit()

    created = await seed_plan_flag_defaults(db_session, [plan])
    assert created == len(FEATURE_KEYS)

    rows = (
        (
            await db_session.execute(
                select(PlanFeatureDefault).where(PlanFeatureDefault.plan_id == plan.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == len(FEATURE_KEYS)
    by_key = {r.key: r.enabled for r in rows}
    for entry in FEATURE_KEYS:
        assert by_key[entry["key"]] is entry["default"]

    # Re-run -> no new rows
    again = await seed_plan_flag_defaults(db_session, [plan])
    assert again == 0
    count = (
        await db_session.execute(
            select(func.count())
            .select_from(PlanFeatureDefault)
            .where(PlanFeatureDefault.plan_id == plan.id)
        )
    ).scalar_one()
    assert count == len(FEATURE_KEYS)


@pytest.mark.anyio
async def test_system_role_permissions_seeded_and_idempotent(db_session: AsyncSession):
    """System roles get the full matrix; re-run inserts nothing."""
    await _seed_system_roles(db_session)

    created = await seed_system_role_permissions(db_session)
    assert created == sum(len(perms) for perms in SYSTEM_ROLE_PERMISSIONS.values())

    roles = (await db_session.execute(select(Role).where(Role.tenant_id.is_(None)))).scalars().all()
    for role in roles:
        rows = (
            (
                await db_session.execute(
                    select(RolePermission).where(RolePermission.role_id == role.id)
                )
            )
            .scalars()
            .all()
        )
        got = {(p.action, p.resource) for p in rows}
        assert got == set(SYSTEM_ROLE_PERMISSIONS[role.name])
        assert all(p.granted for p in rows)

    # Re-run -> no new rows
    again = await seed_system_role_permissions(db_session)
    assert again == 0
    total = (
        await db_session.execute(select(func.count()).select_from(RolePermission))
    ).scalar_one()
    assert total == sum(len(perms) for perms in SYSTEM_ROLE_PERMISSIONS.values())
