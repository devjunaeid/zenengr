"""Sync system roles and permissions CLI script.

Usage:
    uv run sync-permissions
    # or
    uv run python scripts/sync_permissions.py
"""

from __future__ import annotations

import asyncio
import sys

from app.db.session import async_session_factory
from app.services.roles import sync_system_roles_and_permissions


async def main_async() -> int:
    print("Synchronizing system roles and permissions...", end="", flush=True)
    try:
        async with async_session_factory() as session:
            res = await sync_system_roles_and_permissions(session)
            print(
                f" \033[32m[DONE]\033[0m (Roles created: {res['roles_created']}, "
                f"Permissions added: {res['permissions_created']})"
            )
        return 0
    except Exception as exc:
        print(f" \033[31m[FAILED]\033[0m\nError: {exc}")
        return 1


def main() -> None:
    code = asyncio.run(main_async())
    sys.exit(code)


if __name__ == "__main__":
    main()
