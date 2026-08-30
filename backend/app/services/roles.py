"""Role service — system role lookup, default attachment, seed data, CRUD.

FEAT-016 (TODO-161/162/163): roles are first-class rows. System (built-in)
roles mirror the permission matrix in app/services/permissions.py; tenant
admins can create custom roles (tenant_id set) with their own permission
rows.

SYSTEM_ROLE_PERMISSIONS is the single seed source used by the roles
migration (alembic/versions/e1f2a3b4c5d6_add_roles_permissions.py) and by
tests. super_admin carries no permission rows — platform access stays
code-gated (permissions.py platform_has_permission).

Part 2 (TODO-163) adds the tenant role-management operations: list/create/
update/delete/reset/assign, all audited and cache-aware.
"""

from __future__ import annotations

import os
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.security import hash_password
from app.models.admin_user import AdminUser
from app.models.enums import ActorType, AdminUserRole
from app.models.role import Role, RolePermission
from app.schemas.roles import RolePermissionInput
from app.services.audit import log as audit_log
from app.services.feature_flags import FEATURE_KEY_BY_RESOURCE
from app.services.permissions import (
    _TENANT_MATRIX,
    PERMISSION_CATALOG,
    SYSTEM_PROJECT_ROLE_PERMISSIONS,
    clear_permission_cache,
    has_permission,
)

# Role name -> granted (action, resource) tuples. Mirrors _TENANT_MATRIX.
SYSTEM_ROLE_PERMISSIONS: dict[str, frozenset[tuple[str, str]]] = {
    AdminUserRole.SUPER_ADMIN.value: frozenset(),
    **{role.value: frozenset(perms) for role, perms in _TENANT_MATRIX.items()},
}

_SYSTEM_ROLE_IDS: dict[str, uuid.UUID] = {
    AdminUserRole.SUPER_ADMIN.value: uuid.UUID("11111111-1111-4111-8111-111111111111"),
    AdminUserRole.ADMIN.value: uuid.UUID("22222222-2222-4222-8222-222222222222"),
    AdminUserRole.MANAGER.value: uuid.UUID("33333333-3333-4333-8333-333333333333"),
    AdminUserRole.EMPLOYEE.value: uuid.UUID("44444444-4444-4444-8444-444444444444"),
}

# Names that may never be used for tenant custom roles (collide with the
# built-in role semantics / enforcement bypasses).
_RESERVED_ROLE_NAMES: frozenset[str] = frozenset(
    {
        AdminUserRole.SUPER_ADMIN.value,
        AdminUserRole.ADMIN.value,
        AdminUserRole.MANAGER.value,
        AdminUserRole.EMPLOYEE.value,
    }
)


# ── Exceptions ────────────────────────────────────────────────────────────


class RoleNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )


class RoleNameConflictError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role name is already in use",
        )


class RoleImmutableError(HTTPException):
    def __init__(self, detail: str = "Role is immutable") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )


class RoleAssignedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role is assigned to users",
        )


class RoleNotCustomError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only custom roles support this operation",
        )


class SuperAdminRoleError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The super_admin role cannot be modified",
        )


class LastAdminError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last tenant admin",
        )


# ── Helpers ───────────────────────────────────────────────────────────────


async def get_system_role(session: AsyncSession, name: str) -> Role | None:
    """Fetch a system built-in role by name (tenant_id IS NULL)."""
    result = await session.execute(select(Role).where(Role.tenant_id.is_(None), Role.name == name))
    return result.scalar_one_or_none()


async def _get_role_for_tenant(
    session: AsyncSession, tenant_id: uuid.UUID, role_id: uuid.UUID
) -> Role:
    """Fetch a role by id: system built-in or this tenant's custom role.

    Returns None-style 404 via RoleNotFoundError for unknown roles or
    other tenants' custom roles (no cross-tenant leak).
    """
    stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    role = (await session.execute(stmt)).scalar_one_or_none()
    if role is None or (role.tenant_id is not None and role.tenant_id != tenant_id):
        raise RoleNotFoundError()
    return role


