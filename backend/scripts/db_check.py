"""Database connection health and inspection tool.

Run via:
    uv run db-check
    # or
    uv run python scripts/db_check.py
"""

from __future__ import annotations

import asyncio
import sys
import time

from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


def _mask_url(url_str: str) -> str:
    try:
        url = make_url(url_str)
        return url.render_as_string(hide_password=True)
    except Exception:
        return url_str


async def check_database() -> int:
    settings = get_settings()
    masked_url = _mask_url(settings.database_url)

    print("==================================================")
    print(" 🔍 PostgreSQL Connection Inspector")
    print("==================================================")
    print(f" • Target URL:   {masked_url}")
    print(" • Environment:  " + settings.environment)
    print("--------------------------------------------------")
    print(" Connecting to database...", end="", flush=True)

    start_time = time.perf_counter()
    try:
        engine = create_async_engine(settings.database_url, connect_args={"timeout": 10})
        async with engine.connect() as conn:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            print(f" \033[32m[SUCCESS]\033[0m ({elapsed_ms:.1f}ms)")
            print("--------------------------------------------------")

            db_name = (await conn.execute(text("SELECT current_database()"))).scalar()
            user_name = (await conn.execute(text("SELECT current_user"))).scalar()
            server_addr = (await conn.execute(text("SELECT inet_server_addr()"))).scalar()
            server_port = (await conn.execute(text("SELECT inet_server_port()"))).scalar()
            version_str = (await conn.execute(text("SELECT version()"))).scalar()

            # Check alembic migration head if table exists
            alembic_rev = "None / Not initialized"
            try:
                rev_res = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                val = rev_res.scalar()
                if val:
                    alembic_rev = str(val)
            except Exception:
                pass

            print(f" • Active Database:   \033[1m{db_name}\033[0m")
            print(f" • Authenticated As:  \033[1m{user_name}\033[0m")
            print(f" • Server Endpoint:   {server_addr or 'localhost'}:{server_port or 5432}")
            print(f" • Alembic Revision:  {alembic_rev}")
            print(f" • Server Version:    {version_str.split(',')[0] if version_str else 'Unknown'}")
            print("==================================================")
            print(" \033[32m✔ Connection is healthy and ready to use.\033[0m")
            print("==================================================")

        await engine.dispose()
        return 0

    except Exception as exc:
        print(" \033[31m[FAILED]\033[0m")
        print("--------------------------------------------------")
        print(f" \033[31mError:\033[0m {exc}")
        print("==================================================")
        print(" 💡 Troubleshooting Tips:")
        print("  1. If password has special characters (+, }, *, @), URL-encode them.")
        print("  2. Verify PostgreSQL server is running and port 5432 is accessible.")
        print("  3. Check pg_hba.conf permits connections for this user & database.")
        print("==================================================")
        return 1


def main() -> None:
    code = asyncio.run(check_database())
    sys.exit(code)


if __name__ == "__main__":
    main()
