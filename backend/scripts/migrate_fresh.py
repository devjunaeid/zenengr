"""Database wipe, fresh migration, and seed runner (Laravel-style migrate:fresh --seed).

Usage:
  python -m scripts.migrate_fresh
  # Or via uv:
  uv run python -m scripts.migrate_fresh
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from scripts.seed_dev import seed


async def reset_database() -> None:
    settings = get_settings()
    db_url = settings.database_url
    print(f"==> Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    # 1. Drop and recreate public schema
    print("==> 1/3: Dropping and recreating public schema...")
    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC;"))
    await engine.dispose()
    print("    [✓] Database schema wiped clean.")

    # 2. Run Alembic upgrade head
    print("==> 2/3: Running Alembic migrations from scratch (upgrade head)...")
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")
    print("    [✓] All tables and indexes migrated successfully.")

    # 3. Seed initial system data & demo tenant
    print("==> 3/3: Seeding initial system data and demo tenant...")
    await seed()
    print("    [✓] Database seeded successfully!")
    print("\n🎉 Fresh migration complete!")


def main() -> None:
    asyncio.run(reset_database())


if __name__ == "__main__":
    main()