async def _replace_permissions(
    session: AsyncSession,
    role: Role,
    permissions: list[RolePermissionInput] | None,
) -> None:
    """Replace a role's permission rows with the granted inputs (None = no-op)."""
    if permissions is None:
        return
    # Ensure the collection is loaded (new roles have an unloaded empty set).
    await session.refresh(role, attribute_names=["permissions"])
    for old in list(role.permissions):
        await session.delete(old)
    role.permissions.clear()
    # Flush the DELETEs before inserting replacement rows (same unique keys).
    await session.flush()

    seen: set[tuple[str, str]] = set()
    for entry in permissions:
        if not entry.granted:
            continue
        pair = (entry.action, entry.resource)
        if pair in seen:
            continue
        seen.add(pair)
        row = RolePermission(
            role_id=role.id,
            action=entry.action,
            resource=entry.resource,
            granted=True,
        )
        session.add(row)
        role.permissions.append(row)


async def _assert_name_available(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    *,
    exclude_role_id: uuid.UUID | None = None,
) -> None:
    """Raise RoleNameConflictError for reserved names or per-tenant dupes."""
    if name in _RESERVED_ROLE_NAMES:
        raise RoleNameConflictError()
    stmt = select(Role.id).where(Role.tenant_id == tenant_id, Role.name == name)
    if exclude_role_id is not None:
        stmt = stmt.where(Role.id != exclude_role_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise RoleNameConflictError()


# ── Default role attachment ───────────────────────────────────────────────


async def attach_default_role(session: AsyncSession, user: AdminUser) -> None:
    """Set user.role_id from the role enum when missing (system role).

    Custom-role users (role not resolvable as a system role) fall back to
    the EMPLOYEE system role. No-op once role_id is already set.

    The lookups run inside a no_autoflush block: callers commonly add the
    user to the session before this runs, and a Query-invoked autoflush
    would try to INSERT the user with role_id still NULL (the column is
    NOT NULL per the FEAT-016 migration), raising IntegrityError.
    """
    if user.role_id is not None:
        return
    with session.no_autoflush:
        role = await get_system_role(session, user.role.value)
        if role is None:
            role = await get_system_role(session, AdminUserRole.EMPLOYEE.value)
    if role is not None:
        user.role_id = role.id


# ── CRUD ──────────────────────────────────────────────────────────────────


_SYSTEM_PROJECT_ROLE_IDS: dict[str, uuid.UUID] = {
    "lead": uuid.UUID("55555555-5555-4555-8555-555555555555"),
    "contributor": uuid.UUID("66666666-6666-4666-8666-666666666666"),
    "finance": uuid.UUID("77777777-7777-4777-8777-777777777777"),
    "viewer": uuid.UUID("88888888-8888-4888-8888-888888888888"),
}


async def list_roles(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    role_type: str | None = None,
) -> list[Role]:
    """List system built-in roles + this tenant's custom roles.

    The platform-level super_admin system role is excluded.
    """
    filters = [
        or_(Role.tenant_id.is_(None), Role.tenant_id == tenant_id),
        ~and_(Role.tenant_id.is_(None), Role.name == AdminUserRole.SUPER_ADMIN.value),
    ]
    if role_type:
        filters.append(Role.role_type == role_type)

    stmt = (
        select(Role)
        .where(*filters)
        .options(joinedload(Role.permissions))
        .order_by(Role.role_type, Role.tenant_id.is_not(None), Role.name)
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


async def create_role(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    description: str | None,
    role_type: str = "user",
    permissions: list[RolePermissionInput],
    actor_id: uuid.UUID,
) -> Role:
    """Create a tenant custom role with its granted permission rows."""
    await _assert_name_available(session, tenant_id, name)

    role = Role(
        tenant_id=tenant_id,
        name=name,
        description=description or "",
        role_type=role_type,
        is_system=False,
    )
    session.add(role)
    await session.flush()

    await _replace_permissions(session, role, permissions)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="role.created",
        entity_type="role",
        entity_id=str(role.id),
        details={"name": role.name},
    )
    clear_permission_cache()
    await session.commit()
    return role


async def update_role(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    role_id: uuid.UUID,
    name: str | None,
    description: str | None,
    permissions: list[RolePermissionInput] | None,
    actor_id: uuid.UUID,
) -> Role:
    """Update a role: system built-in or this tenant's custom role.

    super_admin/admin are immutable. Other system roles allow permission
    edits only (name/description locked). Custom roles allow everything.
    """
    role = await _get_role_for_tenant(session, tenant_id, role_id)

    if role.name == AdminUserRole.SUPER_ADMIN.value:
        raise SuperAdminRoleError()

    if role.name == AdminUserRole.ADMIN.value:
        if name is not None or description is not None or permissions is not None:
            raise RoleImmutableError("Full tenant access role cannot be edited")
        return role

    changed = False
    if role.is_system:
        # System roles other than admin: name/description immutable
        if name is not None or description is not None:
            raise RoleImmutableError("System role name and description are immutable")
    else:
        if name is not None and name != role.name:
            await _assert_name_available(session, tenant_id, name, exclude_role_id=role.id)
            role.name = name
            changed = True
        if description is not None and description != role.description:
            role.description = description
            changed = True

    if permissions is not None:
        await _replace_permissions(session, role, permissions)
        changed = True

    if changed:
        await session.flush()
        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="role.updated",
            entity_type="role",
            entity_id=str(role.id),
            details={"name": role.name},
        )
        clear_permission_cache()
        await session.commit()

    return role


