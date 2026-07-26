# Backend Standard

## Framework / stack

- Runtime: Python 3.14 (per `backend/pyproject.toml`)
- Framework: FastAPI (with `[standard]` extras)
- Package manager: uv (`uv.lock` present)
- Database: PostgreSQL 16
- ORM / query builder: SQLAlchemy 2.0 (to be added)
- Migrations: Alembic (to be added alongside SQLAlchemy)
- Auth: JWT (Bearer tokens) — to be added
- Validation: Pydantic v2 (built into FastAPI)
- Caching / queues: Redis (provided by Compose stack)
- Testing: pytest + httpx (ASGITransport) — to be added
- Deployment: Docker container (local via Compose); production target TBD (self-hosted)

## Architecture

Layered / hexagonal-ish. Suggested layout (create when implementing backend source):

```text
backend/
  app/
    main.py             # FastAPI app factory + router wiring
    api/                # Route modules (thin controllers — only I/O and HTTP concerns)
      v1/
    services/           # Business logic; no FastAPI/HTTP types
    repositories/       # SQLAlchemy data access
    models/             # ORM models / domain models
    schemas/            # Pydantic request/response schemas
    core/                # Settings, security (JWT), dependencies, logging
    db/                 # Engine, session, base, migrations bootstrap
    utils/              # Pure helpers
  tests/                # Mirror app/ layout; *_test.py
  pyproject.toml
  uv.lock
  Dockerfile
  .dockerignore
```

## API design

- Style: REST
- Base path / versioning: `/api/v1`
- All routes versioned under a single `v1` router; bump version only on breaking changes.
- Error response shape (uniform across all handlers):

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": {}
  }
}
```

- HTTP status usage: 400 (validation), 401 (unauthenticated), 403 (forbidden),
  404 (not found), 409 (conflict), 422 (FastAPI validation), 500 (unexpected).

## Conventions

- Validate all inputs at the API boundary (Pydantic schemas); never trust raw dicts.
- Keep business logic in `services/`, never in `routers/` or `models/`.
- Use dependency injection (FastAPI `Depends`) for sessions, settings, current user — no global state.
- Centralize error handling in a custom exception handler middleware (map service exceptions to the standard error envelope).
- Database sessions: yield-based dependency that commits/rollback-doesn't-leak; never commit inside repositories.
- All async I/O for DB (asyncpg / async SQLAlchemy) and Redis (redis-py asyncio).
- Write tests (pytest) for services and API routes; aim for service-level coverage.

## Code style

- Formatter: `ruff format` (to be configured in `pyproject.toml`)
- Linter: `ruff check` (select: E, F, I, N, UP, B, SIM, ASYNC, S) — note: `S` (bandit) for security-sensitive code paths
- Type checker: `mypy --strict` (or `pyright`) — to be configured
- Import ordering: `ruff`'s `I` (isort-compatible)
- Line length: 100 (matches `ruff format` default of 88 unless overridden; configure to 100 if desired)

## Database

- Use Alembic migrations for all schema changes; never apply schema edits via `Base.metadata.create_all` outside tests/seeds.
- Seed scripts under `backend/scripts/seed.py` for development data.
- Avoid N+1 queries — use `selectinload` / `joinedload` where relationships are needed.
- Async engine; sessions via `async with` + dependency injection.

## Commands

Run from `backend/` (uv):

- Create/refresh venv: `uv sync`
- Add dep: `uv add <package>`
- Add dev dep: `uv add --dev <package>`
- Run dev server: `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Run via fastapi CLI: `uv run fastapi dev --host 0.0.0.0 --port 8000`
- Lint: `uv run ruff check .`  _(once `ruff` added)_
- Format: `uv run ruff format .`  _(once `ruff` added)_
- Type check: `uv run mypy app`  _(once `mypy` added)_
- Test: `uv run pytest`  _(once `pytest` added)_
- Test single file: `uv run pytest tests/test_foo.py`
- Migration: `uv run alembic upgrade head` / `uv run alembic revision --autogenerate -m "msg"`  _(once `alembic` added)_

## Cross-service env contract (local Compose)

The backend reads the following (provided by `docker-compose.yml` from `.env`):

- `DATABASE_URL` — e.g. `postgresql+asyncpg://app:app@postgres:5432/app`
- `REDIS_URL` — e.g. `redis://redis:6379/0`
- `JWT_SECRET` — secret used to sign tokens
- `ENVIRONMENT` — `local` | `dev` | `prod`
- `CORS_ORIGINS` — comma-separated allowlist (the frontend origin for local dev)