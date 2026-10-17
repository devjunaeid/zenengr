---
name: fastapi-async-sqlalchemy
description: Guidelines and patterns for developing backend services with FastAPI, SQLAlchemy 2.0 Async, PostgreSQL, Redis caching, Alembic, and targeted testing. Use when writing, editing, or testing backend endpoints, database models, or services.
---

# FastAPI & Async SQLAlchemy 2.0 Development Skill

This skill guides development for the project's backend stack: **FastAPI 0.140+**, **SQLAlchemy 2.0 (asyncio)**, **asyncpg**, **PostgreSQL 16**, **Redis / cashews**, **Alembic**, and **Docker dev stack**.

---

## 1. Async SQLAlchemy 2.0 Query Patterns

Always use async SQLAlchemy 2.0 style queries. Never use legacy 1.x session query syntax (`session.query(...)`).

### Executing Queries:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

async def get_user_with_roles(db: AsyncSession, user_id: str) -> User | None:
    # Use selectinload/joinedload to prevent MissingGreenlet lazy-loading errors
    stmt = (
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

### Commit & Flush:
* Prefer letting FastAPI request dependency handle commit/rollback on session close, or call `await db.commit()` / `await db.flush()` explicitly when IDs are needed immediately.
* Always handle database exceptions and rollback if managing manual transactions.

---

## 2. API & Controller Conventions

* **Base Path**: All endpoints are under `/api/v1/`.
* **Layered Architecture**:
  * `app/api/v1/`: Thin controllers only. Handle I/O, status codes, query/body parsing.
  * `app/services/`: Business logic. Free of HTTP/FastAPI dependencies.
  * `app/repositories/` or `app/db/`: Data access logic and SQLAlchemy models.
  * `app/schemas/`: Pydantic v2 schemas (`BaseModel` with strict type hints).
* **Standard Error Responses**:
  ```json
  {
    "error": {
      "code": "NOT_FOUND",
      "message": "Resource not found",
      "details": {}
    }
  }
  ```
* **Dependency Injection**: Use `Depends(get_db)` to acquire `AsyncSession`.

---

## 3. Caching with Redis (`cashews`)

* Use `cashews` cache decorators for expensive reads or token validations:
  ```python
  from cashews import cache

  @cache(ttl="10m", key="items:{tenant_id}")
  async def get_cached_items(tenant_id: str):
      ...
  ```
* Explicit cache invalidation when data mutations occur:
  ```python
  await cache.delete_match(f"items:{tenant_id}*")
  ```

---

## 4. Alembic Migrations

When models in `app/models/` are added or altered:
1. Generate migration:
   `docker exec zenengr-backend-dev-1 uv run alembic revision --autogenerate -m "describe_change"`
   *(or run via host if connected to container Postgres port 5432)*
2. Inspect the generated migration in `backend/alembic/versions/` for safety.
3. Apply migration:
   `docker exec zenengr-backend-dev-1 uv run alembic upgrade head`

---

## 5. Development & Targeted Testing Rules

The dev server runs inside Docker (`zenengr-backend-dev-1`) with live volume mounts.

* **Targeted Test Rule**:
  **Never run the full test suite when verifying a single module change.**
  Run tests only for the modified module inside the container:
  ```bash
  docker exec zenengr-backend-dev-1 uv run pytest tests/test_<module>.py
  ```
* **Targeted Lint / Type Check**:
  Check only the modified files:
  ```bash
  uv run ruff check path/to/file.py
  uv run mypy path/to/file.py
  ```
* **Dependency Addition**:
  If adding a backend dependency, rebuild the backend dev container:
  ```bash
  docker compose --profile dev up -d --build backend-dev
  ```