async def delete_role(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    """Delete a tenant custom role. System roles and assigned roles are blocked."""
    role = await _get_role_for_tenant(session, tenant_id, role_id)

    if role.is_system:
        raise RoleNotCustomError()

    assigned_q = select(func.count()).select_from(AdminUser).where(AdminUser.role_id == role.id)
    assigned = (await session.execute(assigned_q)).scalar_one()
    if assigned > 0:
        raise RoleAssignedError()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="role.deleted",
        entity_type="role",
        entity_id=str(role.id),
        details={"name": role.name},
    )
    clear_permission_cache()
    await session.delete(role)
    await session.commit()


async def reset_role_defaults(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Role:
    """Restore a system role's permissions to the seed matrix (manager/employee).

    super_admin/admin are immutable; custom roles have no defaults to reset.
    """
    role = await _get_role_for_tenant(session, tenant_id, role_id)

    if role.name == AdminUserRole.SUPER_ADMIN.value:
        raise SuperAdminRoleError()
    if role.name == AdminUserRole.ADMIN.value:
        raise RoleImmutableError("Full tenant access role cannot be edited")
    if not role.is_system:
        raise RoleNotCustomError()

    if role.role_type == "project":
        seed = SYSTEM_PROJECT_ROLE_PERMISSIONS.get(role.name, frozenset())
    else:
        seed = SYSTEM_ROLE_PERMISSIONS.get(role.name, frozenset())

    await _replace_permissions(
        session,
        role,
        [RolePermissionInput(action=a, resource=r, granted=True) for a, r in sorted(seed)],
    )
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="role.updated",
        entity_type="role",
        entity_id=str(role.id),
        details={"name": role.name, "reset": True},
    )
    clear_permission_cache()
    await session.commit()
    return role


# ── Assignment ────────────────────────────────────────────────────────────


async def assign_user_role(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> AdminUser:
    """Assign a system or tenant custom role to a user in the tenant.

    Syncs user.role_id + the legacy role enum (system roles map by name,
    custom roles map to EMPLOYEE). Last-admin guard: demoting the only
    effective admin (enum ADMIN or role_ref "admin") is rejected.
    """
    stmt = (
        select(AdminUser)
        .where(AdminUser.id == target_user_id)
        .options(selectinload(AdminUser.role_ref))
    )
    target = (await session.execute(stmt)).scalar_one_or_none()
    if target is None or target.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    role = await _get_role_for_tenant(session, tenant_id, role_id)
    if role.name == AdminUserRole.SUPER_ADMIN.value:
        raise SuperAdminRoleError()

    old_enum = target.role
    is_admin_now = old_enum == AdminUserRole.ADMIN or (
        target.role_ref is not None and target.role_ref.name == AdminUserRole.ADMIN.value
    )
    new_is_admin = role.name == AdminUserRole.ADMIN.value

    if is_admin_now and not new_is_admin:
        other_admins_q = (
            select(func.count())
            .select_from(AdminUser)
            .outerjoin(Role, Role.id == AdminUser.role_id)
            .where(
                AdminUser.tenant_id == tenant_id,
                AdminUser.id != target_user_id,
                or_(
                    AdminUser.role == AdminUserRole.ADMIN,
                    Role.name == AdminUserRole.ADMIN.value,
                ),
            )
        )
        other_admins = (await session.execute(other_admins_q)).scalar_one()
        if other_admins == 0:
            raise LastAdminError()

    new_enum = AdminUserRole[role.name.upper()] if role.is_system else AdminUserRole.EMPLOYEE

    target.role_id = role.id
    target.role_ref = role
    target.role = new_enum

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="user.role_changed",
        entity_type="admin_user",
        entity_id=str(target.id),
        details={"from": old_enum.value, "to": new_enum.value},
    )
    await session.commit()
    return target


