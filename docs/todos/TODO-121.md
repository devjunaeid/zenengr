---
id: TODO-121
title: Backend app skeleton, settings, DB session, alembic, tooling
feature: FEAT-000
story: US-046
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-002]
blocks: [TODO-004, TODO-026, TODO-056, TODO-062, TODO-075, TODO-100, TODO-109, TODO-122]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-121 — Backend app skeleton, settings, DB session, alembic, tooling

## Description

Create the full backend application skeleton per `docs/backend-standard.md`: app factory, v1 router with health endpoint, pydantic-settings config (env-aware), async DB engine + session, uniform error handlers, Alembic async setup, ruff/mypy/pytest tooling config in pyproject.toml. Delete old root `main.py`, update Docker entrypoints to `app.main:app`.

## Acceptance criteria

- [x] Directory layout: `app/`, `app/api/v1/`, `app/core/`, `app/db/`, `tests/`
- [x] `app/main.py` has `create_app()` factory wiring CORS + error handlers + v1 router
- [x] `GET /api/v1/health` returns `{"status": "ok"}`
- [x] `app/core/config.py` — `Settings` via pydantic-settings with `database_url`, `redis_url`, `jwt_secret`, `environment`, `cors_origins` (comma-sep -> list); `lru_cache` get_settings()
- [x] `app/core/errors.py` — uniform error envelope + handlers for HTTPException, RequestValidationError, generic 500
- [x] `app/db/base.py` — `DeclarativeBase` subclass with naming convention
- [x] `app/db/session.py` — async engine + session factory + `get_session` dependency
- [x] `tests/conftest.py` — app fixture + httpx AsyncClient via ASGITransport
- [x] `tests/test_health.py` — health returns 200 + 404 returns error envelope
- [x] Alembic async env with `target_metadata = Base.metadata`
- [x] `pyproject.toml` — ruff (line-length 100, select E,F,I,N,UP,B,SIM,ASYNC,S), mypy strict, pytest asyncio_mode=auto
- [x] Dependencies: sqlalchemy[asyncio], asyncpg, pydantic-settings, PyJWT, passlib[bcrypt], redis, email-validator
- [x] Dev dependencies: ruff, mypy, pytest, pytest-asyncio, httpx, alembic
- [x] Root `main.py` deleted; Docker entrypoints updated to `app.main:app`
- [x] All tooling passes green

## Notes

Skeleton only — no business logic in this batch. `passlib[bcrypt]` used for password hashing (pwdlib argon2 extra unavailable on this Python version).