# ── Effective permissions (for auth responses) ─────────────────────────────


async def effective_permissions(session: AsyncSession, *, user: AdminUser) -> list[str]:
    """Effective "action.resource" grants for a user.

    super_admin + tenant-admin roles bypass: return the full catalog (all granted).
    Otherwise return the role's granted pairs from role_permissions.
    Falls back to the static matrix (has_permission) when role_id is None.
    """
    if user.role in (AdminUserRole.SUPER_ADMIN, AdminUserRole.ADMIN):
        return [f"{p['action']}.{p['resource']}" for p in PERMISSION_CATALOG]

    if user.role_id is None:
        return sorted(
            f"{p['action']}.{p['resource']}"
            for p in PERMISSION_CATALOG
            if has_permission(user.role, p["action"], p["resource"])
        )

    role = await session.get(Role, user.role_id)
    if role is not None and role.name in (
        AdminUserRole.SUPER_ADMIN.value,
        AdminUserRole.ADMIN.value,
    ):
        return [f"{p['action']}.{p['resource']}" for p in PERMISSION_CATALOG]

    stmt = select(RolePermission).where(RolePermission.role_id == user.role_id)
    rows = (await session.execute(stmt)).scalars().all()
    return sorted({f"{p.action}.{p.resource}" for p in rows if p.granted})


# ── Catalog ───────────────────────────────────────────────────────────────


async def clear_catalog_cache(tenant_id: uuid.UUID | None = None) -> None:
    """Clear tenant permission catalog cache."""
    from app.core.cache import cache, tenant_catalog_cache_key

    if tenant_id is not None:
        await cache.delete(tenant_catalog_cache_key(tenant_id))
    else:
        await cache.clear()


def get_permission_catalog() -> list[dict[str, str]]:
    """Return the permission catalog (action/resource/label/group) for the UI."""
    return PERMISSION_CATALOG


async def get_permission_catalog_for_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID
) -> list[dict[str, str]]:
    """Return the permission catalog scoped to the tenant's feature flags (cached)."""
    from app.core.cache import cache, tenant_catalog_cache_key

    key = tenant_catalog_cache_key(tenant_id)
    cached = await cache.get(key)
    if cached is not None:
        return cached

    from app.services.feature_flags import get_resolved_flags

    resolved_flags = await get_resolved_flags(session, tenant_id)
    flags_map = {f["key"]: f["enabled"] for f in resolved_flags}

    scoped: list[dict[str, str]] = []
    for item in PERMISSION_CATALOG:
        flag = FEATURE_KEY_BY_RESOURCE.get(item["resource"])
        if flag is not None and not flags_map.get(flag, True):
            continue
        scoped.append(item)

    await cache.set(key, scoped, expire=300)
    return scoped


async def sync_system_roles_and_permissions(session: AsyncSession) -> dict[str, int]:
    """Synchronize system built-in roles and permissions from SYSTEM_ROLE_PERMISSIONS.

    Idempotent:
    - Ensures all system roles exist (super_admin, admin, manager, employee).
    - Ensures all (action, resource) permissions in SYSTEM_ROLE_PERMISSIONS exist.
    - Safe to run on every application startup or CLI command.
    """
    system_role_descriptions: dict[str, str] = {
        AdminUserRole.SUPER_ADMIN.value: "Super admin with full platform access",
        AdminUserRole.ADMIN.value: "Tenant administrator with full tenant access",
        AdminUserRole.MANAGER.value: "Tenant manager with operational access",
        AdminUserRole.EMPLOYEE.value: "Tenant employee with standard access",
    }

    roles_created = 0
    perms_created = 0

    for role_name, role_id in _SYSTEM_ROLE_IDS.items():
        stmt = select(Role).where(
            Role.is_system == True,  # noqa: E712
            Role.tenant_id.is_(None),
            Role.name == role_name,
        )
        role = (await session.execute(stmt)).scalar_one_or_none()
        if role is None:
            role = Role(
                id=role_id,
                tenant_id=None,
                name=role_name,
                description=system_role_descriptions.get(
                    role_name, f"System built-in role: {role_name}"
                ),
                is_system=True,
            )
            session.add(role)
            await session.flush()
            roles_created += 1

        desired_perms = SYSTEM_ROLE_PERMISSIONS.get(role_name, frozenset())
        existing_stmt = select(RolePermission).where(RolePermission.role_id == role.id)
        existing_rows = (await session.execute(existing_stmt)).scalars().all()
        existing_pairs = {(p.action, p.resource) for p in existing_rows}

        for action, resource in desired_perms:
            if (action, resource) not in existing_pairs:
                session.add(
                    RolePermission(
                        id=uuid.uuid4(),
                        role_id=role.id,
                        action=action,
                        resource=resource,
                        granted=True,
                    )
                )
                perms_created += 1

    # Seed system project roles
    project_role_descriptions: dict[str, str] = {
        "lead": "Project lead with full management rights on the project",
        "contributor": "Project contributor managing milestones and files",
        "finance": "Project finance specialist managing invoices and purchases",
        "viewer": "Read-only access to project details and modules",
    }

    for role_name, role_id in _SYSTEM_PROJECT_ROLE_IDS.items():
        stmt = select(Role).where(
            Role.is_system == True,  # noqa: E712
            Role.tenant_id.is_(None),
            Role.name == role_name,
            Role.role_type == "project",
        )
        role = (await session.execute(stmt)).scalar_one_or_none()
        if role is None:
            role = Role(
                id=role_id,
                tenant_id=None,
                name=role_name,
                description=project_role_descriptions.get(
                    role_name, f"System project role: {role_name}"
                ),
                role_type="project",
                is_system=True,
            )
            session.add(role)
            await session.flush()
            roles_created += 1

        desired_perms = SYSTEM_PROJECT_ROLE_PERMISSIONS.get(role_name, frozenset())
        existing_stmt = select(RolePermission).where(RolePermission.role_id == role.id)
        existing_rows = (await session.execute(existing_stmt)).scalars().all()
        existing_pairs = {(p.action, p.resource) for p in existing_rows}

        for action, resource in desired_perms:
            if (action, resource) not in existing_pairs:
                session.add(
                    RolePermission(
                        id=uuid.uuid4(),
                        role_id=role.id,
                        action=action,
                        resource=resource,
                        granted=True,
                    )
                )
                perms_created += 1

    if roles_created > 0 or perms_created > 0:
        await session.commit()

    # Ensure default superadmin user exists
    await ensure_default_superadmin(session)

    return {"roles_created": roles_created, "permissions_created": perms_created}


async def ensure_default_superadmin(session: AsyncSession) -> AdminUser | None:
    """Idempotently ensure a superadmin user exists in the database.

    Reads credentials from SEED_SUPERADMIN_EMAIL and SEED_SUPERADMIN_PASSWORD environment variables.
    """
    stmt = select(AdminUser).where(AdminUser.role == AdminUserRole.SUPER_ADMIN)
    existing = (await session.execute(stmt)).scalars().first()
    if existing is not None:
        return existing

    email = os.getenv("SEED_SUPERADMIN_EMAIL", "admin@zenengr.dev").lower().strip()
    password = os.getenv("SEED_SUPERADMIN_PASSWORD", "password")

    super_role = await get_system_role(session, AdminUserRole.SUPER_ADMIN.value)
    superadmin = AdminUser(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
        full_name="Super Administrator",
        role=AdminUserRole.SUPER_ADMIN,
        role_id=super_role.id if super_role else None,
        is_active=True,
    )
    session.add(superadmin)
    await session.commit()
    return superadmin

